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

# --- [날짜 동기화 계산] ---
base_today = datetime.combine(base_date, datetime.min.time())
days_diff = (target_delivery_date - base_date).days
days_multiplier = max(1, days_diff + 1)

# 기준일 변경 시 즉시 반영되는 날짜 리스트
recent_dates = [(base_today - timedelta(days=i+1)).strftime('%m/%d') for i in range(9, -1, -1)]
future_dates_md = [(base_today + timedelta(days=i)).strftime('%m/%d') for i in range(7)]

# --- [세션 상태 관리 및 날짜 변경 대응] ---
# 표 2 날짜 동기화
if "recent_10days_df" not in st.session_state or list(st.session_state.recent_10days_df.columns[1:]) != recent_dates:
    st.session_state.recent_10days_df = pd.DataFrame({"구분2": items_list, **{d: [0]*len(items_list) for d in recent_dates}})

# 표 3 날짜 동기화
if "schedule_df" not in st.session_state or list(st.session_state.schedule_df.columns[1:]) != future_dates_md:
    st.session_state.schedule_df = pd.DataFrame({"구분2": items_list, **{d: [0]*len(items_list) for d in future_dates_md}})

if "stock_input_df" not in st.session_state:
    st.session_state.stock_input_df = pd.DataFrame({"구분2": items_list, "전일마감재고": [0]*len(items_list), "당일입고예정량": [0]*len(items_list)})

# --- [UI: 키인 데이터 편집] ---
st.markdown("---")
st.subheader("📝 2. 최근 10일 사용량")
st.session_state.recent_10days_df = st.data_editor(st.session_state.recent_10days_df.fillna(0), hide_index=True, use_container_width=True)
calculated_avg = st.session_state.recent_10days_df.iloc[:, 1:].fillna(0).mean(axis=1)

st.markdown("---")
st.subheader("📅 3. 향후 확정 입고 예정")
st.session_state.schedule_df = st.data_editor(st.session_state.schedule_df.fillna(0), hide_index=True, use_container_width=True)

st.markdown("---")
st.subheader("📝 4. 재고 및 당일 입고예정")
combined_stock_df = pd.DataFrame({
    "구분2": items_list, "평균사용량": calculated_avg,
    "전일마감재고": st.session_state.stock_input_df["전일마감재고"].fillna(0),
    "당일입고예정량": st.session_state.stock_input_df["당일입고예정량"].fillna(0)
})
edited_stock = st.data_editor(combined_stock_df, hide_index=True, use_container_width=True)
st.session_state.stock_input_df["전일마감재고"] = edited_stock["전일마감재고"].fillna(0)
st.session_state.stock_input_df["당일입고예정량"] = edited_stock["당일입고예정량"].fillna(0)

# --- [파트 5: 최적 발주 계산] ---
st.markdown("---")
st.subheader("🚀 5. 당일 최적 발주 필요량 결과")

def calculate_row_data(row):
    avg_use = float(row["평균사용량"]) if pd.notnull(row["평균사용량"]) else 0.0
    base_stock = float(row["전일마감재고"]) + float(row["당일입고예정량"])
    lead_time_usage = avg_use * days_multiplier
    
    stock_ratio = (base_stock / lead_time_usage * 100.0) if lead_time_usage > 0 else 999.0
    needed_qty = max(0.0, lead_time_usage - base_stock)
    item_moq = moq_dict.get(row["구분2"], 0)
    
    if item_moq == 0:
        if stock_ratio <= auto_order_threshold:
            return pd.Series([base_stock, lead_time_usage, stock_ratio, needed_qty, 0, float(math.ceil(needed_qty)), "✅ 주력품목 즉시발주"])
        return pd.Series([base_stock, lead_time_usage, stock_ratio, 0, 0, 0, "발주 불필요"])
    elif row["구분2"] == "스타 13호(양곡20kg)":
        if stock_ratio <= auto_order_threshold:
            order_box = float(math.ceil(max(needed_qty, 1) / 320.0) * 320)
            return pd.Series([base_stock, lead_time_usage, stock_ratio, needed_qty, 320, order_box, "📦 13호 소량발주"])
        return pd.Series([base_stock, lead_time_usage, stock_ratio, 0, 320, 0, "발주 불필요"])
    else:
        if stock_ratio <= auto_order_threshold:
            return pd.Series([base_stock, lead_time_usage, stock_ratio, needed_qty, item_moq, float(item_moq), "🚨 자동발주"])
        return pd.Series([base_stock, lead_time_usage, stock_ratio, 0, item_moq, 0, "안정"])

result_df = edited_stock.copy()
new_cols = result_df.apply(calculate_row_data, axis=1)
new_cols.columns = ["당일기초재고", "리드타임소모량", "재고비율(%)", "순수부족량", "기준MOQ", "발주필요량(BOX)", "상태"]
final_df = pd.concat([result_df, new_cols], axis=1)

st.dataframe(final_df, hide_index=True, use_container_width=True)
