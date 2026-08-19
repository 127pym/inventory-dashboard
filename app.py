import streamlit as st
import pandas as pd
import datetime

st.set_page_config(layout="wide", page_title="물류 재고 및 발주 통합 대시보드")

# 1. 전체 품목 데이터 및 기본 구조 정의
if "stock_data" not in st.session_state:
    st.session_state.stock_data = pd.DataFrame({
        "구분2": [
            "101", "102", "103", 
            "스타 13호(양곡20kg)", "스타 1호", "스타 2호", "스타 3호", 
            "스타 4호", "스타 5호", "스타 6호", "스타 7호", "스타 8호", "스타 11호"
        ],
        "excel_key": [
            "I-01", "I-02", "I-03", 
            "C-13", "C-01", "C-02", "C-03", 
            "C-04", "C-05", "C-06", "C-07", "C-08", "C-11"
        ],
        "입수(PLT)": [300, 210, 210, 320, 2520, 960, 640, 640, 640, 320, 320, 320, 160],
        "MOQ_PCS": [3000, 1890, 1680, 2240, 7560, 5760, 3840, 3840, 3200, 1920, 1600, 1600, 1280],
        "전일기말재고": [20100, 14280, 11760, 320, 2680, 960, 1920, 4160, 3200, 3040, 2080, 800, 160],
        "전일입고재고": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "전일실사용량": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "당일입고예정": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    })

# 일자별 사용량 이력 저장 공간
if "usage_history" not in st.session_state:
    st.session_state.usage_history = {}

# 계산 결과 데이터프레임 초기화
if "calculated_result" not in st.session_state:
    st.session_state.calculated_result = None

st.title("📦 물류 재고 및 발주 통합 대시보드")

# 2. 날짜 설정 및 평균 기간 설정
col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
with col1:
    order_date = st.date_input("발주 대상일", datetime.date(2026, 8, 19))
with col2:
    delivery_date = st.date_input("입고 예정일", datetime.date(2026, 8, 24))
with col3:
    avg_days = st.number_input("평균 산출 기간(일)", min_value=1, max_value=30, value=10)
with col4:
    file_date = st.date_input("업로드할 파일의 기준 날짜", datetime.date(2026, 8, 18))
    uploaded_file = st.file_uploader("출고일마감 파일 업로드", type=["xlsx", "xls"])

# 리드타임 일수 계산 (입고예정일 - 발주대상일)
lead_time_days = max(0, (delivery_date - order_date).days)

# 3. 파일 업로드 시 피벗 집계 로직 (운송장 번호 기준 중복 제거)
if uploaded_file is not None:
    with st.spinner("🔄 출고일마감 파일을 분석하고 피벗 집계를 수행하는 중입니다..."):
        try:
            raw_df = pd.read_excel(uploaded_file, sheet_name=0)
            if '운송장번호(박스기준)' in raw_df.columns and '박스호수(실제)' in raw_df.columns:
                # [수정된 부분] 운송장 번호 기준 중복 제거 후 카운트
                df_dedup = raw_df.drop_duplicates(subset=['운송장번호(박스기준)'])
                pivot_counts = df_dedup['박스호수(실제)'].value_counts().to_dict()
                
                date_str = file_date.strftime("%Y-%m-%d")
                st.session_state.usage_history[date_str] = pivot_counts
                
                stock_data = st.session_state.stock_data
                for idx, row in stock_data.iterrows():
                    key = row["excel_key"]
                    stock_data.at[idx, "전일실사용량"] = pivot_counts.get(key, 0)
                st.session_state.stock_data = stock_data
                
                st.success(f"✅ [{date_str}] 피벗 집계 완료! 이력 누적됨")
            else:
                st.error("❌ 파일에 필요한 컬럼('운송장번호(박스기준)', '박스호수(실제)')이 없습니다.")
        except Exception as e:
            st.error(f"파일 처리 중 오류 발생: {e}")

# 4. 최근 N일 평균 사용량 자동 계산 로직
def calculate_recent_average(n_days):
    if not st.session_state.usage_history:
        return [1451, 4153, 3168, 103, 78, 232, 441, 589, 877, 895, 8, 88, 20]
    
    sorted_dates = sorted(st.session_state.usage_history.keys(), reverse=True)
    target_dates = sorted_dates[:n_days]
    
    averages = []
    keys = st.session_state.stock_data["excel_key"].tolist()
    
    for key in keys:
        values = []
        for d in target_dates:
            day_data = st.session_state.usage_history[d]
            values.append(day_data.get(key, 0))
        
        avg = sum(values) / len(values) if values else 0
        averages.append(round(avg, 1))
        
    return averages

current_avg_usage = calculate_recent_average(int(avg_days))
st.session_state.stock_data["평균사용량"] = current_avg_usage

st.info(f"📅 **설정 리드타임:** {lead_time_days}일 | 📈 **평균 산출 반영:** 최근 {min(len(st.session_state.usage_history), int(avg_days))}일간의 누적 데이터 기준")

# 5. 실시간 편집기
st.subheader("📋 재고 데이터 입력 및 수정")
edited_df = st.data_editor(
    st.session_state.stock_data, 
    column_config={
        "구분2": st.column_config.TextColumn(disabled=True),
        "excel_key": st.column_config.TextColumn("RAW코드", disabled=True),
        "입수(PLT)": st.column_config.NumberColumn(disabled=True),
        "MOQ_PCS": st.column_config.NumberColumn(disabled=True),
        "평균사용량": st.column_config.NumberColumn(disabled=True, help="누적 이력 기반 자동 계산됨"),
    },
    num_rows="fixed",
    use_container_width=True,
    hide_index=True,
    key="main_editor"
)

# 6. 계산 실행 버튼
st.markdown("---")
col_btn1, col_btn2 = st.columns([1, 4])
with col_btn1:
    calculate_clicked = st.button("🚀 계산 실행", type="primary", use_container_width=True)

if calculate_clicked:
    with st.spinner("⚙️ 발주 필요량을 계산하는 중입니다..."):
        st.session_state.stock_data = edited_df.copy()
        
        res_df = edited_df.copy()
        res_df["안전재고"] = res_df["평균사용량"] * lead_time_days
        res_df["기초재고소계"] = (
            res_df["전일기말재고"] + res_df["전일입고재고"] - res_df["전일실사용량"] + res_df["당일입고예정"]
        )
        res_df["예상잔여재고"] = res_df["기초재고소계"] - res_df["안전재고"]
        res_df["발주필요량"] = res_df.apply(lambda x: max(0, x["안전재고"] - x["예상잔여재고"]), axis=1)
        
        st.session_state.calculated_result = res_df

# 7. 결과 출력 영역
st.subheader("📊 최종 계산 및 발주 요약")
if st.session_state.calculated_result is not None:
    st.dataframe(
        st.session_state.calculated_result[["구분2", "입수(PLT)", "평균사용량", "안전재고", "기초재고소계", "예상잔여재고", "발주필요량"]], 
        use_container_width=True, 
        hide_index=True
    )
else:
    st.info("ℹ️ 위의 데이터를 확인하고 [계산 실행] 버튼을 누르면 최종 요약 결과가 여기에 표시됩니다.")
