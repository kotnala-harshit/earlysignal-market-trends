# Methodology

Each source is scaled to 0–100 within its product/country history. This preserves direction and relative change without pretending unlike units are directly comparable.

**Velocity** blends bounded 7-day growth, 28-day growth, and mean daily change over the latest 14 points. **Cross-platform confidence** combines weighted source breadth (45%), directional agreement (35%), and 14-day completeness (20%). **Geographic diffusion** averages 28-day momentum for the same product across the other configured markets. **Saturation** combines seller density (40%), ad intensity (30%), and incumbent share (30%). **Commercial opportunity** combines purchase intent (40%), sentiment (30%), and current normalized demand (30%).

The default score is:

`0.30 velocity + 0.20 confidence + 0.10 diffusion + 0.25 commercial + 0.15 saturation headroom`

Weights are explicit in `config.yml` and should be calibrated per category on out-of-sample data.

## Lifecycle labels

- **Breakout:** velocity ≥75 and saturation <55.
- **Emerging:** FMOS ≥60.
- **Mature:** saturation ≥65.
- **Watch:** everything else.

## Backtesting

Walk-forward evaluation calculates scores using observations at or before each cutoff, then measures average-source growth over the future horizon. A hit is FMOS ≥60 followed by ≥10% growth. Metrics are precision among selected opportunities and Spearman rank correlation between score and future growth.

Cutoffs start 28 calendar days after the first observation and advance by the configured number of calendar days (7 by default). A product/market is evaluated only when it has observations on both the cutoff and the exact horizon endpoint. Missing endpoints are skipped, so a shorter observation window is never reported as a full-horizon result. Horizon and step must be positive. Insufficient history returns zero samples.

Synthetic results do not validate real-world predictive power. Before commercial use, backtest licensed historical data with realistic availability timestamps, fees, stock-outs, and multiple-comparison controls.

## Limitations

- Platform metrics can be sampled, redefined, manipulated, or delayed.
- Within-series normalization loses absolute market size.
- Product resolution is exact-name based.
- Momentum is vulnerable to seasonality and one-off news.
- Country analysis hides language, state, income, and urban/rural variation.
