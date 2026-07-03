@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo === Первая настройка бота ===
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo Python не найден.
    echo Скачайте и установите Python с https://www.python.org/downloads/
    echo При установке поставьте галочку "Add Python to PATH".
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Создаю виртуальное окружение...
    python -m venv .venv
)

echo Устанавливаю зависимости...
call .venv\Scripts\activate.bat
pip install -r requirements.txt

if not exist ".env" (
    copy .env.example .env >nul
    echo.
    echo Создан файл .env
    echo Откройте его и впишите BOT_TOKEN и ADMIN_IDS.
    echo Файл: %cd%\.env
    notepad .env
) else (
    echo Файл .env уже есть.
)

if not exist "products\planner_2026.pdf" (
    echo Создаю примеры PDF...
    python create_samples.py
)

echo.
echo === Готово ===
echo 1. Убедитесь, что в .env указан токен бота
echo 2. Запустите start.bat
echo.
pause
