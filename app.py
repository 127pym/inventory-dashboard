import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(layout="wide", page_title="물류 자동화 대시보드")

st.title("📦 물류 재고 및 발주 자동화 대시보드")

# 오늘 날짜 기준 '어제' 날짜 계산 및 최근 10일 날짜 리스트 생성
today = datetime.now()
yesterday = today - timedelta(days=1)
recent_dates = [(yesterday - timedelta(days=i)).strftime('%m/%d') for i in range(9, -1, -1)]

st.write(f"오늘 날짜: {today.strftime('%Y-%m-%d')} (집계 기준: {recent_dates[0]} ~ {recent_dates[-1]})} - **좌우 스크롤 방지를 위해 상하 배치로 전환되었습니다.**")

# 품목 리스트 및 기본 입수 정보
items_list = [
    "101", "102", "103", 
    "스타 13호(양곡20kg)", "스타 1호", "스타 2호", 
    "스타 3호", "스타 4호", "스타 5호", 
    "스타 6호", "스타 7호", "스타 8호", "스타 11호"
]
plt_list = [300, 210, 210, 320, 2520, 960, 640, 640, 640, 320, 320, 320, 160]

# 세션 상태 초기화 (최근 10일 사용량 키인 표)
if "recent_10days_df" not in st.session_state:
    initial_data = {"구분2": items_list}
    for d_str in recent_dates:
        initial_data[d_str] = [100] * len(items_list) 
    st.session_state.recent_10days_df = pd.DataFrame(initial_data)
else:
    current_cols = ["구분2"] + recent_dates
    if list(st.session_state.recent_10days_df.columns) != current_cols:
        new_df = pd.DataFrame({"구분2": items_list})
        for d_str in recent_dates:
            if d_str in st.session_state.recent_10days_df.columns:
                new_df[d_str] = st.session_state.recent_10days_df[d_str]
            else:
                new_df[d_str] = [100] * len(items_list)
        st.session_state.recent_10days_df = new_df

# 세션 상태 초기화 (당일 재고 키인 표)
if "stock_input_df" not in st.session_state:
    st.session_state.stock_input_df = pd.DataFrame({
        "구분2": items_list,
        "현재고량": [13200, 17430, 19320, 160, 3760, 3640, 5760, 4160, 8320, 5280, 2240, 960, 320],
        "납품예정량": [0, 0, 0, 320, 0, 0, 0, 3200, 1920, 1920, 0, 0, 0]
    })

# --- [구조 1] 최근 10일 사용량 키인 (상단 전체 폭 활용) ---
st.subheader("📝 1. 최근 10일 사용량 키인")
st.info(f"어제({recent_dates[-1]})까지의 일자별 실적 입력 (화면 폭에 맞춰 좌우 스크롤 없이 표시됩니다)")

col_config_10days = {"구분2": st.column_config.TextColumn("품목", disabled=True)}
for d_str in recent_dates:
    col_config_10days[d_str] = st.column_config.NumberColumn(d_str, format="%d")

edited_10days = st.data_editor(
    st.session_state.recent_10days_df,
    column_config=col_config_10days,
    hide_index=True,
    use_container_width=True,
    height=480
)
st.session_state.recent_10days_df = edited_10days

# 10일 치 데이터의 행별 평균 계산
days_columns = [col for col in edited_10days.columns if col != "구분2"]
calculated_avg = edited_10days[days_columns].mean(axis=1)

st.markdown("---")

# --- [구조 2] 당일 재고 키인 (하단 전체 폭 활용) ---
st.subheader("📝 2. 당일 재고 키인")
st.info("현재고/납품예정량 키인 + 위 1번에서 계산된 평균사용량 열 자동 연동")

combined_stock_df = pd.DataFrame({
    "구분2": items_list,
    "입수(PLT)": plt_list,
    "평균사용량": calculated_avg,  
    "현재고량": st.session_state.stock_input_df["현재고량"],
    "납품예정량": st.session_state.stock_input_df["납품예정량"]
})

edited_stock = st.data_editor(
    combined_stock_df,
    column_config={
        "구분2": st.column_config.TextColumn("품목", disabled=True),
        "입수(PLT)": st.column_config.NumberColumn("입수(PLT)", disabled=True),
        "평균사용량": st.column_config.NumberColumn("평균사용량", format="%.1f", disabled=True),
        "현재고량": st.column_config.NumberColumn("현재고량", format="%d"),
        "납품예정량": st.column_config.NumberColumn("납품예정량", format="%d"),
    },
    hide_index=True,
    use_container_width=True,
    height=480
)

st.session_state.stock_input_df["현재고량"] = edited_stock["현재고량"]
st.session_state.stock_input_df["납품예정량"] = edited_stock["납품예정량"]

# --- [구조 3] 최적 발주 필요량 ---
st.markdown("---")
st.subheader("🚀 3. 최적 발주 필요량")
st.info("💡 이 부분은 추후 로직을 함께 고민하면서 구현해 나갈 수 있도록 비워두었습니다.")
