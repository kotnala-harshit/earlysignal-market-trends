from datetime import datetime, timezone

import pandas as pd

from .scoring import calculate_scores

RESULT_COLUMNS = ["run_at", "as_of", "horizon_days", "country", "product",
                  "predicted_score", "future_growth", "hit"]


def walk_forward(observations: pd.DataFrame, weights: dict, horizon: int = 14, step: int = 7) -> pd.DataFrame:
    if horizon <= 0 or step <= 0:
        raise ValueError("horizon and step must be positive numbers of days")
    if observations.empty:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    data = observations.copy()
    data["observed_at"] = pd.to_datetime(data.observed_at)
    rows = []
    cutoffs = pd.date_range(data.observed_at.min() + pd.Timedelta(days=28),
                            data.observed_at.max() - pd.Timedelta(days=horizon),
                            freq=pd.Timedelta(days=step))
    for cutoff in cutoffs:
        scores = calculate_scores(data, weights, cutoff)
        for score in scores.itertuples():
            series = data[(data["country"] == score.country) & (data["product"] == score.product)].groupby("observed_at").value.mean().sort_index()
            endpoint = cutoff + pd.Timedelta(days=horizon)
            if cutoff not in series.index or endpoint not in series.index:
                continue
            growth = (series.loc[endpoint] - series.loc[cutoff]) / max(abs(series.loc[cutoff]), 1)
            rows.append({"run_at": datetime.now(timezone.utc).isoformat(), "as_of": pd.Timestamp(cutoff).date().isoformat(),
                         "horizon_days": horizon, "country": score.country, "product": score.product,
                         "predicted_score": score.fmos, "future_growth": round(growth, 4),
                         "hit": int(score.fmos >= 60 and growth >= .10)})
    return pd.DataFrame(rows, columns=RESULT_COLUMNS)


def summary(results: pd.DataFrame) -> dict:
    if results.empty:
        return {"precision_at_60": 0, "rank_correlation": 0, "samples": 0}
    selected = results[results.predicted_score >= 60]
    precision = selected.hit.mean() if len(selected) else 0
    correlation = results.predicted_score.rank().corr(results.future_growth.rank())
    return {"precision_at_60": round(float(precision), 3),
            "rank_correlation": round(float(correlation if pd.notna(correlation) else 0), 3),
            "samples": len(results)}
