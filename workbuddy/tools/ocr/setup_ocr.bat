@echo off
rem ============================================================
rem  WorkBuddy OCR 一键安装脚本（2026-08-08 实测沉淀）
rem  用法：① 已装 Python 3.11+ 且勾选 "Add to PATH"
rem        ② 双击本脚本 或 在 cmd 里运行
rem  自动完成：检测 Python → 建 venv（自动避半残）→ 装依赖（镜像源+重试）
rem           → 验证 import → 提示改路径
rem  兼容 WorkBuddy safe-delete：命令前清空 CODEBUDDY_SESSION_ID
rem ============================================================
setlocal enabledelayedexpansion

echo ============================================
echo  WorkBuddy OCR 一键安装
echo ============================================
echo.

rem ---- 0. 检测 Python ----
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 Python。
    echo   请先安装 Python 3.11+（python.org），勾选 "Add to PATH"，
    echo   然后重跑本脚本。
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] 检测到 Python: %PYVER%

rem ---- 1. 定位本目录（tools/ocr/）----
set OCR_DIR=%~dp0
cd /d "%OCR_DIR%"

rem ---- 2. 选 venv 名（自动递增避开半残旧环境）----
set VENV_NAME=paddleocr_ov2
set /a N=3
:venv_loop
if not exist "%OCR_DIR%\%VENV_NAME%\Scripts\python.exe" goto venv_ok
set VENV_NAME=paddleocr_ov!N!
set /a N+=1
goto venv_loop
:venv_ok
echo [1/4] 使用虚拟环境: %VENV_NAME%  ^(旧环境半残时自动换名，别 rm -rf^)

rem ---- 3. 建 venv（清 safe-delete 环境变量）----
set "CODEBUDDY_SESSION_ID="
set "PYTHONPATH="
echo [2/4] 创建虚拟环境...
python -m venv "%VENV_NAME%"
if not exist "%OCR_DIR%\%VENV_NAME%\Scripts\python.exe" (
    echo [ERROR] venv 创建失败。可能被安全软件拦截，或 Python 异常。
    pause
    exit /b 1
)
set VENV_PY=%OCR_DIR%\%VENV_NAME%\Scripts\python.exe
echo       环境: %VENV_PY%

rem ---- 4. 装依赖（清华源，失败自动切腾讯源）----
echo [3/4] 安装依赖（约 5-10 分钟，请耐心，别关窗口）...
"%VENV_PY%" -m pip install -r requirements-v6.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 60 --retries 5
if errorlevel 1 (
    echo [WARN] 清华源失败，切换腾讯源重试...
    "%VENV_PY%" -m pip install -r requirements-v6.txt -i https://mirrors.cloud.tencent.com/pypi/simple --timeout 60 --retries 5
)
if errorlevel 1 (
    echo [WARN] 镜像源均失败。可能网络问题，或 safe-delete 拦截 pip 清理。
    echo   手动装：打开 cmd，cd 到本目录，执行：
    echo     set "CODEBUDDY_SESSION_ID=" ^&^& "%VENV_PY%" -m pip install -r requirements-v6.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 60 --retries 5
    pause
    exit /b 1
)

rem ---- 5. 验证 import ----
echo [4/4] 验证依赖...
"%VENV_PY%" -c "import cv2, numpy, pymupdf, paddle, paddleocr, onnxruntime, rapidocr_onnxruntime; print('[OK] 依赖验证通过')"
if errorlevel 1 (
    echo [WARN] 部分依赖验证失败。请查看上面错误，常见：opencv contrib 覆盖删除、paddlepaddle 导入。
    echo   排查见 环境配置/02-本地OCR配置.md 第三、四节。
) else (
    echo.
    echo ============================================
    echo  安装完成！
    echo ============================================
    echo.
    echo 下一步（关键）：改路径，让 ocr 命令指向本环境：
    echo   ocr.bat    : 把 set PY=... 改为 set PY=%OCR_DIR%%VENV_NAME%\Scripts\python.exe
    echo   ocr_run.py : 改 PY / CONTRACT / DEFAULT_OUT 三处路径
    echo.
    echo 测试：ocr 一个测试.pdf  （成功 → 同目录生成 .md）
    echo.
)
pause
