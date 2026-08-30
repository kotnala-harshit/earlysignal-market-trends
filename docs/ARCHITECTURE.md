# Architecture

EarlySignal is local-first, reproducible, and honest about unavailable APIs. One normalized observation contract separates acquisition from analytics. SQLite supports a single analyst with zero services; the schema can migrate directly to PostgreSQL when concurrent ingestion is required.

## Data flow

1. An adapter produces normalized daily observations.
2. Idempotent upserts prevent duplicate country/source/product/date records.
3. Source series are normalized independently so view counts do not overwhelm search indices.
4. Features are calculated with an explicit `as_of` cutoff.
5. Scores and backtest predictions are persisted for auditability.
6. Streamlit reads the normalized store and scored output.

The grain is one product, source, country, and day. `value` is source-native. Sentiment and purchase intent are bounded proxies; seller count, ad intensity, and incumbent share represent commercial supply. No personal data is required.

## Production extension points

- Schedule adapters with GitHub Actions, cron, or an orchestrator.
- Preserve source request IDs and licenses in a raw object store.
- Use PostgreSQL for concurrent writers and a materialized feature view at scale.
- Add sources only through official APIs or properly licensed providers.
- Monitor missingness, source drift, score distributions, and backtest decay.
