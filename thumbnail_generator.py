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
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

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

def _load_bg_image(bg_image, target_w: int, target_h: int, zoom: float, offset_x: int, offset_y: int) -> Image.Image:
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
        # 기본 배경 이미지 fallback (sample_living_room or default_bg)
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

def render_thumbnail(
    bg_image=None,
    item_no: str = "No. APT001",
    main_title: str = "사상 중흥S-클래스",
    sub_title: str = "그랜드센트럴",
    feature_text: str = "1572세대 대단지 아파트",
    trade_type: str = "매매",
    price_text: str = "6억2천",
    spec_lines: list = None,
    layout_mode: str = "side_wide",  # "side_wide", "top_panoramic", "side_standard"
    photo_width_ratio: float = 0.65,  # 좌우 모드에서 사진이 차지하는 가로 비율 (0.45 ~ 0.75)
    bg_offset_x: int = 0,
    bg_offset_y: int = 0,
    bg_zoom: float = 1.0,
) -> Image.Image:
    """1080x1080 썸네일을 생성하여 PIL Image로 반환합니다."""
    if spec_lines is None:
        spec_lines = [
            "12월이사예정(협의)",
            "공급 111㎡ / 전용 79.85㎡",
            "방 3 / 욕실 2",
            "남동향 (채광 우수)"
        ]

    W, H = 1080, 1080
    bottom_h = 80
    content_h = H - bottom_h  # 1000px

    if layout_mode == "top_panoramic":
        return _render_top_panoramic(
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
            W=W, H=H, bottom_h=bottom_h, content_h=content_h
        )
    else:
        # side_wide 또는 side_standard
        # standard 모드면 photo_width_ratio를 약 0.50으로 세팅
        effective_ratio = photo_width_ratio if layout_mode == "side_wide" else 0.50
        return _render_side_split(
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
            W=W, H=H, bottom_h=bottom_h, content_h=content_h
        )

def _render_side_split(
    bg_image, item_no, main_title, sub_title, feature_text, trade_type, price_text, spec_lines,
    photo_ratio, bg_offset_x, bg_offset_y, bg_zoom, W, H, bottom_h, content_h
) -> Image.Image:
    """좌우 사선 분할 모드 (와이드 조절 지원)"""
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
    wedge_draw.polygon([(wedge_start, 0), (W, 0), (W, 230)], fill=(244, 138, 38, 255))

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
    poly_draw.polygon(orange_poly, fill=(244, 138, 38, 255))

    white_poly = [
        (0, 0),
        (x_top, 0),
        (x_mid, y_mid),
        (x_bot, content_h),
        (0, content_h)
    ]
    poly_draw.polygon(white_poly, fill=(246, 247, 249, 255))

    canvas = Image.alpha_composite(canvas, poly_layer)
    draw = ImageDraw.Draw(canvas)

    # 4. 상단 물건 번호 띠지 (리본)
    clean_item = (item_no or "").strip()
    if clean_item:
        ribbon_h = 56
        font_item = get_font("NanumGothicBold.ttf", 23)
        ribbon_w = min(x_top - 20, 240)
        draw.polygon([(0, 0), (ribbon_w, 0), (ribbon_w - 30, ribbon_h), (0, ribbon_h)], fill=(244, 138, 38, 255))
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
    draw.rounded_rectangle([left_x, badge_y, left_x + total_badge_w, badge_y + badge_h], radius=badge_h // 2, fill=(244, 138, 38, 255))

    # 코인 아이콘
    coin_path = os.path.join(ASSETS_DIR, "coin.png")
    if os.path.exists(coin_path):
        coin_img = Image.open(coin_path).convert("RGBA").resize((coin_w, coin_w), Image.Resampling.LANCZOS)
        canvas.paste(coin_img, (left_x + coin_margin, badge_y + (badge_h - coin_w) // 2), coin_img)

    # 내부 블랙 캡슐
    inner_x = left_x + coin_margin + coin_w + 6
    draw.rounded_rectangle([inner_x, inner_y, inner_x + inner_w, inner_y + inner_h], radius=inner_h // 2, fill=(28, 30, 33, 255))
    draw.text((inner_x + (inner_w - tw) // 2, inner_y + 6), clean_trade, fill=(244, 138, 38, 255), font=font_trade)

    # 금액 텍스트
    if clean_price:
        price_x = left_x + total_badge_w + 14
        font_price = get_font("NanumGothicExtraBold.ttf", 42 if is_compact else 46)
        draw.text((price_x, badge_y + 3), clean_price, fill=(18, 20, 22, 255), font=font_price)

    # 7. 스펙 4줄 리스트
    spec_start_y = 440
    spec_gap = 66
    font_spec = get_font("NanumGothicBold.ttf", 30 if is_compact else 34)
    icon_files = ["icon_calendar.png", "icon_building.png", "icon_bed.png", "icon_sun.png"]

    for i in range(4):
        txt = spec_lines[i] if i < len(spec_lines) else ""
        if not txt or not txt.strip():
            continue
        cur_y = spec_start_y + i * spec_gap
        icon_path = os.path.join(ASSETS_DIR, icon_files[i])
        icon_box = 36 if is_compact else 40
        if os.path.exists(icon_path):
            ic = Image.open(icon_path).convert("RGBA")
            scale = min(icon_box / ic.width, icon_box / ic.height)
            nw, nh = int(ic.width * scale), int(ic.height * scale)
            ic_resized = ic.resize((nw, nh), Image.Resampling.LANCZOS)
            canvas.paste(ic_resized, (left_x + (icon_box - nw) // 2, cur_y + (icon_box - nh) // 2), ic_resized)

        draw.text((left_x + icon_box + 14, cur_y + 2), txt.strip(), fill=(22, 24, 27, 255), font=font_spec)

    # 8. 하단 고정 바 렌더링
    _draw_footer(canvas, draw, W, H, bottom_h, content_h)

    return canvas.convert("RGB")

def _render_top_panoramic(
    bg_image, item_no, main_title, sub_title, feature_text, trade_type, price_text, spec_lines,
    bg_offset_x, bg_offset_y, bg_zoom, W, H, bottom_h, content_h
) -> Image.Image:
    """상하 파노라마 모드: 상단 약 68% 전체를 와이드 사진으로 노출 (사진 하단 잘림 방지 및 노출 극대화)"""
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
    poly_draw.polygon(orange_poly, fill=(244, 138, 38, 255))

    # 하단 화이트 정보 카드
    white_poly = [
        (0, p_left + band_y),
        (540, p_mid + band_y),
        (W, p_right + band_y),
        (W, content_h),
        (0, content_h)
    ]
    poly_draw.polygon(white_poly, fill=(246, 247, 249, 255))

    canvas = Image.alpha_composite(canvas, poly_layer)
    draw = ImageDraw.Draw(canvas)

    # 상단 물건 번호 띠지
    clean_item = (item_no or "").strip()
    if clean_item:
        draw.polygon([(0, 0), (230, 0), (200, 56), (0, 56)], fill=(244, 138, 38, 255))
        draw.text((26, 16), clean_item, fill=(255, 255, 255, 255), font=get_font("NanumGothicBold.ttf", 23))

    # 상단 우측 오렌지 웨지
    draw.polygon([(820, 0), (W, 0), (W, 160)], fill=(244, 138, 38, 255))

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
    draw.rounded_rectangle([left_x, badge_y, left_x + total_badge_w, badge_y + badge_h], radius=badge_h // 2, fill=(244, 138, 38, 255))

    coin_path = os.path.join(ASSETS_DIR, "coin.png")
    if os.path.exists(coin_path):
        coin_img = Image.open(coin_path).convert("RGBA").resize((coin_w, coin_w), Image.Resampling.LANCZOS)
        canvas.paste(coin_img, (left_x + 10, badge_y + 5), coin_img)

    inner_x = left_x + 10 + coin_w + 6
    draw.rounded_rectangle([inner_x, inner_y, inner_x + inner_w, inner_y + inner_h], radius=inner_h // 2, fill=(28, 30, 33, 255))
    draw.text((inner_x + (inner_w - tw) // 2, inner_y + 6), clean_trade, fill=(244, 138, 38, 255), font=font_trade)

    if clean_price:
        font_price = get_font("NanumGothicExtraBold.ttf", 44)
        draw.text((left_x + total_badge_w + 14, badge_y + 3), clean_price, fill=(18, 20, 22, 255), font=font_price)

    # 우측 4대 스펙
    right_x = 555
    font_spec = get_font("NanumGothicBold.ttf", 28)
    icon_files = ["icon_calendar.png", "icon_building.png", "icon_bed.png", "icon_sun.png"]
    spec_start_y = 612 + shift_down  # 732

    for i in range(4):
        txt = spec_lines[i] if i < len(spec_lines) else ""
        if not txt or not txt.strip():
            continue
        cur_y = spec_start_y + i * 56
        icon_path = os.path.join(ASSETS_DIR, icon_files[i])
        icon_box = 34
        if os.path.exists(icon_path):
            ic = Image.open(icon_path).convert("RGBA")
            scale = min(icon_box / ic.width, icon_box / ic.height)
            nw, nh = int(ic.width * scale), int(ic.height * scale)
            ic_resized = ic.resize((nw, nh), Image.Resampling.LANCZOS)
            canvas.paste(ic_resized, (right_x + (icon_box - nw) // 2, cur_y + (icon_box - nh) // 2), ic_resized)

        draw.text((right_x + icon_box + 14, cur_y + 2), txt.strip(), fill=(22, 24, 27, 255), font=font_spec)

    # 하단 바
    _draw_footer(canvas, draw, W, H, bottom_h, content_h)

    return canvas.convert("RGB")

def _draw_footer(canvas, draw, W, H, bottom_h, content_h):
    """하단 검은색 띠지 (고정 요소)"""
    draw.rectangle([0, content_h, W, H], fill=(35, 36, 40, 255))
    footer_text = "참좋은공인중개사사무소  010-9667-4201"
    font_footer = get_font("NanumGothicBold.ttf", 30)

    ft_box = draw.textbbox((0, 0), footer_text, font=font_footer)
    ft_w, ft_h = ft_box[2] - ft_box[0], ft_box[3] - ft_box[1]

    logo_path = os.path.join(ASSETS_DIR, "logo.png")
    logo_w = 50
    has_logo = os.path.exists(logo_path)
    if has_logo:
        lg = Image.open(logo_path).convert("RGBA")
        logo_w = int(lg.width * (50 / lg.height))
        lg = lg.resize((logo_w, 50), Image.Resampling.LANCZOS)
        start_x = (W - (logo_w + 20 + ft_w)) // 2
        canvas.paste(lg, (start_x, content_h + (bottom_h - 50) // 2), lg)
        draw.text((start_x + logo_w + 20, content_h + (bottom_h - ft_h) // 2 - 2), footer_text, fill=(255, 255, 255, 255), font=font_footer)
    else:
        draw.text(((W - ft_w) // 2, content_h + (bottom_h - ft_h) // 2), footer_text, fill=(255, 255, 255, 255), font=font_footer)
