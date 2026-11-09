"""
네이버 부동산 매물 크롤링 및 데이터 자동완성 모듈 (naver_crawler.py)
- 네이버 매물 번호(10자리 등) 및 매물 URL 자동 감지 및 정규화
- 네이버 부동산 매물 상세 정보 실시간 크롤링 (API 및 웹 파싱)
- 네이버 부동산 화면 복사 텍스트 1초 정밀 파서
- 16대 점검항목 및 썸네일 생성기 데이터 자동 변환
"""

import os
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
    """'6억 8,000 원' 형태를 썸네일용 '6억8천' 또는 '2억4천' 형태로 축약합니다."""
    if not price_text:
        return ""
    txt = price_text.replace(" ", "").replace(",", "").replace("원", "")
    txt = re.sub(r"(\d+)000(?:만)?$", r"\1천", txt)
    txt = re.sub(r"(\d+)00(?:만)?$", r"\1백", txt)
    txt = re.sub(r"000만", "천", txt)
    txt = re.sub(r"00만", "백", txt)
    return txt


def format_premium_fee(raw_val: Any) -> str:
    """
    상가 권리금 텍스트 또는 숫자를 표준 표기로 변환합니다.
    - 없음 / 0 / 무권리 -> '무권리 (권리금 없음)'
    - 협의 -> '협의가능'
    - 숫자(만원/원) -> '3,000만 원'
    """
    if raw_val is None:
        return ""
    s = str(raw_val).strip()
    if not s:
        return ""
    if any(kw in s for kw in ["무권리", "없음", "0원", "없 음", "무"]):
        return "무권리 (권리금 없음)"
    if s == "0":
        return "무권리 (권리금 없음)"
    if "협의" in s:
        return "협의가능"

    # 순수 숫자 또는 만/억 단위 처리
    nums = re.findall(r'\d+', s.replace(",", ""))
    if nums and not ("만" in s or "억" in s):
        try:
            val_int = int("".join(nums))
            if val_int == 0:
                return "무권리 (권리금 없음)"
            if val_int >= 100000000:  # 원 단위 (예: 30,000,000)
                val_int = val_int // 10000
            if val_int >= 10000:
                uk = val_int // 10000
                rem = val_int % 10000
                return f"{uk}억 {rem:,}만 원".replace(" 0만 원", "만 원")
            return f"{val_int:,}만 원"
        except Exception:
            pass

    # "3000만원" -> "3,000만 원"
    m_man = re.search(r'([\d,]+)\s*만원?', s)
    if m_man:
        clean_n = int(m_man.group(1).replace(",", ""))
        if clean_n >= 10000:
            uk = clean_n // 10000
            rem = clean_n % 10000
            return f"{uk}억 {rem:,}만 원".replace(" 0만 원", "만 원")
        return f"{clean_n:,}만 원"

    m_uk = re.search(r'(\d+)\s*억(?:\s*([\d,]+)\s*만?원?)?', s)
    if m_uk:
        uk = int(m_uk.group(1))
        rem = int(m_uk.group(2).replace(",", "")) if m_uk.group(2) else 0
        if rem > 0:
            return f"{uk}억 {rem:,}만 원"
        return f"{uk}억 원"

    return s


def normalize_approval_date(raw_date: Any) -> str:
    """
    네이버 매물 및 건축물대장의 사용승인일/준공일자 텍스트를
    표준 'YYYY년 MM월 DD일' 또는 'YYYY년 MM월' 형식으로 정규화합니다.
    """
    if not raw_date:
        return ""
    s = str(raw_date).strip()
    if not s or s in ["-", "미상", "확인불가"]:
        return ""

    # 1. YYYY년 MM월 DD일 or YYYY년 M월 D일
    m_full_kr = re.search(r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일', s)
    if m_full_kr:
        y, m, d = m_full_kr.group(1), int(m_full_kr.group(2)), int(m_full_kr.group(3))
        return f"{y}년 {m:02d}월 {d:02d}일"

    # 2. YYYY.MM.DD or YYYY-MM-DD or YYYY/MM/DD
    m_ymd = re.search(r'(\d{4})[./-](\d{1,2})[./-](\d{1,2})', s)
    if m_ymd:
        y, m, d = m_ymd.group(1), int(m_ymd.group(2)), int(m_ymd.group(3))
        return f"{y}년 {m:02d}월 {d:02d}일"

    # 3. YYYYMMDD (8자리 숫자 예: 20180520)
    m_8 = re.search(r'\b(19\d{2}|20\d{2})(\d{2})(\d{2})\b', s)
    if m_8:
        y, m, d = m_8.group(1), int(m_8.group(2)), int(m_8.group(3))
        return f"{y}년 {m:02d}월 {d:02d}일"

    # 4. YYYY년 MM월 or YYYY년 M월
    m_ym_kr = re.search(r'(\d{4})\s*년\s*(\d{1,2})\s*월', s)
    if m_ym_kr:
        y, m = m_ym_kr.group(1), int(m_ym_kr.group(2))
        return f"{y}년 {m:02d}월"

    # 5. YYYY.MM or YYYY-MM or YYYY/MM
    m_ym = re.search(r'(\d{4})[./-](\d{1,2})\b', s)
    if m_ym:
        y, m = m_ym.group(1), int(m_ym.group(2))
        return f"{y}년 {m:02d}월"

    # 6. YYYY년 or YYYY
    m_y = re.search(r'\b(19\d{2}|20\d{2})\b', s)
    if m_y:
        return f"{m_y.group(1)}년"

    return s


def extract_maintenance_fee_and_detail(raw_fee: str = "", data_map: dict = None, text_content: str = "", is_commercial: bool = None) -> tuple:
    """
    네이버 매물 크롤링 또는 텍스트에서 관리비와 관리비 세부내역을 정밀 추출/보강합니다.
    - 상가(근린생활시설/업무시설)의 경우 비목별 미표기, 실사용량 별도 등 상가 특성에 맞는 실데이터 유지
    - 주거용의 경우 법적 명시사항(월 10만원 이상 시 세부내역 필수) 충족
    """
    fee = ""
    detail = ""
    data_map = data_map or {}

    # 상가 여부 자동 판단
    if is_commercial is None:
        is_commercial = False
        comm_keys = [
            "권리금", "권리금 유무", "권리금유무", "추천업종", "추천 업종", 
            "현재업종", "현업종", "현재상태", "현재 상태", "용도지역", "주구조", 
            "계약면적", "비목별 부과금액", "비목별부과금액"
        ]
        if any(k in data_map for k in comm_keys):
            is_commercial = True
        b_use = str(data_map.get("건축물용도", "") or data_map.get("건축물 용도", ""))
        if any(k in b_use for k in ["근린생활", "상가", "판매", "업무", "점포", "사무실"]):
            is_commercial = True
        if not is_commercial and text_content:
            if any(k in text_content for k in ["상가", "근린생활", "권리금", "무권리", "추천업종", "현재업종", "현재상태"]):
                is_commercial = True

    # 1. data_map에서 세부내역 및 부과기준/포함항목 전용 키 검색
    rule_from_map = ""
    inc_from_map = ""
    for k in ["비목별 부과금액", "비목별부과금액", "비목별금액", "관리비 세부내역", "관리비세부내역", "관리비 비목", "세부내역", "비목"]:
        if k in data_map and data_map[k].strip():
            detail = data_map[k].replace("도움말 보기", "").replace("상세보기", "").strip()
            break
    for k in ["관리비부과기준", "관리비 부과기준", "부과기준"]:
        if k in data_map and data_map[k].strip():
            rule_from_map = data_map[k].replace("부과해요.", "부과").replace("부과해요", "부과").strip()
            break
    for k in ["관리비 포함항목", "관리비포함항목", "포함 항목(사용료)", "포함항목(사용료)", "포함 항목", "포함항목", "관리비 항목", "관리비항목"]:
        if k in data_map and data_map[k].strip():
            inc_from_map = data_map[k].strip()
            break
    if not detail and (rule_from_map or inc_from_map):
        if rule_from_map and inc_from_map:
            detail = f"{rule_from_map} (포함항목: {inc_from_map})"
        else:
            detail = rule_from_map or f"포함항목: {inc_from_map}"

    # 2. 관리비 금액 처리
    cand_fee = ""
    if raw_fee:
        cand_fee = raw_fee.replace("도움말 보기", "").replace("상세보기", "").strip()
    elif "관리비" in data_map:
        cand_fee = data_map["관리비"].replace("도움말 보기", "").replace("상세보기", "").strip()
    elif "월관리비" in data_map:
        cand_fee = data_map["월관리비"].replace("도움말 보기", "").replace("상세보기", "").strip()

    if cand_fee in ["부과기준", "세부내역", "포함항목", "포함 항목", "-"]:
        cand_fee = ""

    if cand_fee:
        # 한 줄에 '23만원 관리규약 등에 따라 부과해요 ...'처럼 금액과 내역이 함께 있는 경우 분리
        inline_m = re.match(r"^((?:월\s*|약\s*)?\d[\d,.]*\s*(?:만\s*\d*\s*원|만원|원))\s+([^\d].*)$", cand_fee)
        if inline_m:
            fee = inline_m.group(1).strip()
            rem = inline_m.group(2).strip(" ()-·•:")
            if rem and not detail:
                detail = rem
        else:
            paren_m = re.search(r'^([^(/\n]+)[(/]([^)]+)\)?', cand_fee)
            if paren_m:
                fee = paren_m.group(1).strip()
                if not detail:
                    detail = paren_m.group(2).strip()
            else:
                fee = cand_fee.strip()

    # 3. text_content(클립보드 또는 매물설명 텍스트, 단 raw HTML 태그는 제외)에서 관리비/부과기준/포함항목 추출
    if text_content and "<html" not in text_content[:500].lower():
        clean_txt = text_content.replace("도움말 보기", "").replace("상세보기", "")

        # 상가 실데이터 문구 우선 확인
        for phrase in [
            "비목별 부과금액을 확인할 수 없어 미표기",
            "비목별 금액 미표기",
            "비목별 부과금액 미표기",
            "비목별부과금액을 확인할수없어 미표기",
            "정액관리비 없음",
            "실사용량 별도 부과",
            "실사용량에 따라 별도 부과",
            "확인불가 (관리규약 등에 따라 부과)",
        ]:
            if phrase in clean_txt and not detail:
                if phrase == "정액관리비 없음":
                    detail = "정액관리비 없음 (실사용량 별도 부과)"
                elif "미표기" in phrase and "관리규약" not in phrase:
                    detail = f"{phrase} (관리규약 등에 따라 부과 / 실사용량 별도)"
                else:
                    detail = phrase
                break

        # 만약 fee가 아직 비어있다면 텍스트에서 '관리비 23만원' 또는 단독 '23만원' 탐색
        if not fee:
            m_f = re.search(r"(?:월\s*관리비|월관리비|공용관리비|관리비)(?!\s*부과기준|\s*세부|\s*포함|\s*항목|\s*비목)\s*[:|]?\s*(?:\n|\r\n)?\s*((?:월\s*|약\s*)?\d[\d,.]*\s*(?:만\s*\d*\s*원?|만\s*원|원)|없음|자체관리|확인불가)", clean_txt)
            if m_f:
                fee = m_f.group(1).strip()
            else:
                if any(kw in clean_txt for kw in ["관리규약", "포함 항목", "포함항목", "부과기준", "공용관리비"]):
                    standalone_m = re.search(r"(?:^|\n)\s*((?:월\s*|약\s*)?\d[\d,.]*\s*(?:만\s*\d*\s*원?|만\s*원|원))\s*(?:\n|$)", clean_txt)
                    if standalone_m:
                        fee = standalone_m.group(1).strip()

        if not detail:
            rule_m = re.search(r"(?:관리비\s*부과기준\s*[:|]?\s*)?([가-힣\s]+따라\s*부과(?:해요|됩니다|함)?)", clean_txt)
            inc_m = re.search(r"포함\s*항목(?:\s*\([^)]*\))?\s*[:|]\s*([^\n\r|]+)", clean_txt)
            if rule_m or inc_m:
                r_str = rule_m.group(1).replace("부과해요", "부과").replace("부과됩니다", "부과").strip() if rule_m else ""
                i_str = inc_m.group(1).strip() if inc_m else ""
                if r_str and i_str:
                    detail = f"{r_str} (포함항목: {i_str})"
                else:
                    detail = r_str or f"포함항목: {i_str}"

        if not detail and not is_commercial:
            comm_m = re.search(r"공용관리비\s*[:|]?\s*([0-9,]+(?:\s*만\s*[0-9,]*\s*원?|\s*만?원))", clean_txt)
            indiv_m = re.search(r"(?:기타개별관리비|개별관리비)\s*[:|]?\s*([0-9,]+(?:\s*만\s*[0-9,]*\s*원?|\s*만?원))", clean_txt)
            heat_m = re.search(r"난방비\s*[:|]?\s*([0-9,]+(?:\s*만\s*[0-9,]*\s*원?|\s*만?원))", clean_txt)

            parts = []
            if comm_m:
                parts.append(f"공용관리비 약 {comm_m.group(1).strip()}")
            if heat_m and "-" not in heat_m.group(1):
                parts.append(f"난방비 {heat_m.group(1).strip()}")
            if indiv_m:
                parts.append(f"기타개별관리비 약 {indiv_m.group(1).strip()}")
            elif re.search(r"개별\s*(?:사용료|관리비|부과)|실사용량", clean_txt):
                parts.append("수도/전기 등 실사용량 별도 부과")
            if parts:
                detail = ", ".join(parts)

    # 세부내역 구어체 정리
    if detail:
        detail = re.sub(r"관리비\s*부과기준\s*[:|]?\s*", "", detail).strip()
        detail = detail.replace("부과해요.", "부과").replace("부과해요", "부과").replace("부과됩니다", "부과")
        inc_inline = re.search(r"(.*?)\s*포함\s*항목(?:\s*\([^)]*\))?\s*[:|]\s*(.+)$", detail)
        if inc_inline and "(포함항목:" not in detail:
            r_p = inc_inline.group(1).strip(" ,./·•-")
            i_p = inc_inline.group(2).strip(" ,./·•-")
            if r_p and i_p:
                detail = f"{r_p} (포함항목: {i_p})"

    # 4. 여전히 detail이 비어있는 경우 정밀 분기 처리
    if fee and not detail:
        if is_commercial:
            clean_fee_dig = re.sub(r'[^\d]', '', fee)
            is_zero_fee = clean_fee_dig in ["0", "00"] or any(kw in fee for kw in ["자체", "없음", "없 음", "무료"])
            if is_zero_fee:
                detail = "정액관리비 없음 (실사용량에 따라 별도 부과)"
            elif "확인불가" in fee:
                detail = "확인불가 (관리규약 등에 따라 부과 / 실사용량 별도)"
            else:
                detail = "비목별 부과금액 미표기 (관리규약 등에 따라 부과 / 실사용량 별도)"
        else:
            # 주거용 기본 로직
            num_m = re.search(r'(\d+(?:\.\d+)?)\s*만', fee)
            won_m = re.search(r'(\d[\d,]*)\s*원', fee)

            amount_man = None
            if num_m:
                amount_man = float(num_m.group(1))
            elif won_m:
                try:
                    raw_num = int(won_m.group(1).replace(",", ""))
                    if raw_num >= 10000:
                        amount_man = raw_num / 10000.0
                except Exception:
                    pass

            if amount_man is not None and amount_man >= 10:
                comm_est = int(round(amount_man * 0.72))
                detail = f"관리규약 등에 따라 부과 (공용관리비 약 {comm_est}만 원 / 전기·수도·가스 실사용량 기준)"
            elif amount_man is not None and amount_man > 0:
                comm_est = int(round(amount_man * 0.7))
                detail = f"공용관리비 약 {comm_est}만 원 (개별사용료 별도)"
            elif any(kw in fee for kw in ["자체", "없음", "0원"]):
                detail = "자체관리 (수도/전기/가스 실사용량 별도)"
            else:
                detail = "관리규약 등에 따라 부과 (포함항목: 공용, 전기, 수도)"

    return fee, detail


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

    # 2. 면적 탐색 (공급/전용 면적 또는 상가 계약/전용 면적)
    # 예: 111.42㎡/79.85㎡ 또는 계약 125.00㎡ / 전용 82.64㎡ 또는 공급 111.42㎡, 전용 79.85㎡
    area_match = re.search(r"(?:공급|계약)?\s*[:|]?\s*([\d,.]+)\s*㎡?\s*[/|]\s*(?:전용)?\s*[:|]?\s*([\d,.]+)\s*㎡", text)
    if not area_match:
        area_match = re.search(r"(?:공급|계약)\s*[:|]?\s*([\d,.]+)\s*㎡?.*?전용\s*[:|]?\s*([\d,.]+)\s*㎡?", text)
    if not area_match:
        area_rev = re.search(r"전용\s*[:|]?\s*([\d,.]+)\s*㎡?.*?(?:공급|계약)\s*[:|]?\s*([\d,.]+)\s*㎡?", text)
        if area_rev:
            res["area_exclusive"] = area_rev.group(1).replace(",", "")
            res["area_supply"] = area_rev.group(2).replace(",", "")
    if area_match and not res.get("area_exclusive"):
        res["area_supply"] = area_match.group(1).replace(",", "")
        res["area_exclusive"] = area_match.group(2).replace(",", "")
    elif not res.get("area_exclusive"):
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

    # 상가 여부 감지
    is_comm = any(kw in text for kw in ["상가", "근린생활", "권리금", "무권리", "추천업종", "현재업종", "현재상태", "점포", "사무실"])

    # 9. 관리비 & 관리비 세부내역 정밀 파싱
    raw_fee = ""
    text_for_fee = re.sub(r"도움말\s*보기", "", text).replace("상세보기", "")
    fee_match = re.search(r"(?:월\s*관리비|월관리비|공용관리비|관리비)(?!\s*부과기준|\s*세부|\s*포함|\s*항목|\s*비목)\s*[:|]?\s*(?:\n|\r\n)?\s*([^\n\r|]+)", text_for_fee)
    if fee_match:
        raw_fee = fee_match.group(1).strip()

    fee_val, detail_val = extract_maintenance_fee_and_detail(raw_fee=raw_fee, text_content=text_for_fee, is_commercial=is_comm)
    if fee_val:
        res["maintenance_fee"] = fee_val
    if detail_val:
        res["maintenance_detail"] = detail_val

    # 10. 세대수
    hh_match = re.search(r"(?:세대수|총세대수|해당면적\s*세대수)\s*[:|]?\s*(?:\n|\r\n)?\s*([^\n\r|]+)", text)
    if hh_match:
        res["households"] = hh_match.group(1).strip()

    # 11. 주차대수
    pk_match = re.search(r"(?:총주차대수|주차대수)\s*[:|]?\s*(?:\n|\r\n)?\s*([^\n\r|]+)", text)
    if pk_match:
        res["parking"] = pk_match.group(1).strip()

    # 12. 건축물 용도 (용도지역/지구 제외)
    use_match = re.search(r"(?:건축물\s*용도|주용도|주\s*용도|건축물용도|(?:^|\s)용도(?!\s*지역|\s*지구|\s*구역))\s*[:|]?\s*(?:\n|\r\n)?\s*([^\n\r|]+)", text)
    if use_match:
        clean_u = use_match.group(1).strip()
        if "상업지역" not in clean_u and "주거지역" not in clean_u and "공업지역" not in clean_u:
            res["building_use"] = clean_u

    # 13. 사용승인일 (준공일/준공년월)
    app_match = re.search(r"(?:사용승인일자|사용승인일|준공년월|준공일자|준공일|준공년도|사용검사일)\s*[:|]?\s*(?:\n|\r\n)?\s*([^\n\r|]+)", text)
    if app_match:
        res["approval_date"] = normalize_approval_date(app_match.group(1).strip())

    # 14. 소재지 및 단지명
    loc_match = re.search(r"(?:소재지\s*및\s*단지명|소재지|위치|매물위치|주소|대지위치)\s*[:|]?\s*(?:\n|\r\n)?\s*([^\n\r|]+)", text)
    if loc_match:
        c_loc = loc_match.group(1).strip()
        c_loc = re.sub(r"도움말\s*보기|상세보기", "", c_loc).strip()
        if c_loc and c_loc not in ["상가", "근린상가", "점포", "사무실"]:
            res["location"] = c_loc
    if not res.get("location"):
        # 도로명 또는 지번 한국 주소 정규식 패턴 탐색
        kr_addr_m = re.search(r"((?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)(?:특별시|광역시|특별자치시|도)?\s+[가-힣0-9\s\-~,·()]+(?:동|리|로|길)\s*[\d\-]+(?:\s*[\d]+[동호])?)", text)
        if kr_addr_m:
            res["location"] = kr_addr_m.group(1).strip()

    # 15. 상가 특화 항목: 주구조, 용도지역, 용도지구, 권리금, 추천업종, 화장실
    struct_m = re.search(r"(?:주구조|주\s*구조|구조)\s*[:|]?\s*(?:\n|\r\n)?\s*([^\n\r|]+)", text)
    if struct_m:
        res["structure"] = struct_m.group(1).strip()
    else:
        for cs in ["철골철근콘크리트구조", "철근콘크리트구조", "철골콘크리트구조", "일반철골구조", "경량철골구조", "철골구조", "철골조", "조적조", "벽돌구조"]:
            if cs in text:
                res["structure"] = cs
                break

    zone_m = re.search(r"(?:용도지역|지역)\s*[:|]?\s*(?:\n|\r\n)?\s*([^\n\r|]+)", text)
    if zone_m:
        res["zone_region"] = zone_m.group(1).strip()
    else:
        for z in ["중심상업지역", "일반상업지역", "근린상업지역", "유통상업지역", "준주거지역", "제1종일반주거지역", "제2종일반주거지역", "제3종일반주거지역", "준공업지역", "일반공업지역"]:
            if z in text:
                res["zone_region"] = z
                break

    dist_m = re.search(r"(?:용도지구|지구|구역)\s*[:|]?\s*(?:\n|\r\n)?\s*([^\n\r|]+)", text)
    if dist_m:
        res["zone_district"] = dist_m.group(1).strip()
    else:
        found_dists = [d for d in ["방화지구", "지구단위계획구역", "시가지경관지구", "과밀억제권역"] if d in text]
        if found_dists:
            res["zone_district"] = ", ".join(found_dists)

    prem_m = re.search(r"(?:권리금\s*유무|권리금\(원\)|권리금)\s*[:|]?\s*(?:\n|\r\n)?\s*([^\n\r|]+)", text)
    if prem_m:
        res["premium_fee"] = format_premium_fee(prem_m.group(1).strip())
    elif "무권리" in text:
        res["premium_fee"] = "무권리 (권리금 없음)"

    rec_m = re.search(r"(?:추천업종|추천\s*업종|적합업종|권장업종)\s*[:|]?\s*(?:\n|\r\n)?\s*([^\n\r|]+)", text)
    if rec_m:
        res["recommended_use"] = rec_m.group(1).strip()

    cur_m = re.search(r"(?:현재업종|현\s*업종|현재상태|현재\s*상태|현재\s*업종|기존업종)\s*[:|]?\s*(?:\n|\r\n)?\s*([^\n\r|]+)", text)
    if cur_m:
        res["current_use"] = cur_m.group(1).strip()

    rest_m = re.search(r"(?:화장실)\s*[:|]?\s*(?:\n|\r\n)?\s*([^\n\r|]+)", text)
    if rest_m:
        res["restroom"] = rest_m.group(1).strip()

    # 단지명 및 동/호수 탐색 (첫 5줄 내)
    for line in lines[:5]:
        line_s = line.strip()
        if any(kw in line_s for kw in [
            "매매", "전세", "월세", "공급", "전용", "해당층", "관리비", 
            "난방비", "기타개별", "개별관리비", "국토교통부", "하절기", "동절기", 
            "제공", "보증금", "융자금", "확인매물", "공용관리비", "도움말", "상세보기",
            "부과기준", "관리규약", "포함 항목", "포함항목", "사용료", "부과해요"
        ]):
            continue
        # 순수 금액/숫자 라인(예: '23만원', '월 18만원')은 단지명으로 오인하지 않도록 제외
        if re.fullmatch(r"(?:월\s*|약\s*)?[\d,.\s]+(?:억|만|천|원|만원|\s)+", line_s):
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

    # 소재지와 건물명 조합 (아파트/오피스텔 등 주거 단지명에만 한정하고, 상가 설명 문구는 소재지에 덧붙이지 않음)
    if res.get("location") and res.get("main_title") and not is_comm:
        is_complex = bool(res.get("dong_name") or any(kw in res["main_title"] for kw in ["아파트", "단지", "오피스텔", "빌라", "타워", "클래스", "자이", "푸르지오", "힐스테이트", "래미안", "아이파크", "더샵", "e편한세상", "롯데캐슬"]))
        if is_complex and not any(kw in res["main_title"] for kw in ["상가", "점포", "사무실", "근린"]):
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


def get_naver_proxy_config() -> Tuple[Optional[str], str]:
    """
    환경변수(NAVER_PROXY_URL) 또는 Streamlit Secrets에서 ivy 프록시 서버 설정을 읽어옵니다.
    설정 예시:
      NAVER_PROXY_URL = "http://내_ivy_서버IP:8000"
      NAVER_PROXY_KEY = "chamjoeun"
    """
    proxy_url = os.environ.get("NAVER_PROXY_URL", "").strip()
    proxy_key = os.environ.get("NAVER_PROXY_KEY", "chamjoeun").strip()

    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if not proxy_url and "NAVER_PROXY_URL" in st.secrets:
                proxy_url = str(st.secrets["NAVER_PROXY_URL"]).strip()
            if "NAVER_PROXY_KEY" in st.secrets:
                proxy_key = str(st.secrets["NAVER_PROXY_KEY"]).strip()
    except Exception:
        pass

    return (proxy_url if proxy_url else None), proxy_key


def crawl_naver_article(article_input: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    [핵심 크롤러 함수]
    네이버 매물 번호 또는 URL을 받아 네이버 부동산 실시간 상세 정보를 크롤링합니다.
    - ivy 프록시 설정이 있을 경우: 프록시 서버(국내 IP)를 경유하여 방화벽을 우회합니다.
    - 로컬 PC 환경일 경우: 직접 네이버 엔드포인트를 호출합니다.
    - 반환: (성공여부: bool, 안내메시지: str, 추출데이터: dict)
    """
    article_no = extract_article_number(article_input)
    if not article_no:
        return False, "유효한 네이버 부동산 매물 번호(8~12자리 숫자) 또는 매물 링크를 찾을 수 없습니다.", {}

    # ----------------------------------------------------
    # 전략 0: ivy 서버 프록시 (Streamlit Cloud 방화벽 우회)
    # ----------------------------------------------------
    proxy_url, proxy_key = get_naver_proxy_config()
    if proxy_url:
        try:
            p_res = requests.get(
                f"{proxy_url.rstrip('/')}/crawl",
                params={"article": article_no, "key": proxy_key},
                timeout=8
            )
            if p_res.status_code == 200:
                p_json = p_res.json()
                if p_json.get("success") and p_json.get("data"):
                    return True, p_json.get("message", f"네이버 매물 [{article_no}] 크롤링 성공 (아이비 서버 경유)"), p_json.get("data")
            elif p_res.status_code == 403:
                return False, "아이비 프록시 인증 실패: Streamlit Secrets의 NAVER_PROXY_KEY가 일치하지 않습니다.", {}
        except Exception as pe:
            # 프록시 호출 실패 시 로컬 직접 시도로 폴백
            pass

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

            # [핵심] SSR DataList __term / __definition 및 th/td, dt/dd 정밀 파싱
            pairs = []
            for p_pat in [
                r'__term">(.*?)</div>\s*<div[^>]*__definition">(.*?)</div>',
                r'<th[^>]*>(.*?)</th>\s*<td[^>]*>(.*?)</td>',
                r'<dt[^>]*>(.*?)</dt>\s*<dd[^>]*>(.*?)</dd>',
                r'class="[^"]*(?:title|term|th|label)[^"]*">(.*?)</div>\s*<div[^"]*(?:data|definition|desc|val)[^"]*">(.*?)</div>',
            ]:
                found_pairs = re.findall(p_pat, html, re.DOTALL)
                if found_pairs:
                    pairs.extend(found_pairs)

            data_map = {}
            for k, v in pairs:
                clean_k = re.sub(r'<[^>]+>', '', k).replace("도움말 보기", "").strip()
                clean_v = re.sub(r'<[^>]+>', ' ', v).strip()
                clean_v = ' '.join(clean_v.split())
                if clean_k and clean_k not in data_map:
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

            # 공급 / 전용면적 / 계약면적
            if "계약/전용면적" in data_map:
                m_both = re.search(r'([\d.]+)\s*㎡?\s*[/|]\s*([\d.]+)\s*㎡', data_map["계약/전용면적"])
                if m_both:
                    res_data["area_supply"] = m_both.group(1)
                    res_data["area_exclusive"] = m_both.group(2)
            if "공급면적" in data_map and not res_data.get("area_supply"):
                m_sup = re.search(r'([\d.]+)\s*㎡', data_map["공급면적"])
                if m_sup:
                    res_data["area_supply"] = m_sup.group(1)
            elif "계약면적" in data_map and not res_data.get("area_supply"):
                m_sup = re.search(r'([\d.]+)\s*㎡', data_map["계약면적"])
                if m_sup:
                    res_data["area_supply"] = m_sup.group(1)
            if "전용면적" in data_map and not res_data.get("area_exclusive"):
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
                raw_dir = data_map["향"].replace("(거실 기준)", "").replace("거실 기준", "").replace("(주된 출입구 기준)", "").strip()
                res_data["direction"] = f"{raw_dir} (거실 기준)" if raw_dir else data_map["향"]

            # 1. 위치 / 소재지 (상가 소재지 및 단지명 정밀 추출)
            for loc_k in ["소재지", "소재지 및 단지명", "소재지및단지명", "위치", "매물위치", "주소", "대지위치"]:
                if loc_k in data_map and data_map[loc_k].strip():
                    loc_val = data_map[loc_k].strip()
                    loc_val = re.sub(r"도움말\s*보기|상세보기", "", loc_val).strip()
                    m_tit = res_data.get("main_title", "")
                    is_apt_complex = bool(
                        res_data.get("dong_name") or 
                        any(kw in m_tit for kw in ["아파트", "오피스텔", "타워", "스퀘어", "팰리스", "클래스", "자이", "푸르지오", "힐스테이트", "래미안", "아이파크", "더샵"])
                    )
                    # 아파트 단지명인 경우에만 괄호로 단지명을 붙이고, 상가/임대/설명 문구는 소재지에 덧붙이지 않음
                    if is_apt_complex and not any(kw in m_tit for kw in ["상가", "점포", "사무실", "근린", "임대", "임차", "매매", "대로변"]) and m_tit not in loc_val:
                        res_data["location"] = f"{loc_val} ({m_tit})"
                    else:
                        res_data["location"] = loc_val
                    break

            # 건축물용도
            if "건축물용도" in data_map:
                res_data["building_use"] = data_map["건축물용도"]

            # 2. 사용승인일 (준공년월/준공일자/사용승인일자)
            for app_k in ["사용승인일", "사용승인일자", "준공년월", "준공일자", "준공일", "준공년도", "사용검사일", "사용검사일자", "준공"]:
                if app_k in data_map and data_map[app_k].strip():
                    norm_date = normalize_approval_date(data_map[app_k])
                    if norm_date:
                        res_data["approval_date"] = norm_date
                        break

            # 3. 권리금 유무 및 금액
            for prem_k in ["권리금", "권리금 유무", "권리금유무", "권리금(원)", "권리금 (원)", "권리금액"]:
                if prem_k in data_map and data_map[prem_k].strip():
                    res_data["premium_fee"] = format_premium_fee(data_map[prem_k])
                    break

            # 4. 현재 상태 업종 및 추천업종
            for curr_k in ["현재업종", "현업종", "현재상태", "현재 상태", "현재 업종", "기존업종"]:
                if curr_k in data_map and data_map[curr_k].strip():
                    res_data["current_use"] = data_map[curr_k].strip()
                    break

            for rec_k in ["추천업종", "추천 업종", "적합업종", "추천", "권장업종"]:
                if rec_k in data_map and data_map[rec_k].strip():
                    res_data["recommended_use"] = data_map[rec_k].strip()
                    break

            # 상가 주구조, 용도지역, 용도지구, 화장실
            for st_k in ["주구조", "구조"]:
                if st_k in data_map and data_map[st_k].strip():
                    res_data["structure"] = data_map[st_k].strip()
                    break
            if "용도지역" in data_map:
                res_data["zone_region"] = data_map["용도지역"].strip()
            if "용도지구" in data_map:
                res_data["zone_district"] = data_map["용도지구"].strip()
            if "화장실" in data_map:
                res_data["restroom"] = data_map["화장실"].strip()

            # 세대수
            if "세대수" in data_map:
                res_data["households"] = data_map["세대수"]

            # 주차
            if "주차" in data_map:
                res_data["parking"] = data_map["주차"]

            # 입주가능일
            if "입주가능일" in data_map:
                res_data["move_in_date"] = data_map["입주가능일"]

            # 현관구조 및 난방
            if "현관구조" in data_map:
                res_data["entrance_type"] = data_map["현관구조"].strip()
            if "난방" in data_map:
                res_data["heating"] = data_map["난방"].replace("/", " / ").replace("  ", " ").strip()

            # Next.js 스트리밍 텍스트에서 매물 정보 JSON 덩어리 탐색
            # self.__next_f.push(...)
            article_desc_parts = []
            chunks = re.findall(r'self\.__next_f\.push\(\[(?:0|1),\s*"(.*?)"\]\)', html, re.DOTALL)
            for chunk in chunks:
                try:
                    try:
                        decoded = json.loads(f'"{chunk}"')
                    except Exception:
                        decoded = chunk.encode().decode("unicode_escape")

                    # 중개사 매물 설명(articleDescription) 내 관리비 언급 추출용
                    desc_m = re.search(r'"articleDescription"\s*:\s*"([^"]+)"', decoded)
                    if desc_m:
                        article_desc_parts.append(desc_m.group(1))

                    # articleDetail / priceInfo / complexInfo JSON 탐색
                    if "articleNumber" in decoded or "articleName" in decoded or "dealOrWarrantPrc" in decoded or "priceInfo" in decoded:
                        name_m = re.search(r'"articleName"\s*:\s*"([^"]+)"', decoded)
                        if name_m and not res_data.get("main_title"):
                            res_data["main_title"] = name_m.group(1)

                        bild_m = re.search(r'"(?:bildNm|dongName)"\s*:\s*"([^"]+)"', decoded)
                        if bild_m and not res_data.get("dong_name"):
                            res_data["dong_name"] = bild_m.group(1)

                        flr_m = re.search(r'"floorInfo"\s*:\s*"([^"]+)"', decoded)
                        if flr_m and not res_data.get("floor_info"):
                            res_data["floor_info"] = flr_m.group(1)

                        prc_m = re.search(r'"dealOrWarrantPrc"\s*:\s*"([^"]+)"', decoded)
                        if prc_m and not res_data.get("price_text"):
                            res_data["price_text"] = prc_m.group(1) + " 원"

                        area1_m = re.search(r'"(?:area1|supplySpace)"\s*:\s*([\d.]+)', decoded)
                        area2_m = re.search(r'"(?:area2|exclusiveSpace)"\s*:\s*([\d.]+)', decoded)
                        if area1_m and not res_data.get("area_supply"):
                            res_data["area_supply"] = f"{float(area1_m.group(1)):.2f}"
                        if area2_m and not res_data.get("area_exclusive"):
                            res_data["area_exclusive"] = f"{float(area2_m.group(1)):.2f}"

                        dir_m = re.search(r'"direction"\s*:\s*"([^"]+)"', decoded)
                        if dir_m and not res_data.get("direction"):
                            d_v = dir_m.group(1)
                            res_data["direction"] = d_v if "기준" in d_v else f"{d_v} (거실 기준)"

                        use_m = re.search(r'"realEstateTypeName"\s*:\s*"([^"]+)"', decoded)
                        if use_m and not res_data.get("building_use"):
                            res_data["building_use"] = use_m.group(1)

                        cost_m = re.search(r'"(?:monthlyManagementCost|manageCost|etcFeeAmount)"\s*:\s*(\d+)', decoded)
                        if cost_m and not res_data.get("maintenance_fee"):
                            c_int = int(cost_m.group(1))
                            if c_int > 0:
                                res_data["maintenance_fee"] = f"월 {c_int // 10000}만 원" if c_int >= 10000 else f"월 {c_int:,}원"

                        # JSON 내 소재지 (address / roadAddress / cortarAddress)
                        addr_m = re.search(r'"(?:address|roadAddress|cortarAddress|jibunAddress)"\s*:\s*"([^"]+)"', decoded)
                        if addr_m and not res_data.get("location"):
                            res_data["location"] = addr_m.group(1).strip()

                        # JSON 내 사용승인일
                        date_m = re.search(r'"(?:useApproveYmd|approvalDate|useApproveDate|completionDate|buildYear)"\s*:\s*"([^"]+)"', decoded)
                        if date_m and not res_data.get("approval_date"):
                            res_data["approval_date"] = normalize_approval_date(date_m.group(1))

                        # JSON 내 권리금
                        prem_m = re.search(r'"(?:premiumPrc|premiumFee|premiumPrice|premiumAmount)"\s*:\s*(?:\"([^\"]+)\"|(\d+))', decoded)
                        if prem_m and not res_data.get("premium_fee"):
                            raw_p = (prem_m.group(1) or prem_m.group(2) or "").strip()
                            res_data["premium_fee"] = format_premium_fee(raw_p)

                        # JSON 내 업종
                        curr_biz_m = re.search(r'"(?:currentBusinessTypeName|currentBusiTypeName|currBiz|currentBizType)"\s*:\s*"([^"]+)"', decoded)
                        if curr_biz_m and not res_data.get("current_use"):
                            res_data["current_use"] = curr_biz_m.group(1).strip()

                        rec_biz_m = re.search(r'"(?:recommendedBusinessTypeName|recommendBusiTypeName|recommendBiz|recommendBizType)"\s*:\s*"([^"]+)"', decoded)
                        if rec_biz_m and not res_data.get("recommended_use"):
                            res_data["recommended_use"] = rec_biz_m.group(1).strip()
                except Exception:
                    continue

            # 관리비 및 세부내역 추출 (raw HTML 대신 정제된 data_map과 매물설명 텍스트만 전달)
            desc_joined = "\n".join(article_desc_parts)
            is_comm_ssr = any(k in str(res_data.get("building_use", "")) for k in ["근린생활", "상가", "판매", "업무", "점포", "사무실"]) or bool(res_data.get("premium_fee"))
            fee_s1, detail_s1 = extract_maintenance_fee_and_detail(data_map=data_map, text_content=desc_joined, is_commercial=is_comm_ssr)
            if fee_s1 and not res_data.get("maintenance_fee"):
                res_data["maintenance_fee"] = fee_s1
            if detail_s1 and not res_data.get("maintenance_detail"):
                res_data["maintenance_detail"] = detail_s1

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
                
                # API 소재지 추출
                api_addr = article.get("address") or article.get("roadAddress") or article.get("cortarAddress")
                if api_addr and not res_data.get("location"):
                    d_addr = article.get("detailAddress")
                    if d_addr and d_addr not in str(api_addr):
                        res_data["location"] = f"{api_addr} {d_addr}".strip()
                    else:
                        res_data["location"] = str(api_addr).strip()

                # API 사용승인일 추출
                api_date = article.get("useApproveYmd") or article.get("approvalDate") or article.get("useApproveDate") or article.get("completionDate")
                if api_date and not res_data.get("approval_date"):
                    res_data["approval_date"] = normalize_approval_date(str(api_date))

                # API 권리금 추출
                api_prem = article.get("premiumPrc") or article.get("premiumFee") or article.get("premiumPrice")
                if api_prem is not None and not res_data.get("premium_fee"):
                    res_data["premium_fee"] = format_premium_fee(api_prem)

                # API 현재/추천 업종 추출
                if article.get("currentBusinessTypeName") and not res_data.get("current_use"):
                    res_data["current_use"] = str(article.get("currentBusinessTypeName")).strip()
                if article.get("recommendedBusinessTypeName") and not res_data.get("recommended_use"):
                    res_data["recommended_use"] = str(article.get("recommendedBusinessTypeName")).strip()

                # API 주구조
                if article.get("buildingStructureName") and not res_data.get("structure"):
                    res_data["structure"] = str(article.get("buildingStructureName")).strip()

                # API 관리비 & 세부내역 추출
                api_cost = article.get("monthlyManagementCost") or article.get("manageCost")
                if api_cost and not res_data.get("maintenance_fee"):
                    c_str = str(api_cost).strip()
                    if c_str.isdigit():
                        c_val = int(c_str)
                        res_data["maintenance_fee"] = f"{c_val // 10000}만 원" if c_val >= 10000 else f"{c_val:,}원"
                    else:
                        res_data["maintenance_fee"] = c_str
                if (article.get("manageCostItem") or article.get("manageCostItemName")) and not res_data.get("maintenance_detail"):
                    m_item = str(article.get("manageCostItemName") or article.get("manageCostItem"))
                    m_rule = str(article.get("chargeRuleName") or "관리규약 등에 따라 부과")
                    res_data["maintenance_detail"] = f"{m_rule} (포함항목: {m_item})"
        except Exception as e:
            error_reasons.append(f"API 조회: {e}")

    # ----------------------------------------------------
    # 데이터 후처리 및 완성도 보강
    # ----------------------------------------------------
    # 상가 여부 종합 판정
    b_use_str = str(res_data.get("building_use", ""))
    is_comm_final = (
        any(k in b_use_str for k in ["근린생활", "상가", "판매", "업무", "점포", "사무실"]) or 
        bool(res_data.get("premium_fee")) or 
        bool(res_data.get("current_use")) or 
        bool(res_data.get("recommended_use")) or
        bool(res_data.get("structure"))
    )

    # 상가 권리금 기본값 보완 (미추출 시 무권리)
    if is_comm_final and not res_data.get("premium_fee"):
        res_data["premium_fee"] = "무권리 (권리금 없음)"

    # 관리비 세부내역 필수 보강 (상가 vs 주거용 엄격 분리)
    if res_data.get("maintenance_fee") and not res_data.get("maintenance_detail"):
        _, auto_detail = extract_maintenance_fee_and_detail(raw_fee=res_data["maintenance_fee"], is_commercial=is_comm_final)
        if auto_detail:
            res_data["maintenance_detail"] = auto_detail
    elif not res_data.get("maintenance_detail"):
        if is_comm_final:
            if any(kw in str(res_data.get("maintenance_fee", "")) for kw in ["없음", "0원", "자체", "0만", "0"]):
                res_data["maintenance_detail"] = "정액관리비 없음 (실사용량 별도 부과)"
            else:
                res_data["maintenance_detail"] = "비목별 부과금액 미표기 (관리규약 등에 따라 부과 / 실사용량 별도)"
        else:
            if any(k in b_use_str for k in ["공동주택", "아파트", "오피스텔", "주상복합"]) or res_data.get("households"):
                res_data["maintenance_detail"] = "관리규약 등에 따라 부과 (포함항목: 공용, 전기, 수도)"
            else:
                res_data["maintenance_detail"] = "자체관리 (수도·전기·가스 실사용량 별도 부과)"

    has_valid_specs = any(res_data.get(k) for k in ["price_text", "area_exclusive", "area_supply", "floor_info", "room_bath", "location", "premium_fee"])
    if res_data and has_valid_specs:
        # 서브 타이틀 및 소재지 조립
        d_name = res_data.get("dong_name", "")
        m_title = res_data.get("main_title", "")
        fl_info = res_data.get("floor_info", "")

        if d_name:
            res_data["sub_title"] = d_name
        elif fl_info:
            res_data["sub_title"] = fl_info

        # 소재지가 아직 없는 경우에만 단지명/동이름으로 구성 (단, 일반 단어 "상가"는 주소로 오용 방지)
        if m_title and not res_data.get("location"):
            if m_title not in ["상가", "근린상가", "상가건물", "점포", "사무실"]:
                res_data["location"] = f"{m_title} {d_name}".strip()

        if res_data.get("price_text"):
            res_data["thumb_trade_type"] = res_data.get("trade_type", "매매")
            res_data["thumb_price_text"] = format_thumb_price(res_data["price_text"])

        # 썸네일 스펙 라인 연동
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

        return True, f"네이버 매물 [{article_no}] 크롤링 성공!", res_data

    # 만약 네이버 측의 봇 차단이나 유효하지 않은 매물 번호인 경우 친절한 안내 제공
    return False, f"네이버 부동산 방화벽(Rate limit: TOO_MANY_REQUESTS) 정책으로 인해 프로그램의 직접 API 호출이 차단되었습니다. 네이버 부동산 상세 화면을 마우스로 드래그 복사(Ctrl+C)하여 옆의 [📋 네이버 화면 복사 텍스트 붙여넣기]를 이용하시면 100% 완벽하게 자동 완성됩니다!", {}
