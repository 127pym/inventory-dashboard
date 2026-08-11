import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(layout="wide", page_title="물류 자동화 대시보드")

# 1. 초기 데이터 (실제 사용 시 엑셀/CSV로 교체 가능)
data = {
    "구분2": ["101", "102", "103", "스타 1호", "스타 2호", "스타 3호"],
    "입수(PLT)": [300, 210, 210, 2520, 960, 640],
    "평균사용량": [1531, 4472, 3184, 76, 245, 474],
    "기초재고": [13200, 17430, 19320, 160, 3640, 5760],
    "안전재고": [4592, 13415, 9551, 228, 736, 1421]
}
df = pd.DataFrame(data)

# 2. 사이드바: 최소 키인 입력 폼
st.sidebar.header("데이터 입력 (최소 키인)")
selected_item = st.sidebar.selectbox("품목 선택", df["구분2"].tolist())
daily_use = st.sidebar.number_input("당일 사용량", value=0)
daily_in = st.sidebar.number_input("당일 입고예정", value=0)

# 요일별 특수성 반영 (목요일 발주 시 주말 물량 자동 계산)
is_thursday = datetime.now().weekday() == 3 # 목요일이면 True
if is_thursday:
    st.sidebar.warning("⚠️ 목요일: 주말 통합 발주 모드 활성화")
    multiplier = 3 # 금, 토, 일 3일치 계산
else:
    multiplier = 1

# 3. 자동 계산 로직
def calculate_order(row):
    # 미발주 시 예상 잔여재고 = 기초재고 - (평균사용량 * 리드타임 * 멀티플라이어)
    # 여기서는 리드타임 3일 가정
    expected_stock = row["기초재고"] - (row["평균사용량"] * 3 * multiplier)
    needed = row["안전재고"] - expected_stock
    return max(0, needed / row["입수(PLT)"])

df["발주필요량(PLT)"] = df.apply(calculate_order, axis=1)

# 4. 메인 화면: 대시보드 표 출력
st.title("📦 물류 재고 및 발주 자동화 대시보드")
st.write(f"오늘 날짜: {datetime.now().strftime('%Y-%m-%d')}")

# 결과 표 꾸미기
st.subheader("🚀 당일 최적 발주 현황")
st.dataframe(
    df.style.format({"발주필요량(PLT)": "{:.1f}"})
      .background_gradient(subset=["발주필요량(PLT)"], cmap="YlOrRd"),
    use_container_width=True
)

st.info("💡 팁: 목요일에는 시스템이 자동으로 주말 3일 치 물량을 통합 계산합니다.")
