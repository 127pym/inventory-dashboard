import streamlit as st
import pandas as pd
import datetime
import os

st.set_page_config(layout="wide", page_title="물류 재고 및 발주 통합 대시보드")
st.markdown("""
    <style>
    .stDataFrame { font-size: 12px; }
    div[data-testid="stDataFrame"] { padding: 0px !important; }
    </style>
    """, unsafe_allow_html=True)

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
        "구분2": [i[0] for i in ITEM_LIST],
        "excel_key": [i[1] for i in ITEM_LIST],
        "입수(PLT)": [300, 210, 210, 320, 2520, 960, 640, 640, 640, 320, 320, 320, 160],
        "전일기말재고": [20100, 14280, 11760, 320, 2680, 960, 1920, 4160, 3200, 3040, 2080, 800, 160],
        "당일입고량": [0]*len(ITEM_LIST), "입고예정량": [0]*len(ITEM_LIST),
        "전일실사용량": [0]*len(ITEM_LIST), "누적평균사용량": [0]*len(ITEM_LIST)
    })

st.title("📦 물류 재고 및 발주 통합 대시보드")

# --- [2. 설정 및 업로드] ---
col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
with col1: order_date = st.date_input("발주 대상일", datetime.date(2026, 8, 21))
with col2: delivery_date = st.date_input("입고 예정일", datetime.date(2026, 8, 27))
with col4: uploaded_file = st.file_uploader("출고일마감 파일 업로드", type=["xlsx", "xls"])

with st.expander("⚙️ 버퍼 설정", expanded=False):
    m1, m2, m3 = st.columns(3)
    margin_thu_fri = m1.number_input("목/금 버퍼", 1.0, 2.0, 1.20, 0.05)
    margin_mon = m2.number_input("월요일 버퍼", 1.0, 2.0, 1.10, 0.05)
    margin_other = m3.number_input("기타 버퍼", 1.0, 2.0, 1.05, 0.05)

# --- [3. 통합 계산 엔진] ---
res = st.session_state.stock_data.copy()
file_usages = {}
if uploaded_file:
    df = pd.read_excel(uploaded_file)
    if '운송장번호(박스기준)' in df.columns and '박스호수(실제)' in df.columns:
        pivot = df.drop_duplicates(subset=['운송장번호(박스기준)'])['박스호수(실제)'].value_counts()
        for idx, row in res.iterrows():
            file_usages[row["excel_key"]] = int(pivot.get(row["excel_key"], 0))

for idx, row in res.iterrows():
    key = row["excel_key"]
    today_use = file_usages.get(key, row["전일실사용량"])
    res.at[idx, "전일실사용량"] = int(today_use)
    
    old_avg = float(row["누적평균사용량"])
    new_avg = float(today_use) if old_avg == 0 else (old_avg * 0.8) + (float(today_use) * 0.2)
    res.at[idx, "누적평균사용량"] = int(round(new_avg))

lead_time = max(0, (delivery_date - order_date).days) + 1
def get_margin(key, wd):
    if key in ["I-01", "I-02", "I-03"]:
        return margin_thu_fri if wd in [3, 4] else (margin_mon if wd == 0 else margin_other)
    return 1.0

res["안전재고"] = [int(round(float(row["누적평균사용량"]) * lead_time * get_margin(row["excel_key"], order_date.weekday()))) for _, row in res.iterrows()]
res["기초재고소계"] = res["전일기말재고"] + res["당일입고량"] - res["전일실사용량"] + res["입고예정량"]
res["예상잔여재고"] = res["기초재고소계"] - res["안전재고"]
res["발주필요량"] = res.apply(lambda x: max(0, int(x["안전재고"]) - int(x["기초재고소계"])), axis=1)

# --- [4. 통합 데이터 입력 및 요약표] ---
st.subheader("📋 통합 재고 관리 및 발주 요약")
edited_df = st.data_editor(res, use_container_width=True, hide_index=True)

if st.button("💾 데이터 저장 및 히스토리 업데이트", type="primary", use_container_width=True):
    # 히스토리 기록
    history_row = {"날짜": order_date.strftime("%Y-%m-%d")}
    history_row.update({row["excel_key"]: int(row["전일실사용량"]) for _, row in edited_df.iterrows()})
    
    # 데이터 저장
    edited_df.to_csv(DATA_FILE, index=False)
    
    if os.path.exists(HISTORY_FILE):
        hist = pd.read_csv(HISTORY_FILE)
        hist = hist[hist["날짜"] != history_row["날짜"]]
        pd.concat([hist, pd.DataFrame([history_row])]).to_csv(HISTORY_FILE, index=False)
    else:
        pd.DataFrame([history_row]).to_csv(HISTORY_FILE, index=False)
    st.success("✅ 저장 완료!")

# --- [5. 통합 누적 기록부] ---
st.markdown("---")
st.subheader("📈 일자별 실사용량 누적 통계표")
if os.path.exists(HISTORY_FILE):
    hist = pd.read_csv(HISTORY_FILE)
    pivot = hist.set_index("날짜").T.reset_index().rename(columns={"index": "excel_key"})
    meta = edited_df[["excel_key", "구분2"]]
    pivot = pd.merge(meta, pivot, on="excel_key", how="left").fillna(0)
    
    d_cols = [c for c in pivot.columns if c not in ["excel_key", "구분2"]]
    pivot["합계"] = pivot[d_cols].sum(axis=1).astype(int)
    pivot["평균"] = pivot[d_cols].mean(axis=1).round().astype(int)
    st.dataframe(pivot.style.set_properties(**{'font-size': '11px'}), use_container_width=True, hide_index=True)
