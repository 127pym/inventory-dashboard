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
        "평균사용량": [1451, 4153, 3168, 103, 78, 232, 441, 589, 877, 895, 8, 88, 20],
        "전일기말재고": [20100, 14280, 11760, 320, 2680, 960, 1920, 4160, 3200, 3040, 2080, 800, 160],
        "전일입고재고": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "전일실사용량": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "당일입고예정": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    })

st.title("📦 물류 재고 및 발주 통합 대시보드")

# 2. 날짜 설정 (발주대상일 / 입고예정일 분리) 및 파일 업로드
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    order_date = st.date_input("발주 대상일", datetime.date(2026, 8, 24))
with col2:
    delivery_date = st.date_input("입고 예정일", datetime.date(2026, 8, 19))
with col3:
    uploaded_file = st.file_uploader("출고일마감 파일 업로드 (실사용량 자동 반영)", type=["xlsx", "xls"])

# 날짜 차이(일수) 계산 (안전재고 산출용: 발주대상일 - 입고예정일)
lead_time_days = max(0, (order_date - delivery_date).days)
st.info(f"📅 **설정된 리드타임 일수 (발주대상일 - 입고예정일):** {lead_time_days}일")

# 3. 데이터 정제 로직 (배송번호 기준 중복 제거 및 실사용량 자동 매핑)
if uploaded_file is not None:
    try:
        raw_df = pd.read_excel(uploaded_file, sheet_name=0)
        if '배송번호(착지기준)' in raw_df.columns and '박스호수(실제)' in raw_df.columns:
            df_unique = raw_df.drop_duplicates(subset=['배송번호(착지기준)'])
            daily_usage = df_unique['박스호수(실제)'].value_counts().to_dict()
            
            stock_data = st.session_state.stock_data
            for idx, row in stock_data.iterrows():
                key = row["excel_key"]
                stock_data.at[idx, "전일실사용량"] = daily_usage.get(key, 0)
                
            st.session_state.stock_data = stock_data
            st.success("✅ 출고일마감 파일의 실사용량이 성공적으로 반영되었습니다!")
        else:
            st.error("❌ 파일에 필요한 컬럼('배송번호(착지기준)', '박스호수(실제)')이 없습니다.")
    except Exception as e:
        st.error(f"파일 처리 중 오류 발생: {e}")

# 4. 연동 계산 수식 적용 (안전재고를 여기서 먼저 계산)
display_df = st.session_state.stock_data.copy()

# 안전재고 = 평균사용량 × (발주대상일 - 입고예정일)
display_df["안전재고"] = display_df["평균사용량"] * lead_time_days

# 기초재고 소계 = 기말 + 입고 - 실사용 + 입고예정
display_df["기초재고소계"] = (
    display_df["전일기말재고"] + display_df["전일입고재고"] - display_df["전일실사용량"] + display_df["당일입고예정"]
)

# 예상 잔여재고 = 기초재고소계 - 안전재고
display_df["예상잔여재고"] = display_df["기초재고소계"] - display_df["안전재고"]

# 발주 필요량 산출 (안전재고 미달 시)
display_df["발주필요량"] = display_df.apply(lambda x: max(0, x["안전재고"] - x["예상잔여재고"]), axis=1)

# 5. 실시간 편집기 (키인 및 Ctrl+C/V 가능)
st.subheader("📋 실시간 재고/발주 현황 (수정 및 붙여넣기 가능)")
st.info("💡 '전일기말재고', '전일입고재고', '당일입고예정' 등의 셀을 더블클릭하여 직접 입력하거나, 엑셀 표를 복사(Ctrl+C)한 뒤 첫 셀에 붙여넣기(Ctrl+V)할 수 있습니다.")

edited_df = st.data_editor(
    display_df, 
    column_config={
        "구분2": st.column_config.TextColumn(disabled=True),
        "excel_key": st.column_config.TextColumn("RAW코드", disabled=True),
        "입수(PLT)": st.column_config.NumberColumn(disabled=True),
        "MOQ_PCS": st.column_config.NumberColumn(disabled=True),
        "평균사용량": st.column_config.NumberColumn(disabled=True),
        "안전재고": st.column_config.NumberColumn(disabled=True),
        "기초재고소계": st.column_config.NumberColumn(disabled=True),
        "예상잔여재고": st.column_config.NumberColumn(disabled=True),
        "발주필요량": st.column_config.NumberColumn(disabled=True),
    },
    num_rows="fixed",
    use_container_width=True,
    hide_index=True,
    key="main_editor"
)

# 사용자가 수정한 재고 값들을 다시 세션에 반영
for idx in range(len(st.session_state.stock_data)):
    st.session_state.stock_data.at[idx, "전일기말재고"] = edited_df.at[idx, "전일기말재고"]
    st.session_state.stock_data.at[idx, "전일입고재고"] = edited_df.at[idx, "전일입고재고"]
    st.session_state.stock_data.at[idx, "전일실사용량"] = edited_df.at[idx, "전일실사용량"]
    st.session_state.stock_data.at[idx, "당일입고예정"] = edited_df.at[idx, "당일입고예정"]

# 6. 최종 결과 요약 출력
st.subheader("📊 최종 계산 및 발주 요약")
st.dataframe(
    edited_df[["구분2", "입수(PLT)", "평균사용량", "안전재고", "기초재고소계", "예상잔여재고", "발주필요량"]], 
    use_container_width=True, 
    hide_index=True
)
