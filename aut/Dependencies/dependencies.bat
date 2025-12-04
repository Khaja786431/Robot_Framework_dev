@echo off

:start
cls

echo Checking for pip...
python ./get-pip.py

echo Installing OpenCV package...
pip install opencv-python

echo DONE!
pause
exit