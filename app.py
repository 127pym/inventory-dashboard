import streamlit as st
import pandas as pd
import datetime

st.set_page_config(layout="wide", page_title="물류 재고 및 발주 통합 대시보드")

# 1. 초기 데이터
if "stock_data" not in st.session_state:
    st.session_state.stock_data = pd.DataFrame({
        "구분2": ["101", "102", "103", "스타 13호(양곡20kg)", "스타 1호", "스타 2호", "스타 3호", "스타 4호", "스타 5호", "스타 6호", "스타 7호", "스타 8호", "스타 11호"],
        "excel_key": ["I-01", "I-02", "I-03", "C-13", "C-01", "C-02", "C-03", "C-04", "C-05", "C-06", "C-07", "C-08", "C-11"],
        "입수(PLT)": [300, 210, 210, 320, 2520, 960, 640, 640, 640, 320, 320, 320, 160],
        "MOQ_PCS": [3000, 1890, 1680, 2240, 7560, 5760, 3840, 3840, 3200, 1920, 1600, 1600, 1280],
        "전일기말재고": [20100, 14280, 11760, 320, 2680, 960, 1920, 4160, 3200, 3040, 2080, 800, 160],
        "전일실사용량": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    })

if "inbound_schedule" not in st.session_state:
    st.session_state.inbound_schedule = pd.DataFrame(columns=["날짜", "품목코드", "입고예정량"])
    
if "usage_history" not in st.session_state: st.session_state.usage_history = {}
if "calculated_result" not in st.session_state: st.session_state.calculated_result = None

st.title("📦 물류 재고 및 발주 통합 대시보드")

# 2. 날짜 설정
col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
with col1: order_date = st.date_input("발주 대상일", datetime.date(2026, 8, 19))
with col2: delivery_date = st.date_input("입고 예정일", datetime.date(2026, 8, 25))
with col3: avg_days = st.number_input("평균 산출 기간(일)", 1, 30, 10)
with col4: uploaded_file = st.file_uploader("출고일마감 업로드", type=["xlsx", "xls"])

lead_time_days = max(0, (delivery_date - order_date).days)

# 3. 입고 계획표 입력
st.subheader("🗓️ 입고 예정 물량 계획표 (기간 내 자동 합산)")
st.session_state.inbound_schedule = st.data_editor(st.session_state.inbound_schedule, num_rows="dynamic", use_container_width=True)

# 4. 파일 처리 및 평균 산출 (기존 로직 동일)
if uploaded_file is not None:
    raw_df = pd.read_excel(uploaded_file)
    df_dedup = raw_df.drop_duplicates(subset=['운송장번호(박스기준)'])
    pivot = df_dedup['박스호수(실제)'].value_counts().to_dict()
    for idx, row in st.session_state.stock_data.iterrows():
        st.session_state.stock_data.at[idx, "전일실사용량"] = pivot.get(row["excel_key"], 0)

# 5. 계산 실행 (입고계획표에서 날짜 내 물량 합산)
if st.button("🚀 계산 실행", type="primary", use_container_width=True):
    # 날짜 범위 내 물량 합산
    inbound_df = st.session_state.inbound_schedule.copy()
    inbound_df["날짜"] = pd.to_datetime(inbound_df["날짜"]).dt.date
    mask = (inbound_df["날짜"] >= order_date) & (inbound_df["날짜"] <= delivery_date)
    period_inbound = inbound_df[mask].groupby("품목코드")["입고예정량"].sum()
    
    res_df = st.session_state.stock_data.copy()
    # 입고 예정량 매핑
    res_df["입고합계"] = res_df["excel_key"].map(period_inbound).fillna(0)
    
    # 계산
    res_df["안전재고"] = res_df["평균사용량"] * lead_time_days
    res_df["기초재고소계"] = res_df["전일기말재고"] - res_df["전일실사용량"] + res_df["입고합계"]
    res_df["예상잔여재고"] = res_df["기초재고소계"] - res_df["안전재고"]
    res_df["발주필요량"] = res_df.apply(lambda x: max(0, x["안전재고"] - x["예상잔여재고"]), axis=1)
    st.session_state.calculated_result = res_df

# 6. 결과
if st.session_state.calculated_result is not None:
    st.dataframe(st.session_state.calculated_result[["구분2", "입수(PLT)", "평균사용량", "안전재고", "기초재고소계", "예상잔여재고", "발주필요량"]], use_container_width=True)
