"""
부동산 썸네일 생성기 - 스마트폰 외부 임장용 모바일 접속기
Cloudflare Tunnel을 통해 외부 LTE/5G 환경에서 안전하게 접속할 수 있는 공개 HTTPS 주소를 생성합니다.
비밀번호: 4989
"""

import subprocess
import time
import re
import sys
import os
import urllib.request
import webbrowser

try:
    import pyperclip
    HAS_CLIPBOARD = True
except ImportError:
    HAS_CLIPBOARD = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUDFLARED_PATH = os.path.join(BASE_DIR, "cloudflared.exe")

def is_port_open(port=8501):
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('127.0.0.1', port)) == 0

def main():
    print("=" * 65)
    print("  🏢 참좋은공인중개사 - 스마트폰 외부 임장 접속기 시작 중...")
    print("=" * 65)

    # 1. Streamlit 서버 확인 및 실행
    if not is_port_open(8501):
        print(">> [1/2] 로컬 썸네일 엔진 가동 중 (Port 8501)...")
        subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless=true", "--server.port=8501"],
            cwd=BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(3)
    else:
        print(">> [1/2] 썸네일 엔진이 이미 정상 동작 중입니다.")

    # 2. Cloudflare 터널 실행
    print(">> [2/2] 안전한 외부 모바일 암호화 보안 터널 생성 중...")
    if not os.path.exists(CLOUDFLARED_PATH):
        print(">> cloudflared.exe 다운로드 중...")
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        urllib.request.urlretrieve(url, CLOUDFLARED_PATH)

    cf_proc = subprocess.Popen(
        [CLOUDFLARED_PATH, "tunnel", "--url", "http://localhost:8501"],
        cwd=BASE_DIR,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )

    tunnel_url = None
    start_time = time.time()

    while time.time() - start_time < 30:
        line = cf_proc.stderr.readline()
        if not line:
            time.sleep(0.1)
            continue
        match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
        if match:
            tunnel_url = match.group(0)
            break

    if not tunnel_url:
        print(">> 터널 주소 생성에 실패했습니다. 인터넷 연결 상태를 확인해주세요.")
        return

    # 클립보드 복사
    copied_msg = ""
    if HAS_CLIPBOARD:
        try:
            pyperclip.copy(tunnel_url)
            copied_msg = " (클립보드에 자동 복사됨! 카톡에 바로 붙여넣기 가능)"
        except Exception:
            pass

    print("\n" + "=" * 65)
    print("  🎉 스마트폰 외부 접속 준비가 완료되었습니다!")
    print("=" * 65)
    print(f"👉 스마트폰 브라우저 접속 주소:\n   {tunnel_url}{copied_msg}\n")
    print("🔑 접근 비밀번호: 4989  (사고팔고)")
    print("=" * 65)
    print("📱 사용 방법:")
    print("  1. 위 주소를 스마트폰(크롬/사파리)에서 열거나, 카카오톡 '나와의 채팅'에 붙여넣어 누르세요.")
    print("  2. 비밀번호 '4989'를 입력하시면 현장에서 즉시 썸네일 제작이 가능합니다!")
    print("  3. 현장에서 찍은 거실/방 사진을 폰에서 바로 올려 1080x1080으로 다운로드하세요.")
    print("=" * 65)
    print("※ 임장이 끝나실 때까지 이 창을 닫지 마세요. (종료하려면 창을 닫거나 Ctrl+C)\n")

    # QR 코드 안내 페이지 생성 및 로컬 브라우저로 띄우기 (카메라로 바로 찍을 수 있게)
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={tunnel_url}"
    html_content = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>스마트폰 임장용 접속 QR코드</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #F4F6F8;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }}
        .card {{
            background: white;
            padding: 35px 30px;
            border-radius: 18px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.08);
            text-align: center;
            max-width: 380px;
        }}
        h2 {{ color: #1E2022; margin-top: 0; margin-bottom: 6px; font-size: 22px; }}
        .badge {{ background: #FFF2E8; color: #F48A26; padding: 5px 12px; border-radius: 20px; font-weight: 700; font-size: 14px; display: inline-block; margin-bottom: 15px; }}
        .qr-box {{ margin: 15px 0; }}
        .qr-box img {{ width: 220px; height: 220px; border-radius: 12px; border: 1px solid #E5E8EB; }}
        .url-box {{ background: #F8F9FA; padding: 10px; border-radius: 8px; word-break: break-all; font-size: 13px; color: #0066CC; font-weight: 600; margin-bottom: 12px; }}
        .pw-box {{ background: #232529; color: #FFFFFF; padding: 10px 15px; border-radius: 8px; font-weight: 700; font-size: 16px; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="card">
        <h2>🏢 참좋은공인중개사</h2>
        <div class="badge">스마트폰 임장용 외부 접속</div>
        <p style="color: #6C757D; font-size: 13px; margin: 0;">스마트폰 기본 카메라로 아래 QR코드를 스캔하시면 바로 접속됩니다.</p>
        <div class="qr-box">
            <img src="{qr_url}" alt="QR Code">
        </div>
        <div class="url-box">{tunnel_url}</div>
        <div class="pw-box">🔑 접속 비밀번호: 4989</div>
    </div>
</body>
</html>"""
    qr_html_path = os.path.join(BASE_DIR, "mobile_qr.html")
    with open(qr_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    webbrowser.open(f"file:///{qr_html_path}")

    try:
        cf_proc.wait()
    except KeyboardInterrupt:
        print("\n>> 접속기를 종료합니다.")
        cf_proc.kill()

if __name__ == "__main__":
    main()
