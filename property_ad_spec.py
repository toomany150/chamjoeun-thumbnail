"""
부동산 매물 인터넷 표시·광고 점검표 및 블로그 서식/카드 이미지 생성 모듈
- 네이버 부동산 매물 등록 순서 16개 항목 완벽 지원
- 네이버 블로그 스마트에디터용 HTML 표 생성
- 블로그 텍스트 복사 및 네이버 광고 작성 가이드
- Pillow 기반 고화질 중개대상물 표시 카드 이미지 (PNG) 렌더링
"""

import os
import io
import math
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

def get_font(font_name: str, size: int) -> ImageFont.FreeTypeFont:
    """폰트를 안전하게 로드합니다."""
    bundled_paths = [
        os.path.join(ASSETS_DIR, "fonts", font_name),
        os.path.join(ASSETS_DIR, "fonts", "NanumGothicExtraBold.ttf"),
        os.path.join(ASSETS_DIR, "fonts", "NanumGothicBold.ttf"),
        os.path.join(ASSETS_DIR, "fonts", "NanumGothic.ttf"),
    ]
    for p in bundled_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue

    candidates = [
        f"C:/Windows/Fonts/{font_name}",
        f"C:/Windows/Fonts/NanumGothicBold.ttf",
        f"C:/Windows/Fonts/malgunbd.ttf",
        f"C:/Windows/Fonts/malgun.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

# 참좋은공인중개사사무소 고유 정보 (신제환 대표님)
OFFICE_SPEC = {
    "office_name": "참좋은공인중개사사무소",
    "office_owner": "신제환",
    "office_reg_no": "제 26530-2026-00009 호",
    "office_address": "부산광역시 사상구 강선로 9, 1층",
    "office_phone": "010-9667-4201",
    "include_office_info": True,
    "assistant_name": "", # 소속공인중개사 성명
    "assistant_phone": "", # 소속공인중개사 연락처
}

# 사상 중흥S-클래스 추천 예시 데이터 (원클릭 예시 불러오기용)
SAMPLE_APT_SPEC = {
    "location": "부산광역시 사상구 덕포동 220 (사상 중흥S-클래스 105동)",
    "area_supply": "111.42",
    "area_exclusive": "79.85",
    "floor_info": "25 / 36층",
    "floor_type": "해당층 직접입력", # 또는 "고층", "중층", "저층"
    "room_bath": "방 3 / 욕실 2개",
    "maintenance_fee": "월 18만 원",
    "maintenance_detail": "공용관리비 약 13만 원 (수도·전기·가스는 실사용량에 따라 별도 부과)",
    "trade_type": "매매",
    "price_text": "6억 2,000만 원",
    "deposit_sub": "- / -", # 기보증금 / 월세
    "direction": "남동향 (거실 기준)",
    "entrance_type": "계단식",
    "heating": "개별난방 / 도시가스",
    "move_in_date": "즉시입주 협의가능",
    "parking": "총 1,685대 (세대당 1.07대)",
    "households": "331세대 (총 1,572세대)",
    "building_use": "공동주택 (아파트)",
    "approval_date": "2023년 07월 28일",
    **OFFICE_SPEC
}

# 신규 매물 등록용 빈 양식 (중개사무소 정보는 유지하고 매물 정보는 초기화)
BLANK_SPEC = {
    "location": "",
    "area_supply": "",
    "area_exclusive": "",
    "floor_info": "",
    "floor_type": "해당층 직접입력",
    "room_bath": "",
    "maintenance_fee": "",
    "maintenance_detail": "",
    "trade_type": "매매",
    "price_text": "",
    "deposit_sub": "- / -",
    "direction": "",
    "entrance_type": "계단식",
    "heating": "개별난방 / 도시가스",
    "move_in_date": "즉시입주 협의가능",
    "parking": "",
    "households": "",
    "building_use": "공동주택 (아파트)",
    "approval_date": "",
    **OFFICE_SPEC
}

# 하위 호환성 유지
DEFAULT_SPEC = SAMPLE_APT_SPEC


# 네이버 부동산 광고 입력 순서 16개 점검 항목 메타데이터
SPEC_ITEMS_META = [
    {
        "id": "location",
        "num": 1,
        "title": "소재지",
        "guide": "동·리 및 지번 표기 필수 (아파트 동·호수는 의뢰인 동의 시 생략 가능)",
        "badge": "법정필수"
    },
    {
        "id": "area",
        "num": 2,
        "title": "공급/전용면적",
        "guide": "법정단위인 ㎡만 표기 (평수 표기 금지, 전용률 자동 산출)",
        "badge": "법정필수"
    },
    {
        "id": "floor",
        "num": 3,
        "title": "해당층/총층",
        "guide": "아파트의 경우 의뢰인 요청 시 저/중/고층 대체 표기 가능",
        "badge": "법정필수"
    },
    {
        "id": "room_bath",
        "num": 4,
        "title": "방수/욕실수",
        "guide": "건축물대장 또는 실제 현황 기준 방 및 욕실 개수 명시",
        "badge": "법정필수"
    },
    {
        "id": "maintenance",
        "num": 5,
        "title": "관리비",
        "guide": "월 10만 원 이상 시 세부내역(공용/전기/수도 등) 분리 기재 필수",
        "badge": "과태료주의"
    },
    {
        "id": "trade_type",
        "num": 6,
        "title": "거래 형태",
        "guide": "매매, 전세, 월세 중 1개 명확히 명시",
        "badge": "법정필수"
    },
    {
        "id": "price",
        "num": 7,
        "title": "가격 (기보증금/월세)",
        "guide": "거래 형태에 따른 정확한 가격 및 기존 임대차 승계 여부 명시",
        "badge": "법정필수"
    },
    {
        "id": "direction",
        "num": 8,
        "title": "방향",
        "guide": "주실(거실) 또는 안방 창문 기준 명확히 기재",
        "badge": "법정필수"
    },
    {
        "id": "entrance",
        "num": 9,
        "title": "현관구조",
        "guide": "계단식, 복도식, 복합식 중 선택",
        "badge": "네이버광고"
    },
    {
        "id": "heating",
        "num": 10,
        "title": "난방(방식/연료)",
        "guide": "개별/도시가스, 지역/열병합, 중앙/도시가스 등",
        "badge": "네이버광고"
    },
    {
        "id": "move_in",
        "num": 11,
        "title": "입주가능일",
        "guide": "즉시입주, 날짜 지정 또는 협의가능 여부 기재",
        "badge": "법정필수"
    },
    {
        "id": "parking",
        "num": 12,
        "title": "총주차대수",
        "guide": "단지 총 주차대수 및 세대당 주차대수 기재",
        "badge": "법정필수"
    },
    {
        "id": "households",
        "num": 13,
        "title": "해당면적 세대수",
        "guide": "해당 평형 세대수 및 총 세대수 병기 권장",
        "badge": "네이버광고"
    },
    {
        "id": "building_use",
        "num": 14,
        "title": "건축물 용도",
        "guide": "건축물대장 상 용도 부합 (공동주택, 업무시설 등)",
        "badge": "법정필수"
    },
    {
        "id": "approval_date",
        "num": 15,
        "title": "사용승인일",
        "guide": "건축물대장 상 사용승인일(준공인가일) 기재 필수",
        "badge": "법정필수"
    },
    {
        "id": "office_info",
        "num": 16,
        "title": "중개사무소 정보",
        "guide": "상호, 소재지, 연락처, 등록번호, 대표자 성명 5대 항목 필수",
        "badge": "법정필수"
    }
]

def format_area_text(supply_str: str, exclusive_str: str) -> tuple[str, str]:
    """공급면적과 전용면적으로 전용률 텍스트 생성 (법정 단위인 ㎡만 표기, 평형 삭제)"""
    try:
        sup_m2 = float(str(supply_str).replace(",", "").strip())
        exc_m2 = float(str(exclusive_str).replace(",", "").strip())
        rate = round((exc_m2 / sup_m2) * 100, 1) if sup_m2 > 0 else 0
        summary_m2 = f"{sup_m2:.2f}㎡ / {exc_m2:.2f}㎡ (전용률 {rate}%)"
        return summary_m2, ""
    except Exception:
        return f"{supply_str}㎡ / {exclusive_str}㎡", ""

def get_ordered_spec_table_data(data: dict) -> list[dict]:
    """16개 항목 순서대로 정리된 데이터 리스트 반환"""
    area_m2, _ = format_area_text(data.get("area_supply", "111.42"), data.get("area_exclusive", "79.85"))
    area_display = area_m2 # 평수 표기 완전 삭제 (법정계량단위 ㎡ 단독 표기)

    m_fee = str(data.get("maintenance_fee", "월 18만 원")).strip()
    m_detail = str(data.get("maintenance_detail", "")).strip()
    
    if m_fee and not m_fee.startswith("월") and "만" in m_fee:
        m_fee_clean = f"월 {m_fee}"
    else:
        m_fee_clean = m_fee

    if m_detail:
        m_display = f"{m_fee_clean}\n• 세부내역: {m_detail}"
    else:
        m_display = m_fee_clean

    trade = data.get("trade_type", "매매")
    price = data.get("price_text", "6억 2,000만 원")
    dep_sub = data.get("deposit_sub", "")
    price_display = f"{price}" + (f" (기보증금/월세: {dep_sub})" if dep_sub and dep_sub != "- / -" else "")

    items = [
        {"num": 1, "name": "소재지", "val": data.get("location", ""), "guide": "동·리 및 지번 표기 필수 (동·호수 생략 가능)"},
        {"num": 2, "name": "공급/전용면적", "val": area_display, "guide": "법정단위인 ㎡만 표기 (평수 표기 금지)"},
        {"num": 3, "name": "해당층 / 총층", "val": data.get("floor_info", ""), "guide": "아파트 저/중/고층 대체 가능"},
        {"num": 4, "name": "방수 / 욕실수", "val": data.get("room_bath", ""), "guide": "건축물대장 기준"},
        {"num": 5, "name": "관리비", "val": m_display, "guide": "월 10만 원 이상 세부내역 분리 필수"},
        {"num": 6, "name": "거래 형태", "val": trade, "guide": "매매, 전세, 월세 중 1개 명시"},
        {"num": 7, "name": "가격", "val": price_display, "guide": "기보증금 및 월세 승계 여부"},
        {"num": 8, "name": "방향", "val": data.get("direction", ""), "guide": "주실(거실) 기준"},
        {"num": 9, "name": "현관구조", "val": data.get("entrance_type", "계단식"), "guide": "계단식/복도식/복합식"},
        {"num": 10, "name": "난방(방식/연료)", "val": data.get("heating", "개별난방 / 도시가스"), "guide": "난방방식 및 연료"},
        {"num": 11, "name": "입주가능일", "val": data.get("move_in_date", "즉시입주 협의가능"), "guide": "즉시입주 또는 날짜 협의"},
        {"num": 12, "name": "총주차대수", "val": data.get("parking", "1,685대 (세대당 1.07대)"), "guide": "단지 전체 및 세대당 대수"},
        {"num": 13, "name": "해당면적 세대수", "val": data.get("households", "331세대 (총 1,572세대)"), "guide": "해당 면적형 세대수"},
        {"num": 14, "name": "건축물 용도", "val": data.get("building_use", "공동주택 (아파트)"), "guide": "건축물대장 상 용도"},
        {"num": 15, "name": "사용승인일", "val": data.get("approval_date", "2023년 07월 28일"), "guide": "건축물대장 상 사용승인일"},
    ]

    include_office = data.get("include_office_info", True)
    if include_office:
        office_lines = [
            f"• 상호: {data.get('office_name', '참좋은공인중개사사무소')}",
            f"• 대표: {data.get('office_owner', '신제환')}",
            f"• 등록번호: {data.get('office_reg_no', '제 26530-2026-00009 호')}",
            f"• 소재지: {data.get('office_address', '부산광역시 사상구 강선로 9, 1층')}",
            f"• 연락처: {data.get('office_phone', '010-9667-4201')}"
        ]
        as_name = data.get("assistant_name", "").strip()
        as_phone = data.get("assistant_phone", "").strip()
        if as_name or as_phone:
            as_info = f"{as_name} ({as_phone})".strip() if as_phone else as_name
            office_lines.append(f"• 담당(소공): {as_info}")
        office_full = "\n".join(office_lines)
        items.append({"num": 16, "name": "중개사무소 정보", "val": office_full, "guide": "상호, 소재지, 연락처, 등록번호, 대표자 5대 항목 필수"})

    return items


def get_house_spec_table_data(data: dict) -> list[dict]:
    """주택(단독·다가구·전원주택) 16개 인터넷 표시·광고 명시사항"""
    area_land = str(data.get("area_land", "148.7")).strip()
    area_gross = str(data.get("area_gross", "99.2")).strip()
    area_display = f"대지 {area_land}㎡ / 연면적 {area_gross}㎡"

    items = [
        {"num": 1, "name": "소재지", "val": data.get("location", "부산광역시 사상구 감전동"), "guide": "동·리 및 지번 표기 필수 (동·호수 생략 가능)"},
        {"num": 2, "name": "대지 / 연면적", "val": area_display, "guide": "법정단위인 ㎡만 표기 (평수 표기 금지)"},
        {"num": 3, "name": "해당층 / 총층", "val": data.get("floor_info", "지상 2층 / 지하 0층"), "guide": "건축물대장 상 층수"},
        {"num": 4, "name": "방수 / 욕실수", "val": data.get("room_bath", "방 4 / 욕실 2개"), "guide": "실제 주거 구조 기준"},
        {"num": 5, "name": "관리비", "val": data.get("maintenance_fee", "자체관리 (실사용량 별도 부과)"), "guide": "단독주택 자체관리 명시"},
        {"num": 6, "name": "거래 형태", "val": data.get("trade_type", "매매"), "guide": "매매, 전세, 월세 중 1개 명시"},
        {"num": 7, "name": "가격", "val": data.get("price_text", "3억 8,000만 원"), "guide": "매매가 / 보증금·월세"},
        {"num": 8, "name": "방향", "val": data.get("direction", "남향 (거실 기준)"), "guide": "주실(거실) 기준"},
        {"num": 9, "name": "주차대수", "val": data.get("parking", "총 1대 가능 (마당/자주식)"), "guide": "마당 또는 인근 주차 여부"},
        {"num": 10, "name": "난방(방식/연료)", "val": data.get("heating", "개별난방 / 도시가스"), "guide": "난방방식 및 연료"},
        {"num": 11, "name": "입주가능일", "val": data.get("move_in_date", "즉시입주 협의가능"), "guide": "즉시입주 또는 날짜 협의"},
        {"num": 12, "name": "건축물 용도", "val": data.get("building_use", "단독주택"), "guide": "건축물대장 상 용도"},
        {"num": 13, "name": "건축물 구조", "val": data.get("structure", "벽돌구조 / 연와조"), "guide": "건축물대장 주구조"},
        {"num": 14, "name": "사용승인일", "val": data.get("approval_date", "1998년 05월 12일"), "guide": "건축물대장 상 사용승인일"},
        {"num": 15, "name": "주요 특징", "val": data.get("feature", "마당 넓음 · 올리모델링 완료"), "guide": "매물 특장점"},
    ]

    include_office = data.get("include_office_info", True)
    if include_office:
        office_lines = [
            f"• 상호: {data.get('office_name', '참좋은공인중개사사무소')}",
            f"• 대표: {data.get('office_owner', '신제환')}",
            f"• 등록번호: {data.get('office_reg_no', '제 26530-2026-00009 호')}",
            f"• 소재지: {data.get('office_address', '부산광역시 사상구 강선로 9, 1층')}",
            f"• 연락처: {data.get('office_phone', '010-9667-4201')}"
        ]
        as_name = data.get("assistant_name", "").strip()
        as_phone = data.get("assistant_phone", "").strip()
        if as_name or as_phone:
            as_info = f"{as_name} ({as_phone})".strip() if as_phone else as_name
            office_lines.append(f"• 담당(소공): {as_info}")
        office_full = "\n".join(office_lines)
        items.append({"num": 16, "name": "중개사무소 정보", "val": office_full, "guide": "5대 필수 명시"})

    return items


def get_factory_spec_table_data(data: dict) -> list[dict]:
    """공장/창고 16개 인터넷 표시·광고 명시사항"""
    area_land = str(data.get("area_land", "826.5")).strip()
    area_gross = str(data.get("area_gross", "550.0")).strip()
    area_display = f"대지 {area_land}㎡ / 연면적 {area_gross}㎡"

    items = [
        {"num": 1, "name": "소재지", "val": data.get("location", "부산광역시 사상구 삼락동 사상공단"), "guide": "동·리 및 지번 표기"},
        {"num": 2, "name": "대지 / 연면적", "val": area_display, "guide": "공장용지 및 건축 연면적"},
        {"num": 3, "name": "용도지역 / 지목", "val": data.get("zoning", "일반공업지역 / 공장용지"), "guide": "토지이용계획원 기준"},
        {"num": 4, "name": "건축물 용도", "val": data.get("building_use", "공장 (제조업소)"), "guide": "건축물대장 상 용도"},
        {"num": 5, "name": "층고 / 처마고", "val": data.get("height", "처마 8.5m / 최고 9.5m"), "guide": "유효 층고"},
        {"num": 6, "name": "호이스트 설비", "val": data.get("hoist", "5톤 1기 완비"), "guide": "호이스트 용량 및 유무"},
        {"num": 7, "name": "동력 (전기)", "val": data.get("power", "150kW 수전설비"), "guide": "인입 동력 전력"},
        {"num": 8, "name": "진입도로 폭", "val": data.get("road", "8m 포장도로 (츄레라/트레일러 진입 원활)"), "guide": "진입도로 및 접근성"},
        {"num": 9, "name": "거래 형태", "val": data.get("trade_type", "매매"), "guide": "매매, 임대차 중 1개 명시"},
        {"num": 10, "name": "거래 금액", "val": data.get("price_text", "18억 5,000만 원"), "guide": "매매가 또는 보증금/월세"},
        {"num": 11, "name": "관리비", "val": data.get("maintenance_fee", "자체관리"), "guide": "공장 자체관리"},
        {"num": 12, "name": "주차 대수", "val": data.get("parking", "옥외 마당 5대 이상"), "guide": "주차 및 야적 공간"},
        {"num": 13, "name": "입주 가능일", "val": data.get("move_in_date", "즉시입주 협의가능"), "guide": "즉시가동 또는 협의"},
        {"num": 14, "name": "사용승인일", "val": data.get("approval_date", "2015년 10월 20일"), "guide": "건축물대장 준공일"},
        {"num": 15, "name": "주출입구 방향", "val": data.get("direction", "남향 (주출입구 기준)"), "guide": "공장 주출입구 기준"},
    ]

    include_office = data.get("include_office_info", True)
    if include_office:
        office_lines = [
            f"• 상호: {data.get('office_name', '참좋은공인중개사사무소')}",
            f"• 대표: {data.get('office_owner', '신제환')}",
            f"• 등록번호: {data.get('office_reg_no', '제 26530-2026-00009 호')}",
            f"• 소재지: {data.get('office_address', '부산광역시 사상구 강선로 9, 1층')}",
            f"• 연락처: {data.get('office_phone', '010-9667-4201')}"
        ]
        as_name = data.get("assistant_name", "").strip()
        as_phone = data.get("assistant_phone", "").strip()
        if as_name or as_phone:
            as_info = f"{as_name} ({as_phone})".strip() if as_phone else as_name
            office_lines.append(f"• 담당(소공): {as_info}")
        office_full = "\n".join(office_lines)
        items.append({"num": 16, "name": "중개사무소 정보", "val": office_full, "guide": "5대 필수 명시"})

    return items


def generate_blog_html_table(data: dict, items: list = None) -> str:
    """네이버 블로그 스마트에디터에 바로 붙여넣을 수 있는 세련된 HTML 표 서식 생성"""
    if items is None:
        items = get_ordered_spec_table_data(data)
    
    html = """
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Malgun Gothic', sans-serif; max-width: 780px; margin: 25px auto; border: 2px solid #232529; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.08);">
    <div style="background-color: #232529; color: #FFFFFF; padding: 14px 20px; font-size: 17px; font-weight: 700; display: flex; align-items: center; justify-content: space-between;">
        <span>📋 중개대상물 인터넷 표시·광고 명시사항</span>
        <span style="font-size: 13px; color: #F48A26; font-weight: 600;">[공인중개사법 시행령 준수]</span>
    </div>
    <table style="width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; background: #FFFFFF;">
        <tbody>
"""
    for i, it in enumerate(items):
        bg_col = "#F9FAFC" if i % 2 == 0 else "#FFFFFF"
        val_escaped = it['val'].replace("\n", "<br/>")
        html += f"""
            <tr style="background-color: {bg_col}; border-bottom: 1px solid #E5E8EB;">
                <td style="width: 25%; padding: 10px 14px; font-weight: 700; color: #333D4B; border-right: 1px solid #E5E8EB; vertical-align: top;">
                    <span style="display: inline-block; width: 18px; color: #F48A26; font-size: 12px;">{it['num']}.</span> {it['name']}
                </td>
                <td style="width: 75%; padding: 10px 14px; color: #1E2022; line-height: 1.5;">
                    {val_escaped}
                </td>
            </tr>
"""
    include_office = data.get("include_office_info", True)
    if include_office:
        office_name = data.get('office_name', '참좋은공인중개사사무소')
        office_owner = data.get('office_owner', '신제환')
        office_phone = data.get('office_phone', '010-9667-4201')
        office_addr = data.get('office_address', '부산 사상구 강선로 9, 1층')
        as_name = data.get("assistant_name", "").strip()
        as_phone = data.get("assistant_phone", "").strip()
        
        as_tag = f" | 👤 담당(소공): {as_name} ({as_phone})" if (as_name or as_phone) else ""
        html += f"""
        </tbody>
    </table>
    <div style="background-color: #F48A26; color: #FFFFFF; padding: 12px 20px; font-size: 14px; font-weight: 600; text-align: center;">
        🏢 {office_name} (대표 {office_owner}) ☎ {office_phone}{as_tag} | {office_addr}
    </div>
</div>
"""
    else:
        html += """
        </tbody>
    </table>
</div>
"""
    return html.strip()

def generate_clipboard_text(data: dict, items: list = None) -> str:
    """블로그 본문 또는 카카오톡 전송용 일반 텍스트 서식"""
    if items is None:
        items = get_ordered_spec_table_data(data)
    lines = [
        "═══════════════════════════════════════════",
        "📋 [중개대상물 인터넷 표시·광고 명시사항]",
        "═══════════════════════════════════════════"
    ]
    for it in items:
        lines.append(f"■ {it['num']:02d}. {it['name']}: {it['val']}")
    
    include_office = data.get("include_office_info", True)
    if include_office:
        lines.append("───────────────────────────────────────────")
        lines.append(f"🏢 {data.get('office_name', '참좋은공인중개사사무소')} (대표: {data.get('office_owner', '신제환')})")
        lines.append(f"📞 직통 문의: {data.get('office_phone', '010-9667-4201')}")
        lines.append(f"📍 등록번호: {data.get('office_reg_no', '제 26530-2026-00009 호')}")
        lines.append(f"📍 사무소 소재지: {data.get('office_address', '부산광역시 사상구 강선로 9, 1층')}")
        as_name = data.get("assistant_name", "").strip()
        as_phone = data.get("assistant_phone", "").strip()
        if as_name or as_phone:
            as_info = f"{as_name} ({as_phone})".strip() if as_phone else as_name
            lines.append(f"👤 담당(소공): {as_info}")
        lines.append("═══════════════════════════════════════════")
    else:
        lines.append("═══════════════════════════════════════════")
    return "\n".join(lines)

def generate_naver_ad_guide_text(data: dict, items: list = None) -> str:
    """네이버 부동산 매물 등록창을 보면서 그대로 1:1 대조 복사할 수 있는 가이드 텍스트"""
    if items is None:
        items = get_ordered_spec_table_data(data)
    lines = [
        "📝 [네이버 부동산 광고 입력 체크리스트 - 순서 1:1 매칭]",
        "───────────────────────────────────────────"
    ]
    for it in items:
        lines.append(f"[{it['num']:02d}] {it['name']}")
        lines.append(f"    ▶ 입력값: {it['val']}")
        lines.append(f"    ℹ️ 점검사항: {it['guide']}")
        lines.append("")
    return "\n".join(lines)

def render_spec_table_image(data: dict, items: list = None) -> Image.Image:
    """
    1080px 고화질 '중개대상물 인터넷 표시·광고 명시사항' 카드 이미지 렌더링 (Pillow)
    블로그 포스팅 이미지 및 스마트폰 보관용
    """
    if items is None:
        items = get_ordered_spec_table_data(data)
    
    img_w = 1080
    # 높이 계산 (여유 있게 1600px로 잡고 마지막에 크롭)
    estimated_h = 1750
    img = Image.new("RGBA", (img_w, estimated_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    # 폰트 로드
    font_title = get_font("NanumGothicExtraBold.ttf", 36)
    font_sub = get_font("NanumGothicBold.ttf", 22)
    font_trade_badge = get_font("NanumGothicExtraBold.ttf", 32)
    font_label = get_font("NanumGothicBold.ttf", 24)
    font_val = get_font("NanumGothic.ttf", 23)
    font_val_bold = get_font("NanumGothicBold.ttf", 24)
    font_footer = get_font("NanumGothicBold.ttf", 25)
    font_footer_sub = get_font("NanumGothic.ttf", 19)
    font_footer_brand = get_font("NanumGothicBold.ttf", 22)

    # 1. 상단 헤더 영역 (다크 네이비 #1E2022)
    header_h = 150
    draw.rectangle([(0, 0), (img_w, header_h)], fill=(30, 32, 34, 255))
    
    # 주황색 액센트 라인 (상단 6px)
    draw.rectangle([(0, 0), (img_w, 6)], fill=(244, 138, 38, 255))

    # 헤더 텍스트
    draw.text((45, 38), "중개대상물 인터넷 표시·광고 명시사항", font=font_title, fill=(255, 255, 255, 255))
    draw.text((45, 92), "공인중개사법 제18조의2 및 동법 시행령 제17조의2 준수", font=font_sub, fill=(244, 138, 38, 255))

    # 우측 거래 형태 배지 (글자 크기 키우고 정중앙 완벽 배치)
    trade = str(data.get("trade_type", "매매")).strip() or "매매"
    badge_w = 160
    badge_h = 66
    badge_x1 = img_w - 45 - badge_w
    badge_y1 = (header_h - badge_h) // 2
    badge_x2 = badge_x1 + badge_w
    badge_y2 = badge_y1 + badge_h
    draw.rounded_rectangle([(badge_x1, badge_y1), (badge_x2, badge_y2)], radius=12, fill=(244, 138, 38, 255))

    # 텍스트 바운딩 박스를 이용한 정확한 수평/수직 정중앙 좌표 계산
    bbox = font_trade_badge.getbbox(trade)
    t_w = bbox[2] - bbox[0]
    t_h = bbox[3] - bbox[1]
    t_x = badge_x1 + (badge_w - t_w) / 2 - bbox[0]
    t_y = badge_y1 + (badge_h - t_h) / 2 - bbox[1]
    draw.text((t_x, t_y), trade, font=font_trade_badge, fill=(255, 255, 255, 255))

    # 2. 본문 테이블 렌더링
    cur_y = header_h + 30
    margin_x = 45
    col_w_label = 280
    col_w_val = img_w - (margin_x * 2) - col_w_label
    row_pad_y = 12

    for i, it in enumerate(items):
        is_highlight = it["name"] in ["소재지", "가격", "거래 형태", "공급/전용면적"]
        bg_color = (248, 249, 251, 255) if i % 2 == 0 else (255, 255, 255, 255)
        
        # 텍스트 줄바꿈 처리
        val_lines = []
        raw_lines = it["val"].split("\n")
        for rl in raw_lines:
            # 글자수가 길면 줄바꿈
            max_char = 38
            if len(rl) > max_char:
                val_lines.append(rl[:max_char])
                val_lines.append(rl[max_char:])
            else:
                val_lines.append(rl)

        row_content_h = max(42, len(val_lines) * 32 + (row_pad_y * 2))
        
        # 행 배경
        draw.rounded_rectangle(
            [(margin_x, cur_y), (img_w - margin_x, cur_y + row_content_h)],
            radius=6,
            fill=bg_color
        )
        # 행 하단 구분선
        draw.line([(margin_x, cur_y + row_content_h), (img_w - margin_x, cur_y + row_content_h)], fill=(229, 232, 235, 255), width=1)

        # 항목명 (좌측)
        num_str = f"{it['num']:02d}."
        draw.text((margin_x + 16, cur_y + row_pad_y), num_str, font=font_label, fill=(244, 138, 38, 255))
        draw.text((margin_x + 60, cur_y + row_pad_y), it["name"], font=font_label, fill=(51, 61, 75, 255))

        # 내용 (우측)
        text_font = font_val_bold if is_highlight else font_val
        val_color = (235, 87, 87, 255) if it["name"] == "가격" else ((15, 20, 25, 255) if is_highlight else (70, 75, 80, 255))
        
        v_y = cur_y + row_pad_y
        for vl in val_lines:
            draw.text((margin_x + col_w_label, v_y), vl, font=text_font, fill=val_color)
            v_y += 32

        cur_y += row_content_h + 4

    # 3. 하단 풋터 영역 (상단 헤더와 일체감을 이루는 프리미엄 다크 네이비 + 주황 액센트 라인 + 로고 이미지)
    cur_y += 25
    include_office = data.get("include_office_info", True)

    # 로고 이미지 로드 준비
    logo_path = os.path.join(ASSETS_DIR, "logo.png")
    logo_img = None
    if os.path.exists(logo_path):
        try:
            logo_img = Image.open(logo_path).convert("RGBA")
        except Exception:
            logo_img = None

    if include_office:
        # 중개사무소 정보 포함 시 (소공 유무에 따라 높이 150~180px 유동 조절)
        as_name = data.get("assistant_name", "").strip()
        as_phone = data.get("assistant_phone", "").strip()
        has_assistant = bool(as_name or as_phone)
        footer_h = 175 if has_assistant else 150

        # 다크 네이비 배경 (#1E2022) 및 주황색 6px 라인 (#F48A26)
        draw.rectangle([(0, cur_y), (img_w, cur_y + footer_h)], fill=(30, 32, 34, 255))
        draw.rectangle([(0, cur_y), (img_w, cur_y + 6)], fill=(244, 138, 38, 255))

        logo_w_total = 0
        if logo_img:
            try:
                lh = 84
                lw = int(logo_img.width * (lh / logo_img.height))
                resized_logo = logo_img.resize((lw, lh), Image.Resampling.LANCZOS)
                logo_pad_top = (footer_h - lh) // 2
                draw.rounded_rectangle([(margin_x, cur_y + logo_pad_top - 6), (margin_x + lw + 16, cur_y + logo_pad_top + lh + 6)], radius=12, fill=(255, 255, 255, 240))
                img.paste(resized_logo, (margin_x + 8, cur_y + logo_pad_top), resized_logo)
                logo_w_total = lw + 36
            except Exception:
                logo_w_total = 0

        text_x = margin_x + logo_w_total
        office_name = data.get('office_name', '참좋은공인중개사사무소')
        office_owner = data.get('office_owner', '신제환')
        draw.text((text_x, cur_y + 22), f"{office_name}  |  대표: {office_owner}", font=font_footer, fill=(255, 255, 255, 255))
        
        office_phone = data.get('office_phone', '010-9667-4201')
        office_reg_no = data.get('office_reg_no', '제 26530-2026-00009 호')
        office_addr = data.get('office_address', '부산광역시 사상구 강선로 9, 1층')

        footer_line2 = f"☎ 직통 문의: {office_phone}  •  등록번호: {office_reg_no}"
        draw.text((text_x, cur_y + 60), footer_line2, font=font_footer_sub, fill=(225, 230, 235, 255))
        
        if has_assistant:
            as_info = f"{as_name} ({as_phone})".strip() if as_phone else as_name
            footer_line3 = f"[담당 소공] {as_info}"
            draw.text((text_x, cur_y + 94), footer_line3, font=font_footer_sub, fill=(244, 138, 38, 255))
            footer_line4 = f"소재지: {office_addr}"
            draw.text((text_x, cur_y + 128), footer_line4, font=get_font("NanumGothic.ttf", 17), fill=(180, 190, 200, 255))
        else:
            footer_line3 = f"소재지: {office_addr}"
            draw.text((text_x, cur_y + 96), footer_line3, font=font_footer_sub, fill=(180, 190, 200, 255))

        total_h = cur_y + footer_h
    else:
        # 중개사무소 정보를 제외하는 경우에도 상단 헤더와 완벽하게 어울리는 브랜드 마감 풋터 (높이 135px)
        footer_h = 135
        # 다크 네이비 배경 (#1E2022)
        draw.rectangle([(0, cur_y), (img_w, cur_y + footer_h)], fill=(30, 32, 34, 255))
        # 상단 6px 주황색 액센트 라인 (#F48A26)
        draw.rectangle([(0, cur_y), (img_w, cur_y + 6)], fill=(244, 138, 38, 255))

        logo_w_total = 0
        if logo_img:
            try:
                lh = 80
                lw = int(logo_img.width * (lh / logo_img.height))
                resized_logo = logo_img.resize((lw, lh), Image.Resampling.LANCZOS)
                draw.rounded_rectangle([(margin_x, cur_y + 20), (margin_x + lw + 16, cur_y + 20 + lh + 10)], radius=10, fill=(255, 255, 255, 240))
                img.paste(resized_logo, (margin_x + 8, cur_y + 25), resized_logo)
                logo_w_total = lw + 36
            except Exception:
                logo_w_total = 0

        text_x = margin_x + logo_w_total
        draw.text((text_x, cur_y + 28), "중개대상물 인터넷 표시·광고 명시사항 (공식 확인 매물)", font=font_footer, fill=(255, 255, 255, 255))
        draw.text((text_x, cur_y + 68), "공인중개사법 시행령에 따른 법정 필수 15개 항목을 엄격히 준수한 매물 정보입니다.", font=font_footer_sub, fill=(244, 138, 38, 255))
        draw.text((text_x, cur_y + 98), "정직과 신뢰를 바탕으로 투명하고 안전한 부동산 거래 문화를 선도합니다.", font=get_font("NanumGothic.ttf", 17), fill=(180, 190, 200, 255))

        total_h = cur_y + footer_h

    # 최종 크롭
    cropped_img = img.crop((0, 0, img_w, total_h))
    return cropped_img
