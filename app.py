import streamlit as st
import pandas as pd
import datetime

st.set_page_config(layout="wide", page_title="물류 재고 및 발주 통합 대시보드")

# 품목 리스트 및 데이터 설정 (순서 고정)
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
        "전일기말재고": [20100, 14280, 11760, 320, 2680, 960, 1920, 4160, 3200, 3040, 2080, 800, 160],
        "전일실사용량": [0] * len(ITEM_LIST)
    })

if "inbound_schedule" not in st.session_state:
    st.session_state.inbound_schedule = pd.DataFrame(columns=["날짜", "품목코드", "입고예정량"])

# 1. 사이드바: 달력 및 입고량 입력 (시각적 선택)
with st.sidebar:
    st.subheader("📅 입고 물량 추가")
    sel_date = st.date_input("입고 예정일 선택", datetime.date.today())
    sel_item = st.selectbox("품목 선택", options=[i[1] for i in ITEM_LIST])
    sel_qty = st.number_input("입고 수량", min_value=0, step=10)
    if st.button("➕ 입고 일정에 추가"):
        new_row = {"날짜": sel_date, "품목코드": sel_item, "입고예정량": sel_qty}
        st.session_state.inbound_schedule = pd.concat([st.session_state.inbound_schedule, pd.DataFrame([new_row])], ignore_index=True)

st.title("📦 물류 재고 및 발주 통합 대시보드")

# 2. 메인: 입고 계획표 확인 및 수정
st.subheader("🗓️ 현재 등록된 입고 예정 일정")
st.session_state.inbound_schedule = st.data_editor(st.session_state.inbound_schedule, use_container_width=True)

# 3. 계산 로직
col1, col2 = st.columns(2)
with col1: order_date = st.date_input("발주 대상일", datetime.date(2026, 8, 19))
with col2: delivery_date = st.date_input("입고 예정일", datetime.date(2026, 8, 25))

if st.button("🚀 계산 실행", type="primary"):
    # 선택 기간 내 입고 물량 합산
    inbound_df = st.session_state.inbound_schedule.copy()
    inbound_df["날짜"] = pd.to_datetime(inbound_df["날짜"]).dt.date
    mask = (inbound_df["날짜"] >= order_date) & (inbound_df["날짜"] <= delivery_date)
    period_inbound = inbound_df[mask].groupby("품목코드")["입고예정량"].sum()
    
    res = st.session_state.stock_data.copy()
    res["입고합계"] = res["excel_key"].map(period_inbound).fillna(0)
    # 계산 (안전재고는 임의로 평균사용량*5일 가정)
    res["발주필요량"] = (res["전일실사용량"] * 5 - (res["전일기말재고"] - res["전일실사용량"] + res["입고합계"])).clip(lower=0)
    
    st.dataframe(res, use_container_width=True)
