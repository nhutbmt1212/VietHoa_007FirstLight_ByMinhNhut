@echo off
setlocal
title Ollama gemma3:12b

set OLLAMA=C:\Users\nhutb\AppData\Local\Programs\ollama\ollama.exe
set OLLAMA_MAX_LOADED_MODELS=1
set OLLAMA_NUM_PARALLEL=1
set OLLAMA_FLASH_ATTENTION=1
set OLLAMA_KV_CACHE_TYPE=q8_0

rem ── Tat Ollama cu neu dang chay ──────────────────────────────
taskkill /IM ollama.exe /F 2>nul
timeout /t 2 /nobreak >nul

rem ── Khoi dong Ollama serve trong nen ─────────────────────────
start "" "%OLLAMA%" serve
timeout /t 3 /nobreak >nul

rem ── Pre-load model vao VRAM ──────────────────────────────────
"%OLLAMA%" run gemma3:12b "" 2>nul

cls
echo ============================================================
echo  Ollama gemma3:12b - READY
echo  Flash Attention: ON  ^|  KV Cache: q8_0  ^|  GPU: max
echo ============================================================
echo.
echo  [C] Tat Ollama hoan toan
echo  [X] Dong cua so (Ollama van chay nen)
echo.
choice /C:CX /N /M "  Chon: "

if %ERRORLEVEL%==1 (
    echo.
    echo Dang tat Ollama...
    taskkill /IM ollama.exe /F 2>nul
    taskkill /IM ollama_llama_server.exe /F 2>nul
    echo Ollama da tat.
    timeout /t 1 /nobreak >nul
)
exit /b
