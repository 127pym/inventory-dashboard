import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import math

st.set_page_config(layout="wide", page_title="물류 자동화 대시보드")

st.title("📦 물류 재고 및 발주 자동화 대시보드")

# 오늘 날짜 기준 세팅
today = datetime.now()
yesterday = today - timedelta(days=1)
recent_dates = [(yesterday - timedelta(days=i)).strftime('%m/%d') for i in range(9, -1, -1)]
future_dates = [(today + timedelta(days=i)).strftime('%m/%d') for i in range(5)]

st.write(f"오늘 날짜: {today.strftime('%Y-%m-%d')} (사용량 집계: {recent_dates[0]} ~ {recent_dates[-1]})")

# 요일별 특수성 반영 (목요일 발주 시 주말 물량 3일치 통합 계산)
is_thursday = today.weekday() == 3 
if is_thursday:
    st.warning("⚠️ 목요일 감지: 주말 통합 발주 모드 활성화 (3일치 소모량 반영)")
    multiplier = 3 
else:
    multiplier = 1

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

# 2. 세션 상태 초기화 (향후 확정 입고 스케줄 표)
if "schedule_df" not in st.session_state:
    sched_data = {"구분2": items_list}
    for f_date in future_dates:
        sched_data[f_date] = [0] * len(items_list)
    st.session_state.schedule_df = pd.DataFrame(sched_data)

# 3. 세션 상태 초기화 (당일 재고 키인 표)
if "stock_input_df" not in st.session_state:
    st.session_state.stock_input_df = pd.DataFrame({
        "구분2": items_list,
        "현재고량": [13200, 17430, 19320, 160, 3760, 3640, 5760, 4160, 8320, 5280, 2240, 960, 320]
    })


# --- [파트 1] 최근 10일 사용량 키인 ---
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
    height=420
)
st.session_state.recent_10days_df = edited_10days

# 10일 치 데이터의 행별 평균 계산
days_columns = [col for col in edited_10days.columns if col != "구분2"]
calculated_avg = edited_10days[days_columns].mean(axis=1)


# --- [파트 2] 향후 확정 입고 예정 스케줄 관리 ---
st.markdown("---")
st.subheader("📅 2. 향후 확정 입고 예정 스케줄 관리")
st.info("이미 발주가 확정되어 입고될 날짜별 수량을 입력하세요. **리드타임 내(오늘 포함 향후 3일) 입고량은 아래 당일 재고 표에 자동 합산**됩니다.")

col_config_sched = {"구분2": st.column_config.TextColumn("품목", disabled=True)}
for f_date in future_dates:
    col_config_sched[f_date] = st.column_config.NumberColumn(f"{f_date} 입고", format="%d")

edited_schedule = st.data_editor(
    st.session_state.schedule_df,
    column_config=col_config_sched,
    hide_index=True,
    use_container_width=True,
    height=420
)
st.session_state.schedule_df = edited_schedule

# 리드타임 내(오늘 포함 향후 3일간) 확정 입고 예정량 자동 합산
lead_time_days_to_sum = future_dates[:3] 
auto_incoming = edited_schedule[lead_time_days_to_sum].sum(axis=1)


# --- [파트 3] 당일 재고 키인 (평균 및 입고예정 자동 연동) ---
st.markdown("---")
st.subheader("📝 3. 당일 재고 키인")
st.info("현재고를 키인하세요. **'평균사용량'과 '납품예정량(확정 스케줄 자동 연동)'**이 함께 표시됩니다.")

combined_stock_df = pd.DataFrame({
    "구분2": items_list,
    "입수(PLT)": plt_list,
    "평균사용량": calculated_avg,  
    "현재고량": st.session_state.stock_input_df["현재고량"],
    "납품예정량(확정연동)": auto_incoming  
})

edited_stock = st.data_editor(
    combined_stock_df,
    column_config={
        "구분2": st.column_config.TextColumn("품목", disabled=True),
        "입수(PLT)": st.column_config.NumberColumn("입수(PLT)", disabled=True),
        "평균사용량": st.column_config.NumberColumn("평균사용량", format="%.1f", disabled=True),
        "현재고량": st.column_config.NumberColumn("현재고량 (키인)", format="%d"),
        "납품예정량(확정연동)": st.column_config.NumberColumn("납품예정량 (스케줄 연동)", format="%d", disabled=True),
    },
    hide_index=True,
    use_container_width=True,
    height=420
)

st.session_state.stock_input_df["현재고량"] = edited_stock["현재고량"]


# --- [파트 4] 최적 발주 필요량 계산 및 결과 출력 ---
st.markdown("---")
st.subheader("🚀 4. 당일 최적 발주 필요량 결과")

def calculate_order(row):
    safety_stock = row["평균사용량"] * 3
    base_stock = row["현재고량"] + row["납품예정량(확정연동)"]
    expected_stock = base_stock - (row["평균사용량"] * 3 * multiplier)
    needed_qty = safety_stock - expected_stock
    
    if needed_qty <= 0:
        return 0.0
    else:
        plt_unit = row["입수(PLT)"]
        pallets = math.ceil(needed_qty / plt_unit)
        return float(pallets)

result_df = edited_stock.copy()
result_df["안전재고(사용량x3)"] = result_df["평균사용량"] * 3
result_df["발주필요량(PLT)"] = result_df.apply(calculate_order, axis=1)

# 에러를 일으키는 .background_gradient 부분을 제거하고 깔끔한 포맷팅만 적용
st.dataframe(
    result_df[["구분2", "입수(PLT)", "평균사용량", "현재고량", "납품예정량(확정연동)", "안전재고(사용량x3)", "발주필요량(PLT)"]],
    column_config={
        "구분2": st.column_config.TextColumn("품목", disabled=True),
        "입수(PLT)": st.column_config.NumberColumn("입수(PLT)", format="%d", disabled=True),
        "평균사용량": st.column_config.NumberColumn("평균사용량", format="%.1f", disabled=True),
        "현재고량": st.column_config.NumberColumn("현재고량", format="%d", disabled=True),
        "납품예정량(확정연동)": st.column_config.NumberColumn("납품예정량", format="%d", disabled=True),
        "안전재고(사용량x3)": st.column_config.NumberColumn("안전재고", format="%.1f", disabled=True),
        "발주필요량(PLT)": st.column_config.NumberColumn("발주필요량(PLT)", format="%.1f", disabled=True),
    },
    hide_index=True,
    use_container_width=True
)
