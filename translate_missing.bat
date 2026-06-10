@echo off
setlocal
title 007 First Light - Dich (Resume Missing)

set PYTHON=C:\Users\nhutb\AppData\Local\Programs\Python\Python312\python.exe
set LOC=D:\VietHoa_007FirstLight\localization
set PYTHONIOENCODING=utf-8

cls
echo ============================================================
echo  RESUME - Dich tiep nhung cau Tieng Anh con sot lai o 2 file
echo ============================================================
echo.

set START_TIME=%TIME%
echo [START] %DATE% %TIME%
echo.

echo [1/2] DICH DIALOGUE (resume)...
"%PYTHON%" "%LOC%\translate_dialogue_v3.py"
if %ERRORLEVEL% NEQ 0 (
    echo [LOI] Dialogue that bai!
    pause & exit /b 1
)
echo [OK] Dialogue xong luc %TIME%
echo.

echo [2/2] DICH UI (resume)...
"%PYTHON%" "%LOC%\translate_ui_v2.py" --resume
if %ERRORLEVEL% NEQ 0 (
    echo [LOI] UI that bai!
    pause & exit /b 1
)
echo [OK] UI xong luc %TIME%
echo.

echo [POST] Dang chay cac script chinh sua loi sau dich...
"%PYTHON%" "%LOC%\fix_rogue_tags.py"
"%PYTHON%" "%LOC%\sync_tags_from_eng.py"
"%PYTHON%" "%LOC%\fix_translation_issues.py"

echo.
echo ============================================================
echo  HOAN TAT!  Bat dau: %START_TIME%  ^|  Ket thuc: %TIME%
echo  Hay chay inject_all.bat de dua file da dich vao game.
echo ============================================================
pause
