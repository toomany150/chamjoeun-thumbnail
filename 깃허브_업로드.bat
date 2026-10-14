@echo off
chcp 65001 > nul
echo ========================================================
echo   🏢 참좋은공인중개사 - 깃허브(GitHub) 원클릭 업로드 도우미
echo ========================================================
echo.
echo GitHub(https://github.com)에서 새로 만든 빈 저장소 주소를 입력해주세요.
echo (예: https://github.com/내아이디/realestate-thumbnail.git)
echo.
set /p REPO_URL=">> GitHub 저장소 주소 입력: "

if "%REPO_URL%"=="" (
    echo.
    echo [오류] 주소가 입력되지 않았습니다. 다시 실행해주세요.
    pause
    exit /b
)

echo.
echo >> 깃허브 저장소 연결 및 파일 업로드 시작...
git remote remove origin 2>nul
git remote add origin %REPO_URL%
git branch -M main
git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   🎉 깃허브 업로드가 성공적으로 완료되었습니다!
    echo   이제 스트림릿 클라우드(share.streamlit.io)에서 배포하세요.
    echo ========================================================
) else (
    echo.
    echo [안내] 깃허브 로그인이 필요할 수 있습니다. 브라우저 인증 창이 뜨면 승인해주세요.
)
pause
