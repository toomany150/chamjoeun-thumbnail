"""
디자인 모드 관리 모듈 (design_manager.py)
- 기본 프리셋 디자인 테마 제공
- 사용자 커스텀 디자인 모드 저장 / 로드 / 삭제
- 로컬 custom_designs.json 영구 보존으로 다음 실행 시에도 유지
"""

import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CUSTOM_DESIGN_FILE = os.path.join(BASE_DIR, "custom_designs.json")

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

def load_all_designs():
    """기본 디자인 + 사용자 커스텀 디자인을 합쳐서 반환합니다."""
    designs = [d.copy() for d in DEFAULT_DESIGNS]
    if os.path.exists(CUSTOM_DESIGN_FILE):
        try:
            with open(CUSTOM_DESIGN_FILE, "r", encoding="utf-8") as f:
                custom_list = json.load(f)
                if isinstance(custom_list, list):
                    for item in custom_list:
                        item["is_default"] = False
                        designs.append(item)
        except Exception:
            pass
    return designs

def save_custom_design(name: str, primary_hex: str, accent_hex: str, banner_hex: str = None, card_bg_hex: str = None):
    """새로운 커스텀 디자인을 추가하고 JSON에 영구 저장합니다."""
    def hex_to_rgba(h):
        h = h.lstrip("#")
        if len(h) == 6:
            r = int(h[0:2], 16)
            g = int(h[2:4], 16)
            b = int(h[4:6], 16)
            return [r, g, b, 255]
        return [244, 138, 38, 255]

    primary_rgba = hex_to_rgba(primary_hex)
    accent_rgba = hex_to_rgba(accent_hex)
    banner_rgba = hex_to_rgba(banner_hex) if banner_hex else primary_rgba
    card_bg_rgba = hex_to_rgba(card_bg_hex) if card_bg_hex else [246, 247, 249, 255]

    custom_id = f"custom_{len(load_all_designs())}_{int(abs(hash(name)) % 10000)}"
    new_design = {
        "id": custom_id,
        "name": f"🎨 {name.strip()}",
        "primary_color": primary_rgba,
        "accent_color": accent_rgba,
        "banner_bg": banner_rgba,
        "card_bg": card_bg_rgba,
        "is_default": False
    }

    current_customs = []
    if os.path.exists(CUSTOM_DESIGN_FILE):
        try:
            with open(CUSTOM_DESIGN_FILE, "r", encoding="utf-8") as f:
                current_customs = json.load(f)
        except Exception:
            current_customs = []

    current_customs.append(new_design)
    with open(CUSTOM_DESIGN_FILE, "w", encoding="utf-8") as f:
        json.dump(current_customs, f, ensure_ascii=False, indent=2)

    return new_design

def delete_custom_design(design_id: str):
    """사용자가 추가했던 커스텀 디자인을 삭제합니다."""
    if not os.path.exists(CUSTOM_DESIGN_FILE):
        return False
    try:
        with open(CUSTOM_DESIGN_FILE, "r", encoding="utf-8") as f:
            current_customs = json.load(f)
        filtered = [d for d in current_customs if d.get("id") != design_id]
        with open(CUSTOM_DESIGN_FILE, "w", encoding="utf-8") as f:
            json.dump(filtered, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def get_design_by_name(name: str):
    """디자인 이름으로 디자인 설정 객체를 찾습니다."""
    for d in load_all_designs():
        if d["name"] == name:
            return d
    return DEFAULT_DESIGNS[0]
