"""
공적서류(건축물대장, 토지대장, 토지이용계획확인원) 자동 분석 및 16대 점검항목 데이터 추출 모듈
- 건축물대장 (집합건축물대장 전유부/표제부, 일반건축물대장)
- 토지대장 / 임야대장
- 토지이용계획확인서
"""

import re
import io
from typing import Dict, Any, Tuple, Optional

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


def extract_text_from_pdf(pdf_file) -> str:
    """PDF 파일(BytesIO 또는 파일경로)에서 전체 텍스트를 추출합니다."""
    if not HAS_PDFPLUMBER:
        raise ImportError("pdfplumber 라이브러리가 설치되어 있지 않습니다.")
    
    text_content = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_content.append(t)
            # 테이블에서도 텍스트 추출 보조
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    clean_row = [str(c).strip() for c in row if c is not None and str(c).strip()]
                    if clean_row:
                        text_content.append(" | ".join(clean_row))
                        
    return "\n".join(text_content)


def identify_document_type(text: str) -> str:
    """텍스트 내용을 분석하여 서류 유형을 자동 감지합니다."""
    text_condensed = text.replace(" ", "")
    
    if "건축물대장" in text_condensed:
        if "전유부" in text_condensed:
            return "건축물대장 (전유부)"
        elif "총괄표제부" in text_condensed:
            return "건축물대장 (총괄표제부)"
        elif "표제부" in text_condensed:
            return "건축물대장 (표제부)"
        return "건축물대장"
    elif "토지대장" in text_condensed or "임야대장" in text_condensed:
        return "토지대장"
    elif "토지이용계획" in text_condensed:
        return "토지이용계획확인원"
    
    return "기타 공적서류"


# 다음 필드 키워드 패턴 (줄바꿈이 없거나 한 줄로 합쳐진 경우 대비)
NEXT_KW = r"(?=\s*(?:대지위치|도로명주소|건축물명칭|명칭|동명칭|호명칭|주용도|용도|층수|사용승인일|준공일|주차장|주차대수|총주차대수|세대수|가구수|구조|소재지|지번|지목|면적|개별공시지가|국토의|$))"


def clean_val(s: str) -> str:
    """추출된 값에서 불필요한 콜론, 공백, 파이프 등을 정리합니다."""
    if not s:
        return ""
    s = s.strip()
    s = re.sub(r"^[:|\-=>\s]+", "", s)
    s = re.sub(r"[:|\-=>\s]+$", "", s)
    return s.strip()


def parse_building_register(text: str) -> Dict[str, Any]:
    """
    건축물대장(표제부/전유부) 텍스트에서 16개 점검항목 데이터 추출
    """
    res = {}

    # 1. 소재지 / 대지위치
    loc_match = re.search(r"(?:대지위치|대지\s*위치|소재지)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    road_match = re.search(r"(?:도로명주소|도로명\s*주소)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    
    building_name = ""
    dong_name = ""
    ho_name = ""
    
    b_match = re.search(r"(?:건축물명칭|건축물\s*명칭)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if b_match:
        building_name = clean_val(b_match.group(1))
    
    d_match = re.search(r"(?:동명칭및호명칭|동명칭|동\s*명칭)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if d_match:
        dong_name = clean_val(d_match.group(1))
        
    h_match = re.search(r"(?:호명칭|호\s*명칭)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if h_match:
        ho_name = clean_val(h_match.group(1))

    full_loc = ""
    if loc_match:
        full_loc = clean_val(loc_match.group(1))
    elif road_match:
        full_loc = clean_val(road_match.group(1))

    # 괄호 결합
    sub_title_parts = [p for p in [building_name, dong_name, ho_name] if p]
    if sub_title_parts:
        if full_loc:
            res["location"] = f"{full_loc} ({' '.join(sub_title_parts)})"
        else:
            res["location"] = " ".join(sub_title_parts)
    elif full_loc:
        res["location"] = full_loc

    # 썸네일 타이틀용
    if building_name:
        res["main_title"] = building_name
    if dong_name or ho_name:
        res["sub_title"] = f"{dong_name} {ho_name}".strip()

    # 2. 전용면적 / 공급면적
    ex_match = re.search(r"(?:전유면적|전유부분\s*면적|전유\s*면적)\s*[:|]?\s*([\d,.]+)", text)
    if not ex_match:
        ex_match = re.search(r"전유(?:부분)?\s*\|\s*([\d,.]+)", text)
    if ex_match:
        res["area_exclusive"] = ex_match.group(1).replace(",", "").strip()

    # 공용면적 및 공급면적 추정
    comm_match = re.search(r"(?:주거공용|공용면적|공용부분)\s*[:|]?\s*([\d,.]+)", text)
    if comm_match and "area_exclusive" in res:
        try:
            ex_val = float(res["area_exclusive"])
            cm_val = float(comm_match.group(1).replace(",", "").strip())
            res["area_supply"] = f"{round(ex_val + cm_val, 2)}"
        except Exception:
            pass
    
    # 만약 연면적이 있다면 (일반건축물대장/단독주택)
    if "area_exclusive" not in res:
        yeon_match = re.search(r"(?:연면적|연\s*면적)\s*[:|]?\s*([\d,.]+)", text)
        if yeon_match:
            val = yeon_match.group(1).replace(",", "").strip()
            res["area_supply"] = val
            res["area_exclusive"] = val

    # 3. 층수 (지하 / 지상, 해당층)
    floor_high_match = re.search(r"지상\s*(\d+)\s*층(?:\s*[/|]?\s*지하\s*(\d+)\s*층)?", text)
    ho_floor_match = re.search(r"(\d+)\s*층\s*\d+\s*호", text)
    
    current_fl = ""
    total_fl = ""
    if floor_high_match:
        total_fl = f"{floor_high_match.group(1)}층"
    
    if ho_floor_match:
        current_fl = f"{ho_floor_match.group(1)}층"
    elif ho_name:
        num_only = re.sub(r"[^\d]", "", ho_name)
        if len(num_only) >= 3:
            current_fl = f"{num_only[:-2]}층"

    if current_fl and total_fl:
        res["floor_info"] = f"{current_fl} / {total_fl}"
    elif total_fl:
        res["floor_info"] = f"총 {total_fl}"
    elif current_fl:
        res["floor_info"] = current_fl

    # 4. 주용도 (건축물 용도)
    use_match = re.search(r"(?:주용도|주\s*용도)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if use_match:
        clean_use = clean_val(use_match.group(1))
        res["building_use"] = clean_use
    else:
        if "아파트" in text:
            res["building_use"] = "공동주택 (아파트)"
        elif "오피스텔" in text:
            res["building_use"] = "업무시설 (오피스텔)"
        elif "단독주택" in text:
            res["building_use"] = "단독주택"
        elif "근린생활시설" in text:
            res["building_use"] = "제2종근린생활시설"

    # 5. 사용승인일 (준공일)
    date_match = re.search(r"(?:사용승인일|사용\s*승인일|준공일)\s*[:|]?\s*(\d{4}[.\-년\s]+\d{1,2}[.\-월\s]+\d{1,2}일?)", text)
    if date_match:
        raw_date = date_match.group(1).strip()
        date_nums = re.findall(r"\d+", raw_date)
        if len(date_nums) >= 3:
            res["approval_date"] = f"{date_nums[0]}년 {int(date_nums[1]):02d}월 {int(date_nums[2]):02d}일"
        else:
            res["approval_date"] = raw_date

    # 6. 세대수 / 가구수
    hh_match = re.search(r"(?:세대수|세대\s*수)\s*[:|]?\s*([\d,]+)\s*세대", text)
    if hh_match:
        res["households"] = f"총 {hh_match.group(1)}세대"
    else:
        ga_match = re.search(r"(?:가구수|가구\s*수)\s*[:|]?\s*([\d,]+)\s*가구", text)
        if ga_match:
            res["households"] = f"총 {ga_match.group(1)}가구"

    # 7. 주차대수
    park_match = re.search(r"(?:주차장|주차대수|총주차대수)\s*[:|]?\s*(?:옥내\s*[\d,]+\s*대\s*)?(?:옥외\s*[\d,]+\s*대\s*)?총?\s*([\d,]+)\s*대", text)
    if not park_match:
        park_match = re.search(r"총\s*([\d,]+)\s*대", text)
    if park_match:
        res["parking"] = f"총 {park_match.group(1)}대"

    # 8. 구조
    struct_match = re.search(r"(?:주구조|구조)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if struct_match:
        res["structure"] = clean_val(struct_match.group(1))

    # 9. 방수 / 욕실수 추정
    if "area_exclusive" in res:
        try:
            ex = float(res["area_exclusive"])
            if ex >= 80:
                res["room_bath"] = "방 3 / 욕실 2개"
            elif ex >= 50:
                res["room_bath"] = "방 3 / 욕실 1개"
            elif ex >= 30:
                res["room_bath"] = "방 2 / 욕실 1개"
            else:
                res["room_bath"] = "방 1 / 욕실 1개 (원룸)"
        except Exception:
            pass

    return res


def parse_land_register(text: str) -> Dict[str, Any]:
    """
    토지대장 / 임야대장 텍스트에서 데이터 추출
    """
    res = {}
    
    # 1. 소재지 / 지번
    loc_match = re.search(r"(?:소재지|소\s*재\s*지)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    jibun_match = re.search(r"(?:지번|지\s*번)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    
    loc_val = clean_val(loc_match.group(1)) if loc_match else ""
    jibun_val = clean_val(jibun_match.group(1)) if jibun_match else ""
    
    if loc_val and jibun_val:
        res["location"] = f"{loc_val} {jibun_val}"
    elif loc_val:
        res["location"] = loc_val

    # 2. 지목
    jimok_match = re.search(r"(?:지목|지\s*목)\s*[:|]?\s*([가-힣]+)", text)
    jimok = jimok_match.group(1).strip() if jimok_match else "대"
    res["building_use"] = f"토지 (지목: {jimok})"
    res["feature_text"] = f"지목 '{jimok}' 특급 추천 토지"

    # 3. 면적 (㎡)
    area_match = re.search(r"(?:면적|면\s*적)\s*\(?㎡?\)?\s*[:|]?\s*([\d,.]+)", text)
    if area_match:
        m2_str = area_match.group(1).replace(",", "").strip()
        res["area_supply"] = m2_str
        res["area_exclusive"] = m2_str
        try:
            py = round(float(m2_str) * 0.3025, 1)
            res["sub_title"] = f"토지 면적 {m2_str}㎡ (약 {py}평)"
        except Exception:
            pass

    # 4. 개별공시지가
    jiga_match = re.search(r"(?:개별공시지가|공시지가)\s*[:|]?\s*([\d,]+)\s*원?", text)
    if jiga_match:
        res["official_price"] = f"{jiga_match.group(1)}원/㎡"

    res["floor_info"] = "- / -"
    res["room_bath"] = "- / -"
    res["entrance_type"] = "-"
    res["heating"] = "-"
    res["parking"] = "-"
    res["households"] = "-"
    res["approval_date"] = "-"

    return res


def parse_land_use_plan(text: str) -> Dict[str, Any]:
    """
    토지이용계획확인원 텍스트에서 데이터 추출
    """
    res = {}

    # 1. 소재지 / 지번
    loc_match = re.search(r"(?:소재지|신청지)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if loc_match:
        res["location"] = clean_val(loc_match.group(1))

    # 2. 지목 및 면적
    jimok_match = re.search(r"(?:지목)\s*[:|]?\s*([가-힣]+)", text)
    if jimok_match:
        res["building_use"] = f"토지 (지목: {jimok_match.group(1).strip()})"
        
    area_match = re.search(r"(?:면적)\s*[:|]?\s*([\d,.]+)\s*㎡?", text)
    if area_match:
        m2_str = area_match.group(1).replace(",", "").strip()
        res["area_supply"] = m2_str
        res["area_exclusive"] = m2_str

    # 3. 용도지역 / 용도지구 (국토의 계획 및 이용에 관한 법률)
    zone_match = re.search(r"국토의\s*계획\s*및\s*이용에\s*관한\s*법률[^\n\r]*\n?([^|\n\r]+?)" + NEXT_KW, text)
    if not zone_match:
        common_zones = ["제1종전용주거지역", "제2종전용주거지역", "제1종일반주거지역", "제2종일반주거지역", "제3종일반주거지역", "준주거지역", "중심상업지역", "일반상업지역", "근린상업지역", "유통상업지역", "전용공업지역", "일반공업지역", "준공업지역", "보전녹지지역", "생산녹지지역", "자연녹지지역", "계획관리지역"]
        found_zones = [z for z in common_zones if z in text]
        if found_zones:
            res["zone_info"] = ", ".join(found_zones)
    else:
        res["zone_info"] = clean_val(zone_match.group(1))

    if "zone_info" in res:
        res["feature_text"] = f"{res['zone_info']} 추천 매물"

    return res


def parse_official_document(file_or_bytes, filename: str = "") -> Tuple[str, Dict[str, Any], str]:
    """
    공적 서류를 종합 분석하여 (서류유형, 추출된 딕셔너리, 원본텍스트요약)을 반환합니다.
    """
    raw_text = extract_text_from_pdf(file_or_bytes)
    doc_type = identify_document_type(raw_text)

    parsed = {}
    if "건축물대장" in doc_type:
        parsed = parse_building_register(raw_text)
    elif "토지대장" in doc_type:
        parsed = parse_land_register(raw_text)
    elif "토지이용계획" in doc_type:
        parsed = parse_land_use_plan(raw_text)
    else:
        parsed = parse_building_register(raw_text)
        if not parsed.get("location"):
            parsed.update(parse_land_register(raw_text))

    return doc_type, parsed, raw_text
