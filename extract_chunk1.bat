@echo off
setlocal
title Extract chunk1 - Chi doc, khong sua game

set PYTHON=C:\Users\nhutb\AppData\Local\Programs\Python\Python312\python.exe
set GAME_DIR=d:\Games\007 First Light
set TOOLKIT=D:\VietHoa_007FirstLight\007-firstlight-toolkit-main
set OUT=D:\VietHoa_007FirstLight\localization\extracted_chunk1
set PYTHONIOENCODING=utf-8

echo ============================================================
echo  EXTRACT CHUNK1 - Chi doc, khong ghi gi vao game
echo  Output: %OUT%
echo ============================================================
echo.

cd /d "%TOOLKIT%"

"%PYTHON%" tools\extract_text.py ^
    --chunks "D:\Runtime007\Runtime\chunk1.rpkg" ^
    --out "%OUT%"

if %ERRORLEVEL% NEQ 0 (
    echo [LOI] Extract that bai!
    pause & exit /b 1
)

echo.
echo ============================================================
echo  XONG! File da luu tai:
echo  %OUT%\ui.json
echo  %OUT%\dialogue.json
echo  Mo file de xem manh moi chua duoc viet hoa.
echo ============================================================
pause
