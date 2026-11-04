"""
공적서류(건축물대장 표제부/전유부, 일반건축물대장, 토지대장, 토지이용계획확인원) 정밀 분석 모듈
- 집합건축물대장 표제부 (총괄표제부 / 표제부) 정밀 파싱
- 집합건축물대장 전유부 (전유부분 / 공용부분) 정밀 파싱
- 표제부 + 전유부 지능형 자동 병합 (Merge) 시스템
- 일반건축물대장 / 토지대장 / 토지이용계획확인서 파싱
"""

import re
import io
import os
import sys
import tempfile
import subprocess
from typing import Dict, Any, Tuple, Optional, List

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    import pypdfium2
    HAS_PYPDFIUM2 = True
except ImportError:
    HAS_PYPDFIUM2 = False

try:
    import pytesseract
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False


def _ocr_images_windows_native(image_paths: List[str]) -> List[str]:
    """Windows 10/11 내장 한국어 OCR 엔진(Windows.Media.Ocr)을 사용하여 이미지 리스트에서 고속으로 텍스트를 추출합니다."""
    if sys.platform != "win32" or not image_paths:
        return []
    ps_paths = ", ".join([f"'{p.replace(chr(39), chr(39)*2)}'" for p in image_paths])
    ps_script = f"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Foundation.IAsyncOperation`1,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Globalization.Language,Windows.Foundation,ContentType=WindowsRuntime]

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {{ $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' }})[0]
Function Await($WinRtTask, $ResultType) {{
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}}

$lang = New-Object Windows.Globalization.Language('ko')
$ocrEngine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
if (-not $ocrEngine) {{ exit 1 }}

foreach ($imgPath in @({ps_paths})) {{
    Write-Output "===PAGE_SEP==="
    $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($imgPath)) ([Windows.Storage.StorageFile])
    $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $result = Await ($ocrEngine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    $words = @()
    foreach ($line in $result.Lines) {{
        foreach ($w in $line.Words) {{
            $words += [PSCustomObject]@{{ Text = $w.Text; X = $w.BoundingRect.X; Y = $w.BoundingRect.Y }}
        }}
    }}
    $sorted = $words | Sort-Object {{ [Math]::Round($_.Y / 18.0) }}, X
    $curRow = -999
    $rowWords = @()
    foreach ($w in $sorted) {{
        $r = [Math]::Round($w.Y / 18.0)
        if ($r -ne $curRow) {{
            if ($rowWords.Count -gt 0) {{ Write-Output ($rowWords -join ' ') }}
            $curRow = $r
            $rowWords = @($w.Text)
        }} else {{
            $rowWords += $w.Text
        }}
    }}
    if ($rowWords.Count -gt 0) {{ Write-Output ($rowWords -join ' ') }}
    $stream.Dispose()
}}
"""
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=25
        )
        if proc.returncode == 0 and "===PAGE_SEP===" in proc.stdout:
            chunks = proc.stdout.split("===PAGE_SEP===")[1:]
            return [c.strip() for c in chunks if c.strip()]
    except Exception:
        pass
    return []


def _extract_pages_via_ocr(pdf_bytes: bytes) -> List[str]:
    """정부24/세움터 보안 인쇄(벡터 아웃라인/이미지) PDF를 고해상도 이미지로 렌더링한 뒤 OCR로 텍스트를 추출합니다."""
    if not HAS_PYPDFIUM2 or not pdf_bytes:
        return []
    pages_ocr = []
    temp_files = []
    try:
        doc = pypdfium2.PdfDocument(pdf_bytes)
        num_pages = min(len(doc), 5)
        pil_images = []
        for idx in range(num_pages):
            pil_img = doc[idx].render(scale=2.2).to_pil()
            pil_images.append(pil_img)

        # 1순위: Windows 내장 한국어 OCR (초고속·무설치)
        if sys.platform == "win32":
            for idx, p_img in enumerate(pil_images):
                tf = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                tf.close()
                p_img.save(tf.name, format="PNG")
                temp_files.append(tf.name)
            win_res = _ocr_images_windows_native(temp_files)
            if win_res and sum(len(x) for x in win_res) > 30:
                return win_res

        # 2순위: pytesseract (Streamlit Cloud / Linux 환경 지원)
        if HAS_PYTESSERACT:
            for p_img in pil_images:
                try:
                    txt = pytesseract.image_to_string(p_img, lang="kor+eng")
                    if txt and txt.strip():
                        pages_ocr.append(txt.strip())
                except Exception:
                    pass
    except Exception:
        pass
    finally:
        for tf_path in temp_files:
            try:
                if os.path.exists(tf_path):
                    os.remove(tf_path)
            except Exception:
                pass
    return pages_ocr


def extract_pages_text_from_pdf(pdf_file) -> List[str]:
    """PDF 파일에서 페이지별 텍스트 및 표 내용을 추출하며, 보안/이미지 PDF인 경우 자동으로 OCR 분석을 수행합니다."""
    pdf_bytes = None
    if isinstance(pdf_file, (str, bytes)):
        if isinstance(pdf_file, str) and os.path.exists(pdf_file):
            with open(pdf_file, "rb") as f:
                pdf_bytes = f.read()
        elif isinstance(pdf_file, bytes):
            pdf_bytes = pdf_file
    elif hasattr(pdf_file, "getvalue"):
        try:
            pdf_bytes = pdf_file.getvalue()
        except Exception:
            pass
    elif hasattr(pdf_file, "read"):
        try:
            if hasattr(pdf_file, "seek"):
                pdf_file.seek(0)
            pdf_bytes = pdf_file.read()
            if hasattr(pdf_file, "seek"):
                pdf_file.seek(0)
        except Exception:
            pass

    # 1단계: pypdfium2로 초고속 텍스트 유무 사전 점검 (벡터 곡선만 있는 보안 PDF에서 pdfplumber가 15초간 멈추는 현상 원천 차단)
    fast_texts = []
    if HAS_PYPDFIUM2 and pdf_bytes:
        try:
            doc = pypdfium2.PdfDocument(pdf_bytes)
            for i in range(len(doc)):
                t_fast = (doc[i].get_textpage().get_text_range() or "").strip()
                if t_fast:
                    fast_texts.append(t_fast)
        except Exception:
            pass

    total_fast_chars = sum(len(t) for t in fast_texts)
    # 페이지 번호('1 / 4 100%')만 있거나 텍스트가 아예 없는 정부24 보안/이미지 PDF인 경우 즉시 OCR 엔진 가동!
    if pdf_bytes and total_fast_chars < 45:
        ocr_pages = _extract_pages_via_ocr(pdf_bytes)
        if ocr_pages:
            return ocr_pages

    # 2단계: 일반 텍스트 PDF인 경우 pdfplumber로 정밀 추출
    pages_text = []
    if HAS_PDFPLUMBER:
        try:
            target_obj = io.BytesIO(pdf_bytes) if pdf_bytes else pdf_file
            with pdfplumber.open(target_obj) as pdf:
                for page in pdf.pages:
                    if len(page.chars) < 15:
                        continue
                    t = page.extract_text() or ""
                    table_lines = []
                    try:
                        tables = page.extract_tables()
                        for table in tables:
                            for row in table:
                                clean_row = [str(c).strip().replace("\n", " ") for c in row if c is not None and str(c).strip()]
                                if clean_row:
                                    table_lines.append(" | ".join(clean_row))
                    except Exception:
                        pass
                    combined_page = (t + "\n" + "\n".join(table_lines)).strip()
                    if combined_page:
                        pages_text.append(combined_page)
        except Exception:
            pass

    if not pages_text and fast_texts:
        return fast_texts

    if not pages_text and pdf_bytes:
        return _extract_pages_via_ocr(pdf_bytes)

    return pages_text


def extract_text_from_pdf(pdf_file) -> str:
    """PDF 파일(BytesIO 또는 파일경로)에서 전체 텍스트를 추출합니다."""
    pages = extract_pages_text_from_pdf(pdf_file)
    return "\n--- PAGE BREAK ---\n".join(pages)


def identify_document_type(text: str) -> str:
    """텍스트 내용을 분석하여 서류 유형을 정밀 감지합니다."""
    text_condensed = text.replace(" ", "")
    
    is_jeon = any(k in text_condensed for k in ["전유부", "전유부분", "호명칭", "공용부분", "전유면적"])
    is_pyo = any(k in text_condensed for k in ["총괄표제부", "표제부", "총주차대수", "세대수", "가구수"])
    is_bldg = any(k in text_condensed for k in ["건축물대장", "대지위치", "건축물명칭", "허가일", "사용승인일", "주구조", "도로명주소", "주용도"])
    
    if (is_jeon and is_pyo) or ("건축물대장" in text_condensed and is_jeon and is_pyo):
        return "집합건축물대장 (표제부+전유부 복합)"
    elif is_jeon:
        return "집합건축물대장 (전유부)"
    elif is_pyo:
        if "총괄표제부" in text_condensed:
            return "집합건축물대장 (총괄표제부)"
        return "집합건축물대장 (표제부)"
    elif "건축물대장" in text_condensed or is_bldg:
        return "일반건축물대장"
    elif "토지대장" in text_condensed or "임야대장" in text_condensed:
        return "토지대장"
    elif "토지이용계획" in text_condensed:
        return "토지이용계획확인원"
    
    return "기타 공적서류"


# 다음 필드 키워드 패턴 (필드 끝 경계 인식 - 값 내부의 '구조' 단어가 잘리지 않도록 콜론/구분자가 있는 경우만 매칭)
NEXT_KW = r"(?=\s*(?:대지위치|도로명주소|지번\s*[:|]|건축물명칭|명칭\s*[:|]|동명칭|호명칭|주용도|용도\s*[:|]|층수\s*[:|]|사용승인일|허가일|착공일|준공일|주차장\s*[:|]|총주차대수|세대수\s*[:|]|가구수\s*[:|]|주구조\s*[:|]|구조\s*[:|]|지역\s*[:|]|지구\s*[:|]|구역\s*[:|]|소재지|지목\s*[:|]|면적\s*[:|]|개별공시지가|소유자|국토의|$))"


def clean_val(s: str) -> str:
    """추출된 값에서 불필요한 기호, 콜론, 공백, 파이프 등을 정리합니다."""
    if not s:
        return ""
    s = s.strip()
    s = re.sub(r"^[:|\-=>\s]+", "", s)
    s = re.sub(r"[:|\-=>\s]+$", "", s)
    return s.strip()


def _extract_korean_addresses_fallback(text: str) -> Tuple[str, str]:
    """정부24 표 OCR 텍스트에서 지번주소와 도로명주소를 정밀 추출합니다."""
    jibun_addr = ""
    road_addr = ""
    sido_pat = r"(?:서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|울산광역시|세종특별자치시|경기도|강원특별자치도|강원도|충청북도|충청남도|전북특별자치도|전라북도|전라남도|경상북도|경상남도|제주특별자치도|서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)"
    # 도로명주소 패턴 (예: 부산광역시 사상구 사상로 300 (덕포동))
    r_m = re.search(sido_pat + r"\s+[가-힣]+[시군구]\s+(?:[가-힣]+[구읍면]\s+)?[가-힣0-9\-]+(?:로|길)\s*\d+(?:-\d+)?(?:\s*\([^)]+\))?", text)
    if r_m:
        road_addr = clean_val(r_m.group(0))
    # 지번주소 패턴 (예: 부산광역시 사상구 덕포동 795)
    j_m = re.search(sido_pat + r"\s+[가-힣]+[시군구]\s+(?:[가-힣]+[구읍면]\s+)?[가-힣\s]{1,10}?(?:동|리|가)\s+\d+(?:-\d+)?", text)
    if j_m:
        cand = re.sub(r"\s+", " ", clean_val(j_m.group(0)))
        # '덕 포동' 같이 OCR에서 띄어쓰기된 동 이름 정규화
        cand = re.sub(r"([가-힣])\s+([가-힣]+(?:동|리|가)\s+\d+)", r"\1\2", cand)
        jibun_addr = cand
    return jibun_addr, road_addr


def _is_header_noise(val: str) -> bool:
    """추출된 문자열이 실제 값이 아니라 표 헤더 라벨인지 판별합니다."""
    if not val:
        return True
    v_clean = val.replace(" ", "")
    noise_tokens = ["지번", "도로명주소", "호수가구수", "세대수", "고유번호", "건물ID", "호명칭", "호명침", "관련주소"]
    return any(nt in v_clean for nt in noise_tokens)


def parse_building_register_title(text: str) -> Dict[str, Any]:
    """
    [표제부 전문 파서] 집합건축물대장 표제부/총괄표제부에서 건물 전체 핵심 스펙 추출
    """
    res = {}
    # OCR 오인식 보정 (예: '1 10동' -> '110동', '36증' -> '36층')
    text = re.sub(r"(\d)\s+(\d{1,2}동)", r"\1\2", text)
    text = re.sub(r"(\d+)\s*증\b", r"\1층", text)

    # 1. 소재지 / 도로명주소 / 대지위치
    loc_match = re.search(r"(?:대지위치|대지\s*위치|소재지)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    road_match = re.search(r"(?:도로명주소|도로명\s*주소)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    jibun_match = re.search(r"(?:지번|지\s*번)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)

    loc_val = clean_val(loc_match.group(1)) if loc_match else ""
    road_val = clean_val(road_match.group(1)) if road_match else ""
    jibun_val = clean_val(jibun_match.group(1)) if jibun_match else ""

    if _is_header_noise(loc_val):
        loc_val = ""
    if _is_header_noise(road_val):
        road_val = ""
    if _is_header_noise(jibun_val) or not re.search(r"\d", jibun_val):
        jibun_val = ""

    fb_jibun, fb_road = _extract_korean_addresses_fallback(text)
    if not loc_val and fb_jibun:
        loc_val = fb_jibun
    if not road_val and fb_road:
        road_val = fb_road

    building_name = ""
    b_match = re.search(r"(?:건축물명칭|건축물\s*명칭|명칭)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if b_match:
        cand_b = clean_val(b_match.group(1))
        cand_b = re.sub(r"(?:호수|가구수|세대수|호명칭|호명\s*침).*$", "", cand_b).strip()
        if cand_b and not _is_header_noise(cand_b) and len(cand_b) >= 2:
            building_name = cand_b

    dong_name = ""
    d_match = re.search(r"(?:동명칭및호명칭|동명칭|동\s*명칭)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if d_match:
        cand_d = clean_val(d_match.group(1))
        if not _is_header_noise(cand_d):
            dong_name = cand_d
    if not dong_name:
        d_found = re.search(r"\b(\d{3,4}동|제\s*\d{3,4}동)\b", text)
        if d_found:
            dong_name = d_found.group(1).replace(" ", "")

    base_addr = loc_val or road_val
    if jibun_val and loc_val and jibun_val not in loc_val:
        base_addr = f"{loc_val} {jibun_val}".strip()

    title_addons = []
    if building_name:
        title_addons.append(building_name)
    if dong_name and (not building_name or dong_name not in building_name):
        title_addons.append(dong_name)

    if title_addons:
        res["location"] = f"{base_addr} ({' '.join(title_addons)})" if base_addr else " ".join(title_addons)
    elif base_addr:
        res["location"] = base_addr

    if road_val:
        res["road_address"] = road_val
    if loc_val:
        res["jibun_address"] = loc_val
    if building_name:
        res["building_name"] = building_name
        res["main_title"] = building_name
    if dong_name:
        res["dong_name"] = dong_name
        res["sub_title"] = dong_name

    # 2. 층수
    floor_match = re.search(r"지상\s*[:.]?\s*(\d+)\s*층(?:\s*[/|,\s]\s*지하\s*[:.]?\s*(\d+)\s*층)?", text)
    if not floor_match:
        floor_match = re.search(r"(\d+)\s*층\s*[/|]\s*지하\s*(\d+)\s*층", text)
    
    if floor_match:
        high_fl = floor_match.group(1)
        under_fl = floor_match.group(2)
        res["max_floor"] = f"{high_fl}층"
        if under_fl:
            res["floor_info"] = f"총 {high_fl}층 (지하 {under_fl}층)"
        else:
            res["floor_info"] = f"총 {high_fl}층"
    else:
        fl_single = re.search(r"(?:층수|지상층수|지상\s*[:.])\s*[:|]?\s*(\d+)\s*층?", text)
        if fl_single:
            res["max_floor"] = f"{fl_single.group(1)}층"
            res["floor_info"] = f"총 {fl_single.group(1)}층"

    # 3. 주차대수
    park_match = re.search(r"(?:주차장|총주차대수|주차대수)\s*[:|]?\s*([^\n\r]+?)" + NEXT_KW, text)
    if park_match:
        p_raw = park_match.group(1)
        p_nums = re.findall(r"([\d,]+)\s*대", p_raw)
        if p_nums:
            total_pk = p_nums[-1].replace(",", "")
            res["parking"] = f"총 {total_pk}대"
            if "자주식" in p_raw:
                res["parking"] += " (자주식)"
        else:
            clean_pk = clean_val(p_raw)
            if clean_pk and any(c.isdigit() for c in clean_pk) and not _is_header_noise(clean_pk) and "승강기" not in clean_pk:
                res["parking"] = clean_pk

    if not res.get("parking"):
        p_alt = re.search(r"총\s*([\d,]+)\s*대", text)
        if p_alt:
            res["parking"] = f"총 {p_alt.group(1)}대"

    # 4. 세대수 / 가구수 (정부24 '0호/0가구/192세대' 형식 포함)
    hh_slash = re.search(r"\d+\s*호\s*/\s*\d+\s*[가-힣]*\s*/?\s*([\d,]+)\s*세", text)
    hh_match = re.search(r"(?:세대수|세대\s*수)\s*[:|]?\s*([\d,]+)\s*세대", text)
    if hh_slash:
        res["households"] = f"총 {hh_slash.group(1)}세대"
    elif hh_match:
        res["households"] = f"총 {hh_match.group(1)}세대"
    else:
        hh_any = re.search(r"([\d,]+)\s*세대", text)
        if hh_any:
            res["households"] = f"총 {hh_any.group(1)}세대"
        else:
            ga_match = re.search(r"(?:가구수|가구\s*수)\s*[:|]?\s*([\d,]+)\s*가구", text)
            if ga_match and ga_match.group(1) != "0":
                res["households"] = f"총 {ga_match.group(1)}가구"

    if res.get("parking") and res.get("households"):
        try:
            pk_cnt = int(re.sub(r"[^\d]", "", res["parking"]))
            hh_cnt = int(re.sub(r"[^\d]", "", res["households"]))
            if hh_cnt > 0:
                per_hh = round(pk_cnt / hh_cnt, 2)
                res["parking"] = f"총 {pk_cnt:,}대 (세대당 {per_hh}대)"
        except Exception:
            pass

    # 5. 사용승인일 (표 줄바꿈 및 변동사항 '준공인가' 일자까지 모두 감지)
    app_match = re.search(r"사용\s*승인일[\s\S]{0,60}?(\d{4}[.\-년\s]+\d{1,2}[.\-월\s]+\d{1,2}일?)", text)
    if not app_match:
        app_match = re.search(r"\((\d{4}[.\-]\d{1,2}[.\-]\d{1,2})\.?\)[^\n\r]*?준공인가", text)
    if not app_match:
        date_pattern = r"\b(\d{4}[.\-]\d{1,2}[.\-]\d{1,2})\b"
        all_dates = re.findall(date_pattern, text)
        if "사용승인일" in text and len(all_dates) >= 3:
            parts = re.findall(r"\d+", all_dates[2])
            if len(parts) >= 3:
                res["approval_date"] = f"{parts[0]}년 {int(parts[1]):02d}월 {int(parts[2]):02d}일"
    else:
        raw_date = app_match.group(1).strip()
        date_nums = re.findall(r"\d+", raw_date)
        if len(date_nums) >= 3:
            res["approval_date"] = f"{date_nums[0]}년 {int(date_nums[1]):02d}월 {int(date_nums[2]):02d}일"
        else:
            res["approval_date"] = raw_date

    # 6. 주구조 (철근콘크리트구조 등)
    struct_match = re.search(r"(?:주구조|주\s*구조|구조)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if struct_match:
        res["structure"] = clean_val(struct_match.group(1))
    else:
        common_structs = [
            "철골철근콘크리트구조", "철근콘크리트구조", "철골콘크리트구조", "일반철골구조",
            "경량철골구조", "철골구조", "철골조", "조적조", "벽돌구조", "연와조", "목구조"
        ]
        for cs in common_structs:
            if cs in text:
                res["structure"] = cs
                break

    # 7. 용도지역 및 용도지구/구역 (상가 핵심 법적 표기 항목)
    region_match = re.search(r"(?:용도지역|지역\s*[:|]|지역명)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if region_match:
        res["zone_region"] = clean_val(region_match.group(1))
    else:
        common_regions = [
            "중심상업지역", "일반상업지역", "근린상업지역", "유통상업지역",
            "준주거지역", "제1종전용주거지역", "제2종전용주거지역",
            "제1종일반주거지역", "제2종일반주거지역", "제3종일반주거지역",
            "전용공업지역", "일반공업지역", "준공업지역",
            "보전녹지지역", "생산녹지지역", "자연녹지지역", "계획관리지역"
        ]
        for cr in common_regions:
            if cr in text:
                res["zone_region"] = cr
                break

    district_match = re.search(r"(?:용도지구|지구\s*[:|]|구역\s*[:|])\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if district_match:
        res["zone_district"] = clean_val(district_match.group(1))
    else:
        common_districts = ["방화지구", "지구단위계획구역", "시가지경관지구", "상대보호구역", "절대보호구역", "역점관리구역", "과밀억제권역"]
        found_dist = [cd for cd in common_districts if cd in text]
        if found_dist:
            res["zone_district"] = ", ".join(found_dist)

    # 8. 승강기 (엘리베이터)
    elev_match = re.search(r"(?:승강기|엘리베이터|승용|비상용)\s*[:|]?\s*([^\n\r]+?)" + NEXT_KW, text)
    if elev_match:
        res["elevator"] = clean_val(elev_match.group(1))
    else:
        elev_num = re.search(r"승용\s*(\d+)\s*대", text)
        if elev_num:
            res["elevator"] = f"승강기 {elev_num.group(1)}대 완비"

    # 9. 주용도
    use_match = re.search(r"(?:주용도|주\s*용도)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if use_match:
        res["building_use"] = clean_val(use_match.group(1))
    else:
        if "근린생활시설" in text or "상가" in text:
            res["building_use"] = "제1종 및 제2종 근린생활시설"
        elif "아파트" in text:
            res["building_use"] = "공동주택 (아파트)"
        elif "오피스텔" in text:
            res["building_use"] = "업무시설 (오피스텔)"
        elif "다세대" in text or "연립" in text:
            res["building_use"] = "공동주택 (다세대/연립)"

    # 10. 연면적
    yeon_match = re.search(r"(?:연면적|연\s*면적)\s*[:|]?\s*([\d,.]+)", text)
    if yeon_match:
        res["area_total"] = yeon_match.group(1).replace(",", "").strip()

    return res


def parse_building_register_exclusive(text: str) -> Dict[str, Any]:
    """
    [전유부 전문 파서] 집합건축물대장 전유부에서 개별 호실 핵심 스펙 정밀 추출
    """
    res = {}
    # OCR 오인식 보정 (예: '1 10동' -> '110동', '36증' -> '36층')
    text = re.sub(r"(\d)\s+(\d{1,2}동)", r"\1\2", text)
    text = re.sub(r"(\d+)\s*증\b", r"\1층", text)

    # 1. 소재지 / 대지위치 / 도로명
    loc_match = re.search(r"(?:대지위치|대지\s*위치|소재지)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    road_match = re.search(r"(?:도로명주소|도로명\s*주소)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    jibun_match = re.search(r"(?:지번|지\s*번)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)

    loc_val = clean_val(loc_match.group(1)) if loc_match else ""
    road_val = clean_val(road_match.group(1)) if road_match else ""
    jibun_val = clean_val(jibun_match.group(1)) if jibun_match else ""

    if _is_header_noise(loc_val):
        loc_val = ""
    if _is_header_noise(road_val):
        road_val = ""
    if _is_header_noise(jibun_val) or not re.search(r"\d", jibun_val):
        jibun_val = ""

    fb_jibun, fb_road = _extract_korean_addresses_fallback(text)
    if not loc_val and fb_jibun:
        loc_val = fb_jibun
    if not road_val and fb_road:
        road_val = fb_road

    building_name = ""
    b_match = re.search(r"(?:건축물명칭|건축물\s*명칭|명칭)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if b_match:
        cand_b = clean_val(b_match.group(1))
        cand_b = re.sub(r"(?:호수|가구수|세대수|호명칭|호명\s*침).*$", "", cand_b).strip()
        if cand_b and not _is_header_noise(cand_b) and len(cand_b) >= 2:
            building_name = cand_b

    dong_name = ""
    ho_name = ""

    d_match = re.search(r"(?:동명칭및호명칭|동명칭|동\s*명칭)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if d_match:
        d_raw = clean_val(d_match.group(1))
        if not _is_header_noise(d_raw):
            dong_part = re.search(r"(\d+동|제\s*\d+동)", d_raw)
            ho_part = re.search(r"(\d+호|제\s*\d+호)", d_raw)
            if dong_part:
                dong_name = dong_part.group(1).replace(" ", "")
            if ho_part:
                ho_name = ho_part.group(1).replace(" ", "")
            if not dong_name and not ho_name:
                dong_name = d_raw

    h_match = re.search(r"(?:호명칭|호\s*명칭)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if h_match:
        cand_h = clean_val(h_match.group(1))
        if not _is_header_noise(cand_h):
            ho_name = cand_h if "호" in cand_h else f"{cand_h}호"

    if not dong_name:
        d_found = re.search(r"(\d{3,4}동|제\s*\d{3,4}동)", text)
        if d_found:
            dong_name = d_found.group(1).replace(" ", "")
    if not ho_name:
        h_found = re.search(r"(?<![-\w])(\d{3,4}호|제\s*\d{3,4}호)", text)
        if h_found:
            ho_name = h_found.group(1).replace(" ", "")
        else:
            # '110동 405' 처럼 동 뒤에 3~4자리 호수 숫자가 오는 경우
            dh_found = re.search(r"\d{3,4}동\s+(\d{3,4})\b", text)
            if dh_found:
                ho_name = f"{dh_found.group(1)}호"

    base_addr = loc_val or road_val
    if jibun_val and loc_val and jibun_val not in loc_val:
        base_addr = f"{loc_val} {jibun_val}".strip()

    # 중복 토큰 방지
    sub_parts = []
    if building_name:
        sub_parts.append(building_name)
    if dong_name and (not building_name or dong_name not in building_name):
        sub_parts.append(dong_name)
    if ho_name and (not building_name or ho_name not in building_name):
        sub_parts.append(ho_name)

    if sub_parts:
        res["location"] = f"{base_addr} ({' '.join(sub_parts)})" if base_addr else " ".join(sub_parts)
    elif base_addr:
        res["location"] = base_addr

    if road_val:
        res["road_address"] = road_val
    if loc_val:
        res["jibun_address"] = loc_val
    if building_name:
        res["building_name"] = building_name
        res["main_title"] = building_name
    if dong_name or ho_name:
        res["dong_name"] = dong_name
        res["ho_name"] = ho_name
        res["sub_title"] = f"{dong_name} {ho_name}".strip()

    # 2. 면적 정밀 파싱 (라인 단위 전유부분 vs 공용부분 분석 + OCR 폴백)
    exclusive_area = 0.0
    common_area = 0.0

    lines = text.split("\n")
    current_section = None  # "exclusive" or "common"

    for line in lines:
        line_clean = line.replace(" ", "")
        if ("전유부분" in line_clean or "전유부면적" in line_clean) and "경계벽" not in line_clean:
            current_section = "exclusive"
        elif "공용부분" in line_clean:
            current_section = "common"
        elif "소유자현황" in line_clean or "변동사항" in line_clean:
            current_section = None

        if current_section == "exclusive":
            num_matches = re.findall(r"([\d,]+\.\d{2,4})", line)
            if num_matches and exclusive_area == 0.0:
                try:
                    exclusive_area = float(num_matches[0].replace(",", ""))
                except Exception:
                    pass

        elif current_section == "common":
            is_res_comm = any(k in line for k in ["계단", "복도", "승강기", "엘리베이터", "홀", "주거공용", "현관", "벽체"]) and "외부계단" not in line_clean
            if is_res_comm:
                num_matches = re.findall(r"([\d,]+\.\d{2,4})", line)
                if num_matches:
                    try:
                        common_area += float(num_matches[0].replace(",", ""))
                    except Exception:
                        pass

    # OCR에서 '전유부분'/'공용부분' 섹션 헤더가 생략된 경우 라인 패턴 폴백
    if exclusive_area == 0.0:
        for line in lines:
            if any(u in line for u in ["공동주택", "아파트", "오피스텔", "근린생활", "다가구", "다세대"]):
                num_matches = re.findall(r"([\d,]+\.\d{2,4})", line)
                if num_matches:
                    try:
                        exclusive_area = float(num_matches[0].replace(",", ""))
                        break
                    except Exception:
                        pass

    if common_area == 0.0:
        for line in lines:
            line_clean = line.replace(" ", "")
            if any(k in line for k in ["계단실", "승강기", "복도", "벽체", "주거공용"]) and "외부계단" not in line_clean:
                num_matches = re.findall(r"([\d,]+\.\d{2,4})", line)
                if num_matches:
                    try:
                        common_area += float(num_matches[0].replace(",", ""))
                    except Exception:
                        pass

    # 정규식 최종 Fallback
    if exclusive_area == 0.0:
        ex_match = re.search(r"전유부분[^\n\r]*\n?[^\n\r]*?([\d,]+\.\d{2,4})", text)
        if not ex_match:
            ex_match = re.search(r"(?:전유면적|전유부분\s*면적|전유\s*면적)\s*[:|]?\s*([\d,.]+)", text)
        if not ex_match:
            ex_match = re.search(r"전유(?:부분)?\s*\|\s*([\d,.]+)", text)
        if ex_match:
            try:
                exclusive_area = float(ex_match.group(1).replace(",", "").strip())
            except Exception:
                pass

    if exclusive_area > 0:
        res["area_exclusive"] = f"{exclusive_area:.2f}"
        if common_area > 0:
            supp_area = exclusive_area + common_area
            res["area_supply"] = f"{round(supp_area, 2):.2f}"
            res["area_common"] = f"{round(common_area, 2):.2f}"
        else:
            res["area_supply"] = f"{exclusive_area:.2f}"

    # 3. 전유부 내 변동사항 준공인가일(사용승인일) 추출
    app_match = re.search(r"\((\d{4}[.\-]\d{1,2}[.\-]\d{1,2})\.?\)[^\n\r]*?준공인가", text)
    if app_match:
        parts = re.findall(r"\d+", app_match.group(1))
        if len(parts) >= 3:
            res["approval_date"] = f"{parts[0]}년 {int(parts[1]):02d}월 {int(parts[2]):02d}일"

    # 4. 해당 층수 파싱
    current_fl = ""
    fl_match = re.search(r"(?:제\s*)?(\d+)\s*층\s*(?:제\s*)?\d+\s*호", text)
    if fl_match:
        current_fl = f"{fl_match.group(1)}층"
    elif ho_name:
        num_only = re.sub(r"[^\d]", "", ho_name)
        if len(num_only) >= 3:
            current_fl = f"{num_only[:-2]}층"

    if not current_fl:
        fl_direct = re.search(r"층별\s*[:|]?\s*(?:지상\s*)?(\d+)\s*층", text)
        if fl_direct:
            current_fl = f"{fl_direct.group(1)}층"

    if current_fl:
        res["current_floor"] = current_fl
        res["floor_info"] = current_fl

    # 5. 전유부 주용도
    use_match = re.search(r"(?:주용도|용도)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if use_match:
        clean_u = clean_val(use_match.group(1))
        if clean_u:
            res["building_use"] = clean_u
    
    if not res.get("building_use"):
        if "아파트" in text:
            res["building_use"] = "공동주택 (아파트)"
        elif "오피스텔" in text:
            res["building_use"] = "업무시설 (오피스텔)"
        elif "다세대" in text:
            res["building_use"] = "공동주택 (다세대)"
        elif "근린생활시설" in text or "상가" in text:
            res["building_use"] = "제2종근린생활시설"

    # 6. 방수 / 욕실수 추정
    if exclusive_area > 0:
        if exclusive_area >= 80:
            res["room_bath"] = "방 3 / 욕실 2개"
        elif exclusive_area >= 50:
            res["room_bath"] = "방 3 / 욕실 1개"
        elif exclusive_area >= 30:
            res["room_bath"] = "방 2 / 욕실 1개"
        else:
            res["room_bath"] = "방 1 / 욕실 1개 (원룸)"

    return res


def merge_building_registers(title_data: Dict[str, Any], exclusive_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    [핵심 스마트 병합 함수]
    표제부 데이터와 전유부 데이터를 완벽하게 융합하여 16대 점검항목 완성형 데이터 생성
    - 소재지: 도로명 + 지번 + 건물명 + 전유부 동·호수 결합
    - 면적: 전유부 전용면적 + 주거공용면적 합산(공급면적)
    - 층수: 전유부 해당층 / 표제부 총층수 (예: 25 / 36층)
    - 사용승인일: 표제부의 공인 준공일자
    - 주차대수: 표제부의 총 주차대수 및 세대당 주차대수
    - 세대수: 표제부의 총 세대수
    - 주용도: 전유부 용도 우선
    - 구조: 표제부 주구조
    """
    merged = {}

    # 1. 소재지 융합
    road = exclusive_data.get("road_address") or title_data.get("road_address") or ""
    jibun = exclusive_data.get("jibun_address") or title_data.get("jibun_address") or ""
    b_name = exclusive_data.get("building_name") or title_data.get("building_name") or ""
    d_name = exclusive_data.get("dong_name") or title_data.get("dong_name") or ""
    h_name = exclusive_data.get("ho_name") or title_data.get("ho_name") or ""

    base_loc = jibun or road or title_data.get("location") or exclusive_data.get("location") or ""
    # 불필요한 기존 괄호 제거 후 재구성
    base_loc_clean = re.sub(r"\s*\(.*?\)", "", base_loc).strip()

    details = []
    if b_name:
        details.append(b_name)
    if d_name and (not b_name or d_name not in b_name):
        details.append(d_name)
    if h_name and (not b_name or h_name not in b_name):
        details.append(h_name)

    if details:
        merged["location"] = f"{base_loc_clean} ({' '.join(details)})"
    else:
        merged["location"] = base_loc_clean

    # 썸네일 제목 연동
    if b_name:
        merged["main_title"] = b_name
    elif title_data.get("main_title"):
        merged["main_title"] = title_data["main_title"]

    sub_t = f"{d_name} {h_name}".strip()
    if sub_t:
        merged["sub_title"] = sub_t
    elif exclusive_data.get("sub_title"):
        merged["sub_title"] = exclusive_data["sub_title"]

    # 2. 면적 (전유부 우선)
    if exclusive_data.get("area_exclusive"):
        merged["area_exclusive"] = exclusive_data["area_exclusive"]
        if exclusive_data.get("area_supply"):
            merged["area_supply"] = exclusive_data["area_supply"]
        else:
            merged["area_supply"] = exclusive_data["area_exclusive"]
    elif title_data.get("area_total"):
        merged["area_exclusive"] = title_data["area_total"]
        merged["area_supply"] = title_data["area_total"]

    # 3. 층수 융합 (해당층 / 총층)
    cur_fl = exclusive_data.get("current_floor") or ""
    max_fl = title_data.get("max_floor") or ""

    if cur_fl and max_fl:
        merged["floor_info"] = f"{cur_fl} / {max_fl}"
    elif cur_fl:
        merged["floor_info"] = cur_fl
    elif max_fl:
        merged["floor_info"] = f"총 {max_fl}"
    elif title_data.get("floor_info"):
        merged["floor_info"] = title_data["floor_info"]

    # 4. 방수 / 욕실수
    if exclusive_data.get("room_bath"):
        merged["room_bath"] = exclusive_data["room_bath"]

    # 5. 주용도 (전유부 우선 -> 표제부)
    merged["building_use"] = exclusive_data.get("building_use") or title_data.get("building_use") or "공동주택 (아파트)"

    # 6. 사용승인일 (표제부 우선)
    if title_data.get("approval_date"):
        merged["approval_date"] = title_data["approval_date"]
    elif exclusive_data.get("approval_date"):
        merged["approval_date"] = exclusive_data["approval_date"]

    # 7. 주차대수 (표제부 우선)
    if title_data.get("parking"):
        merged["parking"] = title_data["parking"]
    elif exclusive_data.get("parking"):
        merged["parking"] = exclusive_data["parking"]

    # 8. 총 세대수 (표제부 우선)
    if title_data.get("households"):
        merged["households"] = title_data["households"]
    elif exclusive_data.get("households"):
        merged["households"] = exclusive_data["households"]

    # 9. 주구조
    if title_data.get("structure"):
        merged["structure"] = title_data["structure"]
    elif exclusive_data.get("structure"):
        merged["structure"] = exclusive_data["structure"]

    # 10. 용도지역 및 용도지구
    if title_data.get("zone_region"):
        merged["zone_region"] = title_data["zone_region"]
    elif exclusive_data.get("zone_region"):
        merged["zone_region"] = exclusive_data["zone_region"]

    if title_data.get("zone_district"):
        merged["zone_district"] = title_data["zone_district"]
    elif exclusive_data.get("zone_district"):
        merged["zone_district"] = exclusive_data["zone_district"]

    # 11. 승강기 설비
    if title_data.get("elevator"):
        merged["elevator"] = title_data["elevator"]
    elif exclusive_data.get("elevator"):
        merged["elevator"] = exclusive_data["elevator"]

    # 12. 썸네일 특징 문구 자동 생성
    feature_parts = []
    if merged.get("households"):
        feature_parts.append(merged["households"])
    if b_name:
        feature_parts.append(b_name)
    if feature_parts:
        merged["feature_text"] = " · ".join(feature_parts) + " 추천 매물"

    return merged


def parse_general_building_register(text: str) -> Dict[str, Any]:
    """
    일반건축물대장 (단독주택 / 상가주택 / 꼬마빌딩 등) 파서
    """
    title_res = parse_building_register_title(text)
    # 일반건축물은 연면적이 공급/전용면적이 됨
    if "area_total" in title_res:
        title_res["area_exclusive"] = title_res["area_total"]
        title_res["area_supply"] = title_res["area_total"]
    return title_res


def parse_land_register(text: str) -> Dict[str, Any]:
    """
    토지대장 / 임야대장 텍스트에서 데이터 추출
    """
    res = {}
    
    loc_match = re.search(r"(?:소재지|소\s*재\s*지)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    jibun_match = re.search(r"(?:지번|지\s*번)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    
    loc_val = clean_val(loc_match.group(1)) if loc_match else ""
    jibun_val = clean_val(jibun_match.group(1)) if jibun_match else ""
    
    if loc_val and jibun_val:
        res["location"] = f"{loc_val} {jibun_val}"
    elif loc_val:
        res["location"] = loc_val

    jimok_match = re.search(r"(?:지목|지\s*목)\s*[:|]?\s*([가-힣]+)", text)
    jimok = jimok_match.group(1).strip() if jimok_match else "대"
    res["building_use"] = f"토지 (지목: {jimok})"
    res["feature_text"] = f"지목 '{jimok}' 특급 추천 토지"

    area_match = re.search(r"(?:면적|면\s*적)\s*\(?㎡?\)?\s*[:|]?\s*([\d,.]+)", text)
    if area_match:
        m2_str = area_match.group(1).replace(",", "").strip()
        res["area_supply"] = m2_str
        res["area_exclusive"] = m2_str
        try:
            py = round(float(m2_str) * 0.3025, 1)
            res["sub_title"] = f"토지 면적 {m2_str}㎡ (약 {py}평)"
        except Exception:
            pass

    jiga_match = re.search(r"(?:개별공시지가|공시지가)\s*[:|]?\s*([\d,]+)\s*원?", text)
    if jiga_match:
        res["official_price"] = f"{jiga_match.group(1)}원/㎡"

    res["floor_info"] = "- / -"
    res["room_bath"] = "- / -"
    res["entrance_type"] = "-"
    res["heating"] = "-"
    res["parking"] = "-"
    res["households"] = "-"
    res["approval_date"] = "-"

    return res


def parse_land_use_plan(text: str) -> Dict[str, Any]:
    """
    토지이용계획확인원 텍스트에서 데이터 추출
    """
    res = {}

    loc_match = re.search(r"(?:소재지|신청지)\s*[:|]?\s*([^|\n\r]+?)" + NEXT_KW, text)
    if loc_match:
        res["location"] = clean_val(loc_match.group(1))

    jimok_match = re.search(r"(?:지목)\s*[:|]?\s*([가-힣]+)", text)
    if jimok_match:
        res["building_use"] = f"토지 (지목: {jimok_match.group(1).strip()})"
        
    area_match = re.search(r"(?:면적)\s*[:|]?\s*([\d,.]+)\s*㎡?", text)
    if area_match:
        m2_str = area_match.group(1).replace(",", "").strip()
        res["area_supply"] = m2_str
        res["area_exclusive"] = m2_str

    zone_match = re.search(r"국토의\s*계획\s*및\s*이용에\s*관한\s*법률[^\n\r]*\n?([^|\n\r]+?)" + NEXT_KW, text)
    if not zone_match:
        common_zones = ["제1종전용주거지역", "제2종전용주거지역", "제1종일반주거지역", "제2종일반주거지역", "제3종일반주거지역", "준주거지역", "중심상업지역", "일반상업지역", "근린상업지역", "유통상업지역", "전용공업지역", "일반공업지역", "준공업지역", "보전녹지지역", "생산녹지지역", "자연녹지지역", "계획관리지역"]
        found_zones = [z for z in common_zones if z in text]
        if found_zones:
            res["zone_info"] = ", ".join(found_zones)
    else:
        res["zone_info"] = clean_val(zone_match.group(1))

    if "zone_info" in res:
        res["zone_region"] = res["zone_info"]
        res["feature_text"] = f"{res['zone_info']} 추천 매물"

    # 기타 지구/구역 탐색
    common_districts = ["방화지구", "지구단위계획구역", "시가지경관지구", "상대보호구역", "절대보호구역", "역점관리구역", "과밀억제권역"]
    found_dist = [cd for cd in common_districts if cd in text]
    if found_dist:
        res["zone_district"] = ", ".join(found_dist)

    return res


def parse_single_or_multi_document(pages_text: List[str]) -> Tuple[str, Dict[str, Any], str]:
    """
    다중 페이지 또는 복합 서류를 분석하여 표제부와 전유부가 둘 다 있는 경우 자동 병합합니다.
    """
    full_text = "\n".join(pages_text).strip()
    if not full_text:
        return "보안/DRM 문서 (텍스트 미감지)", {}, ""
    doc_type = identify_document_type(full_text)

    # 1. 표제부 + 전유부 복합 서류인 경우
    if "표제부+전유부" in doc_type or ("표제부" in full_text and "전유부분" in full_text):
        title_texts = []
        exclusive_texts = []
        for p in pages_text:
            p_cond = p.replace(" ", "")
            if "전유부" in p_cond or "전유부분" in p_cond:
                exclusive_texts.append(p)
            elif "표제부" in p_cond or "총괄표제부" in p_cond:
                title_texts.append(p)
            else:
                title_texts.append(p)

        t_data = parse_building_register_title("\n".join(title_texts) if title_texts else full_text)
        e_data = parse_building_register_exclusive("\n".join(exclusive_texts) if exclusive_texts else full_text)
        merged = merge_building_registers(t_data, e_data)
        return "집합건축물대장 (표제부 + 전유부 통합완료)", merged, full_text

    # 2. 표제부 단독
    elif "표제부" in doc_type:
        parsed = parse_building_register_title(full_text)
        return doc_type, parsed, full_text

    # 3. 전유부 단독
    elif "전유부" in doc_type:
        parsed = parse_building_register_exclusive(full_text)
        return doc_type, parsed, full_text

    # 4. 토지대장
    elif "토지대장" in doc_type:
        parsed = parse_land_register(full_text)
        return doc_type, parsed, full_text

    # 5. 토지이용계획원
    elif "토지이용계획" in doc_type:
        parsed = parse_land_use_plan(full_text)
        return doc_type, parsed, full_text

    # 6. 일반건축물대장 / 기타
    else:
        parsed = parse_general_building_register(full_text)
        return doc_type, parsed, full_text


def parse_official_document(file_or_bytes, filename: str = "") -> Tuple[str, Dict[str, Any], str]:
    """
    공적 서류를 종합 분석하여 (서류유형, 추출된 딕셔너리, 원본텍스트요약)을 반환합니다.
    """
    pages_text = extract_pages_text_from_pdf(file_or_bytes)
    doc_type, parsed, full_text = parse_single_or_multi_document(pages_text)
    
    # 본문 텍스트에서 식별이 모호했지만 파일명에 단서가 있는 경우 지능형 보강
    if filename:
        fn_clean = filename.replace(" ", "")
        if "표제부" in fn_clean and "전유" in fn_clean:
            doc_type = "집합건축물대장 (표제부+전유부 복합)"
        elif ("표제부" in fn_clean or "총괄" in fn_clean) and "전유부" not in doc_type:
            doc_type = "집합건축물대장 (표제부)"
            if full_text and not parsed:
                parsed = parse_building_register_title(full_text)
        elif ("전유부" in fn_clean or "전유" in fn_clean) and "표제부" not in doc_type:
            doc_type = "집합건축물대장 (전유부)"
            if full_text and not parsed:
                parsed = parse_building_register_exclusive(full_text)

    return doc_type, parsed, full_text


def parse_raw_script_document(raw_text: str) -> Tuple[str, Dict[str, Any]]:
    """
    [핵심 스크립트 대장 파서]
    정부24, 세움터, 일사편리 등에서 마우스로 복사한 대장 텍스트(스크립트)를 단일 입력받아
    표제부/전유부/일반건축물/토지대장 여부를 지능형으로 자동 감지하여 100% 통합 분석합니다.
    """
    if not raw_text or not raw_text.strip():
        return "빈 텍스트", {}

    text = raw_text.strip()
    text_condensed = text.replace(" ", "")

    # 1. 집합건축물대장 (표제부와 전유부 동시 포함 또는 둘 다의 특성이 있는 경우)
    has_title_kw = any(k in text_condensed for k in ["표제부", "총괄표제부", "주차장", "세대수", "총세대수", "대지위치", "허가일", "사용승인일"])
    has_excl_kw = any(k in text_condensed for k in ["전유부", "전유부분", "공용부분", "호명칭", "전유면적", "호실", "제2501호", "호수"])

    # 만약 전유부 면적 패턴(숫자.숫자 ㎡)이나 호명칭이 있으면서 사용승인일/주차도 있으면 복합 서류
    if (has_title_kw and has_excl_kw) or ("표제부" in text_condensed and "전유" in text_condensed):
        t_data = parse_building_register_title(text)
        e_data = parse_building_register_exclusive(text)
        merged = merge_building_registers(t_data, e_data)
        return "집합건축물대장 (표제부+전유부 스크립트 통합 분석)", merged

    # 2. 전유부 단독 스크립트
    elif "전유" in text_condensed or "전유부분" in text_condensed or "공용부분" in text_condensed:
        e_data = parse_building_register_exclusive(text)
        # 혹시 전유부 안에 대지위치나 사용승인일, 건물명이 들어있으면 보강
        t_data = parse_building_register_title(text)
        merged = merge_building_registers(t_data, e_data)
        return "집합건축물대장 (전유부 스크립트)", merged

    # 3. 토지대장
    elif "토지대장" in text_condensed or "임야대장" in text_condensed or "개별공시지가" in text_condensed:
        l_data = parse_land_register(text)
        return "토지대장 스크립트", l_data

    # 4. 토지이용계획
    elif "토지이용계획" in text_condensed or "용도지역" in text_condensed:
        p_data = parse_land_use_plan(text)
        return "토지이용계획확인원 스크립트", p_data

    # 5. 일반건축물대장 또는 표제부
    else:
        # 일반건축물대장 또는 표제부 파싱 시도
        t_data = parse_building_register_title(text)
        e_data = parse_building_register_exclusive(text)
        
        # 전유면적이 잡혔다면 병합
        if e_data.get("area_exclusive") or e_data.get("current_floor"):
            merged = merge_building_registers(t_data, e_data)
            return "건축물대장 스크립트 (통합)", merged
        elif t_data.get("area_total") or t_data.get("location"):
            g_data = parse_general_building_register(text)
            return "일반건축물대장 스크립트", g_data
        else:
            # 기본 파싱 결과 병합 반환
            merged = merge_building_registers(t_data, e_data)
            return "건축물대장 스크립트", merged

