import streamlit as st
import pandas as pd
import datetime
import os

st.set_page_config(layout="wide", page_title="물류 재고 및 발주 통합 대시보드")

DATA_FILE = "inventory_master_data.csv"
HISTORY_FILE = "usage_history.csv"

# --- [고정 틀 1: 품목 데이터 및 영구 저장소 로드 구조] ---
ITEM_LIST = [
    ("101", "I-01"), ("102", "I-02"), ("103", "I-03"), 
    ("스타 13호(양곡20kg)", "C-13"), ("스타 1호", "C-01"), ("스타 2호", "C-02"), 
    ("스타 3호", "C-03"), ("스타 4호", "C-04"), ("스타 5호", "C-05"), 
    ("스타 6호", "C-06"), ("스타 7호", "C-07"), ("스타 8호", "C-08"), ("스타 11호", "C-11")
]

if os.path.exists(DATA_FILE):
    st.session_state.stock_data = pd.read_csv(DATA_FILE)
    if "당일입고량" not in st.session_state.stock_data.columns:
        st.session_state.stock_data.insert(4, "당일입고량", 0)
    if "데이터반영일수" in st.session_state.stock_data.columns:
        st.session_state.stock_data.drop(columns=["데이터반영일수"], inplace=True)
else:
    st.session_state.stock_data = pd.DataFrame({
        "구분2": [i[0] for i in ITEM_LIST],
        "excel_key": [i[1] for i in ITEM_LIST],
        "입수(PLT)": [300, 210, 210, 320, 2520, 960, 640, 640, 640, 320, 320, 320, 160],
        "전일기말재고": [20100, 14280, 11760, 320, 2680, 960, 1920, 4160, 3200, 3040, 2080, 800, 160],
        "당일입고량": [0] * len(ITEM_LIST),
        "입고예정량": [0] * len(ITEM_LIST),
        "전일실사용량": [0] * len(ITEM_LIST),
        "누적평균사용량": [0] * len(ITEM_LIST)
    })
    st.session_state.stock_data.to_csv(DATA_FILE, index=False)

st.title("📦 물류 재고 및 발주 통합 대시보드")

# --- [고정 틀 2: 날짜 및 파일 업로드 + 설정 UI] ---
today = datetime.date(2026, 8, 19)

col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
with col1: order_date = st.date_input("발주 대상일", today)
with col2: delivery_date = st.date_input("입고 예정일", today + datetime.timedelta(days=6))
with col3: avg_days = st.number_input("평균 산출 기간(일)", 1, 30, 10)
with col4: uploaded_file = st.file_uploader("출고일마감 파일 업로드", type=["xlsx", "xls"])

with st.expander("⚙️ [설정] 저온 품목(I-01 ~ I-03) 요일별 버퍼 마진율 조절", expanded=False):
    b_col1, b_col2, b_col3 = st.columns(3)
    with b_col1:
        margin_thu_fri = st.number_input("목/금요일 버퍼 (주말 대비)", 1.0, 2.0, 1.20, step=0.05)
    with b_col2:
        margin_mon = st.number_input("월요일 버퍼 (주말 여파)", 1.0, 2.0, 1.10, step=0.05)
    with b_col3:
        margin_other = st.number_input("기타 평일/주말 버퍼", 1.0, 2.0, 1.05, step=0.05)

weekday_kr = ['월', '화', '수', '목', '금', '토', '일']
current_weekday = order_date.weekday()
st.info(f"📅 발주 대상일: **{weekday_kr[current_weekday]}요일** | 잘못 업로드된 날짜 기록은 하단에서 쉽게 삭제할 수 있습니다.")

# --- [고정 틀 3: 실시간 데이터 편집기] ---
st.subheader("📋 재고 및 누적 데이터 입력")
edited_df = st.data_editor(st.session_state.stock_data, num_rows="fixed", use_container_width=True, hide_index=True)

# --- [계산 로직 (실시간 자동 연산)] ---
res = edited_df.copy()

numeric_cols_to_fix = ["전일기말재고", "당일입고량", "입고예정량", "전일실사용량", "누적평균사용량"]
for col in numeric_cols_to_fix:
    if col in res.columns:
        res[col] = pd.to_numeric(res[col], errors='coerce').fillna(0).astype(int)

file_usages = {}
if uploaded_file is not None:
    try:
        uploaded_file.seek(0)
        df = pd.read_excel(uploaded_file)
        if '운송장번호(박스기준)' in df.columns and '박스호수(실제)' in df.columns:
            pivot = df.drop_duplicates(subset=['운송장번호(박스기준)'])['박스호수(실제)'].value_counts()
            for idx, row in res.iterrows():
                file_usages[row["excel_key"]] = int(pivot.get(row["excel_key"], 0))
    except Exception as e:
        st.error(f"❌ 파일 분석 실패: {e}")

today_str = order_date.strftime("%Y-%m-%d")
history_row = {"날짜": today_str}

for idx, row in res.iterrows():
    key = row["excel_key"]
    today_use = file_usages.get(key, row["전일실사용량"])
    res.at[idx, "전일실사용량"] = int(today_use)
    history_row[key] = int(today_use)
    
    old_avg = float(row["누적평균사용량"])
    if old_avg == 0:
        new_avg = float(today_use)
    else:
        new_avg = (old_avg * 0.8) + (float(today_use) * 0.2)
        
    res.at[idx, "누적평균사용량"] = int(round(new_avg))

lead_time = max(0, (delivery_date - order_date).days) + 1

def get_dynamic_margin(excel_key, weekday):
    if excel_key in ["I-01", "I-02", "I-03"]:
        if weekday in [3, 4]: return margin_thu_fri 
        elif weekday == 0:     return margin_mon       
        else:                  return margin_other     
    return 1.0

safety_stocks = []
for idx, row in res.iterrows():
    margin = get_dynamic_margin(row["excel_key"], current_weekday)
    base_safety = float(row["누적평균사용량"]) * lead_time
    safety_stocks.append(int(round(base_safety * margin)))
    
res["안전재고"] = safety_stocks
res["기초재고소계"] = res["전일기말재고"] + res["당일입고량"] - res["전일실사용량"] + res["입고예정량"]
res["예상잔여재고"] = res["기초재고소계"] - res["안전재고"]
res["발주필요량"] = res.apply(lambda x: max(0, int(x["안전재고"]) - int(x["기초재고소계"])), axis=1)

int_columns = ["입수(PLT)", "전일기말재고", "당일입고량", "입고예정량", "전일실사용량", "누적평균사용량", "안전재고", "기초재고소계", "예상잔여재고", "발주필요량"]
for col in int_columns:
    if col in res.columns:
        res[col] = res[col].astype(int)

# --- [고정 틀 4: 저장 버튼] ---
if st.button("💾 입력한 데이터 및 상태 저장", type="primary", use_container_width=True):
    st.session_state.stock_data = res
    res.to_csv(DATA_FILE, index=False)
    
    history_df = pd.DataFrame([history_row])
    if os.path.exists(HISTORY_FILE):
        existing_history = pd.read_csv(HISTORY_FILE)
        existing_history = existing_history[existing_history["날짜"] != today_str]
        history_df = pd.concat([existing_history, history_df], ignore_index=True)
    
    history_df.to_csv(HISTORY_FILE, index=False)
    st.success("✅ 현재 데이터가 안전하게 저장되었으며, 일자별 사용량 기록부가 갱신되었습니다!")

# --- [고정 틀 5: 최종 계산 및 발주 요약 표] ---
st.markdown("---")
st.subheader("📊 최종 계산 및 발주 요약")

display_df = res[["excel_key", "구분2", "입수(PLT)", "전일실사용량", "누적평균사용량", "안전재고", "기초재고소계", "예상잔여재고", "발주필요량"]]
main_items = ["I-01", "I-02", "I-03", "C-04", "C-05", "C-06"]

def highlight_main_items(row):
    if row["excel_key"] in main_items:
        return ['background-color: #FFF9C4'] * len(row)
    return [''] * len(row)

styled_df = display_df.style.apply(highlight_main_items, axis=1).hide(subset=["excel_key"], axis=1)
st.dataframe(styled_df, use_container_width=True, hide_index=True)

# --- [고정 틀 6: 일자별 사용량 누적 기록부 및 삭제 기능] ---
st.markdown("---")
st.subheader("📈 일자별 품목별 실사용량 누적 기록부")

if os.path.exists(HISTORY_FILE):
    history_view = pd.read_csv(HISTORY_FILE)
    st.dataframe(history_view, use_container_width=True, hide_index=True)
    
    # [추가]: 잘못 업로드된 날짜 데이터 간편 삭제 UI
    if not history_view.empty:
        with st.expander("🗑️ 잘못 업로드된 날짜 데이터 삭제하기", expanded=False):
            dates_available = history_view["날짜"].tolist()
            target_date_to_delete = st.selectbox("삭제할 날짜 선택", dates_available)
            
            if st.button("❌ 선택한 날짜 기록 삭제", type="secondary"):
                # 선택한 날짜를 제외하고 다시 저장
                updated_history = history_view[history_view["날짜"] != target_date_to_delete]
                updated_history.to_csv(HISTORY_FILE, index=False)
                st.success(f"🗑️ [{target_date_to_delete}] 날짜의 데이터가 성공적으로 삭제되었습니다. 페이지를 새로고침합니다.")
                st.rerun()
else:
    st.info("ℹ️ 파일을 업로드하고 [저장] 버튼을 누르면 날짜별 사용량 기록이 여기에 실시간으로 쌓입니다.")
