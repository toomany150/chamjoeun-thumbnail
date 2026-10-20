"""
상가(근린생활시설/상가점포/상가건물) 매물 인터넷 표시·광고 점검표 및 블로그 서식/카드 이미지 생성 모듈
- 공인중개사법 시행령 및 중개대상물 인터넷 표시·광고 명시사항 세부기준 완벽 준수
- 상가 특화 항목: 주출입구 방향, 화장실 구분, 권리금 유무, 추천/현재 업종, 계약전력 및 주요설비, 임대차 수익률(매매 시)
- 네이버 부동산 상가 매물 등록 1:1 대조 체크리스트
- 네이버 블로그 스마트에디터용 프리미엄 다크골드 HTML 표 생성
- 블로그 텍스트 복사 및 1080px 고화질 상가 중개대상물 표시 카드 이미지 (PNG) 렌더링
"""

import os
import io
import re
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

def get_font(font_name: str, size: int) -> ImageFont.FreeTypeFont:
    """폰트를 안전하게 로드합니다."""
    candidates = [
        os.path.join(ASSETS_DIR, "fonts", font_name),
        os.path.join(ASSETS_DIR, "fonts", "NanumGothicExtraBold.ttf"),
        os.path.join(ASSETS_DIR, "fonts", "NanumGothicBold.ttf"),
        os.path.join(ASSETS_DIR, "fonts", "NanumGothic.ttf"),
        f"C:/Windows/Fonts/{font_name}",
        "C:/Windows/Fonts/NanumGothicBold.ttf",
        "C:/Windows/Fonts/malgunbd.ttf",
        "C:/Windows/Fonts/malgun.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

# ----------------------------------------------------
# 🏬 상가 기본값 세팅 (임차 & 매매 2대 모드)
# ----------------------------------------------------
DEFAULT_COMMERCIAL_SPEC_LEASE = {
    "comm_mode": "lease",  # "lease" or "sale"
    "location": "부산광역시 사상구 괘법동 560-1, 1층",
    "area_exclusive": "82.64",    # 전용 25평 (㎡)
    "area_contract": "125.00",    # 계약/공급면적 (㎡)
    "floor_info": "1층 / 지상 5층",
    "restroom": "내부 남녀구분 화장실 완비",
    "maintenance_fee": "월 15만 원",
    "maintenance_detail": "공용관리비 약 10만 원 (수도·전기·가스는 실사용량에 따라 별도 부과)",
    "trade_type": "월세",
    "price_text": "보증금 3,000만 원 / 월 180만 원",
    "premium_fee": "무권리 (권리금 없음)",
    "direction": "남서향 (주된 출입구 기준)",
    "move_in_date": "즉시입점 협의가능",
    "parking": "총 20대 (점포 무료주차 1대 / 고객 유료 주차타워 완비)",
    "current_use": "커피전문점 성업중 (원상복구 및 시설협의 가능)",
    "recommended_use": "카페, 음식점, 베이커리, 판매점, 뷰티샵, 사무실 등",
    "building_use": "제1종 근린생활시설 (휴게음식점)",
    "approval_date": "2018년 06월 15일",
    "facility_info": "전기 15kW 승압완료, 도시가스, 상하수도 인입, 천장형 시스템냉난방기",
    
    # 중개사무소 정보
    "office_name": "참좋은공인중개사사무소",
    "office_owner": "신제환",
    "office_reg_no": "제 26530-2021-00045 호",
    "office_address": "부산광역시 사상구 사상로 200, 1층",
    "office_phone": "010-9667-4201",
    "include_office_info": True,
    "assistant_name": "",
    "assistant_phone": "",
}

DEFAULT_COMMERCIAL_SPEC_SALE = {
    "comm_mode": "sale",
    "location": "부산광역시 사상구 사상로 190, 1층~3층 통상가",
    "area_exclusive": "396.69",   # 전용 120평
    "area_contract": "528.92",    # 계약/연면적 160평
    "floor_info": "1~3층 / 총 5층",
    "restroom": "각 층별 남녀 분리 화장실",
    "maintenance_fee": "자체관리",
    "maintenance_detail": "임차인 실사용량 각 점포별 직접 납부 (공용관리비 실비 정산)",
    "trade_type": "매매",
    "price_text": "15억 원",
    "deposit_rent_summary": "보증금 8,000만 원 / 월 650만 원",
    "loan_amount": "6억 원 (대출 승계 가능)",
    "actual_investment": "8억 2,000만 원 (실투자금)",
    "yield_rate": "확정 수익률 연 6.8% (안정적인 고수익)",
    "premium_fee": "해당사항 없음 (우량 임차인 성업중)",
    "direction": "동향 (대로변 주출입구 기준)",
    "move_in_date": "임대차 승계 매매 (안정적인 월세수입 즉시 발생)",
    "parking": "총 12대 자주식 주차장",
    "current_use": "1층 프랜차이즈 카페, 2층 병의원, 3층 학원 성업중",
    "recommended_use": "수익형 부동산 투자 및 안정적 월세 임대사업용",
    "building_use": "제1종 및 제2종 근린생활시설",
    "approval_date": "2019년 11월 20일",
    "facility_info": "승강기(엘리베이터) 1대, 각 호실 개별 시스템에어컨, 동력전기 완비",
    
    # 중개사무소 정보
    "office_name": "참좋은공인중개사사무소",
    "office_owner": "신제환",
    "office_reg_no": "제 26530-2021-00045 호",
    "office_address": "부산광역시 사상구 사상로 200, 1층",
    "office_phone": "010-9667-4201",
    "include_office_info": True,
    "assistant_name": "",
    "assistant_phone": "",
}

def format_commercial_area_text(exclusive_str: str, contract_str: str) -> str:
    """전용면적과 계약(공급)면적을 바탕으로 법정계량단위(㎡) 및 전용률 텍스트 생성"""
    try:
        exc_m2 = float(str(exclusive_str).replace(",", "").strip())
        con_m2 = float(str(contract_str).replace(",", "").strip()) if contract_str else 0.0
        if con_m2 > 0:
            rate = round((exc_m2 / con_m2) * 100, 1)
            return f"전용 {exc_m2:.2f}㎡ / 계약 {con_m2:.2f}㎡ (전용률 {rate}%)"
        else:
            return f"전용 {exc_m2:.2f}㎡"
    except Exception:
        if contract_str:
            return f"전용 {exclusive_str}㎡ / 계약 {contract_str}㎡"
        return f"전용 {exclusive_str}㎡"

def get_commercial_spec_table_data(data: dict) -> list[dict]:
    """상가 전용 16대 필수 법정 점검항목 리스트 생성"""
    is_sale = str(data.get("comm_mode", "lease")).lower() == "sale" or "매매" in str(data.get("trade_type", ""))
    
    area_display = format_commercial_area_text(data.get("area_exclusive", "82.64"), data.get("area_contract", "125.00"))

    # 관리비 처리
    m_fee = str(data.get("maintenance_fee", "월 15만 원")).strip()
    m_detail = str(data.get("maintenance_detail", "")).strip()
    if m_detail:
        m_display = f"{m_fee}\n• 세부내역: {m_detail}"
    else:
        m_display = m_fee

    # 가격 표시
    trade = str(data.get("trade_type", "매매" if is_sale else "월세")).strip()
    price = str(data.get("price_text", "15억 원" if is_sale else "보증금 3,000만 원 / 월 180만 원")).strip()

    items = [
        {"num": 1, "name": "소재지", "val": data.get("location", ""), "guide": "동·리 및 지번 표기 (호수는 의뢰인 동의 시 층수만 표기 가능)"},
        {"num": 2, "name": "면적 (전용/계약)", "val": area_display, "guide": "법정단위 ㎡ 단독 표기 (평수 제외, 전용률 자동 산출)"},
        {"num": 3, "name": "해당층 / 총층수", "val": data.get("floor_info", ""), "guide": "해당층 및 건축물 전체 지상/지하 총층수 명시"},
        {"num": 4, "name": "화장실 구분", "val": data.get("restroom", "내부 남녀구분 화장실"), "guide": "상가 필수: 내부 남녀구분, 층별 공용, 단독 등"},
        {"num": 5, "name": "관리비", "val": m_display, "guide": "정액 관리비 및 세부내역(청소, 승강기, 공용전기 등) 분리 표기"},
        {"num": 6, "name": "거래 형태", "val": trade, "guide": "월세, 전세, 매매 중 명확히 표기"},
        {"num": 7, "name": "거래 가격", "val": price, "guide": "보증금/월세 또는 매매가 명확히 명시 (부가세 별도 여부 등)"},
    ]

    if is_sale:
        # 매매 시: 수익률 & 투자금 분석 추가
        dep_rent = data.get("deposit_rent_summary", "보증금 8,000만 / 월 650만")
        loan = data.get("loan_amount", "-")
        act_inv = data.get("actual_investment", "-")
        y_rate = data.get("yield_rate", "")
        
        invest_lines = [f"• 임대현황: {dep_rent}"]
        if loan and loan != "-":
            invest_lines.append(f"• 융자금(대출): {loan}")
        if act_inv and act_inv != "-":
            invest_lines.append(f"• 실투자금: {act_inv}")
        if y_rate:
            invest_lines.append(f"• 연간 수익률: {y_rate}")
        
        items.append({"num": 8, "name": "수익률 & 투자금 분석", "val": "\n".join(invest_lines), "guide": "수익형 상가 핵심 투자 분석표"})
    else:
        # 임차 시: 권리금 정보
        prem = data.get("premium_fee", "무권리 (권리금 없음)")
        items.append({"num": 8, "name": "권리금 유무", "val": prem, "guide": "무권리, 시설/바닥 권리금 협의 여부 명시"})

    items.extend([
        {"num": 9, "name": "방향 (출입구 기준)", "val": data.get("direction", "남향 (주된 출입구 기준)"), "guide": "상가는 주실이 없으므로 주된 출입구 기준 명시"},
        {"num": 10, "name": "입점(입주)가능일", "val": data.get("move_in_date", "즉시입점 협의가능"), "guide": "즉시입점, 날짜 협의, 임대차 승계 여부"},
        {"num": 11, "name": "총주차대수", "val": data.get("parking", "총 20대 (점포 1대 무료)"), "guide": "건물 전체 주차대수 및 해당 점포 무료/유료 조건"},
        {"num": 12, "name": "현재 / 추천 업종", "val": f"• 현재: {data.get('current_use', '공실')}\n• 추천: {data.get('recommended_use', '일반음식점, 카페, 판매점 등')}", "guide": "입점 가능 추천 업종 및 인허가 적합성"},
        {"num": 13, "name": "건축물 용도", "val": data.get("building_use", "제1종 근린생활시설"), "guide": "건축물대장 상 법정 용도 (제1·2종 근린생활시설 등)"},
        {"num": 14, "name": "사용승인일 (준공일)", "val": data.get("approval_date", ""), "guide": "건축물대장 상 사용승인일 기재 필수"},
        {"num": 15, "name": "주요 설비 및 시설", "val": data.get("facility_info", "전기용량, 가스, 승강기 유무"), "guide": "계약전력(kW), 도시가스, 덕트, 엘리베이터 등"},
    ])

    if data.get("include_office_info", True):
        office_lines = [
            f"• 상호: {data.get('office_name', '참좋은공인중개사사무소')}",
            f"• 대표: {data.get('office_owner', '신제환')}",
            f"• 등록번호: {data.get('office_reg_no', '제 26530-2021-00045 호')}",
            f"• 소재지: {data.get('office_address', '부산광역시 사상구 사상로 200, 1층')}",
            f"• 직통전화: {data.get('office_phone', '010-9667-4201')}"
        ]
        as_name = data.get("assistant_name", "").strip()
        as_phone = data.get("assistant_phone", "").strip()
        if as_name or as_phone:
            as_info = f"{as_name} ({as_phone})".strip() if as_phone else as_name
            office_lines.append(f"• 담당(소공): {as_info}")
        office_full = "\n".join(office_lines)
        items.append({"num": 16, "name": "중개사무소 정보", "val": office_full, "guide": "상호, 소재지, 연락처, 등록번호, 대표자 성명 5대 항목 필수"})

    return items


def generate_commercial_blog_html_table(data: dict) -> str:
    """네이버 블로그 스마트에디터에 바로 붙여넣을 수 있는 세련된 상가 전용 다크골드 HTML 표 생성"""
    items = get_commercial_spec_table_data(data)
    is_sale = str(data.get("comm_mode", "lease")).lower() == "sale" or "매매" in str(data.get("trade_type", ""))
    type_badge = "상가 매매 (수익형)" if is_sale else "상가 임대차 (월세)"

    html = f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Malgun Gothic', 'Pretendard', sans-serif; max-width: 780px; margin: 25px auto; border: 2px solid #1E2229; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 18px rgba(0,0,0,0.12);">
    <div style="background: linear-gradient(135deg, #181C24 0%, #222834 100%); color: #FFFFFF; padding: 15px 22px; font-size: 17px; font-weight: 700; display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #DAA844;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <span style="color: #DAA844; font-size: 20px;">🏬</span>
            <span style="font-size: 16px;">중개대상물 인터넷 표시·광고 명시사항 <span style="font-size: 14px; color: #DAA844;">[{type_badge}]</span></span>
        </div>
        <span style="font-size: 12px; background: rgba(218,168,68,0.2); color: #DAA844; border: 1px solid #DAA844; padding: 4px 10px; border-radius: 20px; font-weight: 600;">공인중개사법 시행령 준수</span>
    </div>
    <table style="width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; background: #FFFFFF;">
        <tbody>
"""
    for i, it in enumerate(items):
        bg_col = "#F8F9FB" if i % 2 == 0 else "#FFFFFF"
        val_escaped = it['val'].replace("\n", "<br/>")
        is_highlight = it["name"] in ["소재지", "거래 가격", "거래 형태", "면적 (전용/계약)", "수익률 & 투자금 분석", "권리금 유무"]
        name_col = "#DAA844" if is_highlight else "#333D4B"
        val_style = "font-weight: 700; color: #1A202C;" if is_highlight else "color: #2D3748;"

        html += f"""
            <tr style="background-color: {bg_col}; border-bottom: 1px solid #E5E8EB;">
                <td style="width: 28%; padding: 11px 16px; font-weight: 700; color: {name_col}; border-right: 1px solid #E5E8EB; vertical-align: top;">
                    <span style="display: inline-block; width: 22px; color: #DAA844; font-size: 13px;">{it['num']:02d}.</span> {it['name']}
                </td>
                <td style="width: 72%; padding: 11px 16px; {val_style} line-height: 1.6;">
                    {val_escaped}
                </td>
            </tr>
"""

    if data.get("include_office_info", True):
        office_name = data.get('office_name', '참좋은공인중개사사무소')
        office_owner = data.get('office_owner', '신제환')
        office_phone = data.get('office_phone', '010-9667-4201')
        office_addr = data.get('office_address', '부산 사상구 사상로 200')
        as_name = data.get("assistant_name", "").strip()
        as_phone = data.get("assistant_phone", "").strip()
        as_tag = f" | 👤 담당: {as_name} ({as_phone})" if (as_name or as_phone) else ""

        html += f"""
        </tbody>
    </table>
    <div style="background: #181C24; color: #FFFFFF; padding: 14px 20px; font-size: 14px; font-weight: 600; text-align: center; border-top: 1px solid #DAA844;">
        <span style="color: #DAA844; font-weight: 700;">🏢 {office_name}</span> (대표 {office_owner}) ☎ {office_phone}{as_tag}<br/>
        <span style="font-size: 12px; color: #A0AEC0;">소재지: {office_addr} | 등록번호: {data.get('office_reg_no', '제 26530-2021-00045 호')}</span>
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


def generate_commercial_clipboard_text(data: dict) -> str:
    """블로그 본문 또는 카카오톡 전송용 상가 일반 텍스트 서식"""
    items = get_commercial_spec_table_data(data)
    is_sale = str(data.get("comm_mode", "lease")).lower() == "sale" or "매매" in str(data.get("trade_type", ""))
    type_badge = "상가 매매 (수익형)" if is_sale else "상가 임대차 (월세)"

    lines = [
        "═══════════════════════════════════════════",
        f"🏬 [상가 중개대상물 인터넷 표시·광고 명시사항 - {type_badge}]",
        "═══════════════════════════════════════════"
    ]
    for it in items:
        lines.append(f"■ {it['num']:02d}. {it['name']}: {it['val']}")
    
    if data.get("include_office_info", True):
        lines.append("───────────────────────────────────────────")
        lines.append(f"🏢 {data.get('office_name', '참좋은공인중개사사무소')} (대표: {data.get('office_owner', '신제환')})")
        lines.append(f"📞 직통 문의: {data.get('office_phone', '010-9667-4201')} (황금터잡이 신소장)")
        lines.append(f"📍 등록번호: {data.get('office_reg_no', '제 26530-2021-00045 호')}")
        lines.append(f"📍 사무소 소재지: {data.get('office_address', '부산광역시 사상구 사상로 200, 1층')}")
        as_name = data.get("assistant_name", "").strip()
        as_phone = data.get("assistant_phone", "").strip()
        if as_name or as_phone:
            as_info = f"{as_name} ({as_phone})".strip() if as_phone else as_name
            lines.append(f"👤 담당(소공): {as_info}")
        lines.append("═══════════════════════════════════════════")
    else:
        lines.append("═══════════════════════════════════════════")
    return "\n".join(lines)


def generate_commercial_naver_ad_guide_text(data: dict) -> str:
    """네이버 부동산 상가 매물 등록창 대조 체크리스트"""
    items = get_commercial_spec_table_data(data)
    lines = [
        "📝 [네이버 부동산 상가 광고 입력 체크리스트 - 순서 1:1 매칭]",
        "───────────────────────────────────────────"
    ]
    for it in items:
        lines.append(f"[{it['num']:02d}] {it['name']}")
        lines.append(f"    ▶ 입력값: {it['val']}")
        lines.append(f"    ℹ️ 점검사항: {it['guide']}")
        lines.append("")
    return "\n".join(lines)


def render_commercial_spec_table_image(data: dict) -> Image.Image:
    """
    1080px 고화질 상가 중개대상물 인터넷 표시·광고 명시사항 카드 이미지 렌더링 (Pillow)
    다크 골드 럭셔리 스타일 (블로그 이미지 및 모바일 보관용)
    """
    items = get_commercial_spec_table_data(data)
    is_sale = str(data.get("comm_mode", "lease")).lower() == "sale" or "매매" in str(data.get("trade_type", ""))

    img_w = 1080
    estimated_h = 1900
    img = Image.new("RGBA", (img_w, estimated_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    # 폰트 로드
    font_title = get_font("NanumGothicExtraBold.ttf", 36)
    font_sub = get_font("NanumGothicBold.ttf", 22)
    font_trade_badge = get_font("NanumGothicExtraBold.ttf", 30)
    font_label = get_font("NanumGothicBold.ttf", 24)
    font_val = get_font("NanumGothic.ttf", 23)
    font_val_bold = get_font("NanumGothicBold.ttf", 24)
    font_footer = get_font("NanumGothicBold.ttf", 25)
    font_footer_sub = get_font("NanumGothic.ttf", 19)

    # 1. 상단 헤더 영역 (다크 네이비 + 골드 헤어라인)
    header_h = 150
    draw.rectangle([(0, 0), (img_w, header_h)], fill=(18, 22, 30, 255))
    # 골드 액센트 탑 라인 (6px)
    draw.rectangle([(0, 0), (img_w, 6)], fill=(218, 168, 68, 255))

    # 헤더 텍스트
    header_title_txt = "상가(근린생활시설) 중개대상물 표시·광고"
    draw.text((45, 38), header_title_txt, font=font_title, fill=(255, 255, 255, 255))
    draw.text((45, 92), "공인중개사법 제18조의2 및 중개대상물 표시·광고 명시사항 세부기준 준수", font=font_sub, fill=(218, 168, 68, 255))

    # 우측 거래 형태 배지
    trade = str(data.get("trade_type", "매매" if is_sale else "월세")).strip()
    badge_w = 170
    badge_h = 66
    badge_x1 = img_w - 45 - badge_w
    badge_y1 = (header_h - badge_h) // 2
    badge_x2 = badge_x1 + badge_w
    badge_y2 = badge_y1 + badge_h

    badge_color = (218, 168, 68, 255)
    draw.rounded_rectangle([(badge_x1, badge_y1), (badge_x2, badge_y2)], radius=12, fill=badge_color)

    bbox = font_trade_badge.getbbox(trade)
    t_w = bbox[2] - bbox[0]
    t_h = bbox[3] - bbox[1]
    t_x = badge_x1 + (badge_w - t_w) / 2 - bbox[0]
    t_y = badge_y1 + (badge_h - t_h) / 2 - bbox[1]
    draw.text((t_x, t_y), trade, font=font_trade_badge, fill=(18, 22, 30, 255))

    # 2. 본문 테이블 렌더링
    cur_y = header_h + 30
    margin_x = 45
    col_w_label = 290
    col_w_val = img_w - (margin_x * 2) - col_w_label
    row_pad_y = 12

    for i, it in enumerate(items):
        is_highlight = it["name"] in ["소재지", "거래 가격", "거래 형태", "면적 (전용/계약)", "수익률 & 투자금 분석", "권리금 유무"]
        bg_color = (248, 249, 251, 255) if i % 2 == 0 else (255, 255, 255, 255)

        val_lines = []
        raw_lines = it["val"].split("\n")
        for rl in raw_lines:
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
        # 구분선
        draw.line([(margin_x, cur_y + row_content_h), (img_w - margin_x, cur_y + row_content_h)], fill=(229, 232, 235, 255), width=1)

        # 항목명 (좌측)
        num_str = f"{it['num']:02d}."
        draw.text((margin_x + 16, cur_y + row_pad_y), num_str, font=font_label, fill=(218, 168, 68, 255))
        draw.text((margin_x + 62, cur_y + row_pad_y), it["name"], font=font_label, fill=(40, 48, 60, 255))

        # 내용 (우측)
        text_font = font_val_bold if is_highlight else font_val
        val_color = (210, 80, 50, 255) if "가격" in it["name"] else ((18, 22, 30, 255) if is_highlight else (70, 75, 80, 255))

        v_y = cur_y + row_pad_y
        for vl in val_lines:
            draw.text((margin_x + col_w_label, v_y), vl, font=text_font, fill=val_color)
            v_y += 32

        cur_y += row_content_h + 4

    # 3. 하단 풋터 영역
    cur_y += 25
    include_office = data.get("include_office_info", True)

    logo_path = os.path.join(ASSETS_DIR, "logo_gold_emblem.png")
    if not os.path.exists(logo_path):
        logo_path = os.path.join(ASSETS_DIR, "logo.png")

    logo_img = None
    if os.path.exists(logo_path):
        try:
            logo_img = Image.open(logo_path).convert("RGBA")
        except Exception:
            logo_img = None

    if include_office:
        as_name = data.get("assistant_name", "").strip()
        as_phone = data.get("assistant_phone", "").strip()
        has_assistant = bool(as_name or as_phone)
        footer_h = 175 if has_assistant else 150

        draw.rectangle([(0, cur_y), (img_w, cur_y + footer_h)], fill=(18, 22, 30, 255))
        draw.rectangle([(0, cur_y), (img_w, cur_y + 6)], fill=(218, 168, 68, 255))

        logo_w_total = 0
        if logo_img:
            try:
                lh = 80
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
        draw.text((text_x, cur_y + 22), f"{office_name}  |  대표: {office_owner} (황금터잡이 신소장)", font=font_footer, fill=(255, 255, 255, 255))

        office_phone = data.get('office_phone', '010-9667-4201')
        office_reg_no = data.get('office_reg_no', '제 26530-2021-00045 호')
        office_addr = data.get('office_address', '부산광역시 사상구 사상로 200, 1층')

        footer_line2 = f"☎ 직통 문의: {office_phone}  •  등록번호: {office_reg_no}"
        draw.text((text_x, cur_y + 60), footer_line2, font=font_footer_sub, fill=(225, 230, 235, 255))

        if has_assistant:
            as_info = f"{as_name} ({as_phone})".strip() if as_phone else as_name
            footer_line3 = f"[담당 소공] {as_info}"
            draw.text((text_x, cur_y + 94), footer_line3, font=font_footer_sub, fill=(218, 168, 68, 255))
            footer_line4 = f"소재지: {office_addr}"
            draw.text((text_x, cur_y + 128), footer_line4, font=get_font("NanumGothic.ttf", 17), fill=(180, 190, 200, 255))
        else:
            footer_line3 = f"소재지: {office_addr}"
            draw.text((text_x, cur_y + 96), footer_line3, font=font_footer_sub, fill=(180, 190, 200, 255))

        total_h = cur_y + footer_h
    else:
        footer_h = 135
        draw.rectangle([(0, cur_y), (img_w, cur_y + footer_h)], fill=(18, 22, 30, 255))
        draw.rectangle([(0, cur_y), (img_w, cur_y + 6)], fill=(218, 168, 68, 255))

        text_x = margin_x
        draw.text((text_x, cur_y + 28), "상가(근린생활시설) 중개대상물 인터넷 표시·광고 명시사항", font=font_footer, fill=(255, 255, 255, 255))
        draw.text((text_x, cur_y + 68), "공인중개사법 시행령에 따른 법정 필수 항목을 엄격히 준수한 상가 매물 정보입니다.", font=font_footer_sub, fill=(218, 168, 68, 255))
        draw.text((text_x, cur_y + 98), "참좋은공인중개사사무소 (부산 사상구) ☎ 010-9667-4201", font=get_font("NanumGothic.ttf", 17), fill=(180, 190, 200, 255))

        total_h = cur_y + footer_h

    return img.crop((0, 0, img_w, total_h)).convert("RGB")
