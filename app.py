import streamlit as st
import pandas as pd
import datetime

st.set_page_config(layout="wide", page_title="물류 재고 및 발주 통합 대시보드")

# 품목 리스트 정의 (순서 고정)
ITEM_LIST = [
    ("101", "I-01"), ("102", "I-02"), ("103", "I-03"), 
    ("스타 13호(양곡20kg)", "C-13"), ("스타 1호", "C-01"), ("스타 2호", "C-02"), 
    ("스타 3호", "C-03"), ("스타 4호", "C-04"), ("스타 5호", "C-05"), 
    ("스타 6호", "C-06"), ("스타 7호", "C-07"), ("스타 8호", "C-08"), ("스타 11호", "C-11")
]

# 1. 초기 데이터 설정
if "stock_data" not in st.session_state:
    st.session_state.stock_data = pd.DataFrame({
        "구분2": [i[0] for i in ITEM_LIST],
        "excel_key": [i[1] for i in ITEM_LIST],
        "입수(PLT)": [300, 210, 210, 320, 2520, 960, 640, 640, 640, 320, 320, 320, 160],
        "MOQ_PCS": [3000, 1890, 1680, 2240, 7560, 5760, 3840, 3840, 3200, 1920, 1600, 1600, 1280],
        "전일기말재고": [20100, 14280, 11760, 320, 2680, 960, 1920, 4160, 3200, 3040, 2080, 800, 160],
        "전일실사용량": [0] * len(ITEM_LIST)
    })

if "inbound_schedule" not in st.session_state:
    st.session_state.inbound_schedule = pd.DataFrame(columns=["날짜", "품목코드", "입고예정량"])

# 정산 기간 계산
today = datetime.date.today()
start_date = datetime.date(today.year, today.month - 1, 26) if today.day >= 26 else datetime.date(today.year - 1 if today.month == 1 else today.year, (today.month - 2) % 12 + 1, 26)

st.title("📦 물류 재고 및 발주 통합 대시보드")
st.info(f"📅 **현재 정산 기간:** {start_date} ~ {today.replace(day=25) if today.day <= 25 else today.replace(month=today.month % 12 + 1, day=25)}")

# 2. 날짜 설정 및 파일 업로드
c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
with c1: order_date = st.date_input("발주 대상일", today)
with c2: delivery_date = st.date_input("입고 예정일", today + datetime.timedelta(days=6))
with c3: avg_days = st.number_input("평균 산출 기간(일)", 1, 30, 10)
with c4: uploaded_file = st.file_uploader("출고일마감 파일 업로드", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    pivot = df.drop_duplicates(subset=['운송장번호(박스기준)'])['박스호수(실제)'].value_counts()
    for idx, row in st.session_state.stock_data.iterrows():
        st.session_state.stock_data.at[idx, "전일실사용량"] = pivot.get(row["excel_key"], 0)

# 3. 입고 예정표
st.subheader("🗓️ 입고 예정 물량 계획표")
st.session_state.inbound_schedule = st.data_editor(st.session_state.inbound_schedule, num_rows="dynamic", use_container_width=True)

# 4. 실시간 편집기 (메인)
edited_df = st.data_editor(st.session_state.stock_data, num_rows="fixed", use_container_width=True, hide_index=True)

# 5. 계산 실행
if st.button("🚀 계산 실행", type="primary", use_container_width=True):
    inbound_df = st.session_state.inbound_schedule.copy()
    inbound_df["날짜"] = pd.to_datetime(inbound_df["날짜"]).dt.date
    mask = (inbound_df["날짜"] >= order_date) & (inbound_df["날짜"] <= delivery_date)
    period_inbound = inbound_df[mask].groupby("품목코드")["입고예정량"].sum()
    
    res = edited_df.copy()
    res["입고합계"] = res["excel_key"].map(period_inbound).fillna(0)
    # 안전재고는 이전 로직처럼 평균사용량 * 리드타임으로 계산
    res["안전재고"] = (res["전일실사용량"] / avg_days) * max(0, (delivery_date - order_date).days)
    res["기초재고소계"] = res["전일기말재고"] - res["전일실사용량"] + res["입고합계"]
    res["발주필요량"] = res.apply(lambda x: max(0, x["안전재고"] - (x["기초재고소계"] - x["안전재고"])), axis=1)
    
    st.dataframe(res, use_container_width=True)
