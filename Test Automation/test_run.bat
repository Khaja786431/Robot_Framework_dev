@echo off
set PYTHONPATH=%CD%

for /f "tokens=1-5 delims=:/ " %%d in ("%date% %time%") do (
    set timestamp=%%d-%%e-%%f_%%g-%%h-%%i
)

if not exist Logs mkdir Logs

robot ^
--listener Configurations.auto_screen_record_listener.AutoScreenRecordingListener ^
--outputdir Logs\Report_%timestamp% ^
TestSuite\test03.robot

pause
