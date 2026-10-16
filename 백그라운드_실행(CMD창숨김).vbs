Set WshShell = CreateObject("WScript.Shell")
' CMD 검은 창을 화면에 전혀 띄우지 않고(0 = 숨김 모드) 백그라운드로 Streamlit 실행
WshShell.Run "python -m streamlit run app.py --server.port 8501", 0, False
WScript.Sleep 1500
' 기본 인터넷 브라우저로 사이트 자동 열기
WshShell.Run "http://localhost:8501"
