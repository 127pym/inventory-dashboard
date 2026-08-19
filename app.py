import streamlit as st
import pandas as pd
import datetime

st.set_page_config(layout="wide", page_title="물류 재고 및 발주 통합 대시보드")

# 1. 초기 데이터 구조
if "stock_data" not in st.session_state:
    st.session_state.stock_data = pd.DataFrame({
        "구분2": ["101", "102", "103", "스타 13호(양곡20kg)", "스타 1호", "스타 2호", "스타 3호", "스타 4호", "스타 5호", "스타 6호", "스타 7호", "스타 8호", "스타 11호"],
        "excel_key": ["I-01", "I-02", "I-03", "C-13", "C-01", "C-02", "C-03", "C-04", "C-05", "C-06", "C-07", "C-08", "C-11"],
        "입수(PLT)": [300, 210, 210, 320, 2520, 960, 640, 640, 640, 320, 320, 320, 160],
        "MOQ_PCS": [3000, 1890, 1680, 2240, 7560, 5760, 3840, 3840, 3200, 1920, 1600, 1600, 1280],
        "전일기말재고": [20100, 14280, 11760, 320, 2680, 960, 1920, 4160, 3200, 3040, 2080, 800, 160],
        "전일입고재고": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "전일실사용량": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "당일입고예정": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    })

if "usage_history" not in st.session_state:
    st.session_state.usage_history = {}

if "calculated_result" not in st.session_state:
    st.session_state.calculated_result = None

st.title("📦 물류 재고 및 발주 통합 대시보드")

# 2. 파일 처리 로직 (중복 제거 후 카운트)
uploaded_file = st.file_uploader("출고일마감 파일 업로드", type=["xlsx", "xls"])
file_date = st.date_input("기준 날짜", datetime.date.today())

if uploaded_file is not None:
    with st.spinner("피벗 집계 중..."):
        try:
            df = pd.read_excel(uploaded_file)
            # 운송장 번호 기준 중복 제거 후 박스호수별 카운트
            df_dedup = df.drop_duplicates(subset=['운송장번호(박스기준)'])
            pivot_counts = df_dedup['박스호수(실제)'].value_counts().to_dict()
            
            date_str = file_date.strftime("%Y-%m-%d")
            st.session_state.usage_history[date_str] = pivot_counts
            
            # 실사용량 자동 갱신
            stock_data = st.session_state.stock_data
            for idx, row in stock_data.iterrows():
                key = row["excel_key"]
                stock_data.at[idx, "전일실사용량"] = pivot_counts.get(key, 0)
            st.session_state.stock_data = stock_data
            st.success(f"{date_str} 데이터 반영 완료!")
        except Exception as e:
            st.error(f"오류: {e}")

# 3. 나머지는 이전과 동일하게 유지
# ... (이후 코드는 동일하므로 생략)
