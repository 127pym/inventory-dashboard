import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import math
import os

st.set_page_config(layout="wide", page_title="물류 자동화 대시보드")

st.title("📦 물류 재고 및 발주 자동화 대시보드")
SAVE_FILE = "inventory_data.json"

items_list = ["101", "102", "103", "스타 13호(양곡20kg)", "스타 1호", "스타 2호", "스타 3호", "스타 4호", "스타 5호", "스타 6호", "스타 7호", "스타 8호", "스타 11호"]
moq_dict = {"101": 0, "102": 0, "103": 0, "스타 13호(양곡20kg)": 1920, "스타 1호": 7560, "스타 2호": 4800, "스타 3호": 3840, "스타 4호": 3200, "스타 5호": 3200, "스타 6호": 1600, "스타 7호": 1600, "스타 8호": 1600, "스타 11호": 1280}

# --- [상단: 환경 설정] ---
st.markdown("---")
st.subheader("⚙️ 발주 자동화 환경 설정")

col_a, col_b, col_c = st.columns([2, 2, 2])
with col_a:
    base_date = st.date_input("발주 기준일", value=datetime.now().date())
with col_b:
    target_delivery_date = st.date_input("납품 예정일", value=base_date + timedelta(days=1))
with col_c:
    auto_order_threshold = st.number_input("발주 트리거 기준 (%)", min_value=0, max_value=200, value=80, step=5)
    st.caption("리드타임 소모량 대비 부족분 기준%")

# --- [날짜 동기화 계산] ---
base_today = datetime.combine(base_date, datetime.min.time())
days_diff = (target_delivery_date - base_date).days
days_multiplier = max(1, days_diff + 1)

recent_dates = [(base_today - timedelta(days=i+1)).strftime('%m/%d') for i in range(9, -1, -1)]
future_dates_md = [(base_today + timedelta(days=i)).strftime('%m/%d') for i in range(7)]

# --- [세션 상태 안전 초기화] ---
if "recent_10days_df" not in st.session_state or list(st.session_state.recent_10days_df.columns[1:]) != recent_dates:
    st.session_state.recent_10days_df = pd.DataFrame({"구분2": items_list, **{d: [0]*len(items_list) for d in recent_dates}})

if "schedule_df" not in st.session_state or list(st.session_state.schedule_df.columns[1:]) != future_dates_md:
    st.session_state.schedule_df = pd.DataFrame({"구분2": items_list, **{d: [0]*len(items_list) for d in future_dates_md}})

if "stock_input_df" not in st.session_state or len(st.session_state.stock_input_df) != len(items_list):
    st.session_state.stock_input_df = pd.DataFrame({
        "구분2": items_list,
        "전일마감재고": [0] * len(items_list),
        "당일입고예정량": [0] * len(items_list)
    })

# --- [UI: 표 2 - 최근 10일 사용량] ---
st.markdown("---")
st.subheader("📝 2. 최근 10일 사용량")
edited_10days = st.data_editor(st.session_state.recent_10days_df.fillna(0), hide_index=True, use_container_width=True, key="ed_10days")
st.session_state.recent_10days_df = edited_10days
calculated_avg = edited_10days.iloc[:, 1:].apply(pd.to_numeric, errors='coerce').fillna(0).mean(axis=1)

# --- [UI: 표 3 - 향후 입고 예정] ---
st.markdown("---")
st.subheader("📅 3. 향후 확정 입고 예정")
edited_schedule = st.data_editor(st.session_state.schedule_df.fillna(0), hide_index=True, use_container_width=True, key="ed_schedule")
st.session_state.schedule_df = edited_schedule

# --- [UI: 표 4 - 재고 및 당일 입고예정] ---
st.markdown("---")
st.subheader("📝 4. 재고 및 당일 입고예정")

current_prev_stock = st.session_state.stock_input_df["전일마감재고"].tolist() if "전일마감재고" in st.session_state.stock_input_df else [0]*len(items_list)
current_incoming = st.session_state.stock_input_df["당일입고예정량"].tolist() if "당일입고예정량" in st.session_state.stock_input_df else [0]*len(items_list)

combined_stock_df = pd.DataFrame({
    "구분2": items_list, 
    "평균사용량": calculated_avg.values,
    "전일마감재고": current_prev_stock[:len(items_list)],
    "당일입고예정량": current_incoming[:len(items_list)]
})

edited_stock = st.data_editor(combined_stock_df.fillna(0), hide_index=True, use_container_width=True, key="ed_stock")

st.session_state.stock_input_df = pd.DataFrame({
    "구분2": items_list,
    "전일마감재고": edited_stock["전일마감재고"].fillna(0),
    "당일입고예정량": edited_stock["당일입고예정량"].fillna(0)
})

# --- [파트 5: 최적 발주 계산 (기초재고 - 리드타임소모량 기준 적용)] ---
st.markdown("---")
st.subheader("🚀 5. 당일 최적 발주 필요량 결과")

def calculate_row_data(row):
    avg_use = float(row["평균사용량"]) if pd.notnull(row["평균사용량"]) else 0.0
    base_stock = float(row["전일마감재고"]) + float(row["당일입고예정량"])
    lead_time_usage = avg_use * days_multiplier
    
    # 💡 핵심 수정: 당일 기초재고에서 리드타임 소모량을 뺀 잔여 재고 (음수면 부족 상태)
    expected_remaining = base_stock - lead_time_usage
    
    # 순수 부족량 (모자란 수량)
    needed_qty = max(0.0, -expected_remaining)
    item_moq = moq_dict.get(row["구분2"], 0)
    
    # 발주 트리거 판단: 예상 잔여재고가 0 미만이거나 위험 수준일 때
    # (여기서는 기초재고가 리드타임 소모량보다 부족해지기 시작할 때 발주가 들어가도록 설정)
    is_shortage = expected_remaining < (lead_time_usage * (auto_order_threshold / 100.0))
    
    if item_moq == 0: # 주력품목 (101~103)
        if is_shortage or needed_qty > 0:
            return pd.Series([base_stock, lead_time_usage, expected_remaining, needed_qty, 0, float(math.ceil(needed_qty)), "✅ 주력품목 즉시발주"])
        return pd.Series([base_stock, lead_time_usage, expected_remaining, 0, 0, 0, "발주 불필요"])
        
    elif row["구분2"] == "스타 13호(양곡20kg)": # 13호 소량 단위
        if is_shortage or needed_qty > 0:
            order_box = float(math.ceil(max(needed_qty, 1) / 320.0) * 320)
            return pd.Series([base_stock, lead_time_usage, expected_remaining, needed_qty, 320, order_box, "📦 13호 소량발주"])
        return pd.Series([base_stock, lead_time_usage, expected_remaining, 0, 320, 0, "발주 불필요"])
        
    else: # 일반 MOQ 품목
        if is_shortage:
            return pd.Series([base_stock, lead_time_usage, expected_remaining, needed_qty, item_moq, float(item_moq), "🚨 자동발주 (MOQ충족)"])
        return pd.Series([base_stock, lead_time_usage, expected_remaining, 0, item_moq, 0, "안정"])

result_df = edited_stock.copy()
new_cols = result_df.apply(calculate_row_data, axis=1)
new_cols.columns = ["당일기초재고", "리드타임소모량", "예상잔여재고", "순수부족량", "기준MOQ", "발주필요량(BOX)", "상태"]
final_df = pd.concat([result_df, new_cols], axis=1)

st.dataframe(final_df, hide_index=True, use_container_width=True)
