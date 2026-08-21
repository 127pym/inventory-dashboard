import streamlit as st
import pandas as pd
import datetime
import os

# ... (기존 설정은 동일) ...

# --- [추가: 누적 통계 시각화] ---
st.subheader("📈 품목별 사용량 트렌드 및 요약")
if os.path.exists(HISTORY_FILE):
    hist = pd.read_csv(HISTORY_FILE).sort_values("날짜")
    
    # 1. 차트 추가 (저온 품목 중심)
    st.line_chart(hist.set_index("날짜")[["I-01", "I-02", "I-03"]])
    
    # 2. 히트맵 스타일 적용된 표
    pivot = hist.set_index("날짜").T.reset_index().rename(columns={"index": "excel_key"})
    pivot = pd.merge(edited_df[["excel_key", "구분2"]], pivot, on="excel_key", how="left").fillna(0)
    
    d_cols = [c for c in pivot.columns if c not in ["excel_key", "구분2"]]
    pivot["합계"] = pivot[d_cols].sum(axis=1).astype(int)
    pivot["평균"] = pivot[d_cols].mean(axis=1).round().astype(int)
    
    # 히트맵 적용 (사용량이 많을수록 진한 색)
    st.dataframe(pivot.style.background_gradient(subset=d_cols, cmap="YlOrRd"), 
                 use_container_width=True, hide_index=True)
    
    # 3. 요약 카드
    cols = st.columns(3)
    cols[0].metric("총 기록 일수", len(hist))
    cols[1].metric("전체 품목 일평균 사용량", int(pivot["평균"].mean()))
    cols[2].metric("데이터 상태", "정상")
