import streamlit as st
import io
import os
import re
import base64
import subprocess
import importlib
import thumbnail_generator
import property_ad_spec
import commercial_ad_spec
import document_parser
import naver_crawler
import design_manager
importlib.reload(thumbnail_generator)
importlib.reload(property_ad_spec)
importlib.reload(commercial_ad_spec)
importlib.reload(document_parser)
importlib.reload(naver_crawler)
importlib.reload(design_manager)
from design_manager import (
    load_all_designs,
    save_custom_design,
    delete_design,
    get_design_by_name,
    import_design_from_json,
    import_design_from_image,
    reset_default_designs,
    export_all_designs_json
)
from thumbnail_generator import (
    render_thumbnail,
    render_commercial_lease_thumbnail,
    render_commercial_sale_thumbnail,
    render_a4_window_poster
)
from property_ad_spec import (
    DEFAULT_SPEC,
    SAMPLE_APT_SPEC,
    BLANK_SPEC,
    OFFICE_SPEC,
    SPEC_ITEMS_META,
    format_area_text,
    get_ordered_spec_table_data,
    get_house_spec_table_data,
    get_factory_spec_table_data,
    generate_blog_html_table,
    generate_clipboard_text,
    generate_naver_ad_guide_text,
    render_spec_table_image
)
from commercial_ad_spec import (
    DEFAULT_COMMERCIAL_SPEC_LEASE,
    DEFAULT_COMMERCIAL_SPEC_SALE,
    format_commercial_area_text,
    get_commercial_spec_table_data,
    generate_commercial_blog_html_table,
    generate_commercial_clipboard_text,
    generate_commercial_naver_ad_guide_text,
    render_commercial_spec_table_image
)
from document_parser import (
    parse_official_document,
    parse_single_or_multi_document,
    parse_raw_script_document,
    parse_building_register_title,
    parse_building_register_exclusive,
    merge_building_registers,
    identify_document_type,
    extract_pages_text_from_pdf
)
from naver_crawler import (
    crawl_naver_article,
    parse_naver_clipboard_text,
    extract_article_number,
    format_thumb_price,
    extract_maintenance_fee_and_detail
)

def render_direct_download_button(image_bytes: bytes, file_name: str, button_label: str, bg_color: str = "#F48A26") -> str:
    """브라우저 네이티브에서 100% 즉시 다운로드되는 HTML base64 링크를 생성합니다."""
    clean_name = re.sub(r'[\\/*?:"<>|]', "", file_name).strip()
    b64_data = base64.b64encode(image_bytes).decode()
    return f"""
    <div style="margin: 8px 0 14px 0;">
        <a href="data:image/png;base64,{b64_data}" download="{clean_name}" 
           style="display: block; text-align: center; background-color: {bg_color}; color: #FFFFFF !important; 
                  padding: 14px 20px; border-radius: 9px; font-weight: 700; text-decoration: none; 
                  font-size: 15px; box-shadow: 0 4px 12px rgba(244,138,38,0.3); transition: all 0.2s ease-in-out;">
           {button_label}
        </a>
    </div>
    """

def render_direct_print_button(image_bytes: bytes, file_name: str, button_label: str = "창문부착용A4바로출력", bg_color: str = "#1E293B") -> str:
    """브라우저의 인쇄 대화상자(Ctrl+P)를 즉시 호출하여 A4 용지에 꽉 차게 출력하는 고화질 인쇄 버튼을 생성합니다."""
    clean_name = re.sub(r'[\\/*?:"<>|\'\"]', "", file_name).strip()
    b64_data = base64.b64encode(image_bytes).decode()
    uid = abs(hash(file_name + str(len(image_bytes)))) % 1000000

    # inline onclick 에서 큰따옴표 충돌이 전혀 발생하지 않도록 작은따옴표와 DOM 엘리먼트 생성 방식으로 완벽 격리
    js_code = (
        "(function(){"
        "try{"
        f"var ta=document.getElementById('print_data_{uid}');"
        "if(!ta)return;"
        "var b64=ta.value;"
        "var iframe=document.createElement('iframe');"
        "iframe.style.position='fixed';"
        "iframe.style.right='0';"
        "iframe.style.bottom='0';"
        "iframe.style.width='0';"
        "iframe.style.height='0';"
        "iframe.style.border='0';"
        "document.body.appendChild(iframe);"
        "var doc=iframe.contentWindow.document;"
        "doc.open();"
        "doc.write('<!DOCTYPE html><html><head><title>Print</title><style>@page{size:A4 portrait;margin:0;}body{margin:0;padding:0;display:flex;justify-content:center;align-items:center;background:#fff;}img{width:100%;height:auto;max-height:100vh;object-fit:contain;}</style></head><body></body></html>');"
        "doc.close();"
        "var img=doc.createElement('img');"
        "img.src='data:image/png;base64,'+b64;"
        "img.onload=function(){"
        "setTimeout(function(){"
        "try{"
        "iframe.contentWindow.focus();"
        "iframe.contentWindow.print();"
        "}catch(err){window.print();}"
        "},300);"
        "};"
        "doc.body.appendChild(img);"
        "setTimeout(function(){try{document.body.removeChild(iframe);}catch(e){}},60000);"
        "}catch(e){alert('인쇄 호출 중 오류가 발생했습니다: '+e);}"
        "})();"
    )

    clean_text = button_label.replace("🖨️", "").replace("[원클릭 즉시 인쇄]", "").replace("(Ctrl+P)", "").strip()
    if not clean_text:
        clean_text = "창문부착용A4바로출력"

    return f"""<div style="margin: 8px 0 14px 0;">
<textarea id="print_data_{uid}" style="display:none;">{b64_data}</textarea>
<button id="print_btn_{uid}" onclick="{js_code}" style="width: 100%; display: flex; align-items: center; justify-content: center; gap: 8px; text-align: center; background-color: {bg_color}; color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; padding: 15px 20px; border-radius: 9px; font-weight: 800; border: 1.5px solid #475569; cursor: pointer; font-size: 17px; box-shadow: 0 4px 14px rgba(15,23,42,0.35); transition: all 0.2s ease-in-out;">
<span style="font-size: 20px; color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important;">🖨️</span>
<span style="color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; font-weight: 800; font-size: 17px; letter-spacing: -0.3px;">{clean_text}</span>
</button>
</div>"""

def render_copy_button(text_to_copy: str, button_label: str, btn_id: str = "") -> str:
    """텍스트/HTML을 클립보드로 복사하는 원클릭 복사 버튼 컴포넌트입니다."""
    if not btn_id:
        btn_id = f"copy_{abs(hash(button_label)) % 100000}"
    # 줄바꿈 및 특수문자, HTML 태그를 온전하게 전달하기 위해 base64로 인코딩
    b64_text = base64.b64encode(text_to_copy.encode("utf-8")).decode("ascii")
    
    return f"""
    <div style="margin: 8px 0 14px 0;">
        <button id="{btn_id}" onclick="
            (function() {{
                try {{
                    var text = decodeURIComponent(escape(window.atob('{b64_text}')));
                    if (navigator.clipboard && window.isSecureContext) {{
                        navigator.clipboard.writeText(text).then(function() {{
                            var b = document.getElementById('{btn_id}');
                            var old = b.innerText;
                            b.innerText = '✅ 클립보드 복사 완료!';
                            b.style.backgroundColor = '#10B981';
                            setTimeout(function() {{ b.innerText = old; b.style.backgroundColor = '#3182CE'; }}, 2000);
                        }}).catch(function() {{ fallbackCopy('{btn_id}', text); }});
                    }} else {{
                        fallbackCopy('{btn_id}', text);
                    }}
                }} catch (e) {{
                    alert('복사에 실패했습니다. 텍스트를 직접 복사해주세요.');
                }}
                function fallbackCopy(id, val) {{
                    var ta = document.createElement('textarea');
                    ta.value = val;
                    ta.style.position = 'fixed';
                    ta.style.left = '-9999px';
                    document.body.appendChild(ta);
                    ta.select();
                    try {{
                        document.execCommand('copy');
                        var b = document.getElementById(id);
                        var old = b.innerText;
                        b.innerText = '✅ 클립보드 복사 완료!';
                        b.style.backgroundColor = '#10B981';
                        setTimeout(function() {{ b.innerText = old; b.style.backgroundColor = '#3182CE'; }}, 2000);
                    }} catch (err) {{
                        alert('복사 권한이 제한되었습니다. 텍스트를 직접 드래그하여 복사해주세요.');
                    }}
                    document.body.removeChild(ta);
                }}
            }})();
        " style="width: 100%; display: block; text-align: center; background-color: #3182CE; color: #FFFFFF !important; 
                 padding: 13px 18px; border-radius: 8px; font-weight: 700; border: none; cursor: pointer;
                 font-size: 15px; box-shadow: 0 4px 10px rgba(49,130,206,0.3); transition: all 0.2s ease-in-out;">
            {button_label}
        </button>
    </div>
    """

def render_pc_save_button(file_bytes: bytes, filename: str, label: str, uid_key: str, bg_color: str = "#FF4B4B") -> str:
    """
    클릭 시 PC의 저장 위치(경로)를 직접 지정할 수 있는 네이티브 파일 저장 다이얼로그(showSaveFilePicker)를 호출하고,
    미지원 브라우저에서는 표준 다운로드로 안전하게 자동 전환되는 스마트 다운로드 버튼입니다.
    """
    clean_name = re.sub(r'[\\/*?:"<>|\'\"]', '', filename).strip()
    if not clean_name:
        clean_name = "thumbnail.png"
    if not clean_name.lower().endswith(".png"):
        clean_name += ".png"
    
    b64_data = base64.b64encode(file_bytes).decode("ascii")
    uid = abs(hash(f"{uid_key}_{filename}_{len(file_bytes)}")) % 10000000

    clean_label = label.replace("(기본 다운로드)", "").strip()
    if not clean_label.startswith("📥"):
        clean_label = f"📥 {clean_label}"

    js_code = (
        "(async function(){"
        f"var btn=document.getElementById('save_btn_{uid}');"
        "if(!btn||btn.disabled)return;"
        "var origHtml=btn.innerHTML;"
        "var origBg=btn.style.backgroundColor;"
        "btn.disabled=true;"
        "btn.innerHTML='<span style=\"color:#FFF!important;font-weight:800;font-size:17px;\">⏳ 저장 위치 선택 중...</span>';"
        "try{"
        f"var ta=document.getElementById('save_data_{uid}');"
        "if(!ta)throw new Error('Data not found');"
        "var b64=ta.value;"
        "var byteChars=atob(b64);"
        "var byteNums=new Array(byteChars.length);"
        "for(var i=0;i<byteChars.length;i++){byteNums[i]=byteChars.charCodeAt(i);}"
        "var byteArray=new Uint8Array(byteNums);"
        "var blob=new Blob([byteArray],{type:'image/png'});"
        f"var fname='{clean_name}';"
        "if(window.showSaveFilePicker){"
        "try{"
        "var handle=await window.showSaveFilePicker({"
        "suggestedName:fname,"
        "types:[{description:'PNG 이미지 파일 (*.png)',accept:{'image/png':['.png']}}]"
        "});"
        "var writable=await handle.createWritable();"
        "await writable.write(blob);"
        "await writable.close();"
        "btn.innerHTML='<span style=\"color:#FFF!important;font-weight:800;font-size:17px;\">✅ PC 지정 폴더에 저장 완료!</span>';"
        "btn.style.backgroundColor='#10B981';"
        "setTimeout(function(){btn.innerHTML=origHtml;btn.style.backgroundColor=origBg;btn.disabled=false;},3000);"
        "return;"
        "}catch(pickerErr){"
        "if(pickerErr.name==='AbortError'){"
        "btn.innerHTML=origHtml;btn.style.backgroundColor=origBg;btn.disabled=false;"
        "return;"
        "}"
        "console.warn('showSaveFilePicker error, falling back:',pickerErr);"
        "}"
        "}"
        "var url=URL.createObjectURL(blob);"
        "var a=document.createElement('a');"
        "a.href=url;"
        "a.download=fname;"
        "document.body.appendChild(a);"
        "a.click();"
        "document.body.removeChild(a);"
        "setTimeout(function(){URL.revokeObjectURL(url);},15000);"
        "btn.innerHTML='<span style=\"color:#FFF!important;font-weight:800;font-size:17px;\">📥 PC 다운로드 완료!</span>';"
        "btn.style.backgroundColor='#10B981';"
        "setTimeout(function(){btn.innerHTML=origHtml;btn.style.backgroundColor=origBg;btn.disabled=false;},3000);"
        "}catch(err){"
        "alert('저장 중 오류가 발생했습니다: '+err);"
        "btn.innerHTML=origHtml;btn.style.backgroundColor=origBg;btn.disabled=false;"
        "}"
        "})();"
    )

    box_shadow = "0 4px 14px rgba(255, 75, 75, 0.35)" if bg_color == "#FF4B4B" else "0 4px 14px rgba(43, 108, 176, 0.35)"

    return f"""
    <div style="margin: 6px 0 10px 0;">
        <textarea id="save_data_{uid}" style="display:none;">{b64_data}</textarea>
        <button id="save_btn_{uid}" onclick="{js_code}" 
                style="width: 100%; display: flex; align-items: center; justify-content: center; gap: 8px; 
                       background-color: {bg_color}; color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important;
                       padding: 14px 20px; border-radius: 9px; font-weight: 800; border: none; cursor: pointer;
                       font-size: 17px; box-shadow: {box_shadow}; transition: all 0.2s ease-in-out;">
            <span style="color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; font-weight: 800; font-size: 17px; letter-spacing: -0.3px;">
                {clean_label}
            </span>
        </button>
        <div style="font-size: 13px; color: #64748B; margin-top: 6px; text-align: center; line-height: 1.4;">
            💡 클릭 시 PC의 원하는 폴더(바탕화면, 내문서 등)를 직접 지정하여 저장할 수 있습니다.
        </div>
    </div>
    """

def render_poster_action_bar(
    file_bytes: bytes,
    filename: str,
    key_prefix: str,
    title_label: str = "300dpi 초고화질 A4포스터 파일저장"
) -> str:
    """
    포스터 전용 가로형 통합 액션 바:
    - 좌측: '300dpi 초고화질 A4포스터 파일저장' 타이틀 라벨
    - 우측: [출력] 버튼 및 [저장] 버튼 나란히 배치
    - [저장] 클릭 시: 브라우저 showSaveFilePicker API로 PC 내 저장 폴더를 직접 지정하여 파일 저장
    - [출력] 클릭 시: 창문부착용 즉시 인쇄(A4 세로 맞춤) 대화상자 호출
    """
    clean_name = re.sub(r'[\\/*?:"<>|\'\"]', '', filename).strip()
    if not clean_name:
        clean_name = "poster_a4.png"
    if not clean_name.lower().endswith(".png"):
        clean_name += ".png"
    
    b64_data = base64.b64encode(file_bytes).decode("ascii")
    uid = abs(hash(f"{key_prefix}_{filename}_{len(file_bytes)}")) % 10000000

    print_js = (
        "(function(){"
        "try{"
        f"var ta=document.getElementById('poster_data_{uid}');"
        "if(!ta)return;"
        "var b64=ta.value;"
        "var iframe=document.createElement('iframe');"
        "iframe.style.position='fixed';"
        "iframe.style.right='0';"
        "iframe.style.bottom='0';"
        "iframe.style.width='0';"
        "iframe.style.height='0';"
        "iframe.style.border='0';"
        "document.body.appendChild(iframe);"
        "var doc=iframe.contentWindow.document;"
        "doc.open();"
        "doc.write('<!DOCTYPE html><html><head><title>포스터 인쇄</title><style>@page{size:A4 portrait;margin:0;}body{margin:0;padding:0;display:flex;justify-content:center;align-items:center;background:#fff;}img{width:100%;height:auto;max-height:100vh;object-fit:contain;}</style></head><body></body></html>');"
        "doc.close();"
        "var img=doc.createElement('img');"
        "img.src='data:image/png;base64,'+b64;"
        "img.onload=function(){"
        "setTimeout(function(){"
        "try{"
        "iframe.contentWindow.focus();"
        "iframe.contentWindow.print();"
        "}catch(err){window.print();}"
        "},300);"
        "};"
        "doc.body.appendChild(img);"
        "setTimeout(function(){try{document.body.removeChild(iframe);}catch(e){}},60000);"
        "}catch(e){alert('인쇄 호출 중 오류가 발생했습니다: '+e);}"
        "})();"
    )

    save_js = (
        "(async function(){"
        f"var btn=document.getElementById('poster_save_btn_{uid}');"
        "if(!btn||btn.disabled)return;"
        "var origHtml=btn.innerHTML;"
        "var origBg=btn.style.backgroundColor;"
        "btn.disabled=true;"
        "btn.innerHTML='<span style=\"color:#FFF!important;font-weight:800;font-size:15px;\">⏳ 폴더 선택 중...</span>';"
        "try{"
        f"var ta=document.getElementById('poster_data_{uid}');"
        "if(!ta)throw new Error('Data not found');"
        "var b64=ta.value;"
        "var byteChars=atob(b64);"
        "var byteNums=new Array(byteChars.length);"
        "for(var i=0;i<byteChars.length;i++){byteNums[i]=byteChars.charCodeAt(i);}"
        "var byteArray=new Uint8Array(byteNums);"
        "var blob=new Blob([byteArray],{type:'image/png'});"
        f"var fname='{clean_name}';"
        "if(window.showSaveFilePicker){"
        "try{"
        "var handle=await window.showSaveFilePicker({"
        "suggestedName:fname,"
        "types:[{description:'PNG 이미지 파일 (*.png)',accept:{'image/png':['.png']}}]"
        "});"
        "var writable=await handle.createWritable();"
        "await writable.write(blob);"
        "await writable.close();"
        "btn.innerHTML='<span style=\"color:#FFF!important;font-weight:800;font-size:15px;\">✅ 저장 완료!</span>';"
        "btn.style.backgroundColor='#10B981';"
        "setTimeout(function(){btn.innerHTML=origHtml;btn.style.backgroundColor=origBg;btn.disabled=false;},3000);"
        "return;"
        "}catch(pickerErr){"
        "if(pickerErr.name==='AbortError'){"
        "btn.innerHTML=origHtml;btn.style.backgroundColor=origBg;btn.disabled=false;"
        "return;"
        "}"
        "console.warn('showSaveFilePicker fallback:',pickerErr);"
        "}"
        "}"
        "var url=URL.createObjectURL(blob);"
        "var a=document.createElement('a');"
        "a.href=url;"
        "a.download=fname;"
        "document.body.appendChild(a);"
        "a.click();"
        "document.body.removeChild(a);"
        "setTimeout(function(){URL.revokeObjectURL(url);},15000);"
        "btn.innerHTML='<span style=\"color:#FFF!important;font-weight:800;font-size:15px;\">📥 다운로드 완료!</span>';"
        "btn.style.backgroundColor='#10B981';"
        "setTimeout(function(){btn.innerHTML=origHtml;btn.style.backgroundColor=origBg;btn.disabled=false;},3000);"
        "}catch(err){"
        "alert('저장 중 오류가 발생했습니다: '+err);"
        "btn.innerHTML=origHtml;btn.style.backgroundColor=origBg;btn.disabled=false;"
        "}"
        "})();"
    )

    return f"""
    <div style="background: #FFFFFF; border: 1.5px solid #CBD5E1; border-radius: 12px; padding: 14px 18px; margin: 8px 0 14px 0; box-shadow: 0 3px 10px rgba(0,0,0,0.04);">
        <textarea id="poster_data_{uid}" style="display:none;">{b64_data}</textarea>
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 20px;">📄</span>
                <span style="font-size: 16.5px; font-weight: 800; color: #1E293B; letter-spacing: -0.3px;">
                    {title_label}
                </span>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <button id="poster_print_btn_{uid}" onclick="{print_js}"
                        style="display: inline-flex; align-items: center; justify-content: center; gap: 6px;
                               background-color: #1E293B; color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important;
                               padding: 10px 22px; border-radius: 8px; font-weight: 800; font-size: 15px; border: none;
                               cursor: pointer; box-shadow: 0 3px 10px rgba(30,41,59,0.25); transition: all 0.2s ease-in-out;">
                    <span style="font-size: 16px;">🖨️</span>
                    <span style="color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; font-weight: 800;">출력</span>
                </button>
                <button id="poster_save_btn_{uid}" onclick="{save_js}"
                        style="display: inline-flex; align-items: center; justify-content: center; gap: 6px;
                               background-color: #2563EB; color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important;
                               padding: 10px 22px; border-radius: 8px; font-weight: 800; font-size: 15px; border: none;
                               cursor: pointer; box-shadow: 0 3px 10px rgba(37,99,235,0.3); transition: all 0.2s ease-in-out;">
                    <span style="font-size: 16px;">💾</span>
                    <span style="color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; font-weight: 800;">저장</span>
                </button>
            </div>
        </div>
        <div style="font-size: 12.5px; color: #64748B; margin-top: 8px; line-height: 1.4;">
            💡 <b>출력</b> 클릭 시 창문부착용 즉시 인쇄(A4 세로 맞춤), <b>저장</b> 클릭 시 PC의 다운로드 받을 폴더를 직접 지정하여 저장합니다.
        </div>
    </div>
    """

def render_download_save_controller(
    file_bytes: bytes,
    default_filename: str,
    label_download: str,
    key_prefix: str,
    is_poster: bool = False,
    print_bytes: bytes = None,
    print_label: str = "출력",
    print_bg: str = "#1E293B"
):
    """
    1) 포스터인 경우: '300dpi 초고화질 A4포스터 파일저장' 옆에 [출력]과 [저장] 버튼 제공 (클릭 시 PC 저장 폴더 직접 지정)
    2) 썸네일인 경우: PC의 저장 위치(경로)를 직접 지정하여 다운로드하는 스마트 다운로드 버튼 제공
    """
    if is_poster:
        st.markdown(render_poster_action_bar(
            file_bytes=file_bytes,
            filename=default_filename,
            key_prefix=key_prefix,
            title_label="300dpi 초고화질 A4포스터 파일저장"
        ), unsafe_allow_html=True)
    else:
        st.markdown(render_pc_save_button(
            file_bytes=file_bytes,
            filename=default_filename,
            label=label_download,
            uid_key=key_prefix,
            bg_color="#FF4B4B"
        ), unsafe_allow_html=True)

def render_deal_done_controller(key_prefix: str, default_color: str = "#FF0101"):
    """
    거래완료 표시 체크박스 + 색상 선택 피커 + HEX 코드 직접 입력 칸을 가로로 정돈하여 렌더링하고 동기화합니다.
    - 기본 색상: #FF0101 (요청하신 선명한 레드)
    - 색상 피커와 직접 코드 입력 칸 실시간 양방향 연동
    """
    deal_done_key = f"{key_prefix}_deal_done"
    color_key = f"{key_prefix}_deal_color"
    code_key = f"{key_prefix}_deal_hex_code"

    # 이전 네이비(#1E3A8A) 또는 구버전 레드가 남아있거나 없는 경우 #FF0101로 업데이트
    if color_key not in st.session_state or st.session_state[color_key] in ["#1E3A8A", "#DC2626"]:
        st.session_state[color_key] = default_color

    cur_color = st.session_state.get(color_key, default_color)
    if not str(cur_color).startswith("#"):
        cur_color = f"#{cur_color}"
    cur_color = cur_color.upper()

    if code_key not in st.session_state or st.session_state[code_key] in ["#1E3A8A", "#DC2626"]:
        st.session_state[code_key] = cur_color

    c_deal1, c_deal2, c_deal3 = st.columns([1.1, 0.9, 1.2])
    with c_deal1:
        st.checkbox(
            "거래완료 표시",
            key=deal_done_key,
            help="체크 시 썸네일 중앙에 거래완료 배지가 큼직하게 부착됩니다."
        )

    with c_deal2:
        picked = st.color_picker(
            "배지 색상",
            value=cur_color,
            key=f"{key_prefix}_picker_ui",
            help="색상 팔레트에서 선택"
        )
        if picked and picked.upper() != cur_color:
            st.session_state[color_key] = picked.upper()
            st.session_state[code_key] = picked.upper()
            st.rerun()

    with c_deal3:
        typed = st.text_input(
            "색상 코드(HEX)",
            value=st.session_state.get(code_key, cur_color),
            key=f"{key_prefix}_code_ui",
            placeholder="#FF0101",
            help="직접 색상 코드 입력 (예: #FF0101 또는 ff0101)"
        )
        if typed:
            norm_code = typed.strip()
            if not norm_code.startswith("#"):
                norm_code = f"#{norm_code}"
            norm_code = norm_code.upper()
            if re.match(r"^#[0-9A-F]{6}$", norm_code) and norm_code != cur_color:
                st.session_state[color_key] = norm_code
                st.session_state[code_key] = norm_code
                st.rerun()

    return st.session_state.get(deal_done_key, False), st.session_state.get(color_key, default_color)

def render_design_and_layout_controls(key_prefix: str, default_design_name: str = "🍊 참좋은 시그니처 오렌지 (기본)"):
    """
    디자인 모드 & 레이아웃 모드 컨트롤러:
    - 좌측: 디자인 모드 (외부 파일 가져오기, 직접 테마 등록, 마음에 안 드는 디자인 즉시 삭제)
    - 우측: 레이아웃 모드 (와이드 사선형, 상하 파노라마형, 표준 사선형)
    """
    col_dm, col_ly = st.columns([1.1, 1.1])
    
    all_designs = load_all_designs()
    design_names = [d["name"] for d in all_designs]
    
    def_idx = 0
    if default_design_name in design_names:
        def_idx = design_names.index(default_design_name)
    
    with col_dm:
        st.markdown("<b style='font-size:15px; color:#1E2022;'>🎨 디자인 모드</b> <span style='font-size:12px; color:#718096;'>(현장 사진 제외 테마/그래픽)</span>", unsafe_allow_html=True)
        
        # 선택 드롭다운과 즉시 삭제 버튼을 한 줄에 배치
        c_sel, c_del = st.columns([3.8, 1.2])
        with c_sel:
            sel_design_name = st.selectbox(
                "디자인 모드 선택",
                options=design_names,
                index=def_idx if def_idx < len(design_names) else 0,
                key=f"{key_prefix}_design_selector",
                label_visibility="collapsed"
            )
        with c_del:
            if st.button("🗑️ 삭제", key=f"{key_prefix}_del_cur_btn", help="선택한 디자인 모드를 목록에서 삭제합니다.", use_container_width=True):
                ok, msg = delete_design(sel_design_name)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        selected_design = get_design_by_name(sel_design_name)
        
        # ➕ 새 디자인 모드 추가 / 외부 디자인 파일 가져오기 / 백업 관리
        with st.expander("➕ 새 디자인 추가 / 외부 디자인 파일 가져오기", expanded=False):
            tab_imp_file, tab_make_new, tab_export = st.tabs([
                "📁 외부 파일 가져오기",
                "🎨 직접 색상 등록",
                "💾 백업 및 복원"
            ])
            
            with tab_imp_file:
                st.markdown("<span style='font-size:12px; color:#4A5568;'>외부 디자인 파일(<b>.json 설정 파일</b> 또는 <b>.png/.jpg 디자인 프레임/오버레이 이미지</b>)을 가져와 새 디자인 모드로 등록할 수 있습니다.</span>", unsafe_allow_html=True)
                uploaded_design_file = st.file_uploader(
                    "외부 디자인 파일 선택 (.json, .png, .jpg)",
                    type=["json", "png", "jpg", "jpeg"],
                    key=f"{key_prefix}_up_design_file"
                )
                if uploaded_design_file is not None:
                    fname = uploaded_design_file.name
                    if fname.lower().endswith(".json"):
                        if st.button("📥 JSON 디자인 설정 테마 가져오기", key=f"{key_prefix}_btn_imp_json", type="primary", use_container_width=True):
                            content_str = uploaded_design_file.getvalue().decode("utf-8", errors="ignore")
                            ok, msg = import_design_from_json(content_str)
                            if ok:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        img_design_name = st.text_input(
                            "등록할 디자인 모드 이름",
                            value=os.path.splitext(fname)[0],
                            key=f"{key_prefix}_img_dname"
                        )
                        c_p1, c_p2 = st.columns(2)
                        with c_p1:
                            img_pri = st.color_picker("메인 포인트 색상", "#F48A26", key=f"{key_prefix}_img_pri")
                        with c_p2:
                            img_acc = st.color_picker("서브 보조 색상", "#EB5E28", key=f"{key_prefix}_img_acc")
                            
                        if st.button("🖼️ 디자인 프레임 이미지로 등록하기", key=f"{key_prefix}_btn_imp_img", type="primary", use_container_width=True):
                            if img_design_name.strip():
                                saved = import_design_from_image(
                                    name=img_design_name.strip(),
                                    image_bytes=uploaded_design_file.getvalue(),
                                    filename=fname,
                                    primary_hex=img_pri,
                                    accent_hex=img_acc
                                )
                                st.success(f"🎉 '{saved['name']}' 디자인이 영구 저장되었습니다!")
                                st.rerun()
                            else:
                                st.warning("디자인 모드 이름을 입력해주세요.")
                                
            with tab_make_new:
                st.markdown("<span style='font-size:12px; color:#4A5568;'>원하는 테마 색상을 직접 지정하여 새 디자인 모드를 등록하면 <b>영구 저장되어 다음 실행 시에도 유지</b>됩니다.</span>", unsafe_allow_html=True)
                new_d_name = st.text_input("새 디자인 이름", placeholder="예: 봄맞이 핑크 에디션", key=f"{key_prefix}_new_d_name")
                cd1, cd2 = st.columns(2)
                with cd1:
                    new_pri_color = st.color_picker("메인 포인트 색상", "#F48A26", key=f"{key_prefix}_new_d_pri")
                with cd2:
                    new_acc_color = st.color_picker("서브 보조 색상", "#EB5E28", key=f"{key_prefix}_new_d_acc")
                
                if st.button("💾 이 디자인 영구 저장하기", key=f"{key_prefix}_save_design_btn", use_container_width=True, type="primary"):
                    if new_d_name.strip():
                        saved = save_custom_design(new_d_name.strip(), new_pri_color, new_acc_color)
                        st.success(f"🎉 '{saved['name']}' 디자인이 영구 저장되었습니다!")
                        st.rerun()
                    else:
                        st.warning("디자인 이름을 입력해주세요.")
                        
            with tab_export:
                st.markdown("<span style='font-size:12px; color:#4A5568;'>현재 등록된 모든 디자인을 외부 파일(.json)로 저장하거나, 삭제했던 기본 디자인을 복원할 수 있습니다.</span>", unsafe_allow_html=True)
                designs_json_str = export_all_designs_json()
                st.download_button(
                    "💾 현재 모든 디자인 테마 파일(.json) 내보내기",
                    data=designs_json_str,
                    file_name="chamjoeun_designs_backup.json",
                    mime="application/json",
                    key=f"{key_prefix}_btn_exp_json",
                    use_container_width=True
                )
                if st.button("🔄 삭제된 기본 디자인 전체 복원", key=f"{key_prefix}_btn_reset_defs", use_container_width=True):
                    reset_default_designs()
                    st.success("기본 디자인 테마가 모두 원상 복구되었습니다.")
                    st.rerun()

    with col_ly:
        st.markdown("<b style='font-size:15px; color:#1E2022;'>📐 레이아웃 모드</b>", unsafe_allow_html=True)
        layout_options = {
            "상하 파노라마형 (전경 극대화)": "top_panoramic",
            "와이드 사선형 (실내 추천)": "side_wide",
            "표준 사선형 (외관 5:5)": "side_standard",
        }
        selected_layout_label = st.radio(
            "레이아웃 모드",
            options=list(layout_options.keys()),
            index=0,
            horizontal=True,
            key=f"{key_prefix}_layout_selector",
            label_visibility="collapsed"
        )
        layout_mode = layout_options[selected_layout_label]
        
        photo_width_ratio = 0.68
        if layout_mode == "side_wide":
            photo_width_ratio_pct = st.slider(
                "📷 사진 가로 비중 (와이드 조절)",
                min_value=50,
                max_value=76,
                value=68,
                step=2,
                format="%d%%",
                key=f"{key_prefix}_photo_width_slider"
            )
            photo_width_ratio = photo_width_ratio_pct / 100.0
            
    return selected_design, layout_mode, photo_width_ratio


# 페이지 설정
st.set_page_config(
    page_title="부동산 블로그 썸네일 & 네이버광고",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세련된 커스텀 CSS 적용 & 모바일 터치 최적화
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
    
    /* 메인 컨테이너 패딩: Streamlit 상단 메뉴바(Share 등)에 가려지지 않도록 상단 여백 확보 */
    .block-container {
        padding-top: 4.0rem !important;
        padding-bottom: 2.5rem;
    }
    
    /* Deploy 버튼 및 불필요한 클라우드 메뉴 숨기기 */
    .stAppDeployButton, [data-testid="stAppDeployButton"], [data-testid="manage-app-button"] {
        display: none !important;
    }
    
    /* ==================================================== */
    /* 🌟 최상위 메인 3대 메뉴 탭: 크기 3배 (38px), 간격 3배 (50px) */
    /* ==================================================== */
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > div[role="tablist"],
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > [data-baseweb="tab-list"] {
        gap: 50px !important;
        background-color: #F8FAFC !important;
        padding: 14px 24px !important;
        border-radius: 18px !important;
        margin-bottom: 28px !important;
        display: flex !important;
        align-items: center !important;
        border: 1.5px solid #E2E8F0 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04) !important;
    }

    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > div[role="tablist"] > div[role="tab"],
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > [data-baseweb="tab-list"] > [data-baseweb="tab"] {
        height: 76px !important;
        min-height: 76px !important;
        padding: 0 32px !important;
        border-radius: 14px !important;
        background-color: transparent !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border: 2px solid transparent !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > div[role="tablist"] > div[role="tab"] *,
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > div[role="tablist"] > div[role="tab"] p,
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > [data-baseweb="tab-list"] > [data-baseweb="tab"] * {
        font-size: 38px !important;
        font-weight: 800 !important;
        line-height: 1.3 !important;
        color: #475569 !important;
        letter-spacing: -0.5px !important;
    }

    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > div[role="tablist"] > div[role="tab"][aria-selected="true"],
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > [data-baseweb="tab-list"] > [data-baseweb="tab"][aria-selected="true"] {
        background-color: #FFFFFF !important;
        border: 2.5px solid #F48A26 !important;
        box-shadow: 0 6px 20px rgba(244, 138, 38, 0.18) !important;
    }

    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > div[role="tablist"] > div[role="tab"][aria-selected="true"] *,
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > div[role="tablist"] > div[role="tab"][aria-selected="true"] p,
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > [data-baseweb="tab-list"] > [data-baseweb="tab"][aria-selected="true"] * {
        color: #F48A26 !important;
        font-weight: 900 !important;
    }

    /* 📌 하위 서브 탭 (tab-panel 내부: 아파트/주택/상가/공장 등은 단정하고 깔끔한 17px) */
    div[data-testid="stTabPanel"] div[data-testid="stTabs"] div[role="tablist"],
    div[role="tabpanel"] div[data-testid="stTabs"] div[role="tablist"],
    [data-baseweb="tab-panel"] [data-baseweb="tab-list"] {
        gap: 12px !important;
        background-color: #EDF2F7 !important;
        padding: 8px 14px !important;
        border-radius: 12px !important;
        margin-bottom: 20px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: none !important;
    }

    div[data-testid="stTabPanel"] div[data-testid="stTabs"] div[role="tablist"] div[role="tab"],
    div[role="tabpanel"] div[data-testid="stTabs"] div[role="tablist"] div[role="tab"],
    [data-baseweb="tab-panel"] [data-baseweb="tab"] {
        height: 48px !important;
        min-height: 48px !important;
        padding: 0 22px !important;
        border-radius: 9px !important;
        background-color: transparent !important;
        border: 1.5px solid transparent !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    div[data-testid="stTabPanel"] div[data-testid="stTabs"] div[role="tablist"] div[role="tab"] *,
    div[data-testid="stTabPanel"] div[data-testid="stTabs"] div[role="tablist"] div[role="tab"] p,
    [data-baseweb="tab-panel"] [data-baseweb="tab"] * {
        font-size: 17px !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;
        color: #4A5568 !important;
        letter-spacing: normal !important;
    }

    div[data-testid="stTabPanel"] div[data-testid="stTabs"] div[role="tablist"] div[role="tab"][aria-selected="true"],
    [data-baseweb="tab-panel"] [data-baseweb="tab"][aria-selected="true"] {
        background-color: #FFFFFF !important;
        border: 1.5px solid #F48A26 !important;
        box-shadow: 0 2px 8px rgba(244, 138, 38, 0.15) !important;
    }

    div[data-testid="stTabPanel"] div[data-testid="stTabs"] div[role="tablist"] div[role="tab"][aria-selected="true"] *,
    div[data-testid="stTabPanel"] div[data-testid="stTabs"] div[role="tablist"] div[role="tab"][aria-selected="true"] p,
    [data-baseweb="tab-panel"] [data-baseweb="tab"][aria-selected="true"] * {
        color: #F48A26 !important;
        font-weight: 800 !important;
    }

    /* 기본 밑줄/인디케이터 완전히 제거 */
    div[data-testid="stTabs"] .react-aria-SelectionIndicator,
    [data-baseweb="tab-highlight"],
    [data-baseweb="tab-border"] {
        display: none !important;
    }
    div[data-testid="stTabs"] div[role="tablist"]::after {
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
    .badge-red {
        background-color: #FDE8E8;
        color: #E02424;
        border: 1px solid #F8B4B4;
    }
    .badge-green {
        background-color: #DEF7EC;
        color: #03543F;
        border: 1px solid #BCF0DA;
    }
    
    /* 다운로드 버튼 강조 (모바일 터치 최적화) */
    .stDownloadButton > button {
        background-color: #F48A26 !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 14px 24px !important;
        font-size: 16px !important;
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

    /* 카드 박스 */
    .info-card {
        background: #FFFFFF;
        border: 1px solid #E5E8EB;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 15px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }

    /* 입력 필드 (text_input, selectbox) 눈에 확 띄는 선명한 흰색 박스 + 테두리 */
    div[data-baseweb="input"], div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border: 1.8px solid #CBD5E0 !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06) !important;
        transition: all 0.2s ease-in-out !important;
    }
    div[data-baseweb="input"]:hover, div[data-baseweb="select"] > div:hover {
        border-color: #F48A26 !important;
    }
    div[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within {
        border-color: #F48A26 !important;
        box-shadow: 0 0 0 3px rgba(244, 138, 38, 0.25) !important;
    }
    input.st-bc, input {
        color: #1A202C !important;
        font-weight: 600 !important;
        font-size: 15px !important;
    }

    /* 점검표 테이블 행 */
    .check-row {
        border-bottom: 1px solid #E9ECEF;
        padding: 10px 0;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .check-label {
        font-size: 14px;
        font-weight: 700;
        color: #333D4B;
    }
    .check-val {
        font-size: 15px;
        color: #191F28;
        font-weight: 600;
    }
    .check-guide {
        font-size: 12px;
        color: #8B95A1;
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
                <h4 style="margin: 0; color: #F48A26; font-weight: 700;">썸네일 & 네이버광고 올인원 마스터</h4>
                <p style="color: #6C757D; font-size: 14px; margin-top: 8px;">
                    보안 접속을 위해 설정된 비밀번호를 입력해주세요.
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            import streamlit.components.v1 as components
            components.html("""
            <script>
            setTimeout(function() {
                try {
                    var doc = window.parent.document;
                    var pwInputs = doc.querySelectorAll('input[type="password"]');
                    pwInputs.forEach(function(el) {
                        el.setAttribute('autocomplete', 'new-password');
                        el.setAttribute('data-lpignore', 'true');
                        el.setAttribute('data-1p-ignore', 'true');
                    });
                } catch(e) {}
            }, 150);
            </script>
            """, height=0)

            input_pw = st.text_input(
                "접근 비밀번호 입력",
                type="password",
                placeholder="비밀번호 입력 (예: 4989)",
                key="login_pw_input",
                help="설정된 접근 비밀번호를 입력해주세요."
            )
            submit_btn = st.button("🔓 로그인하여 시작하기", type="primary", use_container_width=True)
            
            if submit_btn or (input_pw and input_pw.strip() in VALID_PASSWORDS):
                if input_pw.strip() in VALID_PASSWORDS:
                    st.session_state.authenticated = True
                    st.rerun()
                elif submit_btn:
                    st.error("비밀번호가 일치하지 않습니다.")
            
            st.markdown("""
            <div style="text-align: center; margin-top: 25px; color: #4A5568; font-size: 13px; line-height: 1.5;">
                🔒 참좋은공인중개사사무소 (대표 신제환 ☎ 010-9667-4201)<br/>
                📍 부산광역시 사상구 강선로 9, 1층 (등록번호: 제 26530-2026-00009 호)<br/>
                PC & 스마트폰 모바일 동시 지원
            </div>
            """, unsafe_allow_html=True)
    st.stop()


# ----------------------------------------------------
# 📌 세션 상태(Session State) 초기화
# ----------------------------------------------------

# 1. 썸네일 관련 상태
if "item_no" not in st.session_state:
    st.session_state.item_no = "No. APT001"
if "main_title" not in st.session_state:
    st.session_state.main_title = "사상 중흥S-클래스"
if "sub_title" not in st.session_state:
    st.session_state.sub_title = "그랜드센트럴"
if "feature_text" not in st.session_state:
    st.session_state.feature_text = ""
if "thumb_trade_type" not in st.session_state:
    st.session_state.thumb_trade_type = "매매"
if "thumb_price_text" not in st.session_state:
    st.session_state.thumb_price_text = "6억2천"
if "spec_line1" not in st.session_state:
    st.session_state.spec_line1 = "105동 / 25층(로얄층)"
if "spec_line2" not in st.session_state:
    st.session_state.spec_line2 = "공급 111.42㎡ / 전용 79.85㎡"
if "spec_line3" not in st.session_state:
    st.session_state.spec_line3 = "방 3 / 욕실 2"
if "spec_line4" not in st.session_state:
    st.session_state.spec_line4 = "즉시입주 협의가능"
if "spec_line5" not in st.session_state:
    st.session_state.spec_line5 = "남동향 (거실 기준)"
if "thumb_show_footer" not in st.session_state:
    st.session_state.thumb_show_footer = True
if "thumb_footer_text" not in st.session_state:
    st.session_state.thumb_footer_text = ""

# 거래완료 배지 옵션 상태 (기본값: #FF0101)
DEFAULT_DEAL_COLOR = "#FF0101"

for deal_prefix in ["apt", "house", "comm", "factory"]:
    done_k = f"{deal_prefix}_deal_done"
    color_k = f"{deal_prefix}_deal_color"
    hex_k = f"{deal_prefix}_deal_hex_code"
    if done_k not in st.session_state:
        st.session_state[done_k] = False
    if color_k not in st.session_state or st.session_state[color_k] in ["#DC2626", "#1E3A8A"]:
        st.session_state[color_k] = DEFAULT_DEAL_COLOR
    if hex_k not in st.session_state or st.session_state[hex_k] in ["#DC2626", "#1E3A8A"]:
        st.session_state[hex_k] = st.session_state[color_k]

# 2. 네이버 광고 & 대상중개물 표시 16개 점검 항목 상태 (신소장님 사상 중흥S-클래스 세팅값)
for k, v in DEFAULT_SPEC.items():
    if f"ad_{k}" not in st.session_state:
        st.session_state[f"ad_{k}"] = v
if "ad_include_office_info" not in st.session_state:
    st.session_state.ad_include_office_info = True
if "ad_assistant_name" not in st.session_state:
    st.session_state.ad_assistant_name = ""
if "ad_assistant_phone" not in st.session_state:
    st.session_state.ad_assistant_phone = ""

# 썸네일 프리셋 적용 함수
def apply_preset(p_type):
    if p_type == "living":
        st.session_state.item_no = "No. APT001"
        st.session_state.main_title = "사상 중흥S-클래스"
        st.session_state.sub_title = "그랜드센트럴"
        st.session_state.feature_text = "1572세대 대단지 아파트"
        st.session_state.thumb_trade_type = "매매"
        st.session_state.thumb_price_text = "6억2천"
        st.session_state.spec_line1 = "105동 / 25층(로얄층)"
        st.session_state.spec_line2 = "공급 111.42㎡ / 전용 79.85㎡"
        st.session_state.spec_line3 = "방 3 / 욕실 2"
        st.session_state.spec_line4 = "즉시입주 협의가능"
        st.session_state.spec_line5 = "남동향 (거실 기준)"
        
        # 2단계 점검표도 함께 동기화
        st.session_state.ad_location = "부산광역시 사상구 덕포동 220 (사상 중흥S-클래스 105동)"
        st.session_state.ad_area_supply = "111.42"
        st.session_state.ad_area_exclusive = "79.85"
        st.session_state.ad_floor_info = "25 / 36층"
        st.session_state.ad_room_bath = "방 3 / 욕실 2개"
        st.session_state.ad_maintenance_fee = "18만 원"
        st.session_state.ad_maintenance_detail = "공용관리비 약 13만원 (수도/전기/가스 별도)"
        st.session_state.ad_trade_type = "매매"
        st.session_state.ad_price_text = "6억 2,000만 원"
        st.session_state.ad_direction = "남동향 (거실 기준)"
        st.session_state.ad_entrance_type = "계단식"
        st.session_state.ad_heating = "개별난방 / 도시가스"
        st.session_state.ad_move_in_date = "즉시입주 협의가능"
        st.session_state.ad_parking = "총 1,685대 (세대당 1.07대)"
        st.session_state.ad_households = "331세대 (총 1,572세대)"
        st.session_state.ad_building_use = "공동주택 (아파트)"
        st.session_state.ad_approval_date = "2023년 07월 28일"
    elif p_type == "op":
        st.session_state.item_no = "No. OP-302"
        st.session_state.main_title = "해운대 센텀스퀘어"
        st.session_state.sub_title = "하이엔드 오피스텔"
        st.session_state.feature_text = "초역세권 + 풀옵션 프리미엄"
        st.session_state.thumb_trade_type = "전세"
        st.session_state.thumb_price_text = "2억 4천"
        st.session_state.spec_line1 = "A동 / 18층(고층)"
        st.session_state.spec_line2 = "계약 68㎡ / 전용 42㎡"
        st.session_state.spec_line3 = "방 1.5룸 / 욕실 1"
        st.session_state.spec_line4 = "협의 입주 가능"
        st.session_state.spec_line5 = "동향 (시티뷰 조망)"

        st.session_state.ad_location = "부산광역시 해운대구 우동 1515 (센텀스퀘어)"
        st.session_state.ad_area_supply = "68.20"
        st.session_state.ad_area_exclusive = "42.15"
        st.session_state.ad_floor_info = "18 / 32층"
        st.session_state.ad_room_bath = "방 1.5룸 / 욕실 1개"
        st.session_state.ad_maintenance_fee = "15만 원"
        st.session_state.ad_maintenance_detail = "공용관리비 10만원 + 개별사용량"
        st.session_state.ad_trade_type = "전세"
        st.session_state.ad_price_text = "2억 4,000만 원"
        st.session_state.ad_direction = "동향 (거실 기준)"
        st.session_state.ad_entrance_type = "복도식"
        st.session_state.ad_heating = "개별난방 / 도시가스"
        st.session_state.ad_move_in_date = "협의 입주 가능"
        st.session_state.ad_parking = "총 450대 (세대당 1.1대)"
        st.session_state.ad_households = "120세대 (총 380세대)"
        st.session_state.ad_building_use = "업무시설 (오피스텔)"
        st.session_state.ad_approval_date = "2021년 05월 12일"

# 3. 상가 썸네일 관련 상태 (임차 & 매매)
if "comm_thumb_mode" not in st.session_state:
    st.session_state.comm_thumb_mode = "🔑 상가 임차 (월세)"
if "comm_item_no" not in st.session_state:
    st.session_state.comm_item_no = "No. COMM-01"

# 임차 썸네일 세션 상태
if "comm_lease_top_badge" not in st.session_state:
    st.session_state.comm_lease_top_badge = "사상역 초역세권 · 무권리 추천매물"
if "comm_lease_cp_top" not in st.session_state:
    st.session_state.comm_lease_cp_top = "유동인구 1등! 대로변 1층"
if "comm_lease_main_title" not in st.session_state:
    st.session_state.comm_lease_main_title = "코너 상가 임차"
if "comm_lease_cp_bot" not in st.session_state:
    st.session_state.comm_lease_cp_bot = "가시성 최고! 즉시 입점 가능"
if "comm_lease_pin_bubble" not in st.session_state:
    st.session_state.comm_lease_pin_bubble = "목 좋은 자리!"
if "comm_lease_show_pin" not in st.session_state:
    st.session_state.comm_lease_show_pin = True
if "comm_lease_spec1" not in st.session_state:
    st.session_state.comm_lease_spec1 = "전용 25평 | 보증금 3,000만 / 월 180만"
if "comm_lease_spec2" not in st.session_state:
    st.session_state.comm_lease_spec2 = "추천 : 카페 · 음식점 · 판매점"
if "comm_lease_show_footer" not in st.session_state:
    st.session_state.comm_lease_show_footer = True
if "comm_lease_office" not in st.session_state:
    st.session_state.comm_lease_office = "참좋은 공인중개사사무소"
if "comm_lease_broker" not in st.session_state:
    st.session_state.comm_lease_broker = "황금터잡이 신소장"

# 매매 썸네일 세션 상태
if "comm_sale_top_left" not in st.session_state:
    st.session_state.comm_sale_top_left = "사상 핵심상권 매매"
if "comm_sale_top_right" not in st.session_state:
    st.session_state.comm_sale_top_right = "우량 임차인 성업중"
if "comm_sale_show_chart" not in st.session_state:
    st.session_state.comm_sale_show_chart = True
if "comm_sale_main_hl" not in st.session_state:
    st.session_state.comm_sale_main_hl = "확정 수익률 6.8%"
if "comm_sale_main_sub" not in st.session_state:
    st.session_state.comm_sale_main_sub = "안정적인 알짜 상가 매매"
if "comm_sale_price_spec" not in st.session_state:
    st.session_state.comm_sale_price_spec = "매매가 15억 | 보증금 8천 / 월수익 650만 | 실투자금 6억"
if "comm_sale_show_footer" not in st.session_state:
    st.session_state.comm_sale_show_footer = True
if "comm_sale_office" not in st.session_state:
    st.session_state.comm_sale_office = "참좋은 공인중개사사무소"
if "comm_sale_broker" not in st.session_state:
    st.session_state.comm_sale_broker = "황금터잡이 신소장"

# 4. 상가 중개대상물 표시 항목 상태 (임차 & 매매)
if "comm_ad_mode" not in st.session_state:
    st.session_state.comm_ad_mode = "🔑 상가 임대차 (월세)"
for k, v in DEFAULT_COMMERCIAL_SPEC_LEASE.items():
    if f"comm_ad_{k}" not in st.session_state:
        st.session_state[f"comm_ad_{k}"] = v
for k, v in DEFAULT_COMMERCIAL_SPEC_SALE.items():
    if f"comm_ad_{k}" not in st.session_state:
        st.session_state[f"comm_ad_{k}"] = v

# 항상 최신 공인중개사 등록증 정보(강선로 9, 2026-00009 호)로 세션 강제 동기화 (기존 세션 유지 시 구정보 덮어쓰기)
OFFICE_REFRESH_MAP = {
    "office_name": "참좋은공인중개사사무소",
    "office_owner": "신제환",
    "office_reg_no": "제 26530-2026-00009 호",
    "office_address": "부산광역시 사상구 강선로 9, 1층",
    "office_phone": "010-9667-4201"
}
for ok, ov in OFFICE_REFRESH_MAP.items():
    cur_val = str(st.session_state.get(f"ad_{ok}", ""))
    if not cur_val or "2021-00045" in cur_val or "사상로 200" in cur_val or "051-911-8249" in cur_val:
        st.session_state[f"ad_{ok}"] = ov
    cur_comm = str(st.session_state.get(f"comm_ad_{ok}", ""))
    if not cur_comm or "2021-00045" in cur_comm or "사상로 200" in cur_comm or "051-911-8249" in cur_comm:
        st.session_state[f"comm_ad_{ok}"] = ov

for tel_k in ["office_tel_input", "comm_office_tel_input", "house_office_tel", "factory_office_tel"]:
    if st.session_state.get(tel_k) in [None, "", "051-911-8249"]:
        st.session_state[tel_k] = "010-9667-4201"

# 5. 주택 세션 상태 (썸네일 & 중개대상물)
if "house_item_no" not in st.session_state:
    st.session_state.house_item_no = "No. HOUSE-01"
if "house_main_title" not in st.session_state:
    st.session_state.house_main_title = "사상 덕포동 단독주택"
if "house_sub_title" not in st.session_state:
    st.session_state.house_sub_title = "마당 넓은 올수리 2층 주택"
if "house_feature_text" not in st.session_state:
    st.session_state.house_feature_text = ""
if "house_trade_type" not in st.session_state:
    st.session_state.house_trade_type = "매매"
if "house_price_text" not in st.session_state:
    st.session_state.house_price_text = "3억 8천"
if "house_spec1" not in st.session_state:
    st.session_state.house_spec1 = "지상 2층 / 단독주택"
if "house_spec2" not in st.session_state:
    st.session_state.house_spec2 = "대지 148.7㎡ / 연면적 99.2㎡"
if "house_spec3" not in st.session_state:
    st.session_state.house_spec3 = "방 4개 / 욕실 2개"
if "house_spec4" not in st.session_state:
    st.session_state.house_spec4 = "즉시입주 협의가능"
if "house_spec5" not in st.session_state:
    st.session_state.house_spec5 = "정남향 (일조권 풍부)"
if "house_show_footer" not in st.session_state:
    st.session_state.house_show_footer = True
if "house_footer_text" not in st.session_state:
    st.session_state.house_footer_text = ""
if "house_assistant_phone" not in st.session_state:
    st.session_state.house_assistant_phone = ""
if "house_office_tel" not in st.session_state:
    st.session_state.house_office_tel = "010-9667-4201"

# 6. 공장/창고 세션 상태 (썸네일 & 중개대상물)
if "factory_item_no" not in st.session_state:
    st.session_state.factory_item_no = "No. FACTORY-01"
if "factory_main_title" not in st.session_state:
    st.session_state.factory_main_title = "사상 감전동 특급 공장"
if "factory_sub_title" not in st.session_state:
    st.session_state.factory_sub_title = "트레일러 진입 최상 / 역세권"
if "factory_feature_text" not in st.session_state:
    st.session_state.factory_feature_text = ""
if "factory_trade_type" not in st.session_state:
    st.session_state.factory_trade_type = "월세"
if "factory_price_text" not in st.session_state:
    st.session_state.factory_price_text = "보3,000/월250"
if "factory_spec1" not in st.session_state:
    st.session_state.factory_spec1 = "단층 공장 (층고 8m)"
if "factory_spec2" not in st.session_state:
    st.session_state.factory_spec2 = "대지 660㎡ / 연면적 396㎡ (120평)"
if "factory_spec3" not in st.session_state:
    st.session_state.factory_spec3 = "동력 150kW / 호이스트 5T"
if "factory_spec4" not in st.session_state:
    st.session_state.factory_spec4 = "즉시입주 협의가능"
if "factory_spec5" not in st.session_state:
    st.session_state.factory_spec5 = "마당 넓음 · 주차 8대 가능"
if "factory_show_footer" not in st.session_state:
    st.session_state.factory_show_footer = True
if "factory_footer_text" not in st.session_state:
    st.session_state.factory_footer_text = ""
if "factory_assistant_phone" not in st.session_state:
    st.session_state.factory_assistant_phone = ""
if "factory_office_tel" not in st.session_state:
    st.session_state.factory_office_tel = "010-9667-4201"

# 아파트 및 상가 사무실/담당자 연락처 기본 세션
if "office_tel_input" not in st.session_state:
    st.session_state.office_tel_input = "010-9667-4201"
if "assistant_phone_input" not in st.session_state:
    st.session_state.assistant_phone_input = ""
if "comm_office_tel_input" not in st.session_state:
    st.session_state.comm_office_tel_input = "010-9667-4201"
if "comm_assistant_phone_input" not in st.session_state:
    st.session_state.comm_assistant_phone_input = ""


def apply_comm_preset(p_type):
    if p_type == "lease":
        st.session_state.comm_thumb_mode = "🔑 상가 임차 (월세)"
        st.session_state.comm_lease_top_badge = "사상역 초역세권 · 무권리 추천매물"
        st.session_state.comm_lease_cp_top = "유동인구 1등! 대로변 1층"
        st.session_state.comm_lease_main_title = "코너 상가 임차"
        st.session_state.comm_lease_cp_bot = "가시성 최고! 즉시 입점 가능"
        st.session_state.comm_lease_pin_bubble = "목 좋은 자리!"
        st.session_state.comm_lease_show_pin = True
        st.session_state.comm_lease_spec1 = "전용 25평 | 보증금 3,000만 / 월 180만"
        st.session_state.comm_lease_spec2 = "추천 : 카페 · 음식점 · 판매점"
        for k, v in DEFAULT_COMMERCIAL_SPEC_LEASE.items():
            st.session_state[f"comm_ad_{k}"] = v
    elif p_type == "sale":
        st.session_state.comm_thumb_mode = "💰 상가 매매 (수익형)"
        st.session_state.comm_sale_top_left = "사상 핵심상권 매매"
        st.session_state.comm_sale_top_right = "우량 임차인 성업중"
        st.session_state.comm_sale_show_chart = True
        st.session_state.comm_sale_main_hl = "확정 수익률 6.8%"
        st.session_state.comm_sale_main_sub = "안정적인 알짜 상가 매매"
        st.session_state.comm_sale_price_spec = "매매가 15억 | 보증금 8천 / 월수익 650만 | 실투자금 6억"
        for k, v in DEFAULT_COMMERCIAL_SPEC_SALE.items():
            st.session_state[f"comm_ad_{k}"] = v

if "comm_lease_main_title" not in st.session_state:
    apply_comm_preset("lease")
if "comm_sale_main_sub" not in st.session_state:
    apply_comm_preset("sale")

def safe_set_session_state(key: str, val: any):
    """위젯이 이미 화면에 렌더링된 이후 session_state를 변경할 때 발생하는 StreamlitWidgetAlreadyInstantiatedError 원천 방지"""
    try:
        st.session_state[key] = val
    except Exception:
        pass

def queue_state_update(action_type: str, data: dict = None, preset: str = None, clean_previous: bool = True, success_msg: str = None, error_msg: str = None, target_tab: str = None):
    """
    StreamlitWidgetAlreadyInstantiatedError 원천 차단을 위한 지연 상태 반영 큐.
    Streamlit은 위젯이 렌더링된 후 session_state를 변경하면 즉시 치명적 예외가 발생하므로,
    큐에 작업을 담은 뒤 즉시 rerun()하여 위젯이 생성되기 전 최상단에서 일괄 반영합니다.
    target_tab을 지정하면 rerun 후에도 사용자가 작업하던 탭이 그대로 유지됩니다.
    """
    st.session_state["_pending_state_action"] = {
        "action": action_type,
        "data": data,
        "preset": preset,
        "clean_previous": clean_previous,
        "success_msg": success_msg,
        "error_msg": error_msg,
        "target_tab": target_tab
    }
    st.rerun()

def clear_property_specs():
    """중개사무소 정보(참좋은공인중개사 신제환 대표)는 100% 안전하게 유지하고, 매물 정보만 깨끗하게 초기화합니다."""
    for k, v in BLANK_SPEC.items():
        if k in OFFICE_SPEC:
            continue # 신제환 소장님 고유 중개사무소 정보는 유지
        safe_set_session_state(f"ad_{k}", v)
    safe_set_session_state("item_no", "No. 001")
    safe_set_session_state("main_title", "")
    safe_set_session_state("sub_title", "")
    safe_set_session_state("feature_text", "")
    safe_set_session_state("thumb_trade_type", "매매")
    safe_set_session_state("thumb_price_text", "")
    safe_set_session_state("spec_line1", "")
    safe_set_session_state("spec_line2", "")
    safe_set_session_state("spec_line3", "")
    safe_set_session_state("spec_line4", "즉시입주 협의가능")
    safe_set_session_state("spec_line5", "")

def apply_crawled_or_doc_data(data: dict, clean_previous: bool = True):
    """크롤링 데이터 또는 공적서류 분석 데이터를 16대 점검항목 및 썸네일 세션에 일괄 주입합니다."""
    if not data:
        return

    # 신규 매물 등록 시 이전 매물 잔여 데이터(이전 매물 가격, 관리비, 준공일 등)가 섞이지 않도록 초기화
    # 단, 단편적인 정보(예: 관리비만 복사 등)일 때는 기존에 입력된 귀한 정보가 지워지지 않도록 보호
    has_major_fields = any(data.get(k) for k in ["price_text", "location", "area_exclusive", "dong_name", "main_title"])
    if clean_previous and has_major_fields:
        clear_property_specs()

    # 1. 16대 점검항목 적용
    if data.get("location"): safe_set_session_state("ad_location", str(data["location"]))
    if data.get("area_exclusive"): safe_set_session_state("ad_area_exclusive", str(data["area_exclusive"]))
    if data.get("area_supply"): safe_set_session_state("ad_area_supply", str(data["area_supply"]))
    elif data.get("area_exclusive"): safe_set_session_state("ad_area_supply", str(data["area_exclusive"]))
    if data.get("floor_info"): safe_set_session_state("ad_floor_info", str(data["floor_info"]))
    if data.get("room_bath"): safe_set_session_state("ad_room_bath", str(data["room_bath"]))
    if data.get("building_use"): safe_set_session_state("ad_building_use", str(data["building_use"]))
    if data.get("approval_date"): safe_set_session_state("ad_approval_date", str(data["approval_date"]))
    if data.get("households"): safe_set_session_state("ad_households", str(data["households"]))
    if data.get("parking"): safe_set_session_state("ad_parking", str(data["parking"]))
    if data.get("trade_type"): safe_set_session_state("ad_trade_type", str(data["trade_type"]))
    if data.get("price_text"): safe_set_session_state("ad_price_text", str(data["price_text"]))
    if data.get("direction"): safe_set_session_state("ad_direction", str(data["direction"]))
    if data.get("entrance_type"): safe_set_session_state("ad_entrance_type", str(data["entrance_type"]))
    if data.get("heating"): safe_set_session_state("ad_heating", str(data["heating"]))
    if data.get("move_in_date"): safe_set_session_state("ad_move_in_date", str(data["move_in_date"]))
    if data.get("maintenance_fee"): safe_set_session_state("ad_maintenance_fee", str(data["maintenance_fee"]))
    if data.get("maintenance_detail"):
        safe_set_session_state("ad_maintenance_detail", str(data["maintenance_detail"]))
    elif data.get("maintenance_fee"):
        _, auto_d = extract_maintenance_fee_and_detail(raw_fee=str(data["maintenance_fee"]))
        if auto_d:
            safe_set_session_state("ad_maintenance_detail", auto_d)
    if data.get("deposit_sub"): safe_set_session_state("ad_deposit_sub", str(data["deposit_sub"]))

    # 2. 썸네일 탭 연동
    if data.get("item_no"): safe_set_session_state("item_no", str(data["item_no"]))
    elif data.get("article_no"): safe_set_session_state("item_no", str(data["article_no"]))
    elif data.get("atclNo"): safe_set_session_state("item_no", str(data["atclNo"]))
    if data.get("main_title"): safe_set_session_state("main_title", str(data["main_title"]))
    if data.get("sub_title"): safe_set_session_state("sub_title", str(data["sub_title"]))
    if data.get("feature_text"): safe_set_session_state("feature_text", str(data["feature_text"]))
    if data.get("thumb_trade_type"): safe_set_session_state("thumb_trade_type", str(data["thumb_trade_type"]))
    elif data.get("trade_type"): safe_set_session_state("thumb_trade_type", str(data["trade_type"]))
    if data.get("thumb_price_text"): safe_set_session_state("thumb_price_text", str(data["thumb_price_text"]))
    elif data.get("price_text"):
        safe_set_session_state("thumb_price_text", format_thumb_price(str(data["price_text"])))
    if data.get("spec_line1"): safe_set_session_state("spec_line1", str(data["spec_line1"]))
    elif data.get("floor_info"): safe_set_session_state("spec_line1", str(data["floor_info"]))
    if data.get("spec_line2"): safe_set_session_state("spec_line2", str(data["spec_line2"]))
    elif data.get("area_exclusive"):
        s_area = data.get("area_supply", data["area_exclusive"])
        safe_set_session_state("spec_line2", f"공급 {s_area}㎡ / 전용 {data['area_exclusive']}㎡")
    if data.get("spec_line3"): safe_set_session_state("spec_line3", str(data["spec_line3"]))
    elif data.get("room_bath"): safe_set_session_state("spec_line3", str(data["room_bath"]))
    if data.get("spec_line4"): safe_set_session_state("spec_line4", str(data["spec_line4"]))
    elif data.get("move_in_date"): safe_set_session_state("spec_line4", str(data["move_in_date"]))
    if data.get("spec_line5"): safe_set_session_state("spec_line5", str(data["spec_line5"]))
    elif data.get("direction"): safe_set_session_state("spec_line5", str(data["direction"]))

def apply_commercial_crawled_or_doc_data(data: dict):
    """크롤링 데이터 또는 공적서류 분석 데이터를 상가 18대 점검항목 및 상가 썸네일 세션에 일괄 주입합니다."""
    if not data:
        return

    # 1. 상가 필수 점검항목 적용
    if data.get("location"):
        safe_set_session_state("comm_ad_location", str(data["location"]))
    if data.get("area_exclusive"):
        safe_set_session_state("comm_ad_area_exclusive", str(data["area_exclusive"]))
    if data.get("area_supply"):
        safe_set_session_state("comm_ad_area_contract", str(data["area_supply"]))
    elif data.get("area_contract"):
        safe_set_session_state("comm_ad_area_contract", str(data["area_contract"]))
    elif data.get("area_exclusive"):
        safe_set_session_state("comm_ad_area_contract", str(data["area_exclusive"]))
    if data.get("floor_info"):
        safe_set_session_state("comm_ad_floor_info", str(data["floor_info"]))
    if data.get("building_use"):
        safe_set_session_state("comm_ad_building_use", str(data["building_use"]))
    if data.get("zone_region"):
        safe_set_session_state("comm_ad_zone_region", str(data["zone_region"]))
    if data.get("zone_district"):
        safe_set_session_state("comm_ad_zone_district", str(data["zone_district"]))
    if data.get("structure"):
        safe_set_session_state("comm_ad_structure", str(data["structure"]))
    if data.get("approval_date"):
        safe_set_session_state("comm_ad_approval_date", str(data["approval_date"]))
    if data.get("parking"):
        safe_set_session_state("comm_ad_parking", str(data["parking"]))
    if data.get("trade_type"):
        safe_set_session_state("comm_ad_trade_type", str(data["trade_type"]))
    if data.get("price_text"):
        safe_set_session_state("comm_ad_price_text", str(data["price_text"]))
    if data.get("premium_fee"):
        safe_set_session_state("comm_ad_premium_fee", str(data["premium_fee"]))
    if data.get("direction"):
        d_val = str(data["direction"])
        if "출입구" not in d_val:
            d_val = re.sub(r"\s*\(.*?\)", "", d_val).strip() + " (주된 출입구 기준)"
        safe_set_session_state("comm_ad_direction", d_val)
    if data.get("move_in_date"):
        safe_set_session_state("comm_ad_move_in_date", str(data["move_in_date"]))
    if data.get("maintenance_fee"):
        safe_set_session_state("comm_ad_maintenance_fee", str(data["maintenance_fee"]))
    if data.get("maintenance_detail"):
        safe_set_session_state("comm_ad_maintenance_detail", str(data["maintenance_detail"]))
    elif data.get("maintenance_fee"):
        _, auto_cd = extract_maintenance_fee_and_detail(raw_fee=str(data["maintenance_fee"]))
        if auto_cd:
            safe_set_session_state("comm_ad_maintenance_detail", auto_cd)
    if data.get("restroom"):
        safe_set_session_state("comm_ad_restroom", str(data["restroom"]))
    if data.get("current_use"):
        safe_set_session_state("comm_ad_current_use", str(data["current_use"]))
    if data.get("recommended_use"):
        safe_set_session_state("comm_ad_recommended_use", str(data["recommended_use"]))
    if data.get("elevator"):
        elev_str = str(data["elevator"])
        cur_fac = st.session_state.get("comm_ad_facility_info", "")
        if "승강기" not in cur_fac and "엘리베이터" not in cur_fac:
            safe_set_session_state("comm_ad_facility_info", f"{cur_fac}, {elev_str}".strip(", "))
    elif data.get("facility_info"):
        safe_set_session_state("comm_ad_facility_info", str(data["facility_info"]))

    # 2. 상가 썸네일(임차 / 매매) 탭 실시간 연동
    is_sale_mode = "매매" in st.session_state.get("comm_ad_trade_type", "")
    py_val = ""
    try:
        if data.get("area_exclusive"):
            py_val = f"전용 {round(float(data['area_exclusive']) * 0.3025)}평"
    except Exception:
        pass

    loc_short = data.get("main_title") or (data.get("location", "").split(" ")[-1] if data.get("location") else "상가")
    
    if not is_sale_mode:
        # 임차 썸네일 동기화
        if loc_short:
            safe_set_session_state("comm_lease_main_title", f"{loc_short} 상가 임차")
            safe_set_session_state("comm_lease_top_badge", f"{loc_short} 추천 매물 · {st.session_state.get('comm_ad_premium_fee', '무권리')}")
        price_summary = st.session_state.get("comm_ad_price_text", "")
        if py_val and price_summary:
            safe_set_session_state("comm_lease_spec1", f"{py_val} | {price_summary}")
        elif py_val:
            safe_set_session_state("comm_lease_spec1", py_val)
        if data.get("recommended_use"):
            safe_set_session_state("comm_lease_spec2", f"추천 : {data['recommended_use']}")
    else:
        # 매매 썸네일 동기화
        if loc_short:
            safe_set_session_state("comm_sale_top_left", f"{loc_short} 상가 매매")
            safe_set_session_state("comm_sale_main_sub", f"안정적인 {loc_short} 상가 매매")
        if data.get("price_text"):
            safe_set_session_state("comm_sale_price_spec", f"매매가 {data['price_text']} | {st.session_state.get('comm_ad_structure', '철근콘크리트')} | {py_val}")

# ====================================================
# 🛡️ [위젯 충돌 원천 차단] 지연 상태 큐 최상단 일괄 처리기
# 위젯(Tab 1, Tab 2 등)이 렌더링되기 전 최상단에서 세션 스테이트를 안전하게 업데이트합니다.
# ====================================================
if "_pending_state_action" in st.session_state and st.session_state["_pending_state_action"]:
    pending_act = st.session_state.pop("_pending_state_action")
    act_type = pending_act.get("action")
    if act_type == "apply_apt":
        apply_crawled_or_doc_data(pending_act["data"], clean_previous=pending_act.get("clean_previous", True))
    elif act_type == "apply_comm":
        apply_commercial_crawled_or_doc_data(pending_act["data"])
    elif act_type == "clear_apt":
        clear_property_specs()
    elif act_type == "preset_apt":
        apply_preset(pending_act["preset"])
    elif act_type == "preset_comm":
        apply_comm_preset(pending_act["preset"])

    if pending_act.get("target_tab"):
        st.session_state["target_main_tab"] = pending_act["target_tab"]

    if pending_act.get("success_msg"):
        if "comm" in act_type:
            st.session_state["last_comm_applied_msg"] = pending_act["success_msg"]
        else:
            st.session_state["last_applied_msg"] = pending_act["success_msg"]
    if pending_act.get("error_msg"):
        st.session_state["last_applied_err"] = pending_act["error_msg"]


# -------------------------
# 상단 타이틀 & 모바일 접속 안내
# -------------------------
col_h1, col_h2 = st.columns([2.2, 0.8])
with col_h1:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 5px;">
        <span style="font-size: 32px;">🏢</span>
        <div>
            <h2 style="margin: 0; font-weight: 800; color: #1E2022; font-size: 24px;">부동산 블로그 썸네일 & 네이버광고</h2>
            <p style="margin: 3px 0 0 0; color: #2D3748; font-size: 13.5px; line-height: 1.5;">
                🏢 <b>참좋은공인중개사사무소</b> (대표: 신제환 ☎ 010-9667-4201) &nbsp;|&nbsp; 📍 <b>소재지:</b> 부산광역시 사상구 강선로 9, 1층 &nbsp;|&nbsp; 📜 <b>등록번호:</b> 제 26530-2026-00009 호
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
with col_h2:
    if st.button("🔒 로그아웃 (비밀번호 잠금)", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ----------------------------------------------------
# ⚡ 스마트 자동완성 콘솔 헬퍼 함수 (중개대상물 표시 탭 전용)
# 요구사항 2번: 썸네일에서는 이 마스터 콘솔 안내문구가 나오지 않습니다.
# 요구사항 3번: [새 매물 빈 양식 초기화], [사상 중흥 예시], [센텀 오피스텔 예시] 3개 버튼은 완전 삭제되었습니다.
# ----------------------------------------------------
def render_smart_autocomplete_console(target_prop_type="apt"):
    """네이버 복사 텍스트 / 건축물대장 스크립트·PDF / 매물번호 크롤링 1초 자동완성 콘솔"""
    with st.expander("⚡ [원클릭 1초 스마트 자동완성 콘솔] 네이버 복사 텍스트 / 건축물대장 스크립트 / 매물번호 입력", expanded=False):
        st.markdown("""
        <div style="font-size:13.5px; color:#1A365D; background:#F0F7FF; border:1.5px solid #90CDF4; padding:10px 14px; border-radius:8px; margin-bottom:10px;">
            🚀 <b>네이버 매물 화면 복사 텍스트</b>나 <b>건축물대장 텍스트(스크립트)·PDF</b>를 넣으시면 
            점검항목과 썸네일 데이터가 즉시 0.1초 만에 자동 완성됩니다!
        </div>
        """, unsafe_allow_html=True)

        top_tab_num, top_tab_clip, top_tab_script = st.tabs([
            "🔍 네이버 매물번호 / URL 크롤링",
            "📋 네이버 화면 복사 텍스트 붙여넣기 (가장 확실 & 추천)",
            "📄 건축물대장 텍스트(스크립트) & PDF 업로드"
        ])

        with top_tab_num:
            c_top_n1, c_top_n2 = st.columns([2.5, 1])
            with c_top_n1:
                top_article_val = st.text_input(
                    "네이버 매물 번호 또는 URL",
                    placeholder="예: 2428591234 또는 URL",
                    key="top_input_article_no"
                )
            with c_top_n2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                top_btn_crawl = st.button("🚀 실시간 크롤링 시도", type="primary", use_container_width=True, key="top_btn_crawl_run")

            if top_btn_crawl:
                if top_article_val.strip():
                    with st.spinner("네이버 부동산 매물 정보 실시간 조회 중..."):
                        is_ok, msg, c_data = crawl_naver_article(top_article_val.strip())
                        if is_ok:
                            queue_state_update("apply_apt", data=c_data, clean_previous=True, success_msg=f"🎉 {msg} 즉시 자동 반영되었습니다.")
                        else:
                            st.error(f"⚠️ {msg}")
                else:
                    st.warning("매물 번호 또는 링크 URL을 입력해주세요.")

        with top_tab_clip:
            top_clip_text = st.text_area(
                "네이버 매물 상세 복사 텍스트",
                height=110,
                placeholder="예:\n사상 중흥S-클래스 105동 매매 6억 2,000만원\n아파트 공급 111.42㎡ / 전용 79.85㎡, 25/36층, 남동향\n관리비 18만원...",
                key="top_input_naver_clip"
            )
            if st.button("⚡ 붙여넣은 텍스트 0.1초 분석 & 점검표 즉시 자동완성", type="primary", use_container_width=True, key="top_btn_parse_clip"):
                if top_clip_text.strip():
                    parsed_c = parse_naver_clipboard_text(top_clip_text)
                    if parsed_c:
                        queue_state_update("apply_apt", data=parsed_c, clean_previous=True, success_msg=f"🎉 매물 [{parsed_c.get('main_title', '매물')}] 분석 완료! 점검항목과 썸네일에 즉시 자동 반영되었습니다.")
                    else:
                        st.warning("붙여넣은 텍스트에서 매물 정보를 식별하지 못했습니다. 내용을 확인해주세요.")
                else:
                    st.warning("네이버 매물 텍스트를 먼저 붙여넣어 주세요.")

        with top_tab_script:
            top_doc_tab1, top_doc_tab2 = st.tabs([
                "📋 대장 텍스트 통째로 붙여넣기 (정부24/세움터)",
                "📁 대장 PDF 파일 업로드"
            ])
            with top_doc_tab1:
                top_script_text = st.text_area(
                    "건축물대장 열람 복사 텍스트 (스크립트)",
                    height=120,
                    placeholder="대지위치: 부산시 사상구 덕포동 220\n건축물명칭: 사상 중흥S-클래스 제105동 제2501호\n층별: 25층\n전유부분 면적: 79.85㎡...",
                    key="top_input_script_doc"
                )
                if st.button("🔍 붙여넣은 대장 스크립트 분석 & 즉시 적용", type="primary", use_container_width=True, key="top_btn_parse_script"):
                    if top_script_text.strip():
                        doc_lbl, parsed_doc = parse_raw_script_document(top_script_text)
                        if parsed_doc:
                            queue_state_update("apply_apt", data=parsed_doc, clean_previous=True, success_msg=f"🎉 [{doc_lbl}] 분석 완료! 점검표와 썸네일에 즉시 반영되었습니다.")
                        else:
                            st.warning("대장 텍스트에서 건축물 정보를 식별하지 못했습니다.")
                    else:
                        st.warning("대장 텍스트를 먼저 붙여넣어 주세요.")

            with top_doc_tab2:
                top_uploaded_pdf = st.file_uploader(
                    "건축물대장 PDF 파일",
                    type=["pdf"],
                    key="top_pdf_uploader_key"
                )
                if top_uploaded_pdf:
                    if st.button("🚀 업로드된 PDF 정밀 분석 & 즉시 적용", type="primary", use_container_width=True, key="top_btn_parse_pdf"):
                        try:
                            p_t, p_res, _ = parse_official_document(top_uploaded_pdf, top_uploaded_pdf.name)
                            if p_res:
                                queue_state_update("apply_apt", data=p_res, clean_previous=True, success_msg=f"🎉 [{p_t}] 분석 완료! 즉시 반영되었습니다.")
                            else:
                                st.error("PDF 파일에서 텍스트를 추출하지 못했습니다.")
                        except Exception as e:
                            st.error(f"PDF 분석 오류: {e}")

# ----------------------------------------------------
# 🌟 요구사항 4번: 최상위 2대 메인 탭 (■ "썸네일" / ■ "중개대상물표시")
# ----------------------------------------------------
if st.session_state.get("last_applied_msg"):
    st.success(st.session_state["last_applied_msg"])

# ----------------------------------------------------
# 🏡 주택 점검표 기본값 세션 초기화
# ----------------------------------------------------
if "house_ad_location" not in st.session_state: st.session_state.house_ad_location = "부산광역시 사상구 덕포동"
if "house_ad_area_land" not in st.session_state: st.session_state.house_ad_area_land = "192.0"
if "house_ad_area_gross" not in st.session_state: st.session_state.house_ad_area_gross = "145.2"
if "house_ad_floor_info" not in st.session_state: st.session_state.house_ad_floor_info = "지상 2층 / 지하 0층"
if "house_ad_room_bath" not in st.session_state: st.session_state.house_ad_room_bath = "방 4 / 욕실 2개"
if "house_ad_maintenance_fee" not in st.session_state: st.session_state.house_ad_maintenance_fee = "자체관리 (수도/전기/가스 실사용량 별도)"
if "house_ad_trade_type" not in st.session_state: st.session_state.house_ad_trade_type = "매매"
if "house_ad_price_text" not in st.session_state: st.session_state.house_ad_price_text = "3억 8,000만 원"
if "house_ad_direction" not in st.session_state: st.session_state.house_ad_direction = "남향 (거실 기준)"
if "house_ad_parking" not in st.session_state: st.session_state.house_ad_parking = "총 1대 가능 (마당/자주식)"
if "house_ad_heating" not in st.session_state: st.session_state.house_ad_heating = "개별난방 / 도시가스"
if "house_ad_move_in_date" not in st.session_state: st.session_state.house_ad_move_in_date = "즉시입주 협의가능"
if "house_ad_building_use" not in st.session_state: st.session_state.house_ad_building_use = "단독주택"
if "house_ad_structure" not in st.session_state: st.session_state.house_ad_structure = "벽돌구조 / 연와조"
if "house_ad_approval_date" not in st.session_state: st.session_state.house_ad_approval_date = "1998년 05월 12일"
if "house_ad_feature" not in st.session_state: st.session_state.house_ad_feature = "마당 넓음 · 올리모델링 완료"
if "house_ad_include_office" not in st.session_state: st.session_state.house_ad_include_office = True
if "house_ad_as_name" not in st.session_state: st.session_state.house_ad_as_name = ""
if "house_ad_as_phone" not in st.session_state: st.session_state.house_ad_as_phone = ""

# ----------------------------------------------------
# 🏭 공장 점검표 기본값 세션 초기화
# ----------------------------------------------------
if "factory_ad_location" not in st.session_state: st.session_state.factory_ad_location = "부산광역시 사상구 삼락동 사상공단"
if "factory_ad_area_land" not in st.session_state: st.session_state.factory_ad_area_land = "826.5"
if "factory_ad_area_gross" not in st.session_state: st.session_state.factory_ad_area_gross = "550.0"
if "factory_ad_zoning" not in st.session_state: st.session_state.factory_ad_zoning = "일반공업지역 / 공장용지"
if "factory_ad_building_use" not in st.session_state: st.session_state.factory_ad_building_use = "공장 (제조업소)"
if "factory_ad_height" not in st.session_state: st.session_state.factory_ad_height = "처마 8.5m / 최고 9.5m"
if "factory_ad_hoist" not in st.session_state: st.session_state.factory_ad_hoist = "5톤 1기 완비"
if "factory_ad_power" not in st.session_state: st.session_state.factory_ad_power = "150kW 수전설비"
if "factory_ad_road" not in st.session_state: st.session_state.factory_ad_road = "8m 포장도로 (츄레라/트레일러 진입 원활)"
if "factory_ad_trade_type" not in st.session_state: st.session_state.factory_ad_trade_type = "매매"
if "factory_ad_price_text" not in st.session_state: st.session_state.factory_ad_price_text = "18억 5,000만 원"
if "factory_ad_maintenance_fee" not in st.session_state: st.session_state.factory_ad_maintenance_fee = "자체관리"
if "factory_ad_parking" not in st.session_state: st.session_state.factory_ad_parking = "옥외 마당 5대 이상"
if "factory_ad_move_in_date" not in st.session_state: st.session_state.factory_ad_move_in_date = "즉시입주 협의가능"
if "factory_ad_approval_date" not in st.session_state: st.session_state.factory_ad_approval_date = "2015년 10월 20일"
if "factory_ad_direction" not in st.session_state: st.session_state.factory_ad_direction = "남향 (주출입구 기준)"
if "factory_ad_include_office" not in st.session_state: st.session_state.factory_ad_include_office = True
if "factory_ad_as_name" not in st.session_state: st.session_state.factory_ad_as_name = ""
if "factory_ad_as_phone" not in st.session_state: st.session_state.factory_ad_as_phone = ""


# ====================================================
# [ 탭 1-1 ] 아파트 썸네일 생성기
# ====================================================
def render_tab_apt_thumb():

    col_t_left, col_t_right = st.columns([1.25, 0.75])
    
    with col_t_left:
        # 요구사항 1번: 레이아웃 모드를 우측으로 이동하고 좌측에 디자인 모드 배치 (영구 저장 지원)
        selected_design, layout_mode, photo_width_ratio = render_design_and_layout_controls("apt_thumb", default_design_name="🍊 참좋은 시그니처 오렌지 (기본)")

        # 사진 업로드
        uploaded_bg = st.file_uploader(
            "📸 현장 사진 업로드 (스마트폰 촬영 사진 즉시 지원)",
            type=["jpg", "jpeg", "png", "webp"],
            key="thumb_file_uploader"
        )
        if uploaded_bg:
            st.session_state["saved_apt_uploaded_bg"] = uploaded_bg
        else:
            uploaded_bg = st.session_state.get("saved_apt_uploaded_bg")

        with st.expander("🔍 사진 위치 / 확대 미세 조정", expanded=False):
            c_z1, c_z2, c_z3 = st.columns(3)
            with c_z1:
                bg_zoom = st.slider("사진 확대/축소", 0.6, 2.0, 1.0, 0.05)
            with c_z2:
                bg_offset_x = st.slider("사진 좌우 이동 (px)", -450, 450, 0, 10)
            with c_z3:
                bg_offset_y = st.slider("사진 상하 이동 (px)", -450, 450, 0, 10)

        # 썸네일 렌더링
        spec_lines = [
            st.session_state.spec_line1,
            st.session_state.spec_line2,
            st.session_state.spec_line3,
            st.session_state.spec_line4,
            st.session_state.spec_line5
        ]
        
        with st.spinner("고화질 썸네일 렌더링 중..."):
            thumbnail_img = render_thumbnail(
                bg_image=uploaded_bg,
                item_no=st.session_state.item_no,
                main_title=st.session_state.main_title,
                sub_title=st.session_state.sub_title,
                feature_text=st.session_state.feature_text,
                trade_type=st.session_state.thumb_trade_type,
                price_text=st.session_state.thumb_price_text,
                spec_lines=spec_lines,
                layout_mode=layout_mode,
                photo_width_ratio=photo_width_ratio,
                bg_offset_x=bg_offset_x,
                bg_offset_y=bg_offset_y,
                bg_zoom=bg_zoom,
                show_footer=st.session_state.thumb_show_footer,
                footer_text=st.session_state.thumb_footer_text,
                primary_color=selected_design["primary_color"],
                accent_color=selected_design["accent_color"],
                card_bg=selected_design["card_bg"],
                overlay_image=selected_design.get("overlay_image_path"),
                deal_done=st.session_state.get("apt_deal_done", False),
                deal_color=st.session_state.get("apt_deal_color", "#FF0101")
            )

        st.image(thumbnail_img, caption="블로그 썸네일 실시간 완성 미리보기 (1080 x 1080 px)", use_container_width=True)

    with col_t_right:
        st.markdown("### 🛠️ 썸네일 텍스트 수정")
        st.text_input("🏷️ 물건 번호", key="item_no")
        st.text_input("🏢 메인 타이틀 (아파트명)", key="main_title")
        st.text_input("📍 서브 타이틀 (동/단지명)", key="sub_title")
        st.text_input("✨ 매물 핵심 특징", key="feature_text", placeholder="직접 입력하세요 (예: 1572세대 대단지 아파트)")
        
        c_tr1, c_tr2 = st.columns([1, 1.3])
        with c_tr1:
            trade_opts = ["매매", "전세", "월세", "분양", "급매"]
            if st.session_state.thumb_trade_type not in trade_opts:
                trade_opts.append(st.session_state.thumb_trade_type)
            st.selectbox("거래 형태", trade_opts, key="thumb_trade_type")
        with c_tr2:
            st.text_input("금액 (예: 6억2천)", key="thumb_price_text")

        st.markdown("#### 📋 5대 스펙 텍스트")
        st.text_input("1행: 해당동 / 층수", key="spec_line1")
        st.text_input("2행: 공급/전용면적", key="spec_line2")
        st.text_input("3행: 방/욕실 수", key="spec_line3")
        st.text_input("4행: 입주시기", key="spec_line4")
        st.text_input("5행: 방향 및 특징", key="spec_line5")

        st.markdown("#### 🚩 매물 상태 (거래완료 표시)")
        render_deal_done_controller("apt")

        st.markdown("#### 🏢 하단 띠지 (중개사무소 정보)")
        st.checkbox(
            "하단 띠지 표시 (체크 해제 시 전체 사진 영역 확장)",
            key="thumb_show_footer",
            help="소공 또는 타 중개사 협업 시 띠지 없이 매물 사진만 1080px 꽉 차게 내보낼 수 있습니다."
        )
        if st.session_state.thumb_show_footer:
            st.text_input(
                "띠지 문구 (소공/직원 커스텀 문구 가능)",
                key="thumb_footer_text",
                placeholder="미입력 시: 참좋은공인중개사사무소 (대표 신제환) ☎ 010-9667-4201"
            )
            c_f_tel1, c_f_tel2 = st.columns(2)
            with c_f_tel1:
                st.text_input(
                    "사무실 연락처 (창문 전단지용)",
                    key="office_tel_input",
                    value=st.session_state.get("office_tel_input", "010-9667-4201"),
                    help="창문 포스터 하단 띠지에 '사무실 연락처 : [번호]' 로 표시됩니다."
                )
            with c_f_tel2:
                st.text_input(
                    "📱 담당자 연락처 (창문 전단지용)",
                    key="assistant_phone_input",
                    value=st.session_state.get("assistant_phone_input", ""),
                    placeholder="예: 010-9667-4201",
                    help="연락처를 넣으시면 창문 전단지에 '담당자 : 연락처' 강조 배지가 들어갑니다."
                )

        # 1. 썸네일 이미지 다운로드 바이트
        img_byte_arr = io.BytesIO()
        thumbnail_img.save(img_byte_arr, format="PNG", quality=98)
        img_bytes = img_byte_arr.getvalue()

        clean_title = re.sub(r'[^\w\s-]', '', (st.session_state.main_title or "매물")).strip().replace(" ", "_")
        clean_price = re.sub(r'[^\w\s-]', '', (st.session_state.thumb_price_text or "")).strip().replace(" ", "")
        download_filename = f"부동산썸네일_{clean_title}_{st.session_state.thumb_trade_type}_{clean_price}.png"

        st.markdown("<hr style='margin: 15px 0 12px 0;'/>", unsafe_allow_html=True)
        st.markdown("### 📥 출력 및 저장 옵션")

        render_download_save_controller(
            file_bytes=img_bytes,
            default_filename=download_filename,
            label_download="📥 1080x1080 썸네일 저장",
            key_prefix="apt_thumb_down"
        )

        # 첫번째 화면에서 바로 A4 포스터 인쇄 및 파일저장 연동
        with st.spinner("창문 부착용 A4 포스터 준비 중..."):
            a4_poster_img = render_a4_window_poster(
                thumbnail_img=thumbnail_img,
                bg_image=uploaded_bg,
                item_no=st.session_state.item_no,
                main_title=st.session_state.main_title,
                sub_title=st.session_state.sub_title,
                feature_text=st.session_state.feature_text,
                trade_type=st.session_state.thumb_trade_type,
                price_text=st.session_state.thumb_price_text,
                spec_lines=spec_lines,
                office_name=st.session_state.get("ad_office_name", "참좋은공인중개사사무소"),
                office_owner=st.session_state.get("ad_office_owner", "신제환"),
                office_phone=st.session_state.get("ad_office_phone", "010-9667-4201"),
                office_reg_no=st.session_state.get("ad_office_reg_no", "제 26530-2026-00009 호"),
                office_address=st.session_state.get("ad_office_address", "부산광역시 사상구 강선로 9, 1층"),
                is_commercial=False,
                office_tel=st.session_state.get("office_tel_input", "010-9667-4201"),
                assistant_phone=st.session_state.get("assistant_phone_input", ""),
                primary_color_override=selected_design.get("primary_color", "#F48A26"),
                accent_color_override=selected_design.get("accent_color", "#EB5E28")
            )
            a4_io = io.BytesIO()
            a4_poster_img.save(a4_io, format="PNG", quality=98)
            a4_bytes = a4_io.getvalue()
            a4_filename = f"창문부착용_아파트포스터_{clean_title}_{clean_price}.png"

        render_download_save_controller(
            file_bytes=a4_bytes,
            default_filename=a4_filename,
            label_download="300dpi 초고화질 A4포스터 파일저장",
            key_prefix="apt_thumb_a4_down",
            is_poster=True,
            print_bytes=a4_bytes
        )

        st.info("💡 아파트 썸네일을 만드셨다면, 상단의 **'🖨️ 창문부착용A4'** 또는 **'📋 중개대상물표시'** 탭을 클릭하여 포스터 출력과 네이버 광고 서식을 바로 확인하세요!")


# ====================================================
# [ 탭 2 ] 상가 썸네일 생성기 (임차 & 매매 2대 모드)
# ====================================================


# ====================================================
# [ 탭 1-2 ] 주택 썸네일 생성기 (단독·다가구·전원주택)
# ====================================================
def render_tab_house_thumb():
    col_t_left, col_t_right = st.columns([1.25, 0.75])
    
    with col_t_left:
        # 빠른 추천 프리셋
        col_hpr1, col_hpr2, col_hpr3 = st.columns([1, 1, 1])
        with col_hpr1:
            if st.button("⚡ 덕포동 마당 단독주택 (매매)", use_container_width=True, key="btn_preset_house_1"):
                st.session_state.house_item_no = "No. H-001"
                st.session_state.house_main_title = "사상 덕포동 단독주택"
                st.session_state.house_sub_title = "햇살 가득 남향 코너 마당"
                st.session_state.house_feature_text = "대지 58평 · 올리모델링 완료"
                st.session_state.house_trade_type = "매매"
                st.session_state.house_price_text = "3억 8천"
                st.session_state.house_spec1 = "지상 2층 / 단독주택"
                st.session_state.house_spec2 = "대지 192㎡ / 연면적 145㎡"
                st.session_state.house_spec3 = "방 4개 / 욕실 2개 (마당有)"
                st.session_state.house_spec4 = "즉시입주 협의가능"
                st.session_state.house_spec5 = "정남향 / 주차 1대 가능"
                # 점검표도 동기화
                st.session_state.house_ad_location = "부산광역시 사상구 덕포동"
                st.session_state.house_ad_price_text = "3억 8,000만 원"
                st.session_state.house_ad_trade_type = "매매"
                st.session_state.house_ad_area_land = "192.0"
                st.session_state.house_ad_area_gross = "145.2"
                st.session_state.house_ad_floor_info = "지상 2층 / 지하 0층"
                st.session_state.house_ad_room_bath = "방 4 / 욕실 2개"
                st.session_state.house_ad_direction = "남향 (거실 기준)"
                st.session_state.house_ad_parking = "총 1대 (마당/자주식)"
                st.session_state.house_ad_move_in_date = "즉시입주 협의가능"
                st.rerun()
        with col_hpr2:
            if st.button("⚡ 모라동 올리모델링 주택 (매매)", use_container_width=True, key="btn_preset_house_2"):
                st.session_state.house_item_no = "No. H-002"
                st.session_state.house_main_title = "사상 모라동 리모델링 주택"
                st.session_state.house_sub_title = "역세권 도보 5분 생활권"
                st.session_state.house_feature_text = "샤시·배관 올교체 첫입주"
                st.session_state.house_trade_type = "매매"
                st.session_state.house_price_text = "2억 9천"
                st.session_state.house_spec1 = "지상 2층 단독주택"
                st.session_state.house_spec2 = "대지 132㎡ / 연면적 98㎡"
                st.session_state.house_spec3 = "방 3개 / 욕실 2개"
                st.session_state.house_spec4 = "즉시입주 협의가능"
                st.session_state.house_spec5 = "남동향 / 일조권 우수"
                # 점검표도 동기화
                st.session_state.house_ad_location = "부산광역시 사상구 모라동"
                st.session_state.house_ad_price_text = "2억 9,000만 원"
                st.session_state.house_ad_trade_type = "매매"
                st.session_state.house_ad_area_land = "132.0"
                st.session_state.house_ad_area_gross = "98.5"
                st.session_state.house_ad_floor_info = "지상 2층 / 지하 0층"
                st.session_state.house_ad_room_bath = "방 3 / 욕실 2개"
                st.session_state.house_ad_direction = "남동향 (거실 기준)"
                st.session_state.house_ad_parking = "인근 거주자 우선 주차"
                st.session_state.house_ad_move_in_date = "즉시입주 협의가능"
                st.rerun()
        with col_hpr3:
            st.caption("👈 버튼을 누르면 추천 주택 예시가 즉시 채워집니다.")

        # 요구사항 1번: 디자인모드 및 레이아웃 모드
        selected_design, layout_mode, photo_width_ratio = render_design_and_layout_controls("house_thumb", default_design_name="🌿 싱그러운 에메랄드 그린")

        # 사진 업로드
        uploaded_house_bg = st.file_uploader(
            "📸 주택 현장 실물/외관 사진 업로드 (스마트폰 촬영 사진 즉시 지원)",
            type=["jpg", "jpeg", "png", "webp"],
            key="house_thumb_uploader"
        )
        if uploaded_house_bg:
            st.session_state["saved_house_uploaded_bg"] = uploaded_house_bg
        else:
            uploaded_house_bg = st.session_state.get("saved_house_uploaded_bg")

        with st.expander("🔍 사진 위치 / 확대 미세 조정", expanded=False):
            h_z1, h_z2, h_z3 = st.columns(3)
            with h_z1:
                house_bg_zoom = st.slider("사진 확대/축소", 0.6, 2.0, 1.0, 0.05, key="house_bg_zoom")
            with h_z2:
                house_bg_ox = st.slider("사진 좌우 이동 (px)", -450, 450, 0, 10, key="house_bg_ox")
            with h_z3:
                house_bg_oy = st.slider("사진 상하 이동 (px)", -450, 450, 0, 10, key="house_bg_oy")

        # 썸네일 렌더링
        house_specs = [
            st.session_state.house_spec1,
            st.session_state.house_spec2,
            st.session_state.house_spec3,
            st.session_state.house_spec4,
            st.session_state.house_spec5
        ]

        with st.spinner("고화질 주택 썸네일 렌더링 중..."):
            house_thumb_img = render_thumbnail(
                bg_image=uploaded_house_bg,
                item_no=st.session_state.house_item_no,
                main_title=st.session_state.house_main_title,
                sub_title=st.session_state.house_sub_title,
                feature_text=st.session_state.house_feature_text,
                trade_type=st.session_state.house_trade_type,
                price_text=st.session_state.house_price_text,
                spec_lines=house_specs,
                layout_mode=layout_mode,
                photo_width_ratio=photo_width_ratio,
                bg_offset_x=house_bg_ox,
                bg_offset_y=house_bg_oy,
                bg_zoom=house_bg_zoom,
                show_footer=st.session_state.house_show_footer,
                footer_text=st.session_state.house_footer_text,
                primary_color=selected_design["primary_color"],
                accent_color=selected_design["accent_color"],
                card_bg=selected_design["card_bg"],
                overlay_image=selected_design.get("overlay_image_path"),
                deal_done=st.session_state.get("house_deal_done", False),
                deal_color=st.session_state.get("house_deal_color", "#FF0101")
            )

        st.image(house_thumb_img, caption="주택 블로그 썸네일 실시간 미리보기 (1080 x 1080 px)", use_container_width=True)

    with col_t_right:
        st.markdown("### 🛠️ 주택 썸네일 텍스트 수정")
        st.text_input("🏷️ 물건 번호", key="house_item_no")
        st.text_input("🏡 메인 타이틀 (주택명)", key="house_main_title")
        st.text_input("📍 서브 타이틀 (동/지역명)", key="house_sub_title")
        st.text_input("✨ 매물 핵심 특징", key="house_feature_text", placeholder="직접 입력하세요 (예: 대지 45평 · 올리모델링 첫입주)")

        c_ht1, c_ht2 = st.columns([1, 1.3])
        with c_ht1:
            h_trade_opts = ["매매", "전세", "월세", "급매"]
            if st.session_state.house_trade_type not in h_trade_opts:
                h_trade_opts.append(st.session_state.house_trade_type)
            st.selectbox("거래 형태", h_trade_opts, key="house_trade_type")
        with c_ht2:
            st.text_input("금액 (예: 3억 8천)", key="house_price_text")

        st.markdown("#### 📋 5대 스펙 텍스트")
        st.text_input("1행: 층수 / 구조", key="house_spec1")
        st.text_input("2행: 대지 / 연면적", key="house_spec2")
        st.text_input("3행: 방/욕실 수 (마당 등)", key="house_spec3")
        st.text_input("4행: 입주시기", key="house_spec4")
        st.text_input("5행: 방향 및 주차", key="house_spec5")

        st.markdown("#### 🚩 매물 상태 (거래완료 표시)")
        render_deal_done_controller("house")

        st.markdown("#### 🏢 하단 띠지 (중개사무소 정보)")
        st.checkbox("하단 띠지 표시 (체크 해제 시 전체 사진 영역 확장)", key="house_show_footer")
        if st.session_state.house_show_footer:
            st.text_input("띠지 문구 (소공/직원 커스텀 가능)", key="house_footer_text", placeholder="미입력 시: 참좋은공인중개사사무소 (대표 신제환) ☎ 010-9667-4201")
            c_hf1, c_hf2 = st.columns(2)
            with c_hf1:
                st.text_input("사무실 연락처 (창문 전단지용)", key="house_office_tel", value=st.session_state.get("house_office_tel", "010-9667-4201"))
            with c_hf2:
                st.text_input("📱 담당자 연락처 (창문 전단지용)", key="house_assistant_phone", value=st.session_state.get("house_assistant_phone", ""), placeholder="예: 010-9667-4201")

        # 다운로드 바이트
        h_thumb_io = io.BytesIO()
        house_thumb_img.save(h_thumb_io, format="PNG", quality=98)
        h_thumb_bytes = h_thumb_io.getvalue()

        clean_h_title = re.sub(r'[^\w\s-]', '', (st.session_state.house_main_title or "주택")).strip().replace(" ", "_")
        clean_h_price = re.sub(r'[^\w\s-]', '', (st.session_state.house_price_text or "")).strip().replace(" ", "")
        h_down_name = f"주택썸네일_{clean_h_title}_{st.session_state.house_trade_type}_{clean_h_price}.png"

        st.markdown("<hr style='margin: 15px 0 12px 0;'/>", unsafe_allow_html=True)
        st.markdown("### 📥 출력 및 저장 옵션")

        render_download_save_controller(
            file_bytes=h_thumb_bytes,
            default_filename=h_down_name,
            label_download="📥 1080x1080 주택 썸네일 저장",
            key_prefix="house_thumb_down"
        )


# ====================================================
# [ 탭 1-3 ] 상가 썸네일 생성기 (임차 & 매매 2대 모드)
# ====================================================
def render_tab_comm_thumb():

    col_ct_left, col_ct_right = st.columns([1.25, 0.75])
    
    with col_ct_left:
        # 상가 모드 선택 (임차 vs 매매)
        c_mode_opts = ["🔑 상가 임차 (월세)", "💰 상가 매매 (수익형)"]
        selected_comm_mode = st.radio(
            "상가 매물 유형 선택",
            options=c_mode_opts,
            index=0 if "임차" in st.session_state.comm_thumb_mode else 1,
            horizontal=True,
            key="comm_thumb_mode_selector"
        )
        st.session_state.comm_thumb_mode = selected_comm_mode
        is_sale_mode = "매매" in selected_comm_mode

        # 빠른 추천 프리셋
        col_cpr1, col_cpr2, col_cpr3 = st.columns([1, 1, 1])
        with col_cpr1:
            if st.button("⚡ 사상역 코너 상가 임차 예시", use_container_width=True):
                apply_comm_preset("lease")
                st.rerun()
        with col_cpr2:
            if st.button("⚡ 사상 핵심상권 상가 매매 예시", use_container_width=True):
                apply_comm_preset("sale")
                st.rerun()
        with col_cpr3:
            st.caption("👈 버튼을 누르면 추천 예시가 즉시 채워집니다.")

        # 요구사항 1번: 상가 디자인모드 및 레이아웃 모드
        selected_comm_design, comm_layout_mode, comm_photo_ratio = render_design_and_layout_controls("comm_thumb", default_design_name="👑 럭셔리 골드 (상가·수익형)")

        # 내가 찍어온 사진 업로드
        uploaded_comm_bg = st.file_uploader(
            "📸 내가 찍어온 현장 상가 사진 업로드 (스마트폰 촬영 사진 즉시 지원)",
            type=["jpg", "jpeg", "png", "webp"],
            key="comm_bg_uploader_key"
        )
        if uploaded_comm_bg:
            st.session_state["saved_comm_uploaded_bg"] = uploaded_comm_bg
        else:
            uploaded_comm_bg = st.session_state.get("saved_comm_uploaded_bg")

        with st.expander("🔍 사진 위치 / 확대 미세 조정", expanded=False):
            cz1, cz2, cz3 = st.columns(3)
            with cz1:
                comm_bg_zoom = st.slider("사진 확대/축소", 0.6, 2.0, 1.0, 0.05, key="comm_bg_zoom_slider")
            with cz2:
                comm_bg_offset_x = st.slider("사진 좌우 이동 (px)", -450, 450, 0, 10, key="comm_bg_offset_x_slider")
            with cz3:
                comm_bg_offset_y = st.slider("사진 상하 이동 (px)", -450, 450, 0, 10, key="comm_bg_offset_y_slider")

        # 실시간 고화질 렌더링
        with st.spinner("고화질 상가 썸네일 렌더링 중..."):
            if not is_sale_mode:
                comm_thumb_img = render_commercial_lease_thumbnail(
                    bg_image=uploaded_comm_bg,
                    top_badge_text=st.session_state.comm_lease_top_badge,
                    catchphrase_top=st.session_state.comm_lease_cp_top,
                    main_title=st.session_state.comm_lease_main_title,
                    catchphrase_bot=st.session_state.comm_lease_cp_bot,
                    pin_bubble_text=st.session_state.comm_lease_pin_bubble,
                    show_pin=st.session_state.comm_lease_show_pin,
                    spec_line1=st.session_state.comm_lease_spec1,
                    spec_line2=st.session_state.comm_lease_spec2,
                    bg_offset_x=comm_bg_offset_x,
                    bg_offset_y=comm_bg_offset_y,
                    bg_zoom=comm_bg_zoom,
                    show_footer=st.session_state.comm_lease_show_footer,
                    office_name=st.session_state.comm_lease_office,
                    broker_title=st.session_state.comm_lease_broker,
                    deal_done=st.session_state.get("comm_deal_done", False),
                    deal_color=st.session_state.get("comm_deal_color", "#FF0101")
                )
            else:
                comm_thumb_img = render_commercial_sale_thumbnail(
                    bg_image=uploaded_comm_bg,
                    top_badge_left=st.session_state.comm_sale_top_left,
                    top_badge_right=st.session_state.comm_sale_top_right,
                    show_chart_icon=st.session_state.comm_sale_show_chart,
                    main_highlight_title=st.session_state.comm_sale_main_hl,
                    main_sub_title=st.session_state.comm_sale_main_sub,
                    price_spec_text=st.session_state.comm_sale_price_spec,
                    bg_offset_x=comm_bg_offset_x,
                    bg_offset_y=comm_bg_offset_y,
                    bg_zoom=comm_bg_zoom,
                    show_footer=st.session_state.comm_sale_show_footer,
                    office_name=st.session_state.comm_sale_office,
                    broker_title=st.session_state.comm_sale_broker,
                    deal_done=st.session_state.get("comm_deal_done", False),
                    deal_color=st.session_state.get("comm_deal_color", "#FF0101")
                )

        caption_title = "실시간 완성 미리보기: 상가 임차 (1080 x 1080 px)" if not is_sale_mode else "실시간 완성 미리보기: 상가 매매 (1080 x 1080 px)"
        st.image(comm_thumb_img, caption=caption_title, use_container_width=True)

    with col_ct_right:
        st.text_input("🏷️ 물건 번호 (매물번호)", key="comm_item_no")
        if not is_sale_mode:
            st.markdown("### 🛠️ 상가 임차 텍스트 수정")
            st.text_input("🏷️ 상단 캡슐 뱃지 문구", key="comm_lease_top_badge")
            st.text_input("📢 상단 강조 카피 (1행)", key="comm_lease_cp_top")
            st.text_input("🏬 메인 타이틀 (골드 3D)", key="comm_lease_main_title")
            st.text_input("✨ 하단 서브 카피 (2행)", key="comm_lease_cp_bot")
            
            st.markdown("#### 📍 중앙 골드 핀 & 말풍선")
            st.checkbox("3D 골드 위치 핀 및 말풍선 표시", key="comm_lease_show_pin")
            if st.session_state.comm_lease_show_pin:
                st.text_input("말풍선 문구", key="comm_lease_pin_bubble")

            st.markdown("#### 📋 다크 글래스모피즘 스펙 박스")
            st.text_input("스펙 1행 (전용면적 | 보증금/월세)", key="comm_lease_spec1")
            st.text_input("스펙 2행 (추천 업종 / 특징)", key="comm_lease_spec2")

            st.markdown("#### 🚩 매물 상태 (거래완료 표시)")
            render_deal_done_controller("comm")

            st.markdown("#### 🏢 하단 띠지 정보")
            st.checkbox("하단 띠지 표시", key="comm_lease_show_footer")
            if st.session_state.comm_lease_show_footer:
                c_of1, c_of2 = st.columns(2)
                with c_of1:
                    st.text_input("사무소 상호", key="comm_lease_office")
                with c_of2:
                    st.text_input("소장명 / 직책", key="comm_lease_broker")
        else:
            st.markdown("### 🛠️ 상가 매매 텍스트 수정")
            c_sb1, c_sb2 = st.columns(2)
            with c_sb1:
                st.text_input("🏷️ 상단 좌측 골드 뱃지", key="comm_sale_top_left")
            with c_sb2:
                st.text_input("🏷️ 상단 좌측 다크 뱃지", key="comm_sale_top_right")

            st.checkbox("상단 우측 골드 차트/빌딩 아이콘 표시", key="comm_sale_show_chart")

            st.text_input("💰 메인 하이라이트 (수익률 등 골드 대형)", key="comm_sale_main_hl")
            st.text_input("🏬 메인 서브 타이틀 (화이트 볼드)", key="comm_sale_main_sub")

            st.markdown("#### 📊 하단 스펙 인포 바")
            st.text_input("금액 및 투자 스펙 요약", key="comm_sale_price_spec")

            st.markdown("#### 🚩 매물 상태 (거래완료 표시)")
            render_deal_done_controller("comm")

            st.markdown("#### 🏢 하단 띠지 정보")
            st.checkbox("하단 띠지 표시", key="comm_sale_show_footer")
            if st.session_state.comm_sale_show_footer:
                c_of1, c_of2 = st.columns(2)
                with c_of1:
                    st.text_input("사무소 상호", key="comm_sale_office")
                with c_of2:
                    st.text_input("소장명 / 직책", key="comm_sale_broker")

        # 1. 상가 썸네일 다운로드 바이트
        img_byte_arr = io.BytesIO()
        comm_thumb_img.save(img_byte_arr, format="PNG", quality=98)
        img_bytes = img_byte_arr.getvalue()

        mode_tag = "상가임차" if not is_sale_mode else "상가매매"
        comm_clean_title = re.sub(r'[^\w\s-]', '', (st.session_state.comm_lease_main_title if not is_sale_mode else st.session_state.comm_sale_main_sub)).strip().replace(" ", "_")
        comm_filename = f"{mode_tag}_{comm_clean_title}.png"

        st.markdown("<hr style='margin: 15px 0 12px 0;'/>", unsafe_allow_html=True)
        st.markdown("### 📥 출력 및 저장 옵션")

        render_download_save_controller(
            file_bytes=img_bytes,
            default_filename=comm_filename,
            label_download=f"📥 1080x1080 {mode_tag} 썸네일 저장",
            key_prefix="comm_thumb_down"
        )

        st.info("💡 상가 썸네일과 포스터를 만드셨다면, 상단의 **'🏪 ④ 상가 중개대상물 표시'** 탭을 클릭하여 상가 전용 네이버 광고 체크리스트 및 블로그 서식을 확인하세요!")


# ====================================================
# [ 탭 3 ] 아파트 네이버 광고 & 대상중개물 표시 생성기
# (신소장님 지정 16개 순서 완벽 적용)
# ====================================================


# ====================================================
# [ 탭 1-4 ] 공장 / 창고 썸네일 생성기
# ====================================================
def render_tab_factory_thumb():
    col_t_left, col_t_right = st.columns([1.25, 0.75])
    
    with col_t_left:
        # 빠른 추천 프리셋
        col_fpr1, col_fpr2, col_fpr3 = st.columns([1, 1, 1])
        with col_fpr1:
            if st.button("⚡ 사상공단 1급 제조공장 (매매)", use_container_width=True, key="btn_preset_factory_1"):
                st.session_state.factory_item_no = "No. F-001"
                st.session_state.factory_main_title = "사상공단 1급 제조공장"
                st.session_state.factory_sub_title = "대형 츄레라 진입 · 호이스트 5톤"
                st.session_state.factory_feature_text = "대지 250평 · 동력 150kW 완비"
                st.session_state.factory_trade_type = "매매"
                st.session_state.factory_price_text = "18억 5천"
                st.session_state.factory_spec1 = "일반공업지역 / 공장용지"
                st.session_state.factory_spec2 = "대지 826㎡ / 연면적 550㎡"
                st.session_state.factory_spec3 = "호이스트 5T 1기 / 층고 9.5m"
                st.session_state.factory_spec4 = "동력 150kW / 진입로 8m"
                st.session_state.factory_spec5 = "즉시가동 협의가능"
                # 점검표도 동기화
                st.session_state.factory_ad_location = "부산광역시 사상구 삼락동 사상공단"
                st.session_state.factory_ad_trade_type = "매매"
                st.session_state.factory_ad_price_text = "18억 5,000만 원"
                st.session_state.factory_ad_area_land = "826.5"
                st.session_state.factory_ad_area_gross = "550.0"
                st.session_state.factory_ad_height = "처마 8.5m / 최고 9.5m"
                st.session_state.factory_ad_hoist = "5톤 1기 완비"
                st.session_state.factory_ad_power = "150kW 수전설비"
                st.session_state.factory_ad_road = "8m 포장도로 (츄레라 진입 원활)"
                st.session_state.factory_ad_parking = "옥외 마당 5대 이상"
                st.session_state.factory_ad_move_in_date = "즉시입주 협의가능"
                st.rerun()
        with col_fpr2:
            if st.button("⚡ 강서 대저동 신축 창고 (임대)", use_container_width=True, key="btn_preset_factory_2"):
                st.session_state.factory_item_no = "No. F-002"
                st.session_state.factory_main_title = "강서 대저동 신축 물류창고"
                st.session_state.factory_sub_title = "IC 5분 / 대형 트럭 진입 원활"
                st.session_state.factory_feature_text = "마당 넓음 · 캐노피 설치 완료"
                st.session_state.factory_trade_type = "월세"
                st.session_state.factory_price_text = "보3,000/월250"
                st.session_state.factory_spec1 = "제2종근생(제조업소/창고)"
                st.session_state.factory_spec2 = "대지 660㎡ / 연면적 396㎡ (120평)"
                st.session_state.factory_spec3 = "층고 8m / 바닥 에폭시 완비"
                st.session_state.factory_spec4 = "동력 30kW / 진입로 8m"
                st.session_state.factory_spec5 = "단독 마당 · 주차 8대"
                # 점검표도 동기화
                st.session_state.factory_ad_location = "부산광역시 강서구 대저동"
                st.session_state.factory_ad_trade_type = "월세"
                st.session_state.factory_ad_price_text = "보증금 3,000만 원 / 월 250만 원"
                st.session_state.factory_ad_area_land = "660.0"
                st.session_state.factory_ad_area_gross = "396.0"
                st.session_state.factory_ad_height = "처마 7.5m / 최고 8.5m"
                st.session_state.factory_ad_hoist = "무 (필요시 협의)"
                st.session_state.factory_ad_power = "30kW"
                st.session_state.factory_ad_road = "8m 아스팔트 포장도로"
                st.session_state.factory_ad_parking = "단독 마당 8대 가능"
                st.session_state.factory_ad_move_in_date = "즉시입주 가능"
                st.rerun()
        with col_fpr3:
            st.caption("👈 버튼을 누르면 추천 공장/창고 예시가 즉시 채워집니다.")

        # 요구사항 1번: 디자인모드 및 레이아웃 모드
        selected_design, layout_mode, photo_width_ratio = render_design_and_layout_controls("factory_thumb", default_design_name="💎 로열 사파이어 블루")

        # 사진 업로드
        uploaded_factory_bg = st.file_uploader(
            "📸 공장/창고 현장 실물/외관 사진 업로드 (스마트폰 촬영 사진 즉시 지원)",
            type=["jpg", "jpeg", "png", "webp"],
            key="factory_thumb_uploader"
        )
        if uploaded_factory_bg:
            st.session_state["saved_factory_uploaded_bg"] = uploaded_factory_bg
        else:
            uploaded_factory_bg = st.session_state.get("saved_factory_uploaded_bg")

        with st.expander("🔍 사진 위치 / 확대 미세 조정", expanded=False):
            f_z1, f_z2, f_z3 = st.columns(3)
            with f_z1:
                factory_bg_zoom = st.slider("사진 확대/축소", 0.6, 2.0, 1.0, 0.05, key="factory_bg_zoom")
            with f_z2:
                factory_bg_ox = st.slider("사진 좌우 이동 (px)", -450, 450, 0, 10, key="factory_bg_ox")
            with f_z3:
                factory_bg_oy = st.slider("사진 상하 이동 (px)", -450, 450, 0, 10, key="factory_bg_oy")

        # 썸네일 렌더링
        factory_specs = [
            st.session_state.factory_spec1,
            st.session_state.factory_spec2,
            st.session_state.factory_spec3,
            st.session_state.factory_spec4,
            st.session_state.factory_spec5
        ]

        with st.spinner("고화질 공장 썸네일 렌더링 중..."):
            factory_thumb_img = render_thumbnail(
                bg_image=uploaded_factory_bg,
                item_no=st.session_state.factory_item_no,
                main_title=st.session_state.factory_main_title,
                sub_title=st.session_state.factory_sub_title,
                feature_text=st.session_state.factory_feature_text,
                trade_type=st.session_state.factory_trade_type,
                price_text=st.session_state.factory_price_text,
                spec_lines=factory_specs,
                layout_mode=layout_mode,
                photo_width_ratio=photo_width_ratio,
                bg_offset_x=factory_bg_ox,
                bg_offset_y=factory_bg_oy,
                bg_zoom=factory_bg_zoom,
                show_footer=st.session_state.factory_show_footer,
                footer_text=st.session_state.factory_footer_text,
                primary_color=selected_design["primary_color"],
                accent_color=selected_design["accent_color"],
                card_bg=selected_design["card_bg"],
                overlay_image=selected_design.get("overlay_image_path"),
                deal_done=st.session_state.get("factory_deal_done", False),
                deal_color=st.session_state.get("factory_deal_color", "#FF0101")
            )

        st.image(factory_thumb_img, caption="공장 블로그 썸네일 실시간 미리보기 (1080 x 1080 px)", use_container_width=True)

    with col_t_right:
        st.markdown("### 🛠️ 공장 썸네일 텍스트 수정")
        st.text_input("🏷️ 물건 번호", key="factory_item_no")
        st.text_input("🏭 메인 타이틀 (공장/창고명)", key="factory_main_title")
        st.text_input("📍 서브 타이틀 (동/공단명)", key="factory_sub_title")
        st.text_input("✨ 매물 핵심 특징", key="factory_feature_text", placeholder="직접 입력하세요 (예: 호이스트 5톤 + 전력 150kW 완비)")

        c_ft1, c_ft2 = st.columns([1, 1.3])
        with c_ft1:
            f_trade_opts = ["매매", "월세", "임대", "급매"]
            if st.session_state.factory_trade_type not in f_trade_opts:
                f_trade_opts.append(st.session_state.factory_trade_type)
            st.selectbox("거래 형태", f_trade_opts, key="factory_trade_type")
        with c_ft2:
            st.text_input("금액 (예: 18억 5천)", key="factory_price_text")

        st.markdown("#### 📋 5대 스펙 텍스트")
        st.text_input("1행: 용도지역 / 지목", key="factory_spec1")
        st.text_input("2행: 대지 / 연면적", key="factory_spec2")
        st.text_input("3행: 호이스트 / 층고", key="factory_spec3")
        st.text_input("4행: 동력 / 진입도로", key="factory_spec4")
        st.text_input("5행: 입주 및 주차", key="factory_spec5")

        st.markdown("#### 🚩 매물 상태 (거래완료 표시)")
        render_deal_done_controller("factory")

        st.markdown("#### 🏢 하단 띠지 (중개사무소 정보)")
        st.checkbox("하단 띠지 표시 (체크 해제 시 전체 사진 영역 확장)", key="factory_show_footer")
        if st.session_state.factory_show_footer:
            st.text_input("띠지 문구 (소공/직원 커스텀 가능)", key="factory_footer_text", placeholder="미입력 시: 참좋은공인중개사사무소 (대표 신제환) ☎ 010-9667-4201")
            c_ff1, c_ff2 = st.columns(2)
            with c_ff1:
                st.text_input("사무실 연락처 (창문 전단지용)", key="factory_office_tel", value=st.session_state.get("factory_office_tel", "010-9667-4201"))
            with c_ff2:
                st.text_input("📱 담당자 연락처 (창문 전단지용)", key="factory_assistant_phone", value=st.session_state.get("factory_assistant_phone", ""), placeholder="예: 010-9667-4201")

        # 다운로드 바이트
        f_thumb_io = io.BytesIO()
        factory_thumb_img.save(f_thumb_io, format="PNG", quality=98)
        f_thumb_bytes = f_thumb_io.getvalue()

        clean_f_title = re.sub(r'[^\w\s-]', '', (st.session_state.factory_main_title or "공장")).strip().replace(" ", "_")
        clean_f_price = re.sub(r'[^\w\s-]', '', (st.session_state.factory_price_text or "")).strip().replace(" ", "")
        f_down_name = f"공장썸네일_{clean_f_title}_{st.session_state.factory_trade_type}_{clean_f_price}.png"

        st.markdown("<hr style='margin: 15px 0 12px 0;'/>", unsafe_allow_html=True)
        st.markdown("### 📥 출력 및 저장 옵션")

        render_download_save_controller(
            file_bytes=f_thumb_bytes,
            default_filename=f_down_name,
            label_download="📥 1080x1080 공장 썸네일 저장",
            key_prefix="factory_thumb_down"
        )


# ====================================================
# [ 탭 1-2 ] 창문부착용 A4 포스터 전용 렌더러 (아파트, 주택, 상가, 공장)
# ====================================================
def render_tab_apt_poster():
    st.markdown("""
    <div style="background-color: #F8F9FB; border-left: 4px solid #F48A26; padding: 12px 18px; border-radius: 6px; margin-bottom: 20px;">
        <span style="font-size: 15px; font-weight: 700; color: #1E2022;">
            🖨️ 아파트 중개사무소 창문 부착용 A4 브리핑 포스터 (초고화질 300 DPI)
        </span><br/>
        <span style="font-size: 13px; color: #6C757D;">
            중개사무소 유리창에 부착 시 지나가는 고객의 시선을 사로잡는 인쇄용 브리핑 포스터입니다. 원클릭 즉시 인쇄(Ctrl+P) 또는 300DPI 초고화질 저장이 지원됩니다.
        </span>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_r = st.columns([1.2, 1.1])
    
    uploaded_bg = st.session_state.get("saved_apt_uploaded_bg")
    spec_lines = [
        st.session_state.spec_line1,
        st.session_state.spec_line2,
        st.session_state.spec_line3,
        st.session_state.spec_line4,
        st.session_state.spec_line5
    ]
    all_designs = load_all_designs()
    selected_design = all_designs[0] if all_designs else {
        "primary_color": "#F48A26",
        "accent_color": "#EB5E28",
        "card_bg": "#FFFFFF"
    }
    cur_dname = st.session_state.get("apt_thumb_design_selector")
    if cur_dname:
        selected_design = get_design_by_name(cur_dname)

    with col_l:
        with st.spinner("창문 부착용 300DPI 초고화질 A4 포스터 렌더링 중..."):
            a4_poster_img = render_a4_window_poster(
                bg_image=uploaded_bg,
                item_no=st.session_state.item_no,
                main_title=st.session_state.main_title,
                sub_title=st.session_state.sub_title,
                feature_text=st.session_state.feature_text,
                trade_type=st.session_state.thumb_trade_type,
                price_text=st.session_state.thumb_price_text,
                spec_lines=spec_lines,
                office_name=st.session_state.get("ad_office_name", "참좋은공인중개사사무소"),
                office_owner=st.session_state.get("ad_office_owner", "신제환"),
                office_phone=st.session_state.get("ad_office_phone", "010-9667-4201"),
                office_reg_no=st.session_state.get("ad_office_reg_no", "제 26530-2026-00009 호"),
                office_address=st.session_state.get("ad_office_address", "부산광역시 사상구 강선로 9, 1층"),
                is_commercial=False,
                office_tel=st.session_state.get("office_tel_input", "010-9667-4201"),
                assistant_phone=st.session_state.get("assistant_phone_input", ""),
                primary_color_override=selected_design.get("primary_color", "#F48A26"),
                accent_color_override=selected_design.get("accent_color", "#EB5E28")
            )
        st.image(a4_poster_img, caption="아파트 창문 부착용 A4 포스터 (초고화질 300 DPI)", use_container_width=True)
        
        st.markdown("""
        <div style="font-size:13px; color:#2D3748; background:#F8FAFC; border:1px solid #E2E8F0; padding:12px 14px; border-radius:8px; margin-top:12px; line-height:1.6;">
            💡 <b>창문 부착 인쇄 팁:</b><br/>
            1. 우측 <b>[원클릭 즉시 인쇄]</b>를 누르시면 프린터 인쇄창(Ctrl+P)이 즉시 호출됩니다.<br/>
            2. 인쇄 대화상자에서 용지 방향을 <b>'세로'</b>로 하시고 <b>'용지에 맞춤'</b>을 체크하시면 A4 용지에 여백 없이 선명히 인쇄됩니다!<br/>
            3. 인쇄 후 유리창 안쪽에 부착하시면 지나가는 고객의 시선을 100% 사로잡습니다.
        </div>
        """, unsafe_allow_html=True)

    with col_r:
        clean_title = re.sub(r'[\\/*?:"<>|]', "", st.session_state.main_title).strip()
        clean_price = re.sub(r'[\\/*?:"<>|]', "", st.session_state.thumb_price_text).strip()
        a4_filename = f"창문부착용_아파트포스터_{clean_title}_{clean_price}.png"
        
        a4_io = io.BytesIO()
        a4_poster_img.save(a4_io, format="PNG", quality=98)
        a4_bytes = a4_io.getvalue()

        st.markdown("### 🖨️ 포스터 출력 및 파일 저장")
        render_download_save_controller(
            file_bytes=a4_bytes,
            default_filename=a4_filename,
            label_download="📥 300DPI 초고화질 A4 포스터 파일 저장",
            key_prefix="poster_page_apt",
            is_poster=True,
            print_bytes=a4_bytes
        )

        with st.expander("🛠️ 포스터 주요 문구 및 중개사무소 정보 간편 수정", expanded=True):
            st.text_input("🏷️ 물건 번호", key="poster_apt_item_no", value=st.session_state.item_no)
            st.text_input("🏢 메인 타이틀 (아파트명)", key="poster_apt_main_title", value=st.session_state.main_title)
            st.text_input("📍 서브 타이틀 (동/단지명)", key="poster_apt_sub_title", value=st.session_state.sub_title)
            st.text_input("✨ 매물 핵심 특징", key="poster_apt_feature", value=st.session_state.feature_text)
            
            cp1, cp2 = st.columns(2)
            with cp1:
                st.selectbox("거래 형태", ["매매", "전세", "월세", "분양", "급매"], key="poster_apt_trade_type", index=0 if st.session_state.thumb_trade_type not in ["매매", "전세", "월세", "분양", "급매"] else ["매매", "전세", "월세", "분양", "급매"].index(st.session_state.thumb_trade_type))
            with cp2:
                st.text_input("금액", key="poster_apt_price", value=st.session_state.thumb_price_text)

            if st.button("🔄 포스터 수정 내용 썸네일과 동기화 적용", key="btn_sync_poster_apt", use_container_width=True):
                st.session_state.item_no = st.session_state.poster_apt_item_no
                st.session_state.main_title = st.session_state.poster_apt_main_title
                st.session_state.sub_title = st.session_state.poster_apt_sub_title
                st.session_state.feature_text = st.session_state.poster_apt_feature
                st.session_state.thumb_trade_type = st.session_state.poster_apt_trade_type
                st.session_state.thumb_price_text = st.session_state.poster_apt_price
                st.success("포스터 문구가 동기화되었습니다!")
                st.rerun()


def render_tab_house_poster():
    st.markdown("""
    <div style="background-color: #F8F9FB; border-left: 4px solid #38A169; padding: 12px 18px; border-radius: 6px; margin-bottom: 20px;">
        <span style="font-size: 15px; font-weight: 700; color: #1E2022;">
            🖨️ 주택 / 빌라 / 원룸 중개사무소 창문 부착용 A4 포스터 (초고화질 300 DPI)
        </span><br/>
        <span style="font-size: 13px; color: #6C757D;">
            중개사무소 유리창에 부착 시 지나가는 고객의 시선을 사로잡는 인쇄용 브리핑 포스터입니다. 원클릭 즉시 인쇄(Ctrl+P) 또는 300DPI 초고화질 저장이 지원됩니다.
        </span>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_r = st.columns([1.2, 1.1])
    
    uploaded_house_bg = st.session_state.get("saved_house_uploaded_bg")
    house_specs = [
        st.session_state.house_spec1,
        st.session_state.house_spec2,
        st.session_state.house_spec3,
        st.session_state.house_spec4,
        st.session_state.house_spec5
    ]
    all_designs = load_all_designs()
    selected_design = all_designs[0] if all_designs else {
        "primary_color": "#38A169",
        "accent_color": "#276749",
        "card_bg": "#FFFFFF"
    }
    cur_dname = st.session_state.get("house_thumb_design_selector")
    if cur_dname:
        selected_design = get_design_by_name(cur_dname)

    with col_l:
        with st.spinner("창문 부착용 300DPI 초고화질 A4 포스터 렌더링 중..."):
            house_a4_img = render_a4_window_poster(
                bg_image=uploaded_house_bg,
                item_no=st.session_state.house_item_no,
                main_title=st.session_state.house_main_title,
                sub_title=st.session_state.house_sub_title,
                feature_text=st.session_state.house_feature_text,
                trade_type=st.session_state.house_trade_type,
                price_text=st.session_state.house_price_text,
                spec_lines=house_specs,
                office_name=st.session_state.get("ad_office_name", "참좋은공인중개사사무소"),
                office_owner=st.session_state.get("ad_office_owner", "신제환"),
                office_phone=st.session_state.get("ad_office_phone", "010-9667-4201"),
                office_reg_no=st.session_state.get("ad_office_reg_no", "제 26530-2026-00009 호"),
                office_address=st.session_state.get("ad_office_address", "부산광역시 사상구 강선로 9, 1층"),
                is_commercial=False,
                office_tel=st.session_state.get("house_office_tel", "010-9667-4201"),
                assistant_phone=st.session_state.get("house_assistant_phone", ""),
                primary_color_override=selected_design.get("primary_color", "#38A169"),
                accent_color_override=selected_design.get("accent_color", "#276749")
            )
        st.image(house_a4_img, caption="주택 창문 부착용 A4 포스터 (초고화질 300 DPI)", use_container_width=True)

        st.markdown("""
        <div style="font-size:13px; color:#2D3748; background:#F8FAFC; border:1px solid #E2E8F0; padding:12px 14px; border-radius:8px; margin-top:12px; line-height:1.6;">
            💡 <b>창문 부착 인쇄 팁:</b><br/>
            1. 우측 <b>[원클릭 즉시 인쇄]</b>를 누르시면 프린터 인쇄창(Ctrl+P)이 즉시 호출됩니다.<br/>
            2. 인쇄 대화상자에서 용지 방향을 <b>'세로'</b>로 하시고 <b>'용지에 맞춤'</b>을 체크하시면 A4 용지에 여백 없이 선명히 인쇄됩니다!<br/>
            3. 인쇄 후 유리창 안쪽에 부착하시면 지나가는 고객의 시선을 100% 사로잡습니다.
        </div>
        """, unsafe_allow_html=True)

    with col_r:
        clean_title = re.sub(r'[\\/*?:"<>|]', "", st.session_state.house_main_title).strip()
        clean_price = re.sub(r'[\\/*?:"<>|]', "", st.session_state.house_price_text).strip()
        house_a4_name = f"창문부착용_주택포스터_{clean_title}_{clean_price}.png"

        h_a4_io = io.BytesIO()
        house_a4_img.save(h_a4_io, format="PNG", quality=98)
        house_a4_bytes = h_a4_io.getvalue()

        st.markdown("### 🖨️ 포스터 출력 및 파일 저장")
        render_download_save_controller(
            file_bytes=house_a4_bytes,
            default_filename=house_a4_name,
            label_download="📥 300DPI 초고화질 A4 포스터 파일 저장",
            key_prefix="poster_page_house",
            is_poster=True,
            print_bytes=house_a4_bytes
        )

        with st.expander("🛠️ 포스터 주요 문구 및 중개사무소 정보 간편 수정", expanded=True):
            st.text_input("🏷️ 물건 번호", key="poster_house_item_no", value=st.session_state.house_item_no)
            st.text_input("🏡 메인 타이틀 (주택명)", key="poster_house_main_title", value=st.session_state.house_main_title)
            st.text_input("📍 서브 타이틀 (동/층/구조)", key="poster_house_sub_title", value=st.session_state.house_sub_title)
            st.text_input("✨ 매물 핵심 특징", key="poster_house_feature", value=st.session_state.house_feature_text)
            
            cp1, cp2 = st.columns(2)
            with cp1:
                st.selectbox("거래 형태", ["매매", "전세", "월세", "분양", "단기"], key="poster_house_trade_type", index=0 if st.session_state.house_trade_type not in ["매매", "전세", "월세", "분양", "단기"] else ["매매", "전세", "월세", "분양", "단기"].index(st.session_state.house_trade_type))
            with cp2:
                st.text_input("금액", key="poster_house_price", value=st.session_state.house_price_text)

            if st.button("🔄 포스터 수정 내용 썸네일과 동기화 적용", key="btn_sync_poster_house", use_container_width=True):
                st.session_state.house_item_no = st.session_state.poster_house_item_no
                st.session_state.house_main_title = st.session_state.poster_house_main_title
                st.session_state.house_sub_title = st.session_state.poster_house_sub_title
                st.session_state.house_feature_text = st.session_state.poster_house_feature
                st.session_state.house_trade_type = st.session_state.poster_house_trade_type
                st.session_state.house_price_text = st.session_state.poster_house_price
                st.success("주택 포스터 문구가 동기화되었습니다!")
                st.rerun()


def render_tab_comm_poster():
    st.markdown("""
    <div style="background-color: #181C24; border-left: 4px solid #DAA844; padding: 12px 18px; border-radius: 6px; margin-bottom: 20px; color: #FFFFFF;">
        <span style="font-size: 15px; font-weight: 700; color: #DAA844;">
            🖨️ 상가 / 점포 / 빌딩 창문 부착용 A4 포스터 (초고화질 300 DPI)
        </span><br/>
        <span style="font-size: 13px; color: #CBD5E0;">
            임차 상가 및 매매 상가 전용 브리핑 포스터입니다. 원클릭 즉시 인쇄(Ctrl+P) 또는 300DPI 초고화질 저장이 지원됩니다.
        </span>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_r = st.columns([1.2, 1.1])
    
    uploaded_comm_bg = st.session_state.get("saved_comm_uploaded_bg")
    is_comm_sale = "매매" in st.session_state.get("comm_thumb_mode", "임대차")
    
    if not is_comm_sale:
        comm_a4_title = st.session_state.get("comm_lease_main_title", "코너 상가 임차")
        comm_a4_sub = st.session_state.get("comm_lease_cp_top", "유동인구 1등! 대로변 1층")
        comm_a4_feature = st.session_state.get("comm_lease_top_badge", "사상역 초역세권 · 무권리 추천매물")
        comm_a4_trade = "임대"
        comm_spec1 = st.session_state.get("comm_lease_spec1", "전용 25평 | 보증금 3,000만 / 월 180만")
        comm_a4_price = comm_spec1.split("|")[-1].strip() if "|" in comm_spec1 else comm_spec1
        comm_a4_specs = [
            comm_spec1,
            st.session_state.get("comm_lease_spec2", "추천 : 카페 · 음식점 · 판매점"),
            st.session_state.get("comm_lease_pin_bubble", "목 좋은 자리!"),
            "즉시입점 협의가능",
            "도로변 가시성 우수"
        ]
    else:
        comm_a4_title = st.session_state.get("comm_sale_main_sub", "안정적인 알짜 상가 매매")
        comm_a4_sub = st.session_state.get("comm_sale_top_left", "사상 핵심상권 매매")
        comm_a4_feature = st.session_state.get("comm_sale_top_right", "우량 임차인 성업중")
        comm_a4_trade = "매매"
        comm_a4_price = st.session_state.get("comm_sale_main_hl", "확정 수익률 6.8%")
        comm_a4_specs = [
            st.session_state.get("comm_sale_price_spec", "매매가 15억 | 보증금 8천 / 월수익 650만"),
            comm_a4_price,
            "자주식 주차 및 승강기 완비",
            "안정적인 임대수익 보장",
            "사상 역세권 핵심 상권"
        ]

    all_designs = load_all_designs()
    selected_comm_design = all_designs[0] if all_designs else {
        "primary_color": "#DAA844",
        "accent_color": "#B8860B",
        "card_bg": "#181C24"
    }
    cur_dname = st.session_state.get("comm_thumb_design_selector")
    if cur_dname:
        selected_comm_design = get_design_by_name(cur_dname)

    with col_l:
        with st.spinner("상가 창문 부착용 300DPI 초고화질 A4 포스터 렌더링 중..."):
            comm_a4_poster_img = render_a4_window_poster(
                bg_image=uploaded_comm_bg,
                item_no=st.session_state.get("comm_item_no", "No. COMM-01"),
                main_title=comm_a4_title,
                sub_title=comm_a4_sub,
                feature_text=comm_a4_feature,
                trade_type=comm_a4_trade,
                price_text=comm_a4_price,
                spec_lines=comm_a4_specs,
                office_name=st.session_state.get("comm_ad_office_name", "참좋은공인중개사사무소"),
                office_owner=st.session_state.get("comm_ad_office_owner", "신제환"),
                office_phone=st.session_state.get("comm_ad_office_phone", "010-9667-4201"),
                office_reg_no=st.session_state.get("comm_ad_office_reg_no", "제 26530-2026-00009 호"),
                office_address=st.session_state.get("comm_ad_office_address", "부산광역시 사상구 강선로 9, 1층"),
                is_commercial=True,
                office_tel=st.session_state.get("comm_office_tel_input", "010-9667-4201"),
                assistant_phone=st.session_state.get("comm_assistant_phone_input", ""),
                primary_color_override=selected_comm_design.get("primary_color", "#DAA844"),
                accent_color_override=selected_comm_design.get("accent_color", "#B8860B")
            )
        st.image(comm_a4_poster_img, caption="상가 유리창 부착용 A4 브리핑 포스터 (초고화질 300 DPI)", use_container_width=True)

        st.markdown("""
        <div style="font-size:13px; color:#2D3748; background:#F8FAFC; border:1px solid #E2E8F0; padding:12px 14px; border-radius:8px; margin-top:12px; line-height:1.6;">
            💡 <b>창문 부착 인쇄 팁:</b><br/>
            1. 우측 <b>[원클릭 즉시 인쇄]</b>를 누르시면 프린터 인쇄창(Ctrl+P)이 즉시 호출됩니다.<br/>
            2. 인쇄 대화상자에서 용지 방향을 <b>'세로'</b>로 하시고 <b>'용지에 맞춤'</b>을 체크하시면 A4 용지에 여백 없이 선명히 인쇄됩니다!<br/>
            3. 인쇄 후 유리창 안쪽에 부착하시면 지나가는 고객의 시선을 100% 사로잡습니다.
        </div>
        """, unsafe_allow_html=True)

    with col_r:
        clean_comm_title = re.sub(r'[\\/*?:"<>|]', "", comm_a4_title).strip()
        clean_comm_price = re.sub(r'[\\/*?:"<>|]', "", comm_a4_price).strip()
        comm_a4_name = f"창문부착용_상가포스터_{clean_comm_title}_{clean_comm_price}.png"

        c_a4_io = io.BytesIO()
        comm_a4_poster_img.save(c_a4_io, format="PNG", quality=98)
        comm_a4_bytes = c_a4_io.getvalue()

        st.markdown("### 🖨️ 포스터 출력 및 파일 저장")
        render_download_save_controller(
            file_bytes=comm_a4_bytes,
            default_filename=comm_a4_name,
            label_download="📥 300DPI 초고화질 A4 포스터 파일 저장",
            key_prefix="poster_page_comm",
            is_poster=True,
            print_bytes=comm_a4_bytes
        )

        with st.expander("🛠️ 상가 포스터 주요 문구 간편 수정", expanded=True):
            if not is_comm_sale:
                st.text_input("🏢 상가 메인 타이틀", key="poster_comm_l_title", value=st.session_state.get("comm_lease_main_title", "코너 상가 임차"))
                st.text_input("📍 상단 강조 카피", key="poster_comm_l_sub", value=st.session_state.get("comm_lease_cp_top", "유동인구 1등! 대로변 1층"))
                st.text_input("✨ 캡슐 뱃지 문구", key="poster_comm_l_feat", value=st.session_state.get("comm_lease_top_badge", "사상역 초역세권 · 무권리 추천매물"))
                st.text_input("💰 1행 스펙 (보증금/월세)", key="poster_comm_l_price", value=st.session_state.get("comm_lease_spec1", "전용 25평 | 보증금 3,000만 / 월 180만"))
                if st.button("🔄 임대 상가 포스터 수정 동기화", key="btn_sync_poster_comm_l", use_container_width=True):
                    st.session_state.comm_lease_main_title = st.session_state.poster_comm_l_title
                    st.session_state.comm_lease_cp_top = st.session_state.poster_comm_l_sub
                    st.session_state.comm_lease_top_badge = st.session_state.poster_comm_l_feat
                    st.session_state.comm_lease_spec1 = st.session_state.poster_comm_l_price
                    st.success("상가 문구가 동기화되었습니다!")
                    st.rerun()
            else:
                st.text_input("🏢 매매 상가 메인 타이틀", key="poster_comm_s_title", value=st.session_state.get("comm_sale_main_sub", "안정적인 알짜 상가 매매"))
                st.text_input("📍 상단 좌측 뱃지", key="poster_comm_s_sub", value=st.session_state.get("comm_sale_top_left", "사상 핵심상권 매매"))
                st.text_input("💰 메인 강조 문구 (수익률)", key="poster_comm_s_price", value=st.session_state.get("comm_sale_main_hl", "확정 수익률 6.8%"))
                if st.button("🔄 매매 상가 포스터 수정 동기화", key="btn_sync_poster_comm_s", use_container_width=True):
                    st.session_state.comm_sale_main_sub = st.session_state.poster_comm_s_title
                    st.session_state.comm_sale_top_left = st.session_state.poster_comm_s_sub
                    st.session_state.comm_sale_main_hl = st.session_state.poster_comm_s_price
                    st.success("상가 문구가 동기화되었습니다!")
                    st.rerun()


def render_tab_factory_poster():
    st.markdown("""
    <div style="background-color: #F8F9FB; border-left: 4px solid #3182CE; padding: 12px 18px; border-radius: 6px; margin-bottom: 20px;">
        <span style="font-size: 15px; font-weight: 700; color: #1E2022;">
            🖨️ 공장 / 창고 / 나대지 창문 부착용 A4 포스터 (초고화질 300 DPI)
        </span><br/>
        <span style="font-size: 13px; color: #6C757D;">
            중개사무소 유리창에 부착 시 지나가는 고객의 시선을 사로잡는 인쇄용 브리핑 포스터입니다. 원클릭 즉시 인쇄(Ctrl+P) 또는 300DPI 초고화질 저장이 지원됩니다.
        </span>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_r = st.columns([1.2, 1.1])
    
    uploaded_factory_bg = st.session_state.get("saved_factory_uploaded_bg")
    factory_specs = [
        st.session_state.factory_spec1,
        st.session_state.factory_spec2,
        st.session_state.factory_spec3,
        st.session_state.factory_spec4,
        st.session_state.factory_spec5
    ]
    all_designs = load_all_designs()
    selected_design = all_designs[0] if all_designs else {
        "primary_color": "#3182CE",
        "accent_color": "#2B6CB0",
        "card_bg": "#FFFFFF"
    }
    cur_dname = st.session_state.get("factory_thumb_design_selector")
    if cur_dname:
        selected_design = get_design_by_name(cur_dname)

    with col_l:
        with st.spinner("창문 부착용 300DPI 초고화질 A4 포스터 렌더링 중..."):
            factory_a4_img = render_a4_window_poster(
                bg_image=uploaded_factory_bg,
                item_no=st.session_state.factory_item_no,
                main_title=st.session_state.factory_main_title,
                sub_title=st.session_state.factory_sub_title,
                feature_text=st.session_state.factory_feature_text,
                trade_type=st.session_state.factory_trade_type,
                price_text=st.session_state.factory_price_text,
                spec_lines=factory_specs,
                office_name=st.session_state.get("ad_office_name", "참좋은공인중개사사무소"),
                office_owner=st.session_state.get("ad_office_owner", "신제환"),
                office_phone=st.session_state.get("ad_office_phone", "010-9667-4201"),
                office_reg_no=st.session_state.get("ad_office_reg_no", "제 26530-2026-00009 호"),
                office_address=st.session_state.get("ad_office_address", "부산광역시 사상구 강선로 9, 1층"),
                is_commercial=False,
                office_tel=st.session_state.get("factory_office_tel", "010-9667-4201"),
                assistant_phone=st.session_state.get("factory_assistant_phone", ""),
                primary_color_override=selected_design.get("primary_color", "#3182CE"),
                accent_color_override=selected_design.get("accent_color", "#2B6CB0")
            )
        st.image(factory_a4_img, caption="공장 창문 부착용 A4 포스터 (초고화질 300 DPI)", use_container_width=True)

        st.markdown("""
        <div style="font-size:13px; color:#2D3748; background:#F8FAFC; border:1px solid #E2E8F0; padding:12px 14px; border-radius:8px; margin-top:12px; line-height:1.6;">
            💡 <b>창문 부착 인쇄 팁:</b><br/>
            1. 우측 <b>[원클릭 즉시 인쇄]</b>를 누르시면 프린터 인쇄창(Ctrl+P)이 즉시 호출됩니다.<br/>
            2. 인쇄 대화상자에서 용지 방향을 <b>'세로'</b>로 하시고 <b>'용지에 맞춤'</b>을 체크하시면 A4 용지에 여백 없이 선명히 인쇄됩니다!<br/>
            3. 인쇄 후 유리창 안쪽에 부착하시면 지나가는 고객의 시선을 100% 사로잡습니다.
        </div>
        """, unsafe_allow_html=True)

    with col_r:
        clean_f_title = re.sub(r'[\\/*?:"<>|]', "", st.session_state.factory_main_title).strip()
        clean_f_price = re.sub(r'[\\/*?:"<>|]', "", st.session_state.factory_price_text).strip()
        factory_a4_name = f"창문부착용_공장포스터_{clean_f_title}_{clean_f_price}.png"

        f_a4_io = io.BytesIO()
        factory_a4_img.save(f_a4_io, format="PNG", quality=98)
        factory_a4_bytes = f_a4_io.getvalue()

        st.markdown("### 🖨️ 포스터 출력 및 파일 저장")
        render_download_save_controller(
            file_bytes=factory_a4_bytes,
            default_filename=factory_a4_name,
            label_download="📥 300DPI 초고화질 A4 포스터 파일 저장",
            key_prefix="poster_page_factory",
            is_poster=True,
            print_bytes=factory_a4_bytes
        )

        with st.expander("🛠️ 공장 포스터 주요 문구 간편 수정", expanded=True):
            st.text_input("🏷️ 물건 번호", key="poster_factory_item_no", value=st.session_state.factory_item_no)
            st.text_input("🏭 메인 타이틀 (공장명)", key="poster_factory_main_title", value=st.session_state.factory_main_title)
            st.text_input("📍 서브 타이틀 (위치/도로)", key="poster_factory_sub_title", value=st.session_state.factory_sub_title)
            st.text_input("✨ 매물 핵심 특징", key="poster_factory_feature", value=st.session_state.factory_feature_text)
            
            cp1, cp2 = st.columns(2)
            with cp1:
                st.selectbox("거래 형태", ["매매", "월세", "임대", "급매"], key="poster_factory_trade_type", index=0 if st.session_state.factory_trade_type not in ["매매", "월세", "임대", "급매"] else ["매매", "월세", "임대", "급매"].index(st.session_state.factory_trade_type))
            with cp2:
                st.text_input("금액", key="poster_factory_price", value=st.session_state.factory_price_text)

            if st.button("🔄 공장 포스터 수정 내용 동기화 적용", key="btn_sync_poster_factory", use_container_width=True):
                st.session_state.factory_item_no = st.session_state.poster_factory_item_no
                st.session_state.factory_main_title = st.session_state.poster_factory_main_title
                st.session_state.factory_sub_title = st.session_state.poster_factory_sub_title
                st.session_state.factory_feature_text = st.session_state.poster_factory_feature
                st.session_state.factory_trade_type = st.session_state.poster_factory_trade_type
                st.session_state.factory_price_text = st.session_state.poster_factory_price
                st.success("공장 포스터 문구가 동기화되었습니다!")
                st.rerun()


# ====================================================
# [ 탭 2-1 ] 아파트 네이버 광고 & 중개대상물 표시 생성기
# ====================================================
def render_tab_apt_ad():
    st.markdown("""
    <div style="background-color: #F8F9FB; border-left: 4px solid #F48A26; padding: 12px 18px; border-radius: 6px; margin-bottom: 20px;">
        <span style="font-size: 15px; font-weight: 700; color: #1E2022;">
            📝 아파트 매물 인터넷 표시·광고 점검표 (네이버 부동산 광고 입력 순서 16개 항목)
        </span><br/>
        <span style="font-size: 13px; color: #6C757D;">
            네이버 부동산 매물 등록창의 항목 순서와 1:1로 일치하여, 화면을 보면서 빠르고 정확하게 광고를 등록할 수 있습니다.
        </span>
    </div>
    """, unsafe_allow_html=True)

    # 최근 자동완성 성공 알림 배너
    if st.session_state.get("last_applied_msg"):
        st.success(st.session_state["last_applied_msg"])

    # ----------------------------------------------------
    # 🌐 [요구사항 2] 네이버 부동산 매물 연동 (복사 텍스트 & 매물번호)
    # ----------------------------------------------------
    with st.expander("🌐 [원클릭 1초 자동완성] 네이버 부동산 매물 연동 (클립보드 복사 & 매물번호)", expanded=True):
        st.markdown("""
        <div style="font-size:14px; color:#1A365D; background:#EBF8FF; border:1px solid #BEE3F8; padding:10px 14px; border-radius:8px; margin-bottom:12px;">
            🔗 네이버 부동산의 <b>화면 복사 텍스트</b>를 붙여넣거나 <b>매물 번호</b>를 입력하시면, 
            실시간으로 <b>매물명, 거래가격, 층수, 전용/공급면적, 방수, 방향, 주차대수, 준공일 등 16대 점검항목</b>과 <b>블로그 썸네일</b>을 1초 만에 자동 완성합니다!
        </div>
        """, unsafe_allow_html=True)

        tab_crawl_num, tab_crawl_txt = st.tabs([
            "🔍 네이버 매물번호 / URL 크롤링",
            "📋 네이버 화면 복사 텍스트 붙여넣기 (가장 확실 & 1초 완성! 추천)"
        ])

        with tab_crawl_num:
            c_cr_in, c_cr_btn = st.columns([2.5, 1])
            with c_cr_in:
                input_article_val = st.text_input(
                    "네이버 부동산 매물 번호 또는 URL",
                    placeholder="예: 2428591234 또는 https://fin.land.naver.com/articles/2428591234",
                    help="네이버 부동산 매물 번호(10자리 내외) 또는 브라우저 주소창 링크를 붙여넣으세요.",
                    key="input_naver_article_no"
                )
            with c_cr_btn:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                btn_do_crawl = st.button("🚀 1초 크롤링 시도", type="primary", use_container_width=True, key="btn_crawl_naver")

            if btn_do_crawl:
                if input_article_val.strip():
                    with st.spinner("네이버 부동산 매물 정보 실시간 조회 중..."):
                        is_ok, msg, c_data = crawl_naver_article(input_article_val.strip())
                        if is_ok:
                            queue_state_update("apply_apt", data=c_data, clean_previous=True, success_msg=f"🎉 {msg} 16대 점검항목과 썸네일에 즉시 자동 반영되었습니다.", target_tab="📝 ③ 아파트 중개대상물 표시")
                        else:
                            st.error(f"⚠️ {msg}")
                else:
                    st.warning("매물 번호 또는 매물 링크 URL을 입력해주세요.")

        with tab_crawl_txt:
            st.markdown("""
            <div style="font-size:13px; color:#2B6CB0; background:#EBF8FF; border:1px solid #BEE3F8; padding:8px 12px; border-radius:6px; margin-bottom:8px;">
                💡 <b>1초 자동완성 방법:</b> 네이버 부동산 매물 화면에서 마우스로 매물 정보 영역(매물명, 가격, 면적, 층수 등)을 드래그 복사(Ctrl+C)하여 아래에 붙여넣으세요! 네이버 봇 차단 없이 100% 즉시 반영됩니다.
            </div>
            """, unsafe_allow_html=True)
            clip_article_text = st.text_area(
                "네이버 부동산 매물 상세 복사 텍스트",
                height=120,
                placeholder="예:\n사상 중흥S-클래스 105동 매매 6억 2,000만원\n아파트 공급 111.42㎡ / 전용 79.85㎡, 25/36층, 남동향\n관리비 18만원, 방수/욕실수 3/2개...",
                key="input_naver_clip_text"
            )
            if st.button("⚡ 붙여넣은 매물 텍스트 0.1초 분석 & 16개 항목 즉시 적용", type="primary", use_container_width=True, key="btn_parse_clip_text"):
                if clip_article_text.strip():
                    parsed_clip = parse_naver_clipboard_text(clip_article_text)
                    if parsed_clip:
                        queue_state_update("apply_apt", data=parsed_clip, clean_previous=True, success_msg=f"🎉 네이버 매물 [{parsed_clip.get('main_title', '매물')}] 텍스트 분석 완료! 16대 점검항목과 썸네일에 즉시 자동 반영되었습니다.", target_tab="📝 ③ 아파트 중개대상물 표시")
                    else:
                        st.warning("붙여넣은 텍스트에서 매물 정보를 식별하지 못했습니다. 형식을 확인해주세요.")
                else:
                    st.warning("네이버 부동산 매물 상세 텍스트를 먼저 붙여넣어 주세요.")

    # ----------------------------------------------------
    # 📄 [요구사항 1] 공적서류 (집합건물 표제부/전유부, 토지대장) 자동 분석
    # ----------------------------------------------------
    with st.expander("📄 [원클릭 1초 자동완성] 건축물대장 (표제부 / 전유부) & 공적서류 분석", expanded=True):
        st.markdown("""
        <div style="font-size:14px; color:#2D3748; margin-bottom:10px;">
            정부24, 세움터, 일사편리에서 발급받은 <b>건축물대장(표제부/전유부)</b>, <b>토지대장</b>, <b>토지이용계획원</b> PDF 파일을 올리시면 
            <b>소재지, 면적, 층수, 용도, 준공일, 주차, 세대수</b>가 16개 항목에 1초 만에 자동 완성됩니다!<br/>
            <span style="color:#C53030; font-weight:700;">🏢 집합건물의 경우 표제부와 전유부를 함께 올리시면 건물 전체 정보와 호실 정보가 완벽하게 결합(Merge)됩니다.</span>
        </div>
        """, unsafe_allow_html=True)

        tab_doc_smart, tab_doc_split, tab_doc_txt = st.tabs([
            "📁 스마트 다중/통합 PDF 업로드 (표제부+전유부 자동 병합)",
            "🏢 표제부 & 🚪 전유부 2단계 분리 업로드 (집합건물 전용)",
            "📋 서류 텍스트 직접 붙여넣기 (정부24 보안문서 100% 대응)"
        ])

        # [탭 1] 스마트 통합/다중 업로드
        with tab_doc_smart:
            uploaded_docs = st.file_uploader(
                "건축물대장(표제부, 전유부) / 토지대장 PDF 서류를 드래그하여 놓으세요 (복수 선택 지원)",
                type=["pdf"],
                accept_multiple_files=True,
                help="표제부와 전유부 PDF를 2개 모두 선택하거나 드래그하시면 자동으로 각각 분석하여 하나의 완벽한 점검표로 병합합니다.",
                key="doc_multi_pdf_uploader_key"
            )
            if uploaded_docs:
                upload_sig = "-".join([f"{f.name}_{f.size}" for f in uploaded_docs])
                if st.session_state.get("last_smart_upload_sig") != upload_sig:
                    try:
                        with st.spinner("공적서류 정밀 분석 및 16대 항목 자동 반영 중..."):
                            doc_parsed_result = None
                            doc_parsed_type = ""
                            if len(uploaded_docs) == 1:
                                doc_parsed_type, doc_parsed_result, _ = parse_official_document(uploaded_docs[0], uploaded_docs[0].name)
                            else:
                                title_data = {}
                                exclusive_data = {}
                                other_data = {}
                                types_found = []

                                for u_file in uploaded_docs:
                                    p_type, p_res, _ = parse_official_document(u_file, u_file.name)
                                    types_found.append(p_type)
                                    if "표제부" in p_type:
                                        title_data.update(p_res)
                                    elif "전유부" in p_type:
                                        exclusive_data.update(p_res)
                                    else:
                                        other_data.update(p_res)

                                if title_data and exclusive_data:
                                    doc_parsed_result = merge_building_registers(title_data, exclusive_data)
                                    doc_parsed_type = "집합건축물대장 (표제부 + 전유부 2개 서류 완벽 통합)"
                                elif title_data:
                                    doc_parsed_result = title_data
                                    doc_parsed_type = "집합건축물대장 (표제부)"
                                elif exclusive_data:
                                    doc_parsed_result = exclusive_data
                                    doc_parsed_type = "집합건축물대장 (전유부)"
                                else:
                                    doc_parsed_result = other_data
                                    doc_parsed_type = ", ".join(types_found)

                            st.session_state["last_smart_upload_sig"] = upload_sig
                            if doc_parsed_result:
                                queue_state_update("apply_apt", data=doc_parsed_result, clean_previous=True, success_msg=f"🎉 [{doc_parsed_type}] 분석 완료! 16대 점검항목과 썸네일에 1초 만에 즉시 반영되었습니다.", target_tab="📝 ③ 아파트 중개대상물 표시")
                            else:
                                st.error("⚠️ 업로드하신 PDF 서류에서 텍스트를 읽어오지 못했습니다. 정부24/세움터의 위변조 방지 보안 인쇄(DRM) 전자문서이거나 스캔 이미지일 가능성이 높습니다. 정부24 열람 화면에서 마우스로 텍스트를 복사(Ctrl+C)하여 세 번째 [📋 서류 텍스트 직접 붙여넣기] 탭에 넣어주시면 0.1초 만에 완벽하게 분석됩니다!")
                    except Exception as e:
                        st.error(f"서류 분석 중 오류가 발생했습니다: {e}")

        # [탭 2] 표제부 & 전유부 분리 업로드
        with tab_doc_split:
            col_sp_title, col_sp_excl = st.columns(2)
            with col_sp_title:
                st.markdown("""
                <div style="background:#EBF8FF; border:1px solid #90CDF4; border-radius:8px; padding:8px 12px; margin-bottom:8px;">
                    <b>🏢 1. 표제부 (총괄표제부 / 표제부)</b><br/>
                    <span style="font-size:12px; color:#4A5568;">단지명, 최고층수, 총주차대수, 세대수, 준공일, 구조</span>
                </div>
                """, unsafe_allow_html=True)
                up_title_file = st.file_uploader("표제부 PDF 업로드", type=["pdf"], key="up_split_title")

            with col_sp_excl:
                st.markdown("""
                <div style="background:#FEFCBF; border:1px solid #ECC94B; border-radius:8px; padding:8px 12px; margin-bottom:8px;">
                    <b>🚪 2. 전유부 (각 동·호수)</b><br/>
                    <span style="font-size:12px; color:#4A5568;">해당 동, 호수, 해당층, 전용면적, 주거공용면적(공급면적)</span>
                </div>
                """, unsafe_allow_html=True)
                up_excl_file = st.file_uploader("전유부 PDF 업로드", type=["pdf"], key="up_split_excl")

            if up_title_file or up_excl_file:
                split_sig = f"{getattr(up_title_file, 'name', '')}_{getattr(up_title_file, 'size', '')}_{getattr(up_excl_file, 'name', '')}_{getattr(up_excl_file, 'size', '')}"
                if st.session_state.get("last_split_upload_sig") != split_sig:
                    try:
                        with st.spinner("표제부 및 전유부 정밀 분석 중..."):
                            t_data_sp = {}
                            e_data_sp = {}
                            if up_title_file:
                                _, t_data_sp, _ = parse_official_document(up_title_file, up_title_file.name)
                            if up_excl_file:
                                _, e_data_sp, _ = parse_official_document(up_excl_file, up_excl_file.name)

                            doc_parsed_res_sp = None
                            doc_type_sp = ""
                            if t_data_sp and e_data_sp:
                                doc_parsed_res_sp = merge_building_registers(t_data_sp, e_data_sp)
                                doc_type_sp = "집합건축물대장 (표제부 + 전유부 2단계 통합 완성)"
                            elif t_data_sp:
                                doc_parsed_res_sp = t_data_sp
                                doc_type_sp = "집합건축물대장 (표제부 단독)"
                            elif e_data_sp:
                                doc_parsed_res_sp = e_data_sp
                                doc_type_sp = "집합건축물대장 (전유부 단독)"

                            st.session_state["last_split_upload_sig"] = split_sig
                            if doc_parsed_res_sp:
                                queue_state_update("apply_apt", data=doc_parsed_res_sp, clean_previous=True, success_msg=f"🎉 [{doc_type_sp}] 분석 완료! 16대 점검항목과 썸네일에 즉시 자동 반영되었습니다.", target_tab="📝 ③ 아파트 중개대상물 표시")
                            else:
                                st.error("⚠️ 분리 업로드된 PDF 파일에서 텍스트를 감지하지 못했습니다. 보안(DRM) 문서인 경우 세 번째 [📋 서류 텍스트 직접 붙여넣기] 탭을 이용해주세요!")
                    except Exception as e:
                        st.error(f"분리 서류 분석 중 오류: {e}")

        # [탭 3] 텍스트 직접 붙여넣기
        with tab_doc_txt:
            sub_txt_tab1, sub_txt_tab2 = st.tabs([
                "📋 대장 전체 텍스트(스크립트) 통째로 붙여넣기 (가장 편리 & ⭐추천)",
                "🏢 표제부 & 🚪 전유부 2칸 분리 붙여넣기 (선택)"
            ])
            with sub_txt_tab1:
                st.markdown("""
                <div style="font-size:13px; color:#2D3748; background:#F7FAFC; border:1px solid #CBD5E0; padding:8px 12px; border-radius:6px; margin-bottom:8px;">
                    💡 <b>1초 자동 분석:</b> 정부24, 세움터, 일사편리에서 열람한 건축물대장 텍스트 전체(표제부/전유부/일반대장)를 마우스로 복사(Ctrl+C)하여 아래에 그대로 붙여넣으세요! 표제부와 전유부를 자동으로 인식하여 병합합니다.
                </div>
                """, unsafe_allow_html=True)
                raw_unified_txt = st.text_area(
                    "건축물대장 전체 열람 복사 텍스트 (스크립트)",
                    height=130,
                    placeholder="대지위치: 부산시 사상구 덕포동 220\n건축물명칭: 사상 중흥S-클래스 제105동 제2501호\n층별: 25층\n전유부분 면적: 79.85㎡\n사용승인일: 2023-07-28...",
                    key="txt_raw_unified_doc"
                )
                if st.button("🔍 붙여넣은 대장 텍스트 0.1초 통합 분석 & 즉시 적용", type="primary", key="btn_parse_unified_text", use_container_width=True):
                    if raw_unified_txt.strip():
                        u_doc_type, u_doc_res = parse_raw_script_document(raw_unified_txt)
                        if u_doc_res:
                            queue_state_update("apply_apt", data=u_doc_res, clean_previous=True, success_msg=f"🎉 [{u_doc_type}] 분석 완료! 16대 점검항목과 썸네일에 즉시 자동 반영되었습니다.", target_tab="📝 ③ 아파트 중개대상물 표시")
                        else:
                            st.warning("붙여넣은 대장 텍스트에서 건축물 정보를 식별하지 못했습니다. 내용을 확인해주세요.")
                    else:
                        st.warning("건축물대장 텍스트를 먼저 붙여넣어 주세요.")

            with sub_txt_tab2:
                col_txt_t, col_txt_e = st.columns(2)
                with col_txt_t:
                    st.markdown("<b>🏢 표제부 텍스트</b>", unsafe_allow_html=True)
                    raw_title_txt = st.text_area(
                        "표제부 열람 텍스트",
                        height=100,
                        placeholder="대지위치: 부산시 사상구 덕포동 220\n건축물명칭: 사상 중흥S-클래스\n층수: 지상 36층 / 지하 3층\n세대수: 1,572세대\n주차대수: 1,685대\n사용승인일: 2023-07-28...",
                        key="txt_raw_title"
                    )
                with col_txt_e:
                    st.markdown("<b>🚪 전유부 텍스트</b>", unsafe_allow_html=True)
                    raw_excl_txt = st.text_area(
                        "전유부 열람 텍스트",
                        height=100,
                        placeholder="건축물명칭: 제105동 제2501호\n층별: 25층\n전유부분 면적: 79.85㎡\n공용부분(계단/복도): 31.57㎡...",
                        key="txt_raw_excl"
                    )

                if st.button("🔍 분리 입력된 표제부/전유부 텍스트 분석 및 즉시 적용", type="primary", key="btn_parse_split_text", use_container_width=True):
                    t_parsed = parse_building_register_title(raw_title_txt) if raw_title_txt.strip() else {}
                    e_parsed = parse_building_register_exclusive(raw_excl_txt) if raw_excl_txt.strip() else {}

                    doc_parsed_res_txt = None
                    doc_type_txt = ""
                    if t_parsed and e_parsed:
                        doc_parsed_res_txt = merge_building_registers(t_parsed, e_parsed)
                        doc_type_txt = "집합건축물대장 (표제부 + 전유부 텍스트 통합완료)"
                    elif t_parsed:
                        doc_parsed_res_txt = t_parsed
                        doc_type_txt = "집합건축물대장 (표제부 텍스트)"
                    elif e_parsed:
                        doc_parsed_res_txt = e_parsed
                        doc_type_txt = "집합건축물대장 (전유부 텍스트)"

                    if doc_parsed_res_txt:
                        queue_state_update("apply_apt", data=doc_parsed_res_txt, clean_previous=True, success_msg=f"🎉 [{doc_type_txt}] 분석 완료! 16대 점검항목과 썸네일에 즉시 자동 반영되었습니다.", target_tab="📝 ③ 아파트 중개대상물 표시")
                    else:
                        st.warning("붙여넣은 텍스트에서 건축물대장 정보를 식별하지 못했습니다. 내용을 확인해주세요.")

    # 썸네일 데이터에서 가져오기 및 퀵 컨트롤 버튼
    col_syn1, col_syn2, col_syn3 = st.columns([1, 1, 1])
    with col_syn1:
        if st.button("🔄 썸네일 입력값 동기화", use_container_width=True, help="1단계 썸네일에 입력한 층수, 가격, 날짜 등을 가져옵니다."):
            st.session_state.ad_trade_type = st.session_state.thumb_trade_type
            st.session_state.ad_price_text = st.session_state.thumb_price_text
            st.session_state.ad_floor_info = st.session_state.spec_line1
            st.session_state.ad_room_bath = st.session_state.spec_line3
            st.session_state.ad_move_in_date = st.session_state.spec_line4
            st.session_state.ad_direction = st.session_state.spec_line5
            st.success("썸네일 정보가 점검표에 반영되었습니다!")
            st.rerun()
    with col_syn2:
        if st.button("✨ 새 매물 빈 양식 만들기", use_container_width=True, help="새로운 매물을 등록할 수 있도록 모든 입력칸을 깨끗하게 비웁니다."):
            st.session_state.ad_location = ""
            st.session_state.ad_area_supply = ""
            st.session_state.ad_area_exclusive = ""
            st.session_state.ad_floor_info = ""
            st.session_state.ad_room_bath = ""
            st.session_state.ad_maintenance_fee = ""
            st.session_state.ad_maintenance_detail = ""
            st.session_state.ad_price_text = ""
            st.session_state.ad_deposit_sub = "- / -"
            st.session_state.ad_direction = ""
            st.session_state.ad_move_in_date = "즉시입주 협의가능"
            st.session_state.ad_parking = ""
            st.session_state.ad_households = ""
            st.session_state.ad_building_use = "공동주택 (아파트)"
            st.session_state.ad_approval_date = ""
            st.info("입력칸이 초기화되었습니다. 새로운 매물 정보를 입력해주세요.")
            st.rerun()
    with col_syn3:
        if st.button("📋 사상 중흥S-클래스 예시 복원", use_container_width=True, help="기본 사상 중흥S-클래스 예시 데이터를 다시 채웁니다."):
            for k, v in DEFAULT_SPEC.items():
                st.session_state[f"ad_{k}"] = v
            st.success("기본 예시 데이터로 복원되었습니다.")
            st.rerun()

    # 좌우 컬럼 분할 (PC에서는 좌:입력 / 우:결과, 모바일에서는 위:입력 / 아래:결과)
    col_ad_input, col_ad_output = st.columns([1.1, 1.2])

    with col_ad_input:
        st.markdown("""
        <div style="background:#EBF8FF; border:1.5px solid #63B3ED; border-radius:10px; padding:12px 16px; margin-bottom:15px;">
            <div style="font-size:14px; font-weight:700; color:#2B6CB0; margin-bottom:3px;">
                ✏️ <b>입력 및 수정 방법</b>
            </div>
            <div style="font-size:13px; color:#2D3748; line-height:1.4;">
                아래 흰색 <b>네모 칸을 마우스로 클릭</b>하시면 글자를 바로 지우고 자유롭게 수정하실 수 있습니다!<br/>
                새로운 매물을 등록하시려면 상단의 <b>[✨ 새 매물 빈 양식 만들기]</b> 버튼을 누르시면 편리합니다.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("### 📋 16대 점검항목 입력 및 수정")

        # 1. 소재지
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <b>01. 소재지</b>
            <span class="spec-badge badge-red">동·리·지번 필수</span>
        </div>
        """, unsafe_allow_html=True)
        st.text_input(
            "소재지 주소",
            key="ad_location",
            help="동·리 및 지번 표기 필수 (아파트 동·호수는 생략 가능)"
        )

        # 2. 공급/전용면적
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>02. 공급 / 전용면적</b>
            <span class="spec-badge badge-orange">법정단위 ㎡ 표기 (평수 제외)</span>
        </div>
        """, unsafe_allow_html=True)
        c_ar1, c_ar2 = st.columns(2)
        with c_ar1:
            st.text_input("공급면적 (㎡)", key="ad_area_supply")
        with c_ar2:
            st.text_input("전용면적 (㎡)", key="ad_area_exclusive")
        
        # 실시간 면적 및 전용률 계산 프리뷰 (법정계량단위 ㎡ 단독 표기, 평형 제외)
        area_sum_m2, _ = format_area_text(st.session_state.ad_area_supply, st.session_state.ad_area_exclusive)
        st.markdown(f"""
        <div style="background:#F1F3F5; padding:6px 12px; border-radius:6px; font-size:13px; color:#495057; margin-bottom:8px;">
            📐 <b>계산 결과:</b> {area_sum_m2}
        </div>
        """, unsafe_allow_html=True)

        # 3. 해당층 / 총층
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>03. 해당층 / 총층</b>
            <span class="spec-badge badge-green">저/중/고 표기가능</span>
        </div>
        """, unsafe_allow_html=True)
        st.text_input(
            "해당층 / 총층",
            key="ad_floor_info",
            help="예: 25 / 36층 (아파트의 경우 의뢰인 요청 시 저/중/고층 대체 가능)"
        )

        # 4. 방수 / 욕실수
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>04. 방수 / 욕실수</b>
            <span class="spec-badge badge-gray">대장 기준</span>
        </div>
        """, unsafe_allow_html=True)
        st.text_input(
            "방수 / 욕실수",
            key="ad_room_bath",
            help="예: 3 / 2개"
        )

        # 5. 관리비
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>05. 관리비 & 세부내역</b>
            <span class="spec-badge badge-red">월 10만원↑ 세부내역 필수</span>
        </div>
        """, unsafe_allow_html=True)
        c_mf1, c_mf2 = st.columns([1, 1.4])
        with c_mf1:
            st.text_input("월 관리비", key="ad_maintenance_fee", placeholder="예: 월 18만 원")
        with c_mf2:
            st.text_input(
                "세부내역 (알아보기 쉬운 분리 기재)",
                key="ad_maintenance_detail",
                placeholder="예: 공용관리비 약 13만 원 (수도·전기·가스 실사용량 별도 부과)",
                help="공용관리비와 개별 사용량(전기/수도/가스)을 명확히 구분하여 기재"
            )

        # 6. 거래 형태 & 7. 가격
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>06. 거래 형태 & 07. 가격</b>
            <span class="spec-badge badge-orange">정확한 가격 명시</span>
        </div>
        """, unsafe_allow_html=True)
        c_pr1, c_pr2 = st.columns([1, 1.4])
        with c_pr1:
            trade_opts_ad = ["매매", "전세", "월세", "단기임대"]
            if st.session_state.ad_trade_type not in trade_opts_ad:
                st.session_state.ad_trade_type = trade_opts_ad[0]
            st.selectbox("거래 형태", trade_opts_ad, key="ad_trade_type")
        with c_pr2:
            st.text_input("거래 가격", key="ad_price_text")
        
        st.text_input(
            "기보증금 / 월세 승계액",
            key="ad_deposit_sub",
            help="기보증금 또는 월세가 있는 경우 작성 (없으면 '- / -')"
        )

        # 8. 방향
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>08. 방향 (기준 명시)</b>
            <span class="spec-badge badge-green">주실(거실) 기준</span>
        </div>
        """, unsafe_allow_html=True)
        st.text_input("방향", key="ad_direction", help="예: 남동향 (거실 기준)")

        # 9. 현관구조 & 10. 난방
        c_et1, c_et2 = st.columns(2)
        with c_et1:
            st.markdown("<b>09. 현관구조</b>", unsafe_allow_html=True)
            entrance_opts = ["계단식", "복도식", "복합식"]
            if st.session_state.ad_entrance_type not in entrance_opts:
                st.session_state.ad_entrance_type = entrance_opts[0]
            st.selectbox("현관구조", entrance_opts, key="ad_entrance_type")
        with c_et2:
            st.markdown("<b>10. 난방(방식/연료)</b>", unsafe_allow_html=True)
            st.text_input("난방방식/연료", key="ad_heating")

        # 11. 입주가능일 & 12. 총주차대수
        c_mv1, c_mv2 = st.columns(2)
        with c_mv1:
            st.markdown("<b>11. 입주가능일</b>", unsafe_allow_html=True)
            st.text_input("입주가능일", key="ad_move_in_date")
        with c_mv2:
            st.markdown("<b>12. 총주차대수</b>", unsafe_allow_html=True)
            st.text_input("총주차대수", key="ad_parking")

        # 13. 해당면적 세대수 & 14. 건축물 용도
        c_hs1, c_hs2 = st.columns(2)
        with c_hs1:
            st.markdown("<b>13. 해당면적 세대수</b>", unsafe_allow_html=True)
            st.text_input("해당면적 세대수", key="ad_households")
        with c_hs2:
            st.markdown("<b>14. 건축물 용도</b>", unsafe_allow_html=True)
            st.text_input("건축물 용도", key="ad_building_use")

        # 15. 사용승인일
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>15. 사용승인일 (준공일)</b>
            <span class="spec-badge badge-red">대장 기준 필수</span>
        </div>
        """, unsafe_allow_html=True)
        st.text_input("사용승인일", key="ad_approval_date", help="건축물대장 상 사용승인일 기재 필수")

        # 16. 중개사무소 정보 (ON/OFF 선택 및 소공 지원)
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 15px; margin-bottom: 5px;">
            <b>16. 중개사무소 정보</b>
            <span class="spec-badge badge-green">ON/OFF 선택 가능</span>
        </div>
        """, unsafe_allow_html=True)

        st.checkbox(
            "✅ 중개사무소 정보 포함하기 (텍스트 및 카드 이미지에 반영)",
            key="ad_include_office_info",
            help="체크 해제 시 중개사무소 정보를 제외하고 순수 매물 정보(01~15번 항목)만 출력합니다."
        )

        if st.session_state.ad_include_office_info:
            c_of1, c_of2 = st.columns(2)
            with c_of1:
                st.text_input("중개사무소 명칭 (상호)", key="ad_office_name")
                st.text_input("대표 공인중개사 성명", key="ad_office_owner")
                st.text_input("사무실 연락처", key="ad_office_phone")
            with c_of2:
                st.text_input("중개등록번호", key="ad_office_reg_no")
                st.text_input("사무소 소재지", key="ad_office_address")

            st.markdown("""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 15px; margin-bottom: 5px;">
                <b>17. 소속공인중개사(소공) 담당자 정보</b>
                <span class="spec-badge badge-gray">선택 입력</span>
            </div>
            """, unsafe_allow_html=True)
            c_as1, c_as2 = st.columns(2)
            with c_as1:
                st.text_input("소공/담당자 성명", key="ad_assistant_name", placeholder="예: 하승원 소속공인중개사")
            with c_as2:
                st.text_input("담당자 직통 연락처", key="ad_assistant_phone", placeholder="예: 010-5552-5265")
        else:
            st.info("ℹ️ 중개사무소 정보가 제외되었습니다. 순수 매물 스펙(01~15번 항목)만 출력됩니다. (소공 및 협력 중개사 활용 가능)")


    # 우측: 실시간 완성 뷰 (네이버 광고 점검표 1:1 대조 리스트)
    with col_ad_output:
        st.markdown("### 📋 네이버 광고 16개 점검표 (대조용)")
        st.caption("네이버 부동산 매물 등록창을 띄워두고 위에서부터 순서대로 보며 입력하세요.")

        # 현재 입력 데이터 딕셔너리 구축
        current_spec_data = {
            "location": st.session_state.ad_location,
            "area_supply": st.session_state.ad_area_supply,
            "area_exclusive": st.session_state.ad_area_exclusive,
            "floor_info": st.session_state.ad_floor_info,
            "room_bath": st.session_state.ad_room_bath,
            "maintenance_fee": st.session_state.ad_maintenance_fee,
            "maintenance_detail": st.session_state.ad_maintenance_detail,
            "trade_type": st.session_state.ad_trade_type,
            "price_text": st.session_state.ad_price_text,
            "deposit_sub": st.session_state.ad_deposit_sub,
            "direction": st.session_state.ad_direction,
            "entrance_type": st.session_state.ad_entrance_type,
            "heating": st.session_state.ad_heating,
            "move_in_date": st.session_state.ad_move_in_date,
            "parking": st.session_state.ad_parking,
            "households": st.session_state.ad_households,
            "building_use": st.session_state.ad_building_use,
            "approval_date": st.session_state.ad_approval_date,
            "office_name": st.session_state.ad_office_name,
            "office_owner": st.session_state.ad_office_owner,
            "office_reg_no": st.session_state.ad_office_reg_no,
            "office_address": st.session_state.ad_office_address,
            "office_phone": st.session_state.ad_office_phone,
            "include_office_info": st.session_state.ad_include_office_info,
            "assistant_name": st.session_state.ad_assistant_name,
            "assistant_phone": st.session_state.ad_assistant_phone,
        }

        # 16개 항목 카드 리스트 (코드 노출 없는 안전한 인라인 렌더링)
        items_list = get_ordered_spec_table_data(current_spec_data)
        
        rows_html = []
        for it in items_list:
            num_str = f"{it['num']:02d}"
            # 줄바꿈은 <br/>로 깔끔하게 한 줄씩 정돈
            val_formatted = it['val'].replace('\n', '<br/>')
            row_markup = f'<div style="border-bottom:1px solid #E9ECEF; padding:11px 6px;"><div style="display:flex; justify-content:space-between; margin-bottom:4px;"><span style="font-size:14px; font-weight:700; color:#333D4B;"><span style="color:#F48A26;">[{num_str}]</span> {it["name"]}</span><span style="font-size:12px; color:#8B95A1;">{it["guide"]}</span></div><div style="font-size:15px; color:#191F28; font-weight:600; line-height:1.6; background:#F8F9FB; padding:8px 12px; border-radius:6px; margin-top:4px;">{val_formatted}</div></div>'
            rows_html.append(row_markup)

        full_table_html = f'<div style="background:#FFFFFF; border:1.5px solid #CBD5E0; border-radius:12px; padding:14px 18px; box-shadow:0 2px 8px rgba(0,0,0,0.04); max-height:680px; overflow-y:auto;">{"".join(rows_html)}</div>'
        st.markdown(full_table_html, unsafe_allow_html=True)

        # 전체 텍스트 복사 영역
        st.markdown("<br/>", unsafe_allow_html=True)
        ad_guide_txt = generate_naver_ad_guide_text(current_spec_data)
        st.text_area("📋 [네이버 광고 대조용] 전체 텍스트 복사", value=ad_guide_txt, height=130)

        # 필요 시 1080px 고화질 표시 카드 이미지 다운로드 접이식 메뉴 (중복 이미지는 삭제하고 다운로드 기능만 제공)
        with st.expander("🖼️ [다운로드] 1080px 중개대상물 표시 카드 저장하기", expanded=False):
            with st.spinner("표시 카드 렌더링 중..."):
                spec_card_img = render_spec_table_image(current_spec_data)
            card_byte_arr = io.BytesIO()
            spec_card_img.save(card_byte_arr, format="PNG", quality=95)
            card_bytes = card_byte_arr.getvalue()

            clean_loc = re.sub(r'[^\w\s-]', '', (st.session_state.ad_location.split(" ")[-1] if st.session_state.ad_location else "매물")).strip()
            clean_trade = re.sub(r'[^\w\s-]', '', (st.session_state.ad_trade_type or "매매")).strip()
            card_filename = f"중개대상물표시_{clean_loc}_{clean_trade}.png"

            st.markdown(render_direct_download_button(card_bytes, card_filename, "💾 [원클릭 즉시 다운로드] 1080px 표시 카드 저장", "#1A202C"), unsafe_allow_html=True)
            st.caption("스마트폰에서는 위 버튼을 누르시면 사진첩에 바로 다운로드 저장됩니다.")


# ====================================================
# [ 탭 4 ] 상가 중개대상물 표시 생성기 (임차 & 매매 전용)
# ====================================================


# ====================================================
# [ 탭 2-2 ] 주택 네이버 광고 & 중개대상물 표시 생성기
# ====================================================
def render_tab_house_ad():
    st.markdown('''
    <div style="background-color: #F8F9FB; border-left: 4px solid #38A169; padding: 12px 18px; border-radius: 6px; margin-bottom: 20px;">
        <span style="font-size: 15px; font-weight: 700; color: #1E2022;">
            🏡 주택(단독·다가구·전원주택) 인터넷 표시·광고 점검표 (16개 법정 항목)
        </span><br/>
        <span style="font-size: 13px; color: #6C757D;">
            단독주택, 다가구, 상가주택 등 주택 실무에 특화된 16개 법정 표시항목을 블로그 표 및 네이버 광고 형식으로 완벽하게 자동 생성합니다.
        </span>
    </div>
    ''', unsafe_allow_html=True)

    # 상단 썸네일 데이터 실시간 동기화 배너
    col_hs1, col_hs2 = st.columns([3, 1])
    with col_hs1:
        st.markdown('''
        <div style="font-size:13.5px; color:#22543D; background:#F0FFF4; border:1px solid #9AE6B4; padding:8px 14px; border-radius:6px;">
            🔄 <b>주택 썸네일 데이터 연동:</b> 썸네일에서 수정한 주택명, 거래형태, 가격, 층수, 방수, 입주일, 방향이 점검표에 자동 연동됩니다.
        </div>
        ''', unsafe_allow_html=True)
    with col_hs2:
        if st.button("🔄 주택 썸네일값 즉시 동기화", key="btn_sync_house_ad", use_container_width=True):
            st.session_state.house_ad_trade_type = st.session_state.house_trade_type
            st.session_state.house_ad_price_text = st.session_state.house_price_text
            st.session_state.house_ad_floor_info = st.session_state.house_spec1
            st.session_state.house_ad_room_bath = st.session_state.house_spec3
            st.session_state.house_ad_move_in_date = st.session_state.house_spec4
            st.session_state.house_ad_direction = st.session_state.house_spec5
            if st.session_state.house_main_title:
                st.session_state.house_ad_location = f"부산광역시 사상구 ({st.session_state.house_main_title})"
            st.success("주택 썸네일 데이터가 점검표에 동기화되었습니다!")
            st.rerun()

    # 좌우 분할 (입력 폼 / 실시간 미리보기)
    col_in, col_out = st.columns([1.1, 1.2])
    with col_in:
        st.markdown("### 📋 주택 16대 점검항목 입력 및 수정")
        st.text_input("1. 소재지 (지번 포함)", key="house_ad_location")
        c_a1, c_a2 = st.columns(2)
        with c_a1:
            st.text_input("2-1. 대지면적 (㎡)", key="house_ad_area_land")
        with c_a2:
            st.text_input("2-2. 연면적 (㎡)", key="house_ad_area_gross")
        st.text_input("3. 해당층 / 총층", key="house_ad_floor_info")
        st.text_input("4. 방수 / 욕실수", key="house_ad_room_bath")
        st.text_input("5. 관리비 (세부내역)", key="house_ad_maintenance_fee")
        c_t1, c_t2 = st.columns(2)
        with c_t1:
            st.selectbox("6. 거래 형태", ["매매", "전세", "월세", "급매"], key="house_ad_trade_type")
        with c_t2:
            st.text_input("7. 거래 금액", key="house_ad_price_text")
        st.text_input("8. 주실(거실) 방향", key="house_ad_direction")
        st.text_input("9. 주차 대수", key="house_ad_parking")
        st.text_input("10. 난방 방식 / 연료", key="house_ad_heating")
        st.text_input("11. 입주 가능일", key="house_ad_move_in_date")
        st.text_input("12. 건축물 용도", key="house_ad_building_use")
        st.text_input("13. 주구조", key="house_ad_structure")
        st.text_input("14. 사용승인일", key="house_ad_approval_date")
        st.text_input("15. 주요 특징", key="house_ad_feature")

        st.markdown("#### 🏢 중개사무소 정보")
        st.checkbox("중개사무소 정보 포함", value=True, key="house_ad_include_office")
        c_as1, c_as2 = st.columns(2)
        with c_as1:
            st.text_input("소속공인중개사(직원) 성명", key="house_ad_as_name", placeholder="미입력 시 생략")
        with c_as2:
            st.text_input("소속공인중개사 연락처", key="house_ad_as_phone", placeholder="미입력 시 생략")

    with col_out:
        st.markdown("### 📊 실시간 주택 점검표 미리보기 & 복사")
        house_dict = {
            "location": st.session_state.house_ad_location,
            "area_land": st.session_state.house_ad_area_land,
            "area_gross": st.session_state.house_ad_area_gross,
            "floor_info": st.session_state.house_ad_floor_info,
            "room_bath": st.session_state.house_ad_room_bath,
            "maintenance_fee": st.session_state.house_ad_maintenance_fee,
            "trade_type": st.session_state.house_ad_trade_type,
            "price_text": st.session_state.house_ad_price_text,
            "direction": st.session_state.house_ad_direction,
            "parking": st.session_state.house_ad_parking,
            "heating": st.session_state.house_ad_heating,
            "move_in_date": st.session_state.house_ad_move_in_date,
            "building_use": st.session_state.house_ad_building_use,
            "structure": st.session_state.house_ad_structure,
            "approval_date": st.session_state.house_ad_approval_date,
            "feature": st.session_state.house_ad_feature,
            "include_office_info": st.session_state.house_ad_include_office,
            "office_name": st.session_state.get("ad_office_name", "참좋은공인중개사사무소"),
            "office_owner": st.session_state.get("ad_office_owner", "신제환"),
            "office_reg_no": st.session_state.get("ad_office_reg_no", "제 26530-2026-00009 호"),
            "office_address": st.session_state.get("ad_office_address", "부산광역시 사상구 강선로 9, 1층"),
            "office_phone": st.session_state.get("ad_office_phone", "010-9667-4201"),
            "assistant_name": st.session_state.house_ad_as_name,
            "assistant_phone": st.session_state.house_ad_as_phone
        }
        house_items = get_house_spec_table_data(house_dict)
        house_html = generate_blog_html_table(house_dict, items=house_items)
        house_txt = generate_clipboard_text(house_dict, items=house_items)
        house_guide = generate_naver_ad_guide_text(house_dict, items=house_items)

        tab_hov1, tab_hov2, tab_hov3, tab_hov4 = st.tabs([
            "📋 1. 스마트에디터 HTML 표 복사",
            "📄 2. 네이버광고 등록 체크리스트",
            "💬 3. 텍스트 복사 (카톡/본문)",
            "🖼️ 4. 고화질 카드 이미지 저장"
        ])

        with tab_hov1:
            st.markdown(house_html, unsafe_allow_html=True)
            st.markdown(render_copy_button(house_html, "📋 [원클릭 복사] 블로그 스마트에디터 표 서식 복사", "btn_copy_h_html"), unsafe_allow_html=True)

        with tab_hov2:
            st.text_area("네이버 광고 등록용", value=house_guide, height=350, key="txt_h_guide")
            st.markdown(render_copy_button(house_guide, "📄 [원클릭 복사] 네이버 등록 가이드 복사", "btn_copy_h_guide"), unsafe_allow_html=True)

        with tab_hov3:
            st.text_area("텍스트 양식", value=house_txt, height=350, key="txt_h_clip")
            st.markdown(render_copy_button(house_txt, "💬 [원클릭 복사] 일반 텍스트 복사", "btn_copy_h_txt"), unsafe_allow_html=True)

        with tab_hov4:
            with st.spinner("주택 점검표 카드 이미지 생성 중..."):
                h_card_img = render_spec_table_image(house_dict, items=house_items)
            st.image(h_card_img, caption="1080px 정방형 중개대상물 표시 카드", use_container_width=True)
            h_card_io = io.BytesIO()
            h_card_img.save(h_card_io, format="PNG", quality=98)
            h_card_bytes = h_card_io.getvalue()
            h_card_name = f"중개대상물표시_주택_{st.session_state.house_ad_trade_type}.png"
            st.download_button("📥 1080px 주택 표시 카드 파일 다운로드", data=h_card_bytes, file_name=h_card_name, mime="image/png", key="btn_h_card_down", use_container_width=True)
            st.markdown(render_direct_download_button(h_card_bytes, h_card_name, "💾 [즉시 다운로드] 주택 표시 카드 저장", "#1A202C"), unsafe_allow_html=True)


# ====================================================
# [ 탭 2-3 ] 상가 네이버 광고 & 중개대상물 표시 생성기 (임차 & 매매)
# ====================================================
def render_tab_comm_ad():

    st.markdown("""
    <div style="background-color: #181C24; border-left: 4px solid #DAA844; padding: 14px 18px; border-radius: 6px; margin-bottom: 20px; color: #FFFFFF;">
        <span style="font-size: 16px; font-weight: 700; color: #DAA844;">
            🏪 상가(근린생활시설/점포/건물) 인터넷 표시·광고 점검표 & 블로그 서식 생성기
        </span><br/>
        <span style="font-size: 13px; color: #CBD5E0;">
            주출입구 방향, 화장실 구분, 권리금, 추천업종, 전기/설비, 매매 시 연간 수익률 분석 등 상가 실무에 특화된 법정 표시사항을 완벽하게 생성합니다.
        </span>
    </div>
    """, unsafe_allow_html=True)

    # 1. 거래 형태 라디오 (임대차 vs 매매)
    comm_ad_mode_select = st.radio(
        "상가 거래 형태 선택",
        options=["🔑 상가 임대차 (월세)", "💰 상가 매매 (수익형)"],
        index=0 if "임대차" in st.session_state.comm_ad_mode or "월세" in st.session_state.comm_ad_mode else 1,
        horizontal=True,
        key="comm_ad_mode_radio_selector"
    )
    st.session_state.comm_ad_mode = comm_ad_mode_select
    is_comm_ad_sale = "매매" in comm_ad_mode_select

    # 2. 퀵 액션 버튼들
    c_btn1, c_btn2, c_btn3 = st.columns([1.2, 1, 1])
    with c_btn1:
        if st.button("🔄 상가 썸네일 입력값 동기화", use_container_width=True, help="② 상가 썸네일 탭에 입력한 타이틀과 스펙을 점검표로 가져옵니다."):
            if not is_comm_ad_sale:
                st.session_state.comm_ad_trade_type = "월세"
                st.session_state.comm_ad_recommended_use = st.session_state.comm_lease_spec2.replace("추천 :", "").strip()
                if "|" in st.session_state.comm_lease_spec1:
                    parts = st.session_state.comm_lease_spec1.split("|")
                    st.session_state.comm_ad_price_text = parts[1].strip()
            else:
                st.session_state.comm_ad_trade_type = "매매"
                st.session_state.comm_ad_yield_rate = st.session_state.comm_sale_main_hl
                st.session_state.comm_ad_deposit_rent_summary = st.session_state.comm_sale_price_spec
            st.success("상가 썸네일 입력값이 점검표에 동기화되었습니다!")
            st.rerun()
    with c_btn2:
        if st.button("📋 추천 상가 예시 복원", use_container_width=True):
            defaults = DEFAULT_COMMERCIAL_SPEC_SALE if is_comm_ad_sale else DEFAULT_COMMERCIAL_SPEC_LEASE
            for k, v in defaults.items():
                st.session_state[f"comm_ad_{k}"] = v
            st.success("기본 추천 예시로 복원되었습니다.")
            st.rerun()
    with c_btn3:
        if st.button("✨ 새 상가 빈 양식 만들기", use_container_width=True):
            empty_keys = [
                "location", "area_exclusive", "area_contract", "floor_info", "restroom",
                "maintenance_fee", "maintenance_detail", "price_text", "premium_fee",
                "deposit_rent_summary", "loan_amount", "actual_investment", "yield_rate",
                "direction", "move_in_date", "parking", "current_use", "recommended_use",
                "building_use", "zone_region", "zone_district", "structure", "approval_date", "facility_info"
            ]
            for k in empty_keys:
                st.session_state[f"comm_ad_{k}"] = ""
            st.info("입력칸이 초기화되었습니다.")
            st.rerun()

    # 최근 상가 자동완성 성공 알림 배너
    if st.session_state.get("last_comm_applied_msg"):
        st.success(st.session_state["last_comm_applied_msg"])

    # ----------------------------------------------------
    # 🌐 상가 네이버 부동산 매물 연동 (복사 텍스트 & 매물번호)
    # ----------------------------------------------------
    with st.expander("🌐 [원클릭 1초 자동완성] 네이버 부동산 상가 매물 연동 (클립보드 복사 & 매물번호)", expanded=True):
        st.markdown("""
        <div style="font-size:14px; color:#1A365D; background:#EBF8FF; border:1px solid #BEE3F8; padding:10px 14px; border-radius:8px; margin-bottom:12px;">
            🔗 네이버 부동산의 <b>상가 매물 화면 복사 텍스트</b>를 붙여넣거나 <b>상가 매물 번호</b>를 입력하시면, 
            실시간으로 <b>소재지, 가격, 층수, 전용/계약면적, 방향, 주차대수, 용도, 주구조, 권리금 등 상가 18대 항목</b>과 <b>상가 썸네일</b>을 1초 만에 자동 완성합니다!
        </div>
        """, unsafe_allow_html=True)

        comm_tab_crawl_num, comm_tab_crawl_txt = st.tabs([
            "🔍 네이버 상가 매물번호 / URL 크롤링",
            "📋 네이버 상가 화면 복사 텍스트 붙여넣기 (가장 확실 & 1초 완성! 추천)"
        ])

        with comm_tab_crawl_num:
            c_ccr_in, c_ccr_btn = st.columns([2.5, 1])
            with c_ccr_in:
                comm_input_article_val = st.text_input(
                    "네이버 부동산 상가 매물 번호 또는 URL",
                    placeholder="예: 2428591234 또는 https://fin.land.naver.com/articles/2428591234",
                    help="네이버 부동산 매물 번호(10자리 내외) 또는 브라우저 주소창 링크를 붙여넣으세요.",
                    key="comm_input_naver_article_no"
                )
            with c_ccr_btn:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                btn_do_comm_crawl = st.button("🚀 상가 1초 크롤링 시도", type="primary", use_container_width=True, key="btn_crawl_comm_naver")

            if btn_do_comm_crawl:
                if comm_input_article_val.strip():
                    with st.spinner("네이버 부동산 상가 매물 정보 실시간 조회 중..."):
                        is_ok, msg, c_data = crawl_naver_article(comm_input_article_val.strip())
                        if is_ok:
                            queue_state_update("apply_comm", data=c_data, success_msg=f"🎉 {msg} 상가 18대 점검항목과 썸네일에 즉시 자동 반영되었습니다.", target_tab="🏪 ④ 상가 중개대상물 표시 (임차·매매)")
                        else:
                            st.error(f"⚠️ {msg}")
                else:
                    st.warning("상가 매물 번호 또는 매물 링크 URL을 입력해주세요.")

        with comm_tab_crawl_txt:
            st.markdown("""
            <div style="font-size:13px; color:#2B6CB0; background:#EBF8FF; border:1px solid #BEE3F8; padding:8px 12px; border-radius:6px; margin-bottom:8px;">
                💡 <b>1초 자동완성 방법:</b> 네이버 부동산 상가 매물 화면에서 매물 상세 영역을 마우스로 드래그 복사(Ctrl+C)하여 아래에 붙여넣으세요! 네이버 차단 없이 100% 즉시 반영됩니다.
            </div>
            """, unsafe_allow_html=True)
            comm_clip_article_text = st.text_area(
                "네이버 부동산 상가 매물 상세 복사 텍스트",
                height=120,
                placeholder="예:\n괘법동 1층 상가 월세 3,000/180\n제1종근린생활시설 계약 125㎡ / 전용 82.64㎡, 1/5층, 남서향\n무권리, 주구조 철근콘크리트구조, 일반상업지역, 방화지구...",
                key="comm_input_naver_clip_text"
            )
            if st.button("⚡ 붙여넣은 상가 텍스트 0.1초 분석 & 상가 항목 즉시 적용", type="primary", use_container_width=True, key="btn_parse_comm_clip_text"):
                if comm_clip_article_text.strip():
                    parsed_clip = parse_naver_clipboard_text(comm_clip_article_text)
                    if parsed_clip:
                        queue_state_update("apply_comm", data=parsed_clip, success_msg=f"🎉 네이버 상가 매물 [{parsed_clip.get('main_title', '상가')}] 텍스트 분석 완료! 상가 18대 점검항목과 썸네일에 즉시 자동 반영되었습니다.", target_tab="🏪 ④ 상가 중개대상물 표시 (임차·매매)")
                    else:
                        st.warning("붙여넣은 텍스트에서 상가 매물 정보를 식별하지 못했습니다. 형식을 확인해주세요.")
                else:
                    st.warning("네이버 부동산 상가 매물 상세 텍스트를 먼저 붙여넣어 주세요.")

    # ----------------------------------------------------
    # 📄 상가 건축물대장 (일반 / 표제부 / 전유부) & 공적서류 자동 분석
    # ----------------------------------------------------
    with st.expander("📄 [원클릭 1초 자동완성] 상가 건축물대장 (표제부 / 전유부 / 일반건축물) & 토지이용계획 분석", expanded=True):
        st.markdown("""
        <div style="font-size:14px; color:#2D3748; margin-bottom:10px;">
            정부24, 세움터, 일사편리에서 발급받은 <b>건축물대장(일반/표제부/전유부)</b>, <b>토지대장</b>, <b>토지이용계획원</b> PDF 파일을 올리시면 
            <b>소재지, 전용/계약면적, 층수, 용도, 용도지역, 용도지구, 주구조, 준공일, 주차대수, 승강기</b>가 상가 점검항목에 1초 만에 자동 완성됩니다!<br/>
            <span style="color:#C53030; font-weight:700;">🏬 통상가·근린생활시설 건물의 경우 일반건축물대장 또는 총괄표제부를 올리시면 건물 전체 스펙이 완벽하게 추출됩니다.</span>
        </div>
        """, unsafe_allow_html=True)

        comm_tab_doc_smart, comm_tab_doc_split, comm_tab_doc_txt = st.tabs([
            "📁 스마트 다중/통합 PDF 업로드 (일반건축물 / 표제부+전유부 자동 병합)",
            "🏢 표제부 & 🚪 전유부 2단계 분리 업로드 (구분상가 전용)",
            "📋 서류 텍스트 직접 붙여넣기 (정부24 보안문서 100% 대응)"
        ])

        with comm_tab_doc_smart:
            uploaded_comm_docs = st.file_uploader(
                "건축물대장(일반/표제부/전유부) / 토지이용계획원 PDF 서류를 드래그하여 놓으세요 (복수 선택 지원)",
                type=["pdf"],
                accept_multiple_files=True,
                help="일반건축물대장, 표제부, 전유부 PDF를 선택하거나 드래그하시면 자동으로 각각 분석하여 하나의 완벽한 상가 점검표로 병합합니다.",
                key="comm_doc_multi_pdf_uploader_key"
            )
            if uploaded_comm_docs:
                upload_sig = "-".join([f"{f.name}_{f.size}" for f in uploaded_comm_docs])
                if st.session_state.get("last_comm_smart_upload_sig") != upload_sig:
                    try:
                        with st.spinner("상가 공적서류 정밀 분석 및 상가 18대 항목 자동 반영 중..."):
                            doc_parsed_result = None
                            doc_parsed_type = ""
                            if len(uploaded_comm_docs) == 1:
                                doc_parsed_type, doc_parsed_result, _ = parse_official_document(uploaded_comm_docs[0], uploaded_comm_docs[0].name)
                            else:
                                title_data = {}
                                exclusive_data = {}
                                other_data = {}
                                types_found = []

                                for u_file in uploaded_comm_docs:
                                    p_type, p_res, _ = parse_official_document(u_file, u_file.name)
                                    types_found.append(p_type)
                                    if "표제부" in p_type:
                                        title_data.update(p_res)
                                    elif "전유부" in p_type:
                                        exclusive_data.update(p_res)
                                    else:
                                        other_data.update(p_res)

                                if title_data and exclusive_data:
                                    doc_parsed_result = merge_building_registers(title_data, exclusive_data)
                                    doc_parsed_type = "집합건축물대장 (표제부 + 전유부 통합완료)"
                                elif title_data:
                                    doc_parsed_result = title_data
                                    doc_parsed_type = "집합건축물대장 (표제부)"
                                elif exclusive_data:
                                    doc_parsed_result = exclusive_data
                                    doc_parsed_type = "집합건축물대장 (전유부)"
                                else:
                                    doc_parsed_result = other_data
                                    doc_parsed_type = ", ".join(types_found)

                            st.session_state["last_comm_smart_upload_sig"] = upload_sig
                            if doc_parsed_result:
                                queue_state_update("apply_comm", data=doc_parsed_result, success_msg=f"🎉 [{doc_parsed_type}] 분석 완료! 상가 18대 점검항목과 썸네일에 1초 만에 즉시 반영되었습니다.", target_tab="🏪 ④ 상가 중개대상물 표시 (임차·매매)")
                            else:
                                st.error("⚠️ 업로드하신 PDF 서류에서 텍스트를 읽어오지 못했습니다. 정부24/세움터의 위변조 방지 보안 전자문서인 경우 세 번째 [📋 서류 텍스트 직접 붙여넣기] 탭에 복사해 넣어주세요!")
                    except Exception as e:
                        st.error(f"서류 분석 중 오류가 발생했습니다: {e}")

        with comm_tab_doc_split:
            col_csp_title, col_csp_excl = st.columns(2)
            with col_csp_title:
                st.markdown("""
                <div style="background:#EBF8FF; border:1px solid #90CDF4; border-radius:8px; padding:8px 12px; margin-bottom:8px;">
                    <b>🏢 1. 표제부 (총괄표제부 / 일반건축물대장)</b><br/>
                    <span style="font-size:12px; color:#4A5568;">소재지, 주구조, 용도지역, 층수, 주차, 승강기, 준공일</span>
                </div>
                """, unsafe_allow_html=True)
                up_c_title = st.file_uploader("표제부 PDF", type=["pdf"], key="comm_doc_title_pdf_key")
            with col_csp_excl:
                st.markdown("""
                <div style="background:#FEFCBF; border:1px solid #FAF089; border-radius:8px; padding:8px 12px; margin-bottom:8px;">
                    <b>🚪 2. 전유부 (구분점포 / 개별호실)</b><br/>
                    <span style="font-size:12px; color:#744210;">호실, 전용면적, 해당층, 전유부 용도</span>
                </div>
                """, unsafe_allow_html=True)
                up_c_excl = st.file_uploader("전유부 PDF", type=["pdf"], key="comm_doc_excl_pdf_key")

            if up_c_title or up_c_excl:
                split_sig = f"{getattr(up_c_title, 'name', '')}_{getattr(up_c_excl, 'name', '')}"
                if st.session_state.get("last_comm_split_upload_sig") != split_sig:
                    try:
                        with st.spinner("표제부 및 전유부 융합 분석 중..."):
                            t_data = {}
                            e_data = {}
                            if up_c_title:
                                _, t_data, _ = parse_official_document(up_c_title, up_c_title.name)
                            if up_c_excl:
                                _, e_data, _ = parse_official_document(up_c_excl, up_c_excl.name)

                            if t_data and e_data:
                                res_m = merge_building_registers(t_data, e_data)
                                queue_state_update("apply_comm", data=res_m, success_msg="🎉 표제부와 전유부 2개 서류가 완벽하게 결합되어 상가 항목에 적용되었습니다!", target_tab="🏪 ④ 상가 중개대상물 표시 (임차·매매)")
                            elif t_data:
                                queue_state_update("apply_comm", data=t_data, success_msg="🎉 표제부 분석 완료! 건물 기본 스펙이 상가 항목에 적용되었습니다.", target_tab="🏪 ④ 상가 중개대상물 표시 (임차·매매)")
                            elif e_data:
                                queue_state_update("apply_comm", data=e_data, success_msg="🎉 전유부 분석 완료! 개별 호실 면적이 상가 항목에 적용되었습니다.", target_tab="🏪 ④ 상가 중개대상물 표시 (임차·매매)")

                            st.session_state["last_comm_split_upload_sig"] = split_sig
                    except Exception as e:
                        st.error(f"분리 서류 분석 오류: {e}")

        with comm_tab_doc_txt:
            st.markdown("""
            <div style="font-size:13px; color:#2D3748; background:#FFF5F5; border:1px solid #FEB2B2; padding:10px 14px; border-radius:6px; margin-bottom:10px;">
                💡 <b>정부24 보안문서 해결책:</b> 전자증명서 PDF에 위변조방지 보안이 걸려있는 경우, 
                정부24 열람 화면에서 마우스로 표 전체를 드래그 복사(Ctrl+C)하여 아래에 붙여넣으세요!
            </div>
            """, unsafe_allow_html=True)

            comm_pasted_doc_text = st.text_area(
                "건축물대장 / 토지대장 / 토지이용계획원 복사 텍스트 붙여넣기",
                height=130,
                placeholder="예:\n[표제부]\n대지위치: 부산광역시 사상구 괘법동 560-1\n주구조: 철근콘크리트구조\n지역: 일반상업지역\n지구: 방화지구, 지구단위계획구역\n주용도: 제1종근린생활시설\n사용승인일: 2018.06.15...",
                key="comm_direct_pasted_doc_text"
            )
            if st.button("🚀 붙여넣은 공적서류 텍스트 0.1초 분석 & 상가 항목 즉시 적용", type="primary", use_container_width=True, key="btn_apply_comm_pasted_doc"):
                if comm_pasted_doc_text.strip():
                    doc_type, parsed_dict, _ = parse_single_or_multi_document([comm_pasted_doc_text])
                    if parsed_dict:
                        queue_state_update("apply_comm", data=parsed_dict, success_msg=f"🎉 [{doc_type}] 텍스트 분석 완료! 상가 18대 점검항목과 썸네일에 즉시 반영되었습니다.", target_tab="🏪 ④ 상가 중개대상물 표시 (임차·매매)")
                    else:
                        st.warning("붙여넣은 텍스트에서 상가 건축물대장 정보를 찾지 못했습니다.")
                else:
                    st.warning("공적서류 텍스트를 먼저 붙여넣어 주세요.")

    # 3. 좌우 분할 (입력 / 출력)
    col_cad_in, col_cad_out = st.columns([1.1, 1.2])

    with col_cad_in:
        st.markdown("### 📋 상가 필수 점검항목 입력 및 수정")

        # 01. 소재지
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <b>01. 소재지</b>
            <span class="spec-badge badge-red">동·리·지번 필수</span>
        </div>
        """, unsafe_allow_html=True)
        st.text_input("소재지 주소", key="comm_ad_location")

        # 02. 면적 (전용/계약)
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>02. 면적 (전용 / 계약)</b>
            <span class="spec-badge badge-orange">법정단위 ㎡ 표기 (평수 제외)</span>
        </div>
        """, unsafe_allow_html=True)
        car1, car2 = st.columns(2)
        with car1:
            st.text_input("전용면적 (㎡)", key="comm_ad_area_exclusive")
        with car2:
            st.text_input("계약/연면적 (㎡)", key="comm_ad_area_contract")

        area_calc_m2 = format_commercial_area_text(st.session_state.comm_ad_area_exclusive, st.session_state.comm_ad_area_contract)
        st.markdown(f"""
        <div style="background:#F1F3F5; padding:6px 12px; border-radius:6px; font-size:13px; color:#495057; margin-bottom:8px;">
            📐 <b>계산 결과:</b> {area_calc_m2}
        </div>
        """, unsafe_allow_html=True)

        # 03. 해당층 / 총층수
        st.markdown("<b>03. 해당층 / 총층수</b>", unsafe_allow_html=True)
        st.text_input("해당층 / 총층수", key="comm_ad_floor_info", placeholder="예: 1층 / 지상 5층 (지하 1층)")

        # 04. 화장실 구분 (상가 필수)
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>04. 화장실 구분</b>
            <span class="spec-badge badge-green">상가 특화</span>
        </div>
        """, unsafe_allow_html=True)
        restroom_opts = ["내부 남녀구분 화장실 완비", "내부 단독 화장실", "각 층별 남녀 분리 화장실 (외부 공용)", "외부 공용 화장실"]
        if st.session_state.comm_ad_restroom not in restroom_opts:
            restroom_opts.append(st.session_state.comm_ad_restroom)
        st.selectbox("화장실 구분", restroom_opts, key="comm_ad_restroom")

        # 05. 관리비 & 세부내역
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>05. 관리비 & 세부내역</b>
            <span class="spec-badge badge-red">월 10만원↑ 세부내역 필수</span>
        </div>
        """, unsafe_allow_html=True)
        cmf1, cmf2 = st.columns([1, 1.4])
        with cmf1:
            st.text_input("월 관리비", key="comm_ad_maintenance_fee", placeholder="예: 월 15만 원 또는 자체관리")
        with cmf2:
            st.text_input("세부내역", key="comm_ad_maintenance_detail", placeholder="예: 공용청소, 승강기유지비 등")

        # 06. 거래 형태 & 07. 거래 가격
        st.markdown("<b>06. 거래 형태 & 07. 가격</b>", unsafe_allow_html=True)
        cpr1, cpr2 = st.columns([1, 1.4])
        with cpr1:
            c_trades = ["월세", "전세", "매매"] if not is_comm_ad_sale else ["매매", "월세"]
            if st.session_state.comm_ad_trade_type not in c_trades:
                c_trades.append(st.session_state.comm_ad_trade_type)
            st.selectbox("거래 형태", c_trades, key="comm_ad_trade_type")
        with cpr2:
            st.text_input("거래 가격", key="comm_ad_price_text", placeholder="예: 보증금 3,000만 / 월 180만 또는 15억 원")

        # 08. [임차] 권리금 / [매매] 수익률 & 투자금 분석
        if not is_comm_ad_sale:
            st.markdown("""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
                <b>08. 권리금 유무</b>
                <span class="spec-badge badge-orange">임차 필수</span>
            </div>
            """, unsafe_allow_html=True)
            st.text_input("권리금 정보", key="comm_ad_premium_fee", placeholder="예: 무권리 (권리금 없음) 또는 시설권리금 협의")
        else:
            st.markdown("""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
                <b>08. 수익률 및 투자금 분석</b>
                <span class="spec-badge badge-gold">수익형 매매 핵심</span>
            </div>
            """, unsafe_allow_html=True)
            st.text_input("기임대차 현황 (보증금/월세)", key="comm_ad_deposit_rent_summary", placeholder="예: 보증금 8,000만 원 / 월 650만 원")
            cs_inv1, cs_inv2, cs_inv3 = st.columns(3)
            with cs_inv1:
                st.text_input("융자금(대출)", key="comm_ad_loan_amount", placeholder="예: 6억 원")
            with cs_inv2:
                st.text_input("실투자금", key="comm_ad_actual_investment", placeholder="예: 8억 2,000만 원")
            with cs_inv3:
                st.text_input("연간 수익률", key="comm_ad_yield_rate", placeholder="예: 확정 수익률 연 6.8%")

        # 09. 방향 (주출입구 기준)
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>09. 방향 (주된 출입구 기준)</b>
            <span class="spec-badge badge-green">출입구 기준</span>
        </div>
        """, unsafe_allow_html=True)
        st.text_input("방향", key="comm_ad_direction", placeholder="예: 남서향 (주된 출입구 기준)")

        # 10. 입점(입주)가능일 & 11. 총주차대수
        cmv1, cmv2 = st.columns(2)
        with cmv1:
            st.markdown("<b>10. 입점(입주)가능일</b>", unsafe_allow_html=True)
            st.text_input("입점가능일", key="comm_ad_move_in_date", placeholder="예: 즉시입점 협의가능")
        with cmv2:
            st.markdown("<b>11. 총주차대수</b>", unsafe_allow_html=True)
            st.text_input("총주차대수", key="comm_ad_parking", placeholder="예: 총 20대 (점포 1대 무료)")

        # 12. 현재 업종 & 추천 업종
        st.markdown("<b>12. 현재 및 추천 업종</b>", unsafe_allow_html=True)
        cus1, cus2 = st.columns(2)
        with cus1:
            st.text_input("현재 상태/업종", key="comm_ad_current_use", placeholder="예: 공실 또는 카페 성업중")
        with cus2:
            st.text_input("추천 업종", key="comm_ad_recommended_use", placeholder="예: 카페, 음식점, 베이커리 등")

        # 13. 건축물 법정 용도
        st.markdown("<b>13. 건축물 용도 (법정 주용도)</b>", unsafe_allow_html=True)
        st.text_input("건축물 용도", key="comm_ad_building_use", placeholder="예: 제1종 근린생활시설")

        # 14. 용도지역 & 용도지구 (신소장님 필수 항목)
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>14. 용도지역 및 용도지구</b>
            <span class="spec-badge badge-gold">인허가 핵심</span>
        </div>
        """, unsafe_allow_html=True)
        czn1, czn2 = st.columns(2)
        with czn1:
            st.text_input("용도지역", key="comm_ad_zone_region", placeholder="예: 일반상업지역, 준주거지역 등")
        with czn2:
            st.text_input("용도지구/구역", key="comm_ad_zone_district", placeholder="예: 방화지구, 지구단위계획구역")

        # 15. 주구조 (건축물 주구조)
        st.markdown("""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-top: 10px;">
            <b>15. 주구조 (건물 구조)</b>
            <span class="spec-badge badge-green">대장 표제부 기준</span>
        </div>
        """, unsafe_allow_html=True)
        st.text_input("주구조", key="comm_ad_structure", placeholder="예: 철근콘크리트구조, 일반철골구조 등")

        # 16. 사용승인일 (준공일) & 17. 주요 설비 및 시설
        cbu1, cbu2 = st.columns(2)
        with cbu1:
            st.markdown("<b>16. 사용승인일 (준공일)</b>", unsafe_allow_html=True)
            st.text_input("사용승인일", key="comm_ad_approval_date", placeholder="예: 2018년 06월 15일")
        with cbu2:
            st.markdown("<b>17. 주요 설비 및 시설</b>", unsafe_allow_html=True)
            st.text_input("시설 정보", key="comm_ad_facility_info", placeholder="예: 전기 15kW 승압, 도시가스, 승강기 완비")

        # 18. 중개사무소 정보
        st.markdown("<b>18. 중개사무소 정보</b>", unsafe_allow_html=True)
        st.checkbox("✅ 중개사무소 정보 포함하기", key="comm_ad_include_office_info")
        if st.session_state.comm_ad_include_office_info:
            cof1, cof2 = st.columns(2)
            with cof1:
                st.text_input("중개사무소 상호", key="comm_ad_office_name")
                st.text_input("대표자 성명", key="comm_ad_office_owner")
                st.text_input("사무소 연락처", key="comm_ad_office_phone")
            with cof2:
                st.text_input("등록번호", key="comm_ad_office_reg_no")
                st.text_input("소재지", key="comm_ad_office_address")

            cas1, cas2 = st.columns(2)
            with cas1:
                st.text_input("소공/담당자 성명", key="comm_ad_assistant_name")
            with cas2:
                st.text_input("담당자 직통 연락처", key="comm_ad_assistant_phone")

    with col_cad_out:
        st.markdown("### 📋 네이버 광고 상가 점검표 (대조용)")
        st.caption("네이버 부동산 상가 매물 등록창을 띄워두고 위에서부터 순서대로 보며 등록하세요.")

        current_comm_spec_data = {
            "comm_mode": "sale" if is_comm_ad_sale else "lease",
            "location": st.session_state.get("comm_ad_location", ""),
            "area_exclusive": st.session_state.get("comm_ad_area_exclusive", ""),
            "area_contract": st.session_state.get("comm_ad_area_contract", ""),
            "floor_info": st.session_state.get("comm_ad_floor_info", ""),
            "restroom": st.session_state.get("comm_ad_restroom", ""),
            "maintenance_fee": st.session_state.get("comm_ad_maintenance_fee", ""),
            "maintenance_detail": st.session_state.get("comm_ad_maintenance_detail", ""),
            "trade_type": st.session_state.get("comm_ad_trade_type", "월세" if not is_comm_ad_sale else "매매"),
            "price_text": st.session_state.get("comm_ad_price_text", ""),
            "premium_fee": st.session_state.get("comm_ad_premium_fee", ""),
            "deposit_rent_summary": st.session_state.get("comm_ad_deposit_rent_summary", ""),
            "loan_amount": st.session_state.get("comm_ad_loan_amount", ""),
            "actual_investment": st.session_state.get("comm_ad_actual_investment", ""),
            "yield_rate": st.session_state.get("comm_ad_yield_rate", ""),
            "direction": st.session_state.get("comm_ad_direction", ""),
            "move_in_date": st.session_state.get("comm_ad_move_in_date", ""),
            "parking": st.session_state.get("comm_ad_parking", ""),
            "current_use": st.session_state.get("comm_ad_current_use", ""),
            "recommended_use": st.session_state.get("comm_ad_recommended_use", ""),
            "building_use": st.session_state.get("comm_ad_building_use", ""),
            "zone_region": st.session_state.get("comm_ad_zone_region", "일반상업지역"),
            "zone_district": st.session_state.get("comm_ad_zone_district", ""),
            "structure": st.session_state.get("comm_ad_structure", "철근콘크리트구조"),
            "approval_date": st.session_state.get("comm_ad_approval_date", ""),
            "facility_info": st.session_state.get("comm_ad_facility_info", ""),
            "office_name": st.session_state.get("comm_ad_office_name", "참좋은공인중개사사무소"),
            "office_owner": st.session_state.get("comm_ad_office_owner", "신제환"),
            "office_reg_no": st.session_state.get("comm_ad_office_reg_no", "제 26530-2026-00009 호"),
            "office_address": st.session_state.get("comm_ad_office_address", "부산광역시 사상구 강선로 9, 1층"),
            "office_phone": st.session_state.get("comm_ad_office_phone", "010-9667-4201"),
            "include_office_info": st.session_state.get("comm_ad_include_office_info", True),
            "assistant_name": st.session_state.get("comm_ad_assistant_name", ""),
            "assistant_phone": st.session_state.get("comm_ad_assistant_phone", ""),
        }

        comm_items_list = get_commercial_spec_table_data(current_comm_spec_data)
        c_rows_html = []
        for it in comm_items_list:
            num_str = f"{it['num']:02d}"
            val_formatted = it['val'].replace('\n', '<br/>')
            row_markup = f'<div style="border-bottom:1px solid #E9ECEF; padding:11px 6px;"><div style="display:flex; justify-content:space-between; margin-bottom:4px;"><span style="font-size:14px; font-weight:700; color:#333D4B;"><span style="color:#DAA844;">[{num_str}]</span> {it["name"]}</span><span style="font-size:12px; color:#8B95A1;">{it["guide"]}</span></div><div style="font-size:15px; color:#191F28; font-weight:600; line-height:1.6; background:#F8F9FB; padding:8px 12px; border-radius:6px; margin-top:4px;">{val_formatted}</div></div>'
            c_rows_html.append(row_markup)

        full_comm_table_html = f'<div style="background:#FFFFFF; border:1.5px solid #CBD5E0; border-radius:12px; padding:14px 18px; box-shadow:0 2px 8px rgba(0,0,0,0.04); max-height:680px; overflow-y:auto;">{"".join(c_rows_html)}</div>'
        st.markdown(full_comm_table_html, unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)
        comm_guide_txt = generate_commercial_naver_ad_guide_text(current_comm_spec_data)
        st.text_area("📋 [네이버 부동산 광고 대조용] 상가 전체 텍스트 복사", value=comm_guide_txt, height=130)

        comm_clip_txt = generate_commercial_clipboard_text(current_comm_spec_data)
        st.text_area("💬 [카카오톡 / 블로그 본문용] 상가 일반 텍스트 복사", value=comm_clip_txt, height=110)

        comm_blog_html = generate_commercial_blog_html_table(current_comm_spec_data)
        st.text_area("📝 [네이버 블로그용] 스마트에디터 다크골드 HTML 표 서식", value=comm_blog_html, height=110)

        # 1080px 고화질 상가 카드 다운로드
        with st.expander("🖼️ [다운로드] 1080px 상가 중개대상물 표시 카드 저장하기", expanded=False):
            with st.spinner("상가 표시 카드 렌더링 중..."):
                comm_card_img = render_commercial_spec_table_image(current_comm_spec_data)
            comm_card_byte_arr = io.BytesIO()
            comm_card_img.save(comm_card_byte_arr, format="PNG", quality=95)
            comm_card_bytes = comm_card_byte_arr.getvalue()

            clean_comm_loc = re.sub(r'[^\w\s-]', '', (st.session_state.comm_ad_location.split(" ")[-1] if st.session_state.comm_ad_location else "상가매물")).strip()
            comm_card_filename = f"상가중개대상물표시_{clean_comm_loc}_{'매매' if is_comm_ad_sale else '임차'}.png"

            st.markdown(render_direct_download_button(comm_card_bytes, comm_card_filename, "💾 [원클릭 즉시 다운로드] 1080px 상가 표시 카드 저장", bg_color="#DAA844"), unsafe_allow_html=True)
            st.caption("스마트폰에서는 위 버튼을 누르시면 사진첩에 바로 다운로드 저장됩니다.")


# ====================================================
# [ 탭 2-4 ] 공장 / 창고 네이버 광고 & 중개대상물 표시 생성기
# ====================================================
def render_tab_factory_ad():
    st.markdown('''
    <div style="background-color: #F8F9FB; border-left: 4px solid #3182CE; padding: 12px 18px; border-radius: 6px; margin-bottom: 20px;">
        <span style="font-size: 15px; font-weight: 700; color: #1E2022;">
            🏭 공장 / 창고 인터넷 표시·광고 점검표 (16개 법정 항목)
        </span><br/>
        <span style="font-size: 13px; color: #6C757D;">
            공장용지, 층고, 호이스트, 전력(동력 kW), 진입도로 폭 등 공장/창고 실무에 특화된 법정 항목을 완벽 지원합니다.
        </span>
    </div>
    ''', unsafe_allow_html=True)

    # 상단 썸네일 데이터 실시간 동기화 배너
    col_fs1, col_fs2 = st.columns([3, 1])
    with col_fs1:
        st.markdown('''
        <div style="font-size:13.5px; color:#1A365D; background:#EBF8FF; border:1px solid #90CDF4; padding:8px 14px; border-radius:6px;">
            🔄 <b>공장 썸네일 데이터 연동:</b> 썸네일에서 수정한 공장명, 거래형태, 가격, 대지/연면적, 층고, 호이스트, 전력이 점검표에 자동 연동됩니다.
        </div>
        ''', unsafe_allow_html=True)
    with col_fs2:
        if st.button("🔄 공장 썸네일값 즉시 동기화", key="btn_sync_factory_ad", use_container_width=True):
            st.session_state.factory_ad_trade_type = st.session_state.factory_trade_type
            st.session_state.factory_ad_price_text = st.session_state.factory_price_text
            st.session_state.factory_ad_structure = st.session_state.factory_spec1
            st.session_state.factory_ad_hoist = st.session_state.factory_spec3
            st.session_state.factory_ad_move_in_date = st.session_state.factory_spec5
            if st.session_state.factory_main_title:
                st.session_state.factory_ad_location = f"부산광역시 사상구 ({st.session_state.factory_main_title})"
            st.success("공장 썸네일 데이터가 점검표에 동기화되었습니다!")
            st.rerun()

    # 좌우 분할 (입력 폼 / 실시간 미리보기)
    col_in, col_out = st.columns([1.1, 1.2])
    with col_in:
        st.markdown("### 📋 공장/창고 16대 점검항목 입력 및 수정")
        st.text_input("1. 소재지 (지번 포함)", key="factory_ad_location")
        c_fa1, c_fa2 = st.columns(2)
        with c_fa1:
            st.text_input("2-1. 대지면적 (㎡)", key="factory_ad_area_land")
        with c_fa2:
            st.text_input("2-2. 연면적 (㎡)", key="factory_ad_area_gross")
        st.text_input("3. 용도지역 / 지목", key="factory_ad_zoning")
        st.text_input("4. 건축물 용도", key="factory_ad_building_use")
        c_fh1, c_fh2 = st.columns(2)
        with c_fh1:
            st.text_input("5. 층고 / 처마고", key="factory_ad_height")
        with c_fh2:
            st.text_input("6. 호이스트 설비", key="factory_ad_hoist")
        c_fp1, c_fp2 = st.columns(2)
        with c_fp1:
            st.text_input("7. 동력 (전기 kW)", key="factory_ad_power")
        with c_fp2:
            st.text_input("8. 진입도로 폭 (m)", key="factory_ad_road")
        c_ft1, c_ft2 = st.columns(2)
        with c_ft1:
            st.selectbox("9. 거래 형태", ["매매", "월세", "임대", "급매"], key="factory_ad_trade_type")
        with c_ft2:
            st.text_input("10. 거래 금액", key="factory_ad_price_text")
        st.text_input("11. 관리비", key="factory_ad_maintenance_fee")
        st.text_input("12. 주차 대수 및 마당", key="factory_ad_parking")
        st.text_input("13. 입주 가능일", key="factory_ad_move_in_date")
        st.text_input("14. 사용승인일", key="factory_ad_approval_date")
        st.text_input("15. 주출입구 방향", key="factory_ad_direction")

        st.markdown("#### 🏢 중개사무소 정보")
        st.checkbox("중개사무소 정보 포함", value=True, key="factory_ad_include_office")
        c_fas1, c_fas2 = st.columns(2)
        with c_fas1:
            st.text_input("소속공인중개사(직원) 성명", key="factory_ad_as_name", placeholder="미입력 시 생략")
        with c_fas2:
            st.text_input("소속공인중개사 연락처", key="factory_ad_as_phone", placeholder="미입력 시 생략")

    with col_out:
        st.markdown("### 📊 실시간 공장 점검표 미리보기 & 복사")
        factory_dict = {
            "location": st.session_state.factory_ad_location,
            "area_land": st.session_state.factory_ad_area_land,
            "area_gross": st.session_state.factory_ad_area_gross,
            "zoning": st.session_state.factory_ad_zoning,
            "building_use": st.session_state.factory_ad_building_use,
            "height": st.session_state.factory_ad_height,
            "hoist": st.session_state.factory_ad_hoist,
            "power": st.session_state.factory_ad_power,
            "road": st.session_state.factory_ad_road,
            "trade_type": st.session_state.factory_ad_trade_type,
            "price_text": st.session_state.factory_ad_price_text,
            "maintenance_fee": st.session_state.factory_ad_maintenance_fee,
            "parking": st.session_state.factory_ad_parking,
            "move_in_date": st.session_state.factory_ad_move_in_date,
            "approval_date": st.session_state.factory_ad_approval_date,
            "direction": st.session_state.factory_ad_direction,
            "include_office_info": st.session_state.factory_ad_include_office,
            "office_name": st.session_state.get("ad_office_name", "참좋은공인중개사사무소"),
            "office_owner": st.session_state.get("ad_office_owner", "신제환"),
            "office_reg_no": st.session_state.get("ad_office_reg_no", "제 26530-2026-00009 호"),
            "office_address": st.session_state.get("ad_office_address", "부산광역시 사상구 강선로 9, 1층"),
            "office_phone": st.session_state.get("ad_office_phone", "010-9667-4201"),
            "assistant_name": st.session_state.factory_ad_as_name,
            "assistant_phone": st.session_state.factory_ad_as_phone
        }
        factory_items = get_factory_spec_table_data(factory_dict)
        factory_html = generate_blog_html_table(factory_dict, items=factory_items)
        factory_txt = generate_clipboard_text(factory_dict, items=factory_items)
        factory_guide = generate_naver_ad_guide_text(factory_dict, items=factory_items)

        tab_fov1, tab_fov2, tab_fov3, tab_fov4 = st.tabs([
            "📋 1. 스마트에디터 HTML 표 복사",
            "📄 2. 네이버광고 등록 체크리스트",
            "💬 3. 텍스트 복사 (카톡/본문)",
            "🖼️ 4. 고화질 카드 이미지 저장"
        ])

        with tab_fov1:
            st.markdown(factory_html, unsafe_allow_html=True)
            st.markdown(render_copy_button(factory_html, "📋 [원클릭 복사] 블로그 스마트에디터 표 서식 복사", "btn_copy_f_html"), unsafe_allow_html=True)

        with tab_fov2:
            st.text_area("네이버 광고 등록용", value=factory_guide, height=350, key="txt_f_guide")
            st.markdown(render_copy_button(factory_guide, "📄 [원클릭 복사] 네이버 등록 가이드 복사", "btn_copy_f_guide"), unsafe_allow_html=True)

        with tab_fov3:
            st.text_area("텍스트 양식", value=factory_txt, height=350, key="txt_f_clip")
            st.markdown(render_copy_button(factory_txt, "💬 [원클릭 복사] 일반 텍스트 복사", "btn_copy_f_txt"), unsafe_allow_html=True)

        with tab_fov4:
            with st.spinner("공장 점검표 카드 이미지 생성 중..."):
                f_card_img = render_spec_table_image(factory_dict, items=factory_items)
            st.image(f_card_img, caption="1080px 정방형 공장 중개대상물 표시 카드", use_container_width=True)
            f_card_io = io.BytesIO()
            f_card_img.save(f_card_io, format="PNG", quality=98)
            f_card_bytes = f_card_io.getvalue()
            f_card_name = f"중개대상물표시_공장_{st.session_state.factory_ad_trade_type}.png"
            st.download_button("📥 1080px 공장 표시 카드 파일 다운로드", data=f_card_bytes, file_name=f_card_name, mime="image/png", key="btn_f_card_down", use_container_width=True)
            st.markdown(render_direct_download_button(f_card_bytes, f_card_name, "💾 [즉시 다운로드] 공장 표시 카드 저장", "#1A202C"), unsafe_allow_html=True)


# ====================================================
# 🌟 최상위 3대 메인 메뉴 탭: 썸네일 / 창문부착용A4 / 중개대상물표시
# ====================================================
st.markdown("""
<style>
    /* ==================================================== */
    /* 🌟 최상위 메인 3대 메뉴 탭: 크기 3배 (38px), 간격 3배 (50px) */
    /* ==================================================== */
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > div[role="tablist"],
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > [data-baseweb="tab-list"] {
        gap: 50px !important;
        background-color: #F8FAFC !important;
        padding: 14px 24px !important;
        border-radius: 18px !important;
        margin-bottom: 28px !important;
        display: flex !important;
        align-items: center !important;
        border: 1.5px solid #E2E8F0 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04) !important;
    }

    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > div[role="tablist"] > div[role="tab"],
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > [data-baseweb="tab-list"] > [data-baseweb="tab"] {
        height: 76px !important;
        min-height: 76px !important;
        padding: 0 32px !important;
        border-radius: 14px !important;
        background-color: transparent !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border: 2px solid transparent !important;
        cursor: pointer !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > div[role="tablist"] > div[role="tab"] *,
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > div[role="tablist"] > div[role="tab"] p,
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > [data-baseweb="tab-list"] > [data-baseweb="tab"] * {
        font-size: 38px !important;
        font-weight: 800 !important;
        line-height: 1.3 !important;
        color: #475569 !important;
        letter-spacing: -0.5px !important;
    }

    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > div[role="tablist"] > div[role="tab"][aria-selected="true"],
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > [data-baseweb="tab-list"] > [data-baseweb="tab"][aria-selected="true"] {
        background-color: #FFFFFF !important;
        border: 2.5px solid #F48A26 !important;
        box-shadow: 0 6px 20px rgba(244, 138, 38, 0.18) !important;
    }

    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > div[role="tablist"] > div[role="tab"][aria-selected="true"] *,
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > div[role="tablist"] > div[role="tab"][aria-selected="true"] p,
    .block-container > div[data-testid="stVerticalBlock"] > div[data-testid="stTabs"] > div > [data-baseweb="tab-list"] > [data-baseweb="tab"][aria-selected="true"] * {
        color: #F48A26 !important;
        font-weight: 900 !important;
    }

    /* 📌 하위 서브 탭 (tab-panel 내부: 아파트/주택/상가/공장 등은 단정하고 깔끔한 17px) */
    div[data-testid="stTabPanel"] div[data-testid="stTabs"] div[role="tablist"],
    div[role="tabpanel"] div[data-testid="stTabs"] div[role="tablist"],
    [data-baseweb="tab-panel"] [data-baseweb="tab-list"] {
        gap: 12px !important;
        background-color: #EDF2F7 !important;
        padding: 8px 14px !important;
        border-radius: 12px !important;
        margin-bottom: 20px !important;
        border: 1px solid #E2E8F0 !important;
        box-shadow: none !important;
    }

    div[data-testid="stTabPanel"] div[data-testid="stTabs"] div[role="tablist"] div[role="tab"],
    div[role="tabpanel"] div[data-testid="stTabs"] div[role="tablist"] div[role="tab"],
    [data-baseweb="tab-panel"] [data-baseweb="tab"] {
        height: 48px !important;
        min-height: 48px !important;
        padding: 0 22px !important;
        border-radius: 9px !important;
        background-color: transparent !important;
        border: 1.5px solid transparent !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    div[data-testid="stTabPanel"] div[data-testid="stTabs"] div[role="tablist"] div[role="tab"] *,
    div[data-testid="stTabPanel"] div[data-testid="stTabs"] div[role="tablist"] div[role="tab"] p,
    [data-baseweb="tab-panel"] [data-baseweb="tab"] * {
        font-size: 17px !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;
        color: #4A5568 !important;
        letter-spacing: normal !important;
    }

    div[data-testid="stTabPanel"] div[data-testid="stTabs"] div[role="tablist"] div[role="tab"][aria-selected="true"],
    [data-baseweb="tab-panel"] [data-baseweb="tab"][aria-selected="true"] {
        background-color: #FFFFFF !important;
        border: 1.5px solid #F48A26 !important;
        box-shadow: 0 2px 8px rgba(244, 138, 38, 0.15) !important;
    }

    div[data-testid="stTabPanel"] div[data-testid="stTabs"] div[role="tablist"] div[role="tab"][aria-selected="true"] *,
    div[data-testid="stTabPanel"] div[data-testid="stTabs"] div[role="tablist"] div[role="tab"][aria-selected="true"] p,
    [data-baseweb="tab-panel"] [data-baseweb="tab"][aria-selected="true"] * {
        color: #F48A26 !important;
        font-weight: 800 !important;
    }

    /* 기본 밑줄/인디케이터 완전히 제거 */
    div[data-testid="stTabs"] .react-aria-SelectionIndicator,
    [data-baseweb="tab-highlight"],
    [data-baseweb="tab-border"] {
        display: none !important;
    }
    div[data-testid="stTabs"] div[role="tablist"]::after {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

tab_main_thumb, tab_main_poster, tab_main_ad = st.tabs(["🖼️ 썸네일", "🖨️ 창문부착용A4", "📋 중개대상물표시"])

with tab_main_thumb:
    thumb_sub_apt, thumb_sub_house, thumb_sub_comm, thumb_sub_factory = st.tabs([
        "🏢 아파트",
        "🏡 주택",
        "🏬 상가",
        "🏭 공장"
    ])
    with thumb_sub_apt:
        render_tab_apt_thumb()
    with thumb_sub_house:
        render_tab_house_thumb()
    with thumb_sub_comm:
        render_tab_comm_thumb()
    with thumb_sub_factory:
        render_tab_factory_thumb()

with tab_main_poster:
    poster_sub_apt, poster_sub_house, poster_sub_comm, poster_sub_factory = st.tabs([
        "🏢 아파트",
        "🏡 주택",
        "🏬 상가",
        "🏭 공장"
    ])
    with poster_sub_apt:
        render_tab_apt_poster()
    with poster_sub_house:
        render_tab_house_poster()
    with poster_sub_comm:
        render_tab_comm_poster()
    with poster_sub_factory:
        render_tab_factory_poster()

with tab_main_ad:
    # 썸네일 및 포스터 화면에서는 마스터 콘솔 안내문구가 노출되지 않고, 중개대상물표시 탭에서만 스마트 자동완성 콘솔이 제공됩니다.
    render_smart_autocomplete_console()
    
    ad_sub_apt, ad_sub_house, ad_sub_comm, ad_sub_factory = st.tabs([
        "🏢 아파트",
        "🏡 주택",
        "🏬 상가",
        "🏭 공장"
    ])
    with ad_sub_apt:
        render_tab_apt_ad()
    with ad_sub_house:
        render_tab_house_ad()
    with ad_sub_comm:
        render_tab_comm_ad()
    with ad_sub_factory:
        render_tab_factory_ad()
