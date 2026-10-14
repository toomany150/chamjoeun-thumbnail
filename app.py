import streamlit as st
import io
import os
import importlib
import thumbnail_generator
importlib.reload(thumbnail_generator)
from thumbnail_generator import render_thumbnail

# 페이지 설정
st.set_page_config(
    page_title="부동산 블로그 썸네일 자동 생성기",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세련된 커스텀 CSS 적용 & Deploy 버튼 숨기기
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
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
    }
    
    /* Deploy 버튼 및 불필요한 클라우드 메뉴 숨기기 */
    .stAppDeployButton, [data-testid="stAppDeployButton"], [data-testid="manage-app-button"] {
        display: none !important;
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
    
    /* 고정 요소 안내 띠 */
    .fixed-footer-banner {
        background: #232529;
        color: #FFFFFF;
        border-radius: 10px;
        padding: 12px 18px;
        font-size: 14px;
        font-weight: 500;
        display: flex;
        align-items: center;
        gap: 10px;
        margin-top: 15px;
    }
    
    /* 다운로드 버튼 강조 */
    .stDownloadButton > button {
        background-color: #F48A26 !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 14px 28px !important;
        font-size: 17px !important;
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
    
    /* 로그인 카드 스타일 */
    .login-box {
        max-width: 440px;
        margin: 50px auto;
        padding: 35px 30px;
        background: #FFFFFF;
        border: 1px solid #E5E8EB;
        border-radius: 18px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.06);
        text-align: center;
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
                <h4 style="margin: 0; color: #F48A26; font-weight: 700;">부동산 썸네일 자동 생성기</h4>
                <p style="color: #6C757D; font-size: 14px; margin-top: 8px;">
                    보안 접속을 위해 설정된 비밀번호를 입력해주세요.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("login_form"):
                input_pw = st.text_input(
                    "접근 비밀번호 입력",
                    type="password",
                    placeholder="비밀번호 입력",
                    help="설정된 접근 비밀번호를 입력해주세요."
                )
                submit_btn = st.form_submit_button("🔓 로그인하여 시작하기", use_container_width=True)
                
                if submit_btn:
                    if input_pw.strip() in VALID_PASSWORDS:
                        st.session_state.authenticated = True
                        st.success("✅ 인증되었습니다! 썸네일 생성기로 이동합니다.")
                        st.rerun()
                    else:
                        st.error("비밀번호가 틀렸습니다.")
            
            st.markdown("""
            <div style="text-align: center; margin-top: 25px; color: #ADB5BD; font-size: 13px;">
                🔒 참좋은공인중개사사무소 010-9667-4201<br/>
                24시간 상시 웹 서비스 보안 시스템
            </div>
            """, unsafe_allow_html=True)
    st.stop()


# ----------------------------------------------------
# 썸네일 생성기 메인 앱 (인증 완료 시 렌더링)
# ----------------------------------------------------

# 세션 상태 초기화
if "item_no" not in st.session_state:
    st.session_state.item_no = "No. APT001"
if "main_title" not in st.session_state:
    st.session_state.main_title = "사상 중흥S-클래스"
if "sub_title" not in st.session_state:
    st.session_state.sub_title = "그랜드센트럴"
if "feature_text" not in st.session_state:
    st.session_state.feature_text = "1572세대 대단지 아파트"
if "trade_type" not in st.session_state:
    st.session_state.trade_type = "매매"
if "price_text" not in st.session_state:
    st.session_state.price_text = "6억2천"
if "spec_line1" not in st.session_state:
    st.session_state.spec_line1 = "12월이사예정(협의)"
if "spec_line2" not in st.session_state:
    st.session_state.spec_line2 = "공급 111㎡ / 전용 79.85㎡"
if "spec_line3" not in st.session_state:
    st.session_state.spec_line3 = "방 3 / 욕실 2"
if "spec_line4" not in st.session_state:
    st.session_state.spec_line4 = "남동향 (채광 우수)"

# 프리셋 적용 함수
def apply_preset(p_type):
    if p_type == "living":
        st.session_state.item_no = "No. APT001"
        st.session_state.main_title = "사상 중흥S-클래스"
        st.session_state.sub_title = "그랜드센트럴"
        st.session_state.feature_text = "1572세대 대단지 아파트"
        st.session_state.trade_type = "매매"
        st.session_state.price_text = "6억2천"
        st.session_state.spec_line1 = "12월이사예정(협의)"
        st.session_state.spec_line2 = "공급 111㎡ / 전용 79.85㎡"
        st.session_state.spec_line3 = "방 3 / 욕실 2"
        st.session_state.spec_line4 = "남동향 (채광 우수)"
    elif p_type == "op":
        st.session_state.item_no = "No. OP-302"
        st.session_state.main_title = "해운대 센텀스퀘어"
        st.session_state.sub_title = "하이엔드 오피스텔"
        st.session_state.feature_text = "초역세권 + 풀옵션 프리미엄"
        st.session_state.trade_type = "전세"
        st.session_state.price_text = "2억 4천"
        st.session_state.spec_line1 = "협의 입주 가능"
        st.session_state.spec_line2 = "계약 68㎡ / 전용 42㎡"
        st.session_state.spec_line3 = "방 1.5룸 / 욕실 1"
        st.session_state.spec_line4 = "동향 (시티뷰 조망)"
    elif p_type == "urgent":
        st.session_state.item_no = "No. SALE-77"
        st.session_state.main_title = "광안리 바다뷰 신축"
        st.session_state.sub_title = "로얄층 특가 매물"
        st.session_state.feature_text = "시세 대비 5천 저렴 급매"
        st.session_state.trade_type = "급매"
        st.session_state.price_text = "4억 9천"
        st.session_state.spec_line1 = "즉시 입주 가능"
        st.session_state.spec_line2 = "공급 112㎡ / 전용 84㎡"
        st.session_state.spec_line3 = "방 4 / 욕실 2"
        st.session_state.spec_line4 = "남동향 (파노라마 오션뷰)"

# -------------------------
# 사이드바: 입력 제어판
# -------------------------
with st.sidebar:
    st.markdown("### 🛠️ 썸네일 설정 & 입력")
    
    # 보안 접속 안내 및 로그아웃
    col_sb1, col_sb2 = st.columns([1.5, 1])
    with col_sb1:
        st.caption("🟢 접속 인증됨 (PW: 4989)")
    with col_sb2:
        if st.button("🔒 로그아웃", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    # ⚡ 빠른 템플릿 프리셋
    with st.expander("⚡ 원클릭 예시 템플릿 불러오기", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("거실/아파트", use_container_width=True):
                apply_preset("living")
                st.rerun()
        with c2:
            if st.button("오피스텔", use_container_width=True):
                apply_preset("op")
                st.rerun()
        with c3:
            if st.button("특가 급매", use_container_width=True):
                apply_preset("urgent")
                st.rerun()

    # 0. 레이아웃 스타일 선택 (와이드 기능 핵심)
    st.markdown("#### 📐 1. 레이아웃 & 사진 와이드 설정")
    layout_options = {
        "와이드 사선형 (⭐ 거실/실내 추천)": "side_wide",
        "상하 파노라마형 (가로 100% 전경 극대화)": "top_panoramic",
        "표준 사선형 (시안 기본 5:5 - 외관용)": "side_standard",
    }
    selected_layout_label = st.radio(
        "레이아웃 모드",
        options=list(layout_options.keys()),
        index=0,
        help="거실이나 방 등 가로로 넓은 실내 사진은 '와이드 사선형'이나 '상하 파노라마형'을 선택하시면 사진 전경이 시원하게 잘 보입니다."
    )
    layout_mode = layout_options[selected_layout_label]

    # 와이드 사선형일 때 사진 비중 미세 조절 슬라이더
    photo_width_ratio = 0.68
    if layout_mode == "side_wide":
        photo_width_ratio = st.slider(
            "📷 사진 가로 비중 (와이드 조절)",
            min_value=0.50,
            max_value=0.76,
            value=0.68,
            step=0.02,
            format="%.0f%%",
            help="슬라이더를 올릴수록 사진이 더 넓게 노출되고 좌측 텍스트 영역이 슬림해집니다."
        )

    st.markdown("---")

    # 1. 배경 이미지 업로드
    st.markdown("#### 📸 2. 현장 사진 업로드")
    uploaded_bg = st.file_uploader(
        "거실/건물 사진 업로드 (JPG, PNG, WEBP)",
        type=["jpg", "jpeg", "png", "webp"],
        help="스마트폰으로 현장에서 찍은 사진을 바로 업로드할 수 있습니다."
    )
    
    # 배경 위치 및 줌 조정
    with st.expander("🔍 사진 위치/확대 미세 조정", expanded=False):
        bg_zoom = st.slider("사진 확대/축소", min_value=0.6, max_value=2.0, value=1.0, step=0.05)
        bg_offset_x = st.slider("사진 좌우 이동 (px)", min_value=-450, max_value=450, value=0, step=10, help="사진의 중심을 좌우로 이동하여 보여주고 싶은 부분을 맞춥니다.")
        bg_offset_y = st.slider("사진 상하 이동 (px)", min_value=-450, max_value=450, value=0, step=10)

    st.markdown("---")
    
    # 2. 물건 번호
    st.markdown("#### 🏷️ 3. 물건 번호 (좌측 상단 띠지)")
    item_no = st.text_input("물건 번호 텍스트", value=st.session_state.item_no)

    # 3. 타이틀 영역
    st.markdown("#### 🏢 4. 매물 타이틀 정보")
    main_title = st.text_input("메인 타이틀", value=st.session_state.main_title)
    sub_title = st.text_input("서브 타이틀", value=st.session_state.sub_title)
    feature_text = st.text_input("매물 특징", value=st.session_state.feature_text)

    # 4. 거래 유형 및 금액
    st.markdown("#### 💰 5. 거래 유형 & 금액")
    col_t1, col_t2 = st.columns([1, 1.3])
    with col_t1:
        trade_type_options = ["매매", "전세", "월세", "분양", "급매", "직접입력"]
        default_index = trade_type_options.index(st.session_state.trade_type) if st.session_state.trade_type in trade_type_options else 5
        selected_trade = st.selectbox("거래 유형", trade_type_options, index=default_index)
        if selected_trade == "직접입력":
            trade_type = st.text_input("거래유형 직접입력", value="매매")
        else:
            trade_type = selected_trade
    with col_t2:
        price_text = st.text_input("금액 텍스트", value=st.session_state.price_text)

    # 5. 매물 스펙 4줄
    st.markdown("#### 📋 6. 매물 상세 스펙 (4개 항목)")
    spec_line1 = st.text_input("🕒 1행 (입주시기)", value=st.session_state.spec_line1)
    spec_line2 = st.text_input("🏢 2행 (공급/전용면적)", value=st.session_state.spec_line2)
    spec_line3 = st.text_input("🛏️ 3행 (방/욕실 수)", value=st.session_state.spec_line3)
    spec_line4 = st.text_input("🔆 4행 (방향 및 특징)", value=st.session_state.spec_line4)

    st.markdown("---")
    st.markdown("""
    <div class="fixed-footer-banner">
        🔒 <b>하단 고정 바:</b><br/>
        [로고] 참좋은공인중개사사무소 010-9667-4201
    </div>
    """, unsafe_allow_html=True)


# -------------------------
# 메인 뷰: 실시간 미리보기 및 다운로드
# -------------------------
col_main_left, col_main_right = st.columns([1.3, 0.7])

with col_main_left:
    st.markdown("## 🏢 부동산 썸네일 자동 생성기")
    
    current_mode_desc = "와이드 사선 분할 (사진 약 68% 노출)" if layout_mode == "side_wide" else ("상하 파노라마 (사진 가로 100% 노출)" if layout_mode == "top_panoramic" else "표준 사선 분할 (5:5)")
    st.markdown(f"""
    <span class="spec-badge badge-orange">1080 x 1080 (1:1 정방형 규격)</span>
    <span class="spec-badge badge-orange">{current_mode_desc}</span>
    <span class="spec-badge badge-gray">네이버 블로그 / 스마트플레이스 최적화</span>
    """, unsafe_allow_html=True)

    spec_lines = [spec_line1, spec_line2, spec_line3, spec_line4]
    
    with st.spinner("고화질 썸네일 렌더링 중..."):
        thumbnail_img = render_thumbnail(
            bg_image=uploaded_bg,
            item_no=item_no,
            main_title=main_title,
            sub_title=sub_title,
            feature_text=feature_text,
            trade_type=trade_type,
            price_text=price_text,
            spec_lines=spec_lines,
            layout_mode=layout_mode,
            photo_width_ratio=photo_width_ratio,
            bg_offset_x=bg_offset_x,
            bg_offset_y=bg_offset_y,
            bg_zoom=bg_zoom
        )

    # 썸네일 실시간 프리뷰
    st.image(thumbnail_img, caption="실시간 완성 미리보기 (1080 x 1080 px)", use_container_width=True)

with col_main_right:
    st.markdown("### 💾 파일 저장 및 활용")
    
    # 이미지 바이트 변환
    img_byte_arr = io.BytesIO()
    thumbnail_img.save(img_byte_arr, format="PNG", quality=98)
    img_bytes = img_byte_arr.getvalue()

    # 다운로드 파일명 자동 생성
    clean_title_slug = (main_title or "매물").replace(" ", "_").replace("/", "-")
    clean_price_slug = (price_text or "").replace(" ", "").replace("/", "-")
    download_filename = f"부동산썸네일_{clean_title_slug}_{trade_type}_{clean_price_slug}.png"

    # 다운로드 버튼 (스마트폰에서도 터치 즉시 갤러리/다운로드 폴더에 저장)
    st.download_button(
        label="📥 1080x1080 썸네일 저장 (모바일 다운로드)",
        data=img_bytes,
        file_name=download_filename,
        mime="image/png",
        use_container_width=True
    )

    st.markdown("<br/>", unsafe_allow_html=True)
    
    # 편의 기능: 블로그 포스팅용 텍스트 복사 카드
    with st.container():
        st.markdown("#### 📝 블로그 본문용 요약 텍스트")
        st.caption("블로그 글 작성 시 아래 텍스트를 바로 복사하여 본문에 붙여넣을 수 있습니다.")
        
        blog_summary = f"""[ {item_no} ] {main_title} {sub_title} ({trade_type} {price_text})

■ 매물명: {main_title} {sub_title}
■ 특징: {feature_text}
■ 거래형태: {trade_type} {price_text}
■ 입주시기: {spec_line1}
■ 전용/공급면적: {spec_line2}
■ 구조: {spec_line3}
■ 방향: {spec_line4}

■ 중개사무소: 참좋은공인중개사사무소
■ 대표번호: 010-9667-4201"""

        st.text_area("클릭 후 복사 (Ctrl+C)", value=blog_summary, height=220)

    # 사양 및 가이드 카드
    with st.expander("💡 스마트폰 임장 팁", expanded=True):
        st.markdown("""
        - **스마트폰 촬영 사진**: 현장에서 폰으로 거실/방 사진 찍고 바로 사이드바에서 업로드 가능!
        - **비밀번호**: 외부 접속 시 **`4989`** (사고팔고)를 입력하시면 안전하게 로그인됩니다.
        - **저장**: 다운로드 버튼을 누르면 스마트폰 사진 보관함(갤러리) 또는 다운로드 폴더에 즉시 저장됩니다.
        """)
