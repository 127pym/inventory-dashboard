import streamlit as st
import pandas as pd
import datetime

st.set_page_config(layout="wide", page_title="물류 재고 및 발주 통합 대시보드")

# 1. 컬럼 구조 명확히 정의
COL_ORDER = ["구분2", "excel_key", "입수(PLT)", "MOQ_PCS", "전일기말재고", "입고예정수량(기간합계)", "전일실사용량"]

if "stock_data" not in st.session_state:
    st.session_state.stock_data = pd.DataFrame({
        "구분2": ["101", "102", "103", "스타 13호(양곡20kg)", "스타 1호", "스타 2호", "스타 3호", "스타 4호", "스타 5호", "스타 6호", "스타 7호", "스타 8호", "스타 11호"],
        "excel_key": ["I-01", "I-02", "I-03", "C-13", "C-01", "C-02", "C-03", "C-04", "C-05", "C-06", "C-07", "C-08", "C-11"],
        "입수(PLT)": [300, 210, 210, 320, 2520, 960, 640, 640, 640, 320, 320, 320, 160],
        "MOQ_PCS": [3000, 1890, 1680, 2240, 7560, 5760, 3840, 3840, 3200, 1920, 1600, 1600, 1280],
        "전일기말재고": [20100, 14280, 11760, 320, 2680, 960, 1920, 4160, 3200, 3040, 2080, 800, 160],
        "입고예정수량(기간합계)": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "전일실사용량": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    })

if "usage_history" not in st.session_state: st.session_state.usage_history = {}
if "calculated_result" not in st.session_state: st.session_state.calculated_result = None

st.title("📦 물류 재고 및 발주 통합 대시보드")

# 2. 날짜 및 파일 처리
c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
with c1: order_date = st.date_input("발주 대상일", datetime.date(2026, 8, 19))
with c2: delivery_date = st.date_input("입고 예정일", datetime.date(2026, 8, 25))
with c3: avg_days = st.number_input("평균 산출 기간(일)", 1, 30, 10)
with c4:
    file_date = st.date_input("업로드 기준 날짜", datetime.date.today())
    uploaded_file = st.file_uploader("출고일마감 파일 업로드", type=["xlsx", "xls"])

lead_time_days = max(0, (delivery_date - order_date).days)

if uploaded_file is not None:
    try:
        raw_df = pd.read_excel(uploaded_file)
        if '운송장번호(박스기준)' in raw_df.columns and '박스호수(실제)' in raw_df.columns:
            df_dedup = raw_df.drop_duplicates(subset=['운송장번호(박스기준)'])
            pivot_counts = df_dedup['박스호수(실제)'].value_counts().to_dict()
            st.session_state.usage_history[file_date.strftime("%Y-%m-%d")] = pivot_counts
            for idx, row in st.session_state.stock_data.iterrows():
                st.session_state.stock_data.at[idx, "전일실사용량"] = pivot_counts.get(row["excel_key"], 0)
            st.success("✅ 집계 완료!")
    except Exception as e: st.error(f"오류: {e}")

# 3. 평균 계산
def get_avg():
    if not st.session_state.usage_history: return [0] * len(st.session_state.stock_data)
    dts = sorted(st.session_state.usage_history.keys(), reverse=True)[:int(avg_days)]
    res = []
    for key in st.session_state.stock_data["excel_key"]:
        vals = [st.session_state.usage_history[d].get(key, 0) for d in dts]
        res.append(round(sum(vals)/len(vals), 1))
    return res

st.session_state.stock_data["평균사용량"] = get_avg()

# 4. 에디터 (입고예정수량(기간합계) 명칭 고정)
edited_df = st.data_editor(st.session_state.stock_data, num_rows="fixed", use_container_width=True, hide_index=True)

# 5. 계산 실행 (컬럼명 명시적 호출)
if st.button("🚀 계산 실행", type="primary", use_container_width=True):
    with st.spinner("⚙️ 계산 중..."):
        try:
            res_df = edited_df.copy()
            res_df["안전재고"] = res_df["평균사용량"] * lead_time_days
            # 정확한 컬럼명 호출
            res_df["기초재고소계"] = res_df["전일기말재고"] - res_df["전일실사용량"] + res_df["입고예정수량(기간합계)"]
            res_df["예상잔여재고"] = res_df["기초재고소계"] - res_df["안전재고"]
            res_df["발주필요량"] = res_df.apply(lambda x: max(0, x["안전재고"] - x["예상잔여재고"]), axis=1)
            st.session_state.calculated_result = res_df
        except Exception as e:
            st.error(f"계산 오류: {e}. 컬럼명이 일치하는지 확인하세요.")

# 6. 결과
if st.session_state.calculated_result is not None:
    st.dataframe(st.session_state.calculated_result[["구분2", "입수(PLT)", "평균사용량", "안전재고", "기초재고소계", "예상잔여재고", "발주필요량"]], use_container_width=True, hide_index=True)
