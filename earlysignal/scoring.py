import math
from datetime import timedelta

import pandas as pd


def clip(value: float) -> float:
    return round(max(0.0, min(100.0, float(value))), 2)


def _growth(series: pd.Series, days: int) -> float:
    if len(series) < 2:
        return 0
    target = series.index[-1] - timedelta(days=days)
    prior = series.loc[:target]
    baseline = prior.iloc[-1] if len(prior) else series.iloc[0]
    return (series.iloc[-1] - baseline) / max(abs(baseline), 1)


def calculate_scores(observations: pd.DataFrame, weights: dict, as_of=None) -> pd.DataFrame:
    if observations.empty:
        return pd.DataFrame()
    df = observations.copy()
    df["observed_at"] = pd.to_datetime(df["observed_at"])
    cutoff = pd.Timestamp(as_of) if as_of is not None else df["observed_at"].max()
    df = df[df.observed_at <= cutoff]
    source_weights = weights.get("source_weights", {})
    rows = []
    for (country, product, category), group in df.groupby(["country", "product", "category"]):
        pivot = group.pivot_table(index="observed_at", columns="source", values="value", aggfunc="mean").sort_index()
        normalized = pivot.apply(lambda s: 100 * s / max(s.max(), 1))
        combined = normalized.mean(axis=1)
        g7, g28 = _growth(combined, 7), _growth(combined, 28)
        slope = combined.tail(14).diff().mean() if len(combined) > 1 else 0
        velocity = clip(50 + 35 * math.tanh(1.6 * g7) + 12 * math.tanh(g28) + 3 * slope)
        breadth = sum(source_weights.get(s, .7) for s in pivot.columns) / max(sum(source_weights.values()), 1)
        changes = normalized.tail(8).pct_change().replace([math.inf, -math.inf], pd.NA).mean()
        agreement = max((changes > 0).mean(), (changes <= 0).mean()) if len(changes) else 0
        completeness = pivot.tail(14).notna().mean().mean()
        confidence = clip(100 * (.45 * min(breadth, 1) + .35 * agreement + .20 * completeness))
        latest = group.sort_values("observed_at").groupby("source").tail(1)
        sentiment, intent, demand = (latest.sentiment.mean() + 1) / 2, latest.purchase_intent.mean(), combined.iloc[-1] / 100
        commercial = clip(100 * (.40 * intent + .30 * sentiment + .30 * demand))
        sellers = math.tanh(latest.seller_count.mean() / 75)
        saturation = clip(100 * (.40 * sellers + .30 * latest.ad_intensity.mean() + .30 * latest.incumbent_share.mean()))
        other = "IN" if country == "US" else "US"
        peer = df[(df.country == other) & (df.product == product)]
        peer_recent = peer.groupby("observed_at").value.mean().sort_index()
        diffusion = 0 if peer.empty else clip(50 + 35 * math.tanh(_growth(peer_recent, 28)))
        fmos = clip(weights["velocity"] * velocity + weights["confidence"] * confidence +
                    weights["diffusion"] * diffusion + weights["commercial"] * commercial +
                    weights["headroom"] * (100 - saturation))
        stage = "Breakout" if velocity >= 75 and saturation < 55 else "Emerging" if fmos >= 60 else "Mature" if saturation >= 65 else "Watch"
        rows.append({"scored_at": cutoff.date().isoformat(), "country": country, "product": product,
                     "category": category, "velocity": velocity, "confidence": confidence,
                     "diffusion": diffusion, "saturation": saturation, "commercial": commercial,
                     "fmos": fmos, "stage": stage})
    return pd.DataFrame(rows).sort_values("fmos", ascending=False)
