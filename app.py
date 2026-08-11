import streamlit as st
import pandas as pd
from datetime import datetime
import math
import os

st.set_page_config(layout="wide", page_title="물류 자동화 대시보드")

HISTORY_FILE = "usage_history.csv"

# 1. 초기 품목 및 기본 정보 설정
items_info = {
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
    ]
}
base_df = pd.DataFrame(items_info)

# 2. 누적 사용량 데이터(history.csv) 관리
# 파일이 없으면 가상의 초기 누적 데이터를 만들어줍니다.
if not os.path.exists(HISTORY_FILE):
    # 테스트용 초기 누적 데이터 생성 (최근 10일치 시뮬레이션)
    init_data = []
    for idx, row in base_df.iterrows():
        for i in range(10):
            d_date = (datetime.now() - pd.Timedelta(days=i)).strftime('%Y-%m-%d')
            init_data.append({"날짜": d_date, "구분2": row["구분2"], "사용량": 100}) # 임의 초기값
    pd.DataFrame(init_data).to_csv(HISTORY_FILE, index=False)

# 누적 데이터 불러오기
history_df = pd.read_csv(HISTORY_FILE)

st.title("📦 물류 재고 및 발주 자동화 대시보드 (누적 데이터 연동)")
st.write(f"오늘 날짜: {datetime.now().strftime('%Y-%m-%d')}")

# 요일별 특수성 반영 (목요일 발주 시 주말 물량 3일치 통합)
is_thursday = datetime.now().weekday() == 3 
if is_thursday:
    st.warning("⚠️ 목요일 감지: 주말 통합 발주 모드 활성화 (3일치 소모량 반영)")
    multiplier = 3 
else:
    multiplier = 1

# 3. 사이드바: 오늘 날짜의 사용량 및 재고 키인
st.sidebar.header("📝 오늘의 데이터 키인")
input_date = st.sidebar.date_input("입력 날짜", datetime.now())
selected_item = st.sidebar.selectbox("품목 선택", base_df["구분2"].tolist())
today_usage = st.sidebar.number_input("오늘 실제 사용량", min_value=0, value=0)

current_stock = st.sidebar.number_input("현재고량", min_value=0, value=1000)
incoming_stock = st.sidebar.number_input("납품예정량", min_value=0, value=0)

if st.sidebar.button("오늘 사용량 기록 및 반영"):
    new_row = pd.DataFrame({
        "날짜": [input_date.strftime('%Y-%m-%d')],
        "구분2": [selected_item],
        "사용량": [today_usage]
    })
    # 기존 데이터에 추가 후 저장
    history_df = pd.concat([history_df, new_row], ignore_index=True)
    history_df.to_csv(HISTORY_FILE, index=False)
    st.sidebar.success(f"[{selected_item}] 사용량 {today_usage} 기록 완료!")

# 4. 최근 10일 평균 사용량 자동 계산 로직
def get_recent_avg(item_name):
    item_history = history_df[history_df["구분2"] == item_name]
    if item_history.empty:
        return 0.0
    # 날짜 기준 정렬 후 최근 10개 추출
    item_history = item_history.sort_values(by="날짜", ascending=False)
    recent_10 = item_history.head(10)
    return recent_10["사용량"].mean()

# 대시보드 표 데이터 구성
display_data = []
for idx, row in base_df.iterrows():
    item = row["구분2"]
    plt = row["입수(PLT)"]
    
    # 최근 10일 평균 사용량 계산
    avg_use = get_recent_avg(item)
    
    # 임시로 현재고와 납품예정량은 기본값 부여 (원하시면 테이블 에디터로 확장 가능)
    cur_st = current_stock if item == selected_item else 1000 # 예시 편의상
    inc_st = incoming_stock if item == selected_item else 0
    
    # 안전재고 = 평균사용량 x 3
    safety_stock = avg_use * 3
    base_stock = cur_st + inc_st
    
    # 미발주 시 예상 잔여재고
    expected_stock = base_stock - (avg_use * 3 * multiplier)
    needed_qty = safety_stock - expected_stock
    
    if needed_qty <= 0:
        order_plt = 0.0
    else:
        order_plt = float(math.ceil(needed_qty / plt))
        
    display_data.append({
        "구분2": item,
        "입수(PLT)": plt,
        "최근10일 평균사용량": round(avg_use, 1),
        "현재고량": cur_st,
        "납품예정량": inc_st,
        "안전재고(평균x3)": round(safety_stock, 1),
        "발주필요량(PLT)": order_plt
    })

result_df = pd.DataFrame(display_data)

# 5. 결과 대시보드 출력
st.subheader("🚀 실시간 재고 및 최적 발주 필요량 현황")
st.dataframe(
    result_df.style.format({
        "최근10일 평균사용량": "{:.1f}",
        "현재고량": "{:,}",
        "납품예정량": "{:,}",
        "안전재고(평균x3)": "{:.1f}",
        "발주필요량(PLT)": "{:.1f}"
    }).background_gradient(subset=["발주필요량(PLT)"], cmap="YlOrRd"),
    use_container_width=True
)
