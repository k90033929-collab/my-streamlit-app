import os
import warnings
import urllib.request
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from scipy.stats import spearmanr
from scipy.optimize import minimize
from sklearn.ensemble import RandomForestRegressor
import streamlit as st

warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="디지털 마케팅 캠페인 성과 분석 & 예산 재배치 시뮬레이터",
    page_icon="📊",
    layout="wide"
)

# 폰트 다운로드 및 적용 함수
def set_korean_font():
    font_filename = "NanumGothic.ttf"
    font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    
    if not os.path.exists(font_filename):
        try:
            urllib.request.urlretrieve(font_url, font_filename)
        except Exception as e:
            st.error(f"폰트 다운로드 실패: {e}")
            
    if os.path.exists(font_filename):
        fm.fontManager.addfont(font_filename)
        prop = fm.FontProperties(fname=font_filename)
        font_name = prop.get_name()
        
        plt.rcParams['font.family'] = font_name
        plt.rcParams['font.sans-serif'] = [font_name]
        plt.rc('font', family=font_name)
    
    plt.rcParams['axes.unicode_minus'] = False

st.title("📊 마케팅 캠페인 성과 분석 & 예산 재배치 시뮬레이터")
st.markdown("---")

st.sidebar.header("📁 데이터 업로드")
uploaded_file = st.sidebar.file_uploader("성과 데이터 엑셀(.xlsx) 파일 업로드", type=["xlsx", "xls"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.astype(str).str.strip()

    num_cols = ['광고비', '노출', '클릭', '전환수', '전환매출', 'CTR', 'CPC', 'CPM', '전환률', '전환 단가(CPA)', 'ROAS', '객단가']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if 'CTR' not in df.columns and '노출' in df.columns and '클릭' in df.columns:
        df['CTR'] = np.where(df['노출'] > 0, (df['클릭'] / df['노출']) * 100, 0)
    if '전환률' not in df.columns and '클릭' in df.columns and '전환수' in df.columns:
        df['전환률'] = np.where(df['클릭'] > 0, (df['전환수'] / df['클릭']) * 100, 0)
    if 'ROAS' not in df.columns and '광고비' in df.columns and '전환매출' in df.columns:
        df['ROAS'] = np.where(df['광고비'] > 0, (df['전환매출'] / df['광고비']) * 100, 0)

    tot_b = df['광고비'].sum() if '광고비' in df.columns else 0
    tot_c = df['전환수'].sum() if '전환수' in df.columns else 0
    tot_s = df['전환매출'].sum() if '전환매출' in df.columns else 0
    tot_imp = df['노출'].sum() if '노출' in df.columns else 0
    tot_clk = df['클릭'].sum() if '클릭' in df.columns else 0

    avg_cpa = tot_b / tot_c if tot_c > 0 else 0
    avg_roas = (tot_s / tot_b * 100) if tot_b > 0 else 0
    avg_ctr = (tot_clk / tot_imp * 100) if tot_imp > 0 else 0
    avg_cvr = (tot_c / tot_clk * 100) if tot_clk > 0 else 0
    avg_cpc = tot_b / tot_clk if tot_clk > 0 else 0
    avg_cpm = (tot_b / tot_imp * 1000) if tot_imp > 0 else 0
    avg_aov = tot_s / tot_c if tot_c > 0 else 0

    tab0, tab1, tab2, tab34 = st.tabs([
        "📊 0단계. 종합 대시보드",
        "🎯 1단계. TOP 3 지표 선별",
        "🔮 2단계. TOP 3 지표 개선 시뮬레이션",
        "⚖️ 3&4단계. 예산 재배치(감액/증액) 시뮬레이션"
    ])

    with tab0:
        st.subheader("🌐 전체 캠페인 성과 종합 요약 (Executive Dashboard)")
        
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        m_col1.metric("총 집행 광고비", f"{tot_b:,.0f} 원")
        m_col2.metric("총 전환수", f"{tot_c:,.0f} 건")
        m_col3.metric("총 전환 매출액", f"{tot_s:,.0f} 원")
        m_col4.metric("총 클릭수 (노출수)", f"{tot_clk:,.0f} 회", f"노출 {tot_imp:,.0f}회")

        m_col5, m_col6, m_col7, m_col8 = st.columns(4)
        m_col5.metric("평균 CPA (전환단가)", f"{avg_cpa:,.0f} 원")
        m_col6.metric("평균 ROAS", f"{avg_roas:,.1f}%")
        m_col7.metric("평균 CVR (전환율)", f"{avg_cvr:.2f}%")
        m_col8.metric("평균 CTR (클릭률)", f"{avg_ctr:.2f}%")

        st.markdown("---")
        st.subheader("🌐 매체별 성과 랭킹 TOP 3")

        if '매체' in df.columns and '전환수' in df.columns:
            media_agg = df.groupby('매체').agg({
                '광고비': 'sum', '전환수': 'sum', '전환매출': 'sum', '클릭': 'sum', '노출': 'sum'
            }).reset_index()

            media_agg['CPA'] = np.where(media_agg['전환수'] > 0, media_agg['광고비'] / media_agg['전환수'], 0)
            media_agg['CVR'] = np.where(media_agg['클릭'] > 0, (media_agg['전환수'] / media_agg['클릭']) * 100, 0)
            media_agg['CTR'] = np.where(media_agg['노출'] > 0, (media_agg['클릭'] / media_agg['노출']) * 100, 0)
            media_agg['ROAS'] = np.where(media_agg['광고비'] > 0, (media_agg['전환매출'] / media_agg['광고비']) * 100, 0)
            media_agg['AOV'] = np.where(media_agg['전환수'] > 0, media_agg['전환매출'] / media_agg['전환수'], 0)
            media_agg = media_agg.sort_values(by='전환수', ascending=False)

            top3_cols = st.columns(3)
            for i, (_, row) in enumerate(media_agg.head(3).iterrows()):
                with top3_cols[i]:
                    st.markdown(f"### 🥇 TOP {i+1}. {row['매체']}")
                    st.write(f"• **전환수**: {row['전환수']:,.0f}건 | **예산**: {row['광고비']:,.0f}원")
                    st.write(f"• **CPA**: {row['CPA']:,.0f}원 (평균 대비 {row['CPA']-avg_cpa:+,.0f}원)")
                    st.write(f"• **CVR**: {row['CVR']:.2f}% | **ROAS**: {row['ROAS']:.1f}%")

            st.markdown("---")
            st.subheader("📈 종합 성과 시각화 리포트")

            # 💡 차트 생성 직전 폰트 강제 주입
            set_korean_font()

            fig, axes = plt.subplots(2, 3, figsize=(18, 10))
            sns.set_style("whitegrid")

            ax1 = axes[0, 0]
            sns.barplot(data=media_agg, x='매체', y='광고비', color='#A0C4FF', alpha=0.8, ax=ax1)
            ax2 = ax1.twinx()
            sns.lineplot(data=media_agg, x='매체', y='전환수', color='#E63946', marker='o', linewidth=2.5, ax=ax2)
            ax1.set_title('1. 매체별 광고비 & 전환수', fontsize=11, fontweight='bold')

            ax_cpa = axes[0, 1]
            sns.barplot(data=media_agg, x='매체', y='CPA', palette='Blues_r', ax=ax_cpa)
            ax_cpa.axhline(avg_cpa, color='red', linestyle='--', label=f'평균 CPA ({avg_cpa:,.0f}원)')
            ax_cpa.set_title('2. 매체별 평균 CPA (전환단가)', fontsize=11, fontweight='bold')
            ax_cpa.legend(fontsize=9)

            ax_cvr = axes[0, 2]
            sns.barplot(data=media_agg, x='매체', y='CVR', color='#4EA8DE', alpha=0.7, ax=ax_cvr)
            ax_ctr = ax_cvr.twinx()
            sns.lineplot(data=media_agg, x='매체', y='CTR', color='#FFB703', marker='s', linewidth=2.5, ax=ax_ctr)
            ax_cvr.set_title('3. 매체별 전환율(CVR) & 클릭률(CTR)', fontsize=11, fontweight='bold')

            campaign_col_name = [c for c in df.columns if '캠페인' in c and '목적' not in c]
            ax_camp = axes[1, 0]
            if '전환수' in df.columns and 'ROAS' in df.columns:
                camp_agg_plot = df.groupby(['매체'] if '매체' in df.columns else campaign_col_name[0]).agg({'전환수':'sum', 'ROAS':'mean', '광고비':'sum'}).reset_index()
                sns.scatterplot(data=camp_agg_plot, x='전환수', y='ROAS', size='광고비', sizes=(40, 400), hue='ROAS', palette='viridis', alpha=0.8, ax=ax_camp)
                ax_camp.axhline(avg_roas, color='gray', linestyle=':', label=f'평균 ROAS({avg_roas:.0f}%)')
                ax_camp.set_title('4. 매체/캠페인별 전환수 & ROAS 분포', fontsize=11, fontweight='bold')

            product_col = [c for c in df.columns if any(kw in c for kw in ['상품', '목적', '구분', '유형']) and '캠페인' not in c]
            ax_pie = axes[1, 1]
            if product_col and '전환수' in df.columns:
                p_data = df.groupby(product_col[0])['전환수'].sum().nlargest(5)
                ax_pie.pie(p_data, labels=p_data.index, autopct='%1.1f%%', startangle=140, colors=sns.color_palette("Set2"))
                ax_pie.set_title(f'5. 주요 {product_col[0]}별 전환 비중', fontsize=11, fontweight='bold')

            ax_scat = axes[1, 2]
            if '클릭' in df.columns and '전환수' in df.columns:
                sns.scatterplot(data=df, x='클릭', y='전환수', hue='매체' if '매체' in df.columns else None, alpha=0.7, s=60, ax=ax_scat)
                ax_scat.set_title('6. 클릭수 대비 전환수 효율 상관성', fontsize=11, fontweight='bold')

            plt.tight_layout()
            st.pyplot(fig)

    MAIN_KPI = '전환수'
    COST_METRICS = ['전환 단가(CPA)', 'CPC', 'CPM']
    TARGET_EVAL_METRICS = ['노출', '클릭', '전환수', 'CTR', 'CPC', 'CPM', '전환률', '객단가']
    eval_feature_cols = [c for c in TARGET_EVAL_METRICS if c in df.columns and c != MAIN_KPI]

    if len(eval_feature_cols) >= 2 and MAIN_KPI in df.columns:
        analysis_df = df.dropna(subset=[MAIN_KPI]).copy()
        X_df = analysis_df[eval_feature_cols].fillna(analysis_df[eval_feature_cols].mean())
        y_df = analysis_df[MAIN_KPI]

        spearman_scores = {}
        for col in eval_feature_cols:
            rho, _ = spearmanr(X_df[col], y_df)
            if np.isnan(rho): rho = 0.0
            if col in COST_METRICS and rho > 0: rho = -abs(rho)
            spearman_scores[col] = abs(rho)

        rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        rf_model.fit(X_df, y_df)
        rf_importances = dict(zip(eval_feature_cols, rf_model.feature_importances_))

        ensemble_scores = {}
        for col in eval_feature_cols:
            ensemble_scores[col] = (spearman_scores[col] * 0.5) + (rf_importances[col] * 0.5)

        sorted_ensemble = sorted(ensemble_scores.items(), key=lambda x: x[1], reverse=True)
        top3_metrics = [item[0] for item in sorted_ensemble[:3]]

        with tab1:
            st.subheader("🎯 메인 KPI 영향 지표 평가 (상관분석 + RF 중요도 + 도메인 가드레일)")
            
            t1_col1, t1_col2 = st.columns([1, 1])
            with t1_col1:
                st.markdown("### 📊 Top 3 핵심 영향 지표")
                for rank, (m_name, score) in enumerate(sorted_ensemble[:3], 1):
                    st.info(f"**{rank}위: {m_name}** (앙상블 점수: {score:.3f} | Spearman: {spearman_scores[m_name]:.2f}, RF: {rf_importances[m_name]:.2f})")

            with t1_col2:
                top_df = pd.DataFrame(sorted_ensemble, columns=['지표', '앙상블 점수'])
                set_korean_font()
                fig_top, ax_top = plt.subplots(figsize=(8, 4))
                colors = ['#1D3557' if i < 3 else '#A8DADC' for i in range(len(top_df))]
                sns.barplot(data=top_df, x='앙상블 점수', y='지표', palette=colors, ax=ax_top)
                ax_top.set_title('메인 KPI 영향 지표 선별 결과 (TOP 3 강조)', fontsize=12, fontweight='bold')
                st.pyplot(fig_top)

        with tab2:
            st.subheader("🔮 TOP 3 지표 10% 개선 시 시뮬레이션 (직관적 수치 변화 브리핑)")
            st.write("지표가 10% 개선되었을 때 예상되는 순증가 전환 건수를 텍스트 형태로 산출합니다.")

            for metric in top3_metrics:
                avg_val = X_df[metric].mean()
                if avg_val <= 0: continue

                delta_sign = -1.0 if metric in COST_METRICS else 1.0
                target_val = avg_val * (1 + delta_sign * 0.10)

                is_ratio_metric = metric in ['CTR', '전환률']
                if is_ratio_metric:
                    display_multiplier = 100.0 if avg_val <= 1.0 else 1.0
                    curr_disp = avg_val * display_multiplier
                    target_disp = target_val * display_multiplier
                    val_text = f"현재 {curr_disp:.2f}% → 10% 개선 시 {target_disp:.2f}%"
                else:
                    val_text = f"현재 {avg_val:,.2f} → 10% 개선 시 {target_val:,.2f}"

                X_log = np.log1p(X_df[[metric]])
                log_rf = RandomForestRegressor(n_estimators=50, random_state=42)
                log_rf.fit(X_log, y_df)
                
                pred_base_log = log_rf.predict(np.log1p([[avg_val]]))[0]
                pred_target_log = log_rf.predict(np.log1p([[target_val]]))[0]
                gain_log = max(0.0, pred_target_log - pred_base_log)

                X_cf_base = X_df.copy()
                X_cf_target = X_df.copy()
                X_cf_target[metric] = target_val

                pred_base_rf = rf_model.predict(X_cf_base).mean()
                pred_target_rf = rf_model.predict(X_cf_target).mean()
                gain_rf = max(0.0, pred_target_rf - pred_base_rf)

                blended_gain = (gain_log + gain_rf) / 2.0
                action_type = "10% 절감" if metric in COST_METRICS else "10% 개선"

                st.success(f"📌 **[{metric}] {action_type}** ({val_text})\n\n👉 **기대 전환 추가 증가량:** 약 **+{blended_gain:.1f}건** 순증가")

        with tab34:
            st.subheader("⚖️ 예산 재배치 감액 & 증액 시뮬레이션 (1안 vs 2안 시나리오)")

            campaign_col = campaign_col_name[0] if campaign_col_name else None
            objective_col = [c for c in df.columns if '목적' in c or 'objective' in c.lower()][0] if any('목적' in c or 'objective' in c.lower() for c in df.columns) else None
            media_col = '매체' if '매체' in df.columns else None
            budget_col = '광고비' if '광고비' in df.columns else None
            kpi_col = '전환수' if '전환수' in df.columns else None

            if budget_col and kpi_col:
                group_keys = []
                if campaign_col: group_keys.append(campaign_col)
                if media_col and (not campaign_col or df[campaign_col].nunique() <= 1):
                    group_keys.append(media_col)
                if objective_col and objective_col not in group_keys:
                    group_keys.append(objective_col)

                camp_summary = df.groupby(group_keys, as_index=False).agg({budget_col: 'sum', kpi_col: 'sum'})
                camp_summary['캠페인명'] = camp_summary[group_keys].astype(str).agg(' - '.join, axis=1)
                camp_summary['CPA'] = np.where(camp_summary[kpi_col] > 0, camp_summary[budget_col] / camp_summary[kpi_col], np.nan)

                tot_b_sum = camp_summary[budget_col].sum()
                tot_c_sum = camp_summary[kpi_col].sum()
                target_cpa = tot_b_sum / tot_c_sum if tot_c_sum > 0 else np.nan

                camp_summary['is_fixed'] = camp_summary['캠페인명'].apply(
                    lambda x: any(kw in str(x).lower().replace(" ", "") for kw in ['브랜드검색', '브검', 'brandsearch', 'bs'])
                )
                flexible_camps = camp_summary[camp_summary['is_fixed'] == False].copy()

                def hill_s_curve(x_budget, max_conv, k_param, n_param=1.5):
                    if x_budget <= 0: return 0.0
                    return max_conv * (x_budget**n_param) / ((x_budget**n_param) + (k_param**n_param))

                cut_amounts_1, conv_losses_1 = [], []
                cut_amounts_2, conv_losses_2 = [], []

                for idx, row in flexible_camps.iterrows():
                    cur_budget = row[budget_col]
                    cur_conv = row[kpi_col]
                    cur_cpa = row['CPA']

                    if pd.isna(cur_cpa) or cur_cpa <= target_cpa or cur_budget <= 0 or cur_conv < 1.0:
                        cut_amounts_1.append(0.0); conv_losses_1.append(0.0)
                        cut_amounts_2.append(0.0); conv_losses_2.append(0.0)
                        continue

                    max_conv_est = cur_conv * 2.0
                    k_est = cur_budget * (max(0.01, (max_conv_est / max(cur_conv, 0.1) - 1)) ** (1 / 1.5))
                    s_curve_limit_cut = cur_budget * 0.40
                    step_size = max(10000, cur_budget * 0.02)
                    sim_cut = 0.0

                    while sim_cut + step_size <= s_curve_limit_cut:
                        test_cut = sim_cut + step_size
                        conv_prev = hill_s_curve(cur_budget - sim_cut, max_conv_est, k_est)
                        conv_next = hill_s_curve(cur_budget - test_cut, max_conv_est, k_est)
                        delta_loss = max(0.0, conv_prev - conv_next)
                        mcpa_loss = step_size / delta_loss if delta_loss > 0 else np.inf

                        if mcpa_loss < target_cpa * 0.8: break
                        sim_cut += step_size

                    c1 = 0.0 if (sim_cut / cur_budget) <= 0.05 else sim_cut
                    l1 = max(0.0, cur_conv - hill_s_curve(cur_budget - c1, max_conv_est, k_est)) if c1 > 0 else 0.0

                    c2 = c1 * 0.5
                    l2 = max(0.0, cur_conv - hill_s_curve(cur_budget - c2, max_conv_est, k_est)) if c2 > 0 else 0.0

                    cut_amounts_1.append(c1); conv_losses_1.append(l1)
                    cut_amounts_2.append(c2); conv_losses_2.append(l2)

                flexible_camps['cut_1'] = cut_amounts_1
                flexible_camps['loss_1'] = conv_losses_1
                flexible_camps['cut_2'] = cut_amounts_2
                flexible_camps['loss_2'] = conv_losses_2

                total_saved_1, total_loss_1 = flexible_camps['cut_1'].sum(), flexible_camps['loss_1'].sum()
                total_saved_2, total_loss_2 = flexible_camps['cut_2'].sum(), flexible_camps['loss_2'].sum()

                scale_camps = flexible_camps[(flexible_camps['cut_1'] == 0.0) & (flexible_camps['CPA'] <= target_cpa)].copy()

                def run_scale_simulation(saved_budget, scale_df):
                    if scale_df.empty or saved_budget <= 0: return 0.0, {}
                    n_camps = len(scale_df)
                    def objective_func(weights):
                        est_returns = np.sum(weights * (1 / scale_df['CPA'].fillna(target_cpa)))
                        risk = np.sqrt(np.sum((weights ** 2) * (scale_df['CPA'].fillna(target_cpa) ** 2)))
                        return -(est_returns / (risk + 1e-5))

                    max_weight_cap = 0.50 if n_camps > 1 else 1.0
                    bounds = tuple((0.0, max_weight_cap) for _ in range(n_camps))
                    constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
                    init_w = np.array([1.0 / n_camps] * n_camps)

                    opt_res = minimize(objective_func, init_w, method='SLSQP', bounds=bounds, constraints=constraints)
                    opt_weights = opt_res.x if opt_res.success else init_w

                    total_add_conv, details = 0.0, {}
                    idx_counter = 0

                    for _, row in scale_df.iterrows():
                        alloc_budget = saved_budget * opt_weights[idx_counter]
                        idx_counter += 1

                        cur_budget = row[budget_col]
                        cur_conv = row[kpi_col]
                        
                        max_conv_est = cur_conv * 2.0
                        k_est = cur_budget * ((max_conv_est / max(cur_conv, 0.1) - 1) ** (1 / 1.5))

                        step_size = max(10000, alloc_budget / 20)
                        sim_add_budget = 0.0
                        mcpa_threshold = target_cpa * 1.3

                        while sim_add_budget + step_size <= alloc_budget:
                            next_b = cur_budget + sim_add_budget + step_size
                            prev_b = cur_budget + sim_add_budget
                            
                            delta_c = hill_s_curve(next_b, max_conv_est, k_est) - hill_s_curve(prev_b, max_conv_est, k_est)
                            marginal_cpa = step_size / delta_c if delta_c > 0 else np.inf

                            if marginal_cpa > mcpa_threshold: break
                            sim_add_budget += step_size

                        if (sim_add_budget / cur_budget) <= 0.05: continue

                        add_conv = max(0.0, hill_s_curve(cur_budget + sim_add_budget, max_conv_est, k_est) - cur_conv)
                        total_add_conv += add_conv
                        details[row['캠페인명']] = (sim_add_budget, add_conv)

                    return total_add_conv, details

                add_conv_1, details_1 = run_scale_simulation(total_saved_1, scale_camps)
                add_conv_2, details_2 = run_scale_simulation(total_saved_2, scale_camps)

                net_gain_1 = add_conv_1 - total_loss_1
                net_gain_2 = add_conv_2 - total_loss_2

                st.markdown("### 📉 3단계. 저효율 캠페인 감액 시뮬레이션")
                has_cuts = False
                for _, row in flexible_camps[flexible_camps['cut_1'] > 0].iterrows():
                    has_cuts = True
                    cur_budget = row[budget_col]
                    c1, l1 = row['cut_1'], row['loss_1']
                    c2, l2 = row['cut_2'], row['loss_2']
                    pct1 = (c1 / cur_budget) * 100
                    pct2 = (c2 / cur_budget) * 100

                    with st.expander(f"📌 캠페인: [{row['캠페인명']}] (기존 예산: {cur_budget:,.0f}원 | CPA: {row['CPA']:,.0f}원)"):
                        st.write(f"• **1안(원안)** : 기존 {cur_budget:,.0f}원 ➔ **조정 {cur_budget-c1:,.0f}원** (`-{c1:,.0f}원`, -{pct1:.1f}%) | 예상 손실: `-{l1:.1f}건`")
                        st.write(f"• **2안(50%)** : 기존 {cur_budget:,.0f}원 ➔ **조정 {cur_budget-c2:,.0f}원** (`-{c2:,.0f}원`, -{pct2:.1f}%) | 예상 손실: `-{l2:.1f}건`")

                if not has_cuts:
                    st.info("💡 감액 추천 대상 캠페인이 없습니다. (모든 캠페인의 CPA가 평균 이하이거나 정상 범위입니다)")

                st.markdown("---")
                st.markdown("### 📈 4단계. 고효율 캠페인 증액 시뮬레이션")
                
                col_sc1, col_sc2 = st.columns(2)
                with col_sc1:
                    st.markdown("#### [ 1안 감액 연동 증액 추천 ]")
                    for camp_name, (add_b, add_c) in details_1.items():
                        orig_b = scale_camps[scale_camps['캠페인명'] == camp_name][budget_col].values[0]
                        st.write(f"• **{camp_name}**\n  - 기존 {orig_b:,.0f}원 ➔ **조정 {orig_b+add_b:,.0f}원** (`+{add_b:,.0f}원`)\n  - 기대 추가 전환: `+{add_c:.1f}건`")

                with col_sc2:
                    st.markdown("#### [ 2안(50%) 감액 연동 증액 추천 ]")
                    for camp_name, (add_b, add_c) in details_2.items():
                        orig_b = scale_camps[scale_camps['캠페인명'] == camp_name][budget_col].values[0]
                        st.write(f"• **{camp_name}**\n  - 기존 {orig_b:,.0f}원 ➔ **조정 {orig_b+add_b:,.0f}원** (`+{add_b:,.0f}원`)\n  - 기대 추가 전환: `+{add_c:.1f}건`")

                st.markdown("---")
                st.markdown("### 📋 최종 시뮬레이션 비교 리포트")
                
                rep_col1, rep_col2 = st.columns(2)
                with rep_col1:
                    st.info(f"""
                    **📊 [1안: 원안 제안 (적극적 예산 재배치)]**
                    - 감액 절감 예산 총액 : `-{total_saved_1:,.0f}원`
                    - 감액에 따른 전환 손실: `-{total_loss_1:.1f}건`
                    - 고효율 캠페인 재투입 : `+{total_saved_1:,.0f}원` (추가 전환: `+{add_conv_1:.1f}건`)
                    
                    🎯 **최종 전환 순증가 (Net Gain): 약 +{net_gain_1:+.1f}건**
                    """)

                with rep_col2:
                    st.success(f"""
                    **📊 [2안: 50% 보수적 제안 (리스크 관리형 재배치)]**
                    - 감액 절감 예산 총액 : `-{total_saved_2:,.0f}원`
                    - 감액에 따른 전환 손실: `-{total_loss_2:.1f}건`
                    - 고효율 캠페인 재투입 : `+{total_saved_2:,.0f}원` (추가 전환: `+{add_conv_2:.1f}건`)
                    
                    🎯 **최종 전환 순증가 (Net Gain): 약 +{net_gain_2:+.1f}건**
                    """)

else:
    st.info("👈 좌측 사이드바에서 분석할 마케팅 성과 엑셀(.xlsx) 파일을 업로드해주세요.")
