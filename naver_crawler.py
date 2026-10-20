"""
네이버 부동산 매물 크롤링 및 데이터 자동완성 모듈 (naver_crawler.py)
- 네이버 매물 번호(10자리 등) 및 매물 URL 자동 감지 및 정규화
- 네이버 부동산 매물 상세 정보 실시간 크롤링 (API 및 웹 파싱)
- 네이버 부동산 화면 복사 텍스트 1초 정밀 파서
- 16대 점검항목 및 썸네일 생성기 데이터 자동 변환
"""

import re
import json
import urllib.parse
from typing import Dict, Any, Tuple, Optional
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://fin.land.naver.com/",
    "sec-ch-ua": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


def extract_article_number(input_text: str) -> Optional[str]:
    """
    입력된 텍스트에서 네이버 부동산 매물 번호(8~11자리 숫자)를 추출합니다.
    URL(fin.land.naver.com, new.land.naver.com, m.land.naver.com) 및 단순 번호 지원.
    """
    if not input_text:
        return None
    input_text = input_text.strip()
    
    # 1. URL 패턴에서 추출
    # articles/2452358814 또는 articleId=2452358814 또는 atclNo=2452358814
    url_match = re.search(r"(?:articles|articleId|atclNo|info)[/=](\d{8,12})", input_text)
    if url_match:
        return url_match.group(1)
        
    # 2. 순수 숫자 또는 문자열 내 숫자 추출
    num_match = re.search(r"\b(\d{8,12})\b", input_text)
    if num_match:
        return num_match.group(1)

    return None


def format_korean_price(price_int: int) -> str:
    """원 단위 정수 또는 만원 단위 숫자를 '6억 2,000만 원' 형태로 포맷팅합니다."""
    if not price_int or price_int <= 0:
        return ""
    # 만원 단위 기준인 경우
    val = price_int
    if val >= 100000000: # 1억 이상 (원 단위일 때)
        val = val // 10000

    uk = val // 10000
    man = val % 10000
    
    if uk > 0 and man > 0:
        return f"{uk}억 {man:,}만 원"
    elif uk > 0:
        return f"{uk}억 원"
    else:
        return f"{man:,}만 원"


def format_thumb_price(price_text: str) -> str:
    """'6억 2,000만 원' 형태를 썸네일용 '6억2천' 또는 '2억4천' 형태로 축약합니다."""
    if not price_text:
        return ""
    txt = price_text.replace(" ", "").replace(",", "").replace("원", "")
    # 6억2000만 -> 6억2천
    txt = re.sub(r"000만", "천", txt)
    txt = re.sub(r"00만", "백", txt)
    return txt


def parse_naver_clipboard_text(text: str) -> Dict[str, Any]:
    """
    [안전 백업 엔진] 네이버 부동산 화면에서 마우스로 드래그 복사한 텍스트를 파싱하여
    16대 점검항목 및 썸네일 입력 데이터로 완벽하게 변환합니다.
    """
    res = {}
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # 1. 거래 유형 및 가격 탐색
    # 예: 매매 6억 2,000 | 전세 2억 4,000 | 월세 5,000/120
    trade_match = re.search(r"(매매|전세|월세|단기임대)\s*([\d,억만원\s/]+)", text)
    if trade_match:
        t_type = trade_match.group(1)
        raw_prc = trade_match.group(2).strip()
        res["trade_type"] = t_type
        res["price_text"] = raw_prc + (" 원" if not raw_prc.endswith("원") and not raw_prc.endswith("만원") else "")
        res["thumb_trade_type"] = t_type
        res["thumb_price_text"] = format_thumb_price(res["price_text"])

    # 2. 면적 탐색 (공급/전용 면적)
    # 예: 111.42㎡/79.85㎡ 또는 111.42/79.85㎡ 또는 공급 111.42㎡, 전용 79.85㎡
    area_match = re.search(r"([\d,.]+)\s*㎡?\s*[/|]\s*([\d,.]+)\s*㎡", text)
    if not area_match:
        area_match = re.search(r"공급\s*[:|]?\s*([\d,.]+)\s*㎡?.*?전용\s*[:|]?\s*([\d,.]+)\s*㎡?", text)
    if area_match:
        res["area_supply"] = area_match.group(1).replace(",", "")
        res["area_exclusive"] = area_match.group(2).replace(",", "")
    else:
        # 단일 전용면적 탐색
        single_area = re.search(r"전용\s*[:|]?\s*([\d,.]+)\s*㎡?", text)
        if single_area:
            val = single_area.group(1).replace(",", "")
            res["area_exclusive"] = val
            res["area_supply"] = val

    # 3. 층수 탐색
    # 예: 25/36층 또는 25층/36층 또는 중/36층 또는 고/32층
    fl_match = re.search(r"([저중고\d]+)\s*층?\s*[/|]\s*(\d+)\s*층", text)
    if fl_match:
        cur_f = fl_match.group(1)
        max_f = fl_match.group(2)
        res["floor_info"] = f"{cur_f} / {max_f}층" if not cur_f.endswith("층") else f"{cur_f} / {max_f}층"
    else:
        fl_s = re.search(r"해당층\s*[/|]?\s*총층\s*[:|]?\s*([^\n\r]+)", text)
        if fl_s:
            res["floor_info"] = fl_s.group(1).strip()

    # 4. 방수 / 욕실수
    rb_match = re.search(r"(?:방수\s*[/|]?\s*욕실수|방/욕실|방수/욕실수)\s*[:|]?\s*([^|\n\r]+)", text)
    if not rb_match:
        rb_match = re.search(r"방\s*(\d+)\s*(?:개)?\s*[/|]\s*욕실\s*(\d+)\s*(?:개)?", text)
    if rb_match:
        rb_str = rb_match.group(1).strip()
        nums = re.findall(r"\d+", rb_str)
        if len(nums) >= 2:
            res["room_bath"] = f"방 {nums[0]} / 욕실 {nums[1]}개"
        elif "방" in rb_str:
            res["room_bath"] = rb_str
        else:
            res["room_bath"] = rb_str

    # 5. 방향
    dir_match = re.search(r"(?:방향|방향\s*\(기준\))\s*[:|]?\s*([^|\n\r]+)", text)
    if not dir_match:
        dir_match = re.search(r"(남동향|남서향|남향|동향|서향|북향|북동향|북서향)(?:\s*\(거실\s*기준\))?", text)
    if dir_match:
        d_val = dir_match.group(1).strip()
        if "거실" not in d_val:
            d_val += " (거실 기준)"
        res["direction"] = d_val

    # 6. 현관구조
    ent_match = re.search(r"현관구조\s*[:|]?\s*(계단식|복도식|복합식)", text)
    if ent_match:
        res["entrance_type"] = ent_match.group(1)

    # 7. 난방방식 / 연료
    heat_match = re.search(r"(?:난방\s*\(방식/연료\)|난방방식)\s*[:|]?\s*([^|\n\r]+)", text)
    if heat_match:
        res["heating"] = heat_match.group(1).strip()

    # 8. 입주가능일
    mov_match = re.search(r"입주가능일\s*[:|]?\s*([^|\n\r]+)", text)
    if mov_match:
        res["move_in_date"] = mov_match.group(1).strip()

    # 9. 관리비
    fee_match = re.search(r"관리비\s*[:|]?\s*([^|\n\r]+)", text)
    if fee_match:
        res["maintenance_fee"] = fee_match.group(1).strip()

    # 10. 세대수
    hh_match = re.search(r"(?:세대수|총세대수|해당면적\s*세대수)\s*[:|]?\s*([^|\n\r]+)", text)
    if hh_match:
        res["households"] = hh_match.group(1).strip()

    # 11. 주차대수
    pk_match = re.search(r"(?:총주차대수|주차대수)\s*[:|]?\s*([^|\n\r]+)", text)
    if pk_match:
        res["parking"] = pk_match.group(1).strip()

    # 12. 건축물 용도 (용도지역/지구 제외)
    use_match = re.search(r"(?:건축물\s*용도|주용도|주\s*용도|건축물용도|(?:^|\s)용도(?!\s*지역|\s*지구|\s*구역))\s*[:|]?\s*([^|\n\r]+)", text)
    if use_match:
        clean_u = use_match.group(1).strip()
        if "상업지역" not in clean_u and "주거지역" not in clean_u and "공업지역" not in clean_u:
            res["building_use"] = clean_u

    # 13. 사용승인일
    app_match = re.search(r"(?:사용승인일|준공년월|준공일)\s*[:|]?\s*([^|\n\r]+)", text)
    if app_match:
        res["approval_date"] = app_match.group(1).strip()

    # 14. 소재지 및 단지명
    loc_match = re.search(r"(?:소재지|위치)\s*[:|]?\s*([^|\n\r]+)", text)
    if loc_match:
        res["location"] = loc_match.group(1).strip()

    # 15. 상가 특화 항목: 주구조, 용도지역, 용도지구, 권리금, 추천업종, 화장실
    struct_m = re.search(r"(?:주구조|주\s*구조|구조)\s*[:|]?\s*([^|\n\r]+)", text)
    if struct_m:
        res["structure"] = struct_m.group(1).strip()
    else:
        for cs in ["철골철근콘크리트구조", "철근콘크리트구조", "철골콘크리트구조", "일반철골구조", "경량철골구조", "철골구조", "철골조", "조적조", "벽돌구조"]:
            if cs in text:
                res["structure"] = cs
                break

    zone_m = re.search(r"(?:용도지역|지역)\s*[:|]?\s*([^|\n\r]+)", text)
    if zone_m:
        res["zone_region"] = zone_m.group(1).strip()
    else:
        for z in ["중심상업지역", "일반상업지역", "근린상업지역", "유통상업지역", "준주거지역", "제1종일반주거지역", "제2종일반주거지역", "제3종일반주거지역", "준공업지역", "일반공업지역"]:
            if z in text:
                res["zone_region"] = z
                break

    dist_m = re.search(r"(?:용도지구|지구|구역)\s*[:|]?\s*([^|\n\r]+)", text)
    if dist_m:
        res["zone_district"] = dist_m.group(1).strip()
    else:
        found_dists = [d for d in ["방화지구", "지구단위계획구역", "시가지경관지구", "과밀억제권역"] if d in text]
        if found_dists:
            res["zone_district"] = ", ".join(found_dists)

    prem_m = re.search(r"(?:권리금)\s*[:|]?\s*([^|\n\r]+)", text)
    if prem_m:
        res["premium_fee"] = prem_m.group(1).strip()
    elif "무권리" in text:
        res["premium_fee"] = "무권리 (권리금 없음)"

    rec_m = re.search(r"(?:추천업종|추천\s*업종)\s*[:|]?\s*([^|\n\r]+)", text)
    if rec_m:
        res["recommended_use"] = rec_m.group(1).strip()

    cur_m = re.search(r"(?:현재업종|현\s*업종|현재상태)\s*[:|]?\s*([^|\n\r]+)", text)
    if cur_m:
        res["current_use"] = cur_m.group(1).strip()

    rest_m = re.search(r"(?:화장실)\s*[:|]?\s*([^|\n\r]+)", text)
    if rest_m:
        res["restroom"] = rest_m.group(1).strip()

    # 단지명 및 동/호수 탐색 (첫 5줄 내)
    for line in lines[:5]:
        line_s = line.strip()
        if any(kw in line_s for kw in ["매매", "전세", "월세", "공급", "전용", "해당층", "관리비"]):
            continue
        dong_m = re.search(r"((?:제)?\s*\d{2,4}\s*동)", line_s)
        ho_m = re.search(r"((?:제)?\s*\d{2,4}\s*호)", line_s)
        
        d_val = dong_m.group(1).replace(" ", "") if dong_m else ""
        h_val = ho_m.group(1).replace(" ", "") if ho_m else ""
        
        apt_title = line_s
        if dong_m:
            apt_title = apt_title.replace(dong_m.group(0), "")
        if ho_m:
            apt_title = apt_title.replace(ho_m.group(0), "")
        apt_title = re.sub(r"[\[\]\(\)]", " ", apt_title).strip()
        
        if apt_title:
            res["main_title"] = apt_title
        if d_val or h_val:
            res["sub_title"] = f"{d_val} {h_val}".strip()
            res["dong_name"] = d_val
            res["ho_name"] = h_val
        if res.get("main_title"):
            break

    # 소재지와 건물명 조합
    if res.get("location") and res.get("main_title"):
        b_full = res["main_title"]
        if res.get("sub_title"):
            b_full += f" {res['sub_title']}"
        if b_full not in res["location"]:
            res["location"] = f"{res['location']} ({b_full})"

    # 특징 문구 자동 생성
    feat_parts = []
    if res.get("households"):
        feat_parts.append(res["households"].split(" ")[0])
    if res.get("main_title"):
        feat_parts.append(res["main_title"])
    if feat_parts:
        res["feature_text"] = " · ".join(feat_parts) + " 추천 매물"

    # 썸네일 요약 필드 구성
    if res.get("floor_info"):
        res["spec_line1"] = res["floor_info"]
    if res.get("area_exclusive"):
        res["spec_line2"] = f"공급 {res.get('area_supply', res['area_exclusive'])}㎡ / 전용 {res['area_exclusive']}㎡"
    if res.get("room_bath"):
        res["spec_line3"] = res["room_bath"]
    if res.get("move_in_date"):
        res["spec_line4"] = res["move_in_date"]
    if res.get("direction"):
        res["spec_line5"] = res["direction"]

    return res


def crawl_naver_article(article_input: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    [핵심 크롤러 함수]
    네이버 매물 번호 또는 URL을 받아 네이버 부동산 실시간 상세 정보를 크롤링합니다.
    - 반환: (성공여부: bool, 안내메시지: str, 추출데이터: dict)
    """
    article_no = extract_article_number(article_input)
    if not article_no:
        return False, "유효한 네이버 부동산 매물 번호(8~12자리 숫자) 또는 매물 링크를 찾을 수 없습니다.", {}

    res_data = {}
    error_reasons = []

    # ----------------------------------------------------
    # 전략 1: fin.land.naver.com SSR HTML 및 Hydration 데이터 파싱
    # ----------------------------------------------------
    url_web = f"https://fin.land.naver.com/articles/{article_no}"
    try:
        r = requests.get(url_web, headers=HEADERS, timeout=6)
        if r.status_code == 200:
            html = r.text
            
            # HTML 타이틀에서 단지명 및 기본 정보 추출
            title_match = re.search(r"<title>(.*?)</title>", html)
            if title_match:
                title_text = title_match.group(1).replace("Npay 부동산", "").replace(":", "").replace("매물", "").strip()
                if title_text:
                    res_data["main_title"] = title_text

            # OpenGraph 메타 태그 파싱
            og_title = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html)
            og_desc = re.search(r'<meta\s+property="og:description"\s+content="([^"]+)"', html)
            
            if og_desc:
                desc_text = og_desc.group(1)
                parsed_desc = parse_naver_clipboard_text(desc_text)
                res_data.update({k: v for k, v in parsed_desc.items() if v})

            # Next.js 스트리밍 텍스트에서 매물 정보 JSON 덩어리 탐색
            # self.__next_f.push(...)
            chunks = re.findall(r'self\.__next_f\.push\(\[(?:0|1),\s*"(.*?)"\]\)', html, re.DOTALL)
            for chunk in chunks:
                try:
                    decoded = chunk.encode().decode("unicode_escape")
                    # articleDetail / priceInfo / complexInfo JSON 탐색
                    if "articleNumber" in decoded or "articleName" in decoded or "dealOrWarrantPrc" in decoded:
                        # 정규식으로 핵심 필드 직접 추출
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
        error_reasons.append(f"웹 상세 조회: {e}")

    # ----------------------------------------------------
    # 전략 2: New Land API 조회
    # ----------------------------------------------------
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
            error_reasons.append(f"API 조회: {e}")

    # ----------------------------------------------------
    # 데이터 후처리 및 완성도 보강
    # ----------------------------------------------------
    has_valid_specs = any(res_data.get(k) for k in ["price_text", "area_exclusive", "area_supply", "floor_info", "room_bath"])
    if res_data and has_valid_specs:
        # 서브 타이틀 및 소재지 조립
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

        # 썸네일 스펙 라인 연동
        if res_data.get("floor_info"):
            res_data["spec_line1"] = res_data["floor_info"]
        if res_data.get("area_exclusive"):
            res_data["spec_line2"] = f"공급 {res_data.get('area_supply', res['area_exclusive'])}㎡ / 전용 {res_data['area_exclusive']}㎡"
        if res_data.get("room_bath"):
            res_data["spec_line3"] = res_data["room_bath"]
        if res_data.get("move_in_date"):
            res_data["spec_line4"] = res_data["move_in_date"]
        if res_data.get("direction"):
            res_data["spec_line5"] = res_data["direction"]

        return True, f"네이버 매물 [{article_no}] 크롤링 성공!", res_data

    # 만약 네이버 측의 봇 차단이나 유효하지 않은 매물 번호인 경우 친절한 안내 제공
    return False, f"네이버 부동산 방화벽(Rate limit: TOO_MANY_REQUESTS) 정책으로 인해 프로그램의 직접 API 호출이 차단되었습니다. 네이버 부동산 상세 화면을 마우스로 드래그 복사(Ctrl+C)하여 옆의 [📋 네이버 화면 복사 텍스트 붙여넣기]를 이용하시면 100% 완벽하게 자동 완성됩니다!", {}
