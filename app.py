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
        "전일실사용량": [0] * len(ITEM_LIST),
        "평균사용량": [0.0] * len(ITEM_LIST)
    })

if "calculated_result" not in st.session_state: st.session_state.calculated_result = None

st.title("📦 물류 재고 및 발주 통합 대시보드")

# --- [고정 틀 2: 날짜 및 파일 업로드 + 안전재고 마진율 설정 추가] ---
today = datetime.date(2026, 8, 19)
col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
with col1: order_date = st.date_input("발주 대상일", today)
with col2: delivery_date = st.date_input("입고 예정일", today + datetime.timedelta(days=6))
with col3: avg_days = st.number_input("평균 산출 기간(일)", 1, 30, 10)
# 점장님 요청 반영: 안전재고 대비 여유 마진율 (예: 1.1배 = 110%, 1.2배 = 120% 이하면 미리 발주)
with col4: safety_margin = st.number_input("안전재고 마진율", 1.0, 1.5, 1.1, step=0.05, help="1.1 = 안전재고의 110% 수준일 때 미리 발주 추천")
with col5: uploaded_file = st.file_uploader("출고일마감 파일 업로드", type=["xlsx", "xls"])

# --- [고정 틀 3: 실시간 데이터 편집기] ---
st.subheader("📋 재고 및 입고량 입력 (엑셀 복사/붙여넣기 가능)")
edited_df = st.data_editor(st.session_state.stock_data, num_rows="fixed", use_container_width=True, hide_index=True)

# --- [고정 틀 4: 계산 실행 버튼] ---
if st.button("🚀 계산 실행", type="primary", use_container_width=True):
    with st.spinner("⚙️ 파일 분석 및 계산 중..."):
        res = edited_df.copy()
        
        # 파일 업로드 처리
        if uploaded_file is not None:
            try:
                uploaded_file.seek(0)
                df = pd.read_excel(uploaded_file)
                if '운송장번호(박스기준)' in df.columns and '박스호수(실제)' in df.columns:
                    pivot = df.drop_duplicates(subset=['운송장번호(박스기준)'])['박스호수(실제)'].value_counts()
                    for idx, row in res.iterrows():
                        res.at[idx, "전일실사용량"] = pivot.get(row["excel_key"], 0)
            except Exception as e:
                st.error(f"❌ 파일 분석 실패: {e}")
        
        res["평균사용량"] = res["전일실사용량"] 
        
        # 리드타임 (발주 대상일 포함)
        lead_time = max(0, (delivery_date - order_date).days) + 1
        
        # 기본 안전재고 * 마진율 적용 (예: 110% 또는 120%)
        res["안전재고"] = (res["평균사용량"] * lead_time) * safety_margin
        
        # 기초재고소계
        res["기초재고소계"] = res["전일기말재고"] - res["전일실사용량"] + res["입고예정량"]
        
        # 예상 재고 잔여량 (기초재고소계 - 안전재고)
        res["예상잔여재고"] = res["기초재고소계"] - res["안전재고"]
        
        # 발주필요량
        res["발주필요량"] = res.apply(lambda x: max(0, x["안전재고"] - x["기초재고소계"]), axis=1)
        
        st.session_state.calculated_result = res

# --- [고정 틀 5: 계산 결과 고정 영역 (주력 박스 연한 노란색 음영 스타일링 적용)] ---
st.markdown("---")
st.subheader("📊 최종 계산 및 발주 요약")

if st.session_state.calculated_result is not None:
    display_df = st.session_state.calculated_result[["excel_key", "구분2", "입수(PLT)", "전일실사용량", "평균사용량", "안전재고", "기초재고소계", "예상잔여재고", "발주필요량"]]

    # 주력 박스로 지정할 excel_key 리스트 (I-01, I-02, I-03, 스타 4호(C-04), 5호(C-05), 6호(C-06))
    main_items = ["I-01", "I-02", "I-03", "C-04", "C-05", "C-06"]

    def highlight_main_items(row):
        if row["excel_key"] in main_items:
            return ['background-color: #FFF9C4'] * len(row)
        return [''] * len(row)

    styled_df = display_df.style.apply(highlight_main_items, axis=1).hide(subset=["excel_key"], axis=1)

    st.dataframe(styled_df, use_container_width=True, hide_index=True)
else:
    st.info("ℹ️ 데이터를 입력하고 [계산 실행] 버튼을 누르면 여기에 결과가 표시됩니다.")
