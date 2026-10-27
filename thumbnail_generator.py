"""
부동산 블로그 썸네일 생성 엔진 (Pillow 기반)
규격: 1080 x 1080 (1:1 비율 정방형)
레이아웃 모드 지원:
  1. side_wide: 좌우 와이드 사선 분할형 (실내/거실 사진 추천 - 사진 비중 65%~75%)
  2. top_panoramic: 상하 파노라마 와이드형 (가로 100% 전경 극대화)
  3. side_standard: 좌우 표준 사선 분할형 (건물 외관 등 세로형 사진 추천)
"""

import os
import io
import functools
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageColor

def _to_rgba(c, default=(244, 138, 38, 255)):
    if c is None:
        return default
    if isinstance(c, (tuple, list)):
        if len(c) == 3:
            return (int(c[0]), int(c[1]), int(c[2]), 255)
        elif len(c) >= 4:
            return (int(c[0]), int(c[1]), int(c[2]), int(c[3]))
        return default
    if isinstance(c, str):
        try:
            return ImageColor.getcolor(c, "RGBA")
        except Exception:
            return default
    return default

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

@functools.lru_cache(maxsize=128)
def get_font(font_name: str, size: int) -> ImageFont.FreeTypeFont:
    """번들된 폰트 및 시스템 폰트를 검색하여 로드하고, 없을 경우 시스템 기본 고딕으로 대체합니다."""
    # 1순위: 리눅스/클라우드 배포를 위해 assets/fonts 에 번들된 폰트
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

    # 2순위: 윈도우 로컬 시스템 폰트
    candidates = [
        f"C:/Windows/Fonts/{font_name}",
        f"C:/Windows/Fonts/{font_name.lower()}",
        f"C:/Windows/Fonts/{font_name.upper()}",
        f"C:/Windows/Fonts/NanumGothicExtraBold.ttf",
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

def _load_bg_image(bg_image, target_w: int, target_h: int, zoom: float, offset_x: int, offset_y: int, default_filename: str = "sample_living_room.jpg") -> Image.Image:
    """배경 이미지를 안전하게 로드하고 줌 및 오프셋 크롭을 수행합니다."""
    loaded = None
    if bg_image is not None:
        if isinstance(bg_image, str) and os.path.exists(bg_image):
            loaded = Image.open(bg_image).convert("RGBA")
        elif isinstance(bg_image, (bytes, bytearray)):
            loaded = Image.open(io.BytesIO(bg_image)).convert("RGBA")
        elif hasattr(bg_image, "read"):
            bg_image.seek(0)
            loaded = Image.open(bg_image).convert("RGBA")
        elif isinstance(bg_image, Image.Image):
            loaded = bg_image.convert("RGBA")

    if loaded is None:
        # 기본 배경 이미지 fallback
        default_path = os.path.join(ASSETS_DIR, default_filename)
        if not os.path.exists(default_path):
            default_path = os.path.join(ASSETS_DIR, "sample_living_room.jpg")
        if not os.path.exists(default_path):
            default_path = os.path.join(ASSETS_DIR, "default_bg.jpg")
        if os.path.exists(default_path):
            loaded = Image.open(default_path).convert("RGBA")
        else:
            loaded = Image.new("RGBA", (target_w, target_h), (220, 230, 242, 255))

    img_w, img_h = loaded.size
    base_scale = max(target_w / img_w, target_h / img_h)
    final_scale = base_scale * max(0.5, min(2.5, zoom))
    scaled_w = int(img_w * final_scale)
    scaled_h = int(img_h * final_scale)

    resized = loaded.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

    crop_x = int((scaled_w - target_w) / 2) - offset_x
    crop_y = int((scaled_h - target_h) / 2) - offset_y

    crop_x = max(0, min(scaled_w - target_w, crop_x)) if scaled_w >= target_w else 0
    crop_y = max(0, min(scaled_h - target_h, crop_y)) if scaled_h >= target_h else 0

    return resized.crop((crop_x, crop_y, crop_x + target_w, crop_y + target_h))

def draw_deal_done_badge(
    image: Image.Image,
    badge_text: str = "거래완료",
    badge_color = "#1E3A8A",
    pos: tuple = None
) -> Image.Image:
    """
    썸네일 이미지 위에 세련되고 선명한 '거래완료' 배지(스탬프)를 렌더링합니다.
    - 블로그 가독성과 세련미를 위해 기본 색상을 눈에 부담 없는 고급 클래식 네이비(#1E3A8A)로 제공
    - 크기 2배 확대 (대형 72px 폰트, 여백 56px/28px)
    - 썸네일 정중앙 배치
    """
    if image is None:
        return image
    
    res = image.copy().convert("RGBA")
    W, H = res.size
    
    clean_text = (badge_text or "거래완료").strip()
    font_badge = get_font("NanumGothicExtraBold.ttf", 72)
    
    bbox = font_badge.getbbox(clean_text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    
    pad_x = 56
    pad_y = 28
    bw = tw + pad_x * 2
    bh = th + pad_y * 2
    
    if pos is None:
        # 썸네일 가로/세로 정중앙 배치
        bx = (W - bw) // 2
        by = (H - bh) // 2
    else:
        bx, by = pos
        
    badge_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(badge_layer)
    
    # 1. 부드러운 드롭 섀도우 (입체감 부여)
    shadow_offset = 8
    b_draw.rounded_rectangle(
        [(bx + shadow_offset, by + shadow_offset), (bx + bw + shadow_offset, by + bh + shadow_offset)],
        radius=24,
        fill=(0, 0, 0, 130)
    )
    
    # 2. 메인 배지 본체
    rgba_col = _to_rgba(badge_color, default=(30, 58, 138, 255))
    b_draw.rounded_rectangle(
        [(bx, by), (bx + bw, by + bh)],
        radius=24,
        fill=rgba_col
    )
    
    # 3. 화이트 이너/아웃라인 보더 (5px)
    b_draw.rounded_rectangle(
        [(bx, by), (bx + bw, by + bh)],
        radius=24,
        outline=(255, 255, 255, 240),
        width=5
    )
    
    # 4. 텍스트 중앙 배치
    tx = bx + (bw - tw) / 2 - bbox[0]
    ty = by + (bh - th) / 2 - bbox[1]
    b_draw.text((tx, ty), clean_text, font=font_badge, fill=(255, 255, 255, 255))
    
    return Image.alpha_composite(res, badge_layer)


def render_thumbnail(
    bg_image=None,
    item_no: str = "No. APT001",
    main_title: str = "사상 중흥S-클래스",
    sub_title: str = "그랜드센트럴",
    feature_text: str = "",
    trade_type: str = "매매",
    price_text: str = "6억2천",
    spec_lines: list = None,
    layout_mode: str = "top_panoramic",  # "top_panoramic", "side_wide", "side_standard"
    photo_width_ratio: float = 0.65,  # 좌우 모드에서 사진이 차지하는 가로 비율 (0.45 ~ 0.75)
    bg_offset_x: int = 0,
    bg_offset_y: int = 0,
    bg_zoom: float = 1.0,
    show_footer: bool = True,
    footer_text: str = "",
    primary_color: tuple = None,
    accent_color: tuple = None,
    card_bg: tuple = None,
    overlay_image = None,
    deal_done: bool = False,
    deal_color: str = "#FF0101",
    deal_text: str = "거래완료"
) -> Image.Image:
    """1080x1080 썸네일을 생성하여 PIL Image로 반환합니다."""
    primary_color = _to_rgba(primary_color, (244, 138, 38, 255))
    accent_color = _to_rgba(accent_color, (235, 94, 40, 255))
    card_bg = _to_rgba(card_bg, (246, 247, 249, 255))

    if spec_lines is None:
        spec_lines = [
            "105동 / 15층(로얄층)",
            "공급 111㎡ / 전용 79.85㎡",
            "방 3 / 욕실 2",
            "12월이사예정(협의)",
            "남동향 (채광 우수)"
        ]

    W, H = 1080, 1080
    bottom_h = 80 if show_footer else 0
    content_h = H - bottom_h  # 1000px 또는 1080px

    if layout_mode == "top_panoramic":
        res_img = _render_top_panoramic(
            bg_image=bg_image,
            item_no=item_no,
            main_title=main_title,
            sub_title=sub_title,
            feature_text=feature_text,
            trade_type=trade_type,
            price_text=price_text,
            spec_lines=spec_lines,
            bg_offset_x=bg_offset_x,
            bg_offset_y=bg_offset_y,
            bg_zoom=bg_zoom,
            W=W, H=H, bottom_h=bottom_h, content_h=content_h,
            show_footer=show_footer, footer_text=footer_text,
            primary_color=primary_color, accent_color=accent_color, card_bg=card_bg
        )
    else:
        # side_wide 또는 side_standard
        # standard 모드면 photo_width_ratio를 약 0.50으로 세팅
        effective_ratio = photo_width_ratio if layout_mode == "side_wide" else 0.50
        res_img = _render_side_split(
            bg_image=bg_image,
            item_no=item_no,
            main_title=main_title,
            sub_title=sub_title,
            feature_text=feature_text,
            trade_type=trade_type,
            price_text=price_text,
            spec_lines=spec_lines,
            photo_ratio=effective_ratio,
            bg_offset_x=bg_offset_x,
            bg_offset_y=bg_offset_y,
            bg_zoom=bg_zoom,
            W=W, H=H, bottom_h=bottom_h, content_h=content_h,
            show_footer=show_footer, footer_text=footer_text,
            primary_color=primary_color, accent_color=accent_color, card_bg=card_bg
        )

    # 외부 디자인 프레임/오버레이 그래픽이 지정되어 있다면 합성
    if overlay_image:
        try:
            ov_pil = None
            if isinstance(overlay_image, str):
                base_dir = os.path.dirname(os.path.abspath(__file__))
                ov_path = overlay_image if os.path.isabs(overlay_image) else os.path.join(base_dir, overlay_image)
                if os.path.exists(ov_path):
                    ov_pil = Image.open(ov_path).convert("RGBA")
            elif hasattr(overlay_image, "convert"):
                ov_pil = overlay_image.convert("RGBA")
            
            if ov_pil:
                ov_resized = ov_pil.resize((W, H), Image.Resampling.LANCZOS)
                res_img = Image.alpha_composite(res_img.convert("RGBA"), ov_resized)
        except Exception:
            pass

    if deal_done:
        res_img = draw_deal_done_badge(res_img, badge_text=deal_text, badge_color=deal_color)

    return res_img

def _render_side_split(
    bg_image, item_no, main_title, sub_title, feature_text, trade_type, price_text, spec_lines,
    photo_ratio, bg_offset_x, bg_offset_y, bg_zoom, W, H, bottom_h, content_h,
    show_footer: bool = True, footer_text: str = "",
    primary_color: tuple = (244, 138, 38, 255),
    accent_color: tuple = (235, 94, 40, 255),
    card_bg: tuple = (246, 247, 249, 255)
) -> Image.Image:
    """좌우 사선 분할 모드 (와이드 조절 지원)"""
    primary_color = _to_rgba(primary_color, (244, 138, 38, 255))
    accent_color = _to_rgba(accent_color, (235, 94, 40, 255))
    card_bg = _to_rgba(card_bg, (246, 247, 249, 255))

    canvas = Image.new("RGBA", (W, H), (255, 255, 255, 255))

    # 1. 배경 사진 로드 및 배치
    bg_cropped = _load_bg_image(bg_image, W, content_h, bg_zoom, bg_offset_x, bg_offset_y)
    canvas.paste(bg_cropped, (0, 0))

    # 2. 비율 기반 사선 분할점 동적 계산
    # photo_ratio: 0.45 ~ 0.75
    card_base_w = int(W * (1.0 - photo_ratio))
    x_top = card_base_w + 35
    x_mid = card_base_w + 80
    y_mid = 290
    x_bot = card_base_w - 40

    # 우측 상단 장식 오렌지 웨지
    wedge_draw = ImageDraw.Draw(canvas)
    wedge_start = max(x_top + 160, int(W * 0.70))
    wedge_draw.polygon([(wedge_start, 0), (W, 0), (W, 230)], fill=primary_color)

    # 3. 주황색 쉐브론 밴드 & 좌측 소프트 화이트 카드 레이어
    poly_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    poly_draw = ImageDraw.Draw(poly_layer)

    band_w = 26
    orange_poly = [
        (x_top, 0),
        (x_mid, y_mid),
        (x_bot, content_h),
        (x_bot + band_w, content_h),
        (x_mid + band_w + 4, y_mid),
        (x_top + band_w, 0)
    ]
    poly_draw.polygon(orange_poly, fill=primary_color)

    white_poly = [
        (0, 0),
        (x_top, 0),
        (x_mid, y_mid),
        (x_bot, content_h),
        (0, content_h)
    ]
    poly_draw.polygon(white_poly, fill=card_bg)

    canvas = Image.alpha_composite(canvas, poly_layer)
    draw = ImageDraw.Draw(canvas)

    # 4. 상단 물건 번호 띠지 (리본)
    clean_item = (item_no or "").strip()
    if clean_item:
        ribbon_h = 56
        font_item = get_font("NanumGothicBold.ttf", 23)
        ribbon_w = min(x_top - 20, 240)
        draw.polygon([(0, 0), (ribbon_w, 0), (ribbon_w - 30, ribbon_h), (0, ribbon_h)], fill=primary_color)
        draw.text((26, 16), clean_item, fill=(255, 255, 255, 255), font=font_item)

    # 5. 카드 너비에 따른 타이포그래피 스케일링
    is_compact = photo_ratio >= 0.60
    left_x = 42 if is_compact else 55

    main_size = 46 if is_compact else 52
    sub_size = 44 if is_compact else 50
    feat_size = 32 if is_compact else 36

    font_main = get_font("NanumGothicExtraBold.ttf", main_size)
    font_sub = get_font("NanumGothicExtraBold.ttf", sub_size)
    font_feat = get_font("NanumGothicBold.ttf", feat_size)

    if main_title and main_title.strip():
        draw.text((left_x, 135), main_title.strip(), fill=(18, 20, 22, 255), font=font_main)
    if sub_title and sub_title.strip():
        draw.text((left_x, 198), sub_title.strip(), fill=(18, 20, 22, 255), font=font_sub)
    if feature_text and feature_text.strip():
        draw.text((left_x, 268), feature_text.strip(), fill=(38, 42, 46, 255), font=font_feat)

    # 6. 거래 유형 및 금액 뱃지
    badge_y = 345
    badge_h = 52
    clean_trade = (trade_type or "매매").strip()
    clean_price = (price_text or "").strip()

    font_trade = get_font("NanumGothicExtraBold.ttf", 27)
    tb_box = draw.textbbox((0, 0), clean_trade, font=font_trade)
    tw = tb_box[2] - tb_box[0]

    inner_pad = 18
    inner_w = max(78, tw + inner_pad * 2)
    inner_h = 40
    inner_y = badge_y + (badge_h - inner_h) // 2

    coin_w = 42
    coin_margin = 10
    total_badge_w = coin_margin + coin_w + 8 + inner_w + 8

    # 외곽 오렌지 캡슐
    draw.rounded_rectangle([left_x, badge_y, left_x + total_badge_w, badge_y + badge_h], radius=badge_h // 2, fill=primary_color)

    # 코인 아이콘
    coin_path = os.path.join(ASSETS_DIR, "coin.png")
    if os.path.exists(coin_path):
        coin_img = Image.open(coin_path).convert("RGBA").resize((coin_w, coin_w), Image.Resampling.LANCZOS)
        canvas.paste(coin_img, (left_x + coin_margin, badge_y + (badge_h - coin_w) // 2), coin_img)

    # 내부 블랙 캡슐
    inner_x = left_x + coin_margin + coin_w + 6
    draw.rounded_rectangle([inner_x, inner_y, inner_x + inner_w, inner_y + inner_h], radius=inner_h // 2, fill=(28, 30, 33, 255))
    draw.text((inner_x + (inner_w - tw) // 2, inner_y + 6), clean_trade, fill=primary_color, font=font_trade)

    # 금액 텍스트
    if clean_price:
        price_x = left_x + total_badge_w + 14
        font_price = get_font("NanumGothicExtraBold.ttf", 42 if is_compact else 46)
        draw.text((price_x, badge_y + 3), clean_price, fill=(18, 20, 22, 255), font=font_price)

    # 7. 스펙 리스트 (동/층수 포함 최대 5개 유연 렌더링)
    default_icons = ["icon_building.png", "icon_area.png", "icon_bed.png", "icon_calendar.png", "icon_sun.png"]
    valid_specs = []
    for i, item in enumerate(spec_lines or []):
        if isinstance(item, tuple) and len(item) == 2:
            icon_file, txt = item
        else:
            icon_file = default_icons[i] if i < len(default_icons) else "icon_building.png"
            txt = str(item) if item is not None else ""
        if txt and txt.strip():
            valid_specs.append((icon_file, txt.strip()))

    count = len(valid_specs)
    if count >= 5:
        spec_start_y = 425
        spec_gap = 55
        font_spec = get_font("NanumGothicBold.ttf", 29 if is_compact else 32)
        icon_box = 34 if is_compact else 38
    else:
        spec_start_y = 440
        spec_gap = 66
        font_spec = get_font("NanumGothicBold.ttf", 30 if is_compact else 34)
        icon_box = 36 if is_compact else 40

    for i, (icon_file, txt) in enumerate(valid_specs):
        cur_y = spec_start_y + i * spec_gap
        icon_path = os.path.join(ASSETS_DIR, icon_file)
        if not os.path.exists(icon_path):
            icon_path = os.path.join(ASSETS_DIR, "icon_building.png")
        if os.path.exists(icon_path):
            ic = Image.open(icon_path).convert("RGBA")
            scale = min(icon_box / ic.width, icon_box / ic.height)
            nw, nh = int(ic.width * scale), int(ic.height * scale)
            ic_resized = ic.resize((nw, nh), Image.Resampling.LANCZOS)
            canvas.paste(ic_resized, (left_x + (icon_box - nw) // 2, cur_y + (icon_box - nh) // 2), ic_resized)

        draw.text((left_x + icon_box + 14, cur_y + 2), txt, fill=(22, 24, 27, 255), font=font_spec)

    # 8. 하단 고정 바 렌더링
    _draw_footer(canvas, draw, W, H, bottom_h, content_h, footer_text=footer_text, show_footer=show_footer)

    return canvas.convert("RGB")

def _render_top_panoramic(
    bg_image, item_no, main_title, sub_title, feature_text, trade_type, price_text, spec_lines,
    bg_offset_x, bg_offset_y, bg_zoom, W, H, bottom_h, content_h,
    show_footer: bool = True, footer_text: str = "",
    primary_color: tuple = (244, 138, 38, 255),
    accent_color: tuple = (235, 94, 40, 255),
    card_bg: tuple = (246, 247, 249, 255)
) -> Image.Image:
    """상하 파노라마 모드: 상단 약 68% 전체를 와이드 사진으로 노출 (사진 하단 잘림 방지 및 노출 극대화)"""
    primary_color = _to_rgba(primary_color, (244, 138, 38, 255))
    accent_color = _to_rgba(accent_color, (235, 94, 40, 255))
    card_bg = _to_rgba(card_bg, (246, 247, 249, 255))

    canvas = Image.new("RGBA", (W, H), (255, 255, 255, 255))

    shift_down = 120
    split_peak = 565 + shift_down  # 685px
    bg_cropped = _load_bg_image(bg_image, W, split_peak + 50, bg_zoom, bg_offset_x, bg_offset_y)
    canvas.paste(bg_cropped, (0, 0))

    # 하단 사선 분할 레이어
    poly_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    poly_draw = ImageDraw.Draw(poly_layer)

    # 역동적인 사선 주황 밴드 (두께 18px)
    band_y = 18
    p_left = 530 + shift_down   # 650
    p_mid = 565 + shift_down    # 685
    p_right = 515 + shift_down  # 635

    orange_poly = [
        (0, p_left),
        (540, p_mid),
        (W, p_right),
        (W, p_right + band_y),
        (540, p_mid + band_y),
        (0, p_left + band_y)
    ]
    poly_draw.polygon(orange_poly, fill=primary_color)

    # 하단 화이트 정보 카드
    white_poly = [
        (0, p_left + band_y),
        (540, p_mid + band_y),
        (W, p_right + band_y),
        (W, content_h),
        (0, content_h)
    ]
    poly_draw.polygon(white_poly, fill=card_bg)

    canvas = Image.alpha_composite(canvas, poly_layer)
    draw = ImageDraw.Draw(canvas)

    # 상단 물건 번호 띠지
    clean_item = (item_no or "").strip()
    if clean_item:
        draw.polygon([(0, 0), (230, 0), (200, 56), (0, 56)], fill=primary_color)
        draw.text((26, 16), clean_item, fill=(255, 255, 255, 255), font=get_font("NanumGothicBold.ttf", 23))

    # 상단 우측 오렌지 웨지
    draw.polygon([(820, 0), (W, 0), (W, 160)], fill=primary_color)

    # 하단 2열(좌: 타이틀&금액, 우: 4대 스펙) 정돈 배치
    left_x = 55
    font_main = get_font("NanumGothicExtraBold.ttf", 44)
    font_sub = get_font("NanumGothicExtraBold.ttf", 40)
    font_feat = get_font("NanumGothicBold.ttf", 30)

    # 좌측 정보
    title_start_y = 605 + shift_down  # 725
    if main_title and main_title.strip():
        draw.text((left_x, title_start_y), main_title.strip(), fill=(18, 20, 22, 255), font=font_main)
    if sub_title and sub_title.strip():
        draw.text((left_x, title_start_y + 55), sub_title.strip(), fill=(18, 20, 22, 255), font=font_sub)
    if feature_text and feature_text.strip():
        draw.text((left_x, title_start_y + 110), feature_text.strip(), fill=(38, 42, 46, 255), font=font_feat)

    # 거래 뱃지 & 금액
    badge_y = 770 + shift_down  # 890
    badge_h = 52
    clean_trade = (trade_type or "매매").strip()
    clean_price = (price_text or "").strip()

    font_trade = get_font("NanumGothicExtraBold.ttf", 27)
    tb_box = draw.textbbox((0, 0), clean_trade, font=font_trade)
    tw = tb_box[2] - tb_box[0]

    inner_w = max(78, tw + 36)
    inner_h = 40
    inner_y = badge_y + 6
    coin_w = 42

    total_badge_w = 10 + coin_w + 8 + inner_w + 8
    draw.rounded_rectangle([left_x, badge_y, left_x + total_badge_w, badge_y + badge_h], radius=badge_h // 2, fill=primary_color)

    coin_path = os.path.join(ASSETS_DIR, "coin.png")
    if os.path.exists(coin_path):
        coin_img = Image.open(coin_path).convert("RGBA").resize((coin_w, coin_w), Image.Resampling.LANCZOS)
        canvas.paste(coin_img, (left_x + 10, badge_y + 5), coin_img)

    inner_x = left_x + 10 + coin_w + 6
    draw.rounded_rectangle([inner_x, inner_y, inner_x + inner_w, inner_y + inner_h], radius=inner_h // 2, fill=(28, 30, 33, 255))
    draw.text((inner_x + (inner_w - tw) // 2, inner_y + 6), clean_trade, fill=primary_color, font=font_trade)

    if clean_price:
        font_price = get_font("NanumGothicExtraBold.ttf", 44)
        draw.text((left_x + total_badge_w + 14, badge_y + 3), clean_price, fill=(18, 20, 22, 255), font=font_price)

    # 우측 스펙 리스트 (동/층수 포함 최대 5개 스마트 렌더링)
    right_x = 555
    default_icons = ["icon_building.png", "icon_area.png", "icon_bed.png", "icon_calendar.png", "icon_sun.png"]
    valid_specs = []
    for i, item in enumerate(spec_lines or []):
        if isinstance(item, tuple) and len(item) == 2:
            icon_file, txt = item
        else:
            icon_file = default_icons[i] if i < len(default_icons) else "icon_building.png"
            txt = str(item) if item is not None else ""
        if txt and txt.strip():
            valid_specs.append((icon_file, txt.strip()))

    count = len(valid_specs)
    if count >= 5:
        spec_start_y = 722
        spec_gap = 46
        icon_box = 30
        font_spec = get_font("NanumGothicBold.ttf", 26)
    else:
        spec_start_y = 732
        spec_gap = 56
        icon_box = 34
        font_spec = get_font("NanumGothicBold.ttf", 28)

    for i, (icon_file, txt) in enumerate(valid_specs):
        cur_y = spec_start_y + i * spec_gap
        icon_path = os.path.join(ASSETS_DIR, icon_file)
        if not os.path.exists(icon_path):
            icon_path = os.path.join(ASSETS_DIR, "icon_building.png")
        if os.path.exists(icon_path):
            ic = Image.open(icon_path).convert("RGBA")
            scale = min(icon_box / ic.width, icon_box / ic.height)
            nw, nh = int(ic.width * scale), int(ic.height * scale)
            ic_resized = ic.resize((nw, nh), Image.Resampling.LANCZOS)
            canvas.paste(ic_resized, (right_x + (icon_box - nw) // 2, cur_y + (icon_box - nh) // 2), ic_resized)

        draw.text((right_x + icon_box + 12, cur_y + 1), txt, fill=(22, 24, 27, 255), font=font_spec)

    # 하단 바
    _draw_footer(canvas, draw, W, H, bottom_h, content_h, footer_text=footer_text, show_footer=show_footer)

    return canvas.convert("RGB")

def _draw_footer(canvas, draw, W, H, bottom_h, content_h, footer_text: str = "", show_footer: bool = True):
    """하단 검은색 띠지 (소공/직원 커스텀 및 표시/숨김 지원)"""
    if not show_footer:
        return

    draw.rectangle([0, content_h, W, H], fill=(35, 36, 40, 255))
    text_to_draw = footer_text.strip() if footer_text and footer_text.strip() else "참좋은공인중개사사무소  010-9667-4201"
    font_footer = get_font("NanumGothicBold.ttf", 30)

    ft_box = draw.textbbox((0, 0), text_to_draw, font=font_footer)
    ft_w, ft_h = ft_box[2] - ft_box[0], ft_box[3] - ft_box[1]

    logo_path = os.path.join(ASSETS_DIR, "logo.png")
    # "참좋은" 단어가 들어있을 때만 공식 로고 함께 부착
    show_logo = os.path.exists(logo_path) and ("참좋은" in text_to_draw)
    if show_logo:
        lg = Image.open(logo_path).convert("RGBA")
        logo_w = int(lg.width * (50 / lg.height))
        lg = lg.resize((logo_w, 50), Image.Resampling.LANCZOS)
        start_x = (W - (logo_w + 20 + ft_w)) // 2
        canvas.paste(lg, (start_x, content_h + (bottom_h - 50) // 2), lg)
        draw.text((start_x + logo_w + 20, content_h + (bottom_h - ft_h) // 2 - 2), text_to_draw, fill=(255, 255, 255, 255), font=font_footer)
    else:
        # 소공 또는 기타 텍스트는 중앙 정렬 깔끔하게 출력
        draw.text(((W - ft_w) // 2, content_h + (bottom_h - ft_h) // 2), text_to_draw, fill=(255, 255, 255, 255), font=font_footer)


# ====================================================
# 🏬 상가 썸네일 생성 엔진 (임차 & 매매 2대 모드)
# ====================================================

def draw_sparkle(draw, center_x, center_y, size=16, color=(255, 225, 120, 255)):
    """4-포인트 골드 반짝이 별 그리기"""
    points = [
        (center_x, center_y - size),
        (center_x + size * 0.22, center_y - size * 0.22),
        (center_x + size, center_y),
        (center_x + size * 0.22, center_y + size * 0.22),
        (center_x, center_y + size),
        (center_x - size * 0.22, center_y + size * 0.22),
        (center_x - size, center_y),
        (center_x - size * 0.22, center_y - size * 0.22),
    ]
    draw.polygon(points, fill=color)


def render_commercial_lease_thumbnail(
    bg_image=None,
    top_badge_text: str = "사상역 초역세권 · 무권리 추천매물",
    catchphrase_top: str = "유동인구 1등! 대로변 1층",
    main_title: str = "코너 상가 임차",
    catchphrase_bot: str = "가시성 최고! 즉시 입점 가능",
    pin_bubble_text: str = "목 좋은 자리!",
    show_pin: bool = True,
    spec_line1: str = "전용 25평 | 보증금 3,000만 / 월 180만",
    spec_line2: str = "추천 : 카페 · 음식점 · 판매점",
    bg_offset_x: int = 0,
    bg_offset_y: int = 0,
    bg_zoom: float = 1.0,
    show_footer: bool = True,
    office_name: str = "참좋은 공인중개사사무소",
    broker_title: str = "황금터잡이 신소장",
    deal_done: bool = False,
    deal_color: str = "#FF0101",
    deal_text: str = "거래완료"
) -> Image.Image:
    """[상가 임차 썸네일] - 1080x1080 다크 골드 럭셔리 스타일"""
    W, H = 1080, 1080
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))

    # 1. 배경 사진 로드 (기본: sample_comm_lease.jpg)
    bg_cropped = _load_bg_image(bg_image, W, H, bg_zoom, bg_offset_x, bg_offset_y, default_filename="sample_comm_lease.jpg")
    canvas.paste(bg_cropped, (0, 0))

    # 2. 다크 비네트 & 그라데이션 오버레이 (상하 텍스트 가독성 극대화)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)

    # 상단 어두운 그라데이션
    for y in range(0, 520):
        alpha = int(210 * (1.0 - (y / 520) ** 1.3))
        ov_draw.line([(0, y), (W, y)], fill=(12, 16, 24, alpha))

    # 하단 어두운 그라데이션
    for y in range(540, H):
        ratio = (y - 540) / (H - 540)
        alpha = int(220 * (ratio ** 0.8))
        ov_draw.line([(0, y), (W, y)], fill=(10, 14, 22, alpha))

    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    # 3. 상단 캡슐 뱃지
    clean_badge = (top_badge_text or "").strip()
    if clean_badge:
        font_badge = get_font("NanumGothicBold.ttf", 29)
        bbox = font_badge.getbbox(clean_badge)
        bw = bbox[2] - bbox[0]
        pad_x = 36
        badge_w = max(460, bw + pad_x * 2)
        badge_h = 68
        bx1 = (W - badge_w) // 2
        by1 = 66
        bx2 = bx1 + badge_w
        by2 = by1 + badge_h

        # 은은한 외곽 골드 글로우
        glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        glow_draw.rounded_rectangle([bx1 - 3, by1 - 3, bx2 + 3, by2 + 3], radius=badge_h // 2 + 3, outline=(229, 169, 60, 100), width=3)
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(3))
        canvas = Image.alpha_composite(canvas, glow_layer)
        draw = ImageDraw.Draw(canvas)

        # 뱃지 배경 (다크 반투명 네이비)
        badge_bg = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        b_draw = ImageDraw.Draw(badge_bg)
        b_draw.rounded_rectangle([bx1, by1, bx2, by2], radius=badge_h // 2, fill=(18, 22, 32, 220), outline=(229, 175, 75, 240), width=2)
        canvas = Image.alpha_composite(canvas, badge_bg)
        draw = ImageDraw.Draw(canvas)

        # 뱃지 텍스트
        tx = bx1 + (badge_w - bw) // 2 - bbox[0]
        ty = by1 + (badge_h - (bbox[3] - bbox[1])) // 2 - bbox[1]
        draw.text((tx, ty), clean_badge, fill=(255, 255, 255, 255), font=font_badge)

    # 4. 헤더 3줄 텍스트 (카피1 -> 메인 타이틀 -> 카피2)
    clean_cp_top = (catchphrase_top or "").strip()
    if clean_cp_top:
        font_cp_top = get_font("NanumGothicExtraBold.ttf", 44)
        bbox = font_cp_top.getbbox(clean_cp_top)
        tw = bbox[2] - bbox[0]
        tx = (W - tw) // 2 - bbox[0]
        ty = 195
        draw.text((tx, ty + 3), clean_cp_top, fill=(0, 0, 0, 220), font=font_cp_top)
        draw.text((tx, ty), clean_cp_top, fill=(255, 255, 255, 255), font=font_cp_top)

    clean_main = (main_title or "코너 상가 임차").strip()
    if clean_main:
        font_main = get_font("NanumGothicExtraBold.ttf", 76)
        bbox = font_main.getbbox(clean_main)
        tw = bbox[2] - bbox[0]
        tx = (W - tw) // 2 - bbox[0]
        ty = 275

        # 3D 그림자 레이어
        draw.text((tx, ty + 5), clean_main, fill=(0, 0, 0, 240), font=font_main)
        draw.text((tx, ty + 3), clean_main, fill=(60, 42, 10, 220), font=font_main)
        # 골드 본문 텍스트
        draw.text((tx, ty), clean_main, fill=(245, 197, 66, 255), font=font_main)

        # 양쪽 반짝이 별
        draw_sparkle(draw, tx - 28, ty + 25, size=20, color=(255, 225, 130, 255))
        draw_sparkle(draw, tx + tw + 28, ty + 40, size=20, color=(255, 225, 130, 255))

    clean_cp_bot = (catchphrase_bot or "").strip()
    if clean_cp_bot:
        font_cp_bot = get_font("NanumGothicBold.ttf", 42)
        bbox = font_cp_bot.getbbox(clean_cp_bot)
        tw = bbox[2] - bbox[0]
        tx = (W - tw) // 2 - bbox[0]
        ty = 405
        draw.text((tx, ty + 3), clean_cp_bot, fill=(0, 0, 0, 200), font=font_cp_bot)
        draw.text((tx, ty), clean_cp_bot, fill=(228, 242, 255, 255), font=font_cp_bot)

    # 5. 중앙 골드 3D 핀 & 말풍선 배지
    if show_pin:
        pin_path = os.path.join(ASSETS_DIR, "icon_gold_pin.png")
        if os.path.exists(pin_path):
            pin_img = Image.open(pin_path).convert("RGBA")
            pin_h = 105
            pin_w = int(pin_img.width * (pin_h / pin_img.height))
            pin_resized = pin_img.resize((pin_w, pin_h), Image.Resampling.LANCZOS)
            
            pin_x = (W - pin_w) // 2 + 15
            pin_y = 525

            # 핀 그림자
            sh_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            sh_draw = ImageDraw.Draw(sh_layer)
            sh_draw.ellipse([pin_x + 5, pin_y + pin_h - 10, pin_x + pin_w - 5, pin_y + pin_h + 8], fill=(0, 0, 0, 160))
            sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(4))
            canvas = Image.alpha_composite(canvas, sh_layer)

            canvas.paste(pin_resized, (pin_x, pin_y), pin_resized)
            draw = ImageDraw.Draw(canvas)

            # "목 좋은 자리!" 말풍선 배지
            clean_bubble = (pin_bubble_text or "").strip()
            if clean_bubble:
                font_bubble = get_font("NanumGothicBold.ttf", 22)
                b_box = font_bubble.getbbox(clean_bubble)
                bw = b_box[2] - b_box[0]
                bub_w = bw + 34
                bub_h = 44
                bub_x = pin_x - bub_w + 6
                bub_y = pin_y + 12

                bub_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                bub_draw = ImageDraw.Draw(bub_layer)
                bub_draw.rounded_rectangle([bub_x, bub_y, bub_x + bub_w, bub_y + bub_h], radius=bub_h // 2, fill=(22, 28, 38, 230), outline=(225, 175, 75, 255), width=2)
                tri_points = [(bub_x + bub_w - 6, bub_y + bub_h // 2 - 4), (bub_x + bub_w + 8, bub_y + bub_h // 2 + 6), (bub_x + bub_w - 12, bub_y + bub_h // 2 + 8)]
                bub_draw.polygon(tri_points, fill=(22, 28, 38, 230))
                bub_draw.line([(bub_x + bub_w - 6, bub_y + bub_h // 2 - 4), (bub_x + bub_w + 8, bub_y + bub_h // 2 + 6)], fill=(225, 175, 75, 255), width=2)
                bub_draw.line([(bub_x + bub_w + 8, bub_y + bub_h // 2 + 6), (bub_x + bub_w - 12, bub_y + bub_h // 2 + 8)], fill=(225, 175, 75, 255), width=2)

                canvas = Image.alpha_composite(canvas, bub_layer)
                draw = ImageDraw.Draw(canvas)

                btx = bub_x + (bub_w - bw) // 2 - b_box[0] - 2
                bty = bub_y + (bub_h - (b_box[3] - b_box[1])) // 2 - b_box[1]
                draw.text((btx, bty), clean_bubble, fill=(255, 255, 255, 255), font=font_bubble)

    # 6. 스펙 카드 (Glassmorphism 다크 박스)
    card_w = 800
    card_h = 185
    card_x1 = (W - card_w) // 2
    card_y1 = 650
    card_x2 = card_x1 + card_w
    card_y2 = card_y1 + card_h

    card_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd_draw = ImageDraw.Draw(card_layer)
    cd_draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=18, fill=(18, 24, 38, 230), outline=(218, 168, 68, 140), width=2)
    cd_draw.line([(card_x1 + 25, card_y1 + 2), (card_x2 - 25, card_y1 + 2)], fill=(255, 255, 255, 90), width=1)
    canvas = Image.alpha_composite(canvas, card_layer)
    draw = ImageDraw.Draw(canvas)

    clean_sp1 = (spec_line1 or "").strip()
    if clean_sp1:
        parts = [p.strip() for p in clean_sp1.split("|")] if "|" in clean_sp1 else [clean_sp1]
        font_p1 = get_font("NanumGothicBold.ttf", 32)
        font_p1_bold = get_font("NanumGothicExtraBold.ttf", 34)

        if len(parts) >= 2:
            left_txt = parts[0]
            right_txt = parts[1]
            div_txt = " | "

            bbox_l = font_p1_bold.getbbox(left_txt)
            bbox_d = font_p1.getbbox(div_txt)
            bbox_r = font_p1_bold.getbbox(right_txt)

            wl = bbox_l[2] - bbox_l[0]
            wd = bbox_d[2] - bbox_d[0]
            wr = bbox_r[2] - bbox_r[0]
            tot_w = wl + wd + wr

            sx = (W - tot_w) // 2
            sy = card_y1 + 42

            draw.text((sx - bbox_l[0], sy), left_txt, fill=(244, 150, 48, 255), font=font_p1_bold)
            draw.text((sx + wl - bbox_d[0], sy), div_txt, fill=(170, 185, 205, 255), font=font_p1)
            draw.text((sx + wl + wd - bbox_r[0], sy), right_txt, fill=(255, 255, 255, 255), font=font_p1_bold)
        else:
            bbox = font_p1_bold.getbbox(clean_sp1)
            tw = bbox[2] - bbox[0]
            draw.text(((W - tw) // 2 - bbox[0], card_y1 + 42), clean_sp1, fill=(255, 255, 255, 255), font=font_p1_bold)

    clean_sp2 = (spec_line2 or "").strip()
    if clean_sp2:
        font_sp2 = get_font("NanumGothicBold.ttf", 29)
        bbox = font_sp2.getbbox(clean_sp2)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2 - bbox[0], card_y1 + 108), clean_sp2, fill=(235, 240, 248, 255), font=font_sp2)

    # 7. 하단 풋터 바
    if show_footer:
        footer_y = 985
        footer_h = 95

        draw.rectangle([(0, footer_y), (W, H)], fill=(12, 16, 22, 255))
        draw.line([(0, footer_y), (W, footer_y)], fill=(218, 168, 68, 255), width=2)
        draw.line([(0, H - 3), (W, H - 3)], fill=(218, 168, 68, 180), width=2)

        logo_path = os.path.join(ASSETS_DIR, "logo_gold_emblem.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(ASSETS_DIR, "logo.png")

        cur_left_x = 55
        if os.path.exists(logo_path):
            try:
                lg = Image.open(logo_path).convert("RGBA")
                lg_h = 50
                lg_w = int(lg.width * (lg_h / lg.height))
                lg_resized = lg.resize((lg_w, lg_h), Image.Resampling.LANCZOS)
                canvas.paste(lg_resized, (cur_left_x, footer_y + (footer_h - lg_h) // 2), lg_resized)
                cur_left_x += lg_w + 16
            except Exception:
                pass

        font_office = get_font("NanumGothicBold.ttf", 29)
        draw.text((cur_left_x, footer_y + 32), (office_name or "참좋은 공인중개사사무소").strip(), fill=(255, 255, 255, 255), font=font_office)

        font_broker = get_font("NanumGothicExtraBold.ttf", 30)
        broker_txt = (broker_title or "황금터잡이 신소장").strip()
        b_box = font_broker.getbbox(broker_txt)
        br_w = b_box[2] - b_box[0]
        draw.text((W - 55 - br_w, footer_y + 31), broker_txt, fill=(235, 182, 75, 255), font=font_broker)

    if deal_done:
        canvas = draw_deal_done_badge(canvas, badge_text=deal_text, badge_color=deal_color)

    return canvas.convert("RGB")


def render_commercial_sale_thumbnail(
    bg_image=None,
    top_badge_left: str = "사상 핵심상권 매매",
    top_badge_right: str = "우량 임차인 성업중",
    show_chart_icon: bool = True,
    main_highlight_title: str = "확정 수익률 6.8%",
    main_sub_title: str = "안정적인 알짜 상가 매매",
    price_spec_text: str = "매매가 15억 | 보증금 8천 / 월수익 650만 | 실투자금 6억",
    bg_offset_x: int = 0,
    bg_offset_y: int = 0,
    bg_zoom: float = 1.0,
    show_footer: bool = True,
    office_name: str = "참좋은 공인중개사사무소",
    broker_title: str = "황금터잡이 신소장",
    deal_done: bool = False,
    deal_color: str = "#FF0101",
    deal_text: str = "거래완료"
) -> Image.Image:
    """[상가 매매 썸네일] - 1080x1080 더블 골드 프레임 & 수익률 하이라이트 스타일"""
    W, H = 1080, 1080
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))

    # 1. 배경 로드 (기본: sample_comm_sale.jpg)
    bg_cropped = _load_bg_image(bg_image, W, H, bg_zoom, bg_offset_x, bg_offset_y, default_filename="sample_comm_sale.jpg")
    canvas.paste(bg_cropped, (0, 0))

    # 2. 배경 밸런싱 오버레이
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    for y in range(0, 260):
        alpha = int(140 * (1.0 - (y / 260) ** 1.2))
        ov_draw.line([(0, y), (W, y)], fill=(12, 16, 24, alpha))
    for y in range(650, H):
        ratio = (y - 650) / (H - 650)
        alpha = int(180 * (ratio ** 0.8))
        ov_draw.line([(0, y), (W, y)], fill=(12, 16, 24, alpha))
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    # 3. 럭셔리 더블 골드 프레임 테두리 (외곽 34px, 내부 44px)
    frame_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fr_draw = ImageDraw.Draw(frame_layer)

    gold_color = (218, 168, 68, 255)
    gold_dim = (218, 168, 68, 160)

    fr_draw.rectangle([34, 34, W - 34, H - 34], outline=gold_color, width=3)
    fr_draw.rectangle([44, 44, W - 44, H - 44], outline=gold_dim, width=2)

    for cx in [34, W - 44]:
        for cy in [34, H - 44]:
            fr_draw.rectangle([cx - 2, cy - 2, cx + 10, cy + 10], fill=gold_color)

    canvas = Image.alpha_composite(canvas, frame_layer)
    draw = ImageDraw.Draw(canvas)

    # 4. 상단 좌측 분할 배지 (골드 블록 + 다크 블록)
    b_left = (top_badge_left or "").strip()
    b_right = (top_badge_right or "").strip()

    if b_left or b_right:
        badge_y = 80
        badge_h = 58
        font_b1 = get_font("NanumGothicExtraBold.ttf", 27)
        font_b2 = get_font("NanumGothicBold.ttf", 26)

        bbox_l = font_b1.getbbox(b_left) if b_left else (0, 0, 0, 0)
        bbox_r = font_b2.getbbox(b_right) if b_right else (0, 0, 0, 0)

        wl = bbox_l[2] - bbox_l[0]
        wr = bbox_r[2] - bbox_r[0]

        pad_x = 22
        bw_left = wl + pad_x * 2 if b_left else 0
        bw_right = wr + pad_x * 2 if b_right else 0

        cur_x = 75
        if b_left:
            draw.rectangle([cur_x, badge_y, cur_x + bw_left, badge_y + badge_h], fill=(225, 175, 75, 255))
            tx = cur_x + pad_x - bbox_l[0]
            ty = badge_y + (badge_h - (bbox_l[3] - bbox_l[1])) // 2 - bbox_l[1]
            draw.text((tx, ty), b_left, fill=(18, 20, 24, 255), font=font_b1)
            cur_x += bw_left

        if b_right:
            badge_dark = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            bd_draw = ImageDraw.Draw(badge_dark)
            bd_draw.rectangle([cur_x, badge_y, cur_x + bw_right, badge_y + badge_h], fill=(18, 22, 30, 225), outline=(218, 168, 68, 255), width=2)
            canvas = Image.alpha_composite(canvas, badge_dark)
            draw = ImageDraw.Draw(canvas)

            tx = cur_x + pad_x - bbox_r[0]
            ty = badge_y + (badge_h - (bbox_r[3] - bbox_r[1])) // 2 - bbox_r[1]
            draw.text((tx, ty), b_right, fill=(255, 255, 255, 255), font=font_b2)

    # 5. 상단 우측 골드 차트 아이콘
    if show_chart_icon:
        chart_path = os.path.join(ASSETS_DIR, "icon_gold_chart.png")
        if os.path.exists(chart_path):
            ch_img = Image.open(chart_path).convert("RGBA")
            ch_h = 85
            ch_w = int(ch_img.width * (ch_h / ch_img.height))
            ch_resized = ch_img.resize((ch_w, ch_h), Image.Resampling.LANCZOS)
            canvas.paste(ch_resized, (W - 75 - ch_w, 65), ch_resized)

    # 6. 중앙 다크 히어로 블록
    box_w = 880
    box_h = 240
    box_x1 = (W - box_w) // 2
    box_y1 = 300
    box_x2 = box_x1 + box_w
    box_y2 = box_y1 + box_h

    hero_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hr_draw = ImageDraw.Draw(hero_layer)
    hr_draw.rectangle([box_x1, box_y1, box_x2, box_y2], fill=(20, 26, 36, 235))
    canvas = Image.alpha_composite(canvas, hero_layer)
    draw = ImageDraw.Draw(canvas)

    clean_hl = (main_highlight_title or "").strip()
    if clean_hl:
        font_hl = get_font("NanumGothicExtraBold.ttf", 74)
        bbox = font_hl.getbbox(clean_hl)
        tw = bbox[2] - bbox[0]
        tx = (W - tw) // 2 - bbox[0]
        ty = box_y1 + 35
        draw.text((tx, ty + 4), clean_hl, fill=(0, 0, 0, 230), font=font_hl)
        draw.text((tx, ty), clean_hl, fill=(245, 197, 66, 255), font=font_hl)

    clean_sub = (main_sub_title or "").strip()
    if clean_sub:
        font_sub = get_font("NanumGothicExtraBold.ttf", 64)
        bbox = font_sub.getbbox(clean_sub)
        tw = bbox[2] - bbox[0]
        tx = (W - tw) // 2 - bbox[0]
        ty = box_y1 + 135
        draw.text((tx, ty + 3), clean_sub, fill=(0, 0, 0, 220), font=font_sub)
        draw.text((tx, ty), clean_sub, fill=(255, 255, 255, 255), font=font_sub)

    # 7. 하단 스펙 인포 바
    clean_spec = (price_spec_text or "").strip()
    if clean_spec:
        bar_w = 880
        bar_h = 88
        bar_x1 = (W - bar_w) // 2
        bar_y1 = 720
        bar_x2 = bar_x1 + bar_w
        bar_y2 = bar_y1 + bar_h

        bar_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        br_draw = ImageDraw.Draw(bar_layer)
        br_draw.rectangle([bar_x1, bar_y1, bar_x2, bar_y2], fill=(16, 20, 28, 230))
        br_draw.line([(bar_x1, bar_y1), (bar_x2, bar_y1)], fill=(218, 168, 68, 255), width=2)
        br_draw.line([(bar_x1, bar_y2), (bar_x2, bar_y2)], fill=(218, 168, 68, 255), width=2)
        canvas = Image.alpha_composite(canvas, bar_layer)
        draw = ImageDraw.Draw(canvas)

        font_spec = get_font("NanumGothicBold.ttf", 29)
        bbox = font_spec.getbbox(clean_spec)
        tw = bbox[2] - bbox[0]
        tx = (W - tw) // 2 - bbox[0]
        ty = bar_y1 + (bar_h - (bbox[3] - bbox[1])) // 2 - bbox[1]
        draw.text((tx, ty), clean_spec, fill=(255, 255, 255, 255), font=font_spec)

    # 8. 하단 풋터 바
    if show_footer:
        footer_y = 880
        footer_h = 85

        draw.line([(60, footer_y), (W - 60, footer_y)], fill=(218, 168, 68, 255), width=2)

        logo_path = os.path.join(ASSETS_DIR, "logo_gold_emblem.png")
        if not os.path.exists(logo_path):
            logo_path = os.path.join(ASSETS_DIR, "logo.png")

        cur_left_x = 75
        if os.path.exists(logo_path):
            try:
                lg = Image.open(logo_path).convert("RGBA")
                lg_h = 48
                lg_w = int(lg.width * (lg_h / lg.height))
                lg_resized = lg.resize((lg_w, lg_h), Image.Resampling.LANCZOS)
                canvas.paste(lg_resized, (cur_left_x, footer_y + 20), lg_resized)
                cur_left_x += lg_w + 14
            except Exception:
                pass

        font_office = get_font("NanumGothicBold.ttf", 29)
        draw.text((cur_left_x, footer_y + 28), (office_name or "참좋은 공인중개사사무소").strip(), fill=(255, 255, 255, 255), font=font_office)

        font_broker = get_font("NanumGothicExtraBold.ttf", 30)
        broker_txt = (broker_title or "황금터잡이 신소장").strip()
        b_box = font_broker.getbbox(broker_txt)
        br_w = b_box[2] - b_box[0]
        draw.text((W - 75 - br_w, footer_y + 27), broker_txt, fill=(235, 182, 75, 255), font=font_broker)

    if deal_done:
        canvas = draw_deal_done_badge(canvas, badge_text=deal_text, badge_color=deal_color)

    return canvas.convert("RGB")


# ====================================================
# 🖨️ 중개사무소 창문 부착용 A4 포스터 (Window Poster) 렌더러
# 규격: 2480 x 3508 px (A4 정규 300 DPI, 세로형 1:1.414)
# ====================================================
def render_a4_window_poster(
    thumbnail_img=None,
    bg_image=None,
    item_no: str = "No. APT001",
    main_title: str = "사상 중흥S-클래스",
    sub_title: str = "그랜드센트럴 105동",
    feature_text: str = "1572세대 대단지 아파트 · 초역세권",
    trade_type: str = "매매",
    price_text: str = "6억 2,000만 원",
    spec_lines: list = None,
    office_name: str = "참좋은공인중개사사무소",
    office_owner: str = "신제환",
    office_phone: str = "010-9667-4201",
    office_tel: str = "010-9667-4201",
    office_reg_no: str = "제 26530-2026-00009 호",
    office_address: str = "부산광역시 사상구 강선로 9, 1층",
    assistant_phone: str = "",
    is_commercial: bool = False,
    bg_offset_x: int = 0,
    bg_offset_y: int = 0,
    bg_zoom: float = 1.0,
    primary_color_override = None,
    accent_color_override = None,
    banner_bg_override = None
) -> Image.Image:
    """
    중개사무소 창문(유리창/외벽)에 부착하여 보행자의 시선을 사로잡는
    초고화질 A4(2480 x 3508 px, 300 DPI) 매물 브리핑 포스터를 렌더링합니다.
    - 우측 상단 매물번호 눈에 띄는 캡슐 뱃지 배치
    - 메인타이틀 & 서브타이틀 1.4배 확대 및 밀착 배치
    - 매매 정보 및 4행 입주시기 반영 & 대형 글자 크기
    - 사진 영역 최대화 (중복 세부정보 삭제, 순수 실물 사진 고화질 노출)
    - 6대 정보 2열 x 3행 (3줄) 배치로 가독성 극대화 및 잘림 방지
    - 하단 사무실 연락처(051-911-8249) 및 담당자 연락처 직관 노출
    """
    W = 2480
    H = 3508
    canvas = Image.new("RGBA", (W, H), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # 테마 색상 설정
    if is_commercial:
        primary_color = (26, 32, 44, 255)      # 딥 다크
        accent_color = (218, 168, 68, 255)     # 다크 골드
        banner_bg = (24, 28, 36, 255)
    else:
        primary_color = (244, 138, 38, 255)    # 시그니처 오렌지
        accent_color = (235, 94, 40, 255)      # 딥 오렌지
        banner_bg = (244, 138, 38, 255)

    if primary_color_override:
        primary_color = _to_rgba(primary_color_override, primary_color)
    if accent_color_override:
        accent_color = _to_rgba(accent_color_override, accent_color)
    if banner_bg_override:
        banner_bg = _to_rgba(banner_bg_override, banner_bg)
    elif primary_color_override and not is_commercial:
        banner_bg = primary_color

    # 1. 외곽 더블 테두리 (창문에 부착 시 강력한 주목도 제공)
    draw.rounded_rectangle([(50, 50), (W - 50, H - 50)], radius=36, outline=primary_color, width=14)
    draw.rounded_rectangle([(72, 72), (W - 72, H - 72)], radius=24, outline=(226, 232, 240, 255), width=3)

    # 2. 상단 시작 위치 설정 & 좌측 상단 매물번호 뱃지 (요구사항: 매물좌측상단에 매물번호 넣어줘)
    clean_item = (item_no or "").strip()
    if clean_item:
        font_item = get_font("NanumGothicExtraBold.ttf", 46)
        item_text = f"매물번호 : {clean_item}"
        itb = font_item.getbbox(item_text)
        itw = itb[2] - itb[0]
        ith = itb[3] - itb[1]
        ib_pad_x = 36
        ib_w = itw + ib_pad_x * 2
        ib_h = 76
        ib_x = 100  # 좌측 상단으로 이동!
        ib_y = 95
        draw.rounded_rectangle([(ib_x, ib_y), (ib_x + ib_w, ib_y + ib_h)], radius=20, fill=(248, 250, 252, 255), outline=primary_color, width=3)
        draw.text((ib_x + ib_pad_x - itb[0], ib_y + (ib_h - ith) // 2 - itb[1]), item_text, fill=primary_color, font=font_item)

    # 3. 초대형 메인 타이틀 (상단 중앙에 시원하게 단독 배치)
    cur_y = 175
    main_size = 205
    title_str = (main_title or "추천 부동산 매물").strip()
    font_main = get_font("NanumGothicExtraBold.ttf", main_size)
    mtb = font_main.getbbox(title_str)
    mtw = mtb[2] - mtb[0]
    max_title_w = W - 220
    while mtw > max_title_w and main_size > 110:
        main_size -= 6
        font_main = get_font("NanumGothicExtraBold.ttf", main_size)
        mtb = font_main.getbbox(title_str)
        mtw = mtb[2] - mtb[0]

    title_x = (W - mtw) // 2
    draw.text((title_x, cur_y), title_str, fill=(15, 23, 42, 255), font=font_main)
    cur_y += (mtb[3] - mtb[1]) + 35

    # 4. 초대형 시선강탈 거래형태 & 금액 & 입주가능시기 배너 (중앙 정렬)
    banner_h = 410
    draw.rounded_rectangle([(100, cur_y), (W - 100, cur_y + banner_h)], radius=34, fill=banner_bg)

    # 4-1. 상단: 거래형태 & 금액 (메인타이틀과 동일한 초대형 크기로 중앙 배치)
    trade_str = (trade_type or "매매").strip()
    p_str = (price_text or "상담 환영").strip()

    trade_font_size = 140
    price_font_size = 160

    font_trade = get_font("NanumGothicExtraBold.ttf", trade_font_size)
    font_price = get_font("NanumGothicExtraBold.ttf", price_font_size)

    tb = font_trade.getbbox(trade_str)
    tw = tb[2] - tb[0]
    th = tb[3] - tb[1]

    pb = font_price.getbbox(p_str)
    pw = pb[2] - pb[0]
    ph = pb[3] - pb[1]

    gap_trade_price = 45
    pill_pad_x = 36
    pill_w = tw + pill_pad_x * 2
    pill_h = th + 40

    total_top_w = pill_w + gap_trade_price + pw
    max_top_w = W - 280

    while total_top_w > max_top_w and price_font_size > 100:
        trade_font_size -= 6
        price_font_size -= 6
        font_trade = get_font("NanumGothicExtraBold.ttf", trade_font_size)
        font_price = get_font("NanumGothicExtraBold.ttf", price_font_size)
        tb = font_trade.getbbox(trade_str)
        tw = tb[2] - tb[0]
        th = tb[3] - tb[1]
        pb = font_price.getbbox(p_str)
        pw = pb[2] - pb[0]
        ph = pb[3] - pb[1]
        pill_w = tw + pill_pad_x * 2
        pill_h = th + 36
        total_top_w = pill_w + gap_trade_price + pw

    start_top_x = (W - total_top_w) // 2
    top_row_y = cur_y + 36

    # 거래 형태 화이트 알약 배지
    draw.rounded_rectangle(
        [(start_top_x, top_row_y), (start_top_x + pill_w, top_row_y + pill_h)],
        radius=26,
        fill=(255, 255, 255, 255)
    )
    draw.text(
        (start_top_x + (pill_w - tw) // 2 - tb[0], top_row_y + (pill_h - th) // 2 - tb[1]),
        trade_str,
        fill=primary_color,
        font=font_trade
    )

    # 금액 텍스트
    price_x = start_top_x + pill_w + gap_trade_price
    price_y = top_row_y + (pill_h - ph) // 2 - pb[1]
    draw.text((price_x, price_y), p_str, fill=(255, 255, 255, 255), font=font_price)

    # 4-2. 하단: 입주가능시기 ('입주가능시기 : ' 라벨 명시 & 초대형 중앙 배치)
    raw_move_in = ""
    if spec_lines and len(spec_lines) > 3 and spec_lines[3] and str(spec_lines[3]).strip():
        raw_move_in = str(spec_lines[3]).strip()
    else:
        raw_move_in = "즉시입주 협의가능" if not is_commercial else "성업중 · 즉시입점"

    clean_mi = raw_move_in.replace("입주가능시기", "").replace("입주시기", "").replace("입주가능일", "").replace(":", "").strip()
    if clean_mi:
        move_in_txt = f"입주가능시기 : {clean_mi}"
    else:
        move_in_txt = "입주가능시기 : 즉시입주 협의"

    mi_size = 92
    font_move_in = get_font("NanumGothicBold.ttf", mi_size)
    mib = font_move_in.getbbox(move_in_txt)
    miw = mib[2] - mib[0]
    mih = mib[3] - mib[1]
    max_mi_w = W - 320
    while miw > max_mi_w and mi_size > 54:
        mi_size -= 4
        font_move_in = get_font("NanumGothicBold.ttf", mi_size)
        mib = font_move_in.getbbox(move_in_txt)
        miw = mib[2] - mib[0]
        mih = mib[3] - mib[1]

    # 입주가능시기 전용 캡슐 바 (배너 하단에 반투명 오버레이로 중앙 배치)
    mi_box_w = min(miw + 90, W - 260)
    mi_box_h = 100
    mi_box_x = (W - mi_box_w) // 2
    mi_box_y = cur_y + banner_h - mi_box_h - 30

    draw.rounded_rectangle(
        [(mi_box_x, mi_box_y), (mi_box_x + mi_box_w, mi_box_y + mi_box_h)],
        radius=26,
        fill=(0, 0, 0, 55),
        outline=(255, 255, 255, 80),
        width=2
    )
    draw.text(
        (mi_box_x + (mi_box_w - miw) // 2 - mib[0], mi_box_y + (mi_box_h - mih) // 2 - mib[1]),
        move_in_txt,
        fill=(255, 255, 255, 255),
        font=font_move_in
    )

    cur_y += banner_h + 25

    # 5. 매물 비주얼 영역 (요구사항: 썸네일 디자인된 사진을 비주얼 영역 크기에 맞게 꽉 채우고, 썸네일 하단의 중복정보는 제거!)
    visual_box_w = W - 200
    visual_box_h = 1320  # 기존 1200 -> 1320px로 확대하여 시원하고 웅장하게 배치
    visual_x = 100
    visual_y = cur_y

    # 배경 액자 프레임
    draw.rounded_rectangle([(visual_x - 4, visual_y - 4), (visual_x + visual_box_w + 4, visual_y + visual_box_h + 4)], radius=28, fill=(226, 232, 240, 255))
    draw.rounded_rectangle([(visual_x, visual_y), (visual_x + visual_box_w, visual_y + visual_box_h)], radius=24, fill=(241, 245, 249, 255))

    target_photo = None
    is_from_thumb = False
    if thumbnail_img is not None:
        is_from_thumb = True
        if isinstance(thumbnail_img, Image.Image):
            target_photo = thumbnail_img.convert("RGBA")
        elif isinstance(thumbnail_img, (bytes, bytearray)):
            target_photo = Image.open(io.BytesIO(thumbnail_img)).convert("RGBA")
    elif bg_image is not None:
        if isinstance(bg_image, Image.Image):
            target_photo = bg_image.convert("RGBA")
        elif isinstance(bg_image, (bytes, bytearray)):
            target_photo = Image.open(io.BytesIO(bg_image)).convert("RGBA")
        elif hasattr(bg_image, "read"):
            bg_image.seek(0)
            target_photo = Image.open(bg_image).convert("RGBA")

    if target_photo is not None:
        try:
            target_photo = ImageOps.exif_transpose(target_photo)
        except Exception:
            pass

        pw, ph = target_photo.size

        # ⭐ 요구사항: "썸네일 사진밑에 해당정보는 중복정보니깐 없어도 돼. 썸네일 디자인된 사진을 크기에 맞게 넣고"
        # 썸네일에서 하단 중복 텍스트(매물명, 가격, 스펙 등)가 적힌 하단 영역(약 32%)을 제외하고,
        # 상단의 디자인된 사진 영역(0 ~ 68%)만 취하여 비주얼 박스 전체에 꽉 채웁니다!
        if is_from_thumb:
            valid_h = int(ph * 0.68)
            photo_to_fit = target_photo.crop((0, 0, pw, valid_h))
            src_w, src_h = photo_to_fit.size
        else:
            photo_to_fit = target_photo
            src_w, src_h = pw, ph

        # 비주얼 박스 전체(2280 x 1320)에 꽉 채움 (Cover)
        scale = max(visual_box_w / src_w, visual_box_h / src_h)
        if bg_zoom and bg_zoom != 1.0:
            scale *= bg_zoom
        new_w = int(src_w * scale)
        new_h = int(src_h * scale)
        resized_photo = photo_to_fit.resize((new_w, new_h), Image.Resampling.LANCZOS)

        crop_x = (new_w - visual_box_w) // 2 - int(bg_offset_x * (visual_box_w / 1080))
        crop_y = (new_h - visual_box_h) // 2 - int(bg_offset_y * (visual_box_h / 1080))
        crop_x = max(0, min(new_w - visual_box_w, crop_x))
        crop_y = max(0, min(new_h - visual_box_h, crop_y))

        cropped_photo = resized_photo.crop((crop_x, crop_y, crop_x + visual_box_w, crop_y + visual_box_h))

        # 둥근 모서리 마스크 클리핑
        mask = Image.new("L", (visual_box_w, visual_box_h), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle([(0, 0), (visual_box_w, visual_box_h)], radius=24, fill=255)
        canvas.paste(cropped_photo, (visual_x, visual_y), mask)
    else:
        font_no_img = get_font("NanumGothicBold.ttf", 56)
        no_img_txt = "블로그 완성 썸네일 이미지"
        nib = font_no_img.getbbox(no_img_txt)
        draw.text((visual_x + (visual_box_w - (nib[2] - nib[0])) // 2, visual_y + visual_box_h // 2 - 30), no_img_txt, fill=(148, 163, 184, 255), font=font_no_img)

    cur_y += visual_box_h + 24

    # 6. 핵심 4대 스펙 카드 (요구사항: 4대 핵심사항 글자 크기도 공간에 맞게 더 크게 해줘!)
    if not spec_lines or len(spec_lines) < 5:
        spec_lines = [
            "25층 / 36층 (로얄층)",
            "공급 111.42㎡ / 전용 79.85㎡",
            "방 3 / 욕실 2개",
            "즉시입주 협의가능",
            "남동향 (거실 기준)"
        ]

    # 입주시기 & 주차대수 삭제 -> 4개 핵심 항목만 압축
    cards_data = [
        ("해당층 / 총층", spec_lines[0] if len(spec_lines) > 0 and spec_lines[0] else "고층 / 로얄층"),
        ("공급 및 전용면적", spec_lines[1] if len(spec_lines) > 1 and spec_lines[1] else "상담 시 즉시 안내"),
        ("방수 / 욕실수", spec_lines[2] if len(spec_lines) > 2 and spec_lines[2] else "방 3개 / 욕실 2개"),
        ("방향 (채광 우수)", spec_lines[4] if len(spec_lines) > 4 and spec_lines[4] else "남향 위주 배치")
    ]

    card_cols = 2
    card_gap_x = 28
    card_gap_y = 20
    total_card_w = visual_box_w
    c_w = (total_card_w - (card_cols - 1) * card_gap_x) // card_cols
    c_h = 265  # 225 -> 265px로 대폭 확대하여 공간을 알차게 채움!

    font_c_label = get_font("NanumGothicBold.ttf", 52)  # 46 -> 52px로 라벨 대폭 확대

    for idx, (lbl, val) in enumerate(cards_data):
        row = idx // card_cols
        col = idx % card_cols
        cx = visual_x + col * (c_w + card_gap_x)
        cy = cur_y + row * (c_h + card_gap_y)

        # 카드 박스
        draw.rounded_rectangle([(cx, cy), (cx + c_w, cy + c_h)], radius=26, fill=(248, 250, 252, 255), outline=(226, 232, 240, 255), width=2)
        # 카드 상단 라벨
        draw.text((cx + 42, cy + 28), lbl, fill=(100, 116, 139, 255), font=font_c_label)

        # 카드 메인 값 (68px -> 78px 초대형 폰트로 웅장하게 확대!)
        val_clean = str(val).strip()
        v_size = 78
        font_c_val = get_font("NanumGothicExtraBold.ttf", v_size)
        vb = font_c_val.getbbox(val_clean)
        vw = vb[2] - vb[0]
        max_val_w = c_w - 84
        while vw > max_val_w and v_size > 48:
            v_size -= 2
            font_c_val = get_font("NanumGothicExtraBold.ttf", v_size)
            vb = font_c_val.getbbox(val_clean)
            vw = vb[2] - vb[0]

        draw.text((cx + 42, cy + 124), val_clean, fill=(15, 23, 42, 255), font=font_c_val)

    # 4대 스펙 카드 (2행) 종료 위치 계산
    cur_y += 2 * (c_h + card_gap_y) + 10

    # 6-2. ⭐ 매물 핵심 특징 배너 (요구사항: "매물특징에 별표는 지워죠.")
    feat_clean = (feature_text or "").replace("★", "").replace("☆", "").replace("✦", "").replace("✔", "").strip()
    feat_display = feat_clean if feat_clean else "초역세권 대단지 프리미엄 추천 매물"

    feat_box_w = visual_box_w
    feat_box_h = 180  # 165 -> 180px로 확대!
    feat_x = visual_x
    feat_y = cur_y

    if is_commercial:
        f_bg_color = (26, 32, 44, 255)
        f_outline = accent_color
        f_txt_color = (245, 208, 115, 255)
    else:
        f_bg_color = (255, 247, 237, 255)
        f_outline = primary_color
        f_txt_color = (194, 65, 12, 255)

    draw.rounded_rectangle(
        [(feat_x, feat_y), (feat_x + feat_box_w, feat_y + feat_box_h)],
        radius=28,
        fill=f_bg_color,
        outline=f_outline,
        width=4
    )

    # 12자 내외 문구에 최적화된 90px 초대형 폰트 (기존 82px -> 90px로 초대형 확대!)
    feat_f_size = 90
    font_feat_banner = get_font("NanumGothicExtraBold.ttf", feat_f_size)
    ftb = font_feat_banner.getbbox(feat_display)
    ftw = ftb[2] - ftb[0]
    fth = ftb[3] - ftb[1]
    max_ftw = feat_box_w - 90

    while ftw > max_ftw and feat_f_size > 48:
        feat_f_size -= 2
        font_feat_banner = get_font("NanumGothicExtraBold.ttf", feat_f_size)
        ftb = font_feat_banner.getbbox(feat_display)
        ftw = ftb[2] - ftb[0]
        fth = ftb[3] - ftb[1]

    draw.text(
        (feat_x + (feat_box_w - ftw) // 2 - ftb[0], feat_y + (feat_box_h - fth) // 2 - ftb[1]),
        feat_display,
        fill=f_txt_color,
        font=font_feat_banner
    )

    cur_y += feat_box_h + 30

    # 7. 하단 중개사무소 정보 (요구사항: "하단 매물특징 문구와 중개소하단 정보 사이에 공간이 비잖아. 그 공간을 줄이고")
    # 하단 테두리 바로 위 40px 여백으로 딱 맞추고, 높이를 380px로 넉넉하게 확장하여 공백을 완벽하게 없앰!
    footer_bottom = H - 85
    footer_y = max(cur_y, footer_bottom - 380)

    draw.rounded_rectangle([(100, footer_y), (W - 100, footer_bottom)], radius=28, fill=(15, 23, 42, 255))

    # 상단 사무소 명칭 및 대표자
    font_f_head = get_font("NanumGothicBold.ttf", 54)
    o_name = (office_name or "참좋은공인중개사사무소").strip()
    o_owner = (office_owner or "신제환").strip()
    draw.text((150, footer_y + 40), f"{o_name}   |   대표 공인중개사: {o_owner}", fill=(255, 255, 255, 255), font=font_f_head)

    # 등록번호 및 소재지
    font_f_sub = get_font("NanumGothic.ttf", 38)
    o_reg = (office_reg_no or "제 26530-2026-00009 호").strip()
    o_addr = (office_address or "부산광역시 사상구 강선로 9, 1층").strip()
    f_sub_str = f"등록번호: {o_reg}   •   사무소 소재지: {o_addr}"
    draw.text((150, footer_y + 116), f_sub_str, fill=(203, 213, 225, 255), font=font_f_sub)

    # 구분선
    draw.line([(150, footer_y + 175), (W - 150, footer_y + 175)], fill=(51, 65, 85, 255), width=2)

    # 요구사항: "사무실 연락처:" 삭제! 051-911-8249와 담당자 직통번호의 글자 크기를 동일하게 일치(84px)하여 균형 배치
    tel_clean = (office_tel or "010-9667-4201").strip()
    ast_clean = (assistant_phone or "").strip()

    phone_font_size = 84
    font_phone = get_font("NanumGothicExtraBold.ttf", phone_font_size)

    if ast_clean:
        # 1) 담당자 번호가 있는 경우: 좌측 051-911-8249 & 우측 [담당자 직통 : 010-...] 동일 84px로 좌우 대칭 배치!
        phone_y = footer_y + 225

        # 좌측: 051-911-8249 (옐로우 골드, 84px)
        draw.text((150, phone_y), tel_clean, fill=(251, 191, 36, 255), font=font_phone)

        # 우측: 담당자 직통 번호 (오렌지 알약 뱃지 안에 84px 동일 크기로 렌더링!)
        ast_display_txt = f"담당자 직통 : {ast_clean}"
        ab = font_phone.getbbox(ast_display_txt)
        aw = ab[2] - ab[0]
        ah = ab[3] - ab[1]

        ast_box_w = aw + 64
        ast_box_h = 114
        ast_box_x = W - 150 - ast_box_w
        ast_box_y = footer_y + 210
        draw.rounded_rectangle([(ast_box_x, ast_box_y), (ast_box_x + ast_box_w, ast_box_y + ast_box_h)], radius=24, fill=(244, 138, 38, 255), outline=(255, 255, 255, 220), width=3)
        draw.text((ast_box_x + 32 - ab[0], ast_box_y + (ast_box_h - ah) // 2 - ab[1]), ast_display_txt, fill=(255, 255, 255, 255), font=font_phone)
    else:
        # 2) 담당자 번호가 없는 경우: 좌측 051-911-8249 & 우측 친절 상담 슬로건
        font_solo_phone = get_font("NanumGothicExtraBold.ttf", 98)
        draw.text((150, footer_y + 212), tel_clean, fill=(251, 191, 36, 255), font=font_solo_phone)

        font_slogan = get_font("NanumGothicBold.ttf", 44)
        slogan_txt = "친절 상담 · 책임 중개 · 매물 접수 환영"
        sb = font_slogan.getbbox(slogan_txt)
        sw = sb[2] - sb[0]
        sh = sb[3] - sb[1]
        sl_box_w = sw + 56
        sl_box_h = 92
        sl_box_x = W - 150 - sl_box_w
        sl_box_y = footer_y + 220
        draw.rounded_rectangle([(sl_box_x, sl_box_y), (sl_box_x + sl_box_w, sl_box_y + sl_box_h)], radius=20, fill=(30, 41, 59, 255), outline=(71, 85, 105, 255), width=2)
        draw.text((sl_box_x + 28 - sb[0], sl_box_y + (sl_box_h - sh) // 2 - sb[1]), slogan_txt, fill=(241, 245, 249, 255), font=font_slogan)
    return canvas.convert("RGB")


