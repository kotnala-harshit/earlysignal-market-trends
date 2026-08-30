"""Generate deterministic four-market demo observations."""
import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(42)
products = {
    "Waterless skincare": ("Beauty", 1.5, .72),
    "Smart hydration bottle": ("Electronics", 1.25, .68),
    "Walking pad": ("Fitness", .65, .55),
    "Millet snacks": ("Food", 1.05, .76),
    "Portable blender": ("Home", .25, .48),
}
sources = {"search": 1.0, "reddit": .75, "youtube": 1.35, "marketplace": .9, "news": .55}
market_bias = {
    "US": {"Smart hydration bottle": 1.18, "Walking pad": 1.12},
    "GB": {"Walking pad": 1.15, "Waterless skincare": 1.08},
    "EU": {"Waterless skincare": 1.16, "Portable blender": 1.08},
    "IN": {"Waterless skincare": 1.15, "Millet snacks": 1.28},
}
market_lead = {"US": 8, "GB": 3, "EU": 0, "IN": 6}
fields = ["observed_at", "country", "source", "product", "category", "value", "sentiment",
          "purchase_intent", "seller_count", "ad_intensity", "incumbent_share", "is_demo"]
rows, start = [], date(2026, 5, 1)
for day in range(120):
    observed = start + timedelta(days=day)
    for country in market_bias:
        for product, (category, growth, intent) in products.items():
            bias, lead = market_bias[country].get(product, 1), market_lead[country]
            saturation = min(.9, .18 + day * (.004 if growth < .8 else .002))
            base = 18 + 9 * math.exp((day + lead) * growth / 120)
            seasonal = 1 + .08 * math.sin(day / 7)
            for source, factor in sources.items():
                value = max(1, base * seasonal * factor * bias * (1 + random.uniform(-.07, .07)))
                rows.append([observed.isoformat(), country, source, product, category, round(value, 2),
                             round(.25 + growth * .18 + random.uniform(-.06, .06), 2),
                             round(min(.95, intent + random.uniform(-.05, .05)), 2),
                             round(12 + day * saturation / 2), round(saturation, 2),
                             round(min(.9, saturation * .75), 2), 1])
output = Path(__file__).parents[1] / "data" / "demo_observations.csv"
with output.open("w", newline="") as handle:
    writer = csv.writer(handle, lineterminator="\n")
    writer.writerow(fields)
    writer.writerows(rows)
