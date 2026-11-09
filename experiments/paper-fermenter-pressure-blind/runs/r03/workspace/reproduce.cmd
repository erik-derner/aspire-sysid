@echo off
python fit_explore.py > explore_output.txt
if errorlevel 1 exit /b 1
python fit_nonlinear.py > nonlinear_output.txt
if errorlevel 1 exit /b 1
python fit_more.py > more_output.txt
if errorlevel 1 exit /b 1
python fit_hinges.py > hinge_output.txt
if errorlevel 1 exit /b 1
python fit_final.py > final_output.txt
if errorlevel 1 exit /b 1
python make_submission.py
if errorlevel 1 exit /b 1
python check_submission.py
