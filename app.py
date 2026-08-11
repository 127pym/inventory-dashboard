import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import math
import os

st.set_page_config(layout="wide", page_title="물류 자동화 대시보드")

st.title("📦 물류 재고 및 발주 자동화 대시보드")

SAVE_FILE = "inventory_data.json"

# 품목 리스트 및 기본 입수 정보 (입수 = 1 PLT 당 박스 수)
items_list = [
    "101", "102", "103", 
    "스타 13호(양곡20kg)", "스타 1호", "스타 2호", 
    "스타 3호", "스타 4호", "스타 5호", 
    "스타 6호", "스타 7호", "스타 8호", "스타 11호"
]
plt_list = [300, 210, 210, 320, 2520, 960, 640, 640, 640, 320, 320, 320, 160]


# --- [최상단 배치: 날짜 설정 (표 1, 2 날짜 컬럼 자동 연동의 기준)] ---
st.markdown("---")
st.subheader("🎯 1. 기준일 및 납품 예정일 설정")

date_col1, date_col2, save_col = st.columns([2, 2, 1])

with date_col1:
    base_date = st.date_input("발주 기준일 (오늘)", value=datetime.now().date())

with date_col2:
    target_delivery_date = st.date_input("납품(도착) 예정일", value=base_date + timedelta(days=3))

# 날짜 객체 변환 및 차이 계산
base_today = datetime.combine(base_date, datetime.min.time())
days_diff = (target_delivery_date - base_date).days
days_multiplier = max(1, days_diff)

# [핵심] 상단 날짜 변경 시 표 1 (최근 10일) 날짜 컬럼 자동 생성
yesterday = base_today - timedelta(days=1)
recent_dates = [(yesterday - timedelta(days=i)).strftime('%m/%d') for i in range(9, -1, -1)]

# [핵심] 상단 날짜 변경 시 표 2 (향후 입고 스케줄) 날짜 컬럼 자동 생성
future_dates_obj = [base_today + timedelta(days=i) for i in range(max(7, days_multiplier + 1))]
future_dates_md = [d.strftime('%m/%d') for d in future_dates_obj]

with save_col:
    st.write("") 
    st.write("") 
    if st.button("💾 입력 데이터 저장", use_container_width=True):
        if "recent_10days_df" in st.session_state and "schedule_df" in st.session_state and "stock_input_df" in st.session_state:
            save_dict = {
                "recent_10days": st.session_state.recent_10days_df.to_dict(),
                "schedule": st.session_state.schedule_df.to_dict(),
                "stock_input": st.session_state.stock_input_df.to_dict()
            }
            df_to_save = pd.DataFrame([save_dict])
            df_to_save.to_json(SAVE_FILE)
            st.success("✅ 저장 완료!")

st.info(f"💡 **발주 기준일:** {base_date.strftime('%Y-%m-%d')} | **납품 예정일:** {target_delivery_date.strftime('%Y-%m-%d')} (리드타임 배수: **X {days_multiplier}일**)")


# --- [데이터 영구 저장 및 불러오기 기능] ---
if os.path.exists(SAVE_FILE) and "loaded" not in st.session_state:
    try:
        loaded_df = pd.read_json(SAVE_FILE)
        loaded_dict = loaded_df.iloc[0].to_dict()
        st.session_state.recent_10days_df = pd.DataFrame(loaded_dict["recent_10days"])
        st.session_state.schedule_df = pd.DataFrame(loaded_dict["schedule"])
        if "stock_input" in loaded_dict:
            st.session_state.stock_input_df = pd.DataFrame(loaded_dict["stock_input"])
        st.session_state.loaded = True
    except Exception as e:
        pass


# --- [세션 상태 유지 및 상단 변경 날짜와 컬럼 동기화 로직] ---

# 1. 표 1 컬럼을 상단 기준일의 최근 10일 날짜로 동기화
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

# 2. 표 2 컬럼을 상단 기준일의 향후 스케줄 날짜로 동기화
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

# 3. 표 3 재고 및 입고예정 입력 상태 관리
if "stock_input_df" not in st.session_state or "전일마감재고" not in st.session_state.stock_input_df.columns:
    st.session_state.stock_input_df = pd.DataFrame({
        "구분2": items_list,
        "전일마감재고": [0] * len(items_list),
        "당일입고예정량": [0] * len(items_list)
    })


# --- [파트 1] 최근 10일 사용량 키인 (상단 날짜에 맞춰 컬럼 자동 변환) ---
st.markdown("---")
st.subheader("📝 2. 최근 10일 사용량 키인")
st.info(f"기준일 전날({recent_dates[-1]})까지의 일자별 실적 입력")

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


# --- [파트 2] 향후 확정 입고 예정 스케줄 관리 (상단 날짜에 맞춰 컬럼 자동 변환) ---
st.markdown("---")
st.subheader("📅 3. 향후 확정 입고 예정 스케줄 관리")
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


# --- [파트 3] 전일 마감 재고 및 당일 입고예정 키인 ---
st.markdown("---")
st.subheader("📝 4. 재고 및 당일 입고예정 키인")
st.info("**전일마감재고**와 **당일입고예정량**을 직접 키인하세요. 평균사용량이 함께 표시됩니다.")

combined_stock_df = pd.DataFrame({
    "구분2": items_list,
    "입수(BOX)": plt_list,  
    "평균사용량": calculated_avg.reset_index(drop=True),  
    "전일마감재고": st.session_state.stock_input_df["전일마감재고"].fillna(0).reset_index(drop=True),
    "당일입고예정량": st.session_state.stock_input_df["당일입고예정량"].fillna(0).reset_index(drop=True)
})

edited_stock = st.data_editor(
    combined_stock_df,
    column_config={
        "구분2": st.column_config.TextColumn("품목", disabled=True),
        "입수(BOX)": st.column_config.NumberColumn("입수(BOX)", format="%d", disabled=True),
        "평균사용량": st.column_config.NumberColumn("평균사용량", format="%.1f", disabled=True),
        "전일마감재고": st.column_config.NumberColumn("전일마감재고 (키인)", format="%d"),
        "당일입고예정량": st.column_config.NumberColumn("당일입고예정량 (키인)", format="%d"),
    },
    hide_index=True,
    use_container_width=True,
    height=420,
    key="editor_stock"
)

st.session_state.stock_input_df["전일마감재고"] = edited_stock["전일마감재고"].fillna(0)
st.session_state.stock_input_df["당일입고예정량"] = edited_stock["당일입고예정량"].fillna(0)


# --- [파트 4] 최적 발주 필요량 계산 및 결과 출력 ---
st.markdown("---")
st.subheader("🚀 5. 당일 최적 발주 필요량 결과 (소계, 안전재고비율 산정)")

def calculate_row_data(row):
    avg_use = float(row["평균사용량"]) if pd.notnull(row["평균사용량"]) else 0.0
    prev_stock = float(row["전일마감재고"]) if pd.notnull(row["전일마감재고"]) else 0.0
    incoming = float(row["당일입고예정량"]) if pd.notnull(row["당일입고예정량"]) else 0.0

    base_stock = prev_stock + incoming
    expected_usage = avg_use * days_multiplier
    subtotal_stock = base_stock - expected_usage
    
    if subtotal_stock < 0:
        subtotal_stock = 0.0
    
    safety_stock = expected_usage
    
    if safety_stock > 0:
        safety_ratio = (subtotal_stock / safety_stock) * 100
    else:
        safety_ratio = 0.0

    needed_qty = safety_stock - subtotal_stock
    
    if needed_qty <= 0:
        order_box = 0.0
    else:
        order_box = float(math.ceil(needed_qty))
        
    return pd.Series([base_stock, subtotal_stock, safety_stock, safety_ratio, order_box])

result_df = edited_stock.copy()
result_df[["당일기초재고", "미발주_소계", "안전재고", "안전재고비율", "발주필요량(BOX)"]] = result_df.apply(calculate_row_data, axis=1)

st.dataframe(
    result_df[["구분2", "입수(BOX)", "평균사용량", "전일마감재고", "당일입고예정량", "당일기초재고", "미발주_소계", "안전재고", "안전재고비율", "발주필요량(BOX)"]].fillna(0),
    column_config={
        "구분2": st.column_config.TextColumn("품목", disabled=True),
        "입수(BOX)": st.column_config.NumberColumn("입수(BOX)", format="%d", disabled=True),
        "평균사용량": st.column_config.NumberColumn("예상사용량", format="%.1f", disabled=True),
        "전일마감재고": st.column_config.NumberColumn("전일마감재고", format="%d", disabled=True),
        "당일입고예정량": st.column_config.NumberColumn("당일입고예정", format="%d", disabled=True),
        "당일기초재고": st.column_config.NumberColumn("당일기초재고", format="%.1f", disabled=True),
        "미발주_소계": st.column_config.NumberColumn("소계 (예상잔여재고)", format="%.1f", disabled=True),
        "안전재고": st.column_config.NumberColumn("안전재고", format="%.1f", disabled=True),
        "안전재고비율": st.column_config.NumberColumn("안전재고비율", format="%.1f%%"),
        "발주필요량(BOX)": st.column_config.NumberColumn("발주필요량(BOX)", format="%d", disabled=True),
    },
    hide_index=True,
    use_container_width=True,
)
