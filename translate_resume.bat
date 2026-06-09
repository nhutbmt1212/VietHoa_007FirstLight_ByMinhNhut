@echo off
setlocal
title 007 First Light - Dich (Resume)

set PYTHON=C:\Users\nhutb\AppData\Local\Programs\Python\Python312\python.exe
set OLLAMA=C:\Users\nhutb\AppData\Local\Programs\ollama\ollama.exe
set LOC=D:\VietHoa_007FirstLight\localization
set PYTHONIOENCODING=utf-8
set OLLAMA_MAX_LOADED_MODELS=1
set OLLAMA_NUM_PARALLEL=1
set OLLAMA_FLASH_ATTENTION=1
set OLLAMA_KV_CACHE_TYPE=q8_0

cls
echo ============================================================
echo  RESUME - Tiep tuc dich Dialogue tu cho da dung
echo ============================================================
echo.

echo [INIT] Khoi dong Ollama...
taskkill /IM ollama.exe /F 2>nul
taskkill /IM ollama_llama_server.exe /F 2>nul
timeout /t 2 /nobreak >nul
start "" "%OLLAMA%" serve
timeout /t 4 /nobreak >nul
"%OLLAMA%" run gemma3:12b "" 2>nul
echo [OK] Model san sang.
echo.

set START_TIME=%TIME%
echo [START] %DATE% %TIME%
echo.

echo [1/1] DICH DIALOGUE (resume)...
"%PYTHON%" "%LOC%\translate_dialogue_v3.py"
if %ERRORLEVEL% NEQ 0 (
    echo [LOI] Dialogue that bai!
    pause & exit /b 1
)
echo [OK] Dialogue xong luc %TIME%
echo.

echo [POST] fix_rogue_tags...
"%PYTHON%" "%LOC%\fix_rogue_tags.py"
echo [POST] sync_tags_from_eng...
"%PYTHON%" "%LOC%\sync_tags_from_eng.py"
echo [POST] fix_translation_issues...
"%PYTHON%" "%LOC%\fix_translation_issues.py"

echo.
echo ============================================================
echo  XONG!  Bat dau: %START_TIME%  ^|  Ket thuc: %TIME%
echo  Chay inject_all.bat de dua vao game.
echo ============================================================
pause
