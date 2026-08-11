import streamlit as st
import pandas as pd
from datetime import datetime
import math

st.set_page_config(layout="wide", page_title="물류 자동화 대시보드")

st.title("📦 물류 재고 및 발주 자동화 대시보드")
st.write(f"오늘 날짜: {datetime.now().strftime('%Y-%m-%d')}")

# 요일별 특수성 반영 (목요일 발주 시 주말 물량 3일치 통합 계산)
is_thursday = datetime.now().weekday() == 3 
if is_thursday:
    st.warning("⚠️ 목요일 감지: 주말 통합 발주 모드 활성화 (3일치 소모량 반영)")
    multiplier = 3 
else:
    multiplier = 1

# 품목 리스트 및 기본 입수 정보
items_list = [
    "101", "102", "103", 
    "스타 13호(양곡20kg)", "스타 1호", "스타 2호", 
    "스타 3호", "스타 4호", "스타 5호", 
    "스타 6호", "스타 7호", "스타 8호", "스타 11호"
]
plt_list = [300, 210, 210, 320, 2520, 960, 640, 640, 640, 320, 320, 320, 160]

# 세션 상태 초기화 (2번: 최근 10일 사용량 키인 표)
if "recent_10days_df" not in st.session_state:
    days_cols = [f"D-{i}" for i in range(10, 0, -1)]
    initial_data = {"구분2": items_list}
    for col in days_cols:
        initial_data[col] = [100] * len(items_list) 
    st.session_state.recent_10days_df = pd.DataFrame(initial_data)

# 세션 상태 초기화 (1번: 당일 재고 키인 표)
if "stock_input_df" not in st.session_state:
    st.session_state.stock_input_df = pd.DataFrame({
        "구분2": items_list,
        "현재고량": [13200, 17430, 19320, 160, 3760, 3640, 5760, 4160, 8320, 5280, 2240, 960, 320],
        "납품예정량": [0, 0, 0, 320, 0, 0, 0, 3200, 1920, 1920, 0, 0, 0]
    })


# --- [2번] 상단: 최근 10일 사용량 키인 표 ---
st.subheader("📝 2. 최근 10일 사용량 키인 (일자별 출고 실적 입력)")
st.info("이 표에 입력한 최근 10일간의 수치가 아래 **1번 대시보드의 '평균사용량' 열에 자동으로 계산되어 반영**됩니다.")

edited_10days = st.data_editor(
    st.session_state.recent_10days_df,
    hide_index=True,
    use_container_width=True
)
st.session_state.recent_10days_df = edited_10days

# 10일 치 데이터의 행별 평균 계산
days_columns = [col for col in edited_10days.columns if col != "구분2"]
calculated_avg = edited_10days[days_columns].mean(axis=1)


# --- [1번] 하단: 당일 재고 키인 및 최적 발주 필요량 결과 대시보드 ---
st.subheader("🚀 1. 당일 재고 키인 및 최적 발주 필요량 결과 대시보드")
st.info("아래 표의 **'현재고량'**과 **'납품예정량'**을 키인하시면, 위에서 계산된 평균사용량(열 추가됨)과 함께 연동되어 발주량이 산출됩니다.")

edited_stock = st.data_editor(
    st.session_state.stock_input_df,
    column_config={
        "구분2": st.column_config.TextColumn("품목", disabled=True),
        "현재고량": st.column_config.NumberColumn("현재고량 (키인)", format="%d"),
        "납품예정량": st.column_config.NumberColumn("납품예정량 (키인)", format="%d"),
    },
    hide_index=True,
    use_container_width=True
)
st.session_state.stock_input_df = edited_stock

# 최종 대시보드 데이터프레임 구성 (평균사용량 열을 명확히 포함)
processed_df = pd.DataFrame({
    "구분2": items_list,
    "입수(PLT)": plt_list,
    "평균사용량": calculated_avg,  # 상단 2번 표에서 자동 계산되어 들어온 열
    "현재고량": edited_stock["현재고량"],
    "납품예정량": edited_stock["납품예정량"]
})

def calculate_order(row):
    safety_stock = row["평균사용량"] * 3
    base_stock = row["현재고량"] + row["납품예정량"]
    expected_stock = base_stock - (row["평균사용량"] * 3 * multiplier)
    needed_qty = safety_stock - expected_stock
    
    if needed_qty <= 0:
        return 0.0
    else:
        plt_unit = row["입수(PLT)"]
        pallets = math.ceil(needed_qty / plt_unit)
        return float(pallets)

processed_df["안전재고(사용량x3)"] = processed_df["평균사용량"] * 3
processed_df["발주필요량(PLT)"] = processed_df.apply(calculate_order, axis=1)

# 1번 대시보드 최종 결과 표 출력 (평균사용량 열 포함)
st.dataframe(
    processed_df[["구분2", "입수(PLT)", "평균사용량", "현재고량", "납품예정량", "안전재고(사용량x3)", "발주필요량(PLT)"]]
      .style.format({
          "평균사용량": "{:.1f}",
          "현재고량": "{:,}",
          "납품예정량": "{:,}",
          "안전재고(사용량x3)": "{:.1f}",
          "발주필요량(PLT)": "{:.1f}"
      })
      .background_gradient(subset=["발주필요량(PLT)"], cmap="YlOrRd"),
    use_container_width=True
)
