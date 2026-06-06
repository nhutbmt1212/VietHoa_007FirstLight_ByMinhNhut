@echo off
setlocal
title 007 First Light - Viet Hoa Toan Bo

REM ============================================================
REM  CAU HINH - Chi can sua 2 dong nay khi cai lai game
REM ============================================================
set GAME_DIR=d:\Games\007 First Light
set VIET_HOA_DIR=D:\VietHoa_007FirstLight
REM ============================================================

set PYTHON=C:\Users\nhutb\AppData\Local\Programs\Python\Python312\python.exe
set TOOLKIT=%VIET_HOA_DIR%\007-firstlight-toolkit-main
set PYTHONIOENCODING=utf-8

echo ============================================================
echo  007 First Light - INJECT DICH + FONT
echo  Thu tu: 1) Translation  2) Font
echo  Restore: chay restore_original.bat
echo ============================================================
echo.

REM ── BUOC 1: Inject ban dich ──────────────────────────────────────
echo [BUOC 1/2] Inject ban dich tieng Viet...
cd /d "%TOOLKIT%"
"%PYTHON%" tools\install_translation.py --config examples\vietnamese\translation_config.json --game-dir "%GAME_DIR%"
if %ERRORLEVEL% NEQ 0 (
    echo [LOI] Inject translation that bai!
    pause & exit /b 1
)

REM ── BUOC 2: Inject font ──────────────────────────────────────────
echo.
echo [BUOC 2/2] Inject font tieng Viet co dau...
"%PYTHON%" tools\install_font.py --config examples\vietnamese\font_config.json --game-dir "%GAME_DIR%"
if %ERRORLEVEL% NEQ 0 (
    echo [LOI] Inject font that bai!
    pause & exit /b 1
)

echo.
echo ============================================================
echo  XONG! Mo game len kiem tra.
echo ============================================================
pause
