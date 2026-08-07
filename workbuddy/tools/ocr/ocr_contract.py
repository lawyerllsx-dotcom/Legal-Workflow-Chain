#!/usr/bin/env python
"""Local OCR — Usage: python ocr_contract.py <file> [output_dir] [options]

Engines:
  - v6 (default): PP-OCRv6 medium + OpenVINO GPU (~2.8s/p)
  - vl: PaddleOCR-VL-1.6, ~20s/p, complex layout fallback

Features:
  - Auto digital/scanned page detection & routing
  - Result caching (PDF hash → skip re-OCR)
  - Checkpoint/resume (interrupted runs pick up where they left off)
  - Optional image preprocessing (deskew + CLAHE for poor scans)
  - Stale tmp cleanup on startup
  - Batch mode: --batch <folder> processes all PDFs recursively
  - Auto-fallback: low-yield pages auto-retry with VL engine
"""
import os, sys, time, tempfile, shutil, hashlib, json, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))  # for extract_legal_entities
from datetime import datetime, timedelta

# ── Environment ──────────────────────────────────────────────
os.environ.setdefault('PADDLEX_HOME', 'D:/ai-models/.paddlex')
os.environ.setdefault('MODELSCOPE_CACHE', 'D:/ai-models/.cache/modelscope')
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

# ── Paths ────────────────────────────────────────────────────
MODEL_DIR      = Path(r'D:\ai-models')
VLM_MODEL       = str(MODEL_DIR / 'PaddleOCR-VL-1.6-ov')
LAYOUT_MODEL    = str(MODEL_DIR / '.cache/modelscope/zhaohb/PaddleOCR-VL-1.5-ov/PP-DoclayoutV3-ov/DocLayoutV3.xml')
TMP_ROOT        = MODEL_DIR / 'tmp'
CACHE_DIR       = MODEL_DIR / 'cache'

# ── GPU Acceleration (OpenVINO ONNX Runtime patch) ────────────
_OV_READY = False
_OV_MODELS = {}
try:
    import openvino as _ov
    import onnxruntime as _ort
    _ov_core = _ov.Core()
    if 'GPU' in _ov_core.available_devices:
        def _get_ov_model(onnx_path):
            path = str(onnx_path)
            if path not in _OV_MODELS:
                ir_path = path.replace('.onnx', '.xml')
                if os.path.exists(ir_path):
                    _OV_MODELS[path] = _ov_core.compile_model(ir_path, 'GPU')
                else:
                    return None
            return _OV_MODELS[path]

        _orig_run = _ort.InferenceSession.run
        def _patched_run(self, output_names, input_feed, run_options=None):
            ov_model = _get_ov_model(self._model_path)
            if ov_model is not None:
                ov_input = {}
                for inp in ov_model.inputs:
                    name = inp.get_any_name()
                    for onnx_name, value in input_feed.items():
                        ov_input[name] = value
                        break
                result = ov_model(ov_input)
                return [result[out] for out in ov_model.outputs]
            return _orig_run(self, output_names, input_feed, run_options)
        _ort.InferenceSession.run = _patched_run
        _OV_READY = True
except Exception:
    pass  # CPU fallback if GPU unavailable
MIN_TEXT_CHARS  = 30
TMP_MAX_AGE_H   = 24
RETRY_MAX       = 3       # Max retries per page on crash
RETRY_BASE_S    = 3       # Base backoff seconds

CACHE_DIR.mkdir(parents=True, exist_ok=True)
TMP_ROOT.mkdir(parents=True, exist_ok=True)

# ── Preprocessing (lazy import) ──────────────────────────────
_has_cv2 = None
def _check_cv2():
    global _has_cv2
    if _has_cv2 is None:
        try:
            import cv2, numpy
            _has_cv2 = True
        except ImportError:
            _has_cv2 = False
    return _has_cv2


def preprocess_image(img_path: str) -> str:
    """Apply deskew + CLAHE to improve OCR on poor-quality scans.
    Returns path to preprocessed image (overwrites input if in tmp dir,
    otherwise creates a new tmp file)."""
    if not _check_cv2():
        print('   [WARN] OpenCV not available, skipping preprocessing')
        return img_path

    import cv2, numpy as np
    img = cv2.imread(img_path)
    if img is None:
        print('   [WARN] Cannot read image for preprocessing')
        return img_path

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # ── Deskew ────────────────────────────────────────────
    # Use binary threshold to find text pixels, then minAreaRect for angle
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) > 100:
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        # Only correct if skew > 0.5 degrees
        if abs(angle) > 0.5:
            h, w = gray.shape
            M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
            gray = cv2.warpAffine(gray, M, (w, h),
                                  flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_REPLICATE)

    # ── CLAHE (adaptive contrast) ─────────────────────────
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    cv2.imwrite(img_path, gray)
    return img_path


# ── tmp cleanup ──────────────────────────────────────────────
def cleanup_stale_tmp(max_age_hours: int = TMP_MAX_AGE_H):
    """Remove temp directories older than max_age_hours."""
    now = time.time()
    cleaned = 0
    for entry in TMP_ROOT.iterdir():
        if entry.is_dir() and (entry.name.startswith('ocr_') or entry.name.startswith('tmp')):
            age_h = (now - entry.stat().st_mtime) / 3600
            if age_h > max_age_hours:
                shutil.rmtree(entry, ignore_errors=True)
                cleaned += 1
        elif entry.is_file() and entry.suffix in ('.png', '.jpg', '.jpeg'):
            age_h = (now - entry.stat().st_mtime) / 3600
            if age_h > max_age_hours:
                entry.unlink(missing_ok=True)
                cleaned += 1
    if cleaned:
        print(f'[CLEAN] Removed {cleaned} stale tmp entries (> {max_age_hours}h)')


def _cleanup_stale_cache(max_age_days: int = 30):
    """Remove cached results older than max_age_days."""
    now = time.time()
    cleaned = 0
    for entry in CACHE_DIR.glob('*.md'):
        age_d = (now - entry.stat().st_mtime) / 86400
        if age_d > max_age_days:
            entry.unlink(missing_ok=True)
            meta = entry.with_suffix('.meta.json')
            meta.unlink(missing_ok=True)
            cleaned += 1
    if cleaned:
        print(f'[CACHE] Removed {cleaned} stale entries (> {max_age_days}d)')


# ── File resolution ──────────────────────────────────────────
def resolve_path(raw: str) -> Path:
    """Resolve a file path, with fuzzy search fallback for encoding issues."""
    p = Path(raw)
    if p.exists():
        return p.resolve()
    # Fuzzy search by filename (handles Git Bash encoding garbling)
    name = p.name
    for search_dir in [r'D:\\', os.path.expanduser('~')]:
        if not os.path.exists(search_dir):
            continue
        for root, dirs, files in os.walk(search_dir):
            if name in files:
                found = Path(root) / name
                if found.exists():
                    return found.resolve()
    raise FileNotFoundError(f"Cannot find: {raw}")


# ── Caching ──────────────────────────────────────────────────
def compute_file_fingerprint(file_path: Path) -> str:
    """Compute a stable fingerprint for a file: MD5 of path + size + mtime."""
    stat = file_path.stat()
    raw = f"{file_path.resolve()}|{stat.st_size}|{stat.st_mtime}"
    return hashlib.md5(raw.encode()).hexdigest()


def check_cache(fp: str) -> Path | None:
    """Return cached .md path if it exists and is non-empty."""
    cached = CACHE_DIR / f"{fp}.md"
    if cached.exists() and cached.stat().st_size > 0:
        return cached
    return None


def save_cache(fp: str, md_path: Path):
    """Copy result to cache and write metadata."""
    import shutil as sh
    cached_md = CACHE_DIR / f"{fp}.md"
    sh.copy2(md_path, cached_md)
    meta = {
        'fingerprint': fp,
        'cached_at': datetime.now().isoformat(),
        'source_md': str(md_path),
    }
    (CACHE_DIR / f"{fp}.meta.json").write_text(json.dumps(meta, ensure_ascii=False))


def list_cache():
    """List all cached entries."""
    entries = []
    for meta_file in sorted(CACHE_DIR.glob('*.meta.json')):
        meta = json.loads(meta_file.read_text())
        entries.append(meta)
    return entries


# ── Checkpoint ───────────────────────────────────────────────
def load_checkpoint(output_dir: Path, pdf_stem: str, pdf_fingerprint: str) -> tuple[set[int], Path | None]:
    """Return (set of completed page numbers, path to existing md file or None).
    If PDF fingerprint changed, invalidate checkpoint and return empty."""
    cp_file = output_dir / f"{pdf_stem}.checkpoint.json"
    md_file  = output_dir / f"{pdf_stem}.md"
    if not cp_file.exists():
        return set(), md_file if md_file.exists() else None
    try:
        cp = json.loads(cp_file.read_text())
        if cp.get('pdf_fingerprint') != pdf_fingerprint:
            print('   [CKPT] PDF changed since last run, invalidating checkpoint')
            cp_file.unlink()
            return set(), None
        return set(cp.get('completed_pages', [])), md_file if md_file.exists() else None
    except (json.JSONDecodeError, KeyError):
        return set(), None


def save_checkpoint(output_dir: Path, pdf_stem: str, completed: set[int],
                    pdf_fingerprint: str, total_pages: int):
    """Write checkpoint file."""
    cp_file = output_dir / f"{pdf_stem}.checkpoint.json"
    cp = {
        'pdf_fingerprint': pdf_fingerprint,
        'total_pages': total_pages,
        'completed_pages': sorted(completed),
        'updated': datetime.now().isoformat(),
    }
    cp_file.write_text(json.dumps(cp, ensure_ascii=False))


# ── PDF Processing ───────────────────────────────────────────
def process_pdf_pages(pdf_path: Path, dpi: int = 150, preprocess: bool = False,
                      page_range: tuple[int, int] | None = None):
    """Returns (pages, tmp_dir) where pages = [(page_num, content_or_img_path, is_text)].

    page_range: (start, end) 1-based inclusive, None = all pages."""
    try:
        import fitz
    except ImportError:
        import pymupdf as fitz  # PyMuPDF 1.28+ may drop the fitz alias
    doc = fitz.open(str(pdf_path))
    total = doc.page_count

    if page_range:
        start, end = page_range
        start = max(1, start)
        end = min(total, end)
    else:
        start, end = 1, total

    pages = []
    tmp = tempfile.mkdtemp(prefix='ocr_', dir=str(TMP_ROOT))
    mat = fitz.Matrix(dpi / 72, dpi / 72)

    for i in range(start - 1, end):
        page = doc.load_page(i)
        text = page.get_text().strip()
        if len(text) >= MIN_TEXT_CHARS:
            pages.append((i + 1, text, True))
            print(f'   P{i+1}: digital ({len(text)} chars) → instant')
        else:
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = os.path.join(tmp, f'page_{i+1:04d}.png')
            pix.save(img)
            if preprocess:
                img = preprocess_image(img)
            pages.append((i + 1, img, False))
            print(f'   P{i+1}: scanned → OCR' + (' (preprocessed)' if preprocess else ''))

    doc.close()
    n_digital = sum(1 for p in pages if p[2])
    n_scanned = len(pages) - n_digital
    print(f'      {n_digital} digital + {n_scanned} scanned = {len(pages)} pages (P{start}-P{end} of {total})')
    return pages, tmp


# ── Crash Recovery ─────────────────────────────────────────────
def _retry_predict(pipeline, content, page_num: int, total_pages: int,
                   engine_label: str = 'OCR') -> tuple:
    """Call pipeline.predict() with retry on crash. Returns (result, attempts)."""
    import traceback
    import types
    last_err = None
    for attempt in range(1, RETRY_MAX + 1):
        try:
            result = pipeline.predict(content)
            # Newer PaddleOCR pipelines return a generator — materialize it here
            # so callers can safely iterate/wrap it (fixes: 'generator' object
            # has no attribute '_to_markdown'). list() also forces lazy errors
            # to surface inside this try block so retry still works.
            if isinstance(result, types.GeneratorType):
                result = list(result)
            if attempt > 1:
                print(f'   [RETRY] P{page_num}/{total_pages}: attempt {attempt} OK')
            return result, attempt
        except Exception as e:
            last_err = e
            if attempt < RETRY_MAX:
                delay = RETRY_BASE_S * attempt
                print(f'   [RETRY] P{page_num}/{total_pages}: crashed ({str(e)[:60]}), '
                      f'retry {attempt+1}/{RETRY_MAX} in {delay}s...')
                time.sleep(delay)
            else:
                traceback.print_exc()
    raise last_err

# ── Main (single file) ───────────────────────────────────────
def process_single(input_path: Path, output_dir: Path, preprocess: bool = False,
                   force: bool = False,
                   page_range: tuple[int, int] | None = None,
                   engine: str = 'v6', extract: bool = False,
                   verify: bool = True, summary: bool = False) -> Path:
    """Process a single PDF/image. Returns path to output .md file.

    page_range: (start, end) 1-based inclusive, None = all pages.
    engine: 'v6' (PP-OCRv6, fastest, default), 'rapid' (PP-OCRv4), 'vl' (PaddleOCR-VL, complex layouts)."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Page-range suffix for output filename ──────────────
    if page_range:
        stem = f'{input_path.stem}_P{page_range[0]}-{page_range[1]}'
    else:
        stem = input_path.stem

    # ── Check cache ────────────────────────────────────────
    # Cache is keyed by (file_fingerprint + page_range)
    fp = compute_file_fingerprint(input_path)
    if page_range:
        fp = hashlib.md5(f"{fp}|{page_range[0]}-{page_range[1]}".encode()).hexdigest()

    if not force:
        cached = check_cache(fp)
        if cached:
            dest = output_dir / f'{stem}.md'
            if not dest.exists() or dest.stat().st_size == 0:
                shutil.copy2(cached, dest)
            print(f'[CACHE HIT] {input_path.name} (pages {page_range[0]}-{page_range[1]}) → {dest}' if page_range
                  else f'[CACHE HIT] {input_path.name} → {dest}')
            return dest

    # ── Checkpoint ─────────────────────────────────────────
    completed_pages, existing_md = load_checkpoint(output_dir, stem, fp)

    ext = input_path.suffix.lower()
    cleanup_dir = None
    pages = []
    has_scanned = False

    if ext == '.pdf':
        range_label = f' (P{page_range[0]}-{page_range[1]})' if page_range else ''
        print(f'[PDF] {input_path.name}{range_label}')
        pages, cleanup_dir = process_pdf_pages(input_path, preprocess=preprocess,
                                                page_range=page_range)
        has_scanned = any(not p[2] for p in pages)
    else:
        tmp = tempfile.mkdtemp(prefix='ocr_', dir=str(TMP_ROOT))
        cleanup_dir = tmp
        safe = os.path.join(tmp, 'input' + ext)
        shutil.copy2(input_path, safe)
        if preprocess:
            safe = preprocess_image(safe)
        pages = [(1, safe, False)]
        has_scanned = True
        print(f'[IMG] {input_path.name}' + (' (preprocessed)' if preprocess else ''))

    total_pages = len(pages)

    if completed_pages:
        skipped = sum(1 for p in pages if p[0] in completed_pages)
        print(f'[CKPT] Resuming: {len(completed_pages)}/{total_pages} already done, {total_pages - len(completed_pages)} remaining')

    # ── Load pipeline if needed ────────────────────────────
    pipeline = None
    vl_cached = None  # Cache VL model across pages
    pending_scanned = any(not p[2] and p[0] not in completed_pages for p in pages)

    if pending_scanned:
        if engine == 'v6':
            from paddleocr import PaddleOCR
            print('[LOAD] PaddleOCR (PP-OCRv6: medium_det + medium_rec)', end='', flush=True)
            t0 = time.time()
            pipeline = PaddleOCR(
                text_detection_model_name='PP-OCRv6_medium_det',
                text_detection_model_dir='D:/ai-models/PP-OCRv6/det_onnx',
                text_recognition_model_name='PP-OCRv6_medium_rec',
                text_recognition_model_dir='D:/ai-models/PP-OCRv6/rec_med_onnx',
                textline_orientation_model_name='PP-LCNet_x1_0_textline_ori',
                textline_orientation_model_dir='D:/ai-models/PP-OCRv6/textline_ori_onnx',
                engine='onnxruntime',
                use_textline_orientation=True,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
            )
            print(f' {time.time() - t0:.1f}s')
        else:  # vl
            from paddleocr_vl_openvino.paddleocr_vl_pipeline import PaddleOCRVL
            print('[LOAD] PaddleOCR-VL (OpenVINO CPU)', end='', flush=True)
            t0 = time.time()
            pipeline = PaddleOCRVL(
                vlm_model_path=VLM_MODEL, layout_model_path=LAYOUT_MODEL,
                vlm_device='CPU', layout_device='CPU', layout_precision='fp16',
                vision_int8_quant=True, llm_int8_compress=True,
            )
            print(f' {time.time() - t0:.1f}s')
    else:
        print('[LOAD] Skipped (no pending scanned pages)')

    # ── Process pages ──────────────────────────────────────
    md_file = output_dir / f'{stem}.md'
    mode = 'a' if existing_md and completed_pages else 'w'

    total_chars = 0; total_time = 0.0
    n_processed = 0
    batch_start = time.time()
    b_pages_verify_candidate = 0  # B pages with >3 low-conf lines (--verify would help)
    b_pages_isolated_noise = 0    # B pages with <=3 low-conf lines (isolated, --verify won't help)
    grade_counts = {'A': 0, 'B': 0, 'C': 0}
    vl_cross_checks = 0
    vl_loaded = False
    quality_rows = []             # Per-page quality data for report

    with open(md_file, mode, encoding='utf-8') as out:
        if mode == 'w':
            out.write(f'# {input_path.stem}\n\n')

        for pg_num, content, is_text in pages:
            if pg_num in completed_pages:
                continue

            grade = 'TXT'; n_lines = 0; avg_conf = None; txt = ''

            if is_text:
                t0 = time.time()
                out.write(f'## Page {pg_num} (digital)\n\n{content}\n\n---\n\n')
                elapsed = time.time() - t0
                total_chars += len(content)
                print(f'   P{pg_num}/{total_pages}: {elapsed:.3f}s, {len(content)}c [digital]')
            elif engine == 'v6' and pipeline:
                # PaddleOCR official pipeline (PP-OCRv6)
                t0 = time.time()
                result, retry_n = _retry_predict(pipeline, content, pg_num, total_pages, 'V6')
                lines = []
                all_scores = []
                low_conf_lines = []
                if result:
                    for res in result:
                        texts = res.get('rec_texts', [])
                        scores = res.get('rec_scores', [])
                        for txt, score in zip(texts, scores):
                            s = float(score)
                            all_scores.append(s)
                            marker = ' [!]' if s < 0.7 else (' [~]' if s < 0.85 else '')
                            lines.append(f'{txt}  [{s:.2f}]{marker}')
                            if s < 0.7:
                                low_conf_lines.append(str(txt)[:60])
                    txt = '\n'.join(lines)
                else:
                    txt = ''
                elapsed = time.time() - t0
                total_time += elapsed; total_chars += len(txt)
                n_lines = len(all_scores)
                avg_conf = sum(all_scores) / len(all_scores) if all_scores else 0

                # ── Page quality grade ──────────────────────
                if n_lines >= 40 and avg_conf > 0.9:
                    grade = 'A'
                elif n_lines >= 20 and avg_conf > 0.7:
                    grade = 'B'
                else:
                    grade = 'C'
                grade_counts[grade] = grade_counts.get(grade, 0) + 1

                grade_note = f'[Grade {grade}] {n_lines} lines, avg conf {avg_conf:.2f}'
                if low_conf_lines:
                    grade_note += f', {len(low_conf_lines)} low-confidence lines'

                WARN_LINES = 5
                WARN_CHARS = 100
                low_yield = (n_lines < WARN_LINES and len(txt) < WARN_CHARS) or \
                            (n_lines > 0 and avg_conf < 0.5)  # garbage detection

                if not low_yield:
                    out.write(f'> {grade_note}\n\n')

                # ── Cross-verify low-confidence lines with VL ─
                vl_verified = 0
                vl_conflicts = []
                # Cross-verify: C pages always, B pages only if --verify AND >3 low-conf lines
                need_verify = (grade == 'C') or (verify and grade == 'B' and len(low_conf_lines) > 3)
                if low_conf_lines and need_verify and not low_yield:
                    print(f'   [VL] Cross-verifying {len(low_conf_lines)} low-confidence lines...')
                    t_vl_start = time.time()
                    try:
                        if vl_cached is None:
                            from paddleocr_vl_openvino.paddleocr_vl_pipeline import PaddleOCRVL
                            t0 = time.time()
                            vl_cached = PaddleOCRVL(
                                vlm_model_path=VLM_MODEL, layout_model_path=LAYOUT_MODEL,
                                vlm_device='CPU', layout_device='CPU', layout_precision='fp16',
                                vision_int8_quant=True, llm_int8_compress=True,
                            )
                            vl_loaded = True
                            print(f'   [VL] Loaded {time.time()-t0:.1f}s')
                        vl_cross_checks += 1
                        cv_result, cv_retry = _retry_predict(vl_cached, content, pg_num, total_pages, 'VL')
                        for vl_res in (cv_result if isinstance(cv_result, list) else [cv_result]):
                            vl_md = vl_res._to_markdown()
                            vl_text = vl_md.get('markdown_texts', '') if isinstance(vl_md, dict) else ''

                            for lc_line in low_conf_lines:
                                stripped = lc_line.strip()
                                if stripped and stripped in vl_text:
                                    vl_verified += 1
                                else:
                                    vl_lines = [l for l in vl_text.split('\n') if l.strip()]
                                    best = None
                                    for vl_line in vl_lines:
                                        if stripped and any(c in vl_line for c in stripped if len(c.strip()) > 0):
                                            best = vl_line[:100]
                                            break
                                    vl_conflicts.append((stripped, best))
                            break
                        t_vl = time.time() - t_vl_start
                        print(f'   [VL] Done {t_vl:.1f}s | verified {vl_verified}, conflicts {len(vl_conflicts)}')
                    except Exception as e:
                        print(f'   [VL] Cross-verify failed ({time.time()-t_vl_start:.0f}s): {str(e)[:80]}')

                out.write(f'## Page {pg_num}\n\n{txt}\n\n---\n\n')
                if low_conf_lines:
                    if grade == 'B':
                        if len(low_conf_lines) > 3:
                            b_pages_verify_candidate += 1
                        else:
                            b_pages_isolated_noise += 1
                    out.write(f'> ⚠️ Low-confidence lines ({len(low_conf_lines)}): VL verified {vl_verified}, conflicts {len(vl_conflicts)}\n')
                    for lc in low_conf_lines[:5]:
                        out.write(f'>   - {lc}\n')
                    if vl_conflicts:
                        out.write(f'> ⚠️ VL disagreements:\n')
                        for v6_line, vl_line in vl_conflicts[:5]:
                            vl_show = vl_line[:80] if vl_line else '(no match)'
                            out.write(f'>   v6: {v6_line}\n')
                            out.write(f'>   vl: {vl_show}\n')
                    if len(low_conf_lines) > 5:
                        out.write(f'>   - ... and {len(low_conf_lines) - 5} more\n')
                    out.write('\n')
                out.write('---\n\n')
                elapsed_total = time.time() - batch_start
                eta = elapsed_total / n_processed * (total_pages - n_processed) if n_processed > 0 else 0
                eta_str = f'ETA {eta/60:.0f}m' if eta > 60 else f'ETA {eta:.0f}s'
                stuck_warn = ' [STUCK?]' if elapsed > 120 else ''
                print(f'   P{pg_num}/{total_pages}: {elapsed:.1f}s, {len(txt)}c, {n_lines} lines [{grade}] [{elapsed_total/60:.1f}m {eta_str}]{stuck_warn} [V6]')

                # ── Suspicious page: auto-retry with VL ─────
                if low_yield:
                    print(f'   [WARN] Low yield → auto-retry with VL')
                    out.write(f'> ⚠️ v6 low yield ({n_lines} lines, {len(txt)}c), auto-retrying with VL...\n\n')
                    out.flush()

                    try:
                        if vl_cached is None:
                            from paddleocr_vl_openvino.paddleocr_vl_pipeline import PaddleOCRVL
                            print(f'   [VL] Loading...', end='', flush=True)
                            t_vl = time.time()
                            vl_cached = PaddleOCRVL(
                                vlm_model_path=VLM_MODEL, layout_model_path=LAYOUT_MODEL,
                                vlm_device='CPU', layout_device='CPU', layout_precision='fp16',
                                vision_int8_quant=True, llm_int8_compress=True,
                            )
                            print(f' {time.time()-t_vl:.1f}s')
                        vl_result, vl_retry_n = _retry_predict(vl_cached, content, pg_num, total_pages, 'VL')
                        vl_cross_checks += 1
                        for vl_res in (vl_result if isinstance(vl_result, list) else [vl_result]):
                            vl_md = vl_res._to_markdown()
                            vl_txt = vl_md.get('markdown_texts', '') if isinstance(vl_md, dict) else ''
                            vl_chars = len(vl_txt)
                            if vl_chars > len(txt):
                                print(f'   [VL] Recovered {vl_chars}c (was {len(txt)}c), using VL result')
                                txt = vl_txt
                                n_lines = txt.count('\n') + 1
                                out.write(f'> ✅ VL recovered {vl_chars} chars\n\n')
                            else:
                                print(f'   [VL] No better ({vl_chars}c), keeping v6 result')
                            break
                    except Exception as e:
                        print(f'   [VL] Failed: {str(e)[:80]}')

            else:
                t0 = time.time()
                res, retry_n = _retry_predict(pipeline, content, pg_num, total_pages, 'VL')
                for r in (res if isinstance(res, list) else [res]):
                    md = r._to_markdown()
                    txt = md.get('markdown_texts', '') if isinstance(md, dict) else ''
                    n_lines = txt.count('\n') + 1 if txt else 0
                    grade = 'A' if len(txt) > 500 else ('B' if len(txt) > 100 else 'C')
                    elapsed = time.time() - t0
                    total_time += elapsed; total_chars += len(txt)
                    out.write(f'## Page {pg_num}\n\n{txt}\n\n---\n\n')
                    elapsed_total = time.time() - batch_start
                    eta = elapsed_total / n_processed * (total_pages - n_processed) if n_processed > 0 else 0
                    eta_str = f'ETA {eta/60:.0f}m' if eta > 60 else f'ETA {eta:.0f}s'
                    stuck_warn = ' [STUCK?]' if elapsed > 120 else ''
                    print(f'   P{pg_num}/{total_pages}: {elapsed:.1f}s, {len(txt)}c [{elapsed_total/60:.0f}m {eta_str}]{stuck_warn} [OCR]')
                    break

            # ── Collect quality data ───────────────────────────
            page_txt = txt if not is_text else content
            page_preview = page_txt[:200].replace('\n', ' ').replace('|', '/')
            quality_rows.append({
                'page': pg_num, 'chars': len(page_txt), 'lines': page_txt.count('\n') + 1,
                'grade': grade if not is_text else 'TXT',
                'avg_conf': avg_conf if not is_text and n_lines > 0 else None,
                'preview': page_preview
            })

            # ── Update checkpoint + progress after each page ─
            completed_pages.add(pg_num)
            n_processed += 1
            save_checkpoint(output_dir, stem, completed_pages, fp, total_pages)
            elapsed_total = time.time() - batch_start
            eta = elapsed_total / n_processed * (total_pages - n_processed) if n_processed > 0 else 0
            eta_str = f'{eta/60:.0f}min' if eta > 60 else f'{eta:.0f}s'
            progress = f'{n_processed}/{total_pages} pages ({100*n_processed/total_pages:.0f}%) | elapsed {elapsed_total/60:.0f}min | ETA {eta_str}'
            (output_dir / '.progress').write_text(progress, encoding='utf-8')
            out.flush()

    # ── Cleanup ────────────────────────────────────────────
    if cleanup_dir and os.path.exists(cleanup_dir):
        shutil.rmtree(cleanup_dir, ignore_errors=True)

    # Remove checkpoint + progress on full completion
    cp_file = output_dir / f'{stem}.checkpoint.json'
    pg_file = output_dir / '.progress'
    if cp_file.exists() and len(completed_pages) >= total_pages:
        cp_file.unlink()
    if pg_file.exists():
        pg_file.unlink()

    print(f'\n[OK] {n_processed} pages processed ({total_pages - len([p for p in pages if p[0] in completed_pages and p[0] not in set()])} total), {total_time:.1f}s OCR, {total_chars} chars')
    print(f'     → {md_file}')
    # ── Final summary ──────────────────────────────────────
    elapsed = time.time() - batch_start
    summary = [
        f'{"="*50}',
        f'OCR COMPLETE',
        f'  File:     {input_path.name}',
        f'  Pages:    {n_processed} processed in {elapsed/60:.1f}min ({elapsed/n_processed:.1f}s/pg avg)',
        f'  Engine:   {engine}',
        f'  Output:   {md_file}',
    ]
    if grade_counts['C'] > 0:
        summary.append(f'  Alerts:   {grade_counts["C"]} C-grade page(s)')
    if vl_loaded:
        summary.append(f'  VL used:  {vl_cross_checks} page(s) cross-verified')
    if verify:
        if b_pages_verify_candidate > 0:
            summary.append(f'  VL:       {vl_cross_checks} page(s) cross-verified')
        if b_pages_isolated_noise > 0:
            summary.append(f'  INFO:     {b_pages_isolated_noise} B page(s) with isolated marks (VL won\'t help)')
    summary.append(f'{"="*50}')
    summary_text = '\n'.join(summary)
    print(f'\n{summary_text}')

    (output_dir / '.progress').write_text(
        f'{n_processed}/{total_pages} pages DONE in {elapsed:.0f}s\n' + summary_text, encoding='utf-8')

    # ── Quality report ────────────────────────────────────
    if quality_rows:
        _generate_quality_report(md_file, quality_rows, total_pages)

    # ── Save to cache ──────────────────────────────────────
    save_cache(fp, md_file)

    # ── Fact summary (Safe-DOCX bridge) ────────────────────
    if summary:
        entities_path = output_dir / f'{stem}.entities.json'
        if not entities_path.exists():
            entities_path = None
        _generate_fact_summary(md_file, entities_path)

    # ── Entity extraction ──────────────────────────────────
    if extract:
        try:
            from extract_legal_entities import extract as extract_entities
            md_text = md_file.read_text(encoding='utf-8')
            entities = extract_entities(md_text)
            entities_path = output_dir / f'{stem}.entities.json'
            entities_path.write_text(json.dumps(entities, ensure_ascii=False, indent=2),
                                     encoding='utf-8')
            print(f'     → {entities_path} [{entities["doc_type"]}]')
        except Exception as e:
            print(f'     [EXTRACT] Failed: {e}')

    return md_file


# ── Quality Report ─────────────────────────────────────────────
def _generate_quality_report(md_file: Path, quality_rows: list, total_pages: int):
    """Generate a per-page quality overview for quick assessment."""
    lines = []
    lines.append(f'# OCR Quality Report: {md_file.stem}\n')
    lines.append(f'**Total pages**: {total_pages} | **Processed**: {len(quality_rows)}\n')

    # Summary stats
    grades = [r['grade'] for r in quality_rows]
    a_count = grades.count('A'); b_count = grades.count('B')
    c_count = grades.count('C'); txt_count = grades.count('TXT')
    total_c = sum(r['chars'] for r in quality_rows)
    lines.append(f'**Grades**: {a_count}A / {b_count}B / {c_count}C / {txt_count}TXT | **Total chars**: {total_c:,}\n')
    lines.append('')

    # Quality gate: flag problematic pages
    bad_pages = [r for r in quality_rows if r['grade'] in ('C',) and r['chars'] < 100]
    low_pages = [r for r in quality_rows if r['grade'] == 'C' and r['chars'] >= 100]
    if bad_pages:
        lines.append('## 🔴 Needs re-OCR (very low yield)\n')
        for r in bad_pages:
            lines.append(f'- Page {r["page"]}: {r["chars"]}c, {r["lines"]} lines — `{r["preview"][:80]}...`')
        lines.append('')
    if low_pages:
        lines.append('## 🟡 Low confidence — review recommended\n')
        for r in low_pages:
            conf_str = f', avg conf {r["avg_conf"]:.2f}' if r.get('avg_conf') else ''
            lines.append(f'- Page {r["page"]}: {r["chars"]}c, {r["lines"]} lines{conf_str} — `{r["preview"][:80]}...`')
        lines.append('')

    # Full page table
    lines.append('## Page Details\n')
    lines.append('| Page | Chars | Lines | Grade | Avg Conf | Preview (first 100 chars) |')
    lines.append('|------|-------|-------|-------|----------|---------------------------|')
    for r in quality_rows:
        conf = f'{r["avg_conf"]:.2f}' if r.get('avg_conf') else '-'
        pv = r['preview'][:100].replace('|', '/')
        flag = ' 🔴' if r['grade'] == 'C' and r['chars'] < 100 else (' 🟡' if r['grade'] == 'C' else '')
        lines.append(f'| {r["page"]}{flag} | {r["chars"]} | {r["lines"]} | {r["grade"]} | {conf} | {pv} |')

    qpath = md_file.with_name(f'{md_file.stem}_quality.md')
    qpath.write_text('\n'.join(lines), encoding='utf-8')
    print(f'     → {qpath}')


# ── Fact Summary (Safe-DOCX bridge) ───────────────────────────
def _generate_fact_summary(md_file: Path, entities_path: Path | None = None):
    """Generate a structured fact overview from OCR output — designed for
    Claude Code / safe-docx consumption. Produces _facts.md alongside the OCR output."""
    text = md_file.read_text(encoding='utf-8')

    lines = []
    lines.append(f'# 事实摘要：{md_file.stem}\n')
    lines.append('> 以下摘要由 OCR 管线自动生成，供法律文书起草时快速引用。')
    lines.append('> 精确引用请回溯原始 OCR 输出或源 PDF。\n')

    # ── Entities (if available) ──────────────────────────────
    if entities_path:
        try:
            ent = json.loads(entities_path.read_text(encoding='utf-8'))
            fields = ent.get('fields', {})

            # Parties
            parties = fields.get('当事人', {})
            if parties:
                lines.append('## 当事人\n')
                for role, names in parties.items():
                    for n in names[:3]:
                        lines.append(f'- **{role}**：{n}')
                lines.append('')

            # Amounts
            amounts = fields.get('金额', [])
            if amounts:
                lines.append('## 涉及金额\n')
                for a in amounts[:10]:
                    lines.append(f'- {a}')
                lines.append('')

            # Dates
            dates = fields.get('日期', [])
            if dates:
                lines.append('## 关键日期\n')
                for d in dates[:10]:
                    lines.append(f'- {d}')
                lines.append('')

            # Case numbers
            case_nos = fields.get('案号', [])
            if case_nos:
                lines.append('## 案号\n')
                for c in case_nos:
                    lines.append(f'- {c}')
                lines.append('')

            # ID numbers
            id_nos = fields.get('身份证号', []) or fields.get('统一社会信用代码', [])
            if id_nos:
                lines.append('## 证件号/信用代码\n')
                for i in id_nos:
                    lines.append(f'- {i}')
                lines.append('')

            # Courts
            courts = fields.get('法院', [])
            if courts:
                lines.append('## 管辖法院\n')
                for c in courts:
                    lines.append(f'- {c}')
                lines.append('')

            # Doc type
            dtype = ent.get('doc_type', '')
            if dtype:
                lines.insert(2, f'**文档类型**: {dtype}\n')
        except Exception:
            pass  # Degrade gracefully if entities.json is malformed

    # ── Key clauses / numbered items (heuristic) ──────────────
    import re
    lines.append('## 关键条款 / 编号事项\n')
    # Find "第X条", "第X款", numbered items, etc.
    clause_patterns = [
        (r'第[一二三四五六七八九十百千\d]+条\s*[^\n]{0,100}', '条款'),
        (r'\d+[\.\、\)）]\s*[^\n]{0,100}', '编号项'),
        (r'[\(（]\s*[一二三四五六七八九十\d]\s*[\)）]\s*[^\n]{0,100}', '编号项'),
    ]
    found = set()
    for pat, label in clause_patterns:
        matches = re.findall(pat, text)
        for m in matches[:15]:
            m_clean = m.strip()[:120]
            if m_clean not in found:
                found.add(m_clean)
                lines.append(f'- {m_clean}')
    if not found:
        lines.append('_(未检测到编号条款)_')
    lines.append('')

    fpath = md_file.with_name(f'{md_file.stem}_facts.md')
    fpath.write_text('\n'.join(lines), encoding='utf-8')
    print(f'     → {fpath}')


# ── Batch Summary ─────────────────────────────────────────────
def _generate_summary(output_dir: Path, results: list):
    """Generate a human-readable summary of all extracted entities."""
    lines = []
    lines.append('# Batch OCR Summary\n')
    warnings = []

    for r in results:
        if r['status'] != 'ok':
            lines.append(f'- **{Path(r["file"]).name}**: ❌ ERROR - {r.get("error", "unknown")}')
            warnings.append(f'❌ {Path(r["file"]).name}: processing failed')
            continue

        fname = Path(r['file']).name
        stem = Path(r['file']).stem
        ent_path = output_dir / f'{stem}' / f'{stem}.entities.json'
        if not ent_path.exists():
            ent_path = output_dir / f'{stem}.entities.json'  # single-file output

        if not ent_path.exists():
            lines.append(f'- **{fname}**: no entities extracted')
            continue

        try:
            ent = json.loads(ent_path.read_text(encoding='utf-8'))
        except:
            lines.append(f'- **{fname}**: failed to read entities')
            continue

        dtype = ent.get('doc_type', '?')
        fields = ent.get('fields', {})
        parties = fields.get('当事人', {})

        # Build one-line summary
        parts = [f'{dtype}']

        # Parties
        party_strs = []
        for role in ['原告', '被告', '甲方', '乙方', '丙方', '申请人', '被申请人']:
            names = parties.get(role, [])
            if names:
                party_strs.append(f'{role}={names[0]}')
        if party_strs:
            parts.append(', '.join(party_strs))

        # Key fields
        for key, label in [('案号', '案号'), ('身份证号', '身份证'), ('金额', '金额'),
                           ('合同编号', '合同号'), ('法院', '法院')]:
            vals = fields.get(key, [])
            if vals:
                parts.append(f'{label}={vals[0]}')

        lines.append(f'- **{fname}**: {" | ".join(parts)}')

        # Missing critical fields
        if dtype == '合同' and '当事人' not in fields:
            warnings.append(f'⚠️ {fname}: 合同缺当事人')
        if dtype == '判决书' and '案号' not in fields:
            warnings.append(f'⚠️ {fname}: 判决书缺案号')
        if dtype in ('身份证', '征信报告') and '身份证号' not in fields:
            warnings.append(f'⚠️ {fname}: 证件缺身份证号')

    # Warnings section
    if warnings:
        lines.append('\n## ⚠️ Warnings\n')
        for w in warnings:
            lines.append(f'- {w}')

    summary_path = output_dir / '_summary.md'
    summary_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f'     → {summary_path}')
    if warnings:
        for w in warnings:
            print(f'   {w}')


# ── Batch mode ───────────────────────────────────────────────
def process_batch(folder: Path, output_dir: Path, preprocess: bool = False,
                  force: bool = False, engine: str = 'v6', extract: bool = False,
                  verify: bool = True, summary: bool = False):
    """Process all PDFs and images in a folder recursively."""
    exts = {'.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}
    files = sorted([f for f in folder.rglob('*') if f.suffix.lower() in exts])
    if not files:
        print(f'[BATCH] No supported files found in {folder}')
        return

    print(f'[BATCH] Found {len(files)} file(s) in {folder}')
    results = []
    for i, f in enumerate(files, 1):
        print(f'\n{"="*60}')
        print(f'[{i}/{len(files)}] {f.name}')
        print(f'{"="*60}')
        try:
            md = process_single(f, output_dir / f.stem, preprocess=preprocess,
                                     force=force, engine=engine, extract=extract,
                                     verify=verify, summary=summary)
            results.append({'file': str(f), 'output': str(md), 'status': 'ok'})
        except Exception as e:
            print(f'[ERROR] {f.name}: {e}')
            results.append({'file': str(f), 'output': None, 'status': 'error', 'error': str(e)})

    # Write batch index
    index_path = output_dir / '_batch_index.json'
    index_path.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    ok = sum(1 for r in results if r['status'] == 'ok')
    err = len(results) - ok
    print(f'\n[BATCH DONE] {ok} ok, {err} errors → {index_path}')

    # Generate summary if extract was used
    if extract:
        _generate_summary(output_dir, results)


# ── CLI ──────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description='PaddleOCR-VL-1.6 Local OCR v2',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ocr_contract.py evidence.pdf
  python ocr_contract.py evidence.pdf D:\\output\\
  python ocr_contract.py evidence.pdf --preprocess
  python ocr_contract.py --batch D:\\cases\\ D:\\output\\
  python ocr_contract.py evidence.pdf --force
  python ocr_contract.py --list-cache
  python ocr_contract.py --clear-cache
        """)
    parser.add_argument('input', nargs='?', help='PDF or image file path')
    parser.add_argument('output_dir', nargs='?', default=r'D:\ai-models\output',
                        help=r'Output directory (default: D:\ai-models\output)')
    parser.add_argument('--preprocess', '-p', action='store_true',
                        help='Apply deskew + contrast enhancement for poor scans')
    parser.add_argument('--pages', metavar='RANGE',
                        help='Page range to process, e.g. "16-30" (1-based inclusive)')
    parser.add_argument('--extract', '-x', action='store_true',
                        help='Extract legal entities from OCR output (saves .entities.json)')
    parser.add_argument('--verify', action='store_true', default=True,
                        help='Cross-verify B-grade pages with >3 low-conf lines (default: on)')
    parser.add_argument('--no-verify', action='store_false', dest='verify',
                        help='Disable VL cross-verification')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Suppress per-page output, print only final summary')
    parser.add_argument('--engine', '-e', choices=['v6', 'vl'], default='v6',
                        help='OCR engine: v6 (PP-OCRv6 GPU ~2.8s/p default), vl (PaddleOCR-VL ~20s/p, complex layouts)')
    parser.add_argument('--force', '-f', action='store_true',
                        help='Force re-OCR, ignore cache and checkpoint')
    parser.add_argument('--batch', '-b', metavar='FOLDER',
                        help='Batch process all PDFs/images in folder recursively')
    parser.add_argument('--list-cache', action='store_true',
                        help='List cached OCR results')
    parser.add_argument('--clear-cache', action='store_true',
                        help='Clear all cached results')
    parser.add_argument('--summary', '-s', action='store_true',
                        help='Generate _facts.md summary (structured facts for safe-docx drafting)')
    args = parser.parse_args()

    # ── Cleanup stale tmp + cache on every run ────────────
    cleanup_stale_tmp()
    _cleanup_stale_cache()

    # ── Cache management ──────────────────────────────────
    if args.list_cache:
        entries = list_cache()
        if not entries:
            print('[CACHE] No cached entries')
        else:
            print(f'[CACHE] {len(entries)} entries:')
            for e in entries:
                print(f'  {e["fingerprint"][:12]}…  {e["cached_at"][:19]}  {e["source_md"]}')
        return

    if args.clear_cache:
        count = 0
        for f in CACHE_DIR.iterdir():
            f.unlink()
            count += 1
        print(f'[CACHE] Cleared {count} files')
        return

    # ── Batch mode ────────────────────────────────────────
    if args.batch:
        # In batch mode, the first positional arg (args.input) is the output dir
        out_dir = Path(args.input) if args.input else Path(args.output_dir)
        process_batch(Path(args.batch), out_dir,
                      preprocess=args.preprocess, force=args.force,
                      engine=args.engine, extract=args.extract,
                      verify=args.verify, summary=args.summary)
        return

    # ── Single file mode ──────────────────────────────────
    if not args.input:
        parser.print_help()
        sys.exit(1)

    input_path = resolve_path(args.input)
    output_dir = Path(args.output_dir)

    # Parse page range
    page_range = None
    if args.pages:
        parts = args.pages.split('-')
        if len(parts) != 2:
            print(f'[ERROR] --pages must be "START-END", got "{args.pages}"')
            sys.exit(1)
        try:
            page_range = (int(parts[0]), int(parts[1]))
        except ValueError:
            print(f'[ERROR] Invalid page range: "{args.pages}"')
            sys.exit(1)

    process_single(input_path, output_dir, preprocess=args.preprocess,
                   force=args.force, page_range=page_range, engine=args.engine,
                   extract=args.extract, verify=args.verify, summary=args.summary)


if __name__ == '__main__':
    main()
