"""OCR progress watcher — extracted from ocr.bat inline code.
Usage: python ocr_watch.py [--batch] [output_dir]
"""
import json
import os
import sys
import time


def watch_batch(out: str):
    print('Batch OCR Watch')
    print('=' * 50)
    idx_path = os.path.join(out, '_batch_index.json')
    while True:
        if not os.path.exists(idx_path):
            print('Waiting for batch to start...')
            time.sleep(10)
            continue
        idx = json.load(open(idx_path, encoding='utf-8'))
        done = sum(1 for r in idx if r['status'] == 'ok')
        err = sum(1 for r in idx if r['status'] == 'error')
        total = len(idx)
        print(f'\nFiles: {done} ok / {err} err / {total} total ({100 * done / total:.0f}%)')
        for r in idx:
            name = os.path.basename(r['file'])[:40]
            if r['status'] == 'ok':
                print(f'  [OK] {name}')
            elif r['status'] == 'error':
                print(f'  [ERR] {name} - {str(r.get("error", "?"))[:60]}')
            else:
                stem = os.path.splitext(r['file'])[0]
                pg = os.path.join(out, os.path.basename(stem), '.progress')
                if os.path.exists(pg):
                    p = open(pg, encoding='utf-8').read().strip().split('\n')[0]
                    print(f'  [...] {name} - {p}')
                else:
                    print(f'  [...] {name}')
        if done + err >= total:
            print('\n=== BATCH DONE ===')
            break
        time.sleep(15)


def watch_single(out: str):
    cps = [f for f in os.listdir(out) if f.endswith('.checkpoint.json')]
    if not cps:
        print('No checkpoint found - nothing to watch.')
        return
    cp = max(cps, key=lambda x: os.path.getmtime(os.path.join(out, x)))
    print('Watching OCR progress...')
    print(f'File: {cp.replace(".checkpoint.json", "")}')
    while True:
        try:
            d = json.load(open(os.path.join(out, cp), encoding='utf-8'))
            done = len(d['completed_pages'])
            total = d['total_pages']
            eta = ''
            pgf = os.path.join(out, '.progress')
            if os.path.exists(pgf):
                pg = open(pgf, encoding='utf-8').read().strip().split('\n')[0]
                eta = f' - {pg}'
            print(f'  [{done}/{total}] {100 * done / total:.0f}%{eta}')
            if done >= total:
                print('  DONE!')
                break
        except Exception:
            pass
        time.sleep(10)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:]]
    batch = '--batch' in args
    dirs = [a for a in args if a != '--batch']
    out = dirs[0] if dirs else r'D:\ai-models\output'
    if batch:
        watch_batch(out)
    else:
        watch_single(out)
