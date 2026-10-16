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

# 16개 항목 기본값 세팅 (신소장님 사상 중흥S-클래스 예시 기준)
DEFAULT_SPEC = {
    "location": "부산광역시 사상구 덕포동 220 (사상 중흥S-클래스 105동)",
    "area_supply": "111.42",
    "area_exclusive": "79.85",
    "floor_info": "25 / 36층",
    "floor_type": "해당층 직접입력", # 또는 "고층", "중층", "저층"
    "room_bath": "방 3 / 욕실 2개",
    "maintenance_fee": "18만 원",
    "maintenance_detail": "공용관리비 약 13만원 (수도/전기/가스 실사용량 별도 부과)",
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
    "office_name": "참좋은공인중개사사무소",
    "office_owner": "신제환",
    "office_reg_no": "제 26530-2021-00045 호",
    "office_address": "부산광역시 사상구 사상로 200, 1층",
    "office_phone": "010-9667-4201",
}

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
        "guide": "평수 병기 시 ㎡를 반드시 함께 표기 (전용률 자동 계산)",
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
    """공급면적과 전용면적으로 평형 환산 및 전용률 텍스트 생성"""
    try:
        sup_m2 = float(supply_str.replace(",", "").strip())
        exc_m2 = float(exclusive_str.replace(",", "").strip())
        sup_py = round(sup_m2 * 0.3025, 1)
        exc_py = round(exc_m2 * 0.3025, 1)
        rate = round((exc_m2 / sup_m2) * 100, 1) if sup_m2 > 0 else 0
        summary_m2 = f"{sup_m2:.2f}㎡ / {exc_m2:.2f}㎡ (전용률 {rate}%)"
        summary_py = f"약 {sup_py}평 / {exc_py}평"
        return summary_m2, summary_py
    except Exception:
        return f"{supply_str}㎡ / {exclusive_str}㎡", ""

def get_ordered_spec_table_data(data: dict) -> list[dict]:
    """16개 항목 순서대로 정리된 데이터 리스트 반환"""
    area_m2, area_py = format_area_text(data.get("area_supply", "111.42"), data.get("area_exclusive", "79.85"))
    area_display = f"{area_m2} [ {area_py} ]" if area_py else area_m2

    m_fee = data.get("maintenance_fee", "18만 원")
    m_detail = data.get("maintenance_detail", "")
    m_display = f"{m_fee} ({m_detail})" if m_detail else m_fee

    trade = data.get("trade_type", "매매")
    price = data.get("price_text", "6억 2,000만 원")
    dep_sub = data.get("deposit_sub", "")
    price_display = f"{price}" + (f" (기보증금/월세: {dep_sub})" if dep_sub and dep_sub != "- / -" else "")

    office_lines = [
        f"• 상호: {data.get('office_name', '참좋은공인중개사사무소')}",
        f"• 대표: {data.get('office_owner', '신제환')}",
        f"• 등록번호: {data.get('office_reg_no', '제 26530-2021-00045 호')}",
        f"• 소재지: {data.get('office_address', '부산광역시 사상구 사상로 200, 1층')}",
        f"• 연락처: {data.get('office_phone', '010-9667-4201')}"
    ]
    office_full = "\n".join(office_lines)

    items = [
        {"num": 1, "name": "소재지", "val": data.get("location", ""), "guide": "동·리 및 지번 표기 필수 (동·호수 생략 가능)"},
        {"num": 2, "name": "공급/전용면적", "val": area_display, "guide": "평수 병기 시 ㎡ 단위 반드시 함께 표기"},
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
        {"num": 16, "name": "중개사무소 정보", "val": office_full, "guide": "상호, 소재지, 연락처, 등록번호, 대표자 5대 항목 필수"},
    ]
    return items

def generate_blog_html_table(data: dict) -> str:
    """네이버 블로그 스마트에디터에 바로 붙여넣을 수 있는 세련된 HTML 표 서식 생성"""
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
    html += """
        </tbody>
    </table>
    <div style="background-color: #F48A26; color: #FFFFFF; padding: 12px 20px; font-size: 14px; font-weight: 600; text-align: center;">
        🏢 참좋은공인중개사사무소 (대표 신제환) ☎ 010-9667-4201 | 부산 사상구 사상로 200
    </div>
</div>
"""
    return html.strip()

def generate_clipboard_text(data: dict) -> str:
    """블로그 본문 또는 카카오톡 전송용 일반 텍스트 서식"""
    items = get_ordered_spec_table_data(data)
    lines = [
        "═══════════════════════════════════════════",
        "📋 [중개대상물 인터넷 표시·광고 명시사항]",
        "═══════════════════════════════════════════"
    ]
    for it in items:
        lines.append(f"■ {it['num']:02d}. {it['name']}: {it['val']}")
    lines.append("───────────────────────────────────────────")
    lines.append(f"🏢 {data.get('office_name', '참좋은공인중개사사무소')} (대표: {data.get('office_owner', '신제환')})")
    lines.append(f"📞 직통 문의: {data.get('office_phone', '010-9667-4201')}")
    lines.append(f"📍 등록번호: {data.get('office_reg_no', '제 26530-2021-00045 호')}")
    lines.append(f"📍 사무소 소재지: {data.get('office_address', '부산광역시 사상구 사상로 200, 1층')}")
    lines.append("═══════════════════════════════════════════")
    return "\n".join(lines)

def generate_naver_ad_guide_text(data: dict) -> str:
    """네이버 부동산 매물 등록창을 보면서 그대로 1:1 대조 복사할 수 있는 가이드 텍스트"""
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

def render_spec_table_image(data: dict) -> Image.Image:
    """
    1080px 고화질 '중개대상물 인터넷 표시·광고 명시사항' 카드 이미지 렌더링 (Pillow)
    블로그 포스팅 이미지 및 스마트폰 보관용
    """
    items = get_ordered_spec_table_data(data)
    
    img_w = 1080
    # 높이 계산 (여유 있게 1600px로 잡고 마지막에 크롭)
    estimated_h = 1750
    img = Image.new("RGBA", (img_w, estimated_h), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    # 폰트 로드
    font_title = get_font("NanumGothicExtraBold.ttf", 36)
    font_sub = get_font("NanumGothicBold.ttf", 22)
    font_label = get_font("NanumGothicBold.ttf", 24)
    font_val = get_font("NanumGothic.ttf", 23)
    font_val_bold = get_font("NanumGothicBold.ttf", 24)
    font_footer = get_font("NanumGothicBold.ttf", 24)
    font_footer_sub = get_font("NanumGothic.ttf", 19)

    # 1. 상단 헤더 영역 (다크 네이비 #1E2022)
    header_h = 150
    draw.rectangle([(0, 0), (img_w, header_h)], fill=(30, 32, 34, 255))
    
    # 주황색 액센트 라인
    draw.rectangle([(0, 0), (img_w, 6)], fill=(244, 138, 38, 255))

    # 헤더 텍스트
    draw.text((45, 38), "중개대상물 인터넷 표시·광고 명시사항", font=font_title, fill=(255, 255, 255, 255))
    draw.text((45, 92), "공인중개사법 제18조의2 및 동법 시행령 제17조의2 준수", font=font_sub, fill=(244, 138, 38, 255))

    # 우측 배지
    trade = data.get("trade_type", "매매")
    draw.rounded_rectangle([(img_w - 180, 48), (img_w - 45, 102)], radius=10, fill=(244, 138, 38, 255))
    draw.text((img_w - 150, 58), trade, font=font_sub, fill=(255, 255, 255, 255))

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

    # 3. 하단 풋터 영역 (참좋은공인중개사사무소)
    cur_y += 20
    footer_h = 130
    draw.rectangle([(0, cur_y), (img_w, cur_y + footer_h)], fill=(244, 138, 38, 255))

    # 로고 이미지 삽입 시도
    logo_path = os.path.join(ASSETS_DIR, "logo.png")
    logo_drawn = False
    if os.path.exists(logo_path):
        try:
            logo_img = Image.open(logo_path).convert("RGBA")
            # 풋터에 맞게 리사이즈
            lh = 75
            lw = int(logo_img.width * (lh / logo_img.height))
            logo_img = logo_img.resize((lw, lh), Image.Resampling.LANCZOS)
            img.paste(logo_img, (margin_x, cur_y + 28), logo_img)
            logo_drawn = True
        except Exception:
            pass

    text_x = (margin_x + 95) if logo_drawn else margin_x
    draw.text((text_x, cur_y + 28), f"{data.get('office_name', '참좋은공인중개사사무소')}  |  대표: {data.get('office_owner', '신제환')}", font=font_footer, fill=(255, 255, 255, 255))
    draw.text((text_x, cur_y + 68), f"직통: {data.get('office_phone', '010-9667-4201')}  •  등록번호: {data.get('office_reg_no', '제 26530-2021-00045 호')}", font=font_footer_sub, fill=(255, 240, 230, 255))

    # 최종 크롭
    total_h = cur_y + footer_h
    cropped_img = img.crop((0, 0, img_w, total_h))
    return cropped_img
