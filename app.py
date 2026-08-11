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
    "스타 13호(양곡20kg)": 1920,
    "스타 1호": 7560, "스타 2호": 4800, "스타 3호": 3840, "스타 4호": 3200,
    "스타 5호": 3200, "스타 6호": 1600, "스타 7호": 1600, "스타 8호": 1600,
    "스타 11호": 1280
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
    auto_order_threshold = st.number_input("발주 트리거 기준 (%)", min_value=0, max_value=200, value=80, step=5)
    st.caption("리드타임 소모량 대비 재고 비율이 N% 이하일 때 발주 검토")

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

st.info(f"💡 **발주 기준일:** {base_date.strftime('%Y-%m-%d')} | **납품 예정일:** {target_delivery_date.strftime('%Y-%m-%d')} | **리드타임:** {days_multiplier}일")

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

# --- [파트 4: 최적 발주 및 리드타임 대비 비율 제어 로직] ---
st.markdown("---")
st.subheader("🚀 5. 당일 최적 발주 필요량 결과")

def calculate_row_data(row):
    item_name = row["구분2"]
    avg_use = float(row["평균사용량"])
    base_stock = float(row["전일마감재고"]) + float(row["당일입고예정량"])
    
    # 1. 리드타임 동안 소모될 기준 총량 (평균사용량 × 리드타임 일수)
    lead_time_usage = avg_use * days_multiplier
    
    # 2. 리드타임 소모량 대비 현재 기초재고의 비율(%) 계산
    if lead_time_usage > 0:
        stock_ratio = (base_stock / lead_time_usage) * 100.0
    else:
        stock_ratio = 999.0 # 사용량이 0인 경우 여유로 둠
        
    # 순수 부족량 (기준 소모량 - 현재 기초재고)
    needed_qty = max(0.0, lead_time_usage - base_stock)
    item_moq = moq_dict.get(item_name, 0)
    
    # 3. 주력품목 (101~103)
    if item_moq == 0:
        if stock_ratio <= auto_order_threshold:
            return pd.Series([base_stock, lead_time_usage, stock_ratio, needed_qty, 0, float(math.ceil(needed_qty)), "✅ 주력품목 즉시발주"])
        return pd.Series([base_stock, lead_time_usage, stock_ratio, 0, 0, 0, "발주 불필요 (충분)"])
    
    # 4. 스타 13호 전용 예외 규칙 (320 단위 소량 발주)
    if item_name == "스타 13호(양곡20kg)":
        if stock_ratio <= auto_order_threshold:
            order_box = float(math.ceil(max(needed_qty, 1) / 320.0) * 320)
            return pd.Series([base_stock, lead_time_usage, stock_ratio, needed_qty, 320, order_box, "📦 13호 소량발주 (320단위)"])
        return pd.Series([base_stock, lead_time_usage, stock_ratio, 0, 320, 0, "발주 불필요 (충분)"])

    # 5. 일반 MOQ 상품 로직
    if stock_ratio <= auto_order_threshold:
        return pd.Series([base_stock, lead_time_usage, stock_ratio, needed_qty, item_moq, float(item_moq), "🚨 자동발주 (MOQ충족)"])
    else:
        return pd.Series([base_stock, lead_time_usage, stock_ratio, 0, item_moq, 0, f"안정 ({int(stock_ratio)}% 보유)"])

result_df = edited_stock.copy()
result_df[["당일기초재고", "리드타임소모량", "재고비율(%)", "순수부족량", "적용기준(MOQ/단위)", "발주필요량(BOX)", "상태"]] = result_df.apply(calculate_row_data, axis=1)

st.dataframe(result_df, hide_index=True, use_container_width=True)
