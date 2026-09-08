from datetime import datetime

import pandas as pd
import streamlit as st

import logic


st.set_page_config(page_title="생산 대시보드", layout="wide")
st.title("📊 생산 대시보드")


@st.cache_data
def 파일읽기(파일):
    """업로드한 CSV 또는 Excel 파일을 읽습니다."""
    파일명 = 파일.name.lower()

    if 파일명.endswith(".csv"):
        return pd.read_csv(파일)

    return pd.read_excel(파일)


# ─────────────────────────────────────────────
# 1. 파일 업로드
# ─────────────────────────────────────────────
올린파일 = st.file_uploader(
    "생산 데이터 파일을 올려주세요",
    type=["xlsx", "csv"],
)

if 올린파일 is None:
    st.info("파일을 올리면 대시보드가 표시됩니다.")
    st.stop()


# ─────────────────────────────────────────────
# 2. 파일 읽기 → 열 확인 → 지표 추가
# ─────────────────────────────────────────────
try:
    df = 파일읽기(올린파일)
    logic.열확인(df)
except Exception as e:
    st.error(f"파일을 읽거나 확인하는 중 오류가 발생했습니다: {e}")
    st.stop()

df = logic.지표추가(df)


# ─────────────────────────────────────────────
# 3. 사이드바
# ─────────────────────────────────────────────
st.sidebar.header("⚙️ 대시보드 설정")

집계기준 = st.sidebar.selectbox(
    "집계 기준",
    ["라인", "제품", "날짜"],
    index=0,
)

전체라인 = df["라인"].dropna().unique().tolist()
선택라인 = st.sidebar.multiselect(
    "라인 필터",
    전체라인,
    default=전체라인,
)

불량기준 = st.sidebar.slider(
    "불량 기준(%)",
    min_value=1.0,
    max_value=5.0,
    value=3.0,
    step=0.1,
)

주의기준 = st.sidebar.slider(
    "주의 기준(%)",
    min_value=1.0,
    max_value=5.0,
    value=2.5,
    step=0.1,
)

if 주의기준 >= 불량기준:
    st.error("주의 기준은 불량 기준보다 작아야 합니다.")
    st.stop()


# ─────────────────────────────────────────────
# 4. 라인 필터 적용
# ─────────────────────────────────────────────
필터본 = df[df["라인"].isin(선택라인)].copy()

if 필터본.empty:
    st.warning("선택한 라인에 해당하는 데이터가 없습니다.")
    st.stop()


# ─────────────────────────────────────────────
# 5. 요약
# ─────────────────────────────────────────────
요약값 = logic.요약(필터본)

a, b, c, d = st.columns(4)
a.metric("데이터", f"{요약값['건수']}건")
b.metric("총 생산", f"{요약값['생산량']:,}개")
c.metric("총 불량", f"{요약값['불량수']:,}개")
d.metric("불량률", f"{요약값['불량률']}%")

st.divider()


# ─────────────────────────────────────────────
# 6. 집계 및 경고
# ─────────────────────────────────────────────
try:
    집계 = logic.집계하기(필터본, 집계기준)
except ValueError as e:
    st.error(str(e))
    st.stop()

기준초과 = 집계[집계["불량률"] > 불량기준]

if not 기준초과.empty:
    경고목록 = ", ".join(기준초과[집계기준].astype(str).tolist())
    st.warning(
        f"⚠️ 불량 기준 {불량기준:.1f}%를 초과한 항목: {경고목록}"
    )


# ─────────────────────────────────────────────
# 7. 판정
# ─────────────────────────────────────────────
판정본 = logic.판정하기(필터본, 불량기준, 주의기준)
판정요약값 = logic.판정요약(판정본)


# ─────────────────────────────────────────────
# 8. 탭
# ─────────────────────────────────────────────
탭1, 탭2, 탭3, 탭4 = st.tabs(
    ["📊 집계", "📈 추이", "🚦 판정", "📋 원본"]
)


with 탭1:
    st.subheader(f"{집계기준}별 집계")

    왼쪽, 오른쪽 = st.columns([1, 1])

    with 왼쪽:
        st.dataframe(
            집계,
            use_container_width=True,
            hide_index=True,
        )

    with 오른쪽:
        st.subheader("불량률")
        st.bar_chart(
            집계.set_index(집계기준)["불량률"]
        )


with 탭2:
    st.subheader("일자별 불량률 추이")

    if "날짜" not in 필터본.columns:
        st.info("날짜 열이 없어 추이 차트를 표시할 수 없습니다.")
    else:
        일자별 = logic.집계하기(필터본, "날짜")
        st.line_chart(
            일자별.set_index("날짜")["불량률"]
        )


with 탭3:
    st.subheader("판정 결과")

    p1, p2, p3 = st.columns(3)
    p1.metric("불량", f"{판정요약값['불량']}건")
    p2.metric("주의", f"{판정요약값['주의']}건")
    p3.metric("정상", f"{판정요약값['정상']}건")

    판정차트 = pd.DataFrame(
        {
            "판정": ["불량", "주의", "정상"],
            "건수": [
                판정요약값["불량"],
                판정요약값["주의"],
                판정요약값["정상"],
            ],
        }
    ).set_index("판정")

    st.subheader("판정별 건수")
    st.bar_chart(판정차트["건수"])

    불량행 = 판정본[판정본["판정"] == "불량"].copy()

    st.subheader("불량 판정 데이터")
    st.dataframe(
        불량행,
        use_container_width=True,
        hide_index=True,
    )

    오늘 = datetime.now().strftime("%Y%m%d")
    csv_data = 불량행.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        label="불량 데이터 CSV 다운로드",
        data=csv_data,
        file_name=f"불량데이터_{오늘}.csv",
        mime="text/csv",
    )


with 탭4:
    st.subheader("필터 적용 원본 데이터")
    st.dataframe(
        판정본,
        use_container_width=True,
        hide_index=True,
    )
