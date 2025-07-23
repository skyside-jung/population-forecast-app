
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="인구 예측 + 경제효과 시뮬레이터", layout="wide")
st.title("📂 인구 예측 및 경제효과 시뮬레이터")

uploaded_file = st.file_uploader("엑셀 파일 업로드 (.xlsx)", type=["xlsx"])

if uploaded_file:
    try:
        xls = pd.ExcelFile(uploaded_file)

        # Load all data
        pop_df = pd.read_excel(xls, sheet_name="인구입력")
        birth_df = pd.read_excel(xls, sheet_name="출산율")
        surv_df = pd.read_excel(xls, sheet_name="생존율")
        male_ratio_df = pd.read_excel(xls, sheet_name="성비")
        mig_df = pd.read_excel(xls, sheet_name="이동수")
        coeff_df = pd.read_excel(xls, sheet_name="보정계수")

        st.subheader("✅ 예측 설정 확인 및 조정")

        years = male_ratio_df["년도"].tolist()
        col1, col2, col3 = st.columns(3)
        with col1:
            year1 = st.selectbox("시작년도", years, index=0)
        with col2:
            year2 = st.selectbox("기준년도", years, index=1)
        with col3:
            year3 = st.selectbox("목표년도", years, index=2)

        st.subheader("📉 출산율 조정")
        birth_df_edit = st.data_editor(birth_df, use_container_width=True)

        st.subheader("🧬 생존율 조정")
        surv_df_edit = st.data_editor(surv_df, use_container_width=True)

        st.subheader("🚻 성비 조정")
        male_ratio_df_edit = st.data_editor(male_ratio_df, use_container_width=True)

        st.subheader("🚚 이동수 조정")
        mig_df_edit = st.data_editor(mig_df, use_container_width=True)

        coeff = st.slider("⚙️ 인구 이동 보정계수", 0.0, 2.0, float(coeff_df.iloc[0, 0]), step=0.01)

        if st.button("📊 예측 실행"):
            birth_rate = birth_df_edit[[str(year1), str(year2), str(year3)]].T.to_numpy()
            surv_m = surv_df_edit[[f"남_{year1}", f"남_{year2}", f"남_{year3}"]].T.to_numpy()
            surv_f = surv_df_edit[[f"여_{year1}", f"여_{year2}", f"여_{year3}"]].T.to_numpy()
            male_ratios = dict(zip(male_ratio_df_edit["년도"], male_ratio_df_edit["남성비"]))
            mig_male = mig_df_edit["남자_이동수"].to_numpy()
            mig_female = mig_df_edit["여자_이동수"].to_numpy()

            male1 = pop_df["남자_시작년도"].to_numpy()
            female1 = pop_df["여자_시작년도"].to_numpy()
            male2 = pop_df["남자_기준년도"].to_numpy()
            female2 = pop_df["여자_기준년도"].to_numpy()

            results = []
            year_labels = [year1, year2, year3]

            for i in range(3):
                src_m = male1 if i == 0 else male2
                src_f = female1 if i == 0 else female2
                births_m = 0
                births_f = 0
                proj_m = np.zeros(25, dtype=int)
                proj_f = np.zeros(25, dtype=int)

                for a in range(21):
                    br = birth_rate[i][a]
                    total_births = src_f[a] * br
                    male_rate = male_ratios[year_labels[i]]
                    m_birth = int(total_births * (male_rate / (100 + male_rate)))
                    f_birth = int(total_births * (100 / (100 + male_rate)))
                    births_m += m_birth
                    births_f += f_birth
                    proj_m[a+1] = int(src_m[a] * surv_m[i][a])
                    proj_f[a+1] = int(src_f[a] * surv_f[i][a])

                proj_m[0] = int(births_m * surv_m[i][0])
                proj_f[0] = int(births_f * surv_f[i][0])

                for a in range(21):
                    proj_m[a] += int(proj_m[a] * ((mig_male[a] / (src_m[a] if src_m[a] != 0 else 1)) * coeff))
                    proj_f[a] += int(proj_f[a] * ((mig_female[a] / (src_f[a] if src_f[a] != 0 else 1)) * coeff))

                result_df = pd.DataFrame({
                    "Age Group": pop_df["Age Group"],
                    "Year": year_labels[i+1] if i+1 < 3 else year_labels[i],
                    "Male": proj_m[:21],
                    "Female": proj_f[:21]
                })
                results.append(result_df)

            final_df = pd.concat(results, ignore_index=True)
            st.success("✅ 예측 완료")
            st.dataframe(final_df, use_container_width=True)

            selected_year = st.selectbox("📅 시각화할 연도 선택", sorted(final_df["Year"].unique()))
            chart_df = final_df[final_df["Year"] == selected_year]
            st.bar_chart(chart_df[["Male", "Female"]].set_index(chart_df["Age Group"]))

            csv = final_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 결과 CSV 다운로드", data=csv, file_name="인구예측결과.csv", mime="text/csv")

        # 경제효과 계산
        st.subheader("💰 경제효과 추정 (Form9)")
        st.markdown("계산식: `점수 = 노동인구비율 × A + 연소득액 × B + 방문자수 × C`")

        coef_col = st.columns(3)
        A = coef_col[0].number_input("🔧 노동인구비율 계수 (A)", value=0.382, step=0.001)
        B = coef_col[1].number_input("🔧 연소득 계수 (B)", value=0.271, step=0.001)
        C = coef_col[2].number_input("🔧 방문자수 계수 (C)", value=0.271, step=0.001)

        input_col = st.columns(3)
        labor_ratio = input_col[0].number_input("노동인구비율 (%)", min_value=0.0, max_value=100.0, value=60.0)
        income = input_col[1].number_input("연소득액 (백만원)", min_value=0.0, value=200.0)
        visitors = input_col[2].number_input("연 방문자 수 (천명)", min_value=0.0, value=50.0)

        if st.button("📈 경제효과 계산"):
            score = labor_ratio * A + income * B + visitors * C
            st.success(f"📊 추정된 경제효과 점수: `{score:.2f}`")

    except Exception as e:
        st.error(f"❌ 처리 중 오류 발생: {e}")
else:
    st.info("⬆ 좌측 상단에서 샘플 엑셀 파일을 업로드하세요.")
