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

# 1. 초기 데이터 세팅 (품목, 입수, 평균사용량, 키인 항목들)
if "input_df" not in st.session_state:
    st.session_state.input_df = pd.DataFrame({
        "구분2": [
            "101", "102", "103", 
            "스타 13호(양곡20kg)", "스타 1호", "스타 2호", 
            "스타 3호", "스타 4호", "스타 5호", 
            "스타 6호", "스타 7호", "스타 8호", "스타 11호"
        ],
        "입수(PLT)": [
            300, 210, 210, 
            320, 2520, 960, 
            640, 640, 640, 
            320, 320, 320, 160
        ],
        "평균사용량": [1531, 4472, 3184, 97, 76, 245, 474, 641, 904, 980, 10, 125, 24],
        # 매일 키인해야 하는 항목들만 따로 뺌
        "당일사용량": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        "현재고량": [13200, 17430, 19320, 160, 3760, 3640, 5760, 4160, 8320, 5280, 2240, 960, 320],
        "납품예정량": [0, 0, 0, 320, 0, 0, 0, 3200, 1920, 1920, 0, 0, 0]
    })

# 2. 키인 전용 에디터 (여기서 숫자만 가볍게 수정)
st.subheader("📝 1. 오늘 데이터 키인 (필요한 값만 수정하세요)")
st.info("아래 표에서 **'당일사용량'**, **'현재고량'**, **'납품예정량'**만 숫자를 고치면 아래 결과가 즉시 연동됩니다.")

edited_df = st.data_editor(
    st.session_state.input_df,
    column_config={
        "구분2": st.column_config.TextColumn("품목", disabled=True),
        "입수(PLT)": st.column_config.NumberColumn("입수(PLT)", disabled=True),
        "평균사용량": st.column_config.NumberColumn("평균사용량", disabled=True),
        "당일사용량": st.column_config.NumberColumn("당일사용량 (키인)", format="%d"),
        "현재고량": st.column_config.NumberColumn("현재고량 (키인)", format="%d"),
        "납품예정량": st.column_config.NumberColumn("납품예정량 (키인)", format="%d"),
    },
    hide_index=True,
    use_container_width=True
)

st.session_state.input_df = edited_df

# 3. 발주 계산 로직 함수
def calculate_order(row):
    # 안전재고 = 평균사용량 x 3
    safety_stock = row["평균사용량"] * 3
    
    # 기초재고 = 현재고량 + 납품예정량
    base_stock = row["현재고량"] + row["납품예정량"]
    
    # 미발주 시 예상 잔여재고 (리드타임 3일 * 멀티플라이어 반영)
    expected_stock = base_stock - (row["평균사용량"] * 3 * multiplier)
    
    # 부족한 양 계산
    needed_qty = safety_stock - expected_stock
    
    if needed_qty <= 0:
        return 0.0
    else:
        plt_unit = row["입수(PLT)"]
        # 항상 입수의 배수로 올림 처리
        pallets = math.ceil(needed_qty / plt_unit)
        return float(pallets)

# 결과 데이터프레임 생성
result_df = edited_df.copy()
result_df["안전재고(사용량x3)"] = result_df["평균사용량"] * 3
result_df["발주필요량(PLT)"] = result_df.apply(calculate_order, axis=1)

# 4. 결과 대시보드 출력
st.subheader("🚀 2. 당일 최적 발주 필요량 결과")
st.dataframe(
    result_df[["구분2", "입수(PLT)", "평균사용량", "당일사용량", "현재고량", "납품예정량", "안전재고(사용량x3)", "발주필요량(PLT)"]]
      .style.format({
          "당일사용량": "{:,}",
          "현재고량": "{:,}",
          "납품예정량": "{:,}",
          "안전재고(사용량x3)": "{:,}",
          "발주필요량(PLT)": "{:.1f}"
      })
      .background_gradient(subset=["발주필요량(PLT)"], cmap="YlOrRd"),
    use_container_width=True
)
