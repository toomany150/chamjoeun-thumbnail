@echo off
chcp 65001 > nul
title iwinv(ivy) 서버 네이버 프록시 실행 도우미
color 0F

echo ======================================================================
echo   참좋은부동산 - iwinv(ivy) 서버 네이버 프록시 백그라운드 실행 도우미
echo ======================================================================
echo.
echo [1] 서버 IP: 49.247.132.147
echo [2] 포트: 8000
echo.
echo 💡 접속 후 서버 터미널에 아래 명령어를 복사(Ctrl+C)하여 붙여넣으세요:
echo.
echo    nohup python3 ivy_proxy.py > proxy.log 2>&1 &
echo.
echo ----------------------------------------------------------------------
echo ※ 만약 서버에 최신 ivy_proxy.py가 없다면 지금 업로드할 수도 있습니다.
echo ======================================================================
echo.
echo 1: 바로 SSH 접속하여 프록시 켜기
echo 2: 최신 ivy_proxy.py 파일을 서버에 먼저 전송(scp) 후 접속
echo 3: 종료
echo.
set /p sel="선택번호를 입력하고 엔터를 치세요 (1/2/3): "

if "%sel%"=="1" goto DO_SSH
if "%sel%"=="2" goto DO_SCP
goto END

:DO_SCP
echo.
echo [최신 파일 전송 중...] 서버 비밀번호를 입력해주세요:
scp ivy_proxy.py root@49.247.132.147:~/
echo 전송 완료! SSH로 접속합니다.
echo.

:DO_SSH
echo.
echo SSH 접속 중... 서버 비밀번호를 입력해주세요:
ssh -t root@49.247.132.147 "echo '서버 접속 성공! 아래 명령을 실행합니다: nohup python3 ivy_proxy.py > proxy.log 2>&1 &'; nohup python3 ivy_proxy.py > proxy.log 2>&1 & sleep 1; ps aux | grep ivy_proxy; exec bash"
goto END

:END
echo.
pause
