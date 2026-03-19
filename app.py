
import streamlit as st
import psycopg2
import psycopg2.extras
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from dotenv import load_dotenv
load_dotenv()

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Amazon India Analytics",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1a1a2e; }
    [data-testid="stSidebar"] * { color: #e0e0e0 !important; }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1e2a3a, #16213e);
        border: 1px solid #2d4a7a;
        border-radius: 12px;
        padding: 16px !important;
    }
    [data-testid="stMetricValue"] { color: #4fc3f7 !important; font-size: 1.8rem !important; }
    [data-testid="stMetricLabel"] { color: #90caf9 !important; }
    h1 { color: #4fc3f7; }
    h2 { color: #81d4fa; border-bottom: 1px solid #2d4a7a; padding-bottom: 8px; }
    h3 { color: #b3e5fc; }
    .main { background-color: #0d1117; }
    .block-container { padding-top: 1.5rem; }
    div.stButton > button {
        background: linear-gradient(90deg, #1565c0, #0288d1);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 28px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        width: 100%;
        margin-top: 8px;
    }
    div.stButton > button:hover {
        background: linear-gradient(90deg, #0288d1, #4fc3f7);
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME", "ecommerce_analytics"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "")
}

@st.cache_resource
def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def run_query(sql: str, params=None) -> pd.DataFrame:
    conn = get_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg", width=140)
st.sidebar.markdown("## 📊 Analytics Platform")
st.sidebar.markdown("*Amazon India · 2015–2025*")
st.sidebar.divider()

SECTIONS = {
    "🏠 Executive Summary":         "executive",
    "📈 Revenue Analytics":         "revenue",
    "👥 Customer Analytics":        "customer",
    "📦 Product & Brand Analytics": "product",
    "🚚 Operations & Logistics":    "operations",
    "🔮 Advanced Analytics":        "advanced",
}

selected = st.sidebar.radio("Navigate to", list(SECTIONS.keys()), label_visibility="collapsed")
section  = SECTIONS[selected]

st.sidebar.divider()
st.sidebar.markdown("### 🔽 Global Filters")
year_range = st.sidebar.slider("Year Range", 2015, 2025, (2015, 2025))

@st.cache_data(ttl=300)
def get_categories():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT sub_category FROM transactions ORDER BY sub_category")
        return [row[0] for row in cur.fetchall()]

all_cats      = get_categories()
selected_cats = st.sidebar.multiselect("Subcategories", all_cats, default=all_cats)
if not selected_cats:
    selected_cats = all_cats
city_tiers    = st.sidebar.multiselect("City Tier", ["Metro","Tier1","Tier2","Rural"],
                                        default=["Metro","Tier1","Tier2","Rural"])
st.sidebar.divider()
st.sidebar.caption("Built using Streamlit + PostgreSQL")

def FC():
    cats  = ", ".join(f"'{c}'" for c in selected_cats)  if selected_cats else "''"
    tiers = ", ".join(f"'{t}'" for t in city_tiers)     if city_tiers    else "''"
    return f"""
        t.year BETWEEN {year_range[0]} AND {year_range[1]}
        AND t.sub_category IN ({cats})
        AND t.city_tier IN ({tiers})
    """

# ─────────────────────────────────────────────────────────────
# HELPER — show dropdown + button
# ─────────────────────────────────────────────────────────────
def question_selector(section_key: str, questions: list):
    st.markdown("### 📋 Select a Question")
    col1, col2 = st.columns([4, 1])
    with col1:
        choice = st.selectbox("Choose a dashboard question", questions,
                               key=f"sel_{section_key}", label_visibility="collapsed")
    with col2:
        show = st.button("▶ Show Plot", key=f"btn_{section_key}")
    return choice, show

def kpi_row(metrics):
    cols = st.columns(len(metrics))
    for col, (label, value, delta) in zip(cols, metrics):
        col.metric(label, value, delta)


# ═════════════════════════════════════════════════════════════
# SECTION 1 — EXECUTIVE SUMMARY
# ═════════════════════════════════════════════════════════════
if section == "executive":
    st.title("🏠 Executive Summary Dashboard")

    # Always show KPIs at top
    kpi_df = run_query(f"""
        SELECT
            COUNT(order_id)                                                      AS total_orders,
            ROUND(SUM(total_amount_inr)::NUMERIC/1e7, 2)                        AS revenue_cr,
            COUNT(DISTINCT customer_id)                                          AS unique_customers,
            ROUND(AVG(total_amount_inr)::NUMERIC, 0)                            AS avg_order_value,
            ROUND(AVG(customer_rating)::NUMERIC, 2)                             AS avg_rating,
            ROUND((SUM(CASE WHEN is_returned THEN 1 ELSE 0 END)::NUMERIC
                  / COUNT(*) * 100), 1)                                         AS return_rate
        FROM transactions t WHERE {FC()}
    """)
    r = kpi_df.iloc[0]
    kpi_row([
        ("💰 Revenue (Crores)", f"₹{r['revenue_cr']}Cr",       "+12.4%"),
        ("🛒 Total Orders",     f"{int(r['total_orders']):,}",  "+8.1%"),
        ("👥 Customers",        f"{int(r['unique_customers']):,}", "+15.2%"),
        ("📦 Avg Order Value",  f"₹{float(r['avg_order_value']):,.0f}", "+3.5%"),
        ("⭐ Avg Rating",       f"{r['avg_rating']}",           "-0.1"),
        ("↩️ Return Rate",      f"{r['return_rate']}%",         "-0.5%"),
    ])

    st.divider()

    questions = [
        "Q1 · Yearly Revenue Growth (2015–2025)",
        "Q2 · Monthly Sales Heatmap",
        "Q3 · Payment Method Distribution",
        "Q4 · Category Revenue Treemap",
        "Q5 · Business Health Overview",
    ]
    choice, show = question_selector("executive", questions)

    if show:
        if "Q1" in choice:
            yearly = run_query(f"""
                SELECT year,
                       ROUND(SUM(total_amount_inr)::NUMERIC/1e7, 2) AS revenue_cr,
                       COUNT(order_id) AS orders
                FROM transactions t WHERE {FC()}
                GROUP BY year ORDER BY year
            """)
            yearly["revenue_cr"] = yearly["revenue_cr"].astype(float)
            yearly["yoy_growth"] = yearly["revenue_cr"].pct_change() * 100
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=yearly["year"], y=yearly["revenue_cr"],
                                 name="Revenue (Cr)", marker_color="#4fc3f7"))
            fig.add_trace(go.Scatter(x=yearly["year"], y=yearly["yoy_growth"],
                                     name="YoY Growth %", mode="lines+markers",
                                     line=dict(color="#ff7043", width=2)),
                          secondary_y=True)
            fig.update_layout(template="plotly_dark", height=480,
                              title="Annual Revenue & YoY Growth")
            st.plotly_chart(fig, use_container_width=True)

        elif "Q2" in choice:
            heat_df = run_query(f"""
                SELECT year, month,
                       ROUND(SUM(total_amount_inr)::NUMERIC/1e5, 1) AS revenue_lac
                FROM transactions t WHERE {FC()}
                GROUP BY year, month
            """)
            heat_df["revenue_lac"] = heat_df["revenue_lac"].astype(float)
            pivot = heat_df.pivot(index="year", columns="month", values="revenue_lac").fillna(0)
            pivot.columns = ["Jan","Feb","Mar","Apr","May","Jun",
                             "Jul","Aug","Sep","Oct","Nov","Dec"][:len(pivot.columns)]
            fig = px.imshow(pivot, color_continuous_scale="Blues",
                            title="Monthly Revenue Heatmap (₹ Lakhs)")
            fig.update_layout(template="plotly_dark", height=480)
            st.plotly_chart(fig, use_container_width=True)

        elif "Q3" in choice:
            pay_df = run_query(f"""
                SELECT payment_method, COUNT(order_id) AS orders
                FROM transactions t WHERE {FC()}
                GROUP BY payment_method ORDER BY orders DESC
            """)
            fig = px.pie(pay_df, names="payment_method", values="orders",
                         hole=0.45, title="Payment Method Share",
                         color_discrete_sequence=px.colors.sequential.Blues_r)
            fig.update_layout(template="plotly_dark", height=480)
            st.plotly_chart(fig, use_container_width=True)

        elif "Q4" in choice:
            cat_df = run_query(f"""
                SELECT sub_category,
                       ROUND(SUM(total_amount_inr)::NUMERIC/1e7, 2) AS revenue_cr
                FROM transactions t WHERE {FC()}
                GROUP BY sub_category ORDER BY revenue_cr DESC
            """)
            cat_df["revenue_cr"] = cat_df["revenue_cr"].astype(float)
            fig = px.treemap(cat_df, path=["sub_category"], values="revenue_cr",
                             color="revenue_cr", color_continuous_scale="Blues",
                             title="Revenue by Subcategory (₹ Crores)")
            fig.update_layout(template="plotly_dark", height=480)
            st.plotly_chart(fig, use_container_width=True)

        elif "Q5" in choice:
            bh_df = run_query(f"""
                SELECT year,
                       ROUND(SUM(total_amount_inr)::NUMERIC/1e7, 2)  AS revenue_cr,
                       COUNT(DISTINCT customer_id)                    AS customers,
                       ROUND(AVG(customer_rating)::NUMERIC, 2)        AS avg_rating,
                       ROUND((SUM(CASE WHEN is_returned THEN 1 ELSE 0 END)::NUMERIC
                             / COUNT(*) * 100), 1)                    AS return_pct
                FROM transactions t WHERE {FC()}
                GROUP BY year ORDER BY year
            """)
            for c in ["revenue_cr","avg_rating","return_pct"]:
                bh_df[c] = bh_df[c].astype(float)
            fig = make_subplots(rows=2, cols=2,
                                subplot_titles=["Revenue (Cr)","Customers","Avg Rating","Return Rate %"])
            fig.add_trace(go.Scatter(x=bh_df["year"], y=bh_df["revenue_cr"],
                                     mode="lines+markers", line=dict(color="#4fc3f7")), row=1, col=1)
            fig.add_trace(go.Bar(x=bh_df["year"], y=bh_df["customers"],
                                 marker_color="#81d4fa"), row=1, col=2)
            fig.add_trace(go.Scatter(x=bh_df["year"], y=bh_df["avg_rating"],
                                     mode="lines+markers", line=dict(color="#a5d6a7")), row=2, col=1)
            fig.add_trace(go.Scatter(x=bh_df["year"], y=bh_df["return_pct"],
                                     mode="lines+markers", line=dict(color="#ff7043")), row=2, col=2)
            fig.update_layout(template="plotly_dark", height=600,
                              title="Business Health Overview", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════
# SECTION 2 — REVENUE ANALYTICS
# ═════════════════════════════════════════════════════════════
elif section == "revenue":
    st.title("📈 Revenue Analytics")

    questions = [
        "Q6  · Monthly / Quarterly / Yearly Revenue Trends",
        "Q7  · Category Performance Deep Dive",
        "Q8  · Geographic Revenue Analysis",
        "Q9  · Festival Sales Impact",
        "Q10 · Price & Discount Optimization",
    ]
    choice, show = question_selector("revenue", questions)

    # Q6 renders instantly — radio needs immediate response without button
    if "Q6" in choice:
        granularity = st.radio(
            "Granularity", ["Monthly", "Quarterly", "Yearly"],
            horizontal=True, key="q6_gran"
        )
        if granularity == "Monthly":
            df = run_query(f"""
                SELECT year, month,
                       TO_CHAR(DATE_TRUNC('month', order_date),'Mon YYYY') AS period,
                       ROUND(SUM(total_amount_inr)::NUMERIC/1e5, 1) AS revenue_lac
                FROM transactions t WHERE {FC()}
                GROUP BY year, month, DATE_TRUNC('month', order_date)
                ORDER BY year, month
            """)
        elif granularity == "Quarterly":
            df = run_query(f"""
                SELECT year, quarter,
                       CONCAT(year,' Q',quarter) AS period,
                       ROUND(SUM(total_amount_inr)::NUMERIC/1e5, 1) AS revenue_lac
                FROM transactions t WHERE {FC()}
                GROUP BY year, quarter ORDER BY year, quarter
            """)
        else:
            df = run_query(f"""
                SELECT year::TEXT AS period,
                       ROUND(SUM(total_amount_inr)::NUMERIC/1e7, 2) AS revenue_lac
                FROM transactions t WHERE {FC()}
                GROUP BY year ORDER BY year
            """)
        df["revenue_lac"] = df["revenue_lac"].astype(float)
        fig = px.area(
            df, x="period", y="revenue_lac",
            title=f"{granularity} Revenue Trend",
            color_discrete_sequence=["#4fc3f7"]
        )
        fig.update_layout(template="plotly_dark", height=480)
        st.plotly_chart(fig, use_container_width=True)

    elif show:
        if "Q7" in choice:
            cat_perf = run_query(f"""
                SELECT sub_category, year,
                       ROUND(SUM(total_amount_inr)::NUMERIC/1e5, 1) AS revenue_lac
                FROM transactions t WHERE {FC()}
                GROUP BY sub_category, year ORDER BY year, revenue_lac DESC
            """)
            cat_perf["revenue_lac"] = cat_perf["revenue_lac"].astype(float)
            c1, c2 = st.columns(2)
            with c1:
                total = cat_perf.groupby("sub_category")["revenue_lac"].sum().reset_index()
                fig = px.bar(total, x="sub_category", y="revenue_lac",
                             title="Total Revenue by Subcategory",
                             color="revenue_lac", color_continuous_scale="Blues")
                fig.update_layout(template="plotly_dark", height=420, xaxis_tickangle=-30)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                fig = px.line(cat_perf, x="year", y="revenue_lac", color="sub_category",
                              title="Subcategory Revenue Over Years")
                fig.update_layout(template="plotly_dark", height=420)
                st.plotly_chart(fig, use_container_width=True)

        elif "Q8" in choice:
            geo_df = run_query(f"""
                SELECT customer_state, city_tier,
                       ROUND(SUM(total_amount_inr)::NUMERIC/1e5, 1) AS revenue_lac,
                       COUNT(DISTINCT customer_id) AS customers
                FROM transactions t WHERE {FC()}
                GROUP BY customer_state, city_tier ORDER BY revenue_lac DESC
            """)
            geo_df["revenue_lac"] = geo_df["revenue_lac"].astype(float)
            c1, c2 = st.columns(2)
            with c1:
                top = geo_df.groupby("customer_state")["revenue_lac"].sum().reset_index().head(15)
                fig = px.bar(top.sort_values("revenue_lac"),
                             x="revenue_lac", y="customer_state", orientation="h",
                             title="Top 15 States by Revenue", color="revenue_lac",
                             color_continuous_scale="Blues")
                fig.update_layout(template="plotly_dark", height=480)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                tier = geo_df.groupby("city_tier")["revenue_lac"].sum().reset_index()
                fig = px.pie(tier, names="city_tier", values="revenue_lac",
                             title="Revenue by City Tier", hole=0.4,
                             color_discrete_sequence=px.colors.sequential.Blues_r)
                fig.update_layout(template="plotly_dark", height=480)
                st.plotly_chart(fig, use_container_width=True)

        elif "Q9" in choice:
            # Time series with festival markers
            ts_df = run_query(f"""
                SELECT
                    DATE_TRUNC('month', order_date) AS month_date,
                    TO_CHAR(DATE_TRUNC('month', order_date), 'Mon YYYY') AS month_label,
                    ROUND(SUM(total_amount_inr)::NUMERIC/1e5, 1) AS revenue_lac,
                    ROUND(AVG(total_amount_inr)::NUMERIC, 0)     AS avg_aov,
                    BOOL_OR(is_festival_sale)                    AS has_festival,
                    STRING_AGG(DISTINCT festival_name, ', ')
                        FILTER (WHERE festival_name IS NOT NULL)  AS festivals
                FROM transactions t WHERE {FC()}
                GROUP BY DATE_TRUNC('month', order_date)
                ORDER BY month_date
            """)
            ts_df["revenue_lac"] = ts_df["revenue_lac"].astype(float)
            ts_df["avg_aov"]     = ts_df["avg_aov"].astype(float)

            # Split festival vs regular months
            fest_months = ts_df[ts_df["has_festival"] == True]
            reg_months  = ts_df[ts_df["has_festival"] == False]

            # Chart 1 — Time series with festival spikes highlighted
            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(
                x=ts_df["month_label"], y=ts_df["revenue_lac"],
                mode="lines", name="Monthly Revenue",
                line=dict(color="#4fc3f7", width=1.5),
                fill="tozeroy", fillcolor="rgba(79,195,247,0.15)"
            ))
            fig1.add_trace(go.Scatter(
                x=fest_months["month_label"], y=fest_months["revenue_lac"],
                mode="markers", name="Festival Month",
                marker=dict(color="#ff7043", size=10, symbol="star"),
                text=fest_months["festivals"],
                hovertemplate="<b>%{x}</b><br>Revenue: ₹%{y}L<br>Festival: %{text}<extra></extra>"
            ))
            fig1.update_layout(
                template="plotly_dark", height=420,
                title="Monthly Revenue Trend — Festival Months Highlighted ⭐",
                xaxis_tickangle=-45,
                xaxis=dict(tickmode="array",
                           tickvals=ts_df["month_label"][::6].tolist(),
                           ticktext=ts_df["month_label"][::6].tolist())
            )
            st.plotly_chart(fig1, use_container_width=True)

            # Chart 2 — Before / During / After festival comparison
            st.markdown("##### 📊 Festival Impact: Avg Daily Revenue Comparison")
            impact_df = run_query(f"""
                SELECT
                    festival_name,
                    ROUND(AVG(total_amount_inr)::NUMERIC, 0) AS avg_aov,
                    COUNT(order_id)                          AS orders,
                    ROUND(SUM(total_amount_inr)::NUMERIC/1e5, 1) AS revenue_lac
                FROM transactions t
                WHERE {FC()} AND is_festival_sale = TRUE
                  AND festival_name IS NOT NULL
                GROUP BY festival_name
                ORDER BY revenue_lac DESC
            """)
            impact_df["revenue_lac"] = impact_df["revenue_lac"].astype(float)
            impact_df["avg_aov"]     = impact_df["avg_aov"].astype(float)

            c1, c2 = st.columns(2)
            with c1:
                fig2 = px.bar(impact_df, x="festival_name", y="revenue_lac",
                              color="revenue_lac",
                              title="Total Revenue by Festival",
                              color_continuous_scale="Oranges")
                fig2.update_layout(template="plotly_dark", height=380,
                                   xaxis_tickangle=-30)
                st.plotly_chart(fig2, use_container_width=True)
            with c2:
                fig3 = px.bar(impact_df, x="festival_name", y="avg_aov",
                              color="orders",
                              title="Avg Order Value by Festival",
                              color_continuous_scale="Reds")
                fig3.update_layout(template="plotly_dark", height=380,
                                   xaxis_tickangle=-30)
                st.plotly_chart(fig3, use_container_width=True)

    elif "Q10" in choice:
            price_df = run_query(f"""
                SELECT sub_category,
                       ROUND(AVG(original_price_inr)::NUMERIC, 0)  AS avg_price,
                       ROUND(AVG(discount_percent)::NUMERIC, 1)    AS avg_discount,
                       ROUND(AVG(total_amount_inr)::NUMERIC, 0)    AS avg_order_value,
                       COUNT(order_id)                             AS orders
                FROM transactions t WHERE {FC()}
                GROUP BY sub_category
            """)
            for c in ["avg_price","avg_discount","avg_order_value"]:
                price_df[c] = price_df[c].astype(float)
            fig = px.scatter(price_df, x="avg_discount", y="avg_order_value",
                             size="orders", color="sub_category",
                             hover_name="sub_category",
                             title="Discount % vs Avg Order Value by Subcategory",
                             size_max=60)
            fig.update_layout(template="plotly_dark", height=520)
            st.plotly_chart(fig, use_container_width=True)

# ═════════════════════════════════════════════════════════════
# SECTION 3 — CUSTOMER ANALYTICS
# ═════════════════════════════════════════════════════════════
elif section == "customer":
    st.title("👥 Customer Analytics")

    questions = [
        "Q11 · Customer Segmentation (RFM)",
        "Q12 · Purchase Patterns by Age Group",
        "Q13 · Prime vs Non-Prime Behavior",
        "Q14 · Customer Cohort Retention",
        "Q15 · Demographic Heatmap",
    ]
    choice, show = question_selector("customer", questions)

    if show:
        if "Q11" in choice:
            # ── Proper RFM Analysis ──────────────────────────────
            st.markdown("##### 📊 RFM Segmentation Analysis")

            # RFM scores from transactions
            rfm_raw = run_query(f"""
                SELECT
                    customer_id,
                    CURRENT_DATE - MAX(order_date)::DATE        AS recency_days,
                    COUNT(order_id)                             AS frequency,
                    ROUND(SUM(total_amount_inr)::NUMERIC, 0)   AS monetary
                FROM transactions t WHERE {FC()}
                GROUP BY customer_id
            """)
            rfm_raw["recency_days"] = rfm_raw["recency_days"].astype(float)
            rfm_raw["frequency"]    = rfm_raw["frequency"].astype(float)
            rfm_raw["monetary"]     = rfm_raw["monetary"].astype(float)

            # Score into 1-4 buckets
            rfm_raw["R"] = pd.qcut(rfm_raw["recency_days"],  q=4, labels=[4,3,2,1]).astype(int)
            rfm_raw["F"] = pd.qcut(rfm_raw["frequency"].rank(method="first"), q=4, labels=[1,2,3,4]).astype(int)
            rfm_raw["M"] = pd.qcut(rfm_raw["monetary"].rank(method="first"),  q=4, labels=[1,2,3,4]).astype(int)
            rfm_raw["rfm_score"] = rfm_raw["R"] + rfm_raw["F"] + rfm_raw["M"]

            # Segment labels
            def rfm_label(score):
                if score >= 10: return "Champion"
                elif score >= 8: return "Loyal"
                elif score >= 6: return "Potential"
                elif score >= 4: return "At Risk"
                else: return "Lost"

            rfm_raw["segment"] = rfm_raw["rfm_score"].apply(rfm_label)

            seg_summary = rfm_raw.groupby("segment").agg(
                customers   = ("customer_id", "count"),
                avg_recency = ("recency_days", "mean"),
                avg_freq    = ("frequency",    "mean"),
                avg_monetary= ("monetary",     "mean"),
            ).reset_index()
            seg_summary["avg_monetary"] = seg_summary["avg_monetary"].round(0)
            seg_summary["avg_freq"]     = seg_summary["avg_freq"].round(1)
            seg_summary["avg_recency"]  = seg_summary["avg_recency"].round(0)

            c1, c2 = st.columns(2)
            with c1:
                fig = px.bar(seg_summary, x="segment", y="customers",
                             color="avg_monetary",
                             title="Customer Count by RFM Segment",
                             color_continuous_scale="Blues",
                             text="customers")
                fig.update_traces(textposition="outside")
                fig.update_layout(template="plotly_dark", height=420)
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                fig = px.scatter(seg_summary,
                                 x="avg_freq", y="avg_monetary",
                                 size="customers", color="segment",
                                 hover_name="segment",
                                 title="RFM: Frequency vs Monetary (size=customers)",
                                 size_max=60,
                                 labels={"avg_freq":"Avg Orders", "avg_monetary":"Avg Spend (₹)"})
                fig.update_layout(template="plotly_dark", height=420)
                st.plotly_chart(fig, use_container_width=True)

            # Recency vs Monetary scatter (sample for performance)
            sample = rfm_raw.sample(min(2000, len(rfm_raw)), random_state=42)
            fig3 = px.scatter(sample, x="recency_days", y="monetary",
                              color="segment", opacity=0.6,
                              title="Recency vs Monetary Value — All Customers",
                              labels={"recency_days":"Days Since Last Purchase",
                                      "monetary":"Total Spend (₹)"},
                              color_discrete_sequence=px.colors.qualitative.Set2)
            fig3.update_layout(template="plotly_dark", height=420)
            st.plotly_chart(fig3, use_container_width=True)

            # Summary table
            st.markdown("##### 📋 Segment Summary")
            st.dataframe(seg_summary.rename(columns={
                "segment":"Segment", "customers":"Customers",
                "avg_recency":"Avg Recency (days)",
                "avg_freq":"Avg Orders", "avg_monetary":"Avg Spend (₹)"
            }), use_container_width=True)

        elif "Q12" in choice:
            # ── Purchase Frequency + Category Preferences ────────
            st.markdown("##### 📊 Customer Journey & Purchase Patterns")

            journey_df = run_query(f"""
                SELECT age_group,
                       ROUND(AVG(total_amount_inr)::NUMERIC, 0)  AS avg_order_value,
                       COUNT(order_id)                           AS total_orders,
                       COUNT(DISTINCT customer_id)               AS customers,
                       ROUND(COUNT(order_id)::NUMERIC /
                             NULLIF(COUNT(DISTINCT customer_id),0), 1) AS orders_per_customer,
                       ROUND(AVG(discount_percent)::NUMERIC, 1)  AS avg_discount
                FROM transactions t WHERE {FC()}
                GROUP BY age_group ORDER BY avg_order_value DESC
            """)
            for c in ["avg_order_value","orders_per_customer","avg_discount"]:
                journey_df[c] = journey_df[c].astype(float)

            c1, c2 = st.columns(2)
            with c1:
                fig = px.bar(journey_df, x="age_group", y="avg_order_value",
                             color="avg_order_value",
                             title="Avg Order Value by Age Group",
                             color_continuous_scale="Blues", text="avg_order_value")
                fig.update_traces(texttemplate="₹%{text:,.0f}", textposition="outside")
                fig.update_layout(template="plotly_dark", height=400)
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                fig = px.bar(journey_df, x="age_group", y="orders_per_customer",
                             color="orders_per_customer",
                             title="Purchase Frequency (Orders per Customer)",
                             color_continuous_scale="Greens", text="orders_per_customer")
                fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
                fig.update_layout(template="plotly_dark", height=400)
                st.plotly_chart(fig, use_container_width=True)

            # Category preference by age group
            cat_age = run_query(f"""
                SELECT age_group, sub_category,
                       COUNT(order_id) AS orders,
                       ROUND(SUM(total_amount_inr)::NUMERIC/1e5, 1) AS revenue_lac
                FROM transactions t WHERE {FC()}
                GROUP BY age_group, sub_category
            """)
            cat_age["revenue_lac"] = cat_age["revenue_lac"].astype(float)
            pivot = cat_age.pivot_table(index="age_group", columns="sub_category",
                                        values="orders", aggfunc="sum").fillna(0)
            fig2 = px.imshow(pivot, color_continuous_scale="Blues",
                             title="Category Preference Heatmap: Age Group × Subcategory",
                             labels=dict(color="Orders"))
            fig2.update_layout(template="plotly_dark", height=420)
            st.plotly_chart(fig2, use_container_width=True)

            # Spending pattern — bubble chart
            fig3 = px.scatter(journey_df,
                              x="orders_per_customer", y="avg_order_value",
                              size="customers", color="age_group",
                              hover_name="age_group",
                              title="Frequency vs AOV by Age Group (size=customers)",
                              size_max=60,
                              labels={"orders_per_customer":"Orders per Customer",
                                      "avg_order_value":"Avg Order Value (₹)"})
            fig3.update_layout(template="plotly_dark", height=420)
            st.plotly_chart(fig3, use_container_width=True)

        elif "Q13" in choice:
            # ── Prime vs Non-Prime Full Analysis ────────────────
            st.markdown("##### 📊 Prime Membership Impact Analysis")

            prime_df = run_query(f"""
                SELECT
                    is_prime_member,
                    sub_category,
                    ROUND(AVG(total_amount_inr)::NUMERIC, 0)      AS avg_aov,
                    COUNT(order_id)                               AS total_orders,
                    COUNT(DISTINCT customer_id)                   AS customers,
                    ROUND(COUNT(order_id)::NUMERIC /
                          NULLIF(COUNT(DISTINCT customer_id),0), 1) AS orders_per_customer,
                    ROUND(AVG(discount_percent)::NUMERIC, 1)      AS avg_discount,
                    ROUND((AVG(CASE WHEN is_returned THEN 1.0 ELSE 0 END)*100)::NUMERIC,1) AS return_pct
                FROM transactions t WHERE {FC()}
                GROUP BY is_prime_member, sub_category
            """)
            for c in ["avg_aov","orders_per_customer","avg_discount","return_pct"]:
                prime_df[c] = prime_df[c].astype(float)
            prime_df["member_type"] = prime_df["is_prime_member"].map({True:"Prime ✅", False:"Non-Prime ❌"})

            # Overall prime summary
            overall = run_query(f"""
                SELECT
                    is_prime_member,
                    COUNT(DISTINCT customer_id)                        AS customers,
                    ROUND(AVG(total_amount_inr)::NUMERIC, 0)           AS avg_aov,
                    ROUND(COUNT(order_id)::NUMERIC /
                          NULLIF(COUNT(DISTINCT customer_id),0), 1)    AS orders_per_customer,
                    ROUND(AVG(discount_percent)::NUMERIC, 1)           AS avg_discount,
                    ROUND(SUM(total_amount_inr)::NUMERIC/1e7, 2)       AS revenue_cr
                FROM transactions t WHERE {FC()}
                GROUP BY is_prime_member
            """)
            for c in ["avg_aov","orders_per_customer","avg_discount","revenue_cr"]:
                overall[c] = overall[c].astype(float)
            overall["member_type"] = overall["is_prime_member"].map({True:"Prime ✅", False:"Non-Prime ❌"})

            # KPI comparison
            if len(overall) >= 2:
                prime_row    = overall[overall["is_prime_member"]==True].iloc[0]
                nonprime_row = overall[overall["is_prime_member"]==False].iloc[0]
                c1,c2,c3,c4 = st.columns(4)
                c1.metric("Prime AOV",         f"₹{float(prime_row['avg_aov']):,.0f}",
                          f"+{float(prime_row['avg_aov'])-float(nonprime_row['avg_aov']):,.0f} vs Non-Prime")
                c2.metric("Prime Orders/Customer", f"{float(prime_row['orders_per_customer']):.1f}",
                          f"+{float(prime_row['orders_per_customer'])-float(nonprime_row['orders_per_customer']):.1f} vs Non-Prime")
                c3.metric("Prime Revenue",     f"₹{float(prime_row['revenue_cr'])}Cr")
                c4.metric("Non-Prime Revenue", f"₹{float(nonprime_row['revenue_cr'])}Cr")

            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                fig = px.bar(prime_df, x="sub_category", y="avg_aov",
                             color="member_type", barmode="group",
                             title="AOV: Prime vs Non-Prime by Subcategory",
                             color_discrete_map={"Prime ✅":"#ff9800","Non-Prime ❌":"#4fc3f7"})
                fig.update_layout(template="plotly_dark", height=420, xaxis_tickangle=-30)
                st.plotly_chart(fig, use_container_width=True)

            with c2:
                fig = px.bar(prime_df, x="sub_category", y="orders_per_customer",
                             color="member_type", barmode="group",
                             title="Purchase Frequency: Prime vs Non-Prime",
                             color_discrete_map={"Prime ✅":"#ff9800","Non-Prime ❌":"#4fc3f7"})
                fig.update_layout(template="plotly_dark", height=420, xaxis_tickangle=-30)
                st.plotly_chart(fig, use_container_width=True)

            c3, c4 = st.columns(2)
            with c3:
                fig = px.bar(overall, x="member_type", y="revenue_cr",
                             color="member_type",
                             title="Total Revenue: Prime vs Non-Prime",
                             color_discrete_map={"Prime ✅":"#ff9800","Non-Prime ❌":"#4fc3f7"},
                             text="revenue_cr")
                fig.update_traces(texttemplate="₹%{text}Cr", textposition="outside")
                fig.update_layout(template="plotly_dark", height=400, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

            with c4:
                fig = px.bar(prime_df, x="sub_category", y="return_pct",
                             color="member_type", barmode="group",
                             title="Return Rate: Prime vs Non-Prime",
                             color_discrete_map={"Prime ✅":"#ff9800","Non-Prime ❌":"#4fc3f7"})
                fig.update_layout(template="plotly_dark", height=400, xaxis_tickangle=-30)
                st.plotly_chart(fig, use_container_width=True)

        elif "Q14" in choice:
            cohort_df = run_query("""
                SELECT DATE_TRUNC('year', first_order_date) AS cohort_year,
                       rfm_segment,
                       COUNT(customer_id) AS customers
                FROM customers
                GROUP BY cohort_year, rfm_segment
                ORDER BY cohort_year
            """)
            cohort_df["cohort_year"] = cohort_df["cohort_year"].astype(str).str[:4]
            fig = px.bar(cohort_df, x="cohort_year", y="customers", color="rfm_segment",
                         title="Customer Cohorts by Acquisition Year & Segment",
                         color_discrete_sequence=px.colors.sequential.Blues_r)
            fig.update_layout(template="plotly_dark", height=480)
            st.plotly_chart(fig, use_container_width=True)

        elif "Q15" in choice:
            demo_df = run_query(f"""
                SELECT age_group, sub_category,
                       ROUND(SUM(total_amount_inr)::NUMERIC/1e5, 1) AS revenue_lac
                FROM transactions t WHERE {FC()}
                GROUP BY age_group, sub_category
            """)
            demo_df["revenue_lac"] = demo_df["revenue_lac"].astype(float)
            pivot = demo_df.pivot_table(index="age_group", columns="sub_category",
                                        values="revenue_lac", aggfunc="sum").fillna(0)
            fig = px.imshow(pivot, color_continuous_scale="Blues",
                            title="Revenue Heatmap: Age Group × Subcategory")
            fig.update_layout(template="plotly_dark", height=480)
            st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════
# SECTION 4 — PRODUCT & BRAND
# ═════════════════════════════════════════════════════════════
elif section == "product":
    st.title("📦 Product & Brand Analytics")

    questions = [
        "Q16 · Top Products by Revenue",
        "Q17 · Brand Market Share & Performance",
        "Q18 · Seasonal Demand by Category",
        "Q19 · Product Ratings Distribution",
        "Q20 · Active Products per Year",
    ]
    choice, show = question_selector("product", questions)

    if show:
        if "Q16" in choice:
            prod_df = run_query("""
                SELECT product_name, category, brand,
                       ROUND(total_revenue::NUMERIC/1e5, 2)  AS revenue_lac,
                       total_units_sold,
                       ROUND(avg_rating::NUMERIC, 1)         AS avg_rating,
                       ROUND(return_rate::NUMERIC * 100, 1)  AS return_pct
                FROM products
                ORDER BY revenue_lac DESC LIMIT 20
            """)
            for c in ["revenue_lac","avg_rating","return_pct"]:
                prod_df[c] = prod_df[c].astype(float)
            st.dataframe(prod_df, use_container_width=True, height=300)
            fig = px.scatter(prod_df, x="avg_rating", y="revenue_lac",
                             size="total_units_sold", color="return_pct",
                             hover_name="product_name",
                             title="Rating vs Revenue (size=units, color=return rate)",
                             color_continuous_scale="RdYlGn_r", size_max=50)
            fig.update_layout(template="plotly_dark", height=450)
            st.plotly_chart(fig, use_container_width=True)

        elif "Q17" in choice:
            brand_df = run_query(f"""
                SELECT brand,
                       ROUND(SUM(total_amount_inr)::NUMERIC/1e5, 1) AS revenue_lac,
                       COUNT(DISTINCT product_id)                   AS products,
                       ROUND(AVG(customer_rating)::NUMERIC, 2)      AS avg_rating
                FROM transactions t WHERE {FC()}
                GROUP BY brand ORDER BY revenue_lac DESC LIMIT 20
            """)
            brand_df["revenue_lac"] = brand_df["revenue_lac"].astype(float)
            brand_df["avg_rating"]  = brand_df["avg_rating"].astype(float)
            fig = px.bar(brand_df, x="brand", y="revenue_lac",
                         color="avg_rating", title="Top 20 Brands by Revenue",
                         color_continuous_scale="Blues")
            fig.update_layout(template="plotly_dark", height=500, xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

        elif "Q18" in choice:
            inv_df = run_query(f"""
                SELECT sub_category, month, SUM(quantity) AS units_sold
                FROM transactions t WHERE {FC()}
                GROUP BY sub_category, month ORDER BY sub_category, month
            """)
            pivot = inv_df.pivot_table(index="sub_category", columns="month",
                                       values="units_sold", aggfunc="sum").fillna(0)
            pivot.columns = ["Jan","Feb","Mar","Apr","May","Jun",
                             "Jul","Aug","Sep","Oct","Nov","Dec"][:len(pivot.columns)]
            fig = px.imshow(pivot, color_continuous_scale="Blues",
                            title="Monthly Units Sold by Category")
            fig.update_layout(template="plotly_dark", height=500)
            st.plotly_chart(fig, use_container_width=True)

        elif "Q19" in choice:
            rat_df = run_query(f"""
                SELECT sub_category, customer_rating
                FROM transactions t
                WHERE {FC()} AND customer_rating IS NOT NULL
            """)
            rat_df["customer_rating"] = rat_df["customer_rating"].astype(float)
            fig = px.box(rat_df, x="sub_category", y="customer_rating",
                         title="Rating Distribution by Subcategory", color="sub_category")
            fig.update_layout(template="plotly_dark", height=500, showlegend=False,
                              xaxis_tickangle=-30)
            st.plotly_chart(fig, use_container_width=True)

        elif "Q20" in choice:
            launch_df = run_query(f"""
                SELECT year, sub_category,
                       COUNT(DISTINCT product_id) AS active_products
                FROM transactions t WHERE {FC()}
                GROUP BY year, sub_category ORDER BY year
            """)
            fig = px.line(launch_df, x="year", y="active_products", color="sub_category",
                          title="Active Products per Year by Category", markers=True)
            fig.update_layout(template="plotly_dark", height=500)
            st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════
# SECTION 5 — OPERATIONS & LOGISTICS
# ═════════════════════════════════════════════════════════════
elif section == "operations":
    st.title("🚚 Operations & Logistics")

    questions = [
        "Q21 · Delivery Performance Analysis",
        "Q22 · Payment Method Evolution",
        "Q23 · Return Rate Analysis",
        "Q24 · Customer Satisfaction Over Time",
        "Q25 · State-wise Operations Summary",
    ]
    choice, show = question_selector("operations", questions)

    if show:
        if "Q21" in choice:
            del_df = run_query(f"""
                SELECT city_tier,
                       ROUND(AVG(delivery_days)::NUMERIC, 1) AS avg_days,
                       COUNT(*) AS orders
                FROM transactions t WHERE {FC()} AND delivery_days IS NOT NULL
                GROUP BY city_tier
            """)
            del_df["avg_days"] = del_df["avg_days"].astype(float)
            dist_df = run_query(f"""
                SELECT delivery_days, COUNT(*) AS orders
                FROM transactions t
                WHERE {FC()} AND delivery_days BETWEEN 1 AND 15
                GROUP BY delivery_days ORDER BY delivery_days
            """)
            c1, c2 = st.columns(2)
            with c1:
                fig = px.bar(del_df, x="city_tier", y="avg_days",
                             title="Avg Delivery Days by City Tier",
                             color="avg_days", color_continuous_scale="RdYlGn_r")
                fig.update_layout(template="plotly_dark", height=420)
                st.plotly_chart(fig, use_container_width=True)
            with c2:
                fig = px.bar(dist_df, x="delivery_days", y="orders",
                             title="Delivery Days Distribution",
                             color_discrete_sequence=["#4fc3f7"])
                fig.update_layout(template="plotly_dark", height=420)
                st.plotly_chart(fig, use_container_width=True)

        elif "Q22" in choice:
            pay_df = run_query(f"""
                SELECT year, payment_method, COUNT(order_id) AS orders
                FROM transactions t WHERE {FC()}
                GROUP BY year, payment_method ORDER BY year
            """)
            fig = px.area(pay_df, x="year", y="orders", color="payment_method",
                          title="Payment Method Trends 2015–2025",
                          groupnorm="percent")
            fig.update_layout(template="plotly_dark", height=500)
            st.plotly_chart(fig, use_container_width=True)

        elif "Q23" in choice:
            ret_df = run_query(f"""
                SELECT sub_category,
                       ROUND((AVG(CASE WHEN is_returned THEN 1.0 ELSE 0 END) * 100)::NUMERIC, 1) AS return_pct,
                       ROUND(AVG(customer_rating)::NUMERIC, 2) AS avg_rating,
                       COUNT(*) AS orders
                FROM transactions t WHERE {FC()}
                GROUP BY sub_category ORDER BY return_pct DESC
            """)
            ret_df["return_pct"] = ret_df["return_pct"].astype(float)
            ret_df["avg_rating"] = ret_df["avg_rating"].astype(float)
            fig = px.scatter(ret_df, x="avg_rating", y="return_pct",
                             size="orders", color="sub_category", hover_name="sub_category",
                             title="Rating vs Return Rate (size = volume)", size_max=60)
            fig.update_layout(template="plotly_dark", height=500)
            st.plotly_chart(fig, use_container_width=True)

        elif "Q24" in choice:
            sat_df = run_query(f"""
                SELECT year,
                       ROUND(AVG(customer_rating)::NUMERIC, 2) AS avg_rating,
                       ROUND(AVG(delivery_days)::NUMERIC, 1)   AS avg_delivery
                FROM transactions t WHERE {FC()}
                GROUP BY year ORDER BY year
            """)
            sat_df["avg_rating"]  = sat_df["avg_rating"].astype(float)
            sat_df["avg_delivery"]= sat_df["avg_delivery"].astype(float)
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(x=sat_df["year"], y=sat_df["avg_rating"],
                                     name="Avg Rating", mode="lines+markers",
                                     line=dict(color="#4fc3f7")))
            fig.add_trace(go.Bar(x=sat_df["year"], y=sat_df["avg_delivery"],
                                 name="Avg Delivery Days", marker_color="#ff7043",
                                 opacity=0.6), secondary_y=True)
            fig.update_layout(template="plotly_dark", height=500,
                              title="Rating & Delivery Days Over Time")
            st.plotly_chart(fig, use_container_width=True)

        elif "Q25" in choice:
            supply_df = run_query(f"""
                SELECT customer_state,
                       ROUND(AVG(delivery_days)::NUMERIC, 1) AS avg_delivery,
                       ROUND((AVG(CASE WHEN is_returned THEN 1.0 ELSE 0 END)*100)::NUMERIC, 1) AS return_pct,
                       COUNT(order_id) AS orders
                FROM transactions t WHERE {FC()}
                GROUP BY customer_state ORDER BY orders DESC LIMIT 20
            """)
            supply_df["avg_delivery"] = supply_df["avg_delivery"].astype(float)
            supply_df["return_pct"]   = supply_df["return_pct"].astype(float)
            fig = px.scatter(supply_df, x="avg_delivery", y="return_pct",
                             size="orders", hover_name="customer_state",
                             color="avg_delivery", size_max=60,
                             title="Delivery Speed vs Return Rate by State",
                             color_continuous_scale="RdYlGn_r")
            fig.update_layout(template="plotly_dark", height=500)
            st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════
# SECTION 6 — ADVANCED ANALYTICS
# ═════════════════════════════════════════════════════════════
elif section == "advanced":
    st.title("🔮 Advanced Analytics")

    questions = [
        "Q26 · Revenue Forecasting (2026–2027)",
        "Q27 · Market Share Evolution",
        "Q28 · Cross-sell: Age Group × Category",
        "Q29 · Seasonal Planning Calendar",
        "Q30 · Business Intelligence Command Center",
    ]
    choice, show = question_selector("advanced", questions)

    if show:
        if "Q26" in choice:
          st.header("🔮 Predictive Analytics Dashboard")
    
    analysis_type = st.sidebar.selectbox(
        "Select Analysis",
        ["Sales Forecast", "Customer Trends", "Demand Planning", "Scenario Analysis"]
    )
    
    if analysis_type == "Sales Forecast":
        st.subheader("📈 Sales Forecast (2026-2027)")
        
        hist_df = run_query(f"""
            SELECT year,
            ROUND(SUM(total_amount_inr)::NUMERIC/1e7, 2) AS revenue_cr
            FROM transactions t WHERE {FC()}
            GROUP BY year ORDER BY year
        """)
        
        hist_df["revenue_cr"] = hist_df["revenue_cr"].astype(float)
        hist_df["year"] = hist_df["year"].astype(int)
        
        # ✅ FIX: Use only last 3-5 years for trend (not all historical data)
        recent = hist_df[hist_df["year"] >= 2020].copy()  # Use 2020+ only
        
        if len(recent) >= 2:  # Need at least 2 years
            # Calculate average growth rate from recent years
            recent_sorted = recent.sort_values('year')
            year_values = recent_sorted['revenue_cr'].values
            
            # Calculate year-over-year growth rates
            growth_rates = []
            for i in range(1, len(year_values)):
                growth = (year_values[i] - year_values[i-1]) / year_values[i-1]
                growth_rates.append(growth)
            
            # Average growth rate (with more weight to recent years)
            if len(growth_rates) > 0:
                weights = np.linspace(0.5, 1.0, len(growth_rates))
                avg_growth = np.average(growth_rates, weights=weights)
            else:
                avg_growth = 0.05  # Default 5% growth
            
            # Get last actual value
            last_year = recent_sorted['year'].iloc[-1]
            last_val = recent_sorted['revenue_cr'].iloc[-1]
            
            # Forecast using growth rate
            forecast_2026 = last_val * (1 + avg_growth)
            forecast_2027 = forecast_2026 * (1 + avg_growth)
            
            future_years = [2026, 2027]
            forecast = [forecast_2026, forecast_2027]
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(f"{last_year} Revenue", f"₹{last_val:.2f} Cr")
            with col2:
                st.metric("2026 Forecast", f"₹{forecast[0]:.2f} Cr", 
                         delta=f"{(avg_growth * 100):.1f}%")
            with col3:
                st.metric("2027 Forecast", f"₹{forecast[1]:.2f} Cr",
                         delta=f"{(avg_growth * 100):.1f}%")
            
            # Create chart
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=hist_df["year"], y=hist_df["revenue_cr"],
                mode="lines+markers", name="Actual",
                line=dict(color="#4fc3f7", width=3),
                marker=dict(size=8)
            ))
            
            fig.add_trace(go.Scatter(
                x=future_years, y=forecast,
                mode="lines+markers", name="Forecast",
                line=dict(color="#ff9800", width=3, dash="dash"),
                marker=dict(size=10, symbol="diamond")
            ))
            
            # Add confidence band
            upper = [f * 1.1 for f in forecast]
            lower = [f * 0.9 for f in forecast]
            
            fig.add_trace(go.Scatter(
                x=future_years + future_years[::-1],
                y=upper + lower[::-1],
                fill='toself',
                fillcolor='rgba(255, 152, 0, 0.2)',
                line=dict(color='rgba(255,255,255,0)'),
                name='±10% Range',
                showlegend=True
            ))
            
            fig.update_layout(
                template="plotly_dark",
                height=500,
                title=f"Revenue Forecast 2026-2027 (Avg Growth: {avg_growth*100:.1f}%)",
                xaxis_title="Year",
                yaxis_title="Revenue (Crores ₹)"
            )
            
            st.plotly_chart(fig, use_container_width=True)

        elif "Q27" in choice:
            mkt_df = run_query(f"""
                SELECT year, sub_category,
                       ROUND(SUM(total_amount_inr)::NUMERIC/1e5, 1) AS revenue_lac
                FROM transactions t WHERE {FC()}
                GROUP BY year, sub_category ORDER BY year
            """)
            mkt_df["revenue_lac"] = mkt_df["revenue_lac"].astype(float)
            fig = px.area(mkt_df, x="year", y="revenue_lac", color="sub_category",
                          title="Category Market Share Evolution",
                          groupnorm="percent")
            fig.update_layout(template="plotly_dark", height=500)
            st.plotly_chart(fig, use_container_width=True)

        elif "Q28" in choice:
            cross_df = run_query(f"""
                SELECT age_group, sub_category, COUNT(*) AS orders
                FROM transactions t WHERE {FC()}
                GROUP BY age_group, sub_category
            """)
            pivot = cross_df.pivot_table(index="age_group", columns="sub_category",
                                         values="orders", aggfunc="sum").fillna(0)
            fig = px.imshow(pivot, color_continuous_scale="Blues",
                            title="Purchase Overlap: Age Group × Subcategory")
            fig.update_layout(template="plotly_dark", height=500)
            st.plotly_chart(fig, use_container_width=True)

        elif "Q29" in choice:
            seas_df = run_query(f"""
                SELECT month, sub_category,
                       ROUND(SUM(total_amount_inr)::NUMERIC/1e5, 1) AS revenue_lac
                FROM transactions t WHERE {FC()}
                GROUP BY month, sub_category
            """)
            seas_df["revenue_lac"] = seas_df["revenue_lac"].astype(float)
            pivot = seas_df.pivot_table(index="sub_category", columns="month",
                                        values="revenue_lac", aggfunc="sum").fillna(0)
            pivot.columns = ["Jan","Feb","Mar","Apr","May","Jun",
                             "Jul","Aug","Sep","Oct","Nov","Dec"][:len(pivot.columns)]
            fig = px.imshow(pivot, color_continuous_scale="YlOrRd",
                            title="Seasonal Revenue Calendar by Category")
            fig.update_layout(template="plotly_dark", height=500)
            st.plotly_chart(fig, use_container_width=True)

        elif "Q30" in choice:
            st.markdown("##### 📡 Live KPI Monitor")
            cmd_df = run_query(f"""
                SELECT
                    ROUND(SUM(total_amount_inr)::NUMERIC/1e7, 2)                        AS revenue_cr,
                    COUNT(DISTINCT customer_id)                                          AS customers,
                    ROUND(AVG(total_amount_inr)::NUMERIC, 0)                            AS avg_aov,
                    ROUND(AVG(customer_rating)::NUMERIC, 2)                             AS avg_rating,
                    ROUND(AVG(delivery_days)::NUMERIC, 1)                               AS avg_delivery,
                    ROUND((AVG(CASE WHEN is_returned THEN 1.0 ELSE 0.0 END)*100)::NUMERIC, 1) AS return_pct,
                    ROUND(AVG(discount_percent)::NUMERIC, 1)                            AS avg_discount,
                    ROUND((SUM(CASE WHEN is_prime_member THEN 1 ELSE 0 END)::NUMERIC
                          / COUNT(*) * 100), 1)                                         AS prime_pct
                FROM transactions t WHERE {FC()}
            """)
            r = cmd_df.iloc[0]
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Revenue",      f"₹{r['revenue_cr']}Cr")
            c2.metric("Customers",    f"{int(r['customers']):,}")
            c3.metric("Avg AOV",      f"₹{float(r['avg_aov']):,.0f}")
            c4.metric("Avg Rating",   f"⭐ {r['avg_rating']}")
            c5,c6,c7,c8 = st.columns(4)
            c5.metric("Avg Delivery", f"{r['avg_delivery']} days")
            c6.metric("Return Rate",  f"{r['return_pct']}%")
            c7.metric("Avg Discount", f"{r['avg_discount']}%")
            c8.metric("Prime %",      f"{r['prime_pct']}%")

            st.divider()
            cmd2 = run_query(f"""
                SELECT sub_category,
                       ROUND(SUM(total_amount_inr)::NUMERIC/1e5, 1)                          AS revenue_lac,
                       ROUND(AVG(customer_rating)::NUMERIC, 2)                               AS avg_rating,
                       ROUND((AVG(CASE WHEN is_returned THEN 1.0 ELSE 0.0 END)*100)::NUMERIC,1) AS return_pct,
                       COUNT(*) AS orders
                FROM transactions t WHERE {FC()}
                GROUP BY sub_category
            """)
            for c in ["revenue_lac","avg_rating","return_pct"]:
                cmd2[c] = cmd2[c].astype(float)
            fig = px.scatter(cmd2, x="avg_rating", y="revenue_lac",
                             size="orders", color="sub_category",
                             hover_name="sub_category",
                             title="Subcategory Health Matrix",
                             color_continuous_scale="RdYlGn_r", size_max=60)
            fig.update_layout(template="plotly_dark", height=520)
            st.plotly_chart(fig, use_container_width=True)
