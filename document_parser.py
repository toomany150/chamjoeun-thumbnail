"""
공적서류(건축물대장 표제부/전유부, 일반건축물대장, 토지대장, 토지이용계획확인원) 정밀 분석 모듈
- 집합건축물대장 표제부 (총괄표제부 / 표제부) 정밀 파싱
- 집합건축물대장 전유부 (전유부분 / 공용부분) 정밀 파싱
- 표제부 + 전유부 지능형 자동 병합 (Merge) 시스템
- 일반건축물대장 / 토지대장 / 토지이용계획확인서 파싱
"""

import re
import io
from typing import Dict, Any, Tuple, Optional, List

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


def extract_pages_text_from_pdf(pdf_file) -> List[str]:
    """PDF 파일에서 페이지별 텍스트 및 표 내용을 추출하여 페이지별 리스트로 반환합니다."""
    if not HAS_PDFPLUMBER:
        raise ImportError("pdfplumber 라이브러리가 설치되어 있지 않습니다.")
    
    if hasattr(pdf_file, "seek"):
        try:
            pdf_file.seek(0)
        except Exception:
            pass

    pages_text = []
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                table_lines = []
                try:
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            clean_row = [str(c).strip().replace("\n", " ") for c in row if c is not None and str(c).strip()]
                            if clean_row:
                                table_lines.append(" | ".join(clean_row))
                except Exception:
                    pass
                combined_page = (t + "\n" + "\n".join(table_lines)).strip()
                if combined_page:
                    pages_text.append(combined_page)
    except Exception as e:
        pass
            
    return pages_text


def extract_text_from_pdf(pdf_file) -> str:
    """PDF 파일(BytesIO 또는 파일경로)에서 전체 텍스트를 추출합니다."""
    pages = extract_pages_text_from_pdf(pdf_file)
    return "\n--- PAGE BREAK ---\n".join(pages)


def identify_document_type(text: str) -> str:
    """텍스트 내용을 분석하여 서류 유형을 정밀 감지합니다."""
    text_condensed = text.replace(" ", "")
    
    if "건축물대장" in text_condensed:
        is_jeon = "전유부" in text_condensed or "전유부분" in text_condensed or "전유" in text_condensed
        is_pyo = "표제부" in text_condensed or "총괄표제부" in text_condensed
        
        if is_jeon and is_pyo:
            return "집합건축물대장 (표제부+전유부 복합)"
        elif is_jeon:
            return "집합건축물대장 (전유부)"
        elif is_pyo:
            if "총괄표제부" in text_condensed:
                return "집합건축물대장 (총괄표제부)"
            return "집합건축물대장 (표제부)"
        return "일반건축물대장"
    elif "토지대장" in text_condensed or "임야대장" in text_condensed:
        return "토지대장"
    elif "토지이용계획" in text_condensed:
        return "토지이용계획확인원"
    
    return "기타 공적서류"


# 다음 필드 키워드 패턴 (필드 끝 경계 인식 - 값 내부의 '구조' 단어가 잘리지 않도록 콜론/구분자가 있는 경우만 매칭)
NEXT_KW = r"(?=\s*(?:대지위치|도로명주소|지번\s*[:|]|건축물명칭|명칭\s*[:|]|동명칭|호명칭|주용도|용도\s*[:|]|층수\s*[:|]|사용승인일|허가일|착공일|준공일|주차장\s*[:|]|총주차대수|세대수\s*[:|]|가구수\s*[:|]|주구조\s*[:|]|소재지|지목\s*[:|]|면적\s*[:|]|개별공시지가|소유자|국토의|$))"


def clean_val(s: str) -> str:
    """추출된 값에서 불필요한 기호, 콜론, 공백, 파이프 등을 정리합니다."""
    if not s:
        return ""
    s = s.strip()
    s = re.sub(r"^[:|\-=>\s]+", "", s)
    s = re.sub(r"[:|\-=>\s]+$", "", s)
    return s.strip()


def parse_building_register_title(text: str) -> Dict[str, Any]:
    """
    [표제부 전문 파서] 집합건축물대장 표제부/총괄표제부에서 건물 전체 핵심 스펙 추출
    """
    res = {}

    # 1. 소재지 / 도로명주소 / 대지위치
    loc_match = re.search(r"(?:대지위치|대지\s*위치|소재지)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    road_match = re.search(r"(?:도로명주소|도로명\s*주소)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    jibun_match = re.search(r"(?:지번|지\s*번)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)

    loc_val = clean_val(loc_match.group(1)) if loc_match else ""
    road_val = clean_val(road_match.group(1)) if road_match else ""
    jibun_val = clean_val(jibun_match.group(1)) if jibun_match else ""

    building_name = ""
    b_match = re.search(r"(?:건축물명칭|건축물\s*명칭)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if b_match:
        building_name = clean_val(b_match.group(1))

    dong_name = ""
    d_match = re.search(r"(?:동명칭및호명칭|동명칭|동\s*명칭)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if d_match:
        dong_name = clean_val(d_match.group(1))

    base_addr = loc_val or road_val
    if jibun_val and loc_val and jibun_val not in loc_val:
        base_addr = f"{loc_val} {jibun_val}".strip()

    title_addons = []
    if building_name:
        title_addons.append(building_name)
    if dong_name and (not building_name or dong_name not in building_name):
        title_addons.append(dong_name)

    if title_addons:
        res["location"] = f"{base_addr} ({' '.join(title_addons)})" if base_addr else " ".join(title_addons)
    else:
        res["location"] = base_addr

    res["road_address"] = road_val
    res["jibun_address"] = loc_val
    if building_name:
        res["building_name"] = building_name
        res["main_title"] = building_name
    if dong_name:
        res["dong_name"] = dong_name
        res["sub_title"] = dong_name

    # 2. 층수
    floor_match = re.search(r"지상\s*(\d+)\s*층(?:\s*[/|,\s]\s*지하\s*(\d+)\s*층)?", text)
    if not floor_match:
        floor_match = re.search(r"(\d+)\s*층\s*[/|]\s*지하\s*(\d+)\s*층", text)
    
    if floor_match:
        high_fl = floor_match.group(1)
        under_fl = floor_match.group(2)
        res["max_floor"] = f"{high_fl}층"
        if under_fl:
            res["floor_info"] = f"총 {high_fl}층 (지하 {under_fl}층)"
        else:
            res["floor_info"] = f"총 {high_fl}층"
    else:
        fl_single = re.search(r"(?:층수|지상층수)\s*[:|]?\s*(\d+)\s*층?", text)
        if fl_single:
            res["max_floor"] = f"{fl_single.group(1)}층"
            res["floor_info"] = f"총 {fl_single.group(1)}층"

    # 3. 주차대수
    park_match = re.search(r"(?:주차장|총주차대수|주차대수)\s*[:|]?\s*([^\n\r]+?)" + NEXT_KW, text)
    if park_match:
        p_raw = park_match.group(1)
        p_nums = re.findall(r"([\d,]+)\s*대", p_raw)
        if p_nums:
            total_pk = p_nums[-1].replace(",", "")
            res["parking"] = f"총 {total_pk}대"
            if "자주식" in p_raw:
                res["parking"] += " (자주식)"
        else:
            clean_pk = clean_val(p_raw)
            if clean_pk and any(c.isdigit() for c in clean_pk):
                res["parking"] = clean_pk

    if not res.get("parking"):
        p_alt = re.search(r"총\s*([\d,]+)\s*대", text)
        if p_alt:
            res["parking"] = f"총 {p_alt.group(1)}대"

    # 4. 세대수 / 가구수
    hh_match = re.search(r"(?:세대수|세대\s*수)\s*[:|]?\s*([\d,]+)\s*세대", text)
    if hh_match:
        res["households"] = f"총 {hh_match.group(1)}세대"
    else:
        ga_match = re.search(r"(?:가구수|가구\s*수)\s*[:|]?\s*([\d,]+)\s*가구", text)
        if ga_match:
            res["households"] = f"총 {ga_match.group(1)}가구"

    if res.get("parking") and res.get("households"):
        try:
            pk_cnt = int(re.sub(r"[^\d]", "", res["parking"]))
            hh_cnt = int(re.sub(r"[^\d]", "", res["households"]))
            if hh_cnt > 0:
                per_hh = round(pk_cnt / hh_cnt, 2)
                res["parking"] = f"총 {pk_cnt:,}대 (세대당 {per_hh}대)"
        except Exception:
            pass

    # 5. 사용승인일
    app_match = re.search(r"사용\s*승인일\s*[:|]?\s*(\d{4}[.\-년\s]+\d{1,2}[.\-월\s]+\d{1,2}일?)", text)
    if not app_match:
        date_pattern = r"\b(\d{4}[.\-]\d{2}[.\-]\d{2})\b"
        all_dates = re.findall(date_pattern, text)
        if "사용승인일" in text and len(all_dates) >= 3:
            parts = re.findall(r"\d+", all_dates[2])
            if len(parts) >= 3:
                res["approval_date"] = f"{parts[0]}년 {int(parts[1]):02d}월 {int(parts[2]):02d}일"
    else:
        raw_date = app_match.group(1).strip()
        date_nums = re.findall(r"\d+", raw_date)
        if len(date_nums) >= 3:
            res["approval_date"] = f"{date_nums[0]}년 {int(date_nums[1]):02d}월 {int(date_nums[2]):02d}일"
        else:
            res["approval_date"] = raw_date

    # 6. 주구조 (철근콘크리트구조 등)
    struct_match = re.search(r"(?:주구조|주\s*구조|구조)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if struct_match:
        res["structure"] = clean_val(struct_match.group(1))

    # 7. 주용도
    use_match = re.search(r"(?:주용도|주\s*용도)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if use_match:
        res["building_use"] = clean_val(use_match.group(1))
    else:
        if "아파트" in text:
            res["building_use"] = "공동주택 (아파트)"
        elif "오피스텔" in text:
            res["building_use"] = "업무시설 (오피스텔)"
        elif "다세대" in text or "연립" in text:
            res["building_use"] = "공동주택 (다세대/연립)"

    # 8. 연면적
    yeon_match = re.search(r"(?:연면적|연\s*면적)\s*[:|]?\s*([\d,.]+)", text)
    if yeon_match:
        res["area_total"] = yeon_match.group(1).replace(",", "").strip()

    return res


def parse_building_register_exclusive(text: str) -> Dict[str, Any]:
    """
    [전유부 전문 파서] 집합건축물대장 전유부에서 개별 호실 핵심 스펙 정밀 추출
    """
    res = {}

    # 1. 소재지 / 대지위치 / 도로명
    loc_match = re.search(r"(?:대지위치|대지\s*위치|소재지)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    road_match = re.search(r"(?:도로명주소|도로명\s*주소)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    jibun_match = re.search(r"(?:지번|지\s*번)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)

    loc_val = clean_val(loc_match.group(1)) if loc_match else ""
    road_val = clean_val(road_match.group(1)) if road_match else ""
    jibun_val = clean_val(jibun_match.group(1)) if jibun_match else ""

    building_name = ""
    b_match = re.search(r"(?:건축물명칭|건축물\s*명칭)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if b_match:
        building_name = clean_val(b_match.group(1))

    dong_name = ""
    ho_name = ""

    d_match = re.search(r"(?:동명칭및호명칭|동명칭|동\s*명칭)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if d_match:
        d_raw = clean_val(d_match.group(1))
        dong_part = re.search(r"(\d+동|제\s*\d+동)", d_raw)
        ho_part = re.search(r"(\d+호|제\s*\d+호)", d_raw)
        if dong_part:
            dong_name = dong_part.group(1).replace(" ", "")
        if ho_part:
            ho_name = ho_part.group(1).replace(" ", "")
        if not dong_name and not ho_name:
            dong_name = d_raw

    h_match = re.search(r"(?:호명칭|호\s*명칭)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if h_match:
        ho_name = clean_val(h_match.group(1))

    if not dong_name:
        d_found = re.search(r"(\d{3,4}동|제\s*\d{3,4}동)", text)
        if d_found:
            dong_name = d_found.group(1).replace(" ", "")
    if not ho_name:
        h_found = re.search(r"(\d{3,4}호|제\s*\d{3,4}호)", text)
        if h_found:
            ho_name = h_found.group(1).replace(" ", "")

    base_addr = loc_val or road_val
    if jibun_val and loc_val and jibun_val not in loc_val:
        base_addr = f"{loc_val} {jibun_val}".strip()

    # 중복 토큰 방지
    sub_parts = []
    if building_name:
        sub_parts.append(building_name)
    if dong_name and (not building_name or dong_name not in building_name):
        sub_parts.append(dong_name)
    if ho_name and (not building_name or ho_name not in building_name):
        sub_parts.append(ho_name)

    if sub_parts:
        res["location"] = f"{base_addr} ({' '.join(sub_parts)})" if base_addr else " ".join(sub_parts)
    else:
        res["location"] = base_addr

    res["road_address"] = road_val
    res["jibun_address"] = loc_val
    if building_name:
        res["building_name"] = building_name
        res["main_title"] = building_name
    if dong_name or ho_name:
        res["dong_name"] = dong_name
        res["ho_name"] = ho_name
        res["sub_title"] = f"{dong_name} {ho_name}".strip()

    # 2. 면적 정밀 파싱 (라인 단위 전유부분 vs 공용부분 분석)
    exclusive_area = 0.0
    common_area = 0.0

    lines = text.split("\n")
    current_section = None  # "exclusive" or "common"

    for line in lines:
        line_clean = line.replace(" ", "")
        if "전유부분" in line_clean or "전유부면적" in line_clean:
            current_section = "exclusive"
        elif "공용부분" in line_clean:
            current_section = "common"
        elif "소유자현황" in line_clean or "변동사항" in line_clean:
            current_section = None

        if current_section == "exclusive":
            # 전유부분 행에서 면적 추출 (소수점 숫자)
            num_matches = re.findall(r"([\d,]+\.\d{2,4})", line)
            if num_matches and exclusive_area == 0.0:
                try:
                    exclusive_area = float(num_matches[0].replace(",", ""))
                except Exception:
                    pass

        elif current_section == "common":
            # 주거공용 키워드가 있는 라인의 면적만 합산 (계단실, 복도, 승강기실, 홀 등)
            is_res_comm = any(k in line for k in ["계단", "복도", "승강기", "엘리베이터", "홀", "주거공용", "현관"])
            if is_res_comm:
                num_matches = re.findall(r"([\d,]+\.\d{2,4})", line)
                if num_matches:
                    try:
                        common_area += float(num_matches[0].replace(",", ""))
                    except Exception:
                        pass

    # 라인 단위로 못 찾은 경우 정규식 Fallback
    if exclusive_area == 0.0:
        ex_match = re.search(r"전유부분[^\n\r]*\n?[^\n\r]*?([\d,]+\.\d{2,4})", text)
        if not ex_match:
            ex_match = re.search(r"(?:전유면적|전유부분\s*면적|전유\s*면적)\s*[:|]?\s*([\d,.]+)", text)
        if not ex_match:
            ex_match = re.search(r"전유(?:부분)?\s*\|\s*([\d,.]+)", text)
        if ex_match:
            try:
                exclusive_area = float(ex_match.group(1).replace(",", "").strip())
            except Exception:
                pass

    if exclusive_area > 0:
        res["area_exclusive"] = f"{exclusive_area:.2f}"
        if common_area > 0:
            supp_area = exclusive_area + common_area
            res["area_supply"] = f"{round(supp_area, 2):.2f}"
            res["area_common"] = f"{round(common_area, 2):.2f}"
        else:
            res["area_supply"] = f"{exclusive_area:.2f}"

    # 4. 해당 층수 파싱
    current_fl = ""
    fl_match = re.search(r"(?:제\s*)?(\d+)\s*층\s*(?:제\s*)?\d+\s*호", text)
    if fl_match:
        current_fl = f"{fl_match.group(1)}층"
    elif ho_name:
        num_only = re.sub(r"[^\d]", "", ho_name)
        if len(num_only) >= 3:
            current_fl = f"{num_only[:-2]}층"

    if not current_fl:
        fl_direct = re.search(r"층별\s*[:|]?\s*(?:지상\s*)?(\d+)\s*층", text)
        if fl_direct:
            current_fl = f"{fl_direct.group(1)}층"

    if current_fl:
        res["current_floor"] = current_fl
        res["floor_info"] = current_fl

    # 5. 전유부 주용도
    use_match = re.search(r"(?:주용도|용도)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if use_match:
        clean_u = clean_val(use_match.group(1))
        if clean_u:
            res["building_use"] = clean_u
    
    if not res.get("building_use"):
        if "아파트" in text:
            res["building_use"] = "공동주택 (아파트)"
        elif "오피스텔" in text:
            res["building_use"] = "업무시설 (오피스텔)"
        elif "다세대" in text:
            res["building_use"] = "공동주택 (다세대)"
        elif "근린생활시설" in text or "상가" in text:
            res["building_use"] = "제2종근린생활시설"

    # 6. 방수 / 욕실수 추정
    if exclusive_area > 0:
        if exclusive_area >= 80:
            res["room_bath"] = "방 3 / 욕실 2개"
        elif exclusive_area >= 50:
            res["room_bath"] = "방 3 / 욕실 1개"
        elif exclusive_area >= 30:
            res["room_bath"] = "방 2 / 욕실 1개"
        else:
            res["room_bath"] = "방 1 / 욕실 1개 (원룸)"

    return res


def merge_building_registers(title_data: Dict[str, Any], exclusive_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    [핵심 스마트 병합 함수]
    표제부 데이터와 전유부 데이터를 완벽하게 융합하여 16대 점검항목 완성형 데이터 생성
    - 소재지: 도로명 + 지번 + 건물명 + 전유부 동·호수 결합
    - 면적: 전유부 전용면적 + 주거공용면적 합산(공급면적)
    - 층수: 전유부 해당층 / 표제부 총층수 (예: 25 / 36층)
    - 사용승인일: 표제부의 공인 준공일자
    - 주차대수: 표제부의 총 주차대수 및 세대당 주차대수
    - 세대수: 표제부의 총 세대수
    - 주용도: 전유부 용도 우선
    - 구조: 표제부 주구조
    """
    merged = {}

    # 1. 소재지 융합
    road = exclusive_data.get("road_address") or title_data.get("road_address") or ""
    jibun = exclusive_data.get("jibun_address") or title_data.get("jibun_address") or ""
    b_name = exclusive_data.get("building_name") or title_data.get("building_name") or ""
    d_name = exclusive_data.get("dong_name") or title_data.get("dong_name") or ""
    h_name = exclusive_data.get("ho_name") or title_data.get("ho_name") or ""

    base_loc = jibun or road or title_data.get("location") or exclusive_data.get("location") or ""
    # 불필요한 기존 괄호 제거 후 재구성
    base_loc_clean = re.sub(r"\s*\(.*?\)", "", base_loc).strip()

    details = []
    if b_name:
        details.append(b_name)
    if d_name and (not b_name or d_name not in b_name):
        details.append(d_name)
    if h_name and (not b_name or h_name not in b_name):
        details.append(h_name)

    if details:
        merged["location"] = f"{base_loc_clean} ({' '.join(details)})"
    else:
        merged["location"] = base_loc_clean

    # 썸네일 제목 연동
    if b_name:
        merged["main_title"] = b_name
    elif title_data.get("main_title"):
        merged["main_title"] = title_data["main_title"]

    sub_t = f"{d_name} {h_name}".strip()
    if sub_t:
        merged["sub_title"] = sub_t
    elif exclusive_data.get("sub_title"):
        merged["sub_title"] = exclusive_data["sub_title"]

    # 2. 면적 (전유부 우선)
    if exclusive_data.get("area_exclusive"):
        merged["area_exclusive"] = exclusive_data["area_exclusive"]
        if exclusive_data.get("area_supply"):
            merged["area_supply"] = exclusive_data["area_supply"]
        else:
            merged["area_supply"] = exclusive_data["area_exclusive"]
    elif title_data.get("area_total"):
        merged["area_exclusive"] = title_data["area_total"]
        merged["area_supply"] = title_data["area_total"]

    # 3. 층수 융합 (해당층 / 총층)
    cur_fl = exclusive_data.get("current_floor") or ""
    max_fl = title_data.get("max_floor") or ""

    if cur_fl and max_fl:
        merged["floor_info"] = f"{cur_fl} / {max_fl}"
    elif cur_fl:
        merged["floor_info"] = cur_fl
    elif max_fl:
        merged["floor_info"] = f"총 {max_fl}"
    elif title_data.get("floor_info"):
        merged["floor_info"] = title_data["floor_info"]

    # 4. 방수 / 욕실수
    if exclusive_data.get("room_bath"):
        merged["room_bath"] = exclusive_data["room_bath"]

    # 5. 주용도 (전유부 우선 -> 표제부)
    merged["building_use"] = exclusive_data.get("building_use") or title_data.get("building_use") or "공동주택 (아파트)"

    # 6. 사용승인일 (표제부 우선)
    if title_data.get("approval_date"):
        merged["approval_date"] = title_data["approval_date"]
    elif exclusive_data.get("approval_date"):
        merged["approval_date"] = exclusive_data["approval_date"]

    # 7. 주차대수 (표제부 우선)
    if title_data.get("parking"):
        merged["parking"] = title_data["parking"]
    elif exclusive_data.get("parking"):
        merged["parking"] = exclusive_data["parking"]

    # 8. 총 세대수 (표제부 우선)
    if title_data.get("households"):
        merged["households"] = title_data["households"]
    elif exclusive_data.get("households"):
        merged["households"] = exclusive_data["households"]

    # 9. 주구조
    if title_data.get("structure"):
        merged["structure"] = title_data["structure"]
    elif exclusive_data.get("structure"):
        merged["structure"] = exclusive_data["structure"]

    # 10. 썸네일 특징 문구 자동 생성
    feature_parts = []
    if merged.get("households"):
        feature_parts.append(merged["households"])
    if b_name:
        feature_parts.append(b_name)
    if feature_parts:
        merged["feature_text"] = " · ".join(feature_parts) + " 추천 매물"

    return merged


def parse_general_building_register(text: str) -> Dict[str, Any]:
    """
    일반건축물대장 (단독주택 / 상가주택 / 꼬마빌딩 등) 파서
    """
    title_res = parse_building_register_title(text)
    # 일반건축물은 연면적이 공급/전용면적이 됨
    if "area_total" in title_res:
        title_res["area_exclusive"] = title_res["area_total"]
        title_res["area_supply"] = title_res["area_total"]
    return title_res


def parse_land_register(text: str) -> Dict[str, Any]:
    """
    토지대장 / 임야대장 텍스트에서 데이터 추출
    """
    res = {}
    
    loc_match = re.search(r"(?:소재지|소\s*재\s*지)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    jibun_match = re.search(r"(?:지번|지\s*번)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    
    loc_val = clean_val(loc_match.group(1)) if loc_match else ""
    jibun_val = clean_val(jibun_match.group(1)) if jibun_match else ""
    
    if loc_val and jibun_val:
        res["location"] = f"{loc_val} {jibun_val}"
    elif loc_val:
        res["location"] = loc_val

    jimok_match = re.search(r"(?:지목|지\s*목)\s*[:|]?\s*([가-힣]+)", text)
    jimok = jimok_match.group(1).strip() if jimok_match else "대"
    res["building_use"] = f"토지 (지목: {jimok})"
    res["feature_text"] = f"지목 '{jimok}' 특급 추천 토지"

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

    loc_match = re.search(r"(?:소재지|신청지)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if loc_match:
        res["location"] = clean_val(loc_match.group(1))

    jimok_match = re.search(r"(?:지목)\s*[:|]?\s*([가-힣]+)", text)
    if jimok_match:
        res["building_use"] = f"토지 (지목: {jimok_match.group(1).strip()})"
        
    area_match = re.search(r"(?:면적)\s*[:|]?\s*([\d,.]+)\s*㎡?", text)
    if area_match:
        m2_str = area_match.group(1).replace(",", "").strip()
        res["area_supply"] = m2_str
        res["area_exclusive"] = m2_str

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


def parse_single_or_multi_document(pages_text: List[str]) -> Tuple[str, Dict[str, Any], str]:
    """
    다중 페이지 또는 복합 서류를 분석하여 표제부와 전유부가 둘 다 있는 경우 자동 병합합니다.
    """
    full_text = "\n".join(pages_text).strip()
    if not full_text:
        return "보안/DRM 문서 (텍스트 미감지)", {}, ""
    doc_type = identify_document_type(full_text)

    # 1. 표제부 + 전유부 복합 서류인 경우
    if "표제부+전유부" in doc_type or ("표제부" in full_text and "전유부분" in full_text):
        title_texts = []
        exclusive_texts = []
        for p in pages_text:
            p_cond = p.replace(" ", "")
            if "전유부" in p_cond or "전유부분" in p_cond:
                exclusive_texts.append(p)
            elif "표제부" in p_cond or "총괄표제부" in p_cond:
                title_texts.append(p)
            else:
                title_texts.append(p)

        t_data = parse_building_register_title("\n".join(title_texts) if title_texts else full_text)
        e_data = parse_building_register_exclusive("\n".join(exclusive_texts) if exclusive_texts else full_text)
        merged = merge_building_registers(t_data, e_data)
        return "집합건축물대장 (표제부 + 전유부 통합완료)", merged, full_text

    # 2. 표제부 단독
    elif "표제부" in doc_type:
        parsed = parse_building_register_title(full_text)
        return doc_type, parsed, full_text

    # 3. 전유부 단독
    elif "전유부" in doc_type:
        parsed = parse_building_register_exclusive(full_text)
        return doc_type, parsed, full_text

    # 4. 토지대장
    elif "토지대장" in doc_type:
        parsed = parse_land_register(full_text)
        return doc_type, parsed, full_text

    # 5. 토지이용계획원
    elif "토지이용계획" in doc_type:
        parsed = parse_land_use_plan(full_text)
        return doc_type, parsed, full_text

    # 6. 일반건축물대장 / 기타
    else:
        parsed = parse_general_building_register(full_text)
        return doc_type, parsed, full_text


def parse_official_document(file_or_bytes, filename: str = "") -> Tuple[str, Dict[str, Any], str]:
    """
    공적 서류를 종합 분석하여 (서류유형, 추출된 딕셔너리, 원본텍스트요약)을 반환합니다.
    """
    pages_text = extract_pages_text_from_pdf(file_or_bytes)
    return parse_single_or_multi_document(pages_text)
