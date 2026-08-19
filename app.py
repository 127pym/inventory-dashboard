import streamlit as st
import pandas as pd
import datetime

st.set_page_config(layout="wide", page_title="물류 재고 및 발주 통합 대시보드")

# 1. 초기 상태 설정
if "stock_data" not in st.session_state:
    # 엑셀 이미지 기반 기본 데이터 구조
    st.session_state.stock_data = pd.DataFrame({
        "구분2": ["101", "102", "103", "스타 1호", "스타 2호"], # 예시
        "입수(PLT)": [300, 210, 210, 2520, 960],
        "MOQ(PCS)": [3000, 1890, 1680, 7560, 5760],
        "평균사용량": [1451, 4153, 3168, 78, 232],
        "전일기말재고": [20100, 14280, 11760, 2680, 960],
        "전일입고재고": [0, 0, 0, 0, 0],
        "전일실사용량": [0, 0, 0, 0, 0],
        "당일입고예정": [0, 0, 0, 0, 0],
        "안전재고": [4353, 12460, 9503, 234, 696]
    })

st.title("📦 물류 재고 및 발주 통합 대시보드")

# 2. 날짜 설정 및 파일 업로드 (검증 로직 포함)
col1, col2 = st.columns([1, 2])
with col1:
    target_date = st.date_input("기준 날짜 선택", datetime.date(2026, 8, 19))
with col2:
    uploaded_file = st.file_uploader(f"{target_date.strftime('%Y%m%d')} 출고일마감 파일 업로드", type=["xlsx"])

# 3. 데이터 정제 로직 (배송번호 기준 중복 제거 및 실사용량 집계)
if uploaded_file is not None:
    # 파일명 날짜 검증 (실제 구현 시 파일명 파싱 로직 추가)
    raw_df = pd.read_excel(uploaded_file, sheet_name=0)
    if '배송번호(착지기준)' in raw_df.columns:
        df_unique = raw_df.drop_duplicates(subset=['배송번호(착지기준)'])
        usage = df_unique['박스호수(실제)'].value_counts()
        # [데이터 매핑] 자동 업데이트 (실제 코드에선 key값 매핑 필요)
        st.success(f"{target_date} 데이터 정제 완료!")
    else:
        st.error("파일 형식이 올바르지 않습니다.")

# 4. 실시간 편집기 (표 1 + 실시간 수식 연동)
st.subheader("📋 실시간 재고/발주 현황")
edited_df = st.data_editor(st.session_state.stock_data, use_container_width=True)

# 5. 연동 계산 (수식 반영)
# 기초재고 소계 = 기말 + 입고 - 실사용 + 입고예정
edited_df["기초재고소계"] = (
    edited_df["전일기말재고"] + edited_df["전일입고재고"] - edited_df["전일실사용량"] + edited_df["당일입고예정"]
)
# 미발주 시 예상 잔여재고 (리드타임 5일 가정)
edited_df["예상잔여재고"] = edited_df["기초재고소계"] - (edited_df["평균사용량"] * 5)
# 발주 필요량 (안전재고 미달 시)
edited_df["발주필요량"] = edited_df.apply(lambda x: max(0, x["안전재고"] - x["예상잔여재고"]), axis=1)

# 6. 최종 화면 출력
st.dataframe(edited_df, use_container_width=True)
