#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
====================================================================
참좋은부동산 - ivy(iwinv) 서버용 네이버 부동산 중계 프록시 (ivy_proxy.py)
====================================================================
기능:
  - 네이버 부동산 방화벽(WAF/Rate limit)을 우회하기 위해, 국내 고정 IP를 가진
    ivy 서버에서 네이버 데이터를 대신 수집하여 Streamlit Cloud로 전달하는 초경량 API 서버입니다.
  - 외부 프레임워크(FastAPI/Flask) 설치 없이 Python 내장 `http.server`와 `requests`만으로 작동합니다.

실행 방법:
  1. 의존성 설치:
     pip3 install requests
  2. 실행 (기본 포트 8000, 기본 키 chamjoeun):
     python3 ivy_proxy.py
  3. 백그라운드 상시 실행 (터미널 종료 후에도 유지):
     nohup python3 ivy_proxy.py > proxy.log 2>&1 &
"""

import sys
import os
import re
import json
import argparse
from typing import Dict, Any, Tuple
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests

# Windows CP949 콘솔 인코딩 대응
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 기본 설정값
DEFAULT_PORT = 8000
DEFAULT_KEY = "chamjoeun"

# 네이버 요청 헤더
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://fin.land.naver.com/",
    "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


def format_thumb_price(price_text: str) -> str:
    """'6억 8,000 원' 형태를 썸네일용 '6억8천' 또는 '2억4천' 형태로 축약합니다."""
    if not price_text:
        return ""
    txt = price_text.replace(" ", "").replace(",", "").replace("원", "")
    txt = re.sub(r"(\d+)000(?:만)?$", r"\1천", txt)
    txt = re.sub(r"(\d+)00(?:만)?$", r"\1백", txt)
    txt = re.sub(r"000만", "천", txt)
    txt = re.sub(r"00만", "백", txt)
    return txt


def crawl_naver_core(article_no: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    네이버 매물 번호를 받아 fin.land 및 new.land 엔드포인트에서 데이터를 정밀 추출합니다.
    """
    res_data = {}
    error_reasons = []

    # 1. fin.land.naver.com SSR HTML 파싱
    url_web = f"https://fin.land.naver.com/articles/{article_no}"
    try:
        r = requests.get(url_web, headers=HEADERS, timeout=6)
        if r.status_code == 200:
            html = r.text

            # OpenGraph 메타 태그
            og_title = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html)
            og_desc = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html)

            if og_title:
                res_data["main_title"] = og_title.group(1).replace("Npay 부동산", "").strip()
            
            if og_desc:
                desc = og_desc.group(1).strip()
                m_trade = re.match(r"^(매매|전세|월세|단기임대)\s*(.*)$", desc)
                if m_trade:
                    res_data["trade_type"] = m_trade.group(1)
                    res_data["price_text"] = m_trade.group(2) + " 원"

            # 2. [가장 강력하고 정확한 파서] SSR DataList __term / __definition 추출
            pairs = re.findall(r'__term">(.*?)</div>\s*<div[^>]*__definition">(.*?)</div>', html, re.DOTALL)
            data_map = {}
            for k, v in pairs:
                clean_k = re.sub(r'<[^>]+>', '', k).replace("도움말 보기", "").strip()
                clean_v = re.sub(r'<[^>]+>', ' ', v).strip()
                clean_v = ' '.join(clean_v.split())
                if clean_k not in data_map:
                    data_map[clean_k] = clean_v

            # 가격
            if "매매가" in data_map and not res_data.get("price_text"):
                res_data["price_text"] = data_map["매매가"]
                res_data["trade_type"] = "매매"
            elif "전세가" in data_map and not res_data.get("price_text"):
                res_data["price_text"] = data_map["전세가"]
                res_data["trade_type"] = "전세"
            elif "보증금/월세" in data_map and not res_data.get("price_text"):
                res_data["price_text"] = data_map["보증금/월세"]
                res_data["trade_type"] = "월세"

            # 공급 / 전용면적
            if "공급면적" in data_map:
                m_sup = re.search(r'([\d.]+)\s*㎡', data_map["공급면적"])
                if m_sup:
                    res_data["area_supply"] = m_sup.group(1)
            if "전용면적" in data_map:
                m_exc = re.search(r'([\d.]+)\s*㎡', data_map["전용면적"])
                if m_exc:
                    res_data["area_exclusive"] = m_exc.group(1)

            # 층수
            if "해당층/총층" in data_map:
                raw_floor = data_map["해당층/총층"]
                m_fl = re.search(r'([저중고\d]+)(?:\s*\([^)]*\))?\s*/\s*(\d+층)', raw_floor)
                if m_fl:
                    res_data["floor_info"] = f"{m_fl.group(1)}/{m_fl.group(2)}"
                else:
                    res_data["floor_info"] = raw_floor.replace(" ", "")

            # 방수/욕실수
            if "방수/욕실수" in data_map:
                m_rb = re.search(r'(\d+)\s*/\s*(\d+)', data_map["방수/욕실수"])
                if m_rb:
                    res_data["room_bath"] = f"방 {m_rb.group(1)} / 욕실 {m_rb.group(2)}개"
                else:
                    res_data["room_bath"] = data_map["방수/욕실수"]

            # 향
            if "향" in data_map:
                raw_dir = data_map["향"].replace("(거실 기준)", "").replace("거실 기준", "").strip()
                res_data["direction"] = f"{raw_dir} (거실 기준)" if raw_dir else data_map["향"]

            # 위치 / 소재지
            if "위치" in data_map:
                loc = data_map["위치"]
                if res_data.get("main_title") and res_data["main_title"] not in loc:
                    res_data["location"] = f"{loc} ({res_data['main_title']})"
                else:
                    res_data["location"] = loc

            # 건축물용도
            if "건축물용도" in data_map:
                res_data["building_use"] = data_map["건축물용도"]

            # 사용승인일
            if "사용승인일" in data_map:
                m_date = re.search(r'(\d{4}[.-]\d{2}[.-]\d{2})', data_map["사용승인일"])
                if m_date:
                    res_data["approval_date"] = m_date.group(1).replace(".", "-")
                else:
                    res_data["approval_date"] = data_map["사용승인일"]

            # 세대수
            if "세대수" in data_map:
                res_data["households"] = data_map["세대수"]

            # 주차
            if "주차" in data_map:
                res_data["parking"] = data_map["주차"]

            # 입주가능일
            if "입주가능일" in data_map:
                res_data["move_in_date"] = data_map["입주가능일"]

            # 관리비
            if "관리비" in data_map:
                res_data["maintenance_fee"] = data_map["관리비"]

            # 3. Next.js 스트리밍 내부 검색 (추가 보강)
            chunks = re.findall(r'self\.__next_f\.push\(\[(?:0|1),\s*"(.*?)"\]\)', html, re.DOTALL)
            for chunk in chunks:
                try:
                    decoded = chunk.encode().decode("unicode_escape")
                    if "articleNumber" in decoded or "articleName" in decoded or "dealOrWarrantPrc" in decoded:
                        name_m = re.search(r'"articleName"\s*:\s*"([^"]+)"', decoded)
                        if name_m and not res_data.get("main_title"):
                            res_data["main_title"] = name_m.group(1)

                        bild_m = re.search(r'"bildNm"\s*:\s*"([^"]+)"', decoded)
                        if bild_m:
                            res_data["dong_name"] = bild_m.group(1)

                        flr_m = re.search(r'"floorInfo"\s*:\s*"([^"]+)"', decoded)
                        if flr_m and not res_data.get("floor_info"):
                            res_data["floor_info"] = flr_m.group(1)

                        prc_m = re.search(r'"dealOrWarrantPrc"\s*:\s*"([^"]+)"', decoded)
                        if prc_m and not res_data.get("price_text"):
                            res_data["price_text"] = prc_m.group(1) + " 원"

                        area1_m = re.search(r'"area1"\s*:\s*([\d.]+)', decoded)
                        area2_m = re.search(r'"area2"\s*:\s*([\d.]+)', decoded)
                        if area1_m and not res_data.get("area_supply"):
                            res_data["area_supply"] = f"{float(area1_m.group(1)):.2f}"
                        if area2_m and not res_data.get("area_exclusive"):
                            res_data["area_exclusive"] = f"{float(area2_m.group(1)):.2f}"

                        dir_m = re.search(r'"direction"\s*:\s*"([^"]+)"', decoded)
                        if dir_m and not res_data.get("direction"):
                            res_data["direction"] = dir_m.group(1) + " (거실 기준)"

                        use_m = re.search(r'"realEstateTypeName"\s*:\s*"([^"]+)"', decoded)
                        if use_m and not res_data.get("building_use"):
                            res_data["building_use"] = use_m.group(1)
                except Exception:
                    continue
    except Exception as e:
        error_reasons.append(f"웹조회: {e}")

    # 2. new.land.naver.com API 보강 시도
    if not res_data.get("price_text") or not res_data.get("area_exclusive"):
        url_api = f"https://new.land.naver.com/api/articles/{article_no}"
        try:
            r_api = requests.get(url_api, headers=HEADERS, timeout=4)
            if r_api.status_code == 200:
                data = r_api.json()
                article = data.get("articleDetail") or data.get("article") or data
                if article.get("articleName"):
                    res_data["main_title"] = article.get("articleName")
                if article.get("bildNm"):
                    res_data["dong_name"] = article.get("bildNm")
                if article.get("floorInfo"):
                    res_data["floor_info"] = article.get("floorInfo")
                if article.get("dealOrWarrantPrc"):
                    res_data["price_text"] = article.get("dealOrWarrantPrc") + " 원"
                if article.get("tradeTypeName"):
                    res_data["trade_type"] = article.get("tradeTypeName")
                if article.get("area1"):
                    res_data["area_supply"] = f"{float(article.get('area1')):.2f}"
                if article.get("area2"):
                    res_data["area_exclusive"] = f"{float(article.get('area2')):.2f}"
                if article.get("direction"):
                    res_data["direction"] = article.get("direction") + " (거실 기준)"
                if article.get("realEstateTypeName"):
                    res_data["building_use"] = article.get("realEstateTypeName")
                if article.get("roomCount") and article.get("bathroomCount"):
                    res_data["room_bath"] = f"방 {article.get('roomCount')} / 욕실 {article.get('bathroomCount')}개"
                if article.get("parkingCount"):
                    res_data["parking"] = f"총 {article.get('parkingCount')}대"
                if article.get("totalHouseholdCount"):
                    res_data["households"] = f"총 {article.get('totalHouseholdCount')}세대"
        except Exception as e:
            error_reasons.append(f"API조회: {e}")

    # 3. 데이터 후처리
    has_valid_specs = any(res_data.get(k) for k in ["price_text", "area_exclusive", "area_supply", "floor_info", "room_bath", "main_title"])
    if res_data and has_valid_specs:
        d_name = res_data.get("dong_name", "")
        m_title = res_data.get("main_title", "")
        fl_info = res_data.get("floor_info", "")

        if d_name:
            res_data["sub_title"] = d_name
        elif fl_info:
            res_data["sub_title"] = fl_info

        if m_title and not res_data.get("location"):
            res_data["location"] = f"{m_title} {d_name}".strip()

        if res_data.get("price_text"):
            res_data["thumb_trade_type"] = res_data.get("trade_type", "매매")
            res_data["thumb_price_text"] = format_thumb_price(res_data["price_text"])

        if res_data.get("floor_info"):
            res_data["spec_line1"] = res_data["floor_info"]
        if res_data.get("area_exclusive"):
            res_data["spec_line2"] = f"공급 {res_data.get('area_supply', res_data['area_exclusive'])}㎡ / 전용 {res_data['area_exclusive']}㎡"
        if res_data.get("room_bath"):
            res_data["spec_line3"] = res_data["room_bath"]
        if res_data.get("move_in_date"):
            res_data["spec_line4"] = res_data["move_in_date"]
        if res_data.get("direction"):
            res_data["spec_line5"] = res_data["direction"]

        return True, f"네이버 매물 [{article_no}] 크롤링 성공 (아이비 서버 경유)", res_data

    return False, f"네이버 매물 [{article_no}] 정보를 가져오지 못했습니다. (사유: {', '.join(error_reasons) or '응답 없음'})", {}


class ProxyRequestHandler(BaseHTTPRequestHandler):
    auth_key = DEFAULT_KEY

    def _send_json(self, status_code: int, data: Dict[str, Any]):
        response_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # 1. 헬스 체크
        if path in ["/", "/health", "/status"]:
            self._send_json(200, {
                "status": "ok",
                "service": "chamjoeun-ivy-naver-proxy",
                "message": "아이비 네이버 부동산 중계 프록시 서버가 정상 작동 중입니다."
            })
            return

        # 2. 크롤링 엔드포인트: /crawl?article=2656663434&key=chamjoeun
        if path == "/crawl":
            req_key = query.get("key", [""])[0] or self.headers.get("X-Auth-Key", "")
            if self.auth_key and req_key != self.auth_key:
                self._send_json(403, {
                    "success": False,
                    "message": "인증 실패: 잘못된 API 키(key)입니다."
                })
                return

            article_val = query.get("article", [""])[0]
            if not article_val:
                self._send_json(400, {
                    "success": False,
                    "message": "매물 번호(article) 파라미터가 누락되었습니다. 예: /crawl?article=2656663434&key=..."
                })
                return

            # 숫자만 추출
            article_match = re.search(r"\d{8,12}", article_val)
            if not article_match:
                self._send_json(400, {
                    "success": False,
                    "message": "유효한 매물 번호(8~12자리 숫자)가 아닙니다."
                })
                return

            article_no = article_match.group(0)
            print(f"[ivy-proxy] 크롤링 요청 접수: {article_no}")

            success, message, data = crawl_naver_core(article_no)
            self._send_json(200 if success else 200, {
                "success": success,
                "article_no": article_no,
                "message": message,
                "data": data
            })
            return

        # 미등록 경로
        self._send_json(404, {"success": False, "message": "존재하지 않는 경로입니다. (/crawl 또는 /health 사용)"})

    def log_message(self, format, *args):
        # 콘솔에 깔끔하게 한 줄 로그 출력
        print(f"[{self.log_date_time_string()}] {self.address_string()} - {format % args}")


def run_server(port: int = DEFAULT_PORT, key: str = DEFAULT_KEY):
    ProxyRequestHandler.auth_key = key
    server_address = ("0.0.0.0", port)
    httpd = ThreadingHTTPServer(server_address, ProxyRequestHandler)
    print("=" * 65)
    print(" [START] Chamjoeun - ivy Naver Real Estate Proxy Server")
    print(f" * Port: {port}")
    print(f" * Auth Key: {key}")
    print(f" * Health Check: http://SERVER_IP:{port}/health")
    print(f" * Crawl URL: http://SERVER_IP:{port}/crawl?article=ARTICLE_NO&key={key}")
    print("=" * 65)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nProxy server stopping...")
        httpd.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ivy 네이버 부동산 프록시 서버")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", DEFAULT_PORT)), help="서버 포트 (기본: 8000)")
    parser.add_argument("--key", type=str, default=os.environ.get("PROXY_KEY", DEFAULT_KEY), help="보안 인증 키 (기본: chamjoeun)")
    args = parser.parse_args()

    run_server(port=args.port, key=args.key)
