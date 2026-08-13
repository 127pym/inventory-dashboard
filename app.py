import streamlit as st
import pandas as pd
import io

st.set_page_config(layout="wide", page_title="물류 재고 관리 대시보드")

st.title("📋 1. 재고 및 평균 사용량 현황 (배송번호 기준 자동 집계)")

# --- [기본 품목 및 매핑 정의] ---
items_mapping = [
    {"구분1": "저온", "구분2": "101", "excel_key": "I-01", "입수": 300},
    {"구분1": "저온", "구분2": "102", "excel_key": "I-02", "입수": 210},
    {"구분1": "저온", "구분2": "103", "excel_key": "I-03", "입수": 210},
    {"구분1": "상온", "구분2": "스타 13호(양곡20kg)", "excel_key": "C-13", "입수": 320},
    {"구분1": "상온", "구분2": "스타 1호", "excel_key": "C-01", "입수": 2520},
    {"구분1": "상온", "구분2": "스타 2호", "excel_key": "C-02", "입수": 960},
    {"구분1": "상온", "구분2": "스타 3호", "excel_key": "C-03", "입수": 640},
    {"구분1": "상온", "구분2": "스타 4호", "excel_key": "C-04", "입수": 640},
    {"구분1": "상온", "구분2": "스타 5호", "excel_key": "C-05", "입수": 640},
    {"구분1": "상온", "구분2": "스타 6호", "excel_key": "C-06", "입수": 320},
    {"구분1": "상온", "구분2": "스타 7호", "excel_key": "C-07", "입수": 320},
    {"구분1": "상온", "구분2": "스타 8호", "excel_key": "C-08", "입수": 320},
    {"구분1": "상온", "구분2": "스타 11호", "excel_key": "C-11", "입수": 160},
]

items_df_base = pd.DataFrame(items_mapping)
items_list = items_df_base["구분2"].tolist()

# --- [세션 상태: 실사용량 데이터 관리] ---
if "stock_inputs" not in st.session_state:
    st.session_state.stock_inputs = pd.DataFrame({
        "구분2": items_list,
        "전일기말재고": [0]*len(items_list),
        "전일입고재고": [0]*len(items_list),
        "전일실사용량": [0]*len(items_list),
        "당일입고예정": [0]*len(items_list)
    })

# --- [파일 업로드 및 배송번호 기준 집계 로직] ---
st.markdown("---")
st.subheader("📁 출고일마감 목록 엑셀 업로드")
uploaded_file = st.file_uploader("파일 업로드 시 '전일실사용량'이 자동 반영됩니다.", type=["xlsx", "xls"])

if uploaded_file is not None:
    try:
        raw_df = pd.read_excel(uploaded_file, sheet_name=0)
        
        # 배송번호 기준 중복 제거 및 박스 사용량 집계
        if '배송번호(착지기준)' in raw_df.columns and '박스호수(실제)' in raw_df.columns:
            df_unique = raw_df.drop_duplicates(subset=['배송번호(착지기준)'])
            daily_usage = df_unique['박스호수(실제)'].value_counts().to_dict()
            
            # 전일실사용량 업데이트 (세션 상태 반영)
            stock_inputs = st.session_state.stock_inputs
            for i, row in stock_inputs.iterrows():
                key = items_mapping[i]["excel_key"]
                stock_inputs.at[i, "전일실사용량"] = daily_usage.get(key, 0)
            
            st.session_state.stock_inputs = stock_inputs
            st.success("✅ 주문 건수(배송번호) 기준 중복 제거 및 일일 박스 사용량이 성공적으로 집계되었습니다!")
        else:
            st.error("❌ 파일에 필요한 컬럼('배송번호(착지기준)', '박스호수(실제)')이 없습니다.")
    except Exception as e:
        st.error(f"오류: {e}")

# --- [대시보드 UI 및 결과 계산] ---
st.markdown("---")
st.subheader("📋 1. 재고 및 실사용량 현황")

merged_base = pd.merge(items_df_base, st.session_state.stock_inputs, on="구분2", how="left")

# 데이터 편집기
edited_table1 = st.data_editor(
    merged_base,
    column_config={"구분1": st.column_config.TextColumn(disabled=True), "구분2": st.column_config.TextColumn(disabled=True), "excel_key": st.column_config.TextColumn(disabled=True)},
    hide_index=True,
    use_container_width=True
)

st.session_state.stock_inputs = edited_table1

# 최종 계산
result_df = edited_table1.copy()
result_df["당일기초재고 소계"] = (result_df["전일기말재고"] + result_df["전일입고재고"] - result_df["전일실사용량"] + result_df["당일입고예정"])

st.write("### 최종 재고 요약")
st.dataframe(result_df[["구분2", "전일실사용량", "당일기초재고 소계"]], hide_index=True, use_container_width=True)
