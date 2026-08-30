from datetime import datetime, timezone

import pandas as pd

from .scoring import calculate_scores


def walk_forward(observations: pd.DataFrame, weights: dict, horizon: int = 14, step: int = 7) -> pd.DataFrame:
    data = observations.copy()
    data["observed_at"] = pd.to_datetime(data.observed_at)
    dates = sorted(data.observed_at.unique())
    rows = []
    for cutoff in dates[28:-horizon:step]:
        scores = calculate_scores(data, weights, cutoff)
        for score in scores.itertuples():
            series = data[(data["country"] == score.country) & (data["product"] == score.product)].groupby("observed_at").value.mean().sort_index()
            before = series.loc[:cutoff]
            after = series[(series.index > cutoff) & (series.index <= cutoff + pd.Timedelta(days=horizon))]
            if before.empty or after.empty:
                continue
            growth = (after.iloc[-1] - before.iloc[-1]) / max(abs(before.iloc[-1]), 1)
            rows.append({"run_at": datetime.now(timezone.utc).isoformat(), "as_of": pd.Timestamp(cutoff).date().isoformat(),
                         "horizon_days": horizon, "country": score.country, "product": score.product,
                         "predicted_score": score.fmos, "future_growth": round(growth, 4),
                         "hit": int(score.fmos >= 60 and growth >= .10)})
    return pd.DataFrame(rows)


def summary(results: pd.DataFrame) -> dict:
    if results.empty:
        return {"precision_at_60": 0, "rank_correlation": 0, "samples": 0}
    selected = results[results.predicted_score >= 60]
    precision = selected.hit.mean() if len(selected) else 0
    correlation = results.predicted_score.rank().corr(results.future_growth.rank())
    return {"precision_at_60": round(float(precision), 3),
            "rank_correlation": round(float(correlation if pd.notna(correlation) else 0), 3),
            "samples": len(results)}
