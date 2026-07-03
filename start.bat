@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv" (
    echo Сначала запустите setup.bat
    pause
    exit /b 1
)

if not exist ".env" (
    echo Файл .env не найден. Запустите setup.bat
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
echo Бот запускается... Не закрывайте это окно.
echo Остановить: Ctrl+C
echo.
python bot.py
pause
