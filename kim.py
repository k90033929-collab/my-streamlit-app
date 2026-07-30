import os
import platform
import warnings
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
# Streamlit 서버에 설치된 나눔고딕 폰트 지정
plt.rc('font', family='NanumGothic')
# 마이너스(-) 기호가 깨지는 현상 방지
plt.rc('axes', unicode_minus=False)
import seaborn as sns
import statsmodels.api as sm
import streamlit as st

# ==========================================
# koreanize-matplotlib 안전 임포트 (로컬 및 Streamlit Cloud 호환)
# ==========================================
try:
    import koreanize_matplotlib
except ImportError:
    pass

# ==========================================
# 1. 기본 설정 및 한글 폰트 처리
# ==========================================
st.set_page_config(page_title="광고 성과 분석 & 예산 최적화", layout="wide")
warnings.filterwarnings('ignore')
matplotlib.set_loglevel('error')

@st.cache_resource
def set_korean_font():
    """운영체제에 따른 한글 폰트 설정"""
    system_name = platform.system()
    if system_name == 'Windows':
        plt.rc('font', family='Malgun Gothic')
    elif system_name == 'Darwin': # Mac
        plt.rc('font', family='AppleGothic')
    else: # Linux/Colab/Streamlit Cloud
        plt.rc('font', family='NanumGothic')
    plt.rcParams['axes.unicode_minus'] = False # 마이너스 기호 깨짐 방지

set_korean_font()

# ==========================================
# 메인 UI 타이틀
# ==========================================
st.title("📊 광고 성과 분석 및 예산 최적화 대시보드")
st.markdown("엑셀 데이터를 업로드하면 **상관분석, 회귀분석 예측 시나리오, 매체별 분석, 예산 재분배(S-Curve) 시뮬레이션**을 자동 수행합니다.")

# ==========================================
# 2. 엑셀 파일 업로드 위젯
# ==========================================
uploaded_file = st.file_uploader("📂 '표준업로드_템플릿.xlsx' (데이터가 입력된 엑셀 파일)을 선택하여 업로드해주세요.", type=['xlsx'])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    st.success(f"✅ '{uploaded_file.name}' 파일 업로드 성공! (총 데이터 수: {len(df)}행)")

    # ==========================================
    # 3. 데이터 전처리 및 지표 속성 명확화
    # ==========================================
    df.columns = df.columns.astype(str).str.strip()

    template_metric_cols = [
        '광고비', '노출', '클릭', '전환수', '전환매출',
        'CTR', 'CPC', 'CPM', '전환률', '전환 단가(CPA)', 'ROAS', '객단가'
    ]

    available_metrics = []
    for col in template_metric_cols:
        if col in df.columns:
            converted = pd.to_numeric(df[col], errors='coerce')
            if converted.dropna().nunique() > 1:
                df[col] = converted
                available_metrics.append(col)

    MAIN_KPI = '전환수'
    COST_METRICS = ['전환 단가(CPA)', 'CPC', 'CPM']
    VOLUME_METRICS = ['노출', '클릭', '광고비']
    RATIO_METRICS = ['CTR', '전환률', 'ROAS']

    # ==========================================
    # 4. 분석 가능 여부 사전 검증
    # ==========================================
    if MAIN_KPI not in available_metrics or len(available_metrics) < 2:
        st.error(f"⚠️ 데이터 부족: '{MAIN_KPI}' 또는 상관분석을 위한 수치형 지표 데이터가 부족합니다.")
    else:
        analysis_df = df.dropna(subset=[MAIN_KPI])

        if len(analysis_df) < 5:
            st.warning("⚠️ 데이터 부족: 분석 및 예측 인사이트 도출을 위한 유효 데이터 행(Row) 수가 부족합니다.")
        else:
            st.divider()
            
            # ==========================================
            # 5. [PART 1] 피어슨 상관분석 및 히트맵
            # ==========================================
            st.header(f"📈 [PART 1] 상관분석: '{MAIN_KPI}'에 가장 영향도 높은 지표 선별")
            
            corr_matrix = analysis_df[available_metrics].corr(method='pearson')

            col1, col2 = st.columns([2, 1])
            with col1:
                fig, ax = plt.subplots(figsize=(10, 8))
                sns.heatmap(corr_matrix, annot=True, fmt='.2f', cmap='coolwarm', vmin=-1, vmax=1, linewidths=0.5, ax=ax)
                ax.set_title(f'전체 캠페인 지표 상관관계 히트맵 (KPI: {MAIN_KPI})', fontsize=14, pad=15)
                st.pyplot(fig)

            with col2:
                exclude_cols = [MAIN_KPI, '전환매출', 'ROAS']
                driver_cols = [c for c in available_metrics if c not in exclude_cols]
                kpi_corr = corr_matrix[MAIN_KPI].drop(exclude_cols, errors='ignore').dropna().sort_values(ascending=False)

                top_positive = kpi_corr[kpi_corr > 0.2].head(2)
                top_negative = kpi_corr[kpi_corr < -0.2].tail(2)

                st.info(f"**📌 '{MAIN_KPI}'에 가장 강력한 양(+)의 영향을 미치는 지표:**\n" + 
                        (', '.join([f"{k} (r={v:.2f})" for k,v in top_positive.items()]) if not top_positive.empty else '없음'))
                st.warning(f"**📌 '{MAIN_KPI}'에 가장 강력한 음(-)의 영향을 미치는 지표:**\n" + 
                           (', '.join([f"{k} (r={v:.2f})" for k,v in top_negative.items()]) if not top_negative.empty else '없음'))

            st.divider()

            # ==========================================
            # 6. [PART 2] 회귀분석 기반 성과 예측 시나리오
            # ==========================================
            st.header("🔮 [PART 2] 회귀분석 기반 성과 예측 시나리오 & 액션플랜")
            
            action_plans = {
                'CTR': "소재 이미지/비디오 썸네일 교체, 후킹 헤드라인 A/B 테스트, Call-to-Action(CTA) 버튼 직관화",
                'CPM': "타겟팅 범위 유연화, 게재위치 최적화, 머신러닝 학습을 위한 일예산 배분 조정",
                '전환 단가(CPA)': "랜딩페이지 UX/UI 개선, 구매/신청 폼 간소화, 리타겟팅 오디언스 모수 활용",
                'CPC': "품질지수 개선, 부정 키워드 제외 설정, 저효율 키워드/지면 입찰가 하향",
                '노출': "광고 타겟 오디언스 확장, 핵심 지면 중심 머신러닝 노출 비중 확대",
                '클릭': "검색광고 확장소재 추가, 고효율 광고 지면 입찰 비중 확대",
                '전환률': "랜딩페이지 로딩 속도 개선, 상단 핵심 혜택 프로모션 강조"
            }

            if not driver_cols or len(analysis_df) <= len(driver_cols) + 1:
                st.warning("⚠️ 데이터 부족: 회귀분석 모델 생성을 위한 데이터 수 또는 지표가 부족합니다.")
            else:
                try:
                    X = analysis_df[driver_cols].dropna()
                    y = analysis_df.loc[X.index, MAIN_KPI]

                    X_const = sm.add_constant(X)
                    model = sm.OLS(y, X_const).fit()

                    st.markdown(f"**📈 전체 모델 설명력 (R-squared):** `{model.rsquared*100:.1f}%`")
                    
                    params = model.params.drop('const', errors='ignore')
                    analyzed_metrics = list(dict.fromkeys(list(top_positive.index) + list(top_negative.index)))
                    
                    for metric in analyzed_metrics:
                        if metric in params:
                            coef = params[metric]
                            avg_val = X[metric].mean()
                            delta_10 = avg_val * 0.10
                            
                            with st.expander(f"💡 [{metric}] 시뮬레이션 결과 보기", expanded=True):
                                if metric in COST_METRICS:
                                    if coef <= 0:
                                        expected_gain = abs(coef * delta_10)
                                        st.markdown(f"- 비용 단가를 현재 평균({avg_val:,.2f}원)에서 **10% 절감(-{delta_10:,.2f}원)**할 경우:")
                                        st.markdown(f"  - 👉 '{MAIN_KPI}'는 약 **+{expected_gain:.2f}개 증가**할 것으로 기대됩니다.")
                                        st.markdown(f"  - 🛠️ **추천 액션플랜:** {action_plans.get(metric, '단가 최적화 진행')}")
                                    else:
                                        st.error(f"⚠️ [논리 검증 경고: 단가 체증/프리미엄 지면 쏠림]\n- 현재 {metric}(평균 {avg_val:,.2f}원)가 높을수록 전환수가 높게 나타납니다.\n- [원인 진단] 고단가 프리미엄 지면에 전환이 집중되어 발생하는 착시일 수 있습니다.\n- 🛠️ **추천 액션플랜:** 고단가 지면의 실제 ROI 정밀 검증 필요")
                                else:
                                    if coef >= 0:
                                        expected_gain = coef * delta_10
                                        st.markdown(f"- 효율을 현재 평균({avg_val:,.2f})에서 **10% 개선(+{delta_10:,.2f})**할 경우:")
                                        st.markdown(f"  - 👉 '{MAIN_KPI}'는 약 **+{expected_gain:.2f}개 증가**할 것으로 기대됩니다.")
                                        st.markdown(f"  - 🛠️ **추천 액션플랜:** {action_plans.get(metric, '효율 개선 진행')}")
                                    else:
                                        st.error(f"⚠️ [논리 검증 경고: 비효율/노출 낭비 구간 포착]\n- 현재 {metric}(평균 {avg_val:,.2f}) 수치가 높음에도 전환으로 이어지지 않고 있습니다.\n- 🛠️ **추천 액션플랜:** 타겟 오디언스 정밀화 및 저효율 지면 차단")

                except Exception as e:
                    st.error(f"⚠️ 예측 시뮬레이션 생성 실패: ({e})")

            st.divider()

            # ==========================================
            # 7. [PART 3] 매체/소재별 세부 분석
            # ==========================================
            st.header("🔍 [PART 3] 매체/소재별 핵심 동인 세부 분석 (Top 3)")
            
            def run_group_analysis(dataframe, group_col):
                if group_col in dataframe.columns and dataframe[group_col].dropna().nunique() > 0:
                    st.subheader(f"📍 [{group_col}별] 분석")
                    groups = dataframe[group_col].dropna().unique()
                    
                    tabs = st.tabs([str(g) for g in groups])
                    for i, group in enumerate(groups):
                        with tabs[i]:
                            sub_df = dataframe[dataframe[group_col] == group]
                            valid_sub_metrics = [c for c in available_metrics if sub_df[c].dropna().nunique() > 1]

                            if len(sub_df) < 3 or MAIN_KPI not in valid_sub_metrics:
                                st.warning(f"⚠️ 데이터 부족 (3행 미만)")
                                continue

                            sub_corr = sub_df[valid_sub_metrics].corr(method='pearson')
                            if MAIN_KPI in sub_corr.index:
                                kpi_corr_sub = sub_corr[MAIN_KPI].drop(exclude_cols, errors='ignore').dropna()
                                kpi_corr_sorted = kpi_corr_sub.reindex(kpi_corr_sub.abs().sort_values(ascending=False).index)
                                top_3 = kpi_corr_sorted.head(3)

                                st.write(f"**(유효 데이터 {len(sub_df)}행)**")
                                if not top_3.empty:
                                    rank_emojis = ['🥇 1위', '🥈 2위', '🥉 3위']
                                    for idx, (metric_name, corr_val) in enumerate(top_3.items()):
                                        emoji = rank_emojis[idx] if idx < len(rank_emojis) else f"{idx+1}위"
                                        sign_str = "양(+)" if corr_val > 0 else "음(-)"
                                        st.markdown(f"- {emoji} **영향 지표:** `{metric_name}` | 상관계수 r = **{corr_val:+.2f}** ({sign_str}의 영향)")
                                else:
                                    st.write("⚠️ 유의미한 영향 지표를 찾을 수 없습니다.")

            run_group_analysis(analysis_df, '매체')
            run_group_analysis(analysis_df, '소재명')

            st.divider()

            # ==========================================
            # 8. [PART 4] 양방향(증액/감액) Hill S-Curve 시뮬레이션
            # ==========================================
            st.header("💰 [PART 4] 양방향 S-Curve & 한계 효율 시뮬레이션")
            st.markdown("*(적용 알고리즘: 한계 손실 최소화 감액 + 한계 CPA 임계점 증액 + 5% 이하 필터)*")

            campaign_col = [c for c in df.columns if '캠페인' in c and '목적' not in c][0] if any('캠페인' in c and '목적' not in c for c in df.columns) else None
            objective_col = [c for c in df.columns if '목적' in c or 'objective' in c.lower()][0] if any('목적' in c or 'objective' in c.lower() for c in df.columns) else None
            media_col = '매체' if '매체' in df.columns else None
            budget_col = '광고비' if '광고비' in df.columns else None
            kpi_col = '전환수' if '전환수' in df.columns else None
            click_col = '클릭' if '클릭' in df.columns else None

            if campaign_col and budget_col:
                # 데이터 집계 및 파라미터 세팅
                agg_dict = {budget_col: 'sum'}
                if kpi_col: agg_dict[kpi_col] = 'sum'
                if click_col: agg_dict[click_col] = 'sum'

                for m_col in template_metric_cols:
                    if m_col in df.columns and m_col not in [budget_col, kpi_col, click_col]:
                        agg_dict[m_col] = 'mean'

                group_keys = [campaign_col]
                if objective_col: group_keys.append(objective_col)
                if media_col: group_keys.append(media_col)

                camp_summary = df.groupby(group_keys, as_index=False).agg(agg_dict)
                camp_summary['CPA'] = np.where(camp_summary[kpi_col] > 0, camp_summary[budget_col] / camp_summary[kpi_col], np.nan) if kpi_col else np.nan
                camp_summary['CPC'] = np.where(camp_summary[click_col] > 0, camp_summary[budget_col] / camp_summary[click_col], np.nan) if click_col else np.nan

                total_budget = camp_summary[budget_col].sum()
                total_conv = camp_summary[kpi_col].sum() if kpi_col else 0
                avg_account_cpa = total_budget / total_conv if total_conv > 0 else np.nan
                target_cpa = avg_account_cpa if pd.notnull(avg_account_cpa) else np.inf

                def is_brand_search(name):
                    name_lower = str(name).lower().replace(" ", "")
                    return any(kw in name_lower for kw in ['브랜드검색', '브검', 'brandsearch', 'bs'])

                camp_summary['is_fixed'] = camp_summary[campaign_col].apply(is_brand_search)
                flexible_camps = camp_summary[camp_summary['is_fixed'] == False].copy()

                obj_types = []
                for idx, row in flexible_camps.iterrows():
                    o_val = str(row[objective_col]).strip() if objective_col and pd.notnull(row[objective_col]) else "전환"
                    if "트래픽" in o_val or "traffic" in o_val.lower() or "유입" in o_val:
                        obj_types.append("트래픽")
                    else:
                        obj_types.append("전환")
                flexible_camps['obj_type'] = obj_types

                def hill_s_curve(x_budget, max_conv, k_param, n_param=1.5):
                    if x_budget <= 0: return 0.0
                    return max_conv * (x_budget**n_param) / ((x_budget**n_param) + (k_param**n_param))

                # 시뮬레이션 결과 저장용 리스트
                cut_results_txt = []
                add_results_txt = []

                # (1) 감액 시뮬레이션
                sim_cut_amounts = []
                sim_conv_losses = []
                for idx, row in flexible_camps.iterrows():
                    cur_budget, cur_conv, cur_cpa = row[budget_col], (row[kpi_col] if kpi_col else 0), row['CPA']
                    is_inefficient = (row['obj_type'] == '전환' and (pd.isna(cur_cpa) or cur_cpa > target_cpa)) or \
                                     (row['obj_type'] == '트래픽' and row['CPC'] > flexible_camps['CPC'].mean())

                    if not is_inefficient or cur_budget <= 0:
                        sim_cut_amounts.append(0.0); sim_conv_losses.append(0.0)
                        continue

                    max_conv_est = max(cur_conv * 2.0, 1.0)
                    k_est = cur_budget * (max(0.01, (max_conv_est / max(cur_conv, 0.1) - 1)) ** (1 / 1.5))
                    max_cut_limit, step_size = cur_budget * 0.40, max(10000, (cur_budget * 0.40) / 20)
                    sim_cut = 0.0
                    stop_reason = "최대 안전 감액 한도(40%) 도달"

                    while sim_cut + step_size <= max_cut_limit:
                        test_cut = sim_cut + step_size
                        delta_loss = max(0.0, hill_s_curve(cur_budget - sim_cut, max_conv_est, k_est) - hill_s_curve(cur_budget - test_cut, max_conv_est, k_est))
                        marginal_loss_cpa = step_size / delta_loss if delta_loss > 0 else np.inf
                        if marginal_loss_cpa < target_cpa * 0.8:
                            stop_reason = f"전환 손실 급증 임계점 (한계 손실단가: {marginal_loss_cpa:,.0f}원)"
                            break
                        sim_cut += step_size

                    if (sim_cut / cur_budget) <= 0.05:
                        sim_cut, conv_loss = 0.0, 0.0
                    else:
                        conv_loss = max(0.0, cur_conv - hill_s_curve(cur_budget - sim_cut, max_conv_est, k_est))

                    sim_cut_amounts.append(sim_cut)
                    sim_conv_losses.append(conv_loss)

                    if sim_cut > 0:
                        cut_pct = (sim_cut / cur_budget) * 100
                        cpa_str = f"CPA: {cur_cpa:,.0f}원" if pd.notnull(cur_cpa) else "전환 0건"
                        cut_results_txt.append(f"**[{row[campaign_col]}]** ({cpa_str})\n- 추천 감액(-{cut_pct:.1f}%): **-{sim_cut:,.0f}원**\n- 예상 손실: **약 -{conv_loss:.1f}건**\n- 로직: {stop_reason}")

                flexible_camps['cut_amount'] = sim_cut_amounts
                flexible_camps['conv_loss'] = sim_conv_losses
                total_saved_budget = flexible_camps['cut_amount'].sum()
                total_conv_loss = flexible_camps['conv_loss'].sum()

                # (2) 증액 시뮬레이션
                conv_scale_camps = flexible_camps[(flexible_camps['obj_type'] == '전환') & (flexible_camps['cut_amount'] == 0.0)].copy()
                traffic_scale_camps = flexible_camps[(flexible_camps['obj_type'] == '트래픽') & (flexible_camps['cut_amount'] == 0.0)].copy()

                conv_pool = total_saved_budget * 0.80 if not conv_scale_camps.empty else 0
                traffic_pool = total_saved_budget * 0.20 if not traffic_scale_camps.empty else (total_saved_budget - conv_pool)

                total_expected_add_conv, total_expected_add_clicks, valid_inc_count = 0, 0, 0

                if not conv_scale_camps.empty and conv_pool > 0:
                    conv_scale_camps['score'] = 1 / conv_scale_camps['CPA']
                    conv_scale_camps['weight'] = conv_scale_camps['score'] / conv_scale_camps['score'].sum()
                    for _, row in conv_scale_camps.iterrows():
                        max_alloc, cur_budget, cur_conv, cur_cpa = conv_pool * row['weight'], row[budget_col], row[kpi_col], row['CPA']
                        max_conv_est = cur_conv * 2.2
                        k_est = cur_budget * ((max_conv_est / max(cur_conv, 0.1) - 1) ** (1 / 1.5))
                        step_size, sim_add_budget = max(10000, max_alloc / 20), 0.0
                        mCPA_threshold = target_cpa * 1.3 if pd.notnull(target_cpa) else cur_cpa * 1.5
                        stop_reason = "할당 예산 소진"

                        while sim_add_budget + step_size <= max_alloc:
                            delta_conv = hill_s_curve(cur_budget + sim_add_budget + step_size, max_conv_est, k_est) - hill_s_curve(cur_budget + sim_add_budget, max_conv_est, k_est)
                            marginal_cpa = step_size / delta_conv if delta_conv > 0 else np.inf
                            if marginal_cpa > mCPA_threshold:
                                stop_reason = f"한계 CPA 임계점 (mCPA: {marginal_cpa:,.0f}원)"
                                break
                            sim_add_budget += step_size

                        if (sim_add_budget / cur_budget) > 0.05:
                            valid_inc_count += 1
                            add_conv = max(0.0, hill_s_curve(cur_budget + sim_add_budget, max_conv_est, k_est) - cur_conv)
                            total_expected_add_conv += add_conv
                            inc_pct = (sim_add_budget / cur_budget) * 100
                            add_results_txt.append(f"**[{row[campaign_col]}]** (현재 CPA: {cur_cpa:,.0f}원)\n- 추천 증액(+{inc_pct:.1f}%): **+{sim_add_budget:,.0f}원**\n- 예상 증가: **약 +{add_conv:.1f}건**\n- 로직: {stop_reason}")

                if not traffic_scale_camps.empty and traffic_pool > 0:
                    traffic_scale_camps['score'] = 1 / traffic_scale_camps['CPC']
                    traffic_scale_camps['weight'] = traffic_scale_camps['score'] / traffic_scale_camps['score'].sum()
                    for _, row in traffic_scale_camps.iterrows():
                        alloc_budget, cur_budget = traffic_pool * row['weight'], row[budget_col]
                        if (alloc_budget / cur_budget) > 0.05:
                            valid_inc_count += 1
                            add_clicks = alloc_budget / row['CPC'] if pd.notnull(row['CPC']) else 0
                            total_expected_add_clicks += add_clicks
                            inc_pct = (alloc_budget / cur_budget) * 100
                            add_results_txt.append(f"**[{row[campaign_col]}]** (목적: 트래픽)\n- 추천 증액(+{inc_pct:.1f}%): **+{alloc_budget:,.0f}원**\n- 예상 클릭: **약 +{add_clicks:,.1f}개**")

                # 결과 출력 UI 구성
                net_conv_gain = total_expected_add_conv - total_conv_loss

                st.subheader("🎯 최종 시너지 효과 (Net Gain Report)")
                m_col1, m_col2, m_col3 = st.columns(3)
                m_col1.metric("절감된 낭비 예산", f"{total_saved_budget:,.0f}원", f"손실: -{total_conv_loss:.1f}건", delta_color="inverse")
                m_col2.metric("확보 예산 재투입 (증가)", f"{total_saved_budget:,.0f}원", f"추가: +{total_expected_add_conv:.1f}건", delta_color="normal")
                m_col3.metric("최종 전환 순증가(Net Gain)", f"+{net_conv_gain:+.1f}건", "동일 예산 기준 성과", delta_color="normal")
                
                if total_expected_add_clicks > 0:
                    st.info(f"💡 **[보조 유입]** 추가 트래픽(클릭): 약 **+{total_expected_add_clicks:,.1f}개** 순증가 예상")

                with st.expander("세부 캠페인별 시뮬레이션 결과(감액/증액) 보기"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("### 📉 감액 대상 캠페인")
                        if cut_results_txt:
                            for txt in cut_results_txt:
                                st.markdown(txt)
                                st.write("---")
                        else:
                            st.write("감액 대상 캠페인이 없습니다.")
                    with c2:
                        st.markdown("### 📈 증액 대상 캠페인")
                        if add_results_txt:
                            for txt in add_results_txt:
                                st.markdown(txt)
                                st.write("---")
                        else:
                            st.write("증액 대상 캠페인이 없습니다.")
            else:
                st.error("⚠️ 필수 컬럼 미인식: '캠페인' 또는 '광고비' 컬럼을 엑셀에서 확인해주세요.")
