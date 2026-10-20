"""
상가 썸네일 렌더러 테스트 스크립트 (임차 & 매매)
"""
import os
import io
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

def get_font(font_name: str, size: int) -> ImageFont.FreeTypeFont:
    paths = [
        os.path.join(ASSETS_DIR, "fonts", font_name),
        os.path.join(ASSETS_DIR, "fonts", "NanumGothicExtraBold.ttf"),
        os.path.join(ASSETS_DIR, "fonts", "NanumGothicBold.ttf"),
        os.path.join(ASSETS_DIR, "fonts", "NanumGothic.ttf"),
        f"C:/Windows/Fonts/{font_name}",
        "C:/Windows/Fonts/malgunbd.ttf",
        "C:/Windows/Fonts/malgun.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

def _load_bg(bg_image, target_w: int, target_h: int, zoom: float, offset_x: int, offset_y: int, default_filename: str) -> Image.Image:
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
        default_path = os.path.join(ASSETS_DIR, default_filename)
        if not os.path.exists(default_path):
            default_path = os.path.join(ASSETS_DIR, "sample_living_room.jpg")
        if os.path.exists(default_path):
            loaded = Image.open(default_path).convert("RGBA")
        else:
            loaded = Image.new("RGBA", (target_w, target_h), (25, 30, 42, 255))

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

    # 1. 배경 로드
    bg_cropped = _load_bg(bg_image, W, H, bg_zoom, bg_offset_x, bg_offset_y, "sample_comm_lease.jpg")
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
    # (1) 상단 서브 카피
    clean_cp_top = (catchphrase_top or "").strip()
    if clean_cp_top:
        font_cp_top = get_font("NanumGothicExtraBold.ttf", 44)
        bbox = font_cp_top.getbbox(clean_cp_top)
        tw = bbox[2] - bbox[0]
        tx = (W - tw) // 2 - bbox[0]
        ty = 195
        # 3D 섀도우
        draw.text((tx, ty + 3), clean_cp_top, fill=(0, 0, 0, 220), font=font_cp_top)
        draw.text((tx, ty), clean_cp_top, fill=(255, 255, 255, 255), font=font_cp_top)

    # (2) 메인 타이틀 (골드 3D 타이틀)
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

    # (3) 하단 서브 카피
    clean_cp_bot = (catchphrase_bot or "").strip()
    if clean_cp_bot:
        font_cp_bot = get_font("NanumGothicBold.ttf", 42)
        bbox = font_cp_bot.getbbox(clean_cp_bot)
        tw = bbox[2] - bbox[0]
        tx = (W - tw) // 2 - bbox[0]
        ty = 405
        draw.text((tx, ty + 3), clean_cp_bot, fill=(0, 0, 0, 200), font=font_cp_bot)
        draw.text((tx, ty), clean_cp_bot, fill=(228, 242, 255, 255), font=font_cp_bot)

    # 5. 중앙 골드 3D 핀 & "목 좋은 자리!" 말풍선 배지
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
            # 말풍선 캡슐
            bub_draw.rounded_rectangle([bub_x, bub_y, bub_x + bub_w, bub_y + bub_h], radius=bub_h // 2, fill=(22, 28, 38, 230), outline=(225, 175, 75, 255), width=2)
            # 말풍선 꼬리 (삼각형)
            tri_points = [(bub_x + bub_w - 6, bub_y + bub_h // 2 - 4), (bub_x + bub_w + 8, bub_y + bub_h // 2 + 6), (bub_x + bub_w - 12, bub_y + bub_h // 2 + 8)]
            bub_draw.polygon(tri_points, fill=(22, 28, 38, 230))
            bub_draw.line([(bub_x + bub_w - 6, bub_y + bub_h // 2 - 4), (bub_x + bub_w + 8, bub_y + bub_h // 2 + 6)], fill=(225, 175, 75, 255), width=2)
            bub_draw.line([(bub_x + bub_w + 8, bub_y + bub_h // 2 + 6), (bub_x + bub_w - 12, bub_y + bub_h // 2 + 8)], fill=(225, 175, 75, 255), width=2)

            canvas = Image.alpha_composite(canvas, bub_layer)
            draw = ImageDraw.Draw(canvas)

            # 말풍선 텍스트
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

    # 카드 레이어
    card_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd_draw = ImageDraw.Draw(card_layer)

    # 글래스모피즘 어두운 바탕
    cd_draw.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=18, fill=(18, 24, 38, 230), outline=(218, 168, 68, 140), width=2)
    # 상단 하이라이트 라인
    cd_draw.line([(card_x1 + 25, card_y1 + 2), (card_x2 - 25, card_y1 + 2)], fill=(255, 255, 255, 90), width=1)

    canvas = Image.alpha_composite(canvas, card_layer)
    draw = ImageDraw.Draw(canvas)

    # 카드 1행 텍스트 (전용 평수 | 보증금 / 월세)
    clean_sp1 = (spec_line1 or "").strip()
    if clean_sp1:
        # " | " 분할 여부 확인
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

            # 왼쪽 (전용면적) - 주황/골드
            draw.text((sx - bbox_l[0], sy), left_txt, fill=(244, 150, 48, 255), font=font_p1_bold)
            # 구분자 ( | ) - 연회색
            draw.text((sx + wl - bbox_d[0], sy), div_txt, fill=(170, 185, 205, 255), font=font_p1)
            # 오른쪽 (금액) - 보증금/월세 화이트&골드
            draw.text((sx + wl + wd - bbox_r[0], sy), right_txt, fill=(255, 255, 255, 255), font=font_p1_bold)
        else:
            bbox = font_p1_bold.getbbox(clean_sp1)
            tw = bbox[2] - bbox[0]
            draw.text(((W - tw) // 2 - bbox[0], card_y1 + 42), clean_sp1, fill=(255, 255, 255, 255), font=font_p1_bold)

    # 카드 2행 텍스트 (추천 업종)
    clean_sp2 = (spec_line2 or "").strip()
    if clean_sp2:
        font_sp2 = get_font("NanumGothicBold.ttf", 29)
        bbox = font_sp2.getbbox(clean_sp2)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) // 2 - bbox[0], card_y1 + 108), clean_sp2, fill=(235, 240, 248, 255), font=font_sp2)

    # 7. 하단 풋터 바 (골드 라인 + 다크 네이비 + 사무소/소장명)
    if show_footer:
        footer_y = 985
        footer_h = 95

        # 배경
        draw.rectangle([(0, footer_y), (W, H)], fill=(12, 16, 22, 255))
        # 상단 골드 헤어라인 (2px)
        draw.line([(0, footer_y), (W, footer_y)], fill=(218, 168, 68, 255), width=2)
        # 하단 미세 골드 라인
        draw.line([(0, H - 3), (W, H - 3)], fill=(218, 168, 68, 180), width=2)

        # 좌측: 로고 + 상호
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

        # 우측: 황금터잡이 신소장
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

    # 1. 배경 로드
    bg_cropped = _load_bg(bg_image, W, H, bg_zoom, bg_offset_x, bg_offset_y, "sample_comm_sale.jpg")
    canvas.paste(bg_cropped, (0, 0))

    # 2. 배경 밸런싱 오버레이 (약간의 어두운 비네트)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    # 상단 약간 톤다운
    for y in range(0, 260):
        alpha = int(140 * (1.0 - (y / 260) ** 1.2))
        ov_draw.line([(0, y), (W, y)], fill=(12, 16, 24, alpha))
    # 하단 약간 톤다운
    for y in range(650, H):
        ratio = (y - 650) / (H - 650)
        alpha = int(180 * (ratio ** 0.8))
        ov_draw.line([(0, y), (W, y)], fill=(12, 16, 24, alpha))
    canvas = Image.alpha_composite(canvas, overlay)
    draw = ImageDraw.Draw(canvas)

    # 3. 럭셔리 더블 골드 프레임 테두리 (외곽 36px, 내부 45px)
    frame_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    fr_draw = ImageDraw.Draw(frame_layer)

    gold_color = (218, 168, 68, 255)
    gold_dim = (218, 168, 68, 160)

    # 외곽 프레임
    fr_draw.rectangle([34, 34, W - 34, H - 34], outline=gold_color, width=3)
    # 내부 프레임
    fr_draw.rectangle([44, 44, W - 44, H - 44], outline=gold_dim, width=2)

    # 4개 코너 장식 사각형 (8x8)
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
        # 골드 블록
        if b_left:
            draw.rectangle([cur_x, badge_y, cur_x + bw_left, badge_y + badge_h], fill=(225, 175, 75, 255))
            tx = cur_x + pad_x - bbox_l[0]
            ty = badge_y + (badge_h - (bbox_l[3] - bbox_l[1])) // 2 - bbox_l[1]
            draw.text((tx, ty), b_left, fill=(18, 20, 24, 255), font=font_b1)
            cur_x += bw_left

        # 다크 블록
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
    chart_path = os.path.join(ASSETS_DIR, "icon_gold_chart.png")
    if os.path.exists(chart_path):
        ch_img = Image.open(chart_path).convert("RGBA")
        ch_h = 85
        ch_w = int(ch_img.width * (ch_h / ch_img.height))
        ch_resized = ch_img.resize((ch_w, ch_h), Image.Resampling.LANCZOS)
        canvas.paste(ch_resized, (W - 75 - ch_w, 65), ch_resized)

    # 6. 중앙 다크 히어로 블록 (확정 수익률 & 알짜 상가 매매)
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

    # 1행 (수익률 하이라이트 - 대형 골드 텍스트)
    clean_hl = (main_highlight_title or "").strip()
    if clean_hl:
        font_hl = get_font("NanumGothicExtraBold.ttf", 74)
        bbox = font_hl.getbbox(clean_hl)
        tw = bbox[2] - bbox[0]
        tx = (W - tw) // 2 - bbox[0]
        ty = box_y1 + 35
        # 3D 섀도우
        draw.text((tx, ty + 4), clean_hl, fill=(0, 0, 0, 230), font=font_hl)
        draw.text((tx, ty), clean_hl, fill=(245, 197, 66, 255), font=font_hl)

    # 2행 (메인 타이틀 - 선명한 볼드 화이트)
    clean_sub = (main_sub_title or "").strip()
    if clean_sub:
        font_sub = get_font("NanumGothicExtraBold.ttf", 64)
        bbox = font_sub.getbbox(clean_sub)
        tw = bbox[2] - bbox[0]
        tx = (W - tw) // 2 - bbox[0]
        ty = box_y1 + 135
        draw.text((tx, ty + 3), clean_sub, fill=(0, 0, 0, 220), font=font_sub)
        draw.text((tx, ty), clean_sub, fill=(255, 255, 255, 255), font=font_sub)

    # 7. 하단 스펙 인포 바 (매매가 | 보증금/월수익 | 실투자금)
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
        # 상하 골드 헤어라인
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

        # 상단 골드 헤어라인
        draw.line([(60, footer_y), (W - 60, footer_y)], fill=(218, 168, 68, 255), width=2)

        # 좌측: 로고 + 상호
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

        # 우측: 황금터잡이 신소장
        font_broker = get_font("NanumGothicExtraBold.ttf", 30)
        broker_txt = (broker_title or "황금터잡이 신소장").strip()
        b_box = font_broker.getbbox(broker_txt)
        br_w = b_box[2] - b_box[0]
        draw.text((W - 75 - br_w, footer_y + 27), broker_txt, fill=(235, 182, 75, 255), font=font_broker)

    return canvas.convert("RGB")

if __name__ == "__main__":
    img_lease = render_commercial_lease_thumbnail()
    img_lease.save("test_comm_lease_out.png")
    print("Lease thumbnail saved!")

    img_sale = render_commercial_sale_thumbnail()
    img_sale.save("test_comm_sale_out.png")
    print("Sale thumbnail saved!")
