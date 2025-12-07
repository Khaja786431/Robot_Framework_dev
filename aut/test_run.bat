@echo off
REM Get timestamp in format YYYY-MM-DD_HH-MM-SS
for /f "tokens=1-5 delims=:/ " %%d in ("%date% %time%") do (
    set timestamp=%%d-%%e-%%f_%%g-%%h-%%i
)

REM Create Logs folder if it doesn't exist
if not exist Logs mkdir Logs

REM Run Robot Framework with timestamped output directory
robot --outputdir Logs\Report_%timestamp% TestSuite

echo Execution completed!
pause
exit
