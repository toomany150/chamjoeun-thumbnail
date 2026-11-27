"""
매물 보관함 관리 모듈 (storage_manager.py)
- 형식: 작성일자_매물번호_매물종류.json (예: 20261126_2664012103_아파트.json)
- 보관 대상:
  1) 썸네일 설정 및 제원 데이터 (Thumbnail)
  2) 창문부착용 A4 포스터 데이터 (Poster A4)
  3) 중개대상물 인터넷 표시·광고 16대/18대 필수 점검항목 데이터 (Property Ad Spec)
  4) 부가정보: 저장일시, 매물상태(진행중/거래완료/보류), 메모
- 기능:
  - 신규 매물 보관 / 업데이트
  - 보관 매물 목록 조회 및 검색
  - 매물 불러오기 (데이터 복원 딕셔너리 생성)
  - 매물 삭제
  - ZIP 백업 다운로드 및 복원 업로드 (Streamlit Cloud 환경 대응)
"""

import os
import io
import re
import json
import zipfile
import datetime
from typing import Dict, Any, List, Tuple, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORAGE_DIR = os.path.join(BASE_DIR, "saved_records")

# 매물 종류 영문 -> 한글 라벨 매핑
PROP_TYPE_LABELS = {
    "apt": "아파트",
    "house": "주택",
    "comm": "상가",
    "factory": "공장"
}

PROP_LABEL_TO_TYPE = {
    "아파트": "apt",
    "오피스텔": "apt",
    "주택": "house",
    "상가": "comm",
    "공장": "factory",
    "토지": "factory"
}


def ensure_storage_dir():
    """보관함 폴더가 없으면 자동 생성합니다."""
    if not os.path.exists(STORAGE_DIR):
        os.makedirs(STORAGE_DIR, exist_ok=True)


def sanitize_filename_part(text: str) -> str:
    """윈도우 파일명에 사용 불가능한 특수문자를 안전하게 제거/치환합니다."""
    if not text:
        return "미지정"
    # / \ : * ? " < > | 제거
    cleaned = re.sub(r'[\/\\:\*\?"<>\|\s]+', '_', str(text).strip())
    cleaned = re.sub(r'_+', '_', cleaned).strip('_')
    return cleaned if cleaned else "미지정"


def generate_listing_filename(item_no: str, prop_type: str, date_str: str = None) -> str:
    """
    [매물종류_매물번호_저장날짜.json] 규칙에 따른 표준 파일명을 생성합니다.
    예: 아파트_2664012103_20261127.json
    """
    if not date_str:
        date_str = datetime.datetime.now().strftime("%Y%m%d")
    else:
        # YYYY-MM-DD 등을 YYYYMMDD로 정규화
        date_str = re.sub(r'\D', '', date_str)[:8]
        if len(date_str) < 8:
            date_str = datetime.datetime.now().strftime("%Y%m%d")

    clean_no = sanitize_filename_part(item_no if item_no else "001")
    type_label = PROP_TYPE_LABELS.get(prop_type, prop_type)
    clean_type = sanitize_filename_part(type_label)

    return f"{clean_type}_{clean_no}_{date_str}.json"


def save_listing_record(
    item_no: str,
    prop_type: str,
    thumbnail_data: Dict[str, Any],
    poster_data: Dict[str, Any],
    ad_spec_data: Dict[str, Any],
    status: str = "진행중",
    memo: str = "",
    custom_date_str: str = None,
    overwrite_filename: str = None
) -> Tuple[bool, str, str]:
    """
    매물 1건의 [썸네일, 창문부착용, 중개대상물 정보]를 JSON 파일로 보관합니다.
    - 반환: (성공여부: bool, 안내메시지: str, 파일명: str)
    """
    ensure_storage_dir()

    now_dt = datetime.datetime.now()
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    if overwrite_filename and overwrite_filename.endswith(".json"):
        filename = overwrite_filename
    else:
        filename = generate_listing_filename(item_no, prop_type, custom_date_str)

    filepath = os.path.join(STORAGE_DIR, filename)

    # 요약 정보 추출 (목록에서 빠르게 표시하기 위함)
    main_title = (
        thumbnail_data.get("main_title") or 
        poster_data.get("main_title") or 
        poster_data.get("poster_apt_main_title") or 
        poster_data.get("poster_comm_l_title") or 
        ad_spec_data.get("location") or 
        "매물"
    )
    price_text = (
        thumbnail_data.get("thumb_price_text") or 
        ad_spec_data.get("price_text") or 
        poster_data.get("price") or 
        poster_data.get("poster_apt_price") or 
        poster_data.get("poster_comm_l_price") or 
        ""
    )
    location = (
        ad_spec_data.get("location") or 
        ad_spec_data.get("ad_location") or 
        ad_spec_data.get("comm_ad_location") or 
        thumbnail_data.get("location") or 
        ""
    )

    type_label = PROP_TYPE_LABELS.get(prop_type, prop_type)

    record_payload = {
        "version": "1.0",
        "file_id": filename.replace(".json", ""),
        "filename": filename,
        "saved_at": now_str,
        "item_no": str(item_no or ""),
        "prop_type": prop_type,
        "prop_type_label": type_label,
        "status": status,
        "memo": memo,
        "summary": {
            "main_title": str(main_title),
            "price_text": str(price_text),
            "location": str(location),
            "trade_type": str(ad_spec_data.get("trade_type") or ad_spec_data.get("ad_trade_type") or thumbnail_data.get("thumb_trade_type") or "매매")
        },
        "thumbnail_data": thumbnail_data or {},
        "poster_data": poster_data or {},
        "ad_spec_data": ad_spec_data or {}
    }

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(record_payload, f, ensure_ascii=False, indent=2)
        return True, f"매물 [{filename}] 보관 완료!", filename
    except Exception as e:
        return False, f"매물 저장 실패: {e}", ""


def list_saved_listings() -> List[Dict[str, Any]]:
    """
    보관된 매물 전체 목록을 최신 수정일순으로 정렬하여 반환합니다.
    """
    ensure_storage_dir()
    records = []

    try:
        filenames = [f for f in os.listdir(STORAGE_DIR) if f.endswith(".json")]
    except Exception:
        return []

    for fn in filenames:
        fp = os.path.join(STORAGE_DIR, fn)
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 파일 기본 메타 보강
            summary = data.get("summary", {})
            mtime = os.path.getmtime(fp)
            mtime_str = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")

            records.append({
                "filename": fn,
                "file_id": fn.replace(".json", ""),
                "item_no": data.get("item_no", ""),
                "prop_type": data.get("prop_type", "apt"),
                "prop_type_label": data.get("prop_type_label", "아파트"),
                "status": data.get("status", "진행중"),
                "memo": data.get("memo", ""),
                "saved_at": data.get("saved_at", mtime_str),
                "mtime": mtime,
                "main_title": summary.get("main_title", fn),
                "price_text": summary.get("price_text", ""),
                "location": summary.get("location", ""),
                "trade_type": summary.get("trade_type", "매매")
            })
        except Exception:
            continue

    # 최신 저장순으로 정렬
    records.sort(key=lambda x: x["mtime"], reverse=True)
    return records


def load_listing_record(filename: str) -> Optional[Dict[str, Any]]:
    """
    지정된 파일명의 매물 전체 데이터를 읽어옵니다.
    """
    ensure_storage_dir()
    fp = os.path.join(STORAGE_DIR, filename)
    if not os.path.exists(fp):
        return None

    try:
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def delete_listing_record(filename: str) -> Tuple[bool, str]:
    """
    보관된 매물 파일을 안전하게 삭제합니다.
    """
    ensure_storage_dir()
    fp = os.path.join(STORAGE_DIR, filename)
    if not os.path.exists(fp):
        return False, "삭제할 파일이 존재하지 않습니다."

    try:
        os.remove(fp)
        return True, f"매물 [{filename}] 삭제 완료!"
    except Exception as e:
        return False, f"삭제 실패: {e}"


def update_listing_status(filename: str, new_status: str) -> bool:
    """
    매물 상태(진행중 / 거래완료 / 보류)를 업데이트합니다.
    """
    data = load_listing_record(filename)
    if not data:
        return False
    data["status"] = new_status
    fp = os.path.join(STORAGE_DIR, filename)
    try:
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def create_backup_zip_bytes() -> bytes:
    """
    보관함의 모든 JSON 파일을 하나의 ZIP 압축 바이너리로 내보냅니다. (클라우드 백업용)
    """
    ensure_storage_dir()
    mem_zip = io.BytesIO()

    with zipfile.ZipFile(mem_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for fn in os.listdir(STORAGE_DIR):
            if fn.endswith(".json"):
                fp = os.path.join(STORAGE_DIR, fn)
                zf.write(fp, arcname=fn)

    mem_zip.seek(0)
    return mem_zip.getvalue()


def restore_from_zip_or_json(file_bytes: bytes, filename: str) -> Tuple[int, str]:
    """
    업로드된 ZIP 또는 JSON 파일로부터 보관함을 복원합니다.
    - 반환: (복원된 매물 개수, 안내메시지)
    """
    ensure_storage_dir()
    restored_count = 0

    if filename.endswith(".zip"):
        try:
            mem_zip = io.BytesIO(file_bytes)
            with zipfile.ZipFile(mem_zip, "r") as zf:
                for member in zf.namelist():
                    if member.endswith(".json") and not member.startswith("__MACOSX"):
                        extracted_bytes = zf.read(member)
                        # JSON 형식 유효성 검증
                        try:
                            parsed = json.loads(extracted_bytes.decode("utf-8"))
                            target_name = os.path.basename(member)
                            target_path = os.path.join(STORAGE_DIR, target_name)
                            with open(target_path, "w", encoding="utf-8") as f:
                                json.dump(parsed, f, ensure_ascii=False, indent=2)
                            restored_count += 1
                        except Exception:
                            continue
            return restored_count, f"ZIP 백업 파일에서 {restored_count}개의 매물이 성공적으로 복원되었습니다."
        except Exception as e:
            return 0, f"ZIP 파일 해제 중 오류 발생: {e}"

    elif filename.endswith(".json"):
        try:
            parsed = json.loads(file_bytes.decode("utf-8"))
            target_name = os.path.basename(filename)
            target_path = os.path.join(STORAGE_DIR, target_name)
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)
            return 1, f"매물 파일 [{target_name}] 1건이 성공적으로 복원되었습니다."
        except Exception as e:
            return 0, f"JSON 파일 복원 중 오류 발생: {e}"

    return 0, "지원하지 않는 파일 형식입니다. (.json 또는 .zip 파일만 지원)"


def collect_current_session_data(prop_type: str, session_state: Any) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], str]:
    """
    현재 Streamlit 세션에서 [썸네일, 창문부착용, 중개대상물 정보]를 일괄 수집합니다.
    - 반환: (thumbnail_data, poster_data, ad_spec_data, item_no)
    """
    thumb_data = {}
    poster_data = {}
    ad_data = {}
    item_no = ""

    def _val(k, default=""):
        v = session_state.get(k, default)
        return str(v) if v is not None else ""

    # 1. 아파트
    if prop_type == "apt":
        item_no = _val("item_no") or _val("poster_apt_item_no") or "001"
        for k in [
            "item_no", "main_title", "sub_title", "feature_text", "thumb_trade_type", 
            "thumb_price_text", "spec_line1", "spec_line2", "spec_line3", "spec_line4", "spec_line5",
            "apt_thumb_layout_selector", "apt_thumb_design_selector"
        ]:
            if k in session_state: thumb_data[k] = session_state[k]

        for k in [
            "poster_apt_item_no", "poster_apt_main_title", "poster_apt_sub_title", 
            "poster_apt_trade_type", "poster_apt_price", "poster_apt_feature", 
            "poster_apt_office_tel", "poster_apt_custom_contact"
        ]:
            if k in session_state: poster_data[k] = session_state[k]

        for k in [
            "ad_location", "ad_area_supply", "ad_area_exclusive", "ad_floor_info", 
            "ad_floor_type", "ad_room_bath", "ad_maintenance_fee", "ad_maintenance_detail", 
            "ad_trade_type", "ad_price_text", "ad_deposit_sub", "ad_direction", 
            "ad_entrance_type", "ad_heating", "ad_move_in_date", "ad_parking", 
            "ad_households", "ad_building_use", "ad_approval_date", "ad_assistant_name", "ad_assistant_phone"
        ]:
            if k in session_state: ad_data[k] = session_state[k]

    # 2. 상가
    elif prop_type == "comm":
        item_no = _val("comm_item_no") or _val("poster_comm_item_no") or _val("comm_ad_item_no") or "HD01"
        for k in [
            "comm_lease_main_title", "comm_lease_top_badge", "comm_lease_spec1", "comm_lease_spec2",
            "comm_sale_top_left", "comm_sale_main_sub", "comm_sale_price_spec"
        ]:
            if k in session_state: thumb_data[k] = session_state[k]

        for k in [
            "poster_comm_l_title", "poster_comm_l_sub", "poster_comm_l_price", "poster_comm_l_feat",
            "poster_comm_s_title", "poster_comm_s_sub", "poster_comm_s_price",
            "poster_comm_card_floor", "poster_comm_card_area", "poster_comm_card_recom", "poster_comm_card_dir",
            "poster_comm_office_tel", "poster_comm_custom_contact"
        ]:
            if k in session_state: poster_data[k] = session_state[k]

        for k in [
            "comm_ad_location", "comm_ad_area_contract", "comm_ad_area_exclusive", "comm_ad_floor_info",
            "comm_ad_building_use", "comm_ad_zone_region", "comm_ad_zone_district", "comm_ad_structure",
            "comm_ad_approval_date", "comm_ad_parking", "comm_ad_trade_type", "comm_ad_price_text",
            "comm_ad_premium_fee", "comm_ad_direction", "comm_ad_move_in_date", "comm_ad_maintenance_fee",
            "comm_ad_maintenance_detail", "comm_ad_restroom", "comm_ad_current_use", "comm_ad_recommended_use",
            "comm_ad_facility_info", "comm_ad_loan_amount", "comm_ad_actual_investment", "comm_ad_yield_rate",
            "comm_ad_deposit_rent_summary", "comm_ad_assistant_name", "comm_ad_assistant_phone"
        ]:
            if k in session_state: ad_data[k] = session_state[k]

    # 3. 주택
    elif prop_type == "house":
        item_no = _val("house_item_no") or _val("poster_house_item_no") or "H01"
        for k in [
            "house_item_no", "house_main_title", "house_sub_title", "house_trade_type",
            "house_price_text", "house_feature_text", "house_spec1", "house_spec2", "house_spec3",
            "house_spec4", "house_spec5", "house_thumb_design_selector", "house_deal_done", "house_deal_color"
        ]:
            if k in session_state: thumb_data[k] = session_state[k]

        for k in [
            "poster_house_item_no", "poster_house_main_title", "poster_house_sub_title",
            "poster_house_trade_type", "poster_house_price", "poster_house_feature",
            "poster_house_office_tel", "house_custom_contact_text"
        ]:
            if k in session_state: poster_data[k] = session_state[k]

        for k in [
            "house_ad_location", "house_ad_area_land", "house_ad_area_gross", "house_ad_floor_info",
            "house_ad_room_bath", "house_ad_direction", "house_ad_heating", "house_ad_parking",
            "house_ad_move_in_date", "house_ad_approval_date", "house_ad_building_use",
            "house_ad_maintenance_fee", "house_ad_price_text", "house_ad_trade_type"
        ]:
            if k in session_state: ad_data[k] = session_state[k]

    # 4. 공장
    elif prop_type == "factory":
        item_no = _val("factory_item_no") or _val("poster_factory_item_no") or "F01"
        for k in [
            "factory_item_no", "factory_main_title", "factory_sub_title", "factory_trade_type",
            "factory_price_text", "factory_feature_text", "factory_spec1", "factory_spec2", "factory_spec3",
            "factory_spec4", "factory_spec5", "factory_thumb_design_selector", "factory_deal_done", "factory_deal_color"
        ]:
            if k in session_state: thumb_data[k] = session_state[k]

        for k in [
            "poster_factory_item_no", "poster_factory_main_title", "poster_factory_sub_title",
            "poster_factory_trade_type", "poster_factory_price", "poster_factory_feature",
            "poster_factory_office_tel", "factory_custom_contact_text"
        ]:
            if k in session_state: poster_data[k] = session_state[k]

        for k in [
            "factory_ad_location", "factory_ad_area_land", "factory_ad_area_gross", "factory_ad_zoning",
            "factory_ad_building_use", "factory_ad_height", "factory_ad_hoist", "factory_ad_power",
            "factory_ad_direction", "factory_ad_parking", "factory_ad_move_in_date", "factory_ad_approval_date",
            "factory_ad_trade_type", "factory_ad_price_text"
        ]:
            if k in session_state: ad_data[k] = session_state[k]

    return thumb_data, poster_data, ad_data, item_no


def restore_listing_to_session(record_data: Dict[str, Any], safe_set_fn):
    """
    보관된 매물 레코드의 [썸네일, 창문부착용, 중개대상물 정보]를 세션에 완벽하게 복원합니다.
    """
    if not record_data:
        return

    prop_type = record_data.get("prop_type", "apt")
    thumb_data = record_data.get("thumbnail_data", {})
    poster_data = record_data.get("poster_data", {})
    ad_data = record_data.get("ad_spec_data", {})

    # 1. 썸네일 세션 복원
    for k, v in thumb_data.items():
        safe_set_fn(k, v)

    # 2. 포스터 세션 복원
    for k, v in poster_data.items():
        safe_set_fn(k, v)

    # 3. 중개대상물 정보 세션 복원
    for k, v in ad_data.items():
        safe_set_fn(k, v)

    # 기본 매물번호 세션 보강
    item_no = record_data.get("item_no")
    if item_no:
        if prop_type == "apt":
            safe_set_fn("item_no", str(item_no))
            safe_set_fn("poster_apt_item_no", str(item_no))
        elif prop_type == "comm":
            safe_set_fn("comm_item_no", str(item_no))
            safe_set_fn("poster_comm_item_no", str(item_no))
        elif prop_type == "house":
            safe_set_fn("house_item_no", str(item_no))
            safe_set_fn("poster_house_item_no", str(item_no))
        elif prop_type == "factory":
            safe_set_fn("factory_item_no", str(item_no))
            safe_set_fn("poster_factory_item_no", str(item_no))



def render_tab_storage(safe_set_fn, queue_update_fn):
    """
    [ 탭 4 ] 매물 보관함 UI 전용 렌더러
    - 썸네일, 창문부착용 포스터, 중개대상물 16대 점검표 일괄 보관/불러오기/삭제
    - 형식: 작성일자_매물번호_매물종류.json
    - 클라우드 ZIP 일괄 백업/복원
    """
    import streamlit as st

    st.markdown("""
    <div style="background-color: #F8F9FB; border-left: 4px solid #3182CE; padding: 14px 18px; border-radius: 8px; margin-bottom: 20px;">
        <span style="font-size: 16px; font-weight: 800; color: #1A365D;">
            📁 참좋은 매물 보관함 (썸네일 · 창문부착용 · 중개대상물정보 일괄 보관)
        </span><br/>
        <span style="font-size: 13.5px; color: #4A5568; line-height: 1.6;">
            현재 작업 중인 <b>썸네일 설정, 창문부착용 A4 포스터, 중개대상물 16대 점검표</b> 데이터를 
            <code>작성일자_매물번호_매물종류.json</code> 형식으로 안전하게 영구 보관하고, 언제든 1초 만에 불러오거나 삭제·관리할 수 있습니다.
        </span>
    </div>
    """, unsafe_allow_html=True)

    tab_save, tab_list, tab_backup = st.tabs([
        "💾 현재 매물 보관하기",
        "📋 보관된 매물 목록 (불러오기 / 삭제 / 관리)",
        "☁️ 전체 백업 및 복원 (클라우드 영구보관)"
    ])

    # ----------------------------------------------------
    # [1] 💾 현재 매물 보관하기
    # ----------------------------------------------------
    with tab_save:
        st.markdown("#### 💾 현재 작업 중인 매물 정보 보관")
        st.caption("현재 썸네일, 창문부착용 포스터, 중개대상물표시에 입력된 모든 내용이 함께 묶여서 안전하게 보관됩니다.")

        c_s1, c_s2, c_s3 = st.columns([1, 1.2, 1.2])
        with c_s1:
            prop_opts = ["아파트", "상가", "주택", "공장"]
            # 현재 활성 세션 감지
            detected_type = "아파트"
            if st.session_state.get("comm_ad_location") or st.session_state.get("comm_lease_main_title"):
                detected_type = "상가"
            elif st.session_state.get("house_main_title") or st.session_state.get("house_ad_location"):
                detected_type = "주택"
            elif st.session_state.get("factory_main_title") or st.session_state.get("factory_ad_location"):
                detected_type = "공장"

            sel_prop_label = st.selectbox(
                "매물 종류",
                prop_opts,
                index=prop_opts.index(detected_type),
                key="storage_input_prop_type"
            )
            cur_prop_type = PROP_LABEL_TO_TYPE.get(sel_prop_label, "apt")

        # 자동 매물번호 감지
        detected_item_no = ""
        if cur_prop_type == "apt":
            detected_item_no = str(st.session_state.get("item_no") or st.session_state.get("poster_apt_item_no") or "2664012103")
        elif cur_prop_type == "comm":
            detected_item_no = str(st.session_state.get("comm_item_no") or st.session_state.get("poster_comm_item_no") or "HD76")
        elif cur_prop_type == "house":
            detected_item_no = str(st.session_state.get("house_item_no") or st.session_state.get("poster_house_item_no") or "H01")
        elif cur_prop_type == "factory":
            detected_item_no = str(st.session_state.get("factory_item_no") or st.session_state.get("poster_factory_item_no") or "F01")

        with c_s2:
            input_item_no = st.text_input(
                "매물 번호 (네이버 번호 또는 관리번호)",
                value=detected_item_no,
                key="storage_input_item_no",
                placeholder="예: 2664012103 또는 부산임HD76"
            )

        with c_s3:
            today_str = datetime.datetime.now().strftime("%Y%m%d")
            input_date = st.text_input(
                "작성일자 (YYYYMMDD)",
                value=today_str,
                key="storage_input_date",
                help="기본값은 오늘 날짜입니다."
            )

        c_m1, c_m2 = st.columns([2, 1])
        with c_m1:
            input_memo = st.text_input(
                "간단 메모 (선택사항)",
                key="storage_input_memo",
                placeholder="예: 사상역 도보 3분 초역세권, 소유자 입주협의 가능"
            )
        with c_m2:
            input_status = st.selectbox(
                "매물 상태",
                ["진행중", "거래완료", "보류"],
                key="storage_input_status"
            )

        # 파일명 미리보기
        preview_filename = generate_listing_filename(input_item_no, cur_prop_type, input_date)
        st.markdown(f"""
        <div style="background:#EDF2F7; border:1px solid #CBD5E0; padding:10px 14px; border-radius:6px; margin: 10px 0 16px 0;">
            🏷️ <b>저장 파일명 규칙:</b> <code style="font-size:14px; color:#2B6CB0; font-weight:700;">{preview_filename}</code>
        </div>
        """, unsafe_allow_html=True)

        if st.button("💾 이 매물 지금 보관함에 저장하기", type="primary", use_container_width=True, key="btn_do_save_listing"):
            thumb_d, poster_d, ad_d, auto_no = collect_current_session_data(cur_prop_type, st.session_state)
            final_no = input_item_no.strip() if input_item_no.strip() else auto_no
            ok, msg, saved_fn = save_listing_record(
                item_no=final_no,
                prop_type=cur_prop_type,
                thumbnail_data=thumb_d,
                poster_data=poster_d,
                ad_spec_data=ad_d,
                status=input_status,
                memo=input_memo.strip(),
                custom_date_str=input_date.strip()
            )
            if ok:
                st.success(f"🎉 {msg}")
                st.rerun()
            else:
                st.error(f"⚠️ {msg}")

    # ----------------------------------------------------
    # [2] 📋 보관된 매물 목록 (불러오기 / 삭제 / 관리)
    # ----------------------------------------------------
    with tab_list:
        listings = list_saved_listings()
        st.markdown(f"#### 📋 보관된 매물 목록 (총 {len(listings)}건)")

        if not listings:
            st.info("💡 아직 보관함에 저장된 매물이 없습니다. 위의 **[💾 현재 매물 보관하기]** 탭에서 첫 매물을 저장해보세요!")
        else:
            c_f1, c_f2, c_f3 = st.columns([1.5, 1, 1])
            with c_f1:
                search_kw = st.text_input("🔍 매물명 / 매물번호 / 소재지 검색", key="storage_search_kw", placeholder="검색어 입력...").strip()
            with c_f2:
                filter_prop = st.selectbox("매물종류 필터", ["전체", "아파트", "상가", "주택", "공장"], key="storage_filter_prop")
            with c_f3:
                filter_status = st.selectbox("상태 필터", ["전체", "진행중", "거래완료", "보류"], key="storage_filter_status")

            # 필터링 적용
            filtered = []
            for item in listings:
                if search_kw:
                    kw_lower = search_kw.lower()
                    target_txt = f"{item['filename']} {item['main_title']} {item['location']} {item['price_text']} {item['memo']}".lower()
                    if kw_lower not in target_txt:
                        continue
                if filter_prop != "전체" and item["prop_type_label"] != filter_prop:
                    continue
                if filter_status != "전체" and item["status"] != filter_status:
                    continue
                filtered.append(item)

            st.caption(f"검색 결과: {len(filtered)}건")

            for idx, item in enumerate(filtered):
                fn = item["filename"]
                status_color = "#38A169" if item["status"] == "진행중" else ("#E53E3E" if item["status"] == "거래완료" else "#D69E2E")
                status_badge = f"<span style='background:{status_color}; color:#fff; font-size:12px; font-weight:700; padding:2px 8px; border-radius:12px;'>{item['status']}</span>"
                type_badge = f"<span style='background:#ED8936; color:#fff; font-size:12px; font-weight:700; padding:2px 8px; border-radius:12px;'>{item['prop_type_label']}</span>"

                with st.container():
                    st.markdown(f"""
                    <div style="background:#FFFFFF; border:1.5px solid #E2E8F0; border-radius:8px; padding:12px 16px; margin-bottom:8px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                            <div>
                                {type_badge} {status_badge} &nbsp;
                                <b style="font-size:15px; color:#1A202C;">{item['main_title']}</b>
                            </div>
                            <span style="font-size:12px; color:#718096;">저장일시: {item['saved_at']}</span>
                        </div>
                        <div style="font-size:13.5px; color:#2D3748; line-height:1.6;">
                            💰 <b>가격:</b> {item['price_text'] or '-'} &nbsp;|&nbsp; 
                            📍 <b>소재지:</b> {item['location'] or '-'} &nbsp;|&nbsp; 
                            📄 <b>파일명:</b> <code style="color:#2B6CB0;">{fn}</code>
                            {f"<br/>📝 <b>메모:</b> <span style='color:#4A5568;'>{item['memo']}</span>" if item.get('memo') else ""}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    c_act1, c_act2, c_act3, c_act4 = st.columns([1.5, 1.2, 1, 1.2])
                    with c_act1:
                        if st.button(f"📂 이 매물 불러오기", key=f"btn_load_{idx}_{fn}", type="primary", use_container_width=True):
                            full_rec = load_listing_record(fn)
                            if full_rec:
                                target_tab_name = f"🏢 {full_rec.get('prop_type_label', '아파트')}"
                                queue_update_fn(
                                    action_type="restore_listing",
                                    data=full_rec,
                                    target_tab=target_tab_name,
                                    success_msg=f"🎉 보관 매물 [{fn}]이 썸네일, 창문부착용, 중개대상물 정보에 완벽히 복원되었습니다!"
                                )
                            else:
                                st.error("매물 데이터를 읽어올 수 없습니다.")

                    with c_act2:
                        next_status = "거래완료" if item["status"] == "진행중" else "진행중"
                        btn_label = "🔴 거래완료 처리" if item["status"] == "진행중" else "🟢 진행중으로 변경"
                        if st.button(btn_label, key=f"btn_toggle_{idx}_{fn}", use_container_width=True):
                            update_listing_status(fn, next_status)
                            st.rerun()

                    with c_act3:
                        if st.button("🗑️ 삭제", key=f"btn_del_{idx}_{fn}", use_container_width=True):
                            d_ok, d_msg = delete_listing_record(fn)
                            if d_ok:
                                st.success(d_msg)
                                st.rerun()
                            else:
                                st.error(d_msg)

                    with c_act4:
                        full_json_str = ""
                        rec_raw = load_listing_record(fn)
                        if rec_raw:
                            full_json_str = json.dumps(rec_raw, ensure_ascii=False, indent=2)
                        st.download_button(
                            label="📥 JSON 다운로드",
                            data=full_json_str.encode("utf-8") if full_json_str else b"",
                            file_name=fn,
                            mime="application/json",
                            key=f"dl_single_{idx}_{fn}",
                            use_container_width=True
                        )

    # ----------------------------------------------------
    # [3] ☁️ 전체 백업 및 복원 (클라우드 영구보관)
    # ----------------------------------------------------
    with tab_backup:
        st.markdown("#### ☁️ 클라우드 일괄 백업 및 복원 도구")
        st.markdown("""
        <div style="font-size:13.5px; color:#2C5282; background:#EBF8FF; border:1px solid #BEE3F8; padding:12px 16px; border-radius:8px; line-height:1.6; margin-bottom:14px;">
            💡 <b>Streamlit Cloud 영구보관 팁:</b><br/>
            Streamlit Cloud(웹)는 새로운 코드가 배포되거나 재시작되면 서버 안의 임시 저장 파일이 초기화될 수 있습니다.<br/>
            아래 <b>[전체 매물 일괄 백업 (.zip 다운로드)]</b>를 이용해 소중한 매물 데이터를 내 PC에 한 번씩 저장해 두시면 언제든 업로드하여 100% 원상 복원할 수 있습니다!
        </div>
        """, unsafe_allow_html=True)

        c_bk1, c_bk2 = st.columns(2)
        with c_bk1:
            st.markdown("##### 📥 1. 내 PC로 전체 매물 백업받기")
            zip_bytes = create_backup_zip_bytes()
            today_zip_name = f"참좋은부동산_매물보관함_전체백업_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.zip"
            st.download_button(
                label=f"📦 전체 매물 일괄 백업 다운로드 (.zip)",
                data=zip_bytes,
                file_name=today_zip_name,
                mime="application/zip",
                use_container_width=True,
                type="primary",
                key="btn_dl_all_zip"
            )

        with c_bk2:
            st.markdown("##### 📤 2. 백업 파일로부터 복원하기")
            up_backup = st.file_uploader(
                "백업 ZIP 파일 또는 개별 .json 파일 선택",
                type=["zip", "json"],
                key="up_backup_restore_file"
            )
            if up_backup is not None:
                if st.button("⚡ 선택한 파일로 보관함 복원하기", use_container_width=True, key="btn_do_restore_backup"):
                    b_bytes = up_backup.read()
                    cnt, r_msg = restore_from_zip_or_json(b_bytes, up_backup.name)
                    if cnt > 0:
                        st.success(f"🎉 {r_msg}")
                        st.rerun()
                    else:
                        st.error(f"⚠️ {r_msg}")



def render_quick_save_bar(prop_type: str, key_prefix: str, custom_title: str = None):
    """
    썸네일, 창문부착용 포스터, 중개대상물표시 작업 완료 영역에 배치되는 1초 보관 바
    - 형식: 매물종류_매물번호_저장날짜.json (예: 아파트_2664012103_20261127.json)
    """
    import streamlit as st

    type_label = PROP_TYPE_LABELS.get(prop_type, prop_type)
    today_str = datetime.datetime.now().strftime("%Y%m%d")

    # 자동 매물번호 감지
    auto_no = "001"
    if prop_type == "apt":
        auto_no = str(st.session_state.get("item_no") or st.session_state.get("poster_apt_item_no") or "2664012103")
    elif prop_type == "comm":
        auto_no = str(st.session_state.get("comm_item_no") or st.session_state.get("poster_comm_item_no") or "HD01")
    elif prop_type == "house":
        auto_no = str(st.session_state.get("house_item_no") or st.session_state.get("poster_house_item_no") or "H01")
    elif prop_type == "factory":
        auto_no = str(st.session_state.get("factory_item_no") or st.session_state.get("poster_factory_item_no") or "F01")

    # 헤더 및 안내
    title_text = custom_title or f"💾 [{type_label}] 3종 세트(썸네일+창문포스터+중개대상물표시) 한 번에 보관하기"
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #FFF7ED 0%, #FFEDD5 100%); border: 1.5px solid #F97316; border-radius: 8px; padding: 12px 16px; margin: 18px 0 10px 0;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <b style="font-size: 15px; color: #9A3412;">{title_text}</b><br/>
                <span style="font-size: 13px; color: #7C2D12;">
                    💡 어느 화면에서 누르셔도 현재 작업하신 <b>{type_label}</b>의 <b>①썸네일 + ②창문부착용 포스터 + ③중개대상물 16대 점검표</b> 3가지가 파일 하나로 <b>한 번에 묶여서 일괄 저장</b>됩니다! (각 탭마다 따로 누르실 필요 없습니다)
                </span>
            </div>
            <span style="background:#EA580C; color:#fff; font-size:12px; font-weight:700; padding:3px 10px; border-radius:12px;">3종 원클릭 일괄보관</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c_qb1, c_qb2, c_qb3 = st.columns([1.1, 1.3, 1.4])
    with c_qb1:
        cur_no = st.text_input("매물번호 확인/수정", value=auto_no, key=f"{key_prefix}_qsave_no", placeholder="매물번호")
    with c_qb2:
        cur_memo = st.text_input("간단 메모 (선택)", key=f"{key_prefix}_qsave_memo", placeholder="예: 급매, 소유자 통화완료")

    preview_name = generate_listing_filename(cur_no, prop_type, today_str)

    with c_qb3:
        st.markdown(f"<div style='font-size:12px; color:#6B7280; margin-top:2px;'>저장 파일명: <code style='color:#C2410C; font-weight:700;'>{preview_name}</code></div>", unsafe_allow_html=True)
        if st.button(f"💾 [{type_label}] 3종 세트 한 번에 저장하기", type="primary", use_container_width=True, key=f"{key_prefix}_btn_do_qsave"):
            t_d, p_d, a_d, a_no = collect_current_session_data(prop_type, st.session_state)
            f_no = cur_no.strip() if cur_no.strip() else a_no
            s_ok, s_msg, s_fn = save_listing_record(
                item_no=f_no,
                prop_type=prop_type,
                thumbnail_data=t_d,
                poster_data=p_d,
                ad_spec_data=a_d,
                status="진행중",
                memo=cur_memo.strip(),
                custom_date_str=today_str
            )
            if s_ok:
                st.success(f"🎉 [{s_fn}] 3종 세트(썸네일+창문포스터+중개표시)가 한 번에 안전하게 보관되었습니다! 다른 탭에서 중복 저장하실 필요가 없습니다. (상단 '📁 매물보관함'에서 언제든 1초 복원 가능)")
                st.rerun()
            else:
                st.error(f"⚠️ {s_msg}")
