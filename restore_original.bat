@echo off
setlocal
title 007 First Light - Khoi Phuc Game Goc

REM ============================================================
REM  CAU HINH - Chi sua 2 dong nay khi cai lai game
REM ============================================================
set GAME_DIR=d:\Games\007 First Light
set VIET_HOA_DIR=D:\VietHoa_007FirstLight
REM ============================================================

set PYTHON=C:\Users\nhutb\AppData\Local\Programs\Python\Python312\python.exe
set TOOLKIT=%VIET_HOA_DIR%\007-firstlight-toolkit-main
set PYTHONIOENCODING=utf-8

echo ============================================================
echo  007 First Light - KHOI PHUC VE GAME GOC
echo  Luong: inject lai ban tieng Anh goc + restore font goc
echo ============================================================
echo.

cd /d "%TOOLKIT%"

REM ── BUOC 1: Inject lai ban tieng Anh goc vao tat ca chunks ───────
echo [BUOC 1/2] Inject lai ban tieng Anh goc...
echo  (su dung localization\extracted - cung luong voi ban Viet)
echo.
"%PYTHON%" tools\install_translation.py ^
    --config examples\vietnamese\translation_config_english.json ^
    --game-dir "%GAME_DIR%"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [LOI] Inject tieng Anh that bai! Ma loi: %ERRORLEVEL%
    pause & exit /b 1
)

echo.

REM ── BUOC 2: Restore font goc tu original_font.GFXF ───────────────
echo [BUOC 2/2] Restore font goc...
echo  (inject original_font.GFXF da backup tu lan install dau tien)
echo.
"%PYTHON%" "%VIET_HOA_DIR%\restore_font_original.py" --game-dir "%GAME_DIR%"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [LOI] Restore font that bai! Ma loi: %ERRORLEVEL%
    echo [INFO] Neu chua tung inject font, font van la ban goc - OK.
    REM Khong exit loi vi co the chua tung inject font bao gio
)

echo.
echo ============================================================
echo  XONG! Game da ve trang thai tieng Anh goc.
echo.
echo  Ban co the:
echo   - Chay inject_all.bat de cai lai tieng Viet
echo   - Mo game luon de choi ban goc
echo ============================================================
pause
exit /b 0
