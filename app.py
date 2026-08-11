import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import math
import os

st.set_page_config(layout="wide", page_title="물류 자동화 대시보드")

st.title("📦 물류 재고 및 발주 자동화 대시보드")

SAVE_FILE = "inventory_data.json"

# 1. 오늘 날짜 기준으로 날짜 리스트 자동 갱신 설정
today = datetime.now()
yesterday = today - timedelta(days=1)
recent_dates = [(yesterday - timedelta(days=i)).strftime('%m/%d') for i in range(9, -1, -1)]

future_dates_obj = [today + timedelta(days=i) for i in range(7)]
future_dates_md = [d.strftime('%m/%d') for d in future_dates_obj]

st.write(f"오늘 날짜: {today.strftime('%Y-%m-%d')} (사용량 자동 집계: {recent_dates[0]} ~ {recent_dates[-1]})")

# 품목 리스트 및 기본 입수 정보 (입수 = 1 PLT 당 박스 수)
items_list = [
    "101", "102", "103", 
    "스타 13호(양곡20kg)", "스타 1호", "스타 2호", 
    "스타 3호", "스타 4호", "스타 5호", 
    "스타 6호", "스타 7호", "스타 8호", "스타 11호"
]
plt_list = [300, 210, 210, 320, 2520, 960, 640, 640, 640, 320, 320, 320, 160]

# --- [데이터 영구 저장 및 불러오기 기능] ---
if os.path.exists(SAVE_FILE) and "loaded" not in st.session_state:
    try:
        loaded_df = pd.read_json(SAVE_FILE)
        loaded_dict = loaded_df.iloc[0].to_dict()
        st.session_state.recent_10days_df = pd.DataFrame(loaded_dict["recent_10days"])
        st.session_state.schedule_df = pd.DataFrame(loaded_dict["schedule"])
        st.session_state.stock_input_df = pd.DataFrame(loaded_dict["stock_input"])
        st.session_state.loaded = True
    except Exception as e:
        pass


# --- [세션 상태 유지 및 데이터 동기화 로직] ---

if "recent_10days_df" not in st.session_state:
    initial_data = {"구분2": items_list}
    for d_str in recent_dates:
        initial_data[d_str] = [0] * len(items_list) 
    st.session_state.recent_10days_df = pd.DataFrame(initial_data)
else:
    df_old = st.session_state.recent_10days_df
    new_df = pd.DataFrame({"구분2": items_list})
    for d_str in recent_dates:
        if d_str in df_old.columns:
            new_df[d_str] = df_old[d_str]
        else:
            new_df[d_str] = [0] * len(items_list)
    st.session_state.recent_10days_df = new_df

if "schedule_df" not in st.session_state:
    sched_data = {"구분2": items_list}
    for f_date in future_dates_md:
        sched_data[f_date] = [0] * len(items_list)
    st.session_state.schedule_df = pd.DataFrame(sched_data)
else:
    df_sched_old = st.session_state.schedule_df
    new_sched_df = pd.DataFrame({"구분2": items_list})
    for f_date in future_dates_md:
        if f_date in df_sched_old.columns:
            new_sched_df[f_date] = df_sched_old[f_date]
        else:
            new_sched_df[f_date] = [0] * len(items_list)
    st.session_state.schedule_df = new_sched_df

if "stock_input_df" not in st.session_state:
    st.session_state.stock_input_df = pd.DataFrame({
        "구분2": items_list,
        "현재고량": [0] * len(items_list)
    })


# --- [납품 예정일 설정 및 저장 버튼 통합 배치] ---
st.markdown("---")
st.subheader("🎯 납품(도착) 예정일 설정 및 데이터 관리")

ctrl_col1, ctrl_col2 = st.columns([3, 1])

with ctrl_col1:
    with st.form("date_form"):
        target_delivery_date_str = st.text_input("납품 예정일 (YYYY-MM-DD)", value=today.strftime('%Y-%m-%d'))
        submitted = st.form_submit_button("📅 납품일 적용")

try:
    target_date = datetime.strptime(target_delivery_date_str.strip(), "%Y-%m-%d")
    days_diff = (target_date.date() - today.date()).days
    days_multiplier = max(1, days_diff)
except ValueError:
    days_multiplier = 3

with ctrl_col2:
    st.write("") 
    st.write("") 
    if st.button("💾 현재 입력 데이터 저장", use_container_width=True):
        if "recent_10days_df" in st.session_state and "schedule_df" in st.session_state and "stock_input_df" in st.session_state:
            save_dict = {
                "recent_10days": st.session_state.recent_10days_df.to_dict(),
                "schedule": st.session_state.schedule_df.to_dict(),
                "stock_input": st.session_state.stock_input_df.to_dict()
            }
            df_to_save = pd.DataFrame([save_dict])
            df_to_save.to_json(SAVE_FILE)
            st.success("✅ 저장 완료!")

st.info(f"💡 설정된 납품일: **{target_delivery_date_str}** (리드타임 배수: **X {days_multiplier}일**)")


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
st.session_state.recent_10days_df = edited_10days.fillna(0)

days_columns = [col for col in edited_10days.columns if col != "구분2"]
calculated_avg = edited_10days[days_columns].fillna(0).mean(axis=1)


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
st.session_state.schedule_df = edited_schedule.fillna(0)

today_str_md = today.strftime('%m/%d')
if today_str_md in edited_schedule.columns:
    today_incoming = edited_schedule[today_str_md].fillna(0).reset_index(drop=True)
else:
    today_incoming = pd.Series([0] * len(items_list))


# --- [파트 3] 당일 재고 키인 ---
st.markdown("---")
st.subheader("📝 3. 당일 재고 키인")
st.info(f"현재고를 키인하세요. **'평균사용량'과 '오늘({today.strftime('%m/%d')}) 당일 입고예정량'**이 함께 표시됩니다.")

combined_stock_df = pd.DataFrame({
    "구분2": items_list,
    "입수(BOX)": plt_list,  
    "평균사용량": calculated_avg.reset_index(drop=True),  
    "현재고량": st.session_state.stock_input_df["현재고량"].fillna(0).reset_index(drop=True),
    "당일입고예정량": today_incoming.reset_index(drop=True)
})

edited_stock = st.data_editor(
    combined_stock_df,
    column_config={
        "구분2": st.column_config.TextColumn("품목", disabled=True),
        "입수(BOX)": st.column_config.NumberColumn("입수(BOX)", format="%d", disabled=True),
        "평균사용량": st.column_config.NumberColumn("평균사용량", format="%.1f", disabled=True),
        "현재고량": st.column_config.NumberColumn("현재고량 (키인)", format="%d"),
        "당일입고예정량": st.column_config.NumberColumn("당일 입고예정", format="%d", disabled=True),
    },
    hide_index=True,
    use_container_width=True,
    height=420,
    key="editor_stock"
)

st.session_state.stock_input_df["현재고량"] = edited_stock["현재고량"].fillna(0)


# --- [파트 4] 최적 발주 필요량 계산 및 결과 출력 (소계 컬럼 반영) ---
st.markdown("---")
st.subheader("🚀 4. 당일 최적 발주 필요량 결과 (미발주 시 예상 잔여재고 및 소계 산정)")

def calculate_row_data(row):
    avg_use = float(row["평균사용량"]) if pd.notnull(row["평균사용량"]) else 0.0
    curr_stock = float(row["현재고량"]) if pd.notnull(row["현재고량"]) else 0.0
    incoming = float(row["당일입고예정량"]) if pd.notnull(row["당일입고예정량"]) else 0.0

    # 사진 속 예시 공식 반영: 소계(예상 잔여재고) = 현재고량 + 입고예정량 - (예상사용량 × 리드타임)
    expected_usage = avg_use * days_multiplier
    subtotal_stock = (curr_stock + incoming) - expected_usage
    
    # 안전재고는 예상사용량과 동일하거나 기준에 맞게 설정 (여기서는 평균사용량 * 리드타임)
    safety_stock = expected_usage
    
    # 발주 필요량 산정 (소계가 안전재고보다 부족할 경우 부족분만큼 발주)
    needed_qty = safety_stock - subtotal_stock
    
    if needed_qty <= 0:
        order_box = 0.0
    else:
        order_box = float(math.ceil(needed_qty))
        
    return pd.Series([subtotal_stock, safety_stock, order_box])

result_df = edited_stock.copy()
result_df[["미발주_소계", "안전재고", "발주필요량(BOX)"]] = result_df.apply(calculate_row_data, axis=1)

st.dataframe(
    result_df[["구분2", "입수(BOX)", "평균사용량", "당일입고예정량", "현재고량", "미발주_소계", "안전재고", "발주필요량(BOX)"]].fillna(0),
    column_config={
        "구분2": st.column_config.TextColumn("품목", disabled=True),
        "입수(BOX)": st.column_config.NumberColumn("입수(BOX)", format="%d", disabled=True),
        "평균사용량": st.column_config.NumberColumn("예상사용량", format="%.1f", disabled=True),
        "당일입고예정량": st.column_config.NumberColumn("입고예정량", format="%d", disabled=True),
        "현재고량": st.column_config.NumberColumn("현재고량", format="%d", disabled=True),
        "미발주_소계": st.column_config.NumberColumn("소계 (예상잔여재고)", format="%.1f", disabled=True),
        "안전재고": st.column_config.NumberColumn("안전재고", format="%.1f", disabled=True),
        "발주필요량(BOX)": st.column_config.NumberColumn("발주필요량(BOX)", format="%d", disabled=True),
    },
    hide_index=True,
    use_container_width=True
)
