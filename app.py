import streamlit as st
import pandas as pd
import io

st.set_page_config(layout="wide", page_title="물류 재고 관리 대시보드")

st.title("📋 1. 재고 및 평균 사용량 현황 (대용량 엑셀 대응)")

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

if "calculated_avg_series" not in st.session_state:
    st.session_state.calculated_avg_series = pd.Series([0]*len(items_list), index=items_list)

if "stock_inputs" not in st.session_state:
    st.session_state.stock_inputs = pd.DataFrame({
        "구분2": items_list,
        "전일기말재고": [0]*len(items_list),
        "전일입고재고": [0]*len(items_list),
        "전일실사용량": [0]*len(items_list),
        "당일입고예정": [0]*len(items_list)
    })

st.markdown("---")
st.subheader("📁 전일 출고실적 엑셀 업로드 ('5.누적 출고실적RAW')")
uploaded_file = st.file_uploader("35MB 대용량 출고실적 파일을 업로드하세요", type=["xlsx", "xls", "xlsm"])

if uploaded_file is not None:
    try:
        bytes_data = uploaded_file.getvalue()
        excel_buffer = io.BytesIO(bytes_data)
        
        # 💡 대용량/복잡한 서식 파일도 가볍게 읽어내는 calamine 엔진 적용
        raw_df = None
        target_sheet = 0 # 기본 첫 번째 시트 또는 이름 지정
        
        try:
            xls = pd.ExcelFile(excel_buffer, engine="calamine")
            for sheet in xls.sheet_names:
                if "누적 출고실적RAW" in sheet or "5" in sheet:
                    target_sheet = sheet
                    break
            excel_buffer.seek(0)
            raw_df = pd.read_excel(excel_buffer, sheet_name=target_sheet, engine="calamine")
        except Exception as inner_e:
            # 혹시 calamine이 없거나 실패하면 기본 openpyxl 시도
            excel_buffer.seek(0)
            raw_df = pd.read_excel(excel_buffer, sheet_name=0, engine="openpyxl")

        # 품목 코드 열 탐색
        code_col_idx = 0
        for idx, col in enumerate(raw_df.columns):
            sample_vals = raw_df.iloc[:40, idx].astype(str).values
            if any("I-" in v or "C-" in v for v in sample_vals):
                code_col_idx = idx
                break
                
        col_code = raw_df.columns[code_col_idx]
        numeric_cols = raw_df.select_dtypes(include=['number']).columns
        
        if len(numeric_cols) >= 10:
            recent_10_cols = numeric_cols[-10:]
            
            avg_dict = {}
            for _, row in raw_df.iterrows():
                code = str(row[col_code]).strip()
                mean_val = row[recent_10_cols].mean()
                avg_dict[code] = mean_val
            
            new_avgs = []
            for item in items_mapping:
                k = item["excel_key"]
                new_avgs.append(avg_dict.get(k, 0))
            
            st.session_state.calculated_avg_series = pd.Series(new_avgs, index=items_list)
            st.success("✅ 대용량 출고실적 파일에서 최근 10일치 데이터를 성공적으로 읽어와 평균 사용량을 산출했습니다!")
        else:
            st.error("❌ 엑셀 시트에 최근 10일치 이상의 수치 데이터 열이 부족합니다.")
            
    except Exception as e:
        st.error(f"파일 처리 중 오류 발생: {e}")

# --- [UI: 사진 1번 표 형태 구현] ---
st.markdown("---")
st.subheader("📋 1. 재고 및 평균 사용량 현황")

stock_df_state = st.session_state.stock_inputs
merged_base = pd.merge(items_df_base, stock_df_state, on="구분2", how="left").fillna(0)
merged_base["평균사용량 *최근 10일"] = st.session_state.calculated_avg_series.values.round(0)

editor_columns_config = {
    "구분1": st.column_config.TextColumn(disabled=True),
    "구분2": st.column_config.TextColumn(disabled=True),
    "excel_key": st.column_config.TextColumn("RAW코드", disabled=True),
    "입수": st.column_config.NumberColumn(disabled=True),
    "평균사용량 *최근 10일": st.column_config.NumberColumn(disabled=True),
}

edited_table1 = st.data_editor(
    merged_base[["구분1", "구분2", "excel_key", "입수", "평균사용량 *최근 10일", "전일기말재고", "전일입고재고", "전일실사용량", "당일입고예정"]],
    column_config=editor_columns_config,
    hide_index=True,
    use_container_width=True,
    key="table1_editor"
)

st.session_state.stock_inputs = edited_table1[["구분2", "전일기말재고", "전일입고재고", "전일실사용량", "당일입고예정"]]

final_base_stock = (
    edited_table1["전일기말재고"] + 
    edited_table1["전일입고재고"] - 
    edited_table1["전일실사용량"] + 
    edited_table1["당일입고예정"]
)

result_summary = edited_table1.copy()
result_summary["당일기초재고 소계"] = final_base_stock
st.dataframe(result_summary, hide_index=True, use_container_width=True)
