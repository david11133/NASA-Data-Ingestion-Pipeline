@echo off
setlocal

REM Install requirements if the requirements.txt file exists
if exist "C:\opt\airflow\requirements.txt" (
    python -m pip install --upgrade pip
    pip install --user -r C:\opt\airflow\requirements.txt
)

REM Initialize the Airflow database if it doesn't exist
if not exist "C:\opt\airflow\airflow.db" (
    airflow db init
    airflow users create --username admin --firstname admin --lastname admin --role Admin --email admin@example.com --password admin
)

REM Upgrade the database schema
airflow db upgrade

REM Start the Airflow web server and scheduler
start airflow webserver
start airflow scheduler

endlocal
