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
    "스타 1호": 7560, "스타 2호": 4800, "스타 3호": 3840, "스타 4호": 3200,
    "스타 5호": 3200, "스타 6호": 1600, "스타 7호": 1600, "스타 8호": 1600,
    "스타 10호": 2400, "스타 11호": 1280, "스타 13호(양곡20kg)": 1920
}

# --- [상단: 환경 설정 (기준일 + MOQ 발주 기준%)] ---
st.markdown("---")
st.subheader("⚙️ 발주 자동화 환경 설정")

col_a, col_b, col_c = st.columns([2, 2, 2])

with col_a:
    base_date = st.date_input("발주 기준일", value=datetime.now().date())
with col_b:
    target_delivery_date = st.date_input("납품 예정일", value=base_date + timedelta(days=3))
with col_c:
    # 0~100 사이의 퍼센트 입력
    auto_order_threshold = st.number_input("MOQ 자동 발주 임계값 (%)", min_value=0, max_value=100, value=80, step=5)
    st.caption("필요 수량이 MOQ의 N% 이상일 경우 MOQ 수량으로 자동 발주")

# 날짜 로직
base_today = datetime.combine(base_date, datetime.min.time())
days_diff = (target_delivery_date - base_date).days
days_multiplier = max(1, days_diff)

recent_dates = [(base_today - timedelta(days=i+1)).strftime('%m/%d') for i in range(9, -1, -1)]
future_dates_obj = [base_today + timedelta(days=i) for i in range(max(7, days_multiplier + 1))]
future_dates_md = [d.strftime('%m/%d') for d in future_dates_obj]

# ... (이후 데이터 로드 및 초기화 로직은 기존과 동일) ...
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

# --- [파트 1, 2, 3은 생략 (이전 코드와 동일)] ---
# (코드 간결화를 위해 생략했지만, 실제 깃허브에는 아래 파트 4 함수만 잘 연동하시면 됩니다.)

# --- [파트 4: 핵심 변경 로직] ---
def calculate_row_data(row):
    item_name = row["구분2"]
    avg_use = float(row["평균사용량"]) if pd.notnull(row["평균사용량"]) else 0.0
    prev_stock = float(row["전일마감재고"]) if pd.notnull(row["전일마감재고"]) else 0.0
    incoming = float(row["당일입고예정량"]) if pd.notnull(row["당일입고예정량"]) else 0.0

    base_stock = prev_stock + incoming
    expected_usage = avg_use * days_multiplier
    subtotal_stock = max(0, base_stock - expected_usage)
    needed_qty = max(0, expected_usage - subtotal_stock)
    
    item_moq = moq_dict.get(item_name, 0)
    
    # 자동 발주 로직
    if needed_qty <= 0:
        final_order = 0
        status = "발주 불필요"
    elif needed_qty >= (item_moq * (auto_order_threshold / 100)):
        final_order = item_moq # 임계값 넘으면 MOQ만큼 발주
        status = "자동 발주 (MOQ 채움)"
    else:
        final_order = 0 # 임계값 미달 시 미발주
        status = f"미달 (필요:{int(needed_qty)} < {auto_order_threshold}%)"
        
    return pd.Series([base_stock, subtotal_stock, item_moq, final_order, status])

# result_df 생성 및 출력 (위 함수를 적용하여 출력)
# ... (이후 데이터프레임 출력 부분도 위 로직을 반영하여 수정) ...
