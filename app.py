import streamlit as st
import pandas as pd
from datetime import datetime
import math

st.set_page_config(layout="wide", page_title="물류 자동화 대시보드")

# 1. 기본 품목 및 입수(PLT), 평균사용량 데이터 정의
if "df_data" not in st.session_state:
    st.session_state.df_data = pd.DataFrame({
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
        # 사용자가 한 번에 키인할 수 있는 컬럼 (초기값 설정)
        "현재고량": [13200, 17430, 19320, 160, 3760, 3640, 5760, 4160, 8320, 5280, 2240, 960, 320],
        "납품예정량": [0, 0, 0, 320, 0, 0, 0, 3200, 1920, 1920, 0, 0, 0]
    })

st.title("📦 물류 재고 및 발주 자동화 대시보드")
st.write(f"오늘 날짜: {datetime.now().strftime('%Y-%m-%d')}")

# 요일별 특수성 반영 (목요일 발주 시 주말 물량 3일치 통합 계산)
is_thursday = datetime.now().weekday() == 3 
if is_thursday:
    st.warning("⚠️ 목요일 감지: 주말 통합 발주 모드 활성화 (3일치 소모량 반영)")
    multiplier = 3 
else:
    multiplier = 1

# 2. 사이드바: 전체 키인 안내
st.sidebar.header("📝 키인 안내")
st.sidebar.info("오른쪽 메인 화면의 표에서 **'현재고량'**과 **'납품예정량'** 숫자를 직접 수정(클릭 후 타이핑)할 수 있습니다.")

# 3. 메인 화면: 한 번에 키인할 수 있는 에디터 테이블 제공
st.subheader("1. 재고 및 납품예정량 입력 (여기서 숫자를 수정하세요)")
edited_df = st.data_editor(
    st.session_state.df_data,
    column_config={
        "구분2": st.column_config.TextColumn("품목", disabled=True),
        "입수(PLT)": st.column_config.NumberColumn("입수(PLT)", disabled=True),
        "평균사용량": st.column_config.NumberColumn("평균사용량", disabled=True),
        "현재고량": st.column_config.NumberColumn("현재고량 (키인)", format="%d"),
        "납품예정량": st.column_config.NumberColumn("납품예정량 (키인)", format="%d"),
    },
    hide_index=True,
    use_container_width=True
)

# 사용자가 수정한 값을 세션에 저장
st.session_state.df_data = edited_df

# 4. 요구사항 반영 핵심 계산 로직
def calculate_order(row):
    # 안전재고 = 사용량(평균사용량) x 3
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
        # 발주량은 항상 '입수(PLT)'의 배수로 올림 처리
        plt_unit = row["입수(PLT)"]
        pallets = math.ceil(needed_qty / plt_unit)
        return float(pallets)

# 계산 결과 데이터프레임 생성
result_df = edited_df.copy()
result_df["안전재고(사용량x3)"] = result_df["평균사용량"] * 3
result_df["발주필요량(PLT)"] = result_df.apply(calculate_order, axis=1)

# 5. 결과 대시보드 표 출력
st.subheader("🚀 당일 최적 발주 필요량 결과")
st.dataframe(
    result_df[["구분2", "입수(PLT)", "평균사용량", "현재고량", "납품예정량", "안전재고(사용량x3)", "발주필요량(PLT)"]]
      .style.format({
          "현재고량": "{:,}",
          "납품예정량": "{:,}",
          "안전재고(사용량x3)": "{:,}",
          "발주필요량(PLT)": "{:.1f}"
      })
      .background_gradient(subset=["발주필요량(PLT)"], cmap="YlOrRd"),
    use_container_width=True
)
