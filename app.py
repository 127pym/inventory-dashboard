import streamlit as st
import pandas as pd
import zipfile
import io

st.title("🔍 파일 무결성 진단 도구")

uploaded_file = st.file_uploader("파일을 올려보세요", type=["xlsx", "xls"])

if uploaded_file is not None:
    bytes_data = uploaded_file.getvalue()
    
    # 1. 압축 파일 구조(ZIP) 확인 (xlsx는 본래 zip임)
    is_zip = zipfile.is_zipfile(io.BytesIO(bytes_data))
    st.write(f"📂 파일이 유효한 ZIP 구조인가요?: **{is_zip}**")
    
    if not is_zip:
        st.error("❌ 파일이 압축 구조가 아닙니다. 현재 보안/DRM 모듈이 압축을 막고 있거나, 아예 엑셀이 아닌 다른 포맷입니다.")
    else:
        st.success("✅ 파일이 압축 구조를 가지고 있습니다. 이제 내용물을 읽어볼게요.")
        
        # 2. 내용물(시트) 읽기 시도
        try:
            xls = pd.ExcelFile(io.BytesIO(bytes_data), engine="openpyxl")
            st.write("📊 시트 목록:", xls.sheet_names)
            st.success("🎉 축하합니다! 파일이 완벽하게 암호화 해제된 상태입니다!")
        except Exception as e:
            st.error(f"⚠️ 압축 구조는 맞지만, 내부 데이터 읽기 실패: {e}")
