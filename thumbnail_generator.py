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
from PIL import Image, ImageDraw, ImageFont, ImageFilter

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
    show_footer: bool = True,
    footer_text: str = "",
) -> Image.Image:
    """1080x1080 썸네일을 생성하여 PIL Image로 반환합니다."""
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
            W=W, H=H, bottom_h=bottom_h, content_h=content_h,
            show_footer=show_footer, footer_text=footer_text
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
            W=W, H=H, bottom_h=bottom_h, content_h=content_h,
            show_footer=show_footer, footer_text=footer_text
        )

def _render_side_split(
    bg_image, item_no, main_title, sub_title, feature_text, trade_type, price_text, spec_lines,
    photo_ratio, bg_offset_x, bg_offset_y, bg_zoom, W, H, bottom_h, content_h,
    show_footer: bool = True, footer_text: str = ""
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
    show_footer: bool = True, footer_text: str = ""
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

    return canvas.convert("RGB")

