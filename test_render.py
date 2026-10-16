import os
from PIL import Image, ImageDraw, ImageFont

def get_font(font_name, size):
    paths = [
        f"C:/Windows/Fonts/{font_name}",
        f"C:/Windows/Fonts/{font_name.lower()}",
        f"C:/Windows/Fonts/{font_name.upper()}",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    # Fallback to malgun
    return ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", size)

def create_thumbnail(
    bg_image_path="default_building.jpg",
    item_no="No. APT001",
    main_title="사상 중흥S-클래스",
    sub_title="그랜드센트럴",
    feature_text="1572세대 대단지 아파트",
    trade_type="매매",
    price_text="5억 8천",
    spec_lines=None,
    output_path="test_thumbnail.png"
):
    if spec_lines is None:
        spec_lines = [
            "즉시 입주 가능",
            "공급 105㎡ / 전용 84㎡",
            "방 3 / 욕실 2",
            "남향 (채광 우수)"
        ]

    W, H = 1080, 1080
    bottom_h = 80
    content_h = H - bottom_h  # 1000

    # Base canvas
    canvas = Image.new("RGBA", (W, H), (255, 255, 255, 255))

    # 1. Background photo on the right
    if os.path.exists(bg_image_path):
        bg = Image.open(bg_image_path).convert("RGBA")
        # Cover 1080 x 1000
        # Calculate aspect ratio
        target_w, target_h = W, content_h
        img_w, img_h = bg.size
        scale = max(target_w / img_w, target_h / img_h)
        new_w, new_h = int(img_w * scale), int(img_h * scale)
        bg_resized = bg.resize((new_w, new_h), Image.Resampling.LANCZOS)
        # Crop center
        crop_x = (new_w - target_w) // 2
        crop_y = (new_h - target_h) // 2
        bg_cropped = bg_resized.crop((crop_x, crop_y, crop_x + target_w, crop_y + target_h))
        canvas.paste(bg_cropped, (0, 0))
    else:
        # Fallback background
        bg_fallback = Image.new("RGBA", (W, content_h), (200, 215, 230, 255))
        canvas.paste(bg_fallback, (0, 0))

    # 2. Top-right decorative orange wedge
    wedge_draw = ImageDraw.Draw(canvas)
    # Vibrant orange: #F48A26, Darker orange: #E66A12
    wedge_poly = [(740, 0), (W, 0), (W, 250)]
    wedge_draw.polygon(wedge_poly, fill=(244, 138, 38, 255))

    # 3. Left off-white content background & Orange diagonal band
    # Divider points
    # White polygon: (0,0) -> (580, 0) -> (660, 300) -> (450, content_h) -> (0, content_h)
    # Orange band width ~ 26px
    poly_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    poly_draw = ImageDraw.Draw(poly_layer)

    # Orange band polygon
    orange_poly = [
        (580, 0),
        (660, 300),
        (450, content_h),
        (478, content_h),
        (692, 300),
        (608, 0)
    ]
    poly_draw.polygon(orange_poly, fill=(244, 138, 38, 255))

    # Off-white content polygon (soft light gray #F5F6F8)
    white_poly = [
        (0, 0),
        (580, 0),
        (660, 300),
        (450, content_h),
        (0, content_h)
    ]
    poly_draw.polygon(white_poly, fill=(245, 246, 248, 255))

    canvas = Image.alpha_composite(canvas, poly_layer)
    draw = ImageDraw.Draw(canvas)

    # 4. Top-left property number ribbon
    if item_no:
        ribbon_h = 58
        ribbon_w = 260
        ribbon_poly = [
            (0, 0),
            (ribbon_w, 0),
            (ribbon_w - 35, ribbon_h),
            (0, ribbon_h)
        ]
        draw.polygon(ribbon_poly, fill=(244, 138, 38, 255))
        font_item = get_font("NanumGothicBold.ttf", 25)
        # Center text vertically in ribbon
        draw.text((32, 16), item_no, fill=(255, 255, 255, 255), font=font_item)

    # 5. Left Content: Titles and Feature
    left_x = 58
    font_main = get_font("NanumGothicExtraBold.ttf", 52)
    font_sub = get_font("NanumGothicExtraBold.ttf", 50)
    font_feat = get_font("NanumGothicBold.ttf", 36)

    # Main title
    draw.text((left_x, 140), main_title, fill=(18, 20, 22, 255), font=font_main)
    # Sub title
    draw.text((left_x, 212), sub_title, fill=(18, 20, 22, 255), font=font_sub)
    # Feature text
    draw.text((left_x, 288), feature_text, fill=(35, 38, 42, 255), font=font_feat)

    # 6. Transaction Type & Price Badge
    badge_y = 365
    badge_h = 56
    # Measure trade_type text width
    font_trade = get_font("NanumGothicExtraBold.ttf", 30)
    tb_box = draw.textbbox((0, 0), trade_type, font=font_trade)
    trade_text_w = tb_box[2] - tb_box[0]

    # Inner black pill width
    inner_pill_pad = 22
    inner_pill_w = max(90, trade_text_w + inner_pill_pad * 2)
    inner_pill_h = 44
    inner_pill_y = badge_y + (badge_h - inner_pill_h) // 2

    coin_w = 46
    coin_margin = 12
    total_badge_w = coin_margin + coin_w + 10 + inner_pill_w + 8
    badge_x = left_x

    # Draw outer orange pill
    draw.rounded_rectangle(
        [badge_x, badge_y, badge_x + total_badge_w, badge_y + badge_h],
        radius=badge_h // 2,
        fill=(244, 138, 38, 255)
    )

    # Draw or paste coin icon
    coin_x = badge_x + coin_margin
    coin_y = badge_y + (badge_h - coin_w) // 2
    if os.path.exists("asset_coin_raw.png"):
        coin_img = Image.open("asset_coin_raw.png").convert("RGBA")
        coin_resized = coin_img.resize((coin_w, coin_w), Image.Resampling.LANCZOS)
        canvas.paste(coin_resized, (coin_x, coin_y), coin_resized)
    else:
        # Fallback coin circle
        draw.ellipse([coin_x, coin_y, coin_x + coin_w, coin_y + coin_w], fill=(255, 195, 0, 255), outline=(220, 140, 0, 255), width=2)
        draw.text((coin_x + 14, coin_y + 8), "₩", fill=(120, 60, 0, 255), font=get_font("NanumGothicBold.ttf", 24))

    # Inner dark pill
    inner_x = coin_x + coin_w + 8
    draw.rounded_rectangle(
        [inner_x, inner_pill_y, inner_x + inner_pill_w, inner_pill_y + inner_pill_h],
        radius=inner_pill_h // 2,
        fill=(28, 30, 33, 255)
    )

    # Trade text inside inner pill (Vibrant Orange / Coral-red #FF5F15)
    trade_text_x = inner_x + (inner_pill_w - trade_text_w) // 2
    draw.text((trade_text_x, inner_pill_y + 6), trade_type, fill=(244, 138, 38, 255), font=font_trade)

    # Price Text next to badge
    price_x = badge_x + total_badge_w + 18
    font_price = get_font("NanumGothicExtraBold.ttf", 46)
    # Vertically align price text with badge
    draw.text((price_x, badge_y + 3), price_text, fill=(18, 20, 22, 255), font=font_price)

    # 7. 4 Spec lines with icons
    spec_start_y = 460
    spec_line_gap = 68
    icon_assets = [
        "asset_icon_calendar.png",
        "asset_icon_building.png",
        "asset_icon_bed.png",
        "asset_icon_sun.png"
    ]
    font_spec = get_font("NanumGothicBold.ttf", 34)

    for i, line_text in enumerate(spec_lines[:4]):
        cur_y = spec_start_y + i * spec_line_gap
        # Icon
        icon_path = icon_assets[i] if i < len(icon_assets) else None
        icon_x = left_x + 4
        icon_size = 40
        if icon_path and os.path.exists(icon_path):
            icon_img = Image.open(icon_path).convert("RGBA")
            # Preserve aspect ratio
            iw, ih = icon_img.size
            scale = min(icon_size / iw, icon_size / ih)
            niw, nih = int(iw * scale), int(ih * scale)
            icon_resized = icon_img.resize((niw, nih), Image.Resampling.LANCZOS)
            # Center in 40x40
            canvas.paste(icon_resized, (icon_x + (icon_size - niw) // 2, cur_y + (40 - nih) // 2), icon_resized)
        
        # Text
        text_x = icon_x + icon_size + 18
        draw.text((text_x, cur_y + 2), line_text, fill=(22, 24, 27, 255), font=font_spec)

    # 8. Fixed Bottom Bar
    bar_y1 = content_h
    bar_y2 = H
    # Dark charcoal background #232428
    draw.rectangle([0, bar_y1, W, bar_y2], fill=(35, 36, 40, 255))

    # Bottom bar contents: Logo + "참좋은공인중개사사무소 010-9667-4201"
    footer_text = "참좋은공인중개사사무소  010-9667-4201"
    font_footer = get_font("NanumGothicBold.ttf", 30)

    # Compute text width
    ft_box = draw.textbbox((0, 0), footer_text, font=font_footer)
    ft_w = ft_box[2] - ft_box[0]
    ft_h = ft_box[3] - ft_box[1]

    logo_h = 50
    logo_w = 50
    gap = 20

    has_logo = os.path.exists("asset_logo_clean.png")
    if has_logo:
        logo_img = Image.open("asset_logo_clean.png").convert("RGBA")
        lw, lh = logo_img.size
        logo_w = int(lw * (logo_h / lh))
        logo_resized = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)

    total_footer_w = (logo_w + gap if has_logo else 0) + ft_w
    start_footer_x = (W - total_footer_w) // 2

    if has_logo:
        logo_y = bar_y1 + (bottom_h - logo_h) // 2
        canvas.paste(logo_resized, (start_footer_x, logo_y), logo_resized)
        cur_text_x = start_footer_x + logo_w + gap
    else:
        cur_text_x = start_footer_x

    text_y = bar_y1 + (bottom_h - ft_h) // 2 - 2
    draw.text((cur_text_x, text_y), footer_text, fill=(255, 255, 255, 255), font=font_footer)

    # Save output
    rgb_out = canvas.convert("RGB")
    rgb_out.save(output_path, quality=98)
    print(f"Thumbnail saved successfully to {output_path} ({W}x{H})")
    return rgb_out

if __name__ == "__main__":
    create_thumbnail()
