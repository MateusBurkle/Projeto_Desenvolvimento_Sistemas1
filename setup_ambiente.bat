@echo off
REM Cria o ambiente virtual do back-end e instala as dependencias (rodar uma vez, na pasta CRUD_LEAF_TI)
cd /d "%~dp0backend"
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo Ambiente pronto. Para ativar depois: backend\.venv\Scripts\activate
pause
