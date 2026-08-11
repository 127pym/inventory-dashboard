import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(layout="wide", page_title="물류 자동화 대시보드")

st.title("📦 물류 재고 및 발주 자동화 대시보드")
st.write(f"오늘 날짜: {datetime.now().strftime('%Y-%m-%d')}")

# 품목 리스트 및 기본 입수 정보
items_list = [
    "101", "102", "103", 
    "스타 13호(양곡20kg)", "스타 1호", "스타 2호", 
    "스타 3호", "스타 4호", "스타 5호", 
    "스타 6호", "스타 7호", "스타 8호", "스타 11호"
]
plt_list = [300, 210, 210, 320, 2520, 960, 640, 640, 640, 320, 320, 320, 160]

# 세션 상태 초기화 (최근 10일 사용량 키인 표)
if "recent_10days_df" not in st.session_state:
    days_cols = [f"D-{i}" for i in range(10, 0, -1)]
    initial_data = {"구분2": items_list}
    for col in days_cols:
        initial_data[col] = [100] * len(items_list) 
    st.session_state.recent_10days_df = pd.DataFrame(initial_data)

# 세션 상태 초기화 (당일 재고 키인 표)
if "stock_input_df" not in st.session_state:
    st.session_state.stock_input_df = pd.DataFrame({
        "구분2": items_list,
        "현재고량": [13200, 17430, 19320, 160, 3760, 3640, 5760, 4160, 8320, 5280, 2240, 960, 320],
        "납품예정량": [0, 0, 0, 320, 0, 0, 0, 3200, 1920, 1920, 0, 0, 0]
    })

# 스크롤 없이 한 화면에서 관리할 수 있도록 탭(Tabs) 구조 적용
tab1, tab2, tab3 = st.tabs(["📝 1. 최근 10일 사용량 키인", "📝 2. 당일 재고 키인", "🚀 3. 최적 발주 필요량"])

with tab1:
    st.info("일자별 출고 실적을 입력하면 각 박스별 평균 사용량이 계산됩니다.")
    edited_10days = st.data_editor(
        st.session_state.recent_10days_df,
        hide_index=True,
        use_container_width=True,
        height=400
    )
    st.session_state.recent_10days_df = edited_10days

# 10일 치 데이터의 행별 평균 계산
days_columns = [col for col in st.session_state.recent_10days_df.columns if col != "구분2"]
calculated_avg = st.session_state.recent_10days_df[days_columns].mean(axis=1)

with tab2:
    st.info("현재고와 납품예정량을 키인하세요. 위 1번에서 계산된 **'평균사용량'이 열로 자동 추가**되어 표시됩니다.")
    
    combined_stock_df = pd.DataFrame({
        "구분2": items_list,
        "입수(PLT)": plt_list,
        "평균사용량": calculated_avg,  
        "현재고량": st.session_state.stock_input_df["현재고량"],
        "납품예정량": st.session_state.stock_input_df["납품예정량"]
    })

    edited_stock = st.data_editor(
        combined_stock_df,
        column_config={
            "구분2": st.column_config.TextColumn("품목", disabled=True),
            "입수(PLT)": st.column_config.NumberColumn("입수(PLT)", disabled=True),
            "평균사용량": st.column_config.NumberColumn("평균사용량 (자동계산)", format="%.1f", disabled=True),
            "현재고량": st.column_config.NumberColumn("현재고량 (키인)", format="%d"),
            "납품예정량": st.column_config.NumberColumn("납품예정량 (키인)", format="%d"),
        },
        hide_index=True,
        use_container_width=True,
        height=400
    )

    st.session_state.stock_input_df["현재고량"] = edited_stock["현재고량"]
    st.session_state.stock_input_df["납품예정량"] = edited_stock["납품예정량"]

with tab3:
    st.info("💡 이 부분은 추후 로직을 함께 고민하면서 구현해 나갈 수 있도록 비워두었습니다.")
