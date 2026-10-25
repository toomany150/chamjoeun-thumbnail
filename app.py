import streamlit as st
import io
import os
import re
import base64
import importlib
import thumbnail_generator
import property_ad_spec
import commercial_ad_spec
import document_parser
import naver_crawler
importlib.reload(thumbnail_generator)
importlib.reload(property_ad_spec)
importlib.reload(commercial_ad_spec)
importlib.reload(document_parser)
importlib.reload(naver_crawler)
from thumbnail_generator import (
    render_thumbnail,
    render_commercial_lease_thumbnail,
    render_commercial_sale_thumbnail,
    render_a4_window_poster
)
from property_ad_spec import (
    DEFAULT_SPEC,
    SAMPLE_APT_SPEC,
    BLANK_SPEC,
    OFFICE_SPEC,
    SPEC_ITEMS_META,
    format_area_text,
    get_ordered_spec_table_data,
    generate_blog_html_table,
    generate_clipboard_text,
    generate_naver_ad_guide_text,
    render_spec_table_image
)
from commercial_ad_spec import (
    DEFAULT_COMMERCIAL_SPEC_LEASE,
    DEFAULT_COMMERCIAL_SPEC_SALE,
    format_commercial_area_text,
    get_commercial_spec_table_data,
    generate_commercial_blog_html_table,
    generate_commercial_clipboard_text,
    generate_commercial_naver_ad_guide_text,
    render_commercial_spec_table_image
)
from document_parser import (
    parse_official_document,
    parse_single_or_multi_document,
    parse_raw_script_document,
    parse_building_register_title,
    parse_building_register_exclusive,
    merge_building_registers,
    identify_document_type,
    extract_pages_text_from_pdf
)
from naver_crawler import (
    crawl_naver_article,
    parse_naver_clipboard_text,
    extract_article_number,
    format_thumb_price
)

def render_direct_download_button(image_bytes: bytes, file_name: str, button_label: str, bg_color: str = "#F48A26") -> str:
    """브라우저 네이티브에서 100% 즉시 다운로드되는 HTML base64 링크를 생성합니다."""
    clean_name = re.sub(r'[\\/*?:"<>|]', "", file_name).strip()
    b64_data = base64.b64encode(image_bytes).decode()
    return f"""
    <div style="margin: 8px 0 14px 0;">
        <a href="data:image/png;base64,{b64_data}" download="{clean_name}" 
           style="display: block; text-align: center; background-color: {bg_color}; color: #FFFFFF !important; 
                  padding: 14px 20px; border-radius: 9px; font-weight: 700; text-decoration: none; 
                  font-size: 15px; box-shadow: 0 4px 12px rgba(244,138,38,0.3); transition: all 0.2s ease-in-out;">
           {button_label}
        </a>
    </div>
    """

def render_direct_print_button(image_bytes: bytes, file_name: str, button_label: str = "🖨️ [원클릭 즉시 인쇄] 창문 부착용 A4 바로 출력", bg_color: str = "#1A202C") -> str:
    """브라우저의 인쇄 대화상자(Ctrl+P)를 즉시 호출하여 A4 용지에 꽉 차게 출력하는 버튼을 생성합니다."""
    b64_data = base64.b64encode(image_bytes).decode()
    return f"""
    <div style="margin: 8px 0 14px 0;">
        <button onclick="
            var printWin = window.open('', '_blank');
            printWin.document.write('<!DOCTYPE html><html><head><title>{file_name}</title><style>@page {{ size: A4 portrait; margin: 0; }} body {{ margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; background: #fff; }} img {{ width: 100%; height: auto; max-width: 100vw; max-height: 100vh; object-fit: contain; }}</style></head><body><img src=\\'data:image/png;base64,{b64_data}\\' onload=\\'setTimeout(function(){{ window.print(); window.close(); }}, 300);\\' /></body></html>');
            printWin.document.close();
        " 
        style="width: 100%; display: block; text-align: center; background-color: {bg_color}; color: #FFFFFF !important; 
               padding: 15px 20px; border-radius: 9px; font-weight: 800; border: none; cursor: pointer;
               font-size: 16px; box-shadow: 0 4px 14px rgba(26,32,44,0.35); transition: all 0.2s ease-in-out;">
           {button_label}
        </button>
    </div>
    """

# 페이지 설정
st.set_page_config(
    page_title="부동산 블로그 썸네일 & 네이버광고 대상중개물표시 올인원 마스터",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세련된 커스텀 CSS 적용 & 모바일 터치 최적화
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
    }
    
    /* 사이드바 스타일링 */
    [data-testid="stSidebar"] {
        background-color: #F8F9FB;
        border-right: 1px solid #E5E8EB;
    }
    
    /* 메인 컨테이너 패딩: Streamlit 상단 메뉴바(Share 등)에 가려지지 않도록 상단 여백 확보 */
    .block-container {
        padding-top: 4.0rem !important;
        padding-bottom: 2.5rem;
    }
    
    /* Deploy 버튼 및 불필요한 클라우드 메뉴 숨기기 */
    .stAppDeployButton, [data-testid="stAppDeployButton"], [data-testid="manage-app-button"] {
        display: none !important;
    }
    
    /* 탭 헤더 스타일링 (크고 누르기 쉽게) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: #EDF1F5;
        padding: 6px;
        border-radius: 12px;
        margin-bottom: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 48px;
        border-radius: 9px;
        font-size: 16px;
        font-weight: 700;
        padding: 0 20px;
        color: #495057;
        background-color: transparent;
        transition: all 0.2s ease-in-out;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #F48A26 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
    }

    /* 배지 스타일 */
    .spec-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        margin-right: 6px;
        margin-bottom: 6px;
    }
    .badge-orange {
        background-color: #FFF2E8;
        color: #F48A26;
        border: 1px solid #FFD5B2;
    }
    .badge-gray {
        background-color: #F1F3F5;
        color: #495057;
    }
    .badge-red {
        background-color: #FDE8E8;
        color: #E02424;
        border: 1px solid #F8B4B4;
    }
    .badge-green {
        background-color: #DEF7EC;
        color: #03543F;
        border: 1px solid #BCF0DA;
    }
    
    /* 다운로드 버튼 강조 (모바일 터치 최적화) */
    .stDownloadButton > button {
        background-color: #F48A26 !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 14px 24px !important;
        font-size: 16px !important;
        font-weight: 700 !important;
        box-shadow: 0 4px 14px rgba(244, 138, 38, 0.35) !important;
        transition: all 0.2s ease-in-out !important;
        width: 100% !important;
    }
    .stDownloadButton > button:hover {
        background-color: #E27917 !important;
        box-shadow: 0 6px 20px rgba(244, 138, 38, 0.45) !important;
        transform: translateY(-1px) !important;
    }

    /* 카드 박스 */
    .info-card {
        background: #FFFFFF;
        border: 1px solid #E5E8EB;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 15px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }

    /* 입력 필드 (text_input, selectbox) 눈에 확 띄는 선명한 흰색 박스 + 테두리 */
    div[data-baseweb="input"], div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border: 1.8px solid #CBD5E0 !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06) !important;
        transition: all 0.2s ease-in-out !important;
    }
    div[data-baseweb="input"]:hover, div[data-baseweb="select"] > div:hover {
        border-color: #F48A26 !important;
    }
    div[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within {
        border-color: #F48A26 !important;
        box-shadow: 0 0 0 3px rgba(244, 138, 38, 0.25) !important;
    }
    input.st-bc, input {
        color: #1A202C !important;
        font-weight: 600 !important;
        font-size: 15px !important;
    }

    /* 점검표 테이블 행 */
    .check-row {
        border-bottom: 1px solid #E9ECEF;
        padding: 10px 0;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .check-label {
        font-size: 14px;
        font-weight: 700;
        color: #333D4B;
    }
    .check-val {
        font-size: 15px;
        color: #191F28;
        font-weight: 600;
    }
    .check-guide {
        font-size: 12px;
        color: #8B95A1;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# 🔐 모바일 & 외부 접속 비밀번호 잠금 장치
# ----------------------------------------------------
VALID_PASSWORDS = ["참좋은1234", "4989"]

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    col_l1, col_l2, col_l3 = st.columns([1, 1.4, 1])
    with col_l2:
        st.markdown("<br/><br/>", unsafe_allow_html=True)
        with st.container():
            st.markdown("""
            <div style="text-align: center; margin-bottom: 20px;">
                <span style="font-size: 45px;">🏢</span>
                <h2 style="margin: 10px 0 5px 0; color: #1E2022; font-weight: 800;">참좋은공인중개사</h2>
                <h4 style="margin: 0; color: #F48A26; font-weight: 700;">썸네일 & 네이버광고 올인원 마스터</h4>
                <p style="color: #6C757D; font-size: 14px; margin-top: 8px;">
                    보안 접속을 위해 설정된 비밀번호를 입력해주세요.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("login_form"):
                input_pw = st.text_input(
                    "접근 비밀번호 입력",
                    type="password",
                    placeholder="비밀번호 입력 (기본: 4989)",
                    help="설정된 접근 비밀번호를 입력해주세요."
                )
                submit_btn = st.form_submit_button("🔓 로그인하여 시작하기", use_container_width=True)
                
                if submit_btn:
                    if input_pw.strip() in VALID_PASSWORDS:
                        st.session_state.authenticated = True
                        st.success("✅ 인증되었습니다! 메인 화면으로 이동합니다.")
                        st.rerun()
                    else:
                        st.error("비밀번호가 틀렸습니다. (비밀번호: 4989)")
            
            st.markdown("""
            <div style="text-align: center; margin-top: 25px; color: #4A5568; font-size: 13px; line-height: 1.5;">
                🔒 참좋은공인중개사사무소 (대표 신제환 ☎ 010-9667-4201)<br/>
                📍 부산광역시 사상구 강선로 9, 1층 (등록번호: 제 26530-2026-00009 호)<br/>
                PC & 스마트폰 모바일 동시 지원
            </div>
            """, unsafe_allow_html=True)
    st.stop()


# ----------------------------------------------------
# 📌 세션 상태(Session State) 초기화
# ----------------------------------------------------

# 1. 썸네일 관련 상태
if "item_no" not in st.session_state:
    st.session_state.item_no = "No. APT001"
if "main_title" not in st.session_state:
    st.session_state.main_title = "사상 중흥S-클래스"
if "sub_title" not in st.session_state:
    st.session_state.sub_title = "그랜드센트럴"
if "feature_text" not in st.session_state:
    st.session_state.feature_text = "1572세대 대단지 아파트"
if "thumb_trade_type" not in st.session_state:
    st.session_state.thumb_trade_type = "매매"
if "thumb_price_text" not in st.session_state:
    st.session_state.thumb_price_text = "6억2천"
if "spec_line1" not in st.session_state:
    st.session_state.spec_line1 = "105동 / 25층(로얄층)"
if "spec_line2" not in st.session_state:
    st.session_state.spec_line2 = "공급 111.42㎡ / 전용 79.85㎡"
if "spec_line3" not in st.session_state:
    st.session_state.spec_line3 = "방 3 / 욕실 2"
if "spec_line4" not in st.session_state:
    st.session_state.spec_line4 = "즉시입주 협의가능"
if "spec_line5" not in st.session_state:
    st.session_state.spec_line5 = "남동향 (거실 기준)"
if "thumb_show_footer" not in st.session_state:
    st.session_state.thumb_show_footer = True
if "thumb_footer_text" not in st.session_state:
    st.session_state.thumb_footer_text = ""

# 2. 네이버 광고 & 대상중개물 표시 16개 점검 항목 상태 (신소장님 사상 중흥S-클래스 세팅값)
for k, v in DEFAULT_SPEC.items():
    if f"ad_{k}" not in st.session_state:
        st.session_state[f"ad_{k}"] = v
if "ad_include_office_info" not in st.session_state:
    st.session_state.ad_include_office_info = True
if "ad_assistant_name" not in st.session_state:
    st.session_state.ad_assistant_name = ""
if "ad_assistant_phone" not in st.session_state:
    st.session_state.ad_assistant_phone = ""

# 썸네일 프리셋 적용 함수
def apply_preset(p_type):
    if p_type == "living":
        st.session_state.item_no = "No. APT001"
        st.session_state.main_title = "사상 중흥S-클래스"
        st.session_state.sub_title = "그랜드센트럴"
        st.session_state.feature_text = "1572세대 대단지 아파트"
        st.session_state.thumb_trade_type = "매매"
        st.session_state.thumb_price_text = "6억2천"
        st.session_state.spec_line1 = "105동 / 25층(로얄층)"
        st.session_state.spec_line2 = "공급 111.42㎡ / 전용 79.85㎡"
        st.session_state.spec_line3 = "방 3 / 욕실 2"
        st.session_state.spec_line4 = "즉시입주 협의가능"
        st.session_state.spec_line5 = "남동향 (거실 기준)"
        
        # 2단계 점검표도 함께 동기화
        st.session_state.ad_location = "부산광역시 사상구 덕포동 220 (사상 중흥S-클래스 105동)"
        st.session_state.ad_area_supply = "111.42"
        st.session_state.ad_area_exclusive = "79.85"
        st.session_state.ad_floor_info = "25 / 36층"
        st.session_state.ad_room_bath = "방 3 / 욕실 2개"
        st.session_state.ad_maintenance_fee = "18만 원"
        st.session_state.ad_maintenance_detail = "공용관리비 약 13만원 (수도/전기/가스 별도)"
        st.session_state.ad_trade_type = "매매"
        st.session_state.ad_price_text = "6억 2,000만 원"
        st.session_state.ad_direction = "남동향 (거실 기준)"
        st.session_state.ad_entrance_type = "계단식"
        st.session_state.ad_heating = "개별난방 / 도시가스"
        st.session_state.ad_move_in_date = "즉시입주 협의가능"
        st.session_state.ad_parking = "총 1,685대 (세대당 1.07대)"
        st.session_state.ad_households = "331세대 (총 1,572세대)"
        st.session_state.ad_building_use = "공동주택 (아파트)"
        st.session_state.ad_approval_date = "2023년 07월 28일"
    elif p_type == "op":
        st.session_state.item_no = "No. OP-302"
        st.session_state.main_title = "해운대 센텀스퀘어"
        st.session_state.sub_title = "하이엔드 오피스텔"
        st.session_state.feature_text = "초역세권 + 풀옵션 프리미엄"
        st.session_state.thumb_trade_type = "전세"
        st.session_state.thumb_price_text = "2억 4천"
        st.session_state.spec_line1 = "A동 / 18층(고층)"
        st.session_state.spec_line2 = "계약 68㎡ / 전용 42㎡"
        st.session_state.spec_line3 = "방 1.5룸 / 욕실 1"
        st.session_state.spec_line4 = "협의 입주 가능"
        st.session_state.spec_line5 = "동향 (시티뷰 조망)"

        st.session_state.ad_location = "부산광역시 해운대구 우동 1515 (센텀스퀘어)"
        st.session_state.ad_area_supply = "68.20"
        st.session_state.ad_area_exclusive = "42.15"
        st.session_state.ad_floor_info = "18 / 32층"
        st.session_state.ad_room_bath = "방 1.5룸 / 욕실 1개"
        st.session_state.ad_maintenance_fee = "15만 원"
        st.session_state.ad_maintenance_detail = "공용관리비 10만원 + 개별사용량"
        st.session_state.ad_trade_type = "전세"
        st.session_state.ad_price_text = "2억 4,000만 원"
        st.session_state.ad_direction = "동향 (거실 기준)"
        st.session_state.ad_entrance_type = "복도식"
        st.session_state.ad_heating = "개별난방 / 도시가스"
        st.session_state.ad_move_in_date = "협의 입주 가능"
        st.session_state.ad_parking = "총 450대 (세대당 1.1대)"
        st.session_state.ad_households = "120세대 (총 380세대)"
        st.session_state.ad_building_use = "업무시설 (오피스텔)"
        st.session_state.ad_approval_date = "2021년 05월 12일"

# 3. 상가 썸네일 관련 상태 (임차 & 매매)
if "comm_thumb_mode" not in st.session_state:
    st.session_state.comm_thumb_mode = "🔑 상가 임차 (월세)"
if "comm_item_no" not in st.session_state:
    st.session_state.comm_item_no = "No. COMM-01"

# 임차 썸네일 세션 상태
if "comm_lease_top_badge" not in st.session_state:
    st.session_state.comm_lease_top_badge = "사상역 초역세권 · 무권리 추천매물"
if "comm_lease_cp_top" not in st.session_state:
    st.session_state.comm_lease_cp_top = "유동인구 1등! 대로변 1층"
if "comm_lease_main_title" not in st.session_state:
    st.session_state.comm_lease_main_title = "코너 상가 임차"
if "comm_lease_cp_bot" not in st.session_state:
    st.session_state.comm_lease_cp_bot = "가시성 최고! 즉시 입점 가능"
if "comm_lease_pin_bubble" not in st.session_state:
    st.session_state.comm_lease_pin_bubble = "목 좋은 자리!"
if "comm_lease_show_pin" not in st.session_state:
    st.session_state.comm_lease_show_pin = True
if "comm_lease_spec1" not in st.session_state:
    st.session_state.comm_lease_spec1 = "전용 25평 | 보증금 3,000만 / 월 180만"
if "comm_lease_spec2" not in st.session_state:
    st.session_state.comm_lease_spec2 = "추천 : 카페 · 음식점 · 판매점"
if "comm_lease_show_footer" not in st.session_state:
    st.session_state.comm_lease_show_footer = True
if "comm_lease_office" not in st.session_state:
    st.session_state.comm_lease_office = "참좋은 공인중개사사무소"
if "comm_lease_broker" not in st.session_state:
    st.session_state.comm_lease_broker = "황금터잡이 신소장"

# 매매 썸네일 세션 상태
if "comm_sale_top_left" not in st.session_state:
    st.session_state.comm_sale_top_left = "사상 핵심상권 매매"
if "comm_sale_top_right" not in st.session_state:
    st.session_state.comm_sale_top_right = "우량 임차인 성업중"
if "comm_sale_show_chart" not in st.session_state:
    st.session_state.comm_sale_show_chart = True
if "comm_sale_main_hl" not in st.session_state:
    st.session_state.comm_sale_main_hl = "확정 수익률 6.8%"
if "comm_sale_main_sub" not in st.session_state:
    st.session_state.comm_sale_main_sub = "안정적인 알짜 상가 매매"
if "comm_sale_price_spec" not in st.session_state:
    st.session_state.comm_sale_price_spec = "매매가 15억 | 보증금 8천 / 월수익 650만 | 실투자금 6억"
if "comm_sale_show_footer" not in st.session_state:
    st.session_state.comm_sale_show_footer = True
if "comm_sale_office" not in st.session_state:
    st.session_state.comm_sale_office = "참좋은 공인중개사사무소"
if "comm_sale_broker" not in st.session_state:
    st.session_state.comm_sale_broker = "황금터잡이 신소장"

# 4. 상가 중개대상물 표시 항목 상태 (임차 & 매매)
if "comm_ad_mode" not in st.session_state:
    st.session_state.comm_ad_mode = "🔑 상가 임대차 (월세)"
for k, v in DEFAULT_COMMERCIAL_SPEC_LEASE.items():
    if f"comm_ad_{k}" not in st.session_state:
        st.session_state[f"comm_ad_{k}"] = v
for k, v in DEFAULT_COMMERCIAL_SPEC_SALE.items():
    if f"comm_ad_{k}" not in st.session_state:
        st.session_state[f"comm_ad_{k}"] = v

# 항상 최신 공인중개사 등록증 정보(강선로 9, 2026-00009 호)로 세션 강제 동기화 (기존 세션 유지 시 구정보 덮어쓰기)
OFFICE_REFRESH_MAP = {
    "office_name": "참좋은공인중개사사무소",
    "office_owner": "신제환",
    "office_reg_no": "제 26530-2026-00009 호",
    "office_address": "부산광역시 사상구 강선로 9, 1층",
    "office_phone": "010-9667-4201"
}
for ok, ov in OFFICE_REFRESH_MAP.items():
    cur_val = str(st.session_state.get(f"ad_{ok}", ""))
    if not cur_val or "2021-00045" in cur_val or "사상로 200" in cur_val:
        st.session_state[f"ad_{ok}"] = ov
    cur_comm = str(st.session_state.get(f"comm_ad_{ok}", ""))
    if not cur_comm or "2021-00045" in cur_comm or "사상로 200" in cur_comm:
        st.session_state[f"comm_ad_{ok}"] = ov

def apply_comm_preset(p_type):
    if p_type == "lease":
        st.session_state.comm_thumb_mode = "🔑 상가 임차 (월세)"
        st.session_state.comm_lease_top_badge = "사상역 초역세권 · 무권리 추천매물"
        st.session_state.comm_lease_cp_top = "유동인구 1등! 대로변 1층"
        st.session_state.comm_lease_main_title = "코너 상가 임차"
        st.session_state.comm_lease_cp_bot = "가시성 최고! 즉시 입점 가능"
        st.session_state.comm_lease_pin_bubble = "목 좋은 자리!"
        st.session_state.comm_lease_show_pin = True
        st.session_state.comm_lease_spec1 = "전용 25평 | 보증금 3,000만 / 월 180만"
        st.session_state.comm_lease_spec2 = "추천 : 카페 · 음식점 · 판매점"
        for k, v in DEFAULT_COMMERCIAL_SPEC_LEASE.items():
            st.session_state[f"comm_ad_{k}"] = v
    elif p_type == "sale":
        st.session_state.comm_thumb_mode = "💰 상가 매매 (수익형)"
        st.session_state.comm_sale_top_left = "사상 핵심상권 매매"
        st.session_state.comm_sale_top_right = "우량 임차인 성업중"
        st.session_state.comm_sale_show_chart = True
        st.session_state.comm_sale_main_hl = "확정 수익률 6.8%"
        st.session_state.comm_sale_main_sub = "안정적인 알짜 상가 매매"
        st.session_state.comm_sale_price_spec = "매매가 15억 | 보증금 8천 / 월수익 650만 | 실투자금 6억"
        for k, v in DEFAULT_COMMERCIAL_SPEC_SALE.items():
            st.session_state[f"comm_ad_{k}"] = v

def safe_set_session_state(key: str, val: any):
    """위젯이 이미 화면에 렌더링된 이후 session_state를 변경할 때 발생하는 StreamlitWidgetAlreadyInstantiatedError 원천 방지"""
    try:
        st.session_state[key] = val
    except Exception:
        pass

def queue_state_update(action_type: str, data: dict = None, preset: str = None, clean_previous: bool = True, success_msg: str = None, error_msg: str = None, target_tab: str = None):
    """
    StreamlitWidgetAlreadyInstantiatedError 원천 차단을 위한 지연 상태 반영 큐.
    Streamlit은 위젯이 렌더링된 후 session_state를 변경하면 즉시 치명적 예외가 발생하므로,
    큐에 작업을 담은 뒤 즉시 rerun()하여 위젯이 생성되기 전 최상단에서 일괄 반영합니다.
    target_tab을 지정하면 rerun 후에도 사용자가 작업하던 탭이 그대로 유지됩니다.
    """
    st.session_state["_pending_state_action"] = {
        "action": action_type,
        "data": data,
        "preset": preset,
        "clean_previous": clean_previous,
        "success_msg": success_msg,
        "error_msg": error_msg,
        "target_tab": target_tab
    }
    st.rerun()

def clear_property_specs():
    """중개사무소 정보(참좋은공인중개사 신제환 대표)는 100% 안전하게 유지하고, 매물 정보만 깨끗하게 초기화합니다."""
    for k, v in BLANK_SPEC.items():
        if k in OFFICE_SPEC:
            continue # 신제환 소장님 고유 중개사무소 정보는 유지
        safe_set_session_state(f"ad_{k}", v)
    safe_set_session_state("item_no", "No. 001")
    safe_set_session_state("main_title", "")
    safe_set_session_state("sub_title", "")
    safe_set_session_state("feature_text", "")
    safe_set_session_state("thumb_trade_type", "매매")
    safe_set_session_state("thumb_price_text", "")
    safe_set_session_state("spec_line1", "")
    safe_set_session_state("spec_line2", "")
    safe_set_session_state("spec_line3", "")
    safe_set_session_state("spec_line4", "즉시입주 협의가능")
    safe_set_session_state("spec_line5", "")

def apply_crawled_or_doc_data(data: dict, clean_previous: bool = True):
    """크롤링 데이터 또는 공적서류 분석 데이터를 16대 점검항목 및 썸네일 세션에 일괄 주입합니다."""
    if not data:
        return

    # 신규 매물 등록 시 이전 매물 잔여 데이터(이전 매물 가격, 관리비, 준공일 등)가 섞이지 않도록 초기화
    # 단, 단편적인 정보(예: 관리비만 복사 등)일 때는 기존에 입력된 귀한 정보가 지워지지 않도록 보호
    has_major_fields = any(data.get(k) for k in ["price_text", "location", "area_exclusive", "dong_name", "main_title"])
    if clean_previous and has_major_fields:
        clear_property_specs()

    # 1. 16대 점검항목 적용
    if data.get("location"): safe_set_session_state("ad_location", str(data["location"]))
    if data.get("area_exclusive"): safe_set_session_state("ad_area_exclusive", str(data["area_exclusive"]))
    if data.get("area_supply"): safe_set_session_state("ad_area_supply", str(data["area_supply"]))
    elif data.get("area_exclusive"): safe_set_session_state("ad_area_supply", str(data["area_exclusive"]))
    if data.get("floor_info"): safe_set_session_state("ad_floor_info", str(data["floor_info"]))
    if data.get("room_bath"): safe_set_session_state("ad_room_bath", str(data["room_bath"]))
    if data.get("building_use"): safe_set_session_state("ad_building_use", str(data["building_use"]))
    if data.get("approval_date"): safe_set_session_state("ad_approval_date", str(data["approval_date"]))
    if data.get("households"): safe_set_session_state("ad_households", str(data["households"]))
    if data.get("parking"): safe_set_session_state("ad_parking", str(data["parking"]))
    if data.get("trade_type"): safe_set_session_state("ad_trade_type", str(data["trade_type"]))
    if data.get("price_text"): safe_set_session_state("ad_price_text", str(data["price_text"]))
    if data.get("direction"): safe_set_session_state("ad_direction", str(data["direction"]))
    if data.get("entrance_type"): safe_set_session_state("ad_entrance_type", str(data["entrance_type"]))
    if data.get("heating"): safe_set_session_state("ad_heating", str(data["heating"]))
    if data.get("move_in_date"): safe_set_session_state("ad_move_in_date", str(data["move_in_date"]))
    if data.get("maintenance_fee"): safe_set_session_state("ad_maintenance_fee", str(data["maintenance_fee"]))
    if data.get("maintenance_detail"): safe_set_session_state("ad_maintenance_detail", str(data["maintenance_detail"]))
    if data.get("deposit_sub"): safe_set_session_state("ad_deposit_sub", str(data["deposit_sub"]))

    # 2. 썸네일 탭 연동
    if data.get("item_no"): safe_set_session_state("item_no", str(data["item_no"]))
    elif data.get("article_no"): safe_set_session_state("item_no", str(data["article_no"]))
    elif data.get("atclNo"): safe_set_session_state("item_no", str(data["atclNo"]))
    if data.get("main_title"): safe_set_session_state("main_title", str(data["main_title"]))
    if data.get("sub_title"): safe_set_session_state("sub_title", str(data["sub_title"]))
    if data.get("feature_text"): safe_set_session_state("feature_text", str(data["feature_text"]))
    if data.get("thumb_trade_type"): safe_set_session_state("thumb_trade_type", str(data["thumb_trade_type"]))
    elif data.get("trade_type"): safe_set_session_state("thumb_trade_type", str(data["trade_type"]))
    if data.get("thumb_price_text"): safe_set_session_state("thumb_price_text", str(data["thumb_price_text"]))
    elif data.get("price_text"):
        safe_set_session_state("thumb_price_text", format_thumb_price(str(data["price_text"])))
    if data.get("spec_line1"): safe_set_session_state("spec_line1", str(data["spec_line1"]))
    elif data.get("floor_info"): safe_set_session_state("spec_line1", str(data["floor_info"]))
    if data.get("spec_line2"): safe_set_session_state("spec_line2", str(data["spec_line2"]))
    elif data.get("area_exclusive"):
        s_area = data.get("area_supply", data["area_exclusive"])
        safe_set_session_state("spec_line2", f"공급 {s_area}㎡ / 전용 {data['area_exclusive']}㎡")
    if data.get("spec_line3"): safe_set_session_state("spec_line3", str(data["spec_line3"]))
    elif data.get("room_bath"): safe_set_session_state("spec_line3", str(data["room_bath"]))
    if data.get("spec_line4"): safe_set_session_state("spec_line4", str(data["spec_line4"]))
    elif data.get("move_in_date"): safe_set_session_state("spec_line4", str(data["move_in_date"]))
    if data.get("spec_line5"): safe_set_session_state("spec_line5", str(data["spec_line5"]))
    elif data.get("direction"): safe_set_session_state("spec_line5", str(data["direction"]))

def apply_commercial_crawled_or_doc_data(data: dict):
    """크롤링 데이터 또는 공적서류 분석 데이터를 상가 18대 점검항목 및 상가 썸네일 세션에 일괄 주입합니다."""
    if not data:
        return

    # 1. 상가 필수 점검항목 적용
    if data.get("location"):
        safe_set_session_state("comm_ad_location", str(data["location"]))
    if data.get("area_exclusive"):
        safe_set_session_state("comm_ad_area_exclusive", str(data["area_exclusive"]))
    if data.get("area_supply"):
        safe_set_session_state("comm_ad_area_contract", str(data["area_supply"]))
    elif data.get("area_contract"):
        safe_set_session_state("comm_ad_area_contract", str(data["area_contract"]))
    elif data.get("area_exclusive"):
        safe_set_session_state("comm_ad_area_contract", str(data["area_exclusive"]))
    if data.get("floor_info"):
        safe_set_session_state("comm_ad_floor_info", str(data["floor_info"]))
    if data.get("building_use"):
        safe_set_session_state("comm_ad_building_use", str(data["building_use"]))
    if data.get("zone_region"):
        safe_set_session_state("comm_ad_zone_region", str(data["zone_region"]))
    if data.get("zone_district"):
        safe_set_session_state("comm_ad_zone_district", str(data["zone_district"]))
    if data.get("structure"):
        safe_set_session_state("comm_ad_structure", str(data["structure"]))
    if data.get("approval_date"):
        safe_set_session_state("comm_ad_approval_date", str(data["approval_date"]))
    if data.get("parking"):
        safe_set_session_state("comm_ad_parking", str(data["parking"]))
    if data.get("trade_type"):
        safe_set_session_state("comm_ad_trade_type", str(data["trade_type"]))
    if data.get("price_text"):
        safe_set_session_state("comm_ad_price_text", str(data["price_text"]))
    if data.get("premium_fee"):
        safe_set_session_state("comm_ad_premium_fee", str(data["premium_fee"]))
    if data.get("direction"):
        d_val = str(data["direction"])
        if "출입구" not in d_val:
            d_val = re.sub(r"\s*\(.*?\)", "", d_val).strip() + " (주된 출입구 기준)"
        safe_set_session_state("comm_ad_direction", d_val)
    if data.get("move_in_date"):
        safe_set_session_state("comm_ad_move_in_date", str(data["move_in_date"]))
    if data.get("maintenance_fee"):
        safe_set_session_state("comm_ad_maintenance_fee", str(data["maintenance_fee"]))
    if data.get("maintenance_detail"):
        safe_set_session_state("comm_ad_maintenance_detail", str(data["maintenance_detail"]))
    if data.get("restroom"):
        safe_set_session_state("comm_ad_restroom", str(data["restroom"]))
    if data.get("current_use"):
        safe_set_session_state("comm_ad_current_use", str(data["current_use"]))
    if data.get("recommended_use"):
        safe_set_session_state("comm_ad_recommended_use", str(data["recommended_use"]))
    if data.get("elevator"):
        elev_str = str(data["elevator"])
        cur_fac = st.session_state.get("comm_ad_facility_info", "")
        if "승강기" not in cur_fac and "엘리베이터" not in cur_fac:
            safe_set_session_state("comm_ad_facility_info", f"{cur_fac}, {elev_str}".strip(", "))
    elif data.get("facility_info"):
        safe_set_session_state("comm_ad_facility_info", str(data["facility_info"]))

    # 2. 상가 썸네일(임차 / 매매) 탭 실시간 연동
    is_sale_mode = "매매" in st.session_state.get("comm_ad_trade_type", "")
    py_val = ""
    try:
        if data.get("area_exclusive"):
            py_val = f"전용 {round(float(data['area_exclusive']) * 0.3025)}평"
    except Exception:
        pass

    loc_short = data.get("main_title") or (data.get("location", "").split(" ")[-1] if data.get("location") else "상가")
    
    if not is_sale_mode:
        # 임차 썸네일 동기화
        if loc_short:
            safe_set_session_state("comm_lease_main_title", f"{loc_short} 상가 임차")
            safe_set_session_state("comm_lease_top_badge", f"{loc_short} 추천 매물 · {st.session_state.get('comm_ad_premium_fee', '무권리')}")
        price_summary = st.session_state.get("comm_ad_price_text", "")
        if py_val and price_summary:
            safe_set_session_state("comm_lease_spec1", f"{py_val} | {price_summary}")
        elif py_val:
            safe_set_session_state("comm_lease_spec1", py_val)
        if data.get("recommended_use"):
            safe_set_session_state("comm_lease_spec2", f"추천 : {data['recommended_use']}")
    else:
        # 매매 썸네일 동기화
        if loc_short:
            safe_set_session_state("comm_sale_top_left", f"{loc_short} 상가 매매")
            safe_set_session_state("comm_sale_main_sub", f"안정적인 {loc_short} 상가 매매")
        if data.get("price_text"):
            safe_set_session_state("comm_sale_price_spec", f"매매가 {data['price_text']} | {st.session_state.get('comm_ad_structure', '철근콘크리트')} | {py_val}")

# ====================================================
# 🛡️ [위젯 충돌 원천 차단] 지연 상태 큐 최상단 일괄 처리기
# 위젯(Tab 1, Tab 2 등)이 렌더링되기 전 최상단에서 세션 스테이트를 안전하게 업데이트합니다.
# ====================================================
if "_pending_state_action" in st.session_state and st.session_state["_pending_state_action"]:
    pending_act = st.session_state.pop("_pending_state_action")
    act_type = pending_act.get("action")
    if act_type == "apply_apt":
        apply_crawled_or_doc_data(pending_act["data"], clean_previous=pending_act.get("clean_previous", True))
    elif act_type == "apply_comm":
        apply_commercial_crawled_or_doc_data(pending_act["data"])
    elif act_type == "clear_apt":
        clear_property_specs()
    elif act_type == "preset_apt":
        apply_preset(pending_act["preset"])
    elif act_type == "preset_comm":
        apply_comm_preset(pending_act["preset"])

    if pending_act.get("target_tab"):
        st.session_state["target_main_tab"] = pending_act["target_tab"]

    if pending_act.get("success_msg"):
        if "comm" in act_type:
            st.session_state["last_comm_applied_msg"] = pending_act["success_msg"]
        else:
            st.session_state["last_applied_msg"] = pending_act["success_msg"]
    if pending_act.get("error_msg"):
        st.session_state["last_applied_err"] = pending_act["error_msg"]


# -------------------------
# 상단 타이틀 & 모바일 접속 안내
# -------------------------
col_h1, col_h2 = st.columns([2.2, 0.8])
with col_h1:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 5px;">
        <span style="font-size: 32px;">🏢</span>
        <div>
            <h2 style="margin: 0; font-weight: 800; color: #1E2022; font-size: 24px;">부동산 블로그 썸네일 & 네이버광고 올인원 마스터</h2>
            <p style="margin: 3px 0 0 0; color: #2D3748; font-size: 13.5px; line-height: 1.5;">
                🏢 <b>참좋은공인중개사사무소</b> (대표: 신제환 ☎ 010-9667-4201) &nbsp;|&nbsp; 📍 <b>소재지:</b> 부산광역시 사상구 강선로 9, 1층 &nbsp;|&nbsp; 📜 <b>등록번호:</b> 제 26530-2026-00009 호
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
with col_h2:
    if st.button("🔒 로그아웃 (비밀번호 잠금)", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ----------------------------------------------------
# ⚡ [최상단 전면 배치] 1초 스마트 자동완성 마스터 콘솔
# (네이버 복사 텍스트 / 대장 스크립트·PDF / 매물번호 크롤링 1초 완성)
# ----------------------------------------------------
if st.session_state.get("last_applied_msg"):
    st.success(st.session_state["last_applied_msg"])

with st.expander("⚡ [원클릭 1초 스마트 자동완성 마스터 콘솔] 네이버 복사 텍스트 / 건축물대장 스크립트 / 매물번호 입력", expanded=True):
    st.markdown("""
    <div style="font-size:14px; color:#1A365D; background:#F0F7FF; border:1.5px solid #90CDF4; padding:12px 16px; border-radius:10px; margin-bottom:12px;">
        🚀 <b>네이버 매물 화면 복사 텍스트</b>나 <b>건축물대장 텍스트(스크립트)</b>를 아래에 붙여넣으시면, 
        <b>16대 점검항목(중개대상물 표시)</b>과 <b>블로그 썸네일(아파트명, 가격, 5대 스펙)</b>을 0.1초 만에 자동으로 싹 채워드립니다!<br/>
        <span style="color:#2B6CB0; font-size:12.5px;">🏢 중개사무소 정보(참좋은공인중개사사무소 신제환 대표 | 강선로 9 | 제 26530-2026-00009 호)는 100% 안전하게 유지되며 매물 정보만 깨끗하게 갱신됩니다.</span>
    </div>
    """, unsafe_allow_html=True)

    c_top_b1, c_top_b2, c_top_b3 = st.columns([1.2, 1.2, 1.2])
    with c_top_b1:
        if st.button("✨ 새 매물 빈 양식으로 초기화", use_container_width=True, help="중개사무소 정보는 유지하고 모든 매물 항목을 깨끗하게 비웁니다."):
            queue_state_update("clear_apt", success_msg="✨ 새 매물을 입력하실 수 있도록 모든 매물 항목이 깨끗하게 초기화되었습니다!")
    with c_top_b2:
        if st.button("⚡ 사상 중흥 예시 채우기", use_container_width=True):
            queue_state_update("preset_apt", preset="living", success_msg="📋 사상 중흥S-클래스 추천 예시가 반영되었습니다.")
    with c_top_b3:
        if st.button("⚡ 센텀 오피스텔 예시 채우기", use_container_width=True):
            queue_state_update("preset_apt", preset="op", success_msg="📋 해운대 센텀스퀘어 오피스텔 예시가 반영되었습니다.")

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    top_tab_clip, top_tab_script, top_tab_num = st.tabs([
        "📋 네이버 화면 복사 텍스트 붙여넣기 (가장 확실 & 1초 완성! ⭐추천)",
        "📄 건축물대장 텍스트(스크립트) 붙여넣기 & PDF 업로드",
        "🔍 네이버 부동산 매물 번호 / URL 크롤링 (실험적)"
    ])

    # 1. 네이버 화면 복사 텍스트 붙여넣기
    with top_tab_clip:
        st.markdown("""
        <div style="font-size:13px; color:#2B6CB0; background:#EBF8FF; border:1px solid #BEE3F8; padding:8px 12px; border-radius:6px; margin-bottom:8px;">
            💡 <b>사용 방법:</b> 네이버 부동산 매물 상세 화면에서 마우스로 매물 정보 영역(매물명, 가격, 면적, 층수 등)을 드래그 복사(Ctrl+C)하여 아래에 붙여넣고 버튼을 누르세요!
        </div>
        """, unsafe_allow_html=True)
        top_clip_text = st.text_area(
            "네이버 매물 상세 복사 텍스트",
            height=110,
            placeholder="예:\n사상 중흥S-클래스 105동 매매 6억 2,000만원\n아파트 공급 111.42㎡ / 전용 79.85㎡, 25/36층, 남동향\n관리비 18만원, 방수/욕실수 3/2개...",
            key="top_input_naver_clip"
        )
        if st.button("⚡ 붙여넣은 네이버 텍스트 분석 & 썸네일·점검표 즉시 자동완성", type="primary", use_container_width=True, key="top_btn_parse_clip"):
            if top_clip_text.strip():
                parsed_c = parse_naver_clipboard_text(top_clip_text)
                if parsed_c:
                    queue_state_update("apply_apt", data=parsed_c, clean_previous=True, success_msg=f"🎉 네이버 매물 [{parsed_c.get('main_title', '매물')}] 분석 완료! 썸네일과 16대 점검항목에 즉시 자동 반영되었습니다.")
                else:
                    st.warning("붙여넣은 텍스트에서 매물 정보를 식별하지 못했습니다. 내용을 확인해주세요.")
            else:
                st.warning("네이버 부동산 매물 상세 텍스트를 먼저 붙여넣어 주세요.")

    # 2. 건축물대장 텍스트(스크립트) 붙여넣기 & PDF
    with top_tab_script:
        top_doc_tab1, top_doc_tab2 = st.tabs([
            "📋 대장 텍스트(스크립트) 통째로 붙여넣기 (정부24/세움터 열람 복사본)",
            "📁 대장 PDF 파일 업로드"
        ])
        with top_doc_tab1:
            st.markdown("""
            <div style="font-size:13px; color:#2D3748; background:#F7FAFC; border:1px solid #E2E8F0; padding:8px 12px; border-radius:6px; margin-bottom:8px;">
                💡 <b>정부24 / 세움터 / 일사편리 100% 지원:</b> 화면에서 열람한 건축물대장(표제부/전유부/일반대장) 텍스트를 마우스로 복사하여 그대로 붙여넣으세요! 표제부와 전유부를 구분할 필요 없이 프로그램이 지능적으로 자동 병합합니다.
            </div>
            """, unsafe_allow_html=True)
            top_script_text = st.text_area(
                "건축물대장 열람 복사 텍스트 (스크립트)",
                height=120,
                placeholder="대지위치: 부산시 사상구 덕포동 220\n건축물명칭: 사상 중흥S-클래스 제105동 제2501호\n층별: 25층\n전유부분 면적: 79.85㎡\n사용승인일: 2023-07-28...",
                key="top_input_script_doc"
            )
            if st.button("🔍 붙여넣은 대장 스크립트 통합 분석 & 즉시 적용", type="primary", use_container_width=True, key="top_btn_parse_script"):
                if top_script_text.strip():
                    doc_lbl, parsed_doc = parse_raw_script_document(top_script_text)
                    if parsed_doc:
                        queue_state_update("apply_apt", data=parsed_doc, clean_previous=True, success_msg=f"🎉 [{doc_lbl}] 분석 완료! 썸네일과 16대 점검항목에 깨끗하게 즉시 반영되었습니다.")
                    else:
                        st.warning("붙여넣은 대장 텍스트에서 건축물 정보를 식별하지 못했습니다. 내용을 확인해주세요.")
                else:
                    st.warning("건축물대장 텍스트를 먼저 붙여넣어 주세요.")

        with top_doc_tab2:
            top_uploaded_pdf = st.file_uploader(
                "건축물대장 (표제부 / 전유부) PDF 파일",
                type=["pdf"],
                key="top_pdf_uploader_key"
            )
            if top_uploaded_pdf:
                if st.button("🚀 업로드된 PDF 정밀 분석 & 즉시 적용", type="primary", use_container_width=True, key="top_btn_parse_pdf"):
                    try:
                        p_t, p_res, _ = parse_official_document(top_uploaded_pdf, top_uploaded_pdf.name)
                        if p_res:
                            queue_state_update("apply_apt", data=p_res, clean_previous=True, success_msg=f"🎉 [{p_t}] 분석 완료! 썸네일과 점검표에 즉시 반영되었습니다.")
                        else:
                            st.error("PDF 파일에서 텍스트를 추출하지 못했습니다. 보안문서인 경우 앞의 [📋 대장 텍스트 통째로 붙여넣기]를 이용해주세요!")
                    except Exception as e:
                        st.error(f"PDF 분석 오류: {e}")

    # 3. 네이버 부동산 매물 번호 / URL 크롤링
    with top_tab_num:
        c_top_n1, c_top_n2 = st.columns([2.5, 1])
        with c_top_n1:
            top_article_val = st.text_input(
                "네이버 매물 번호 (숫자) 또는 매물 링크 URL",
                placeholder="예: 2428591234 또는 https://fin.land.naver.com/articles/2428591234",
                key="top_input_article_no"
            )
        with c_top_n2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            top_btn_crawl = st.button("🚀 실시간 크롤링 시도", type="primary", use_container_width=True, key="top_btn_crawl_run")

        if top_btn_crawl:
            if top_article_val.strip():
                with st.spinner("네이버 부동산 매물 정보 실시간 조회 중..."):
                    is_ok, msg, c_data = crawl_naver_article(top_article_val.strip())
                    if is_ok:
                        queue_state_update("apply_apt", data=c_data, clean_previous=True, success_msg=f"🎉 {msg} 썸네일과 점검표에 즉시 자동 반영되었습니다.", target_tab="📝 ③ 아파트 중개대상물 표시")
                    else:
                        st.error(f"⚠️ {msg}")
            else:
                st.warning("매물 번호 또는 링크 URL을 입력해주세요.")

# ----------------------------------------------------
# 🌟 메인 2대 탭 구성 (1. 썸네일 생성 / 2. 네이버광고 점검표)
# ----------------------------------------------------
MAIN_TAB_LIST = [
    "🏢 ① 아파트 썸네일",
    "🏬 ② 상가 썸네일 (임차·매매)",
    "📝 ③ 아파트 중개대상물 표시",
    "🏪 ④ 상가 중개대상물 표시 (임차·매매)"
]

target_tab = st.session_state.pop("target_main_tab", None)

if target_tab and target_tab in MAIN_TAB_LIST:
    try:
        tab_apt_thumb, tab_comm_thumb, tab_apt_ad, tab_comm_ad = st.tabs(MAIN_TAB_LIST, default=target_tab)
    except TypeError:
        tab_apt_thumb, tab_comm_thumb, tab_apt_ad, tab_comm_ad = st.tabs(MAIN_TAB_LIST)

    label_keyword = "③ 아파트 중개대상물" if "③" in target_tab else ("④ 상가 중개대상물" if "④" in target_tab else ("② 상가 썸네일" if "②" in target_tab else "① 아파트 썸네일"))
    st.components.v1.html(f"""
    <script>
    function selectTargetTab() {{
        try {{
            var doc = window.parent.document;
            var allTabs = doc.querySelectorAll('button[data-baseweb="tab"]');
            for (var i = 0; i < allTabs.length; i++) {{
                var txt = (allTabs[i].textContent || allTabs[i].innerText || "").trim();
                if (txt.indexOf("{label_keyword}") !== -1) {{
                    allTabs[i].click();
                    return true;
                }}
            }}
        }} catch (e) {{}}
        return false;
    }}
    setTimeout(selectTargetTab, 50);
    setTimeout(selectTargetTab, 150);
    setTimeout(selectTargetTab, 350);
    </script>
    """, height=0, width=0)
else:
    tab_apt_thumb, tab_comm_thumb, tab_apt_ad, tab_comm_ad = st.tabs(MAIN_TAB_LIST)

# ====================================================
# [ 탭 1 ] 아파트 블로그 썸네일 생성기
# ====================================================
with tab_apt_thumb:
    col_t_left, col_t_right = st.columns([1.25, 0.75])
    
    with col_t_left:
        # 빠른 프리셋
        col_pr1, col_pr2, col_pr3 = st.columns([1, 1, 1])
        with col_pr1:
            if st.button("⚡ 사상 중흥 아파트 예시", use_container_width=True):
                apply_preset("living")
                st.rerun()
        with col_pr2:
            if st.button("⚡ 센텀 오피스텔 예시", use_container_width=True):
                apply_preset("op")
                st.rerun()
        with col_pr3:
            st.caption("👈 버튼을 누르면 추천 예시가 즉시 채워집니다.")

        # 레이아웃 설정
        col_ly1, col_ly2 = st.columns([1.2, 1])
        with col_ly1:
            layout_options = {
                "와이드 사선형 (⭐ 거실/실내 추천)": "side_wide",
                "상하 파노라마형 (가로 100% 전경 극대화)": "top_panoramic",
                "표준 사선형 (시안 기본 5:5 - 외관용)": "side_standard",
            }
            selected_layout_label = st.radio(
                "레이아웃 모드",
                options=list(layout_options.keys()),
                index=0,
                horizontal=True
            )
            layout_mode = layout_options[selected_layout_label]
        
        with col_ly2:
            photo_width_ratio = 0.68
            if layout_mode == "side_wide":
                photo_width_ratio_pct = st.slider(
                    "📷 사진 가로 비중 (와이드 조절)",
                    min_value=50,
                    max_value=76,
                    value=68,
                    step=2,
                    format="%d%%"
                )
                photo_width_ratio = photo_width_ratio_pct / 100.0

        # 사진 업로드
        uploaded_bg = st.file_uploader(
            "📸 현장 사진 업로드 (스마트폰 촬영 사진 즉시 지원)",
            type=["jpg", "jpeg", "png", "webp"],
            key="thumb_file_uploader"
        )

        with st.expander("🔍 사진 위치 / 확대 미세 조정", expanded=False):
            c_z1, c_z2, c_z3 = st.columns(3)
            with c_z1:
                bg_zoom = st.slider("사진 확대/축소", 0.6, 2.0, 1.0, 0.05)
            with c_z2:
                bg_offset_x = st.slider("사진 좌우 이동 (px)", -450, 450, 0, 10)
            with c_z3:
                bg_offset_y = st.slider("사진 상하 이동 (px)", -450, 450, 0, 10)

        # 썸네일 렌더링
        spec_lines = [
            st.session_state.spec_line1,
            st.session_state.spec_line2,
            st.session_state.spec_line3,
            st.session_state.spec_line4,
            st.session_state.spec_line5
        ]
        
        with st.spinner("고화질 썸네일 렌더링 중..."):
            thumbnail_img = render_thumbnail(
                bg_image=uploaded_bg,
                item_no=st.session_state.item_no,
                main_title=st.session_state.main_title,
                sub_title=st.session_state.sub_title,
                feature_text=st.session_state.feature_text,
                trade_type=st.session_state.thumb_trade_type,
                price_text=st.session_state.thumb_price_text,
                spec_lines=spec_lines,
                layout_mode=layout_mode,
                photo_width_ratio=photo_width_ratio,
                bg_offset_x=bg_offset_x,
                bg_offset_y=bg_offset_y,
                bg_zoom=bg_zoom,
                show_footer=st.session_state.thumb_show_footer,
                footer_text=st.session_state.thumb_footer_text
            )

        # 🌟 썸네일 & 창문 부착용 A4 포스터 출력 2대 옵션
        tab_view_thumb, tab_view_a4 = st.tabs([
            "🖼️ 1. 블로그 썸네일 (1080x1080 정방형)",
            "🖨️ 2. 중개사무소 창문 부착용 A4 포스터 (210x297mm 인쇄용)"
        ])

        with tab_view_thumb:
            st.image(thumbnail_img, caption="블로그 썸네일 실시간 완성 미리보기 (1080 x 1080 px)", use_container_width=True)

        with tab_view_a4:
            with st.spinner("창문 부착용 300DPI 초고화질 A4 포스터 렌더링 중..."):
                a4_poster_img = render_a4_window_poster(
                    thumbnail_img=None,
                    bg_image=uploaded_bg,
                    item_no=st.session_state.item_no,
                    main_title=st.session_state.main_title,
                    sub_title=st.session_state.sub_title,
                    feature_text=st.session_state.feature_text,
                    trade_type=st.session_state.thumb_trade_type,
                    price_text=st.session_state.thumb_price_text,
                    spec_lines=spec_lines,
                    office_name=st.session_state.get("ad_office_name", "참좋은공인중개사사무소"),
                    office_owner=st.session_state.get("ad_office_owner", "신제환"),
                    office_phone=st.session_state.get("ad_office_phone", "010-9667-4201"),
                    office_reg_no=st.session_state.get("ad_office_reg_no", "제 26530-2026-00009 호"),
                    office_address=st.session_state.get("ad_office_address", "부산광역시 사상구 강선로 9, 1층"),
                    is_commercial=False,
                    bg_offset_x=bg_offset_x,
                    bg_offset_y=bg_offset_y,
                    bg_zoom=bg_zoom
                )
            st.image(a4_poster_img, caption="중개사무소 유리창 부착용 A4 브리핑 포스터 (초고화질 300 DPI)", use_container_width=True)

    with col_t_right:
        st.markdown("### 🛠️ 썸네일 텍스트 수정")
        st.text_input("🏷️ 물건 번호", key="item_no")
        st.text_input("🏢 메인 타이틀 (아파트명)", key="main_title")
        st.text_input("📍 서브 타이틀 (동/단지명)", key="sub_title")
        st.text_input("✨ 매물 핵심 특징", key="feature_text")
        
        c_tr1, c_tr2 = st.columns([1, 1.3])
        with c_tr1:
            trade_opts = ["매매", "전세", "월세", "분양", "급매"]
            if st.session_state.thumb_trade_type not in trade_opts:
                trade_opts.append(st.session_state.thumb_trade_type)
            st.selectbox("거래 형태", trade_opts, key="thumb_trade_type")
        with c_tr2:
            st.text_input("금액 (예: 6억2천)", key="thumb_price_text")

        st.markdown("#### 📋 5대 스펙 텍스트")
        st.text_input("1행: 해당동 / 층수", key="spec_line1")
        st.text_input("2행: 공급/전용면적", key="spec_line2")
        st.text_input("3행: 방/욕실 수", key="spec_line3")
        st.text_input("4행: 입주시기", key="spec_line4")
        st.text_input("5행: 방향 및 특징", key="spec_line5")

        st.markdown("#### 🏢 하단 띠지 (중개사무소 정보)")
        st.checkbox(
            "하단 띠지 표시 (체크 해제 시 전체 사진 영역 확장)",
            key="thumb_show_footer",
            help="소공 또는 타 중개사 협업 시 띠지 없이 매물 사진만 1080px 꽉 차게 내보낼 수 있습니다."
        )
        if st.session_state.thumb_show_footer:
            st.text_input(
                "띠지 문구 (소공/직원 커스텀 문구 가능)",
                key="thumb_footer_text",
                placeholder="미입력 시: 참좋은공인중개사사무소 (대표 신제환) ☎ 010-9667-4201"
            )

        # 1. 썸네일 이미지 다운로드 바이트
        img_byte_arr = io.BytesIO()
        thumbnail_img.save(img_byte_arr, format="PNG", quality=98)
        img_bytes = img_byte_arr.getvalue()

        clean_title = re.sub(r'[^\w\s-]', '', (st.session_state.main_title or "매물")).strip().replace(" ", "_")
        clean_price = re.sub(r'[^\w\s-]', '', (st.session_state.thumb_price_text or "")).strip().replace(" ", "")
        download_filename = f"부동산썸네일_{clean_title}_{st.session_state.thumb_trade_type}_{clean_price}.png"

        # 2. A4 창문 포스터 다운로드 및 인쇄 바이트
        a4_byte_arr = io.BytesIO()
        a4_poster_img.save(a4_byte_arr, format="PNG", quality=98)
        a4_bytes = a4_byte_arr.getvalue()
        a4_download_filename = f"창문부착용_A4포스터_{clean_title}_{clean_price}.png"

        st.markdown("<hr style='margin: 15px 0 12px 0;'/>", unsafe_allow_html=True)
        st.markdown("### 📥 출력 및 저장 옵션")

        tab_down_thumb, tab_down_a4 = st.tabs([
            "🖼️ 1. 블로그 썸네일 저장",
            "🖨️ 2. 창문 부착용 A4 바로 출력/저장"
        ])

        with tab_down_thumb:
            st.download_button(
                label="📥 1080x1080 썸네일 저장 (기본 다운로드)",
                data=img_bytes,
                file_name=download_filename,
                mime="image/png",
                key="btn_thumb_download_main",
                use_container_width=True
            )
            st.markdown(render_direct_download_button(img_bytes, download_filename, "💾 [즉시 다운로드] 썸네일 원클릭 파일 저장"), unsafe_allow_html=True)
            st.caption("📱 스마트폰에서는 위 이미지를 1초간 길게 누르시면 '사진 앱에 저장'도 가능합니다.")

        with tab_down_a4:
            st.markdown(render_direct_print_button(a4_bytes, a4_download_filename, "🖨️ [원클릭 즉시 인쇄] 창문 부착용 A4 바로 출력 (Ctrl+P)", bg_color="#1A202C"), unsafe_allow_html=True)
            st.download_button(
                label="📥 300DPI 초고화질 A4 포스터 파일 저장",
                data=a4_bytes,
                file_name=a4_download_filename,
                mime="image/png",
                key="btn_a4_download_main",
                use_container_width=True
            )
            st.markdown(render_direct_download_button(a4_bytes, a4_download_filename, "💾 [즉시 다운로드] A4 포스터 원클릭 파일 저장", bg_color="#2B6CB0"), unsafe_allow_html=True)
            st.markdown("""
            <div style="font-size:12.5px; color:#2D3748; background:#F8FAFC; border:1px solid #CBD5E0; padding:10px 14px; border-radius:8px; margin-top:6px; line-height:1.5;">
                💡 <b>창문 부착 인쇄 팁:</b><br/>
                1. 상단의 <b>[🖨️ 원클릭 즉시 인쇄]</b>를 누르시면 프린터 인쇄창이 바로 열립니다.<br/>
                2. 인쇄 설정에서 용지 방향을 <b>'세로'</b>로 하시고 <b>'용지에 맞춤'</b>을 선택하시면 A4 용지에 여백 없이 칼같이 선명하게 출력됩니다!<br/>
                3. 출력 후 중개사무소 창문(유리창) 안쪽에 부착하시면 지나가는 고객의 시선을 100% 사로잡습니다.
            </div>
            """, unsafe_allow_html=True)

        st.info("💡 아파트 썸네일과 포스터를 만드셨다면, 상단의 **'📝 ③ 아파트 중개대상물 표시'** 탭을 클릭하여 네이버 부동산 광고 및 블로그 본문 서식을 바로 확인하세요!")


# ====================================================
# [ 탭 2 ] 상가 썸네일 생성기 (임차 & 매매 2대 모드)
# ====================================================
with tab_comm_thumb:
    col_ct_left, col_ct_right = st.columns([1.25, 0.75])
    
    with col_ct_left:
        # 상가 모드 선택 (임차 vs 매매)
        c_mode_opts = ["🔑 상가 임차 (월세)", "💰 상가 매매 (수익형)"]
        selected_comm_mode = st.radio(
            "상가 매물 유형 선택",
            options=c_mode_opts,
            index=0 if "임차" in st.session_state.comm_thumb_mode else 1,
            horizontal=True,
            key="comm_thumb_mode_selector"
        )
        st.session_state.comm_thumb_mode = selected_comm_mode
        is_sale_mode = "매매" in selected_comm_mode

        # 빠른 추천 프리셋
        col_cpr1, col_cpr2, col_cpr3 = st.columns([1, 1, 1])
        with col_cpr1:
            if st.button("⚡ 사상역 코너 상가 임차 예시", use_container_width=True):
                apply_comm_preset("lease")
                st.rerun()
        with col_cpr2:
            if st.button("⚡ 사상 핵심상권 상가 매매 예시", use_container_width=True):
                apply_comm_preset("sale")
                st.rerun()
        with col_cpr3:
            st.caption("👈 버튼을 누르면 추천 예시가 즉시 채워집니다.")

        # 내가 찍어온 사진 업로드
        uploaded_comm_bg = st.file_uploader(
            "📸 내가 찍어온 현장 상가 사진 업로드 (스마트폰 촬영 사진 즉시 지원)",
            type=["jpg", "jpeg", "png", "webp"],
            key="comm_bg_uploader_key"
        )

        with st.expander("🔍 사진 위치 / 확대 미세 조정", expanded=False):
            cz1, cz2, cz3 = st.columns(3)
            with cz1:
                comm_bg_zoom = st.slider("사진 확대/축소", 0.6, 2.0, 1.0, 0.05, key="comm_bg_zoom_slider")
            with cz2:
                comm_bg_offset_x = st.slider("사진 좌우 이동 (px)", -450, 450, 0, 10, key="comm_bg_offset_x_slider")
            with cz3:
                comm_bg_offset_y = st.slider("사진 상하 이동 (px)", -450, 450, 0, 10, key="comm_bg_offset_y_slider")

        # 실시간 고화질 렌더링
        with st.spinner("고화질 상가 썸네일 렌더링 중..."):
            if not is_sale_mode:
                comm_thumb_img = render_commercial_lease_thumbnail(
                    bg_image=uploaded_comm_bg,
                    top_badge_text=st.session_state.comm_lease_top_badge,
                    catchphrase_top=st.session_state.comm_lease_cp_top,
                    main_title=st.session_state.comm_lease_main_title,
                    catchphrase_bot=st.session_state.comm_lease_cp_bot,
                    pin_bubble_text=st.session_state.comm_lease_pin_bubble,
                    show_pin=st.session_state.comm_lease_show_pin,
                    spec_line1=st.session_state.comm_lease_spec1,
                    spec_line2=st.session_state.comm_lease_spec2,
                    bg_offset_x=comm_bg_offset_x,
                    bg_offset_y=comm_bg_offset_y,
                    bg_zoom=comm_bg_zoom,
                    show_footer=st.session_state.comm_lease_show_footer,
                    office_name=st.session_state.comm_lease_office,
                    broker_title=st.session_state.comm_lease_broker
                )
            else:
                comm_thumb_img = render_commercial_sale_thumbnail(
                    bg_image=uploaded_comm_bg,
                    top_badge_left=st.session_state.comm_sale_top_left,
                    top_badge_right=st.session_state.comm_sale_top_right,
                    show_chart_icon=st.session_state.comm_sale_show_chart,
                    main_highlight_title=st.session_state.comm_sale_main_hl,
                    main_sub_title=st.session_state.comm_sale_main_sub,
                    price_spec_text=st.session_state.comm_sale_price_spec,
                    bg_offset_x=comm_bg_offset_x,
                    bg_offset_y=comm_bg_offset_y,
                    bg_zoom=comm_bg_zoom,
                    show_footer=st.session_state.comm_sale_show_footer,
                    office_name=st.session_state.comm_sale_office,
                    broker_title=st.session_state.comm_sale_broker
                )

        # 🌟 상가 썸네일 & 창문 부착용 A4 포스터 출력 2대 옵션
        tab_comm_view_thumb, tab_comm_view_a4 = st.tabs([
            "🖼️ 1. 상가 블로그 썸네일 (1080x1080)",
            "🖨️ 2. 중개사무소 창문 부착용 A4 포스터 (210x297mm)"
        ])

        with tab_comm_view_thumb:
            caption_title = "실시간 완성 미리보기: 상가 임차 (1080 x 1080 px)" if not is_sale_mode else "실시간 완성 미리보기: 상가 매매 (1080 x 1080 px)"
            st.image(comm_thumb_img, caption=caption_title, use_container_width=True)

        with tab_comm_view_a4:
            # 상가 포스터에 전달할 파라미터 조합
            if not is_sale_mode:
                comm_a4_title = st.session_state.comm_lease_main_title or "상가 임대"
                comm_a4_sub = st.session_state.comm_lease_cp_top or st.session_state.comm_lease_cp_bot or "역세권 특급 상권"
                comm_a4_feature = st.session_state.comm_lease_top_badge or "추천 매물"
                comm_a4_trade = "임대"
                comm_a4_price = st.session_state.comm_lease_spec1.split("|")[-1].strip() if "|" in st.session_state.comm_lease_spec1 else st.session_state.comm_lease_spec1
                comm_a4_specs = [
                    st.session_state.comm_lease_spec1,
                    st.session_state.comm_lease_spec2,
                    st.session_state.comm_lease_pin_bubble if st.session_state.comm_lease_show_pin else "유동인구 풍부",
                    "즉시입점 협의가능",
                    "도로변 가시성 우수"
                ]
            else:
                comm_a4_title = st.session_state.comm_sale_main_sub or "수익형 상가 매매"
                comm_a4_sub = st.session_state.comm_sale_top_left or "급매 / 고수익률"
                comm_a4_feature = st.session_state.comm_sale_top_right or "특급 투자처"
                comm_a4_trade = "매매"
                comm_a4_price = st.session_state.comm_sale_main_hl or st.session_state.comm_sale_price_spec or "수익률 7.2%"
                comm_a4_specs = [
                    st.session_state.comm_sale_price_spec,
                    st.session_state.comm_sale_main_hl,
                    "자주식 주차 및 승강기 완비",
                    "안정적인 임대수익 보장",
                    "사상 역세권 핵심 상권"
                ]

            with st.spinner("상가 창문 부착용 300DPI 초고화질 A4 포스터 렌더링 중..."):
                comm_a4_poster_img = render_a4_window_poster(
                    thumbnail_img=None,
                    bg_image=uploaded_comm_bg,
                    item_no=st.session_state.get("comm_item_no", "No. COMM-01"),
                    main_title=comm_a4_title,
                    sub_title=comm_a4_sub,
                    feature_text=comm_a4_feature,
                    trade_type=comm_a4_trade,
                    price_text=comm_a4_price,
                    spec_lines=comm_a4_specs,
                    office_name=st.session_state.get("comm_ad_office_name", "참좋은공인중개사사무소"),
                    office_owner=st.session_state.get("comm_ad_office_owner", "신제환"),
                    office_phone=st.session_state.get("comm_ad_office_phone", "010-9667-4201"),
                    office_reg_no=st.session_state.get("comm_ad_office_reg_no", "제 26530-2026-00009 호"),
                    office_address=st.session_state.get("comm_ad_office_address", "부산광역시 사상구 강선로 9, 1층"),
                    is_commercial=True
                )
            st.image(comm_a4_poster_img, caption="상가 유리창 부착용 A4 브리핑 포스터 (초고화질 300 DPI)", use_container_width=True)

    with col_ct_right:
        st.text_input("🏷️ 물건 번호 (매물번호)", key="comm_item_no")
        if not is_sale_mode:
            st.markdown("### 🛠️ 상가 임차 텍스트 수정")
            st.text_input("🏷️ 상단 캡슐 뱃지 문구", key="comm_lease_top_badge")
            st.text_input("📢 상단 강조 카피 (1행)", key="comm_lease_cp_top")
            st.text_input("🏬 메인 타이틀 (골드 3D)", key="comm_lease_main_title")
            st.text_input("✨ 하단 서브 카피 (2행)", key="comm_lease_cp_bot")
            
            st.markdown("#### 📍 중앙 골드 핀 & 말풍선")
            st.checkbox("3D 골드 위치 핀 및 말풍선 표시", key="comm_lease_show_pin")
            if st.session_state.comm_lease_show_pin:
                st.text_input("말풍선 문구", key="comm_lease_pin_bubble")

            st.markdown("#### 📋 다크 글래스모피즘 스펙 박스")
            st.text_input("스펙 1행 (전용면적 | 보증금/월세)", key="comm_lease_spec1")
            st.text_input("스펙 2행 (추천 업종 / 특징)", key="comm_lease_spec2")

            st.markdown("#### 🏢 하단 띠지 정보")
            st.checkbox("하단 띠지 표시", key="comm_lease_show_footer")
            if st.session_state.comm_lease_show_footer:
                c_of1, c_of2 = st.columns(2)
                with c_of1:
                    st.text_input("사무소 상호", key="comm_lease_office")
                with c_of2:
                    st.text_input("소장명 / 직책", key="comm_lease_broker")
        else:
            st.markdown("### 🛠️ 상가 매매 텍스트 수정")
            c_sb1, c_sb2 = st.columns(2)
            with c_sb1:
                st.text_input("🏷️ 상단 좌측 골드 뱃지", key="comm_sale_top_left")
            with c_sb2:
                st.text_input("🏷️ 상단 좌측 다크 뱃지", key="comm_sale_top_right")

            st.checkbox("상단 우측 골드 차트/빌딩 아이콘 표시", key="comm_sale_show_chart")

            st.text_input("💰 메인 하이라이트 (수익률 등 골드 대형)", key="comm_sale_main_hl")
            st.text_input("🏬 메인 서브 타이틀 (화이트 볼드)", key="comm_sale_main_sub")

            st.markdown("#### 📊 하단 스펙 인포 바")
            st.text_input("금액 및 투자 스펙 요약", key="comm_sale_price_spec")

            st.markdown("#### 🏢 하단 띠지 정보")
            st.checkbox("하단 띠지 표시", key="comm_sale_show_footer")
            if st.session_state.comm_sale_show_footer:
                c_of1, c_of2 = st.columns(2)
                with c_of1:
                    st.text_input("사무소 상호", key="comm_sale_office")
                with c_of2:
                    st.text_input("소장명 / 직책", key="comm_sale_broker")

        # 1. 상가 썸네일 다운로드 바이트
        img_byte_arr = io.BytesIO()
        comm_thumb_img.save(img_byte_arr, format="PNG", quality=98)
        img_bytes = img_byte_arr.getvalue()

        mode_tag = "상가임차" if not is_sale_mode else "상가매매"
        comm_clean_title = re.sub(r'[^\w\s-]', '', (st.session_state.comm_lease_main_title if not is_sale_mode else st.session_state.comm_sale_main_sub)).strip().replace(" ", "_")
        comm_filename = f"{mode_tag}_{comm_clean_title}.png"

        # 2. 상가 A4 창문 포스터 다운로드 및 인쇄 바이트
        comm_a4_byte_arr = io.BytesIO()
        comm_a4_poster_img.save(comm_a4_byte_arr, format="PNG", quality=98)
        comm_a4_bytes = comm_a4_byte_arr.getvalue()
        comm_a4_download_filename = f"창문부착용_상가_{mode_tag}_{comm_clean_title}_A4포스터.png"

        st.markdown("<hr style='margin: 15px 0 12px 0;'/>", unsafe_allow_html=True)
        st.markdown("### 📥 출력 및 저장 옵션")

        tab_comm_down_thumb, tab_comm_down_a4 = st.tabs([
            f"🖼️ 1. {mode_tag} 썸네일 저장",
            "🖨️ 2. 창문 부착용 A4 바로 출력/저장"
        ])

        with tab_comm_down_thumb:
            st.download_button(
                label=f"📥 1080x1080 {mode_tag} 썸네일 저장 (기본 다운로드)",
                data=img_bytes,
                file_name=comm_filename,
                mime="image/png",
                key="btn_comm_thumb_download",
                use_container_width=True
            )
            st.markdown(render_direct_download_button(img_bytes, comm_filename, "💾 [즉시 다운로드] 썸네일 원클릭 파일 저장", bg_color="#DAA844"), unsafe_allow_html=True)
            st.caption("📱 스마트폰에서는 위 이미지를 1초간 길게 누르시면 '사진 앱에 저장'도 가능합니다.")

        with tab_comm_down_a4:
            st.markdown(render_direct_print_button(comm_a4_bytes, comm_a4_download_filename, "🖨️ [원클릭 즉시 인쇄] 상가 창문용 A4 바로 출력 (Ctrl+P)", bg_color="#B7791F"), unsafe_allow_html=True)
            st.download_button(
                label="📥 300DPI 초고화질 A4 포스터 파일 저장",
                data=comm_a4_bytes,
                file_name=comm_a4_download_filename,
                mime="image/png",
                key="btn_comm_a4_download_main",
                use_container_width=True
            )
            st.markdown(render_direct_download_button(comm_a4_bytes, comm_a4_download_filename, "💾 [즉시 다운로드] A4 포스터 원클릭 파일 저장", bg_color="#2B6CB0"), unsafe_allow_html=True)
            st.markdown("""
            <div style="font-size:12.5px; color:#2D3748; background:#F8FAFC; border:1px solid #CBD5E0; padding:10px 14px; border-radius:8px; margin-top:6px; line-height:1.5;">
                💡 <b>상가 매물 창문 부착 팁:</b><br/>
                1. 상단의 <b>[🖨️ 원클릭 즉시 인쇄]</b>를 누르시면 프린터 인쇄창이 바로 뜹니다.<br/>
                2. 용지 방향을 <b>'세로'</b>, 배율을 <b>'용지에 맞춤'</b>으로 선택하시면 A4 용지에 선명하고 꽉 차게 인쇄됩니다.<br/>
                3. 상가 매물은 골드 톤 디자인으로 유리창에 부착 시 고급스럽고 매물 문의율이 매우 높습니다!
            </div>
            """, unsafe_allow_html=True)

        st.info("💡 상가 썸네일과 포스터를 만드셨다면, 상단의 **'🏪 ④ 상가 중개대상물 표시'** 탭을 클릭하여 상가 전용 네이버 광고 체크리스트 및 블로그 서식을 확인하세요!")


# ====================================================
# [ 탭 3 ] 아파트 네이버 광고 & 대상중개물 표시 생성기
# (신소장님 지정 16개 순서 완벽 적용)
# ====================================================
with tab_apt_ad:
    st.markdown("""
    <div style="background-color: #F8F9FB; border-left: 4px solid #F48A26; padding: 12px 18px; border-radius: 6px; margin-bottom: 20px;">
        <span style="font-size: 15px; font-weight: 700; color: #1E2022;">
            📝 아파트 매물 인터넷 표시·광고 점검표 (네이버 부동산 광고 입력 순서 16개 항목)
        </span><br/>
        <span style="font-size: 13px; color: #6C757D;">
            네이버 부동산 매물 등록창의 항목 순서와 1:1로 일치하여, 화면을 보면서 빠르고 정확하게 광고를 등록할 수 있습니다.
        </span>
    </div>
    """, unsafe_allow_html=True)

    # 최근 자동완성 성공 알림 배너
    if st.session_state.get("last_applied_msg"):
        st.success(st.session_state["last_applied_msg"])

    # ----------------------------------------------------
    # 🌐 [요구사항 2] 네이버 부동산 매물 연동 (복사 텍스트 & 매물번호)
    # ----------------------------------------------------
    with st.expander("🌐 [원클릭 1초 자동완성] 네이버 부동산 매물 연동 (클립보드 복사 & 매물번호)", expanded=True):
        st.markdown("""
        <div style="font-size:14px; color:#1A365D; background:#EBF8FF; border:1px solid #BEE3F8; padding:10px 14px; border-radius:8px; margin-bottom:12px;">
            🔗 네이버 부동산의 <b>화면 복사 텍스트</b>를 붙여넣거나 <b>매물 번호</b>를 입력하시면, 
            실시간으로 <b>매물명, 거래가격, 층수, 전용/공급면적, 방수, 방향, 주차대수, 준공일 등 16대 점검항목</b>과 <b>블로그 썸네일</b>을 1초 만에 자동 완성합니다!
        </div>
        """, unsafe_allow_html=True)

        tab_crawl_txt, tab_crawl_num = st.tabs([
            "📋 네이버 화면 복사 텍스트 붙여넣기 (가장 확실 & 1초 완성! 추천)",
            "🔍 네이버 매물번호 / URL 크롤링 (실험적)"
        ])

        with tab_crawl_txt:
            st.markdown("""
            <div style="font-size:13px; color:#2B6CB0; background:#EBF8FF; border:1px solid #BEE3F8; padding:8px 12px; border-radius:6px; margin-bottom:8px;">
                💡 <b>1초 자동완성 방법:</b> 네이버 부동산 매물 화면에서 마우스로 매물 정보 영역(매물명, 가격, 면적, 층수 등)을 드래그 복사(Ctrl+C)하여 아래에 붙여넣으세요! 네이버 봇 차단 없이 100% 즉시 반영됩니다.
            </div>
            """, unsafe_allow_html=True)
            clip_article_text = st.text_area(
                "네이버 부동산 매물 상세 복사 텍스트",
                height=120,
                placeholder="예:\n사상 중흥S-클래스 105동 매매 6억 2,000만원\n아파트 공급 111.42㎡ / 전용 79.85㎡, 25/36층, 남동향\n관리비 18만원, 방수/욕실수 3/2개...",
                key="input_naver_clip_text"
            )
            if st.button("⚡ 붙여넣은 매물 텍스트 0.1초 분석 & 16개 항목 즉시 적용", type="primary", use_container_width=True, key="btn_parse_clip_text"):
                if clip_article_text.strip():
                    parsed_clip = parse_naver_clipboard_text(clip_article_text)
                    if parsed_clip:
                        queue_state_update("apply_apt", data=parsed_clip, clean_previous=True, success_msg=f"🎉 네이버 매물 [{parsed_clip.get('main_title', '매물')}] 텍스트 분석 완료! 16대 점검항목과 썸네일에 즉시 자동 반영되었습니다.", target_tab="📝 ③ 아파트 중개대상물 표시")
                    else:
                        st.warning("붙여넣은 텍스트에서 매물 정보를 식별하지 못했습니다. 형식을 확인해주세요.")
                else:
                    st.warning("네이버 부동산 매물 상세 텍스트를 먼저 붙여넣어 주세요.")

        with tab_crawl_num:
            c_cr_in, c_cr_btn = st.columns([2.5, 1])
            with c_cr_in:
                input_article_val = st.text_input(
                    "네이버 부동산 매물 번호 또는 URL",
                    placeholder="예: 2428591234 또는 https://fin.land.naver.com/articles/2428591234",
                    help="네이버 부동산 매물 번호(10자리 내외) 또는 브라우저 주소창 링크를 붙여넣으세요.",
                    key="input_naver_article_no"
                )
            with c_cr_btn:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                btn_do_crawl = st.button("🚀 1초 크롤링 시도", type="primary", use_container_width=True, key="btn_crawl_naver")

            if btn_do_crawl:
                if input_article_val.strip():
                    with st.spinner("네이버 부동산 매물 정보 실시간 조회 중..."):
                        is_ok, msg, c_data = crawl_naver_article(input_article_val.strip())
                        if is_ok:
                            queue_state_update("apply_apt", data=c_data, clean_previous=True, success_msg=f"🎉 {msg} 16대 점검항목과 썸네일에 즉시 자동 반영되었습니다.", target_tab="📝 ③ 아파트 중개대상물 표시")
                        else:
                            st.error(f"⚠️ {msg}")
                else:
                    st.warning("매물 번호 또는 매물 링크 URL을 입력해주세요.")

    # ----------------------------------------------------
    # 📄 [요구사항 1] 공적서류 (집합건물 표제부/전유부, 토지대장) 자동 분석
    # ----------------------------------------------------
    with st.expander("📄 [원클릭 1초 자동완성] 건축물대장 (표제부 / 전유부) & 공적서류 분석", expanded=True):
        st.markdown("""
        <div style="font-size:14px; color:#2D3748; margin-bottom:10px;">
            정부24, 세움터, 일사편리에서 발급받은 <b>건축물대장(표제부/전유부)</b>, <b>토지대장</b>, <b>토지이용계획원</b> PDF 파일을 올리시면 
            <b>소재지, 면적, 층수, 용도, 준공일, 주차, 세대수</b>가 16개 항목에 1초 만에 자동 완성됩니다!<br/>
            <span style="color:#C53030; font-weight:700;">🏢 집합건물의 경우 표제부와 전유부를 함께 올리시면 건물 전체 정보와 호실 정보가 완벽하게 결합(Merge)됩니다.</span>
        </div>
        """, unsafe_allow_html=True)

        tab_doc_smart, tab_doc_split, tab_doc_txt = st.tabs([
            "📁 스마트 다중/통합 PDF 업로드 (표제부+전유부 자동 병합)",
            "🏢 표제부 & 🚪 전유부 2단계 분리 업로드 (집합건물 전용)",
            "📋 서류 텍스트 직접 붙여넣기 (정부24 보안문서 100% 대응)"
        ])

        # [탭 1] 스마트 통합/다중 업로드
        with tab_doc_smart:
            uploaded_docs = st.file_uploader(
                "건축물대장(표제부, 전유부) / 토지대장 PDF 서류를 드래그하여 놓으세요 (복수 선택 지원)",
                type=["pdf"],
                accept_multiple_files=True,
                help="표제부와 전유부 PDF를 2개 모두 선택하거나 드래그하시면 자동으로 각각 분석하여 하나의 완벽한 점검표로 병합합니다.",
                key="doc_multi_pdf_uploader_key"
            )
            if uploaded_docs:
                upload_sig = "-".join([f"{f.name}_{f.size}" for f in uploaded_docs])
                if st.session_state.get("last_smart_upload_sig") != upload_sig:
                    try:
                        with st.spinner("공적서류 정밀 분석 및 16대 항목 자동 반영 중..."):
                            doc_parsed_result = None
                            doc_parsed_type = ""
                            if len(uploaded_docs) == 1:
                                doc_parsed_type, doc_parsed_result, _ = parse_official_document(uploaded_docs[0], uploaded_docs[0].name)
                            else:
                                title_data = {}
                                exclusive_data = {}
                                other_data = {}
                                types_found = []

                                for u_file in uploaded_docs:
                                    p_type, p_res, _ = parse_official_document(u_file, u_file.name)
                                    types_found.append(p_type)
                                    if "표제부" in p_type:
                                        title_data.update(p_res)
                                    elif "전유부" in p_type:
                                        exclusive_data.update(p_res)
                                    else:
                                        other_data.update(p_res)

                                if title_data and exclusive_data:
                                    doc_parsed_result = merge_building_registers(title_data, exclusive_data)
                                    doc_parsed_type = "집합건축물대장 (표제부 + 전유부 2개 서류 완벽 통합)"
                                elif title_data:
                                    doc_parsed_result = title_data
                                    doc_parsed_type = "집합건축물대장 (표제부)"
                                elif exclusive_data:
                                    doc_parsed_result = exclusive_data
                                    doc_parsed_type = "집합건축물대장 (전유부)"
                                else:
                                    doc_parsed_result = other_data
                                    doc_parsed_type = ", ".join(types_found)

                            st.session_state["last_smart_upload_sig"] = upload_sig
                            if doc_parsed_result:
                                queue_state_update("apply_apt", data=doc_parsed_result, clean_previous=True, success_msg=f"🎉 [{doc_parsed_type}] 분석 완료! 16대 점검항목과 썸네일에 1초 만에 즉시 반영되었습니다.", target_tab="📝 ③ 아파트 중개대상물 표시")
                            else:
                                st.error("⚠️ 업로드하신 PDF 서류에서 텍스트를 읽어오지 못했습니다. 정부24/세움터의 위변조 방지 보안 인쇄(DRM) 전자문서이거나 스캔 이미지일 가능성이 높습니다. 정부24 열람 화면에서 마우스로 텍스트를 복사(Ctrl+C)하여 세 번째 [📋 서류 텍스트 직접 붙여넣기] 탭에 넣어주시면 0.1초 만에 완벽하게 분석됩니다!")
                    except Exception as e:
                        st.error(f"서류 분석 중 오류가 발생했습니다: {e}")

        # [탭 2] 표제부 & 전유부 분리 업로드
        with tab_doc_split:
            col_sp_title, col_sp_excl = st.columns(2)
            with col_sp_title:
                st.markdown("""
                <div style="background:#EBF8FF; border:1px solid #90CDF4; border-radius:8px; padding:8px 12px; margin-bottom:8px;">
                    <b>🏢 1. 표제부 (총괄표제부 / 표제부)</b><br/>
                    <span style="font-size:12px; color:#4A5568;">단지명, 최고층수, 총주차대수, 세대수, 준공일, 구조</span>
                </div>
                """, unsafe_allow_html=True)
                up_title_file = st.file_uploader("표제부 PDF 업로드", type=["pdf"], key="up_split_title")

            with col_sp_excl:
                st.markdown("""
                <div style="background:#FEFCBF; border:1px solid #ECC94B; border-radius:8px; padding:8px 12px; margin-bottom:8px;">
                    <b>🚪 2. 전유부 (각 동·호수)</b><br/>
                    <span style="font-size:12px; color:#4A5568;">해당 동, 호수, 해당층, 전용면적, 주거공용면적(공급면적)</span>
                </div>
                """, unsafe_allow_html=True)
                up_excl_file = st.file_uploader("전유부 PDF 업로드", type=["pdf"], key="up_split_excl")

            if up_title_file or up_excl_file:
                split_sig = f"{getattr(up_title_file, 'name', '')}_{getattr(up_title_file, 'size', '')}_{getattr(up_excl_file, 'name', '')}_{getattr(up_excl_file, 'size', '')}"
                if st.session_state.get("last_split_upload_sig") != split_sig:
                    try:
                        with st.spinner("표제부 및 전유부 정밀 분석 중..."):
                            t_data_sp = {}
                            e_data_sp = {}
                            if up_title_file:
                                _, t_data_sp, _ = parse_official_document(up_title_file, up_title_file.name)
                            if up_excl_file:
                                _, e_data_sp, _ = parse_official_document(up_excl_file, up_excl_file.name)

                            doc_parsed_res_sp = None
                            doc_type_sp = ""
                            if t_data_sp and e_data_sp:
                                doc_parsed_res_sp = merge_building_registers(t_data_sp, e_data_sp)
                                doc_type_sp = "집합건축물대장 (표제부 + 전유부 2단계 통합 완성)"
                            elif t_data_sp:
                                doc_parsed_res_sp = t_data_sp
                                doc_type_sp = "집합건축물대장 (표제부 단독)"
                            elif e_data_sp:
                                doc_parsed_res_sp = e_data_sp
                                doc_type_sp = "집합건축물대장 (전유부 단독)"

                            st.session_state["last_split_upload_sig"] = split_sig
                            if doc_parsed_res_sp:
                                queue_state_update("apply_apt", data=doc_parsed_res_sp, clean_previous=True, success_msg=f"🎉 [{doc_type_sp}] 분석 완료! 16대 점검항목과 썸네일에 즉시 자동 반영되었습니다.", target_tab="📝 ③ 아파트 중개대상물 표시")
                            else:
                                st.error("⚠️ 분리 업로드된 PDF 파일에서 텍스트를 감지하지 못했습니다. 보안(DRM) 문서인 경우 세 번째 [📋 서류 텍스트 직접 붙여넣기] 탭을 이용해주세요!")
                    except Exception as e:
                        st.error(f"분리 서류 분석 중 오류: {e}")

        # [탭 3] 텍스트 직접 붙여넣기
        with tab_doc_txt:
            sub_txt_tab1, sub_txt_tab2 = st.tabs([
                "📋 대장 전체 텍스트(스크립트) 통째로 붙여넣기 (가장 편리 & ⭐추천)",
                "🏢 표제부 & 🚪 전유부 2칸 분리 붙여넣기 (선택)"
            ])
            with sub_txt_tab1:
                st.markdown("""
                <div style="font-size:13px; color:#2D3748; background:#F7FAFC; border:1px solid #CBD5E0; padding:8px 12px; border-radius:6px; margin-bottom:8px;">
                    💡 <b>1초 자동 분석:</b> 정부24, 세움터, 일사편리에서 열람한 건축물대장 텍스트 전체(표제부/전유부/일반대장)를 마우스로 복사(Ctrl+C)하여 아래에 그대로 붙여넣으세요! 표제부와 전유부를 자동으로 인식하여 병합합니다.
                </div>
                """, unsafe_allow_html=True)
                raw_unified_txt = st.text_area(
                    "건축물대장 전체 열람 복사 텍스트 (스크립트)",
                    height=130,
                    placeholder="대지위치: 부산시 사상구 덕포동 220\n건축물명칭: 사상 중흥S-클래스 제105동 제2501호\n층별: 25층\n전유부분 면적: 79.85㎡\n사용승인일: 2023-07-28...",
                    key="txt_raw_unified_doc"
                )
                if st.button("🔍 붙여넣은 대장 텍스트 0.1초 통합 분석 & 즉시 적용", type="primary", key="btn_parse_unified_text", use_container_width=True):
                    if raw_unified_txt.strip():
                        u_doc_type, u_doc_res = parse_raw_script_document(raw_unified_txt)
                        if u_doc_res:
                            queue_state_update("apply_apt", data=u_doc_res, clean_previous=True, success_msg=f"🎉 [{u_doc_type}] 분석 완료! 16대 점검항목과 썸네일에 즉시 자동 반영되었습니다.", target_tab="📝 ③ 아파트 중개대상물 표시")
                        else:
                            st.warning("붙여넣은 대장 텍스트에서 건축물 정보를 식별하지 못했습니다. 내용을 확인해주세요.")
                    else:
                        st.warning("건축물대장 텍스트를 먼저 붙여넣어 주세요.")

            with sub_txt_tab2:
                col_txt_t, col_txt_e = st.columns(2)
                with col_txt_t:
                    st.markdown("<b>🏢 표제부 텍스트</b>", unsafe_allow_html=True)
                    raw_title_txt = st.text_area(
                        "표제부 열람 텍스트",
                        height=100,
                        placeholder="대지위치: 부산시 사상구 덕포동 220\n건축물명칭: 사상 중흥S-클래스\n층수: 지상 36층 / 지하 3층\n세대수: 1,572세대\n주차대수: 1,685대\n사용승인일: 2023-07-28...",
                        key="txt_raw_title"
                    )
                with col_txt_e:
                    st.markdown("<b>🚪 전유부 텍스트</b>", unsafe_allow_html=True)
                    raw_excl_txt = st.text_area(
                        "전유부 열람 텍스트",
                        height=100,
                        placeholder="건축물명칭: 제105동 제2501호\n층별: 25층\n전유부분 면적: 79.85㎡\n공용부분(계단/복도): 31.57㎡...",
                        key="txt_raw_excl"
                    )

                if st.button("🔍 분리 입력된 표제부/전유부 텍스트 분석 및 즉시 적용", type="primary", key="btn_parse_split_text", use_container_width=True):
                    t_parsed = parse_building_register_title(raw_title_txt) if raw_title_txt.strip() else {}
                    e_parsed = parse_building_register_exclusive(raw_excl_txt) if raw_excl_txt.strip() else {}

                    doc_parsed_res_txt = None
                    doc_type_txt = ""
                    if t_parsed and e_parsed:
                        doc_parsed_res_txt = merge_building_registers(t_parsed, e_parsed)
                        doc_type_txt = "집합건축물대장 (표제부 + 전유부 텍스트 통합완료)"
                    elif t_parsed:
                        doc_parsed_res_txt = t_parsed
                        doc_type_txt = "집합건축물대장 (표제부 텍스트)"
                    elif e_parsed:
                        doc_parsed_res_txt = e_parsed
                        doc_type_txt = "집합건축물대장 (전유부 텍스트)"

                    if doc_parsed_res_txt:
                        queue_state_update("apply_apt", data=doc_parsed_res_txt, clean_previous=True, success_msg=f"🎉 [{doc_type_txt}] 분석 완료! 16대 점검항목과 썸네일에 즉시 자동 반영되었습니다.", target_tab="📝 ③ 아파트 중개대상물 표시")
                    else:
                        st.warning("붙여넣은 텍스트에서 건축물대장 정보를 식별하지 못했습니다. 내용을 확인해주세요.")

    # 썸네일 데이터에서 가져오기 및 퀵 컨트롤 버튼
    col_syn1, col_syn2, col_syn3 = st.columns([1, 1, 1])
    with col_syn1:
        if st.button("🔄 썸네일 입력값 동기화", use_container_width=True, help="1단계 썸네일에 입력한 층수, 가격, 날짜 등을 가져옵니다."):
            st.session_state.ad_trade_type = st.session_state.thumb_trade_type
            st.session_state.ad_price_text = st.session_state.thumb_price_text
            st.session_state.ad_floor_info = st.session_state.spec_line1
            st.session_state.ad_room_bath = st.session_state.spec_line3
            st.session_state.ad_move_in_date = st.session_state.spec_line4
            st.session_state.ad_direction = st.session_state.spec_line5
            st.success("썸네일 정보가 점검표에 반영되었습니다!")
            st.rerun()
    with col_syn2:
        if st.button("✨ 새 매물 빈 양식 만들기", use_container_width=True, help="새로운 매물을 등록할 수 있도록 모든 입력칸을 깨끗하게 비웁니다."):
            st.session_state.ad_location = ""
            st.session_state.ad_area_supply = ""
            st.session_state.ad_area_exclusive = ""
            st.session_state.ad_floor_info = ""
            st.session_state.ad_room_bath = ""
            st.session_state.ad_maintenance_fee = ""
            st.session_state.ad_maintenance_detail = ""
            st.session_state.ad_price_text = ""
            st.session_state.ad_deposit_sub = "- / -"
            st.session_state.ad_direction = ""
            st.session_state.ad_move_in_date = "즉시입주 협의가능"
            st.session_state.ad_parking = ""
            st.session_state.ad_households = ""
            st.session_state.ad_building_use = "공동주택 (아파트)"
            st.session_state.ad_approval_date = ""
            st.info("입력칸이 초기화되었습니다. 새로운 매물 정보를 입력해주세요.")
            st.rerun()
    with col_syn3:
        if st.button("📋 사상 중흥S-클래스 예시 복원", use_container_width=True, help="기본 사상 중흥S-클래스 예시 데이터를 다시 채웁니다."):
            for k, v in DEFAULT_SPEC.items():
                st.session_state[f"ad_{k}"] = v
            st.success("기본 예시 데이터로 복원되었습니다.")
            st.rerun()

    # 좌우 컬럼 분할 (PC에서는 좌:입력 / 우:결과, 모바일에서는 위:입력 / 아래:결과)
    col_ad_input, col_ad_output = st.columns([1.1, 1.2])

    with col_ad_input:
        st.markdown("""
        <div style="background:#EBF8FF; border:1.5px solid #63B3ED; border-radius:10px; padding:12px 16px; margin-bottom:15px;">
            <div style="font-size:14px; font-weight:700; color:#2B6CB0; margin-bottom:3px;">
                ✏️ <b>입력 및 수정 방법</b>
            </div>
            <div style="font-size:13px; color:#2D3748; line-height:1.4;">
                아래 흰색 <b>네모 칸을 마우스로 클릭</b>하시면 글자를 바로 지우고 자유롭게 수정하실 수 있습니다!<br/>
                새로운 매물을 등록하시려면 상단의 <b>[✨ 새 매물 빈 양식 만들기]</b> 버튼을 누르시면 편리합니다.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("### 📋 16대 점검항목 입력 및 수정")

        # 1. 소재지
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <b>01. 소재지</b>
            <span class="spec-badge badge-red">동·리·지번 필수</span>
        </div>
        """, unsafe_allow_html=True)
        st.text_input(
            "소재지 주소",
            key="ad_location",
            help="동·리 및 지번 표기 필수 (아파트 동·호수는 생략 가능)"
        )

        # 2. 공급/전용면적
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>02. 공급 / 전용면적</b>
            <span class="spec-badge badge-orange">법정단위 ㎡ 표기 (평수 제외)</span>
        </div>
        """, unsafe_allow_html=True)
        c_ar1, c_ar2 = st.columns(2)
        with c_ar1:
            st.text_input("공급면적 (㎡)", key="ad_area_supply")
        with c_ar2:
            st.text_input("전용면적 (㎡)", key="ad_area_exclusive")
        
        # 실시간 면적 및 전용률 계산 프리뷰 (법정계량단위 ㎡ 단독 표기, 평형 제외)
        area_sum_m2, _ = format_area_text(st.session_state.ad_area_supply, st.session_state.ad_area_exclusive)
        st.markdown(f"""
        <div style="background:#F1F3F5; padding:6px 12px; border-radius:6px; font-size:13px; color:#495057; margin-bottom:8px;">
            📐 <b>계산 결과:</b> {area_sum_m2}
        </div>
        """, unsafe_allow_html=True)

        # 3. 해당층 / 총층
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>03. 해당층 / 총층</b>
            <span class="spec-badge badge-green">저/중/고 표기가능</span>
        </div>
        """, unsafe_allow_html=True)
        st.text_input(
            "해당층 / 총층",
            key="ad_floor_info",
            help="예: 25 / 36층 (아파트의 경우 의뢰인 요청 시 저/중/고층 대체 가능)"
        )

        # 4. 방수 / 욕실수
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>04. 방수 / 욕실수</b>
            <span class="spec-badge badge-gray">대장 기준</span>
        </div>
        """, unsafe_allow_html=True)
        st.text_input(
            "방수 / 욕실수",
            key="ad_room_bath",
            help="예: 3 / 2개"
        )

        # 5. 관리비
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>05. 관리비 & 세부내역</b>
            <span class="spec-badge badge-red">월 10만원↑ 세부내역 필수</span>
        </div>
        """, unsafe_allow_html=True)
        c_mf1, c_mf2 = st.columns([1, 1.4])
        with c_mf1:
            st.text_input("월 관리비", key="ad_maintenance_fee", placeholder="예: 월 18만 원")
        with c_mf2:
            st.text_input(
                "세부내역 (알아보기 쉬운 분리 기재)",
                key="ad_maintenance_detail",
                placeholder="예: 공용관리비 약 13만 원 (수도·전기·가스 실사용량 별도 부과)",
                help="공용관리비와 개별 사용량(전기/수도/가스)을 명확히 구분하여 기재"
            )

        # 6. 거래 형태 & 7. 가격
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>06. 거래 형태 & 07. 가격</b>
            <span class="spec-badge badge-orange">정확한 가격 명시</span>
        </div>
        """, unsafe_allow_html=True)
        c_pr1, c_pr2 = st.columns([1, 1.4])
        with c_pr1:
            trade_opts_ad = ["매매", "전세", "월세", "단기임대"]
            if st.session_state.ad_trade_type not in trade_opts_ad:
                st.session_state.ad_trade_type = trade_opts_ad[0]
            st.selectbox("거래 형태", trade_opts_ad, key="ad_trade_type")
        with c_pr2:
            st.text_input("거래 가격", key="ad_price_text")
        
        st.text_input(
            "기보증금 / 월세 승계액",
            key="ad_deposit_sub",
            help="기보증금 또는 월세가 있는 경우 작성 (없으면 '- / -')"
        )

        # 8. 방향
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>08. 방향 (기준 명시)</b>
            <span class="spec-badge badge-green">주실(거실) 기준</span>
        </div>
        """, unsafe_allow_html=True)
        st.text_input("방향", key="ad_direction", help="예: 남동향 (거실 기준)")

        # 9. 현관구조 & 10. 난방
        c_et1, c_et2 = st.columns(2)
        with c_et1:
            st.markdown("<b>09. 현관구조</b>", unsafe_allow_html=True)
            entrance_opts = ["계단식", "복도식", "복합식"]
            if st.session_state.ad_entrance_type not in entrance_opts:
                st.session_state.ad_entrance_type = entrance_opts[0]
            st.selectbox("현관구조", entrance_opts, key="ad_entrance_type")
        with c_et2:
            st.markdown("<b>10. 난방(방식/연료)</b>", unsafe_allow_html=True)
            st.text_input("난방방식/연료", key="ad_heating")

        # 11. 입주가능일 & 12. 총주차대수
        c_mv1, c_mv2 = st.columns(2)
        with c_mv1:
            st.markdown("<b>11. 입주가능일</b>", unsafe_allow_html=True)
            st.text_input("입주가능일", key="ad_move_in_date")
        with c_mv2:
            st.markdown("<b>12. 총주차대수</b>", unsafe_allow_html=True)
            st.text_input("총주차대수", key="ad_parking")

        # 13. 해당면적 세대수 & 14. 건축물 용도
        c_hs1, c_hs2 = st.columns(2)
        with c_hs1:
            st.markdown("<b>13. 해당면적 세대수</b>", unsafe_allow_html=True)
            st.text_input("해당면적 세대수", key="ad_households")
        with c_hs2:
            st.markdown("<b>14. 건축물 용도</b>", unsafe_allow_html=True)
            st.text_input("건축물 용도", key="ad_building_use")

        # 15. 사용승인일
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>15. 사용승인일 (준공일)</b>
            <span class="spec-badge badge-red">대장 기준 필수</span>
        </div>
        """, unsafe_allow_html=True)
        st.text_input("사용승인일", key="ad_approval_date", help="건축물대장 상 사용승인일 기재 필수")

        # 16. 중개사무소 정보 (ON/OFF 선택 및 소공 지원)
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 15px; margin-bottom: 5px;">
            <b>16. 중개사무소 정보</b>
            <span class="spec-badge badge-green">ON/OFF 선택 가능</span>
        </div>
        """, unsafe_allow_html=True)

        st.checkbox(
            "✅ 중개사무소 정보 포함하기 (텍스트 및 카드 이미지에 반영)",
            key="ad_include_office_info",
            help="체크 해제 시 중개사무소 정보를 제외하고 순수 매물 정보(01~15번 항목)만 출력합니다."
        )

        if st.session_state.ad_include_office_info:
            c_of1, c_of2 = st.columns(2)
            with c_of1:
                st.text_input("중개사무소 명칭 (상호)", key="ad_office_name")
                st.text_input("대표 공인중개사 성명", key="ad_office_owner")
                st.text_input("사무실 연락처", key="ad_office_phone")
            with c_of2:
                st.text_input("중개등록번호", key="ad_office_reg_no")
                st.text_input("사무소 소재지", key="ad_office_address")

            st.markdown("<b>👤 소속공인중개사(소공) 담당자 정보 (선택 입력)</b>", unsafe_allow_html=True)
            c_as1, c_as2 = st.columns(2)
            with c_as1:
                st.text_input("소공/담당자 성명", key="ad_assistant_name", placeholder="예: 김소공 소속공인중개사")
            with c_as2:
                st.text_input("담당자 직통 연락처", key="ad_assistant_phone", placeholder="예: 010-1234-5678")
        else:
            st.info("ℹ️ 중개사무소 정보가 제외되었습니다. 순수 매물 스펙(01~15번 항목)만 출력됩니다. (소공 및 협력 중개사 활용 가능)")


    # 우측: 실시간 완성 뷰 (네이버 광고 점검표 1:1 대조 리스트)
    with col_ad_output:
        st.markdown("### 📋 네이버 광고 16개 점검표 (대조용)")
        st.caption("네이버 부동산 매물 등록창을 띄워두고 위에서부터 순서대로 보며 입력하세요.")

        # 현재 입력 데이터 딕셔너리 구축
        current_spec_data = {
            "location": st.session_state.ad_location,
            "area_supply": st.session_state.ad_area_supply,
            "area_exclusive": st.session_state.ad_area_exclusive,
            "floor_info": st.session_state.ad_floor_info,
            "room_bath": st.session_state.ad_room_bath,
            "maintenance_fee": st.session_state.ad_maintenance_fee,
            "maintenance_detail": st.session_state.ad_maintenance_detail,
            "trade_type": st.session_state.ad_trade_type,
            "price_text": st.session_state.ad_price_text,
            "deposit_sub": st.session_state.ad_deposit_sub,
            "direction": st.session_state.ad_direction,
            "entrance_type": st.session_state.ad_entrance_type,
            "heating": st.session_state.ad_heating,
            "move_in_date": st.session_state.ad_move_in_date,
            "parking": st.session_state.ad_parking,
            "households": st.session_state.ad_households,
            "building_use": st.session_state.ad_building_use,
            "approval_date": st.session_state.ad_approval_date,
            "office_name": st.session_state.ad_office_name,
            "office_owner": st.session_state.ad_office_owner,
            "office_reg_no": st.session_state.ad_office_reg_no,
            "office_address": st.session_state.ad_office_address,
            "office_phone": st.session_state.ad_office_phone,
            "include_office_info": st.session_state.ad_include_office_info,
            "assistant_name": st.session_state.ad_assistant_name,
            "assistant_phone": st.session_state.ad_assistant_phone,
        }

        # 16개 항목 카드 리스트 (코드 노출 없는 안전한 인라인 렌더링)
        items_list = get_ordered_spec_table_data(current_spec_data)
        
        rows_html = []
        for it in items_list:
            num_str = f"{it['num']:02d}"
            # 줄바꿈은 <br/>로 깔끔하게 한 줄씩 정돈
            val_formatted = it['val'].replace('\n', '<br/>')
            row_markup = f'<div style="border-bottom:1px solid #E9ECEF; padding:11px 6px;"><div style="display:flex; justify-content:space-between; margin-bottom:4px;"><span style="font-size:14px; font-weight:700; color:#333D4B;"><span style="color:#F48A26;">[{num_str}]</span> {it["name"]}</span><span style="font-size:12px; color:#8B95A1;">{it["guide"]}</span></div><div style="font-size:15px; color:#191F28; font-weight:600; line-height:1.6; background:#F8F9FB; padding:8px 12px; border-radius:6px; margin-top:4px;">{val_formatted}</div></div>'
            rows_html.append(row_markup)

        full_table_html = f'<div style="background:#FFFFFF; border:1.5px solid #CBD5E0; border-radius:12px; padding:14px 18px; box-shadow:0 2px 8px rgba(0,0,0,0.04); max-height:680px; overflow-y:auto;">{"".join(rows_html)}</div>'
        st.markdown(full_table_html, unsafe_allow_html=True)

        # 전체 텍스트 복사 영역
        st.markdown("<br/>", unsafe_allow_html=True)
        ad_guide_txt = generate_naver_ad_guide_text(current_spec_data)
        st.text_area("📋 [네이버 광고 대조용] 전체 텍스트 복사", value=ad_guide_txt, height=130)

        # 필요 시 1080px 고화질 표시 카드 이미지 다운로드 접이식 메뉴 (중복 이미지는 삭제하고 다운로드 기능만 제공)
        with st.expander("🖼️ [다운로드] 1080px 중개대상물 표시 카드 저장하기", expanded=False):
            with st.spinner("표시 카드 렌더링 중..."):
                spec_card_img = render_spec_table_image(current_spec_data)
            card_byte_arr = io.BytesIO()
            spec_card_img.save(card_byte_arr, format="PNG", quality=95)
            card_bytes = card_byte_arr.getvalue()

            clean_loc = re.sub(r'[^\w\s-]', '', (st.session_state.ad_location.split(" ")[-1] if st.session_state.ad_location else "매물")).strip()
            clean_trade = re.sub(r'[^\w\s-]', '', (st.session_state.ad_trade_type or "매매")).strip()
            card_filename = f"중개대상물표시_{clean_loc}_{clean_trade}.png"

            st.markdown(render_direct_download_button(card_bytes, card_filename, "💾 [원클릭 즉시 다운로드] 1080px 표시 카드 저장", "#1A202C"), unsafe_allow_html=True)
            st.caption("스마트폰에서는 위 버튼을 누르시면 사진첩에 바로 다운로드 저장됩니다.")


# ====================================================
# [ 탭 4 ] 상가 중개대상물 표시 생성기 (임차 & 매매 전용)
# ====================================================
with tab_comm_ad:
    st.markdown("""
    <div style="background-color: #181C24; border-left: 4px solid #DAA844; padding: 14px 18px; border-radius: 6px; margin-bottom: 20px; color: #FFFFFF;">
        <span style="font-size: 16px; font-weight: 700; color: #DAA844;">
            🏪 상가(근린생활시설/점포/건물) 인터넷 표시·광고 점검표 & 블로그 서식 생성기
        </span><br/>
        <span style="font-size: 13px; color: #CBD5E0;">
            주출입구 방향, 화장실 구분, 권리금, 추천업종, 전기/설비, 매매 시 연간 수익률 분석 등 상가 실무에 특화된 법정 표시사항을 완벽하게 생성합니다.
        </span>
    </div>
    """, unsafe_allow_html=True)

    # 1. 거래 형태 라디오 (임대차 vs 매매)
    comm_ad_mode_select = st.radio(
        "상가 거래 형태 선택",
        options=["🔑 상가 임대차 (월세)", "💰 상가 매매 (수익형)"],
        index=0 if "임대차" in st.session_state.comm_ad_mode or "월세" in st.session_state.comm_ad_mode else 1,
        horizontal=True,
        key="comm_ad_mode_radio_selector"
    )
    st.session_state.comm_ad_mode = comm_ad_mode_select
    is_comm_ad_sale = "매매" in comm_ad_mode_select

    # 2. 퀵 액션 버튼들
    c_btn1, c_btn2, c_btn3 = st.columns([1.2, 1, 1])
    with c_btn1:
        if st.button("🔄 상가 썸네일 입력값 동기화", use_container_width=True, help="② 상가 썸네일 탭에 입력한 타이틀과 스펙을 점검표로 가져옵니다."):
            if not is_comm_ad_sale:
                st.session_state.comm_ad_trade_type = "월세"
                st.session_state.comm_ad_recommended_use = st.session_state.comm_lease_spec2.replace("추천 :", "").strip()
                if "|" in st.session_state.comm_lease_spec1:
                    parts = st.session_state.comm_lease_spec1.split("|")
                    st.session_state.comm_ad_price_text = parts[1].strip()
            else:
                st.session_state.comm_ad_trade_type = "매매"
                st.session_state.comm_ad_yield_rate = st.session_state.comm_sale_main_hl
                st.session_state.comm_ad_deposit_rent_summary = st.session_state.comm_sale_price_spec
            st.success("상가 썸네일 입력값이 점검표에 동기화되었습니다!")
            st.rerun()
    with c_btn2:
        if st.button("📋 추천 상가 예시 복원", use_container_width=True):
            defaults = DEFAULT_COMMERCIAL_SPEC_SALE if is_comm_ad_sale else DEFAULT_COMMERCIAL_SPEC_LEASE
            for k, v in defaults.items():
                st.session_state[f"comm_ad_{k}"] = v
            st.success("기본 추천 예시로 복원되었습니다.")
            st.rerun()
    with c_btn3:
        if st.button("✨ 새 상가 빈 양식 만들기", use_container_width=True):
            empty_keys = [
                "location", "area_exclusive", "area_contract", "floor_info", "restroom",
                "maintenance_fee", "maintenance_detail", "price_text", "premium_fee",
                "deposit_rent_summary", "loan_amount", "actual_investment", "yield_rate",
                "direction", "move_in_date", "parking", "current_use", "recommended_use",
                "building_use", "zone_region", "zone_district", "structure", "approval_date", "facility_info"
            ]
            for k in empty_keys:
                st.session_state[f"comm_ad_{k}"] = ""
            st.info("입력칸이 초기화되었습니다.")
            st.rerun()

    # 최근 상가 자동완성 성공 알림 배너
    if st.session_state.get("last_comm_applied_msg"):
        st.success(st.session_state["last_comm_applied_msg"])

    # ----------------------------------------------------
    # 🌐 상가 네이버 부동산 매물 연동 (복사 텍스트 & 매물번호)
    # ----------------------------------------------------
    with st.expander("🌐 [원클릭 1초 자동완성] 네이버 부동산 상가 매물 연동 (클립보드 복사 & 매물번호)", expanded=True):
        st.markdown("""
        <div style="font-size:14px; color:#1A365D; background:#EBF8FF; border:1px solid #BEE3F8; padding:10px 14px; border-radius:8px; margin-bottom:12px;">
            🔗 네이버 부동산의 <b>상가 매물 화면 복사 텍스트</b>를 붙여넣거나 <b>상가 매물 번호</b>를 입력하시면, 
            실시간으로 <b>소재지, 가격, 층수, 전용/계약면적, 방향, 주차대수, 용도, 주구조, 권리금 등 상가 18대 항목</b>과 <b>상가 썸네일</b>을 1초 만에 자동 완성합니다!
        </div>
        """, unsafe_allow_html=True)

        comm_tab_crawl_txt, comm_tab_crawl_num = st.tabs([
            "📋 네이버 상가 화면 복사 텍스트 붙여넣기 (가장 확실 & 1초 완성! 추천)",
            "🔍 네이버 상가 매물번호 / URL 크롤링 (실험적)"
        ])

        with comm_tab_crawl_txt:
            st.markdown("""
            <div style="font-size:13px; color:#2B6CB0; background:#EBF8FF; border:1px solid #BEE3F8; padding:8px 12px; border-radius:6px; margin-bottom:8px;">
                💡 <b>1초 자동완성 방법:</b> 네이버 부동산 상가 매물 화면에서 매물 상세 영역을 마우스로 드래그 복사(Ctrl+C)하여 아래에 붙여넣으세요! 네이버 차단 없이 100% 즉시 반영됩니다.
            </div>
            """, unsafe_allow_html=True)
            comm_clip_article_text = st.text_area(
                "네이버 부동산 상가 매물 상세 복사 텍스트",
                height=120,
                placeholder="예:\n괘법동 1층 상가 월세 3,000/180\n제1종근린생활시설 계약 125㎡ / 전용 82.64㎡, 1/5층, 남서향\n무권리, 주구조 철근콘크리트구조, 일반상업지역, 방화지구...",
                key="comm_input_naver_clip_text"
            )
            if st.button("⚡ 붙여넣은 상가 텍스트 0.1초 분석 & 상가 항목 즉시 적용", type="primary", use_container_width=True, key="btn_parse_comm_clip_text"):
                if comm_clip_article_text.strip():
                    parsed_clip = parse_naver_clipboard_text(comm_clip_article_text)
                    if parsed_clip:
                        queue_state_update("apply_comm", data=parsed_clip, success_msg=f"🎉 네이버 상가 매물 [{parsed_clip.get('main_title', '상가')}] 텍스트 분석 완료! 상가 18대 점검항목과 썸네일에 즉시 자동 반영되었습니다.", target_tab="🏪 ④ 상가 중개대상물 표시 (임차·매매)")
                    else:
                        st.warning("붙여넣은 텍스트에서 상가 매물 정보를 식별하지 못했습니다. 형식을 확인해주세요.")
                else:
                    st.warning("네이버 부동산 상가 매물 상세 텍스트를 먼저 붙여넣어 주세요.")

        with comm_tab_crawl_num:
            c_ccr_in, c_ccr_btn = st.columns([2.5, 1])
            with c_ccr_in:
                comm_input_article_val = st.text_input(
                    "네이버 부동산 상가 매물 번호 또는 URL",
                    placeholder="예: 2428591234 또는 https://fin.land.naver.com/articles/2428591234",
                    help="네이버 부동산 매물 번호(10자리 내외) 또는 브라우저 주소창 링크를 붙여넣으세요.",
                    key="comm_input_naver_article_no"
                )
            with c_ccr_btn:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                btn_do_comm_crawl = st.button("🚀 상가 1초 크롤링 시도", type="primary", use_container_width=True, key="btn_crawl_comm_naver")

            if btn_do_comm_crawl:
                if comm_input_article_val.strip():
                    with st.spinner("네이버 부동산 상가 매물 정보 실시간 조회 중..."):
                        is_ok, msg, c_data = crawl_naver_article(comm_input_article_val.strip())
                        if is_ok:
                            queue_state_update("apply_comm", data=c_data, success_msg=f"🎉 {msg} 상가 18대 점검항목과 썸네일에 즉시 자동 반영되었습니다.", target_tab="🏪 ④ 상가 중개대상물 표시 (임차·매매)")
                        else:
                            st.error(f"⚠️ {msg}")
                else:
                    st.warning("상가 매물 번호 또는 매물 링크 URL을 입력해주세요.")

    # ----------------------------------------------------
    # 📄 상가 건축물대장 (일반 / 표제부 / 전유부) & 공적서류 자동 분석
    # ----------------------------------------------------
    with st.expander("📄 [원클릭 1초 자동완성] 상가 건축물대장 (표제부 / 전유부 / 일반건축물) & 토지이용계획 분석", expanded=True):
        st.markdown("""
        <div style="font-size:14px; color:#2D3748; margin-bottom:10px;">
            정부24, 세움터, 일사편리에서 발급받은 <b>건축물대장(일반/표제부/전유부)</b>, <b>토지대장</b>, <b>토지이용계획원</b> PDF 파일을 올리시면 
            <b>소재지, 전용/계약면적, 층수, 용도, 용도지역, 용도지구, 주구조, 준공일, 주차대수, 승강기</b>가 상가 점검항목에 1초 만에 자동 완성됩니다!<br/>
            <span style="color:#C53030; font-weight:700;">🏬 통상가·근린생활시설 건물의 경우 일반건축물대장 또는 총괄표제부를 올리시면 건물 전체 스펙이 완벽하게 추출됩니다.</span>
        </div>
        """, unsafe_allow_html=True)

        comm_tab_doc_smart, comm_tab_doc_split, comm_tab_doc_txt = st.tabs([
            "📁 스마트 다중/통합 PDF 업로드 (일반건축물 / 표제부+전유부 자동 병합)",
            "🏢 표제부 & 🚪 전유부 2단계 분리 업로드 (구분상가 전용)",
            "📋 서류 텍스트 직접 붙여넣기 (정부24 보안문서 100% 대응)"
        ])

        with comm_tab_doc_smart:
            uploaded_comm_docs = st.file_uploader(
                "건축물대장(일반/표제부/전유부) / 토지이용계획원 PDF 서류를 드래그하여 놓으세요 (복수 선택 지원)",
                type=["pdf"],
                accept_multiple_files=True,
                help="일반건축물대장, 표제부, 전유부 PDF를 선택하거나 드래그하시면 자동으로 각각 분석하여 하나의 완벽한 상가 점검표로 병합합니다.",
                key="comm_doc_multi_pdf_uploader_key"
            )
            if uploaded_comm_docs:
                upload_sig = "-".join([f"{f.name}_{f.size}" for f in uploaded_comm_docs])
                if st.session_state.get("last_comm_smart_upload_sig") != upload_sig:
                    try:
                        with st.spinner("상가 공적서류 정밀 분석 및 상가 18대 항목 자동 반영 중..."):
                            doc_parsed_result = None
                            doc_parsed_type = ""
                            if len(uploaded_comm_docs) == 1:
                                doc_parsed_type, doc_parsed_result, _ = parse_official_document(uploaded_comm_docs[0], uploaded_comm_docs[0].name)
                            else:
                                title_data = {}
                                exclusive_data = {}
                                other_data = {}
                                types_found = []

                                for u_file in uploaded_comm_docs:
                                    p_type, p_res, _ = parse_official_document(u_file, u_file.name)
                                    types_found.append(p_type)
                                    if "표제부" in p_type:
                                        title_data.update(p_res)
                                    elif "전유부" in p_type:
                                        exclusive_data.update(p_res)
                                    else:
                                        other_data.update(p_res)

                                if title_data and exclusive_data:
                                    doc_parsed_result = merge_building_registers(title_data, exclusive_data)
                                    doc_parsed_type = "집합건축물대장 (표제부 + 전유부 통합완료)"
                                elif title_data:
                                    doc_parsed_result = title_data
                                    doc_parsed_type = "집합건축물대장 (표제부)"
                                elif exclusive_data:
                                    doc_parsed_result = exclusive_data
                                    doc_parsed_type = "집합건축물대장 (전유부)"
                                else:
                                    doc_parsed_result = other_data
                                    doc_parsed_type = ", ".join(types_found)

                            st.session_state["last_comm_smart_upload_sig"] = upload_sig
                            if doc_parsed_result:
                                queue_state_update("apply_comm", data=doc_parsed_result, success_msg=f"🎉 [{doc_parsed_type}] 분석 완료! 상가 18대 점검항목과 썸네일에 1초 만에 즉시 반영되었습니다.", target_tab="🏪 ④ 상가 중개대상물 표시 (임차·매매)")
                            else:
                                st.error("⚠️ 업로드하신 PDF 서류에서 텍스트를 읽어오지 못했습니다. 정부24/세움터의 위변조 방지 보안 전자문서인 경우 세 번째 [📋 서류 텍스트 직접 붙여넣기] 탭에 복사해 넣어주세요!")
                    except Exception as e:
                        st.error(f"서류 분석 중 오류가 발생했습니다: {e}")

        with comm_tab_doc_split:
            col_csp_title, col_csp_excl = st.columns(2)
            with col_csp_title:
                st.markdown("""
                <div style="background:#EBF8FF; border:1px solid #90CDF4; border-radius:8px; padding:8px 12px; margin-bottom:8px;">
                    <b>🏢 1. 표제부 (총괄표제부 / 일반건축물대장)</b><br/>
                    <span style="font-size:12px; color:#4A5568;">소재지, 주구조, 용도지역, 층수, 주차, 승강기, 준공일</span>
                </div>
                """, unsafe_allow_html=True)
                up_c_title = st.file_uploader("표제부 PDF", type=["pdf"], key="comm_doc_title_pdf_key")
            with col_csp_excl:
                st.markdown("""
                <div style="background:#FEFCBF; border:1px solid #FAF089; border-radius:8px; padding:8px 12px; margin-bottom:8px;">
                    <b>🚪 2. 전유부 (구분점포 / 개별호실)</b><br/>
                    <span style="font-size:12px; color:#744210;">호실, 전용면적, 해당층, 전유부 용도</span>
                </div>
                """, unsafe_allow_html=True)
                up_c_excl = st.file_uploader("전유부 PDF", type=["pdf"], key="comm_doc_excl_pdf_key")

            if up_c_title or up_c_excl:
                split_sig = f"{getattr(up_c_title, 'name', '')}_{getattr(up_c_excl, 'name', '')}"
                if st.session_state.get("last_comm_split_upload_sig") != split_sig:
                    try:
                        with st.spinner("표제부 및 전유부 융합 분석 중..."):
                            t_data = {}
                            e_data = {}
                            if up_c_title:
                                _, t_data, _ = parse_official_document(up_c_title, up_c_title.name)
                            if up_c_excl:
                                _, e_data, _ = parse_official_document(up_c_excl, up_c_excl.name)

                            if t_data and e_data:
                                res_m = merge_building_registers(t_data, e_data)
                                queue_state_update("apply_comm", data=res_m, success_msg="🎉 표제부와 전유부 2개 서류가 완벽하게 결합되어 상가 항목에 적용되었습니다!", target_tab="🏪 ④ 상가 중개대상물 표시 (임차·매매)")
                            elif t_data:
                                queue_state_update("apply_comm", data=t_data, success_msg="🎉 표제부 분석 완료! 건물 기본 스펙이 상가 항목에 적용되었습니다.", target_tab="🏪 ④ 상가 중개대상물 표시 (임차·매매)")
                            elif e_data:
                                queue_state_update("apply_comm", data=e_data, success_msg="🎉 전유부 분석 완료! 개별 호실 면적이 상가 항목에 적용되었습니다.", target_tab="🏪 ④ 상가 중개대상물 표시 (임차·매매)")

                            st.session_state["last_comm_split_upload_sig"] = split_sig
                    except Exception as e:
                        st.error(f"분리 서류 분석 오류: {e}")

        with comm_tab_doc_txt:
            st.markdown("""
            <div style="font-size:13px; color:#2D3748; background:#FFF5F5; border:1px solid #FEB2B2; padding:10px 14px; border-radius:6px; margin-bottom:10px;">
                💡 <b>정부24 보안문서 해결책:</b> 전자증명서 PDF에 위변조방지 보안이 걸려있는 경우, 
                정부24 열람 화면에서 마우스로 표 전체를 드래그 복사(Ctrl+C)하여 아래에 붙여넣으세요!
            </div>
            """, unsafe_allow_html=True)

            comm_pasted_doc_text = st.text_area(
                "건축물대장 / 토지대장 / 토지이용계획원 복사 텍스트 붙여넣기",
                height=130,
                placeholder="예:\n[표제부]\n대지위치: 부산광역시 사상구 괘법동 560-1\n주구조: 철근콘크리트구조\n지역: 일반상업지역\n지구: 방화지구, 지구단위계획구역\n주용도: 제1종근린생활시설\n사용승인일: 2018.06.15...",
                key="comm_direct_pasted_doc_text"
            )
            if st.button("🚀 붙여넣은 공적서류 텍스트 0.1초 분석 & 상가 항목 즉시 적용", type="primary", use_container_width=True, key="btn_apply_comm_pasted_doc"):
                if comm_pasted_doc_text.strip():
                    doc_type, parsed_dict, _ = parse_single_or_multi_document([comm_pasted_doc_text])
                    if parsed_dict:
                        queue_state_update("apply_comm", data=parsed_dict, success_msg=f"🎉 [{doc_type}] 텍스트 분석 완료! 상가 18대 점검항목과 썸네일에 즉시 반영되었습니다.", target_tab="🏪 ④ 상가 중개대상물 표시 (임차·매매)")
                    else:
                        st.warning("붙여넣은 텍스트에서 상가 건축물대장 정보를 찾지 못했습니다.")
                else:
                    st.warning("공적서류 텍스트를 먼저 붙여넣어 주세요.")

    # 3. 좌우 분할 (입력 / 출력)
    col_cad_in, col_cad_out = st.columns([1.1, 1.2])

    with col_cad_in:
        st.markdown("### 📋 상가 필수 점검항목 입력 및 수정")

        # 01. 소재지
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <b>01. 소재지</b>
            <span class="spec-badge badge-red">동·리·지번 필수</span>
        </div>
        """, unsafe_allow_html=True)
        st.text_input("소재지 주소", key="comm_ad_location")

        # 02. 면적 (전용/계약)
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>02. 면적 (전용 / 계약)</b>
            <span class="spec-badge badge-orange">법정단위 ㎡ 표기 (평수 제외)</span>
        </div>
        """, unsafe_allow_html=True)
        car1, car2 = st.columns(2)
        with car1:
            st.text_input("전용면적 (㎡)", key="comm_ad_area_exclusive")
        with car2:
            st.text_input("계약/연면적 (㎡)", key="comm_ad_area_contract")

        area_calc_m2 = format_commercial_area_text(st.session_state.comm_ad_area_exclusive, st.session_state.comm_ad_area_contract)
        st.markdown(f"""
        <div style="background:#F1F3F5; padding:6px 12px; border-radius:6px; font-size:13px; color:#495057; margin-bottom:8px;">
            📐 <b>계산 결과:</b> {area_calc_m2}
        </div>
        """, unsafe_allow_html=True)

        # 03. 해당층 / 총층수
        st.markdown("<b>03. 해당층 / 총층수</b>", unsafe_allow_html=True)
        st.text_input("해당층 / 총층수", key="comm_ad_floor_info", placeholder="예: 1층 / 지상 5층 (지하 1층)")

        # 04. 화장실 구분 (상가 필수)
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>04. 화장실 구분</b>
            <span class="spec-badge badge-green">상가 특화</span>
        </div>
        """, unsafe_allow_html=True)
        restroom_opts = ["내부 남녀구분 화장실 완비", "내부 단독 화장실", "각 층별 남녀 분리 화장실 (외부 공용)", "외부 공용 화장실"]
        if st.session_state.comm_ad_restroom not in restroom_opts:
            restroom_opts.append(st.session_state.comm_ad_restroom)
        st.selectbox("화장실 구분", restroom_opts, key="comm_ad_restroom")

        # 05. 관리비 & 세부내역
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>05. 관리비 & 세부내역</b>
            <span class="spec-badge badge-red">월 10만원↑ 세부내역 필수</span>
        </div>
        """, unsafe_allow_html=True)
        cmf1, cmf2 = st.columns([1, 1.4])
        with cmf1:
            st.text_input("월 관리비", key="comm_ad_maintenance_fee", placeholder="예: 월 15만 원 또는 자체관리")
        with cmf2:
            st.text_input("세부내역", key="comm_ad_maintenance_detail", placeholder="예: 공용청소, 승강기유지비 등")

        # 06. 거래 형태 & 07. 거래 가격
        st.markdown("<b>06. 거래 형태 & 07. 가격</b>", unsafe_allow_html=True)
        cpr1, cpr2 = st.columns([1, 1.4])
        with cpr1:
            c_trades = ["월세", "전세", "매매"] if not is_comm_ad_sale else ["매매", "월세"]
            if st.session_state.comm_ad_trade_type not in c_trades:
                c_trades.append(st.session_state.comm_ad_trade_type)
            st.selectbox("거래 형태", c_trades, key="comm_ad_trade_type")
        with cpr2:
            st.text_input("거래 가격", key="comm_ad_price_text", placeholder="예: 보증금 3,000만 / 월 180만 또는 15억 원")

        # 08. [임차] 권리금 / [매매] 수익률 & 투자금 분석
        if not is_comm_ad_sale:
            st.markdown("""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
                <b>08. 권리금 유무</b>
                <span class="spec-badge badge-orange">임차 필수</span>
            </div>
            """, unsafe_allow_html=True)
            st.text_input("권리금 정보", key="comm_ad_premium_fee", placeholder="예: 무권리 (권리금 없음) 또는 시설권리금 협의")
        else:
            st.markdown("""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
                <b>08. 수익률 및 투자금 분석</b>
                <span class="spec-badge badge-gold">수익형 매매 핵심</span>
            </div>
            """, unsafe_allow_html=True)
            st.text_input("기임대차 현황 (보증금/월세)", key="comm_ad_deposit_rent_summary", placeholder="예: 보증금 8,000만 원 / 월 650만 원")
            cs_inv1, cs_inv2, cs_inv3 = st.columns(3)
            with cs_inv1:
                st.text_input("융자금(대출)", key="comm_ad_loan_amount", placeholder="예: 6억 원")
            with cs_inv2:
                st.text_input("실투자금", key="comm_ad_actual_investment", placeholder="예: 8억 2,000만 원")
            with cs_inv3:
                st.text_input("연간 수익률", key="comm_ad_yield_rate", placeholder="예: 확정 수익률 연 6.8%")

        # 09. 방향 (주출입구 기준)
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>09. 방향 (주된 출입구 기준)</b>
            <span class="spec-badge badge-green">출입구 기준</span>
        </div>
        """, unsafe_allow_html=True)
        st.text_input("방향", key="comm_ad_direction", placeholder="예: 남서향 (주된 출입구 기준)")

        # 10. 입점(입주)가능일 & 11. 총주차대수
        cmv1, cmv2 = st.columns(2)
        with cmv1:
            st.markdown("<b>10. 입점(입주)가능일</b>", unsafe_allow_html=True)
            st.text_input("입점가능일", key="comm_ad_move_in_date", placeholder="예: 즉시입점 협의가능")
        with cmv2:
            st.markdown("<b>11. 총주차대수</b>", unsafe_allow_html=True)
            st.text_input("총주차대수", key="comm_ad_parking", placeholder="예: 총 20대 (점포 1대 무료)")

        # 12. 현재 업종 & 추천 업종
        st.markdown("<b>12. 현재 및 추천 업종</b>", unsafe_allow_html=True)
        cus1, cus2 = st.columns(2)
        with cus1:
            st.text_input("현재 상태/업종", key="comm_ad_current_use", placeholder="예: 공실 또는 카페 성업중")
        with cus2:
            st.text_input("추천 업종", key="comm_ad_recommended_use", placeholder="예: 카페, 음식점, 베이커리 등")

        # 13. 건축물 법정 용도
        st.markdown("<b>13. 건축물 용도 (법정 주용도)</b>", unsafe_allow_html=True)
        st.text_input("건축물 용도", key="comm_ad_building_use", placeholder="예: 제1종 근린생활시설")

        # 14. 용도지역 & 용도지구 (신소장님 필수 항목)
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>14. 용도지역 및 용도지구</b>
            <span class="spec-badge badge-gold">인허가 핵심</span>
        </div>
        """, unsafe_allow_html=True)
        czn1, czn2 = st.columns(2)
        with czn1:
            st.text_input("용도지역", key="comm_ad_zone_region", placeholder="예: 일반상업지역, 준주거지역 등")
        with czn2:
            st.text_input("용도지구/구역", key="comm_ad_zone_district", placeholder="예: 방화지구, 지구단위계획구역")

        # 15. 주구조 (건축물 주구조)
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>15. 주구조 (건물 구조)</b>
            <span class="spec-badge badge-green">대장 표제부 기준</span>
        </div>
        """, unsafe_allow_html=True)
        st.text_input("주구조", key="comm_ad_structure", placeholder="예: 철근콘크리트구조, 일반철골구조 등")

        # 16. 사용승인일 (준공일) & 17. 주요 설비 및 시설
        cbu1, cbu2 = st.columns(2)
        with cbu1:
            st.markdown("<b>16. 사용승인일 (준공일)</b>", unsafe_allow_html=True)
            st.text_input("사용승인일", key="comm_ad_approval_date", placeholder="예: 2018년 06월 15일")
        with cbu2:
            st.markdown("<b>17. 주요 설비 및 시설</b>", unsafe_allow_html=True)
            st.text_input("시설 정보", key="comm_ad_facility_info", placeholder="예: 전기 15kW 승압, 도시가스, 승강기 완비")

        # 18. 중개사무소 정보
        st.markdown("<b>18. 중개사무소 정보</b>", unsafe_allow_html=True)
        st.checkbox("✅ 중개사무소 정보 포함하기", key="comm_ad_include_office_info")
        if st.session_state.comm_ad_include_office_info:
            cof1, cof2 = st.columns(2)
            with cof1:
                st.text_input("중개사무소 상호", key="comm_ad_office_name")
                st.text_input("대표자 성명", key="comm_ad_office_owner")
                st.text_input("사무소 연락처", key="comm_ad_office_phone")
            with cof2:
                st.text_input("등록번호", key="comm_ad_office_reg_no")
                st.text_input("소재지", key="comm_ad_office_address")

            cas1, cas2 = st.columns(2)
            with cas1:
                st.text_input("소공/담당자 성명", key="comm_ad_assistant_name")
            with cas2:
                st.text_input("담당자 직통 연락처", key="comm_ad_assistant_phone")

    with col_cad_out:
        st.markdown("### 📋 네이버 광고 상가 점검표 (대조용)")
        st.caption("네이버 부동산 상가 매물 등록창을 띄워두고 위에서부터 순서대로 보며 등록하세요.")

        current_comm_spec_data = {
            "comm_mode": "sale" if is_comm_ad_sale else "lease",
            "location": st.session_state.get("comm_ad_location", ""),
            "area_exclusive": st.session_state.get("comm_ad_area_exclusive", ""),
            "area_contract": st.session_state.get("comm_ad_area_contract", ""),
            "floor_info": st.session_state.get("comm_ad_floor_info", ""),
            "restroom": st.session_state.get("comm_ad_restroom", ""),
            "maintenance_fee": st.session_state.get("comm_ad_maintenance_fee", ""),
            "maintenance_detail": st.session_state.get("comm_ad_maintenance_detail", ""),
            "trade_type": st.session_state.get("comm_ad_trade_type", "월세" if not is_comm_ad_sale else "매매"),
            "price_text": st.session_state.get("comm_ad_price_text", ""),
            "premium_fee": st.session_state.get("comm_ad_premium_fee", ""),
            "deposit_rent_summary": st.session_state.get("comm_ad_deposit_rent_summary", ""),
            "loan_amount": st.session_state.get("comm_ad_loan_amount", ""),
            "actual_investment": st.session_state.get("comm_ad_actual_investment", ""),
            "yield_rate": st.session_state.get("comm_ad_yield_rate", ""),
            "direction": st.session_state.get("comm_ad_direction", ""),
            "move_in_date": st.session_state.get("comm_ad_move_in_date", ""),
            "parking": st.session_state.get("comm_ad_parking", ""),
            "current_use": st.session_state.get("comm_ad_current_use", ""),
            "recommended_use": st.session_state.get("comm_ad_recommended_use", ""),
            "building_use": st.session_state.get("comm_ad_building_use", ""),
            "zone_region": st.session_state.get("comm_ad_zone_region", "일반상업지역"),
            "zone_district": st.session_state.get("comm_ad_zone_district", ""),
            "structure": st.session_state.get("comm_ad_structure", "철근콘크리트구조"),
            "approval_date": st.session_state.get("comm_ad_approval_date", ""),
            "facility_info": st.session_state.get("comm_ad_facility_info", ""),
            "office_name": st.session_state.get("comm_ad_office_name", "참좋은공인중개사사무소"),
            "office_owner": st.session_state.get("comm_ad_office_owner", "신제환"),
            "office_reg_no": st.session_state.get("comm_ad_office_reg_no", "제 26530-2026-00009 호"),
            "office_address": st.session_state.get("comm_ad_office_address", "부산광역시 사상구 강선로 9, 1층"),
            "office_phone": st.session_state.get("comm_ad_office_phone", "010-9667-4201"),
            "include_office_info": st.session_state.get("comm_ad_include_office_info", True),
            "assistant_name": st.session_state.get("comm_ad_assistant_name", ""),
            "assistant_phone": st.session_state.get("comm_ad_assistant_phone", ""),
        }

        comm_items_list = get_commercial_spec_table_data(current_comm_spec_data)
        c_rows_html = []
        for it in comm_items_list:
            num_str = f"{it['num']:02d}"
            val_formatted = it['val'].replace('\n', '<br/>')
            row_markup = f'<div style="border-bottom:1px solid #E9ECEF; padding:11px 6px;"><div style="display:flex; justify-content:space-between; margin-bottom:4px;"><span style="font-size:14px; font-weight:700; color:#333D4B;"><span style="color:#DAA844;">[{num_str}]</span> {it["name"]}</span><span style="font-size:12px; color:#8B95A1;">{it["guide"]}</span></div><div style="font-size:15px; color:#191F28; font-weight:600; line-height:1.6; background:#F8F9FB; padding:8px 12px; border-radius:6px; margin-top:4px;">{val_formatted}</div></div>'
            c_rows_html.append(row_markup)

        full_comm_table_html = f'<div style="background:#FFFFFF; border:1.5px solid #CBD5E0; border-radius:12px; padding:14px 18px; box-shadow:0 2px 8px rgba(0,0,0,0.04); max-height:680px; overflow-y:auto;">{"".join(c_rows_html)}</div>'
        st.markdown(full_comm_table_html, unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)
        comm_guide_txt = generate_commercial_naver_ad_guide_text(current_comm_spec_data)
        st.text_area("📋 [네이버 부동산 광고 대조용] 상가 전체 텍스트 복사", value=comm_guide_txt, height=130)

        comm_clip_txt = generate_commercial_clipboard_text(current_comm_spec_data)
        st.text_area("💬 [카카오톡 / 블로그 본문용] 상가 일반 텍스트 복사", value=comm_clip_txt, height=110)

        comm_blog_html = generate_commercial_blog_html_table(current_comm_spec_data)
        st.text_area("📝 [네이버 블로그용] 스마트에디터 다크골드 HTML 표 서식", value=comm_blog_html, height=110)

        # 1080px 고화질 상가 카드 다운로드
        with st.expander("🖼️ [다운로드] 1080px 상가 중개대상물 표시 카드 저장하기", expanded=False):
            with st.spinner("상가 표시 카드 렌더링 중..."):
                comm_card_img = render_commercial_spec_table_image(current_comm_spec_data)
            comm_card_byte_arr = io.BytesIO()
            comm_card_img.save(comm_card_byte_arr, format="PNG", quality=95)
            comm_card_bytes = comm_card_byte_arr.getvalue()

            clean_comm_loc = re.sub(r'[^\w\s-]', '', (st.session_state.comm_ad_location.split(" ")[-1] if st.session_state.comm_ad_location else "상가매물")).strip()
            comm_card_filename = f"상가중개대상물표시_{clean_comm_loc}_{'매매' if is_comm_ad_sale else '임차'}.png"

            st.markdown(render_direct_download_button(comm_card_bytes, comm_card_filename, "💾 [원클릭 즉시 다운로드] 1080px 상가 표시 카드 저장", bg_color="#DAA844"), unsafe_allow_html=True)
            st.caption("스마트폰에서는 위 버튼을 누르시면 사진첩에 바로 다운로드 저장됩니다.")

