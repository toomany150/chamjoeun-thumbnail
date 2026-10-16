import streamlit as st
import io
import os
import re
import base64
import importlib
import thumbnail_generator
import property_ad_spec
import document_parser
importlib.reload(thumbnail_generator)
importlib.reload(property_ad_spec)
importlib.reload(document_parser)
from thumbnail_generator import render_thumbnail
from property_ad_spec import (
    DEFAULT_SPEC,
    SPEC_ITEMS_META,
    format_area_text,
    get_ordered_spec_table_data,
    generate_blog_html_table,
    generate_clipboard_text,
    generate_naver_ad_guide_text,
    render_spec_table_image
)
from document_parser import parse_official_document

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
    
    /* 메인 컨테이너 패딩 */
    .block-container {
        padding-top: 1.2rem;
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
            <div style="text-align: center; margin-top: 25px; color: #ADB5BD; font-size: 13px;">
                🔒 참좋은공인중개사사무소 010-9667-4201<br/>
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
            <p style="margin: 2px 0 0 0; color: #6C757D; font-size: 14px;">
                참좋은공인중개사사무소 (대표 신제환 010-9667-4201) | PC & 스마트폰 모바일 연동
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
with col_h2:
    if st.button("🔒 로그아웃 (비밀번호 잠금)", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ----------------------------------------------------
# 🌟 메인 2대 탭 구성 (1. 썸네일 생성 / 2. 네이버광고 점검표)
# ----------------------------------------------------
tab_thumb, tab_ad = st.tabs([
    "🎨 1단계: 블로그 썸네일 생성기 (1080x1080)",
    "📝 2단계: 네이버 광고 점검표 & 대상중개물 표시"
])

# ====================================================
# [ 탭 1 ] 블로그 썸네일 생성기
# ====================================================
with tab_thumb:
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
                photo_width_ratio = st.slider(
                    "📷 사진 가로 비중 (와이드 조절)",
                    min_value=0.50,
                    max_value=0.76,
                    value=0.68,
                    step=0.02,
                    format="%.0f%%"
                )

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

        st.image(thumbnail_img, caption="실시간 완성 미리보기 (1080 x 1080 px)", use_container_width=True)

    with col_t_right:
        st.markdown("### 🛠️ 썸네일 텍스트 수정")
        st.session_state.item_no = st.text_input("🏷️ 물건 번호", value=st.session_state.item_no)
        st.session_state.main_title = st.text_input("🏢 메인 타이틀 (아파트명)", value=st.session_state.main_title)
        st.session_state.sub_title = st.text_input("📍 서브 타이틀 (동/단지명)", value=st.session_state.sub_title)
        st.session_state.feature_text = st.text_input("✨ 매물 핵심 특징", value=st.session_state.feature_text)
        
        c_tr1, c_tr2 = st.columns([1, 1.3])
        with c_tr1:
            trade_opts = ["매매", "전세", "월세", "분양", "급매"]
            cur_idx = trade_opts.index(st.session_state.thumb_trade_type) if st.session_state.thumb_trade_type in trade_opts else 0
            st.session_state.thumb_trade_type = st.selectbox("거래 형태", trade_opts, index=cur_idx)
        with c_tr2:
            st.session_state.thumb_price_text = st.text_input("금액 (예: 6억2천)", value=st.session_state.thumb_price_text)

        st.markdown("#### 📋 5대 스펙 텍스트")
        st.session_state.spec_line1 = st.text_input("1행: 해당동 / 층수", value=st.session_state.spec_line1)
        st.session_state.spec_line2 = st.text_input("2행: 공급/전용면적", value=st.session_state.spec_line2)
        st.session_state.spec_line3 = st.text_input("3행: 방/욕실 수", value=st.session_state.spec_line3)
        st.session_state.spec_line4 = st.text_input("4행: 입주시기", value=st.session_state.spec_line4)
        st.session_state.spec_line5 = st.text_input("5행: 방향 및 특징", value=st.session_state.spec_line5)

        st.markdown("#### 🏢 하단 띠지 (중개사무소 정보)")
        st.session_state.thumb_show_footer = st.checkbox(
            "하단 띠지 표시 (체크 해제 시 전체 사진 영역 확장)",
            value=st.session_state.thumb_show_footer,
            help="소공 또는 타 중개사 협업 시 띠지 없이 매물 사진만 1080px 꽉 차게 내보낼 수 있습니다."
        )
        if st.session_state.thumb_show_footer:
            st.session_state.thumb_footer_text = st.text_input(
                "띠지 문구 (소공/직원 커스텀 문구 가능)",
                value=st.session_state.thumb_footer_text,
                placeholder="미입력 시: 참좋은공인중개사사무소 (부산 사상구) ☎ 051-313-2288"
            )

        # 썸네일 이미지 다운로드
        img_byte_arr = io.BytesIO()
        thumbnail_img.save(img_byte_arr, format="PNG", quality=98)
        img_bytes = img_byte_arr.getvalue()

        clean_title = re.sub(r'[^\w\s-]', '', (st.session_state.main_title or "매물")).strip().replace(" ", "_")
        clean_price = re.sub(r'[^\w\s-]', '', (st.session_state.thumb_price_text or "")).strip().replace(" ", "")
        download_filename = f"부동산썸네일_{clean_title}_{st.session_state.thumb_trade_type}_{clean_price}.png"

        st.download_button(
            label="📥 1080x1080 썸네일 저장 (기본 다운로드)",
            data=img_bytes,
            file_name=download_filename,
            mime="image/png",
            key="btn_thumb_download_main",
            use_container_width=True
        )

        # 브라우저 네이티브 다이렉트 다운로드 (오류 없는 100% 즉시 저장)
        st.markdown(render_direct_download_button(img_bytes, download_filename, "💾 [즉시 다운로드] 브라우저 원클릭 파일 저장"), unsafe_allow_html=True)
        st.caption("📱 스마트폰에서는 위 이미지를 1초간 길게 누르시면 '사진 앱에 저장'도 가능합니다.")

        st.info("💡 썸네일을 만드셨다면, 상단의 **'2단계: 네이버 광고 점검표'** 탭을 클릭하여 네이버 부동산 광고 및 블로그 본문 서식을 바로 확인하세요!")


# ====================================================
# [ 탭 2 ] 네이버 광고 & 대상중개물 표시 생성기
# (신소장님 지정 16개 순서 완벽 적용)
# ====================================================
with tab_ad:
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

    # ----------------------------------------------------
    # 📄 [공적서류 1초 자동완성] 건축물대장 / 토지대장 / 토지이용계획원
    # ----------------------------------------------------
    with st.expander("📄 [원클릭 1초 자동완성] 건축물대장 / 토지대장 / 토지이용계획원 서류 분석", expanded=True):
        st.markdown("""
        <div style="font-size:14px; color:#2D3748; margin-bottom:10px;">
            정부24, 세움터, 일사편리에서 발급받은 <b>건축물대장(표제부/전유부)</b>, <b>토지대장</b>, <b>토지이용계획원</b> PDF 파일을 올리시면 <b>소재지, 면적, 층수, 용도, 준공일, 주차, 세대수</b>가 16개 항목에 1초 만에 자동 완성됩니다!
        </div>
        """, unsafe_allow_html=True)

        tab_up_pdf, tab_up_txt = st.tabs(["📁 PDF 서류 파일 끌어다 놓기", "📋 서류 텍스트 직접 붙여넣기"])

        doc_parsed_result = None
        doc_parsed_type = ""

        with tab_up_pdf:
            uploaded_doc = st.file_uploader(
                "건축물대장 / 토지대장 / 토지이용계획원 PDF 서류를 드래그하여 놓으세요",
                type=["pdf"],
                help="PDF 형식의 공적 서류를 업로드하시면 실시간 정밀 분석합니다.",
                key="doc_pdf_uploader_key"
            )
            if uploaded_doc is not None:
                try:
                    with st.spinner("공적서류 정밀 분석 중..."):
                        doc_parsed_type, doc_parsed_result, _ = parse_official_document(uploaded_doc, uploaded_doc.name)
                except Exception as e:
                    st.error(f"서류 분석 중 오류가 발생했습니다: {e}")

        with tab_up_txt:
            raw_input_text = st.text_area(
                "인터넷 열람 서류 텍스트를 복사(Ctrl+C)하여 여기에 붙여넣으세요(Ctrl+V)",
                height=130,
                placeholder="예: [표제부] 대지위치: 부산광역시 사상구 덕포동 220, 건축물명칭: 사상 중흥S-클래스, 전유면적: 79.85㎡, 사용승인일: 2023-07-28..."
            )
            if st.button("🔍 붙여넣은 텍스트 분석하기", key="btn_parse_raw_text"):
                if raw_input_text.strip():
                    from document_parser import identify_document_type, parse_building_register, parse_land_register, parse_land_use_plan
                    doc_parsed_type = identify_document_type(raw_input_text)
                    if "건축물대장" in doc_parsed_type:
                        doc_parsed_result = parse_building_register(raw_input_text)
                    elif "토지대장" in doc_parsed_type:
                        doc_parsed_result = parse_land_register(raw_input_text)
                    elif "토지이용계획" in doc_parsed_type:
                        doc_parsed_result = parse_land_use_plan(raw_input_text)
                    else:
                        doc_parsed_result = parse_building_register(raw_input_text)
                        if not doc_parsed_result.get("location"):
                            doc_parsed_result.update(parse_land_register(raw_input_text))

        # 분석 결과 프리뷰 및 자동완성 적용 버튼
        if doc_parsed_result:
            st.success(f"🎉 **{doc_parsed_type}** 서류 분석이 완료되었습니다!")
            
            c_pv1, c_pv2, c_pv3 = st.columns(3)
            with c_pv1:
                st.markdown(f"📍 **소재지**: `{doc_parsed_result.get('location', '미감지')}`")
                st.markdown(f"🏢 **주용도**: `{doc_parsed_result.get('building_use', '미감지')}`")
                st.markdown(f"📅 **사용승인일**: `{doc_parsed_result.get('approval_date', '미감지')}`")
            with c_pv2:
                st.markdown(f"📐 **전용면적**: `{doc_parsed_result.get('area_exclusive', '-')} ㎡`")
                st.markdown(f"📐 **공급/연면적**: `{doc_parsed_result.get('area_supply', '-')} ㎡`")
                st.markdown(f"🏢 **층수정보**: `{doc_parsed_result.get('floor_info', '미감지')}`")
            with c_pv3:
                st.markdown(f"🚗 **주차대수**: `{doc_parsed_result.get('parking', '미감지')}`")
                st.markdown(f"👨‍👩‍👧 **세대수**: `{doc_parsed_result.get('households', '미감지')}`")
                st.markdown(f"🚪 **방/욕실**: `{doc_parsed_result.get('room_bath', '미감지')}`")
                if "zone_info" in doc_parsed_result:
                    st.markdown(f"🌐 **용도지역**: `{doc_parsed_result['zone_info']}`")

            if st.button("⚡ 위 서류 정보를 16대 점검항목 & 썸네일에 1초 즉시 적용하기", type="primary", use_container_width=True, key="btn_apply_doc_info"):
                # 점검항목 적용
                if doc_parsed_result.get("location"):
                    st.session_state.ad_location = doc_parsed_result["location"]
                if doc_parsed_result.get("area_exclusive"):
                    st.session_state.ad_area_exclusive = doc_parsed_result["area_exclusive"]
                if doc_parsed_result.get("area_supply"):
                    st.session_state.ad_area_supply = doc_parsed_result["area_supply"]
                elif doc_parsed_result.get("area_exclusive"):
                    st.session_state.ad_area_supply = doc_parsed_result["area_exclusive"]
                if doc_parsed_result.get("floor_info"):
                    st.session_state.ad_floor_info = doc_parsed_result["floor_info"]
                if doc_parsed_result.get("room_bath"):
                    st.session_state.ad_room_bath = doc_parsed_result["room_bath"]
                if doc_parsed_result.get("building_use"):
                    st.session_state.ad_building_use = doc_parsed_result["building_use"]
                if doc_parsed_result.get("approval_date"):
                    st.session_state.ad_approval_date = doc_parsed_result["approval_date"]
                if doc_parsed_result.get("households"):
                    st.session_state.ad_households = doc_parsed_result["households"]
                if doc_parsed_result.get("parking"):
                    st.session_state.ad_parking = doc_parsed_result["parking"]

                # 썸네일 탭 연동
                if doc_parsed_result.get("main_title"):
                    st.session_state.main_title = doc_parsed_result["main_title"]
                if doc_parsed_result.get("sub_title"):
                    st.session_state.sub_title = doc_parsed_result["sub_title"]
                if doc_parsed_result.get("feature_text"):
                    st.session_state.feature_text = doc_parsed_result["feature_text"]
                if doc_parsed_result.get("floor_info"):
                    st.session_state.spec_line1 = doc_parsed_result["floor_info"]
                if doc_parsed_result.get("area_exclusive"):
                    st.session_state.spec_line2 = f"전용 {doc_parsed_result['area_exclusive']}㎡"
                if doc_parsed_result.get("room_bath"):
                    st.session_state.spec_line3 = doc_parsed_result["room_bath"]

                st.success("✅ 공적서류 정보가 16대 점검항목과 썸네일에 완벽하게 반영되었습니다!")
                st.rerun()

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
        st.session_state.ad_location = st.text_input(
            "소재지 주소",
            value=st.session_state.ad_location,
            help="동·리 및 지번 표기 필수 (아파트 동·호수는 생략 가능)"
        )

        # 2. 공급/전용면적
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>02. 공급 / 전용면적</b>
            <span class="spec-badge badge-orange">㎡ 병기 필수</span>
        </div>
        """, unsafe_allow_html=True)
        c_ar1, c_ar2 = st.columns(2)
        with c_ar1:
            st.session_state.ad_area_supply = st.text_input("공급면적 (㎡)", value=st.session_state.ad_area_supply)
        with c_ar2:
            st.session_state.ad_area_exclusive = st.text_input("전용면적 (㎡)", value=st.session_state.ad_area_exclusive)
        
        # 실시간 평수 및 전용률 환산 프리뷰
        area_sum_m2, area_sum_py = format_area_text(st.session_state.ad_area_supply, st.session_state.ad_area_exclusive)
        st.markdown(f"""
        <div style="background:#F1F3F5; padding:6px 12px; border-radius:6px; font-size:13px; color:#495057; margin-bottom:8px;">
            📐 <b>계산 결과:</b> {area_sum_m2} | <b>{area_sum_py}</b>
        </div>
        """, unsafe_allow_html=True)

        # 3. 해당층 / 총층
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>03. 해당층 / 총층</b>
            <span class="spec-badge badge-green">저/중/고 표기가능</span>
        </div>
        """, unsafe_allow_html=True)
        st.session_state.ad_floor_info = st.text_input(
            "해당층 / 총층",
            value=st.session_state.ad_floor_info,
            help="예: 25 / 36층 (아파트의 경우 의뢰인 요청 시 저/중/고층 대체 가능)"
        )

        # 4. 방수 / 욕실수
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>04. 방수 / 욕실수</b>
            <span class="spec-badge badge-gray">대장 기준</span>
        </div>
        """, unsafe_allow_html=True)
        st.session_state.ad_room_bath = st.text_input(
            "방수 / 욕실수",
            value=st.session_state.ad_room_bath,
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
            st.session_state.ad_maintenance_fee = st.text_input("월 관리비", value=st.session_state.ad_maintenance_fee)
        with c_mf2:
            st.session_state.ad_maintenance_detail = st.text_input("세부내역", value=st.session_state.ad_maintenance_detail, help="공용관리비, 전기/수도 실비 분리 기재")

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
            cur_trade_idx = trade_opts_ad.index(st.session_state.ad_trade_type) if st.session_state.ad_trade_type in trade_opts_ad else 0
            st.session_state.ad_trade_type = st.selectbox("거래 형태", trade_opts_ad, index=cur_trade_idx)
        with c_pr2:
            st.session_state.ad_price_text = st.text_input("거래 가격", value=st.session_state.ad_price_text)
        
        st.session_state.ad_deposit_sub = st.text_input(
            "기보증금 / 월세 승계액",
            value=st.session_state.ad_deposit_sub,
            help="기보증금 또는 월세가 있는 경우 작성 (없으면 '- / -')"
        )

        # 8. 방향
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>08. 방향 (기준 명시)</b>
            <span class="spec-badge badge-green">주실(거실) 기준</span>
        </div>
        """, unsafe_allow_html=True)
        st.session_state.ad_direction = st.text_input("방향", value=st.session_state.ad_direction, help="예: 남동향 (거실 기준)")

        # 9. 현관구조 & 10. 난방
        c_et1, c_et2 = st.columns(2)
        with c_et1:
            st.markdown("<b>09. 현관구조</b>", unsafe_allow_html=True)
            st.session_state.ad_entrance_type = st.selectbox("현관구조", ["계단식", "복도식", "복합식"], index=["계단식", "복도식", "복합식"].index(st.session_state.ad_entrance_type) if st.session_state.ad_entrance_type in ["계단식", "복도식", "복합식"] else 0)
        with c_et2:
            st.markdown("<b>10. 난방(방식/연료)</b>", unsafe_allow_html=True)
            st.session_state.ad_heating = st.text_input("난방방식/연료", value=st.session_state.ad_heating)

        # 11. 입주가능일 & 12. 총주차대수
        c_mv1, c_mv2 = st.columns(2)
        with c_mv1:
            st.markdown("<b>11. 입주가능일</b>", unsafe_allow_html=True)
            st.session_state.ad_move_in_date = st.text_input("입주가능일", value=st.session_state.ad_move_in_date)
        with c_mv2:
            st.markdown("<b>12. 총주차대수</b>", unsafe_allow_html=True)
            st.session_state.ad_parking = st.text_input("총주차대수", value=st.session_state.ad_parking)

        # 13. 해당면적 세대수 & 14. 건축물 용도
        c_hs1, c_hs2 = st.columns(2)
        with c_hs1:
            st.markdown("<b>13. 해당면적 세대수</b>", unsafe_allow_html=True)
            st.session_state.ad_households = st.text_input("해당면적 세대수", value=st.session_state.ad_households)
        with c_hs2:
            st.markdown("<b>14. 건축물 용도</b>", unsafe_allow_html=True)
            st.session_state.ad_building_use = st.text_input("건축물 용도", value=st.session_state.ad_building_use)

        # 15. 사용승인일
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>15. 사용승인일 (준공일)</b>
            <span class="spec-badge badge-red">대장 기준 필수</span>
        </div>
        """, unsafe_allow_html=True)
        st.session_state.ad_approval_date = st.text_input("사용승인일", value=st.session_state.ad_approval_date, help="건축물대장 상 사용승인일 기재 필수")

        # 16. 중개사무소 정보 (ON/OFF 선택 및 소공 지원)
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 15px; margin-bottom: 5px;">
            <b>16. 중개사무소 정보</b>
            <span class="spec-badge badge-green">ON/OFF 선택 가능</span>
        </div>
        """, unsafe_allow_html=True)

        st.session_state.ad_include_office_info = st.checkbox(
            "✅ 중개사무소 정보 포함하기 (텍스트 및 카드 이미지에 반영)",
            value=st.session_state.ad_include_office_info,
            help="체크 해제 시 중개사무소 정보를 제외하고 순수 매물 정보(01~15번 항목)만 출력합니다."
        )

        if st.session_state.ad_include_office_info:
            c_of1, c_of2 = st.columns(2)
            with c_of1:
                st.session_state.ad_office_name = st.text_input("중개사무소 명칭 (상호)", value=st.session_state.ad_office_name)
                st.session_state.ad_office_owner = st.text_input("대표 공인중개사 성명", value=st.session_state.ad_office_owner)
                st.session_state.ad_office_phone = st.text_input("사무실 연락처", value=st.session_state.ad_office_phone)
            with c_of2:
                st.session_state.ad_office_reg_no = st.text_input("중개등록번호", value=st.session_state.ad_office_reg_no)
                st.session_state.ad_office_address = st.text_input("사무소 소재지", value=st.session_state.ad_office_address)

            st.markdown("<b>👤 소속공인중개사(소공) 담당자 정보 (선택 입력)</b>", unsafe_allow_html=True)
            c_as1, c_as2 = st.columns(2)
            with c_as1:
                st.session_state.ad_assistant_name = st.text_input("소공/담당자 성명", value=st.session_state.ad_assistant_name, placeholder="예: 김소공 소속공인중개사")
            with c_as2:
                st.session_state.ad_assistant_phone = st.text_input("담당자 직통 연락처", value=st.session_state.ad_assistant_phone, placeholder="예: 010-1234-5678")
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
