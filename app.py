import streamlit as st
import pandas as pd
import datetime
import os

st.set_page_config(layout="wide", page_title="물류 재고 및 발주 통합 대시보드 (영구 저장형)")

DATA_FILE = "inventory_master_data.csv"

# --- [고정 틀 1: 품목 데이터 및 영구 저장소 로드 구조] ---
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
        "입고예정량": [0] * len(ITEM_LIST),
        "전일실사용량": [0] * len(ITEM_LIST),
        "누적평균사용량": [0.0] * len(ITEM_LIST),
        "데이터반영일수": [0] * len(ITEM_LIST)
    })
    st.session_state.stock_data.to_csv(DATA_FILE, index=False)

if "calculated_result" not in st.session_state: 
    st.session_state.calculated_result = None

st.title("📦 물류 재고 및 발주 통합 대시보드 (영구 저장 및 정수 처리)")

# --- [고정 틀 2: 날짜 및 파일 업로드] ---
today = datetime.date(2026, 8, 19)
col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
with col1: order_date = st.date_input("발주 대상일", today)
with col2: delivery_date = st.date_input("입고 예정일", today + datetime.timedelta(days=6))
with col3: avg_days = st.number_input("평균 산출 기간(일)", 1, 30, 10)
with col4: uploaded_file = st.file_uploader("출고일마감 파일 업로드", type=["xlsx", "xls"])

weekday_kr = ['월', '화', '수', '목', '금', '토', '일']
current_weekday = order_date.weekday()
st.info(f"📅 발주 대상일: **{weekday_kr[current_weekday]}요일** | 소수점 없는 깔끔한 정수형 발주 계산 시스템 작동 중")

# --- [고정 틀 3: 실시간 데이터 편집기] ---
st.subheader("📋 재고 및 누적 데이터 입력 (새로고침해도 데이터 유지)")
edited_df = st.data_editor(st.session_state.stock_data, num_rows="fixed", use_container_width=True, hide_index=True)

# --- [고정 틀 4: 계산 실행 버튼] ---
if st.button("🚀 계산 실행 및 데이터 저장", type="primary", use_container_width=True):
    with st.spinner("⚙️ 데이터 분석 및 정수 변환 중..."):
        res = edited_df.copy()
        
        file_usages = {}
        if uploaded_file is not None:
            try:
                uploaded_file.seek(0)
                df = pd.read_excel(uploaded_file)
                if '운송장번호(박스기준)' in df.columns and '박스호수(실제)' in df.columns:
                    pivot = df.drop_duplicates(subset=['운송장번호(박스기준)'])['박스호수(실제)'].value_counts()
                    for idx, row in res.iterrows():
                        file_usages[row["excel_key"]] = pivot.get(row["excel_key"], 0)
            except Exception as e:
                st.error(f"❌ 파일 분석 실패: {e}")
        
        # 누적 평균 계산
        for idx, row in res.iterrows():
            key = row["excel_key"]
            today_use = file_usages.get(key, row["전일실사용량"])
            res.at[idx, "전일실사용량"] = int(today_use)
            
            old_avg = row["누적평균사용량"]
            days = row["데이터반영일수"]
            
            if days == 0 or old_avg == 0:
                new_avg = float(today_use)
                new_days = 1
            else:
                new_avg = (old_avg * 0.8) + (today_use * 0.2)
                new_days = days + 1
                
            res.at[idx, "누적평균사용량"] = round(new_avg, 1)
            res.at[idx, "데이터반영일수"] = new_days

        # 안전재고 산출 및 정수형(int)으로 반올림 처리
        lead_time = max(0, (delivery_date - order_date).days) + 1
        
        def get_dynamic_margin(excel_key, weekday):
            if excel_key in ["I-01", "I-02", "I-03"]:
                if weekday in [3, 4]: return 1.25 
                elif weekday == 0:     return 1.15 
                else:                  return 1.10
            return 1.0

        safety_stocks = []
        for idx, row in res.iterrows():
            margin = get_dynamic_margin(row["excel_key"], current_weekday)
            base_safety = row["누적평균사용량"] * lead_time
            safety_stocks.append(int(round(base_safety * margin))) # 소수점 제거를 위해 반올림 후 int 변환
            
        res["안전재고"] = safety_stocks
        res["기초재고소계"] = res["전일기말재고"] - res["전일실사용량"] + res["입고예정량"]
        res["예상잔여재고"] = res["기초재고소계"] - res["안전재고"]
        res["발주필요량"] = res.apply(lambda x: max(0, int(x["안전재고"] - x["기초재고소계"])), axis=1)
        
        # 누적평균사용량도 보기 좋게 반올림 정수로 정돈
        res["누적평균사용량"] = res["누적평균사용량"].round().astype(int)

        st.session_state.stock_data = res
        res.to_csv(DATA_FILE, index=False)
        
        st.session_state.calculated_result = res
        st.success("✅ 계산이 완료되었으며, 소수점이 제거된 정수 데이터로 저장되었습니다!")

# --- [고정 틀 5: 계산 결과 고정 영역] ---
st.markdown("---")
st.subheader("📊 최종 계산 및 발주 요약 (깔끔한 정수형 출력)")

if st.session_state.calculated_result is not None:
    display_df = st.session_state.calculated_result[["excel_key", "구분2", "입수(PLT)", "전일실사용량", "누적평균사용량", "안전재고", "기초재고소계", "예상잔여재고", "발주필요량"]]

    main_items = ["I-01", "I-02", "I-03", "C-04", "C-05", "C-06"]

    def highlight_main_items(row):
        if row["excel_key"] in main_items:
            return ['background-color: #FFF9C4'] * len(row)
        return [''] * len(row)

    styled_df = display_df.style.apply(highlight_main_items, axis=1).hide(subset=["excel_key"], axis=1)

    st.dataframe(styled_df, use_container_width=True, hide_index=True)
else:
    st.info("ℹ️ 데이터를 입력하고 [계산 실행 및 데이터 저장] 버튼을 누르면 결과가 표시됩니다.")
