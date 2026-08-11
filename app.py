import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import math

st.set_page_config(layout="wide", page_title="물류 자동화 대시보드")

st.title("📦 물류 재고 및 발주 자동화 대시보드")

today = datetime.now()
yesterday = today - timedelta(days=1)
recent_dates = [(yesterday - timedelta(days=i)).strftime('%m/%d') for i in range(9, -1, -1)]

# 스케줄 표의 날짜를 YYYY-MM-DD와 MM/D 형태로 모두 대응할 수 있도록 넉넉히 생성
future_dates_obj = [today + timedelta(days=i) for i in range(7)]
future_dates_md = [d.strftime('%m/%d') for d in future_dates_obj]

st.write(f"오늘 날짜: {today.strftime('%Y-%m-%d')} (사용량 기본 집계: {recent_dates[0]} ~ {recent_dates[-1]})")

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

# 2. 세션 상태 초기화 (향후 확정 입고 예정 스케줄 표 - MM/D 기준으로 깔끔하게 고정)
if "schedule_df" not in st.session_state:
    sched_data = {"구분2": items_list}
    for f_date in future_dates_md:
        sched_data[f_date] = [0] * len(items_list)
    st.session_state.schedule_df = pd.DataFrame(sched_data)

# 3. 세션 상태 초기화 (당일 재고 키인 표)
if "stock_input_df" not in st.session_state:
    st.session_state.stock_input_df = pd.DataFrame({
        "구분2": items_list,
        "현재고량": [13200, 17430, 19320, 160, 3760, 3640, 5760, 4160, 8320, 5280, 2240, 960, 320]
    })


# --- [납품 예정일 설정] ---
st.markdown("---")
st.subheader("🎯 납품(도착) 예정일 설정")
with st.form("date_form"):
    col_d1, col_d2 = st.columns([1, 3])
    with col_d1:
        target_delivery_date_str = st.text_input("납품 예정일 (YYYY-MM-DD)", value=today.strftime('%Y-%m-%d'))
    submitted = st.form_submit_button("📅 납품일 적용")

try:
    target_date = datetime.strptime(target_delivery_date_str.strip(), "%Y-%m-%d")
    target_date_str_md = target_date.strftime('%m/%d') # 스케줄 표 컬럼과 맞춤 (예: 08/11)
    days_diff = (target_date.date() - today.date()).days
    days_multiplier = max(1, days_diff)
except ValueError:
    target_date_str_md = ""
    days_multiplier = 3

st.info(f"💡 설정된 납품일: **{target_delivery_date_str}** (안전재고 배수: **X {days_multiplier}**)")


# --- [파트 1] 최근 10일 사용량 키인 ---
st.markdown("---")
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
    height=420,
    key="editor_10days"
)
st.session_state.recent_10days_df = edited_10days

days_columns = [col for col in edited_10days.columns if col != "구분2"]
calculated_avg = edited_10days[days_columns].mean(axis=1)


# --- [파트 2] 향후 확정 입고 예정 스케줄 관리 ---
st.markdown("---")
st.subheader("📅 2. 향후 확정 입고 예정 스케줄 관리")
st.info("이미 발주가 확정되어 입고될 날짜별 수량을 입력하세요.")

col_config_sched = {"구분2": st.column_config.TextColumn("품목", disabled=True)}
for f_date in future_dates_md:
    col_config_sched[f_date] = st.column_config.NumberColumn(f"{f_date} 입고", format="%d")

edited_schedule = st.data_editor(
    st.session_state.schedule_df,
    column_config=col_config_sched,
    hide_index=True,
    use_container_width=True,
    height=420,
    key="editor_schedule"
)
st.session_state.schedule_df = edited_schedule

# 스케줄 표에서 선택한 날짜에 해당하는 입고량 안전하게 추출 (None 방지)
if target_date_str_md in edited_schedule.columns:
    specific_incoming = edited_schedule[target_date_str_md].fillna(0)
else:
    specific_incoming = pd.Series([0] * len(items_list))


# --- [파트 3] 당일 재고 키인 ---
st.markdown("---")
st.subheader("📝 3. 당일 재고 키인")
st.info(f"현재고를 키인하세요. **'평균사용량'과 선택하신 납품일({target_delivery_date_str})의 '입고예정량'**이 함께 표시됩니다.")

combined_stock_df = pd.DataFrame({
    "구분2": items_list,
    "입수(PLT)": plt_list,
    "평균사용량": calculated_avg,  
    "현재고량": st.session_state.stock_input_df["현재고량"],
    "납품예정량(해당일)": specific_incoming  
})

edited_stock = st.data_editor(
    combined_stock_df,
    column_config={
        "구분2": st.column_config.TextColumn("품목", disabled=True),
        "입수(PLT)": st.column_config.NumberColumn("입수(PLT)", disabled=True),
        "평균사용량": st.column_config.NumberColumn("평균사용량", format="%.1f", disabled=True),
        "현재고량": st.column_config.NumberColumn("현재고량 (키인)", format="%d"),
        "납품예정량(해당일)": st.column_config.NumberColumn("해당일 납품예정", format="%d", disabled=True),
    },
    hide_index=True,
    use_container_width=True,
    height=420,
    key="editor_stock"
)

st.session_state.stock_input_df["현재고량"] = edited_stock["현재고량"]


# --- [파트 4] 최적 발주 필요량 계산 및 결과 출력 ---
st.markdown("---")
st.subheader("🚀 4. 당일 최적 발주 필요량 결과")

def calculate_order(row):
    avg_use = float(row["평균사용량"]) if pd.notnull(row["평균사용량"]) else 0.0
    curr_stock = float(row["현재고량"]) if pd.notnull(row["현재고량"]) else 0.0
    incoming = float(row["납품예정량(해당일)"]) if pd.notnull(row["납품예정량(해당일)"]) else 0.0
    plt_unit = float(row["입수(PLT)"]) if pd.notnull(row["입수(PLT)"]) and float(row["입수(PLT)"]) > 0 else 1.0

    safety_stock = avg_use * days_multiplier
    base_stock = curr_stock + incoming
    expected_stock = base_stock - (avg_use * days_multiplier)
    needed_qty = safety_stock - expected_stock
    
    if needed_qty <= 0:
        return 0.0
    else:
        return float(math.ceil(needed_qty / plt_unit))

result_df = edited_stock.copy()
safety_col_name = f"안전재고(사용량 x {days_multiplier})"
result_df[safety_col_name] = result_df["평균사용량"] * days_multiplier
result_df["발주필요량(PLT)"] = result_df.apply(calculate_order, axis=1)

st.dataframe(
    result_df[["구분2", "입수(PLT)", "평균사용량", "현재고량", "납품예정량(해당일)", safety_col_name, "발주필요량(PLT)"]],
    column_config={
        "구분2": st.column_config.TextColumn("품목", disabled=True),
        "입수(PLT)": st.column_config.NumberColumn("입수(PLT)", format="%d", disabled=True),
        "평균사용량": st.column_config.NumberColumn("평균사용량", format="%.1f", disabled=True),
        "현재고량": st.column_config.NumberColumn("현재고량", format="%d", disabled=True),
        "납품예정량(해당일)": st.column_config.NumberColumn("해당일 납품예정", format="%d", disabled=True),
        safety_col_name: st.column_config.NumberColumn("안전재고", format="%.1f", disabled=True),
        "발주필요량(PLT)": st.column_config.NumberColumn("발주필요량(PLT)", format="%.1f", disabled=True),
    },
    hide_index=True,
    use_container_width=True
)
