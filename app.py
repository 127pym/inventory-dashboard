import streamlit as st
import pandas as pd
import datetime
import os

st.set_page_config(layout="wide", page_title="물류 재고 및 발주 통합 대시보드")

DATA_FILE = "inventory_master_data.csv"
HISTORY_FILE = "usage_history.csv"

# --- [1. 데이터 로드/초기화] ---
ITEM_LIST = [
    ("101", "I-01"), ("102", "I-02"), ("103", "I-03"), 
    ("스타 13호(양곡20kg)", "C-13"), ("스타 1호", "C-01"), ("스타 2호", "C-02"), 
    ("스타 3호", "C-03"), ("스타 4호", "C-04"), ("스타 5호", "C-05"), 
    ("스타 6호", "C-06"), ("스타 7호", "C-07"), ("스타 8호", "C-08"), ("스타 11호", "C-11")
]

if os.path.exists(DATA_FILE):
    st.session_state.stock_data = pd.read_csv(DATA_FILE)
else:
    st.session_state.stock_data = pd.DataFrame({
        "구분2": [i[0] for i in ITEM_LIST], "excel_key": [i[1] for i in ITEM_LIST],
        "단가": [1000] * len(ITEM_LIST), # [추가] 단가 컬럼
        "전일기말재고": [20100, 14280, 11760, 320, 2680, 960, 1920, 4160, 3200, 3040, 2080, 800, 160],
        "당일입고량": [0]*len(ITEM_LIST), "입고예정량": [0]*len(ITEM_LIST),
        "전일실사용량": [0]*len(ITEM_LIST), "누적평균사용량": [0]*len(ITEM_LIST)
    })

st.title("📦 물류 재고 및 발주 비용 정산 대시보드")

# --- [2. 계산 로직] ---
res = st.session_state.stock_data.copy()
# ... (기존 계산 로직 동일) ...
# (중략) 
# 리드타임 및 마진 적용 로직 등은 기존과 동일하게 유지

# --- [3. 통합 표] ---
st.subheader("📋 재고 및 발주 관리 (단가 입력 필수)")
edited_df = st.data_editor(res, use_container_width=True, hide_index=True)

if st.button("💾 데이터 저장 및 정산 업데이트"):
    edited_df.to_csv(DATA_FILE, index=False)
    # 히스토리 저장 (단가 정보도 같이 보관하여 금액 산출)
    hist_row = {"날짜": datetime.date.today().strftime("%Y-%m-%d")}
    hist_row.update({row["excel_key"]: int(row["전일실사용량"]) for _, row in edited_df.iterrows()})
    
    # 단가 정보 저장 (금액 산출용)
    price_map = {row["excel_key"]: row["단가"] for _, row in edited_df.iterrows()}
    
    hist = pd.read_csv(HISTORY_FILE) if os.path.exists(HISTORY_FILE) else pd.DataFrame()
    hist = pd.concat([hist[hist["날짜"] != hist_row["날짜"]], pd.DataFrame([hist_row])])
    hist.to_csv(HISTORY_FILE, index=False)
    st.rerun()

# --- [4. 정산 대장 (품목별 사용량 * 단가)] ---
st.markdown("---")
st.subheader("💰 월간 비용 정산 내역 (사용량 × 단가)")

if os.path.exists(HISTORY_FILE):
    hist = pd.read_csv(HISTORY_FILE)
    price_map = dict(zip(edited_df["excel_key"], edited_df["단가"]))
    
    # 사용량 데이터에 단가 곱해서 금액으로 변환
    cost_df = hist.copy()
    for col in cost_df.columns:
        if col in price_map:
            cost_df[col] = cost_df[col] * price_map[col]
            
    # 표 변환 (품목 세로, 날짜 가로)
    pivot = cost_df.set_index("날짜").T.reset_index().rename(columns={"index": "excel_key"})
    pivot = pd.merge(edited_df[["excel_key", "구분2"]], pivot, on="excel_key", how="left").fillna(0)
    
    # 합계 계산
    d_cols = [c for c in pivot.columns if c not in ["excel_key", "구분2"]]
    pivot["총금액"] = pivot[d_cols].sum(axis=1).astype(int)
    
    st.dataframe(pivot.style.format({c: "{:,}원" for c in d_cols + ["총금액"]}), 
                 use_container_width=True, hide_index=True)
