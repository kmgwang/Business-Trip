import io
import os
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

from PIL import Image, ImageDraw, ImageFont

# PDF 생성을 위한 ReportLab 모듈
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# 페이지 기본 설정
st.set_page_config(
    page_title="화천기공 해외출장비 자동 산정 및 정산 프로그램",
    page_icon="✈️",
    layout="wide"
)

# 출장비 기준 규정 테이블
RULES_TABLE = {
    ("갑", "임원(부사장이상)"): {"daily": 135, "hotel": -1, "curr": "USD"},
    ("갑", "임원"): {"daily": 90, "hotel": 130, "curr": "USD"},
    ("갑", "1급"): {"daily": 70, "hotel": 100, "curr": "USD"},
    ("갑", "2급"): {"daily": 65, "hotel": 95, "curr": "USD"},
    ("갑", "3급이하"): {"daily": 60, "hotel": 90, "curr": "USD"},

    ("을", "임원(부사장이상)"): {"daily": 130, "hotel": -1, "curr": "USD"},
    ("을", "임원"): {"daily": 85, "hotel": 125, "curr": "USD"},
    ("을", "1급"): {"daily": 65, "hotel": 95, "curr": "USD"},
    ("을", "2급"): {"daily": 60, "hotel": 90, "curr": "USD"},
    ("을", "3급이하"): {"daily": 55, "hotel": 85, "curr": "USD"},

    ("병", "임원(부사장이상)"): {"daily": 130, "hotel": -1, "curr": "USD"},
    ("병", "임원"): {"daily": 80, "hotel": 110, "curr": "USD"},
    ("병", "1급"): {"daily": 60, "hotel": 90, "curr": "USD"},
    ("병", "2급"): {"daily": 55, "hotel": 85, "curr": "USD"},
    ("병", "3급이하"): {"daily": 55, "hotel": 80, "curr": "USD"},

    ("특", "임원(부사장이상)"): {"daily": 23000, "hotel": -1, "curr": "JPY"},
    ("특", "임원"): {"daily": 11000, "hotel": 17000, "curr": "JPY"},
    ("특", "1급"): {"daily": 8000, "hotel": 12000, "curr": "JPY"},
    ("특", "2급"): {"daily": 7000, "hotel": 11000, "curr": "JPY"},
    ("특", "3급이하"): {"daily": 7000, "hotel": 10000, "curr": "JPY"},
}

POSITION_MAPPING = {
    "회장": "임원(부사장이상)", "명예회장": "임원(부사장이상)", "사장": "임원(부사장이상)", "부사장": "임원(부사장이상)",
    "전무": "임원", "상무": "임원", "이사": "임원", "이사대우": "임원",
    "부장": "1급", "차장": "1급",
    "과장": "2급", "대리": "2급",
    "계장": "3급이하", "사원": "3급이하", "1급 기능장": "3급이하", "2급 기능장": "3급이하"
}

DEPARTMENTS = [
    "임원", "경영지원본부", "경영지원실", "인사지원팀", "관리팀", 
    "재무전략실", "노동조합", "재무팀", "자금팀", "정보실", 
    "정보팀", "IBU", "성장전략실", "프로젝트팀", "구매전략본부", 
    "HTB 대만지사", "구매팀", "VI팀", "품질혁신본부", "QM팀", 
    "보전팀", "생산본부", "생산관리팀", "생산기술팀", "가공팀", 
    "F/S가공", "정밀가공", "가공지원", "UNIT팀", "UNIT준비", 
    "UNIT조립", "UNIT서비스", "생산1팀", "생산2팀", "서비스센터", 
    "서비스1팀", "서비스2팀", "서비스3팀", "서비스4팀", "기술개발연구소", 
    "MC개발팀", "TC개발팀", "5축개발팀", "UNIT개발팀", "제어개발팀", 
    "제어SW개발팀", "가공기술1팀", "가공기술2팀", "소재사업부문", "기타"
]

# 세션 스테이트 초기화
if "df_input" not in st.session_state:
    st.session_state.df_input = pd.DataFrame(columns=[
        "부서", "성명", "출장지", "지역구분", "직급", "직급구분",
        "출발일", "도착일", "숙박일수", "출장일수", "적용환율",
        "일당_KRW", "일당_지급처", "숙박비_KRW", "숙박비_지급처",
        "교통비_KRW", "교통비_지급처", "기타경비_KRW", "기타_지급처"
    ])

def get_region_by_location(loc):
    if not loc: return ""
    group_gap = [
        "영국", "독일", "프랑스", "이탈리아", "스페인", "스위스", "네덜란드", "벨기에", "오스트리아", "포르투갈", "스웨덴", "노르웨이", "덴마크", "핀란드", "아일랜드", "그리스",
        "미국", "캐나다", "멕시코", "브라질", "아르헨티나", "칠레", "콜롬비아", "페루",
        "UAE", "아랍에미리트", "사우디", "카타르", "이스라엘", "쿠웨이트", "오만", "바레인", "요르단", "레바논",
        "이집트", "남아공", "남아프리카공화국", "나이지리아", "케냐", "모로코", "알제리", "튜니지아", "에티오피아", "가나",
        "호주", "뉴질랜드", "피지", "파푸아뉴기니",
        "폴란드", "체코", "루마니아", "우크라이나", "헝가리", "슬로바키아", "불가리아", "크로아티아", "세르비아", "리투아니아", "라트비아", "에스토니아",
        "러시아", "싱가포르", "홍콩", "대만"
    ]
    group_eul = ["중국"]
    group_byeong = [
        "베트남", "태국", "말레이시아", "인도네시아", "필리핀", "미얀마", "캄보디아", "라오스", "브루나이",
        "인도", "파키스탄", "방글라데시", "스리랑카", "네팔", "부탄", "몰디브",
        "카자흐스탄", "우즈베키스탄", "투르크메니스탄", "키르기스스탄", "타지키스탄", "몽골"
    ]
    group_teuk = ["일본"]

    if any(k in loc for k in group_teuk):
        return "특"
    elif any(k in loc for k in group_eul):
        if not any(sub in loc for sub in ["홍콩", "대만"]):
            return "을"
        else:
            return "갑"
    elif any(k in loc for k in group_gap):
        return "갑"
    elif any(k in loc for k in group_byeong):
        return "병"
    return ""

def calculate_row_amounts(region, rank, start_date, end_date, flight_night, rate_val):
    d_start = pd.to_datetime(start_date)
    d_end = pd.to_datetime(end_date)
    days = (d_end - d_start).days + 1
    nights = max(0, days - 1)
    if flight_night:
        nights = max(0, nights - 1)

    if days <= 0 or not region or not rank:
        return 0, 0, days, nights

    rule = RULES_TABLE.get((region, rank), {"daily": 60, "hotel": 90, "curr": "USD"})
    daily_std = rule["daily"]
    hotel_std = rule["hotel"]

    actual_rate = (rate_val / 100.0) if region == "특" else rate_val

    total_daily_foreign = daily_std * days
    daily_krw = int((total_daily_foreign * actual_rate) // 1000) * 1000

    if hotel_std == -1:
        hotel_krw = 0
    else:
        total_hotel_foreign = hotel_std * nights
        hotel_krw = int((total_hotel_foreign * actual_rate) // 1000) * 1000

    return daily_krw, hotel_krw, days, nights

def calculate_expenses_df(df):
    results = []
    for _, row in df.iterrows():
        agency_pay = 0
        employee_pay = 0

        d_krw = float(row.get("일당_KRW", 0))
        d_pay = str(row.get("일당_지급처", "출장자"))
        h_krw = float(row.get("숙박비_KRW", 0))
        h_pay = str(row.get("숙박비_지급처", "출장자"))
        t_krw = float(row.get("교통비_KRW", 0))
        t_pay = str(row.get("교통비_지급처", "여행사"))
        e_krw = float(row.get("기타경비_KRW", 0))
        e_pay = str(row.get("기타_지급처", "여행사"))

        for amt, pay in [(d_krw, d_pay), (h_krw, h_pay), (t_krw, t_pay), (e_krw, e_pay)]:
            if "여행사" in pay:
                agency_pay += amt
            else:
                employee_pay += amt

        total_krw = agency_pay + employee_pay

        r_dict = row.to_dict()
        r_dict["출장기간"] = f"{int(row['숙박일수'])}박 {int(row['출장일수'])}일"
        r_dict["총출장비_KRW"] = total_krw
        r_dict["여행사지급액_KRW"] = agency_pay
        r_dict["출장자지급액_KRW"] = employee_pay
        results.append(r_dict)
    return pd.DataFrame(results)

# 메인 UI 레이아웃
st.title("✈️ 화천기공 해외출장비 자동 산정 및 정산 프로그램")
st.markdown("---")

# 상단 환율 설정 영역
col_r1, col_r2, col_r3 = st.columns([2, 1.5, 3.5])
with col_r1:
    main_rate = st.number_input("메인 적용 환율 (USD/JPY 기준)", value=1415.30, step=0.1, format="%.2f")
with col_r2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🌐 서울외국환중개 사이트", use_container_width=True):
        st.markdown('<meta http-equiv="refresh" content="0;url=http://www.smbs.biz/ExRate/TodayExRate.jsp">', unsafe_allow_html=True)
with col_r3:
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("※ 환율 변경 후 아래 '환율 일괄 적용' 버튼을 누르면 전체 데이터에 반영됩니다.")

if st.button("🔄 전체 데이터에 메인 환율 일괄 적용"):
    if not st.session_state.df_input.empty:
        for idx, row in st.session_state.df_input.iterrows():
            d_krw, h_krw, _, _ = calculate_row_amounts(
                row["지역구분"], row["직급구분"], row["출발일"], row["도착일"], False, main_rate
            )
            st.session_state.df_input.at[idx, "적용환율"] = main_rate
            st.session_state.df_input.at[idx, "일당_KRW"] = d_krw
            st.session_state.df_input.at[idx, "숙박비_KRW"] = h_krw
        st.success("모든 출장자의 환율 및 일당/숙박비가 재계산되었습니다.")
        st.rerun()

st.markdown("---")

# 출장자 정보 입력 폼
with st.expander("➕ 신규 출장자 정보 입력 및 추가", expanded=True):
    with st.form("traveler_form", clear_on_submit=True):
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            inp_dep = st.selectbox("부서", DEPARTMENTS)
            inp_name = st.text_input("성명")
        with f_col2:
            inp_loc = st.text_input("출장지 (예: 독일 프랑크푸르트)")
            auto_region = get_region_by_location(inp_loc)
            inp_region = st.selectbox("지역구분", ["", "갑", "을", "병", "특"], index=["", "갑", "을", "병", "특"].index(auto_region) if auto_region in ["", "갑", "을", "병", "특"] else 0)
        with f_col3:
            inp_position = st.selectbox("직급", [""] + list(POSITION_MAPPING.keys()))
            auto_rank = POSITION_MAPPING.get(inp_position, "")
            inp_rank = st.selectbox("직급구분 (자동)", ["", "3급이하", "2급", "1급", "임원", "임원(부사장이상)"], index=["", "3급이하", "2급", "1급", "임원", "임원(부사장이상)"].index(auto_rank) if auto_rank in ["", "3급이하", "2급", "1급", "임원", "임원(부사장이상)"] else 0)
        with f_col4:
            inp_start = st.date_input("출발일", datetime.today())
            inp_end = st.date_input("도착일", datetime.today() + timedelta(days=4))
            inp_flight_night = st.checkbox("기내 박 적용 (숙박 1박 차감)")

        st.markdown("#### 경비 산정 내역")
        c_col1, c_col2, c_col3, c_col4 = st.columns(4)
        with c_col1:
            init_d_krw, init_h_krw, _, _ = calculate_row_amounts(inp_region, inp_rank, inp_start, inp_end, inp_flight_night, main_rate)
            inp_daily_krw = st.number_input("일당 (KRW)", value=init_d_krw, step=1000)
            inp_daily_pay = st.selectbox("일당 지급처", ["출장자", "여행사"], index=0)
        with c_col2:
            inp_hotel_krw = st.number_input("숙박비 (KRW)", value=init_h_krw, step=1000)
            inp_hotel_pay = st.selectbox("숙박비 지급처", ["출장자", "여행사"], index=0)
        with c_col3:
            inp_air_krw = st.number_input("교통비/항공권 (KRW)", value=0, step=1000)
            inp_air_pay = st.selectbox("교통비 지급처", ["여행사", "출장자"], index=0)
        with c_col4:
            inp_etc_krw = st.number_input("기타 경비 (KRW)", value=0, step=1000)
            inp_etc_pay = st.selectbox("기타 지급처", ["여행사", "출장자"], index=0)

        submitted = st.form_submit_button("출장자 정보 반영 / 저장", use_container_width=True)
        if submitted:
            if not inp_name.strip():
                st.warning("성명을 입력해주세요.")
            elif not inp_region or not inp_rank:
                st.warning("지역구분과 직급을 올바르게 선택해주세요.")
            else:
                d_end = pd.to_datetime(inp_end)
                d_start = pd.to_datetime(inp_start)
                days = (d_end - d_start).days + 1
                nights = max(0, days - 1)
                if inp_flight_night:
                    nights = max(0, nights - 1)

                new_row = {
                    "부서": inp_dep, "성명": inp_name.strip(), "출장지": inp_loc.strip(),
                    "지역구분": inp_region, "직급": inp_position, "직급구분": inp_rank,
                    "출발일": inp_start.strftime("%Y-%m-%d"), "도착일": inp_end.strftime("%Y-%m-%d"),
                    "숙박일수": nights, "출장일수": days, "적용환율": main_rate,
                    "일당_KRW": inp_daily_krw, "일당_지급처": inp_daily_pay,
                    "숙박비_KRW": inp_hotel_krw, "숙박비_지급처": inp_hotel_pay,
                    "교통비_KRW": inp_air_krw, "교통비_지급처": inp_air_pay,
                    "기타경비_KRW": inp_etc_krw, "기타_지급처": inp_etc_pay
                }
                st.session_state.df_input = pd.concat([st.session_state.df_input, pd.DataFrame([new_row])], ignore_index=True)
                st.success(f"{inp_name.strip} 출장자 정보가 등록되었습니다.")
                st.rerun()

st.markdown("---")
st.subheader(f"📋 등록된 출장자 목록 (총 {len(st.session_state.df_input)}건)")

if not st.session_state.df_input.empty:
    # 데이터 편집 기능 제공
    edited_df = st.data_editor(st.session_state.df_input, num_rows="dynamic", use_container_width=True)
    st.session_state.df_input = edited_df

    st.markdown("---")
    st.subheader("📥 자금팀 연결용 이미지 및 PDF 보고서 생성")

    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        if st.button("🖼️ 자금팀 연결용 이미지(PNG) 생성", use_container_width=True):
            try:
                df_res = calculate_expenses_df(st.session_state.df_input)
                
                try:
                    font_title = ImageFont.truetype("malgun.ttf", 26)
                    font_bold = ImageFont.truetype("malgunbd.ttf", 15)
                    font_regular = ImageFont.truetype("malgun.ttf", 14)
                except:
                    font_title = font_bold = font_regular = ImageFont.load_default()

                cols = ["순번", "출장지", "부서", "출장자", "출발", "도착", "출장기간", "교통비", "출장비", "기타금액", "집계", "출장자 지급", "여행사", "총계", "지급요청일"]
                col_widths = [50, 110, 110, 110, 110, 110, 80, 110, 110, 100, 120, 120, 120, 120, 130]
                row_height = 36
                header_h1 = 30
                
                img_width = sum(col_widths) + 40
                img_height = 140 + header_h1 + row_height + (len(df_res) * row_height)
                
                img = Image.new("RGB", (img_width, img_height), color=(255, 255, 255))
                draw = ImageDraw.Draw(img)

                current_year = datetime.now().year
                draw.text((20, 20), f"{current_year}년 해외출장비 지급 내역", fill=(0, 0, 0), font=font_title)

                x_start = 20
                y_start = 80
                weekdays = ("월", "화", "수", "목", "금", "토", "일")

                x_hr_start = x_start + sum(col_widths[:7])
                x_hr_end = x_start + sum(col_widths[:11])
                draw.rectangle([x_hr_start, y_start, x_hr_end, y_start + header_h1], fill=(30, 78, 161), outline=(0, 0, 0))
                draw.text((x_hr_start + (x_hr_end - x_hr_start)/2 - 60, y_start + 5), "인사지원팀 확인", fill=(255, 255, 255), font=font_bold)

                x_fin_start = x_hr_end
                x_fin_end = x_start + sum(col_widths[:15])
                draw.rectangle([x_fin_start, y_start, x_fin_end, y_start + header_h1], fill=(245, 205, 170), outline=(0, 0, 0))
                draw.text((x_fin_start + (x_fin_end - x_fin_start)/2 - 40, y_start + 5), "자금팀 확인", fill=(0, 0, 0), font=font_bold)

                y_head = y_start + header_h1
                x_curr = x_start
                for idx, c_name in enumerate(cols):
                    w = col_widths[idx]
                    box = [x_curr, y_head, x_curr + w, y_head + row_height]
                    bg_color = (30, 78, 161) if 7 <= idx <= 10 else ((245, 205, 170) if 11 <= idx <= 15 else (230, 230, 230))
                    txt_color = (255, 255, 255) if 7 <= idx <= 10 else (0, 0, 0)
                    draw.rectangle(box, fill=bg_color, outline=(0, 0, 0))
                    
                    bbox = draw.textbbox((0, 0), c_name, font=font_bold)
                    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                    draw.text((x_curr + (w - tw) / 2, y_head + (row_height - th) / 2 - 2), c_name, fill=txt_color, font=font_bold)
                    x_curr += w

                y_data = y_head + row_height
                for row_i, r in df_res.iterrows():
                    try:
                        d_start_dt = datetime.strptime(str(r['출발일']), "%Y-%m-%d")
                        start_str = d_start_dt.strftime("%m월 %d일")
                        end_str = datetime.strptime(str(r['도착일']), "%Y-%m-%d").strftime("%m월 %d일")
                        pay_req_dt = d_start_dt - timedelta(days=1)
                        pay_req_str = f"{pay_req_dt.strftime('%m월 %d일')}({weekdays[pay_req_dt.weekday()]})"
                    except:
                        start_str, end_str, pay_req_str = str(r['출발일']), str(r['도착일']), str(r['출발일'])

                    days_num = str(r['출장기간']).split('일')[0].split('박')[-1].strip() + "일"
                    sub_total = r["교통비_KRW"] + r["숙박비_KRW"] + r["기타경비_KRW"] + r["일당_KRW"]

                    row_vals = [
                        str(row_i + 1), r["출장지"], r["부서"], r["성명"], start_str, end_str, days_num,
                        f"₩{int(r['교통비_KRW']):,}", f"₩{int(r['숙박비_KRW'] + r['일당_KRW']):,}", f"₩{int(r['기타경비_KRW']):,}",
                        f"₩{int(sub_total):,}", f"₩{int(r['출장자지급액_KRW']):,}", f"₩{int(r['여행사지급액_KRW']):,}",
                        f"₩{int(r['총출장비_KRW']):,}", pay_req_str
                    ]

                    x_curr = x_start
                    for idx, val in enumerate(row_vals):
                        w = col_widths[idx]
                        box = [x_curr, y_data, x_curr + w, y_data + row_height]
                        f_to_use = font_bold if idx in [14, 10, 13] else font_regular
                        bg_c = (220, 38, 38) if idx == 14 else (255, 255, 255)
                        t_c = (255, 255, 255) if idx == 14 else (0, 0, 0)
                        
                        draw.rectangle(box, fill=bg_c, outline=(0, 0, 0))
                        bbox = draw.textbbox((0, 0), str(val), font=f_to_use)
                        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                        draw.text((x_curr + (w - tw) / 2, y_data + (row_height - th) / 2 - 2), str(val), fill=t_c, font=f_to_use)
                        x_curr += w
                    y_data += row_height

                buf = io.BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)
                
                st.download_button(
                    label="💾 생성된 이미지 다운로드",
                    data=buf,
                    file_name=f"자금팀연결용_해외출장비_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    mime="image/png",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"이미지 생성 중 오류 발생: {str(e)}")

    with col_btn2:
        if st.button("📄 출장비 산정내역서 PDF 일괄 생성", use_container_width=True):
            try:
                try:
                    pdfmetrics.registerFont(TTFont("MalgunGothic", "malgun.ttf"))
                    pdfmetrics.registerFont(TTFont("MalgunGothicBold", "malgunbd.ttf"))
                    font_name = "MalgunGothic"
                    font_bold = "MalgunGothicBold"
                except:
                    font_name = "Helvetica"
                    font_bold = "Helvetica-Bold"

                df_res = calculate_expenses_df(st.session_state.df_input)
                
                # 첫 번째 사용자의 PDF 바이트 버퍼 생성 예시 (다중 사용자일 경우 압축 파일 제공 가능)
                for _, r in df_res.iterrows():
                    pdf_buf = io.BytesIO()
                    doc = SimpleDocTemplate(pdf_buf, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
                    elements = []

                    style_title = ParagraphStyle('TitleStyle', fontName=font_bold, fontSize=18, leading=22, alignment=1)
                    style_h2 = ParagraphStyle('H2Style', fontName=font_bold, fontSize=11, leading=14, textColor=colors.HexColor("#000000"))
                    style_center = ParagraphStyle('CenterStyle', fontName=font_name, fontSize=9, leading=12, alignment=1)
                    style_center_bold = ParagraphStyle('CenterBold', fontName=font_bold, fontSize=9, leading=12, alignment=1)
                    style_header_cell = ParagraphStyle('HeaderCell', fontName=font_bold, fontSize=9, leading=11, alignment=1, textColor=colors.black)

                    elements.append(Paragraph("해외출장비 산정 내역서", style_title))
                    elements.append(Spacer(1, 10))

                    rate_val = float(r['적용환율'])
                    rate_val_str = f"1 ¥ = {rate_val:,.2f} 원 (적용환율: {rate_val / 100.0:,.4f})" if str(r['지역구분']) == "특" else f"1 USD = {rate_val:,.2f} 원"

                    info_data = [
                        [Paragraph("소속", style_center_bold), Paragraph(str(r["부서"]), style_center), Paragraph("성명", style_center_bold), Paragraph(str(r["성명"]), style_center), Paragraph("직급", style_center_bold), Paragraph(str(r["직급"]), style_center)],
                        [Paragraph("출장지", style_center_bold), Paragraph(str(r["출장지"]), style_center), Paragraph("지역구분", style_center_bold), Paragraph(str(r["지역구분"]), style_center), Paragraph("직급구분", style_center_bold), Paragraph(str(r["직급구분"]), style_center)],
                        [Paragraph("출발일", style_center_bold), Paragraph(str(r["출발일"]), style_center), Paragraph("도착일", style_center_bold), Paragraph(str(r["도착일"]), style_center), Paragraph("출장기간", style_center_bold), Paragraph(str(r["출장기간"]), style_center)],
                        [Paragraph("적용환율", style_center_bold), Paragraph("", style_center), Paragraph("", style_center), Paragraph(rate_val_str, style_center), Paragraph("", style_center), Paragraph("", style_center)]
                    ]
                    info_table = Table(info_data, colWidths=[65, 110, 65, 110, 65, 125])
                    info_table.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#F1F5F9")),
                        ('BACKGROUND', (2,0), (2,-1), colors.HexColor("#F1F5F9")),
                        ('BACKGROUND', (4,0), (4,-1), colors.HexColor("#F1F5F9")),
                        ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor("#FEF08A")),
                        ('SPAN', (0, 3), (2, 3)), ('SPAN', (3, 3), (5, 3)),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#94A3B8")),
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ]))
                    elements.append(info_table)
                    elements.append(Spacer(1, 12))

                    doc.build(elements)
                    pdf_buf.seek(0)

                    st.download_button(
                        label=f"📄 [{r['성명']}] 산정내역서 PDF 다운로드",
                        data=pdf_buf,
                        file_name=f"해외출장비_산정내역서_{r['성명']}.pdf",
                        mime="application/pdf"
                    )
            except Exception as e:
                st.error(f"PDF 생성 중 오류 발생: {str(e)}")
else:
    st.info("등록된 출장자 데이터가 없습니다. 상단에서 출장자 정보를 추가해주세요.")

