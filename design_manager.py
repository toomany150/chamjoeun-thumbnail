"""
디자인 모드 관리 모듈 (design_manager.py)
- 기본 프리셋 디자인 테마 제공
- 사용자 커스텀 디자인 모드 저장 / 로드 / 삭제
- 외부 디자인 파일 (.json 테마 설정 또는 .png/.jpg 디자인 프레임/오버레이) 가져오기 & 내보내기 지원
- 마음에 들지 않는 디자인(기본 테마 포함) 영구 삭제 기능 및 기본 복구 기능
- 로컬 custom_designs.json 영구 보존으로 다음 실행 시에도 유지
"""

import os
import json
import base64
import shutil
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CUSTOM_DESIGN_FILE = os.path.join(BASE_DIR, "custom_designs.json")
CUSTOM_DESIGN_ASSETS_DIR = os.path.join(BASE_DIR, "assets", "custom_designs")

os.makedirs(CUSTOM_DESIGN_ASSETS_DIR, exist_ok=True)

DEFAULT_DESIGNS = [
    {
        "id": "orange_signature",
        "name": "🍊 참좋은 시그니처 오렌지 (기본)",
        "primary_color": [244, 138, 38, 255],     # #F48A26
        "accent_color": [235, 94, 40, 255],       # #EB5E28
        "banner_bg": [244, 138, 38, 255],
        "card_bg": [246, 247, 249, 255],
        "is_default": True
    },
    {
        "id": "gold_luxury",
        "name": "👑 럭셔리 다크 골드 (고급·수익형)",
        "primary_color": [218, 168, 68, 255],     # #DAA844
        "accent_color": [180, 130, 40, 255],
        "banner_bg": [24, 28, 36, 255],
        "card_bg": [250, 248, 243, 255],
        "is_default": True
    },
    {
        "id": "navy_modern",
        "name": "🌊 모던 사파이어 블루 (신축·세련)",
        "primary_color": [37, 99, 235, 255],      # #2563EB
        "accent_color": [29, 78, 216, 255],
        "banner_bg": [30, 58, 138, 255],
        "card_bg": [243, 247, 254, 255],
        "is_default": True
    },
    {
        "id": "emerald_nature",
        "name": "🌲 클린 에메랄드 그린 (공장·토지)",
        "primary_color": [16, 185, 129, 255],     # #10B981
        "accent_color": [5, 150, 105, 255],
        "banner_bg": [6, 95, 70, 255],
        "card_bg": [240, 253, 244, 255],
        "is_default": True
    },
    {
        "id": "red_impact",
        "name": "🔥 급매 강력추천 레드 (시선집중)",
        "primary_color": [220, 38, 38, 255],      # #DC2626
        "accent_color": [185, 28, 28, 255],
        "banner_bg": [153, 27, 27, 255],
        "card_bg": [254, 242, 242, 255],
        "is_default": True
    },
    {
        "id": "monochrome_black",
        "name": "🖤 모던 미니멀 블랙&그레이",
        "primary_color": [30, 41, 59, 255],       # #1E293B
        "accent_color": [71, 85, 105, 255],
        "banner_bg": [15, 23, 42, 255],
        "card_bg": [248, 250, 252, 255],
        "is_default": True
    }
]

def _read_storage():
    """custom_designs.json을 읽어 (custom_list, hidden_default_ids) 형태로 반환합니다."""
    if not os.path.exists(CUSTOM_DESIGN_FILE):
        return [], []
    try:
        with open(CUSTOM_DESIGN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                # 구버전 포맷 지원: 리스트 전체가 custom_designs
                return data, []
            elif isinstance(data, dict):
                return data.get("custom_designs", []), data.get("hidden_default_ids", [])
    except Exception:
        pass
    return [], []

def _write_storage(custom_list, hidden_default_ids):
    """custom_designs.json에 저장합니다."""
    payload = {
        "custom_designs": custom_list,
        "hidden_default_ids": hidden_default_ids
    }
    with open(CUSTOM_DESIGN_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def hex_to_rgba(h):
    if not h:
        return [244, 138, 38, 255]
    if isinstance(h, (list, tuple)):
        return [int(x) for x in h[:4]]
    h = str(h).lstrip("#")
    if len(h) == 6:
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        return [r, g, b, 255]
    elif len(h) == 8:
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        a = int(h[6:8], 16)
        return [r, g, b, a]
    return [244, 138, 38, 255]

def rgba_to_hex(rgba):
    if isinstance(rgba, (list, tuple)) and len(rgba) >= 3:
        return f"#{int(rgba[0]):02x}{int(rgba[1]):02x}{int(rgba[2]):02x}".upper()
    return "#F48A26"

def load_all_designs():
    """기본 디자인(삭제/숨김 제외) + 사용자 커스텀 디자인을 합쳐서 반환합니다."""
    custom_list, hidden_ids = _read_storage()
    
    designs = []
    for d in DEFAULT_DESIGNS:
        if d["id"] not in hidden_ids:
            item = d.copy()
            item["is_default"] = True
            designs.append(item)
            
    for item in custom_list:
        c_item = item.copy()
        c_item["is_default"] = False
        designs.append(c_item)
        
    return designs

def save_custom_design(
    name: str,
    primary_hex: str,
    accent_hex: str,
    banner_hex: str = None,
    card_bg_hex: str = None,
    overlay_image_path: str = None
):
    """새로운 커스텀 디자인을 추가하고 JSON에 영구 저장합니다."""
    primary_rgba = hex_to_rgba(primary_hex)
    accent_rgba = hex_to_rgba(accent_hex)
    banner_rgba = hex_to_rgba(banner_hex) if banner_hex else primary_rgba
    card_bg_rgba = hex_to_rgba(card_bg_hex) if card_bg_hex else [246, 247, 249, 255]

    custom_id = f"custom_{int(abs(hash(name)) % 100000)}_{len(load_all_designs())}"
    display_name = name.strip()
    if not display_name.startswith("🎨") and not display_name.startswith("🖼️"):
        display_name = f"🎨 {display_name}"

    new_design = {
        "id": custom_id,
        "name": display_name,
        "primary_color": primary_rgba,
        "accent_color": accent_rgba,
        "banner_bg": banner_rgba,
        "card_bg": card_bg_rgba,
        "overlay_image_path": overlay_image_path,
        "is_default": False
    }

    custom_list, hidden_ids = _read_storage()
    # 중복 이름이 있으면 덮어쓰기
    custom_list = [d for d in custom_list if d.get("name") != display_name and d.get("id") != custom_id]
    custom_list.append(new_design)
    _write_storage(custom_list, hidden_ids)

    return new_design

def import_design_from_json(json_content_or_dict):
    """
    외부 디자인 설정 파일 (.json) 가져오기
    단일 디자인 객체이거나 디자인 리스트 모두 지원합니다.
    """
    if isinstance(json_content_or_dict, str):
        try:
            data = json.loads(json_content_or_dict)
        except Exception as e:
            return False, f"JSON 파싱 실패: {str(e)}"
    else:
        data = json_content_or_dict

    items_to_add = []
    if isinstance(data, list):
        items_to_add = data
    elif isinstance(data, dict):
        if "custom_designs" in data and isinstance(data["custom_designs"], list):
            items_to_add = data["custom_designs"]
        else:
            items_to_add = [data]

    if not items_to_add:
        return False, "유효한 디자인 설정 데이터를 찾을 수 없습니다."

    custom_list, hidden_ids = _read_storage()
    added_count = 0

    for it in items_to_add:
        if not isinstance(it, dict):
            continue
        # 기본 디자인인 경우 무시 (이미 기본 프리셋으로 내장됨)
        if it.get("is_default"):
            # 숨김 목록에 있었다면 숨김 해제
            def_id = it.get("id")
            if def_id in hidden_ids:
                hidden_ids.remove(def_id)
            continue

        raw_name = it.get("name", "가져온 디자인").strip()
        pri = it.get("primary_color", [244, 138, 38, 255])
        acc = it.get("accent_color", [235, 94, 40, 255])
        ban = it.get("banner_bg", pri)
        cbg = it.get("card_bg", [246, 247, 249, 255])
        overlay = it.get("overlay_image_path", None)

        cid = it.get("id") or f"custom_import_{added_count}_{int(abs(hash(raw_name)) % 100000)}"
        display_name = raw_name if (raw_name.startswith("🎨") or raw_name.startswith("🖼️")) else f"🎨 {raw_name}"

        # 중복 제거 (이름 또는 id 기준)
        custom_list = [d for d in custom_list if d.get("name") != display_name and d.get("id") != cid]
        custom_list.append({
            "id": cid,
            "name": display_name,
            "primary_color": hex_to_rgba(pri),
            "accent_color": hex_to_rgba(acc),
            "banner_bg": hex_to_rgba(ban),
            "card_bg": hex_to_rgba(cbg),
            "overlay_image_path": overlay,
            "is_default": False
        })
        added_count += 1

    _write_storage(custom_list, hidden_ids)
    return True, f"{added_count}개의 외부 디자인을 성공적으로 가져왔습니다!"

def import_design_from_image(name: str, image_bytes: bytes, filename: str, primary_hex: str = "#F48A26", accent_hex: str = "#EB5E28"):
    """
    외부 디자인 그래픽 파일 (PNG/JPG 프레임 또는 배경 템플릿) 가져오기
    assets/custom_designs/ 폴더에 영구 보존하고 디자인 모드로 등록합니다.
    """
    safe_name = re.sub(r'[^\w\.-]', '_', filename)
    saved_rel_path = os.path.join("assets", "custom_designs", f"{int(abs(hash(name)) % 10000)}_{safe_name}")
    saved_abs_path = os.path.join(BASE_DIR, saved_rel_path)

    with open(saved_abs_path, "wb") as f:
        f.write(image_bytes)

    display_name = f"🖼️ {name.strip()}"
    return save_custom_design(
        name=display_name,
        primary_hex=primary_hex,
        accent_hex=accent_hex,
        overlay_image_path=saved_rel_path
    )

def delete_design(design_identifier: str):
    """
    사용자가 마음에 들지 않는 디자인을 삭제합니다.
    - 기본 프리셋 디자인: hidden_default_ids에 추가하여 목록에서 숨김(삭제)
    - 커스텀 디자인: custom_designs에서 영구 제거 및 관련 파일 정리
    """
    custom_list, hidden_ids = _read_storage()
    clean_id = (design_identifier or "").strip()
    clean_stripped = re.sub(r'^[^\w가-힣]+', '', clean_id).strip()

    # 1. 기본 디자인인지 확인
    for d in DEFAULT_DESIGNS:
        d_name_stripped = re.sub(r'^[^\w가-힣]+', '', d["name"]).strip()
        if d["id"] == clean_id or d["name"] == clean_id or d_name_stripped == clean_stripped:
            if d["id"] not in hidden_ids:
                hidden_ids.append(d["id"])
                _write_storage(custom_list, hidden_ids)
            return True, f"'{d['name']}' 디자인이 삭제되었습니다."

    # 2. 커스텀 디자인인지 확인
    target_custom = None
    for d in custom_list:
        c_name_stripped = re.sub(r'^[^\w가-힣]+', '', d.get("name", "")).strip()
        if d.get("id") == clean_id or d.get("name") == clean_id or c_name_stripped == clean_stripped:
            target_custom = d
            break

    if target_custom:
        # 연결된 외부 이미지 파일 삭제
        overlay = target_custom.get("overlay_image_path")
        if overlay:
            abs_img = os.path.join(BASE_DIR, overlay)
            if os.path.exists(abs_img):
                try:
                    os.remove(abs_img)
                except Exception:
                    pass

        new_custom_list = [d for d in custom_list if d.get("id") != target_custom.get("id")]
        _write_storage(new_custom_list, hidden_ids)
        return True, f"'{target_custom['name']}' 디자인이 영구 삭제되었습니다."

    return False, "삭제할 디자인을 찾을 수 없습니다."

def reset_default_designs():
    """삭제했던 기본 디자인들을 원래대로 초기화 복원합니다."""
    custom_list, _ = _read_storage()
    _write_storage(custom_list, [])
    return True, "모든 기본 디자인 테마가 복원되었습니다."

def export_all_designs_json():
    """모든 디자인 설정을 외부 파일로 내보낼 수 있도록 JSON 텍스트로 직렬화합니다."""
    designs = load_all_designs()
    return json.dumps(designs, ensure_ascii=False, indent=2)

def get_design_by_name(name: str):
    """디자인 이름으로 디자인 설정 객체를 찾습니다."""
    for d in load_all_designs():
        if d["name"] == name:
            return d
    all_d = load_all_designs()
    return all_d[0] if all_d else DEFAULT_DESIGNS[0]
