import pandas as pd
import plotly.express as px
import streamlit as st

from earlysignal.backtest import summary
from earlysignal.cli import observations, score
from earlysignal.config import load_config
from earlysignal.db import connect
from earlysignal.ingest import read_csv, upsert

st.set_page_config(page_title="EarlySignal", page_icon="📈", layout="wide")
st.markdown('<meta http-equiv="refresh" content="900">', unsafe_allow_html=True)
st.title("EarlySignal")
st.caption("Product trend intelligence · United States, United Kingdom, Europe + India")
connection, config = connect(), load_config()
data = observations(connection)
if data.empty:
    upsert(connection, read_csv("data/demo_observations.csv"))
    data = observations(connection)
scores = score(connection, config)

country = st.sidebar.selectbox("Market", ["All"] + config["countries"])
category = st.sidebar.selectbox("Category", ["All"] + sorted(scores.category.unique()))
minimum = st.sidebar.slider("Minimum opportunity score", 0, 100, 45)
filtered = scores[scores.fmos >= minimum]
if country != "All":
    filtered = filtered[filtered.country == country]
if category != "All":
    filtered = filtered[filtered.category == category]

top = filtered.iloc[0] if not filtered.empty else None
c1, c2, c3, c4 = st.columns(4)
c1.metric("Opportunities", len(filtered))
c2.metric("Top FMOS", f"{top.fmos:.0f}" if top is not None else "—")
c3.metric("Breakouts", int((filtered.stage == "Breakout").sum()))
c4.metric("Sources", data.source.nunique())

left, right = st.columns([1.4, 1])
with left:
    st.subheader("Opportunity leaderboard")
    st.dataframe(filtered[["country", "product", "category", "fmos", "velocity", "confidence", "saturation", "stage"]],
                 hide_index=True, use_container_width=True,
                 column_config={"fmos": st.column_config.ProgressColumn("FMOS", min_value=0, max_value=100)})
with right:
    st.subheader("Opportunity vs saturation")
    st.plotly_chart(px.scatter(filtered, x="saturation", y="fmos", color="country", size="velocity",
                               hover_name="product", range_x=[0,100], range_y=[0,100]), use_container_width=True)

st.subheader("Market comparison")
comparison = scores.pivot_table(index=["product", "category"], columns="country", values="fmos").reset_index()
markets = [market for market in config["countries"] if market in comparison.columns]
if markets:
    melted = comparison.melt(id_vars=["product", "category"], value_vars=markets, var_name="country", value_name="FMOS")
    st.plotly_chart(px.bar(melted, x="product", y="FMOS", color="country", barmode="group"), use_container_width=True)

product = st.selectbox("Inspect a product", sorted(data["product"].unique()))
history = data[data["product"] == product].groupby(["observed_at", "country", "source"], as_index=False).value.mean()
st.plotly_chart(px.line(history, x="observed_at", y="value", color="source", line_dash="country",
                       title=f"Raw source signals · {product}"), use_container_width=True)

backtests = pd.read_sql_query("SELECT * FROM backtests", connection)
with st.expander("Backtest health"):
    st.info("Run the backtest command to populate evaluation.") if backtests.empty else st.json(summary(backtests))
st.caption("Demo mode · Synthetic data for demonstration, not commercial decisions.")
