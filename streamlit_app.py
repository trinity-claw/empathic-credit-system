"""Empathic Credit System — Dashboard."""

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

st.set_page_config(page_title="ECS Dashboard", page_icon="📊", layout="wide")

page = st.sidebar.radio(
    "Navigation",
    [
        "Score Distribution",
        "Credit Products",
        "Emotional Trends",
        "Fairness",
        "SHAP Explorer",
    ],
)


@st.cache_data
def load_val_data() -> pd.DataFrame:
    path = PROCESSED_DIR / "val.parquet"
    if not path.exists():
        st.error(f"File not found: {path}. Run the training notebooks first.")
        st.stop()
    return pd.read_parquet(path)


def _score_from_proba(proba: float) -> int:
    return max(0, min(1000, int((1 - proba) * 1000)))


def _tier(score: int) -> str:
    if score >= 850:
        return "long_term (R$50k)"
    if score >= 700:
        return "long_term (R$20k)"
    if score >= 550:
        return "short_term (R$8k)"
    return "short_term (R$2k)"


# ---------------------------------------------------------------------------
# Page: Score Distribution
# ---------------------------------------------------------------------------
if page == "Score Distribution":
    st.title("Credit Score Distribution")
    df = load_val_data()

    try:
        import joblib

        model_path = PROJECT_ROOT / "models" / "xgb_financial.pkl"
        cal_path = PROJECT_ROOT / "models" / "calibrator_financial.pkl"
        if model_path.exists() and cal_path.exists():
            model = joblib.load(model_path)
            calibrator = joblib.load(cal_path)
            features = [c for c in df.columns if c != "target"]
            X = df[features].astype("float64")
            raw = model.predict_proba(X)[:, 1]
            cal = calibrator.transform(raw)
            df["score"] = [_score_from_proba(p) for p in cal]
            df["probability"] = cal
        else:
            rng = np.random.default_rng(42)
            df["probability"] = rng.beta(2, 30, len(df))
            df["score"] = [_score_from_proba(p) for p in df["probability"]]
    except Exception:
        rng = np.random.default_rng(42)
        df["probability"] = rng.beta(2, 30, len(df))
        df["score"] = [_score_from_proba(p) for p in df["probability"]]

    col1, col2 = st.columns(2)

    with col1:
        fig = px.histogram(
            df,
            x="score",
            nbins=50,
            color_discrete_sequence=["#4C72B0"],
            title="Score Distribution (0-1000)",
            labels={"score": "Credit Score"},
        )
        fig.add_vline(
            x=850, line_dash="dash", line_color="green", annotation_text="850: Top tier"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.histogram(
            df,
            x="probability",
            nbins=50,
            color_discrete_sequence=["#C44E52"],
            title="Probability of Default Distribution",
            labels={"probability": "P(Default)"},
        )
        fig.add_vline(
            x=0.15,
            line_dash="dash",
            line_color="red",
            annotation_text="Threshold: 0.15",
        )
        st.plotly_chart(fig, use_container_width=True)

    approved = (df["probability"] < 0.15).sum()
    st.metric(
        "Approval Rate", f"{approved / len(df):.1%}", f"{approved:,} of {len(df):,}"
    )


# ---------------------------------------------------------------------------
# Page: Credit Products
# ---------------------------------------------------------------------------
elif page == "Credit Products":
    st.title("Credit Product Distribution")
    df = load_val_data()

    try:
        import joblib

        model_path = PROJECT_ROOT / "models" / "xgb_financial.pkl"
        cal_path = PROJECT_ROOT / "models" / "calibrator_financial.pkl"
        if model_path.exists() and cal_path.exists():
            model = joblib.load(model_path)
            calibrator = joblib.load(cal_path)
            features = [c for c in df.columns if c != "target"]
            X = df[features].astype("float64")
            raw = model.predict_proba(X)[:, 1]
            cal = calibrator.transform(raw)
            df["score"] = [_score_from_proba(p) for p in cal]
            df["decision"] = ["DENIED" if p >= 0.15 else "APPROVED" for p in cal]
        else:
            rng = np.random.default_rng(42)
            cal = rng.beta(2, 30, len(df))
            df["score"] = [_score_from_proba(p) for p in cal]
            df["decision"] = ["DENIED" if p >= 0.15 else "APPROVED" for p in cal]
    except Exception:
        rng = np.random.default_rng(42)
        cal = rng.beta(2, 30, len(df))
        df["score"] = [_score_from_proba(p) for p in cal]
        df["decision"] = ["DENIED" if p >= 0.15 else "APPROVED" for p in cal]

    approved_df = df[df["decision"] == "APPROVED"].copy()
    approved_df["tier"] = approved_df["score"].apply(_tier)

    col1, col2 = st.columns(2)
    with col1:
        tier_counts = approved_df["tier"].value_counts()
        fig = px.pie(
            values=tier_counts.values,
            names=tier_counts.index,
            title="Approved Credit Tier Distribution",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        decision_counts = df["decision"].value_counts()
        fig = px.bar(
            x=decision_counts.index,
            y=decision_counts.values,
            title="Approval vs Denial",
            labels={"x": "Decision", "y": "Count"},
            color=decision_counts.index,
            color_discrete_map={"APPROVED": "#55A868", "DENIED": "#C44E52"},
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Tier Breakdown")
    st.dataframe(
        approved_df.groupby("tier")
        .agg(
            count=("score", "size"),
            avg_score=("score", "mean"),
            min_score=("score", "min"),
            max_score=("score", "max"),
        )
        .reset_index(),
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# Page: Emotional Trends
# ---------------------------------------------------------------------------
elif page == "Emotional Trends":
    st.title("Emotional Trends (Simulated Stream)")
    st.caption(
        "Simulated time series of emotional sensor readings from the mobile app."
    )

    rng = np.random.default_rng(42)
    n_points = 200
    dates = pd.date_range("2026-04-01", periods=n_points, freq="h")

    trend = np.linspace(0, 0.3, n_points)
    stress = np.clip(0.4 + trend + rng.normal(0, 0.08, n_points), 0, 1)
    impulsivity = np.clip(0.35 + 0.5 * trend + rng.normal(0, 0.1, n_points), 0, 1)
    stability = np.clip(0.6 - 0.7 * trend + rng.normal(0, 0.09, n_points), 0, 1)

    emo_df = pd.DataFrame(
        {
            "timestamp": dates,
            "stress_level": stress,
            "impulsivity_score": impulsivity,
            "emotional_stability": stability,
        }
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=emo_df["timestamp"],
            y=emo_df["stress_level"],
            name="Stress",
            line=dict(color="#C44E52"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=emo_df["timestamp"],
            y=emo_df["impulsivity_score"],
            name="Impulsivity",
            line=dict(color="#DD8452"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=emo_df["timestamp"],
            y=emo_df["emotional_stability"],
            name="Stability",
            line=dict(color="#55A868"),
        )
    )
    fig.update_layout(
        title="Emotional Indicators Over Time",
        xaxis_title="Time",
        yaxis_title="Score (0-1)",
        yaxis=dict(range=[0, 1]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

    events = rng.poisson(3, n_points).clip(0, 15)
    event_df = pd.DataFrame({"timestamp": dates, "financial_stress_events_7d": events})
    fig2 = px.bar(
        event_df,
        x="timestamp",
        y="financial_stress_events_7d",
        title="Financial Stress Events (7-day rolling count)",
        color_discrete_sequence=["#4C72B0"],
    )
    st.plotly_chart(fig2, use_container_width=True)


# ---------------------------------------------------------------------------
# Page: Fairness
# ---------------------------------------------------------------------------
elif page == "Fairness":
    st.title("Fairness Analysis")
    df = load_val_data()

    try:
        import joblib

        model_path = PROJECT_ROOT / "models" / "xgb_financial.pkl"
        cal_path = PROJECT_ROOT / "models" / "calibrator_financial.pkl"
        if model_path.exists() and cal_path.exists():
            model = joblib.load(model_path)
            calibrator = joblib.load(cal_path)
            features = [c for c in df.columns if c != "target"]
            X = df[features].astype("float64")
            raw = model.predict_proba(X)[:, 1]
            cal = calibrator.transform(raw)
            df["approved"] = (cal < 0.15).astype(int)
        else:
            rng = np.random.default_rng(42)
            df["approved"] = (rng.beta(2, 30, len(df)) < 0.15).astype(int)
    except Exception:
        rng = np.random.default_rng(42)
        df["approved"] = (rng.beta(2, 30, len(df)) < 0.15).astype(int)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Approval Rate by Age Cohort")
        bins = [18, 30, 40, 50, 60, 120]
        labels = ["18-29", "30-39", "40-49", "50-59", "60+"]
        df["age_cohort"] = pd.cut(df["age"], bins=bins, labels=labels, right=False)
        age_rates = df.groupby("age_cohort", observed=True)["approved"].mean()

        fig = px.bar(
            x=age_rates.index.astype(str),
            y=age_rates.values,
            title="Approval Rate by Age Group",
            labels={"x": "Age Cohort", "y": "Approval Rate"},
            color_discrete_sequence=["#4C72B0"],
        )
        fig.add_hline(
            y=age_rates.max() * 0.8,
            line_dash="dash",
            line_color="red",
            annotation_text="4/5ths Rule Threshold",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Approval Rate by Income Quartile")
        df["income_q"] = pd.qcut(
            df["monthly_income"].fillna(df["monthly_income"].median()),
            q=4,
            labels=["Q1 (Low)", "Q2", "Q3", "Q4 (High)"],
        )
        income_rates = df.groupby("income_q", observed=True)["approved"].mean()

        fig = px.bar(
            x=income_rates.index.astype(str),
            y=income_rates.values,
            title="Approval Rate by Income Quartile",
            labels={"x": "Income Quartile", "y": "Approval Rate"},
            color_discrete_sequence=["#55A868"],
        )
        fig.add_hline(
            y=income_rates.max() * 0.8,
            line_dash="dash",
            line_color="red",
            annotation_text="4/5ths Rule Threshold",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("4/5ths Rule Check")
    st.markdown("""
    The **4/5ths (80%) rule** from US EEOC guidelines states that the approval rate
    for any protected group should be at least 80% of the highest group's rate.
    If a bar falls below the red dashed line, it indicates potential disparate impact.
    """)


# ---------------------------------------------------------------------------
# Page: SHAP Explorer
# ---------------------------------------------------------------------------
elif page == "SHAP Explorer":
    st.title("SHAP Feature Importance Explorer")

    try:
        import joblib

        model_path = PROJECT_ROOT / "models" / "xgb_financial.pkl"
        if not model_path.exists():
            st.warning(
                "Model not found. Run training notebooks first. Showing example data."
            )
            raise FileNotFoundError

        model = joblib.load(model_path)
        from src.api.model_store import FINANCIAL_FEATURES
        from src.explainability.shap_explainer import CreditExplainer

        explainer = CreditExplainer.from_model(model, FINANCIAL_FEATURES)

        st.subheader("Input Features")
        col1, col2, col3 = st.columns(3)
        with col1:
            rev_util = st.slider("Revolving Utilization", 0.0, 2.0, 0.3, 0.01)
            age = st.slider("Age", 18, 100, 45)
            debt_ratio = st.slider("Debt Ratio", 0.0, 5.0, 0.2, 0.01)
            monthly_income = st.number_input("Monthly Income", 0, 100000, 5000)
        with col2:
            past_due_30 = st.number_input("Past Due 30-59", 0, 20, 0)
            past_due_60 = st.number_input("Past Due 60-89", 0, 20, 0)
            past_due_90 = st.number_input("Past Due 90+", 0, 20, 0)
            sentinel = st.selectbox("Had Past Due Sentinel", [0, 1])
        with col3:
            open_lines = st.number_input("Open Credit Lines", 0, 50, 4)
            re_loans = st.number_input("Real Estate Loans", 0, 20, 1)
            dependents = st.number_input("Dependents", 0, 20, 2)

        features = {
            "revolving_utilization": rev_util,
            "age": age,
            "past_due_30_59": float(past_due_30),
            "debt_ratio": debt_ratio,
            "monthly_income": float(monthly_income),
            "open_credit_lines": open_lines,
            "past_due_90": float(past_due_90),
            "real_estate_loans": re_loans,
            "past_due_60_89": float(past_due_60),
            "dependents": float(dependents),
            "had_past_due_sentinel": sentinel,
        }

        X = pd.DataFrame([features])[FINANCIAL_FEATURES].astype("float64")
        result = explainer.explain_one(X)
        explanation = result.to_dict()

        contribs = explanation["contributions"]
        sorted_contribs = sorted(
            contribs.items(), key=lambda x: abs(x[1]), reverse=True
        )
        feat_names = [x[0] for x in sorted_contribs]
        feat_vals = [x[1] for x in sorted_contribs]
        colors = ["#C44E52" if v > 0 else "#4C72B0" for v in feat_vals]

        fig = go.Figure(
            go.Bar(
                x=feat_vals,
                y=feat_names,
                orientation="h",
                marker_color=colors,
            )
        )
        fig.update_layout(
            title=f"SHAP Contributions (base={explanation['base_value']:.3f}, prediction={explanation['prediction']:.3f})",
            xaxis_title="SHAP Value (log-odds)",
            yaxis=dict(autorange="reversed"),
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Top Risk Factors")
        for factor in explanation["top_factors"]:
            direction = (
                "increases" if factor["direction"] == "increases_risk" else "decreases"
            )
            st.write(
                f"- **{factor['feature']}**: {factor['contribution']:+.4f} ({direction} risk)"
            )

    except (FileNotFoundError, Exception):
        st.info("Interactive SHAP requires trained models. Showing static example.")
        example_contribs = {
            "past_due_90": 0.85,
            "revolving_utilization": 0.42,
            "past_due_30_59": 0.28,
            "debt_ratio": 0.15,
            "open_credit_lines": 0.05,
            "had_past_due_sentinel": -0.02,
            "dependents": -0.08,
            "real_estate_loans": -0.12,
            "monthly_income": -0.35,
            "age": -0.52,
            "past_due_60_89": 0.03,
        }
        sorted_c = sorted(
            example_contribs.items(), key=lambda x: abs(x[1]), reverse=True
        )
        fig = go.Figure(
            go.Bar(
                x=[v for _, v in sorted_c],
                y=[k for k, _ in sorted_c],
                orientation="h",
                marker_color=["#C44E52" if v > 0 else "#4C72B0" for _, v in sorted_c],
            )
        )
        fig.update_layout(
            title="SHAP Contributions (Example)",
            xaxis_title="SHAP Value (log-odds)",
            yaxis=dict(autorange="reversed"),
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)
