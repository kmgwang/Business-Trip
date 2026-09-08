"""화면과 상관없이 일만 하는 코드 — streamlit을 전혀 모릅니다."""
import pandas as pd

필수열 = ["라인", "생산량", "불량수"]


def 열확인(df):
    """필수 열이 있는지 확인. 없으면 ValueError."""
    없음 = [c for c in 필수열 if c not in df.columns]

    if 없음:
        raise ValueError(f"필요한 열이 없습니다: {', '.join(없음)}")

    return True


def 지표추가(df):
    """불량률·달성률 열을 붙인 복사본을 돌려준다."""
    d = df.copy()

    d["불량률"] = (
        d["불량수"] / d["생산량"] * 100
    ).round(2)

    if "계획수량" in d.columns:
        d["달성률"] = (
            d["생산량"] / d["계획수량"] * 100
        ).round(1)

    return d


def 집계하기(df, 기준열):
    """기준열로 묶어 건수·생산량·불량수·불량률을 구한다."""
    결과 = df.groupby(기준열).agg(
        건수=("생산량", "count"),
        생산량=("생산량", "sum"),
        불량수=("불량수", "sum")
    ).reset_index()

    결과["불량률"] = (
        결과["불량수"] / 결과["생산량"] * 100
    ).round(2)

    return 결과


def 요약(df):
    """화면 상단 큰 숫자용."""
    생산 = int(df["생산량"].sum())
    불량 = int(df["불량수"].sum())

    return {
        "건수": len(df),
        "생산량": 생산,
        "불량수": 불량,
        "불량률": round(불량 / 생산 * 100, 2)
        if 생산 else 0.0
    }


# -----------------------------
# 판정 기능
# -----------------------------

def 판정하기(df, 불량기준, 주의기준):
    """각 행의 불량률을 기준으로 판정한다."""
    d = df.copy()

    def 판정(불량률):
        if 불량률 > 불량기준:
            return "불량"
        elif 불량률 > 주의기준:
            return "주의"
        else:
            return "정상"

    d["판정"] = d["불량률"].apply(판정)

    return d


def 판정요약(df):
    """불량/주의/정상 건수를 계산한다."""
    return {
        "불량": int((df["판정"] == "불량").sum()),
        "주의": int((df["판정"] == "주의").sum()),
        "정상": int((df["판정"] == "정상").sum())
    }
