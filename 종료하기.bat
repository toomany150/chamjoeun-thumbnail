@echo off
chcp 65001 > nul
echo ========================================================
echo   부동산 썸네일 & 네이버광고 프로그램 종료 중...
echo ========================================================
taskkill /F /IM streamlit.exe 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8501"') do taskkill /F /PID %%a 2>nul
echo.
echo [완료] 프로그램이 정상적으로 종료되었습니다.
timeout /t 2 > nul
