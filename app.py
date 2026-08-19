import streamlit as st
import pandas as pd
import datetime

st.set_page_config(layout="wide", page_title="물류 재고 및 발주 통합 대시보드")

# --- [고정 틀 1: 품목 데이터 및 구조] ---
ITEM_LIST = [
    ("101", "I-01"), ("102", "I-02"), ("103", "I-03"), 
    ("스타 13호(양곡20kg)", "C-13"), ("스타 1호", "C-01"), ("스타 2호", "C-02"), 
    ("스타 3호", "C-03"), ("스타 4호", "C-04"), ("스타 5호", "C-05"), 
    ("스타 6호", "C-06"), ("스타 7호", "C-07"), ("스타 8호", "C-08"), ("스타 11호", "C-11")
]

if "stock_data" not in st.session_state:
    st.session_state.stock_data = pd.DataFrame({
        "구분2": [i[0] for i in ITEM_LIST],
        "excel_key": [i[1] for i in ITEM_LIST],
        "입수(PLT)": [300, 210, 210, 320, 2520, 960, 640, 640, 640, 320, 320, 320, 160],
        "전일기말재고": [20100, 14280, 11760, 320, 2680, 960, 1920, 4160, 3200, 3040, 2080, 800, 160],
        "입고예정량": [0] * len(ITEM_LIST),
        "전일실사용량": [0] * len(ITEM_LIST)
    })

st.title("📦 물류 재고 및 발주 통합 대시보드")

# --- [고정 틀 2: 날짜 및 파일 업로드] ---
today = datetime.date(2026, 8, 19)
col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
with col1: order_date = st.date_input("발주 대상일", today)
with col2: delivery_date = st.date_input("입고 예정일", today + datetime.timedelta(days=6))
with col3: avg_days = st.number_input("평균 산출 기간(일)", 1, 30, 10)
with col4: uploaded_file = st.file_uploader("출고일마감 파일 업로드", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        if '운송장번호(박스기준)' in df.columns and '박스호수(실제)' in df.columns:
            pivot = df.drop_duplicates(subset=['운송장번호(박스기준)'])['박스호수(실제)'].value_counts()
            for idx, row in st.session_state.stock_data.iterrows():
                st.session_state.stock_data.at[idx, "전일실사용량"] = pivot.get(row["excel_key"], 0)
    except Exception as e: st.error(f"❌ 파일 읽기 오류: {e}")

# --- [고정 틀 3: 실시간 즉시 계산 편집기] ---
st.subheader("📋 재고 및 입고량 입력 (수정 시 즉시 결과 반영)")
edited_df = st.data_editor(st.session_state.stock_data, num_rows="fixed", use_container_width=True, hide_index=True)

# --- [고정 틀 4: 즉시 계산 로직 (버튼 필요 없음)] ---
res = edited_df.copy()
lead_time = max(0, (delivery_date - order_date).days)
res["안전재고"] = (res["전일실사용량"] / avg_days) * lead_time
res["기초재고소계"] = res["전일기말재고"] - res["전일실사용량"] + res["입고예정량"]
res["발주필요량"] = res.apply(lambda x: max(0, x["안전재고"] - (x["기초재고소계"] - x["안전재고"])), axis=1)

# --- [고정 틀 5: 계산 결과 고정 영역] ---
st.markdown("---")
st.subheader("📊 최종 계산 및 발주 요약")
st.dataframe(
    res[["구분2", "입수(PLT)", "전일실사용량", "안전재고", "기초재고소계", "발주필요량"]], 
    use_container_width=True, hide_index=True
)
