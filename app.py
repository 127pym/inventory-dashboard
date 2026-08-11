import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(layout="wide", page_title="물류 자동화 대시보드")

st.title("📦 물류 재고 및 발주 자동화 대시보드")

# 오늘 날짜 기준 날짜 세팅
today = datetime.now()
yesterday = today - timedelta(days=1)
recent_dates = [(yesterday - timedelta(days=i)).strftime('%m/%d') for i in range(9, -1, -1)]

# 향후 5일간의 입고 예정 스케줄 날짜 생성 (오늘부터 D+4)
future_dates = [(today + timedelta(days=i)).strftime('%m/%d') for i in range(5)]

st.write(f"오늘 날짜: {today.strftime('%Y-%m-%d')} (사용량 집계: {recent_dates[0]} ~ {recent_dates[-1]})")

# 품목 리스트 및 기본 입수 정보
items_list = [
    "101", "102", "103", 
    "스타 13호(양곡20kg)", "스타 1호", "스타 2호", 
    "스타 3호", "스타 4호", "스타 5호", 
    "스타 6호", "스타 7호", "스타 8호", "스타 11호"
]
plt_list = [300, 210, 210, 320, 2520, 960, 640, 640, 640, 320, 320, 320, 160]

# 1. 세션 상태 초기화 (최근 10일 사용량 키인 표)
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

# 2. 세션 상태 초기화 (향후 입고 예정 스케줄 표 - 신규 추가!)
if "schedule_df" not in st.session_state:
    sched_data = {"구분2": items_list}
    for f_date in future_dates:
        sched_data[f_date] = [0] * len(items_list)
    # 초기 예시 데이터 몇 개 부여
    sched_data[future_dates[0]][3] = 320  # 스타 13호 오늘 입고예정 예시
    st.session_state.schedule_df = pd.DataFrame(sched_data)

# 3. 세션 상태 초기화 (당일 재고 키인 표)
if "stock_input_df" not in st.session_state:
    st.session_state.stock_input_df = pd.DataFrame({
        "구분2": items_list,
        "현재고량": [13200, 17430, 19320, 160, 3760, 3640, 5760, 4160, 8320, 5280, 2240, 960, 320]
    })


# --- [구조 1] 최근 10일 사용량 키인 ---
st.subheader("📝 1. 최근 10일 사용량 키인")
st.info(f"어제({recent_dates[-1]})까지의 일자별 실적 입력")

col_config_10days = {"구분2": st.column_config.TextColumn("품목", disabled=True)}
for d_str in recent_dates:
    col_config_10days[d_str] = st.column_config.NumberColumn(d_str, format="%d")

edited_10days = st.data_editor(
    st.session_state.recent_10days_df,
    column_config=col_config_10days,
    hide_index=True,
    use_container_width=True,
    height=450
)
st.session_state.recent_10days_df = edited_10days

# 10일 치 데이터의 행별 평균 계산
days_columns = [col for col in edited_10days.columns if col != "구분2"]
calculated_avg = edited_10days[days_columns].mean(axis=1)


# --- [구조 신규] 3. 향후 입고 예정 스케줄 관리 ---
st.markdown("---")
st.subheader("📅 3. 향후 입고 예정 스케줄 관리 (날짜별 납품예정량 입력)")
st.info("날짜별로 잡혀있는 입고 예정 수량을 입력하세요. **오늘 및 리드타임 내에 들어오는 물량은 아래 당일 재고 표에 자동으로 합산**됩니다.")

col_config_sched = {"구분2": st.column_config.TextColumn("품목", disabled=True)}
for f_date in future_dates:
    col_config_sched[f_date] = st.column_config.NumberColumn(f"{f_date} 입고", format="%d")

edited_schedule = st.data_editor(
    st.session_state.schedule_df,
    column_config=col_config_sched,
    hide_index=True,
    use_container_width=True,
    height=450
)
st.session_state.schedule_df = edited_schedule

# [자동 계산 로직] 리드타임 내(예: 오늘 포함 향후 3일간) 들어올 납품예정량 자동 합산
# 필요에 따라 기간을 조절할 수 있습니다 (여기서는 첫 3일간의 입고량을 리드타임 유입량으로 산정)
lead_time_days_to_sum = future_dates[:3] # 오늘 포함 3일치
auto_incoming = edited_schedule[lead_time_days_to_sum].sum(axis=1)


# --- [구조 2] 당일 재고 키인 (납품예정량은 스케줄표에서 자동 연동됨) ---
st.markdown("---")
st.subheader("📝 2. 당일 재고 키인")
st.info("현재고를 키인하세요. '평균사용량'과 '납품예정량(위 스케줄 표에서 자동 연동)'이 함께 표시됩니다.")

combined_stock_df = pd.DataFrame({
    "구분2": items_list,
    "입수(PLT)": plt_list,
    "평균사용량": calculated_avg,  
    "현재고량": st.session_state.stock_input_df["현재고량"],
    "납품예정량(자동반영)": auto_incoming  # <-- 위 스케줄에서 계산된 값이 자동으로 쏙 들어감!
})

edited_stock = st.data_editor(
    combined_stock_df,
    column_config={
        "구분2": st.column_config.TextColumn("품목", disabled=True),
        "입수(PLT)": st.column_config.NumberColumn("입수(PLT)", disabled=True),
        "평균사용량": st.column_config.NumberColumn("평균사용량", format="%.1f", disabled=True),
        "현재고량": st.column_config.NumberColumn("현재고량 (키인)", format="%d"),
        "납품예정량(자동반영)": st.column_config.NumberColumn("납품예정량 (스케줄 연동)", format="%d", disabled=True),
    },
    hide_index=True,
    use_container_width=True,
    height=450
)

st.session_state.stock_input_df["현재고량"] = edited_stock["현재고량"]


# --- [구조 4] 최적 발주 필요량 ---
st.markdown("---")
st.subheader("🚀 4. 최적 발주 필요량")
st.info("💡 이 부분은 방금 연동된 데이터(평균사용량, 현재고, 리드타임 납품예정량)를 바탕으로 최종 발주량을 산출하는 로직을 채워 넣을 차례입니다.")
