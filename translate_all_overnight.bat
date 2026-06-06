@echo off
setlocal
title 007 First Light - Dich Toan Bo (Qua Dem)

set PYTHON=C:\Users\nhutb\AppData\Local\Programs\Python\Python312\python.exe
set OLLAMA=C:\Users\nhutb\AppData\Local\Programs\ollama\ollama.exe
set LOC=D:\VietHoa_007FirstLight\localization
set PYTHONIOENCODING=utf-8

rem ── Env Ollama toi uu GPU ─────────────────────────────────────
set OLLAMA_MAX_LOADED_MODELS=1
set OLLAMA_NUM_PARALLEL=1
set OLLAMA_FLASH_ATTENTION=1
set OLLAMA_KV_CACHE_TYPE=q8_0

cls
echo ============================================================
echo  007 First Light - DICH TOAN BO QUA DEM
echo  UI + Dialogue  ^|  gemma3:12b  ^|  GPU max
echo ============================================================
echo.

rem ── Tat Ollama cu, khoi dong lai voi env moi ─────────────────
echo [INIT] Khoi dong Ollama...
taskkill /IM ollama.exe /F 2>nul
taskkill /IM ollama_llama_server.exe /F 2>nul
timeout /t 2 /nobreak >nul
start "" "%OLLAMA%" serve
timeout /t 4 /nobreak >nul

rem ── Pre-load model vao VRAM ngay ─────────────────────────────
echo [INIT] Load gemma3:12b vao VRAM...
"%OLLAMA%" run gemma3:12b "" 2>nul
echo [OK] Model san sang.
echo.

rem ── Ghi thoi gian bat dau ────────────────────────────────────
set START_TIME=%TIME%
echo [START] %DATE% %TIME%
echo.

rem ══════════════════════════════════════════════════════════════
echo [1/2] DICH DIALOGUE...
echo ──────────────────────────────────────────────────────────
"%PYTHON%" "%LOC%\translate_dialogue_v3.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [LOI] Dich dialogue that bai! Ma loi: %ERRORLEVEL%
    echo Chay lai voi --resume de tiep tuc tu cho bi dung.
    pause & exit /b 1
)
echo.
echo [OK] Dialogue xong luc %TIME%
echo.

rem ══════════════════════════════════════════════════════════════
echo [2/2] DICH UI...
echo ──────────────────────────────────────────────────────────
"%PYTHON%" "%LOC%\translate_ui_v2.py"
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [LOI] Dich UI that bai! Ma loi: %ERRORLEVEL%
    echo Kiem tra log roi chay lai.
    pause & exit /b 1
)
echo.
echo [OK] UI xong luc %TIME%
echo.

rem ── Post-process: fix tag + spacing ──────────────────────────
echo [POST] Chay fix_rogue_tags.py...
"%PYTHON%" "%LOC%\fix_rogue_tags.py"

echo [POST] Chay sync_tags_from_eng.py...
"%PYTHON%" "%LOC%\sync_tags_from_eng.py"

echo [POST] Chay fix_translation_issues.py...
"%PYTHON%" "%LOC%\fix_translation_issues.py"

echo.
echo ============================================================
echo  HOAN TAT!
echo  Bat dau : %START_TIME%
echo  Ket thuc: %TIME%
echo.
echo  Buoc tiep: chay inject_all.bat de dua vao game.
echo ============================================================
echo.
pause
