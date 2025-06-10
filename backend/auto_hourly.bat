@echo off
:loop
echo %date% %time% 
C:\Python39\python.exe "C:\Users\vkhaf\OneDrive\Desktop\AI agent\hourly_commit_collector.py"
echo %date% %time% 
timeout /t 3600 /nobreak >nul
goto loop