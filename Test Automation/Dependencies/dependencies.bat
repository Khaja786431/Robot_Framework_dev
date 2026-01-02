@echo off

:start
cls

echo Checking for pip...
python ./get-pip.py

echo Installing required packages or libraries...
pip install opencv-python numpy pillow pytesseract robotframework

echo DONE!
pause
exit

@REM Command to start appium server "appium --allow-insecure=uiautomator2:adb_shell"
@REM to start recording on multiple DUT's use this in .robot--> ${DUTS}   Phone,Cluster


@REM #To switch branch
@REM git checkout main

@REM To pull changes from main branch
@REM git pull origin main

@REM To check the changes
@REM git checkout

@REM TO check all changes or modifications or untracked changes 
@REM git status

@REM To create branch and switch 
@REM git checkout -b "branchname"

@REM To add files to staging area
@REM git add .

@REM To commit files
@REM git commit -m "description"

@REM To push files from local to remote repo
@REM git push --set-upstream origin "branch_name"