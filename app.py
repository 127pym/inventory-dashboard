import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import math
import os

st.set_page_config(layout="wide", page_title="물류 자동화 대시보드")

st.title("📦 물류 재고 및 발주 자동화 대시보드")

SAVE_FILE = "inventory_data.json"

# 품목 리스트 및 기본 입수 정보
items_list = [
    "101", "102", "103", 
    "스타 13호(양곡20kg)", "스타 1호", "스타 2호", 
    "스타 3호", "스타 4호", "스타 5호", 
    "스타 6호", "스타 7호", "스타 8호", "스타 11호"
]
plt_list = [300, 210, 210, 320, 2520, 960, 640, 640, 640, 320, 320, 320, 160]

moq_dict = {
    "101": 0, "102": 0, "103": 0,
    "스타 1호": 7560, "스타 2호": 4800, "스타 3호": 3840, "스타 4호": 3200,
    "스타 5호": 3200, "스타 6호": 1600, "스타 7호": 1600, "스타 8호": 1600,
    "스타 11호": 1280, "스타 13호(양곡20kg)": 1920
}

# --- [상단: 환경 설정] ---
st.markdown("---")
st.subheader("⚙️ 발주 자동화 환경 설정")

col_a, col_b, col_c, save_col = st.columns([2, 2, 2, 1])

with col_a:
    base_date = st.date_input("발주 기준일", value=datetime.now().date())
with col_b:
    target_delivery_date = st.date_input("납품 예정일", value=base_date + timedelta(days=1))
with col_c:
    auto_order_threshold = st.number_input("MOQ 자동 발주 임계값 (%)", min_value=0, max_value=100, value=80, step=5)
    st.caption("MOQ 품목이 필요량 N% 이상일 때 자동 발주")

# 리드타임 로직: 당일 포함 + 1일
base_today = datetime.combine(base_date, datetime.min.time())
days_diff = (target_delivery_date - base_date).days
days_multiplier = max(1, days_diff + 1) 

yesterday = base_today - timedelta(days=1)
recent_dates = [(yesterday - timedelta(days=i)).strftime('%m/%d') for i in range(9, -1, -1)]
future_dates_obj = [base_today + timedelta(days=i) for i in range(max(7, days_multiplier + 1))]
future_dates_md = [d.strftime('%m/%d') for d in future_dates_obj]

with save_col:
    st.write("") 
    st.write("") 
    if st.button("💾 데이터 저장", use_container_width=True):
        if "recent_10days_df" in st.session_state and "schedule_df" in st.session_state and "stock_input_df" in st.session_state:
            save_dict = {
                "recent_10days": st.session_state.recent_10days_df.to_dict(),
                "schedule": st.session_state.schedule_df.to_dict(),
                "stock_input": st.session_state.stock_input_df.to_dict()
            }
            df_to_save = pd.DataFrame([save_dict])
            df_to_save.to_json(SAVE_FILE)
            st.success("✅ 저장 완료!")

st.info(f"💡 **발주 기준일:** {base_date.strftime('%Y-%m-%d')} | **납품 예정일:** {target_delivery_date.strftime('%Y-%m-%d')} | **재고 확보:** {days_multiplier}일(리드) + 3일(안전버퍼)")

# --- [데이터 저장/로드 로직] ---
if os.path.exists(SAVE_FILE) and "loaded" not in st.session_state:
    try:
        loaded_df = pd.read_json(SAVE_FILE)
        loaded_dict = loaded_df.iloc[0].to_dict()
        st.session_state.recent_10days_df = pd.DataFrame(loaded_dict["recent_10days"])
        st.session_state.schedule_df = pd.DataFrame(loaded_dict["schedule"])
        if "stock_input" in loaded_dict:
            st.session_state.stock_input_df = pd.DataFrame(loaded_dict["stock_input"])
        st.session_state.loaded = True
    except: pass

# --- [세션 초기화 및 키인 로직] ---
if "recent_10days_df" not in st.session_state:
    initial_data = {"구분2": items_list}
    for d_str in recent_dates: initial_data[d_str] = [0] * len(items_list) 
    st.session_state.recent_10days_df = pd.DataFrame(initial_data)

if "schedule_df" not in st.session_state:
    sched_data = {"구분2": items_list}
    for f_date in future_dates_md: sched_data[f_date] = [0] * len(items_list)
    st.session_state.schedule_df = pd.DataFrame(sched_data)

if "stock_input_df" not in st.session_state or "전일마감재고" not in st.session_state.stock_input_df.columns:
    st.session_state.stock_input_df = pd.DataFrame({
        "구분2": items_list,
        "전일마감재고": [0] * len(items_list),
        "당일입고예정량": [0] * len(items_list)
    })

# --- [UI: 사용량, 스케줄, 재고 입력] ---
st.markdown("---")
st.subheader("📝 2. 최근 10일 사용량 키인")
st.session_state.recent_10days_df = st.data_editor(st.session_state.recent_10days_df, hide_index=True, use_container_width=True)
calculated_avg = st.session_state.recent_10days_df[[col for col in st.session_state.recent_10days_df.columns if col != "구분2"]].mean(axis=1)

st.markdown("---")
st.subheader("📅 3. 향후 확정 입고 예정 스케줄")
st.session_state.schedule_df = st.data_editor(st.session_state.schedule_df, hide_index=True, use_container_width=True)

st.markdown("---")
st.subheader("📝 4. 재고 및 당일 입고예정 키인")
combined_stock_df = pd.DataFrame({
    "구분2": items_list, "입수(BOX)": plt_list, "평균사용량": calculated_avg.reset_index(drop=True),
    "전일마감재고": st.session_state.stock_input_df["전일마감재고"].reset_index(drop=True),
    "당일입고예정량": st.session_state.stock_input_df["당일입고예정량"].reset_index(drop=True)
})
edited_stock = st.data_editor(combined_stock_df, hide_index=True, use_container_width=True)
st.session_state.stock_input_df["전일마감재고"] = edited_stock["전일마감재고"]
st.session_state.stock_input_df["당일입고예정량"] = edited_stock["당일입고예정량"]

# --- [파트 4: 최적 발주 및 주력상품 예외/안전재고 로직] ---
st.markdown("---")
st.subheader("🚀 5. 당일 최적 발주 필요량 결과")

def calculate_row_data(row):
    avg_use = float(row["평균사용량"])
    base_stock = float(row["전일마감재고"]) + float(row["당일입고예정량"])
    
    # 필수 확보: 리드타임(days_multiplier) + 안전버퍼(3일)
    safety_buffer = avg_use * 3
    required_stock = (avg_use * days_multiplier) + safety_buffer
    
    # 미발주 시 예상 잔여재고 (리드타임 종료 시점)
    expected_remaining = base_stock - (avg_use * days_multiplier)
    
    # 발주 필요량 (안전버퍼까지 고려한 수치)
    needed_qty = max(0.0, required_stock - base_stock)
    
    item_moq = moq_dict.get(row["구분2"], 0)
    
    # 1. 주력상품(101~103, moq 0) 로직
    if item_moq == 0:
        if needed_qty > 0:
            return pd.Series([base_stock, expected_remaining, needed_qty, 0, float(math.ceil(needed_qty)), "✅ 주력품목 즉시발주"])
        return pd.Series([base_stock, expected_remaining, 0, 0, 0, "발주 불필요"])
    
    # 2. 일반 MOQ 상품 로직
    threshold_qty = item_moq * (auto_order_threshold / 100.0)
    
    # 안전버퍼(3일) 위협 시 긴급 발주
    is_critical = expected_remaining <= safety_buffer
    
    if is_critical or needed_qty >= threshold_qty:
        return pd.Series([base_stock, expected_remaining, needed_qty, item_moq, float(item_moq), "🚨 긴급/자동발주 (MOQ충족)"])
    else:
        return pd.Series([base_stock, expected_remaining, needed_qty, item_moq, 0, f"안정 (필요:{int(needed_qty)})"])

result_df = edited_stock.copy()
result_df[["당일기초재고", "예상잔여", "순수부족량", "기준MOQ", "발주필요량(BOX)", "상태"]] = result_df.apply(calculate_row_data, axis=1)

st.dataframe(result_df, hide_index=True, use_container_width=True)
