{{ config(
    materialized='incremental',
    unique_key='published_date',
    column_types={'published_date': 'DATE'}
) }}

WITH staging AS (
    SELECT * FROM {{ ref('stg_scraped_news') }}

    {% if is_incremental() %}
        WHERE published_date >= (SELECT COALESCE(MAX(published_date), CAST('1970-01-01' AS DATE)) FROM {{ this }})
    {% endif %}
),

flagged_articles AS (
    SELECT
        published_date,
        is_indonesia_relevant,
        {{ gpr_flags() }}
    FROM staging
),

daily_aggregates AS (
    SELECT
        published_date,
        -- total_articles counts only Indonesia-relevant articles —
        -- this is the denominator for a true country-specific index
        COUNT(*) FILTER (WHERE is_indonesia_relevant = 1) AS total_articles,

        SUM(CASE WHEN is_indonesia_relevant = 1 THEN is_war_threat       ELSE 0 END) AS count_war_threat,
        SUM(CASE WHEN is_indonesia_relevant = 1 THEN is_peace_threat     ELSE 0 END) AS count_peace_threat,
        SUM(CASE WHEN is_indonesia_relevant = 1 THEN is_military_buildup ELSE 0 END) AS count_military_buildup,
        SUM(CASE WHEN is_indonesia_relevant = 1 THEN is_war_act          ELSE 0 END) AS count_war_act,
        SUM(CASE WHEN is_indonesia_relevant = 1 THEN is_terror_act       ELSE 0 END) AS count_terror_act

    FROM flagged_articles
    GROUP BY 1
)

SELECT
    published_date,
    total_articles,

    /* --- Sub-category indices (% of Indonesia-relevant articles) --- */
    ROUND((count_war_threat       * 100.0 / NULLIF(total_articles, 0)), 4) AS idx_war_threat,
    ROUND((count_peace_threat     * 100.0 / NULLIF(total_articles, 0)), 4) AS idx_peace_threat,
    ROUND((count_military_buildup * 100.0 / NULLIF(total_articles, 0)), 4) AS idx_military_buildup,
    ROUND((count_war_act          * 100.0 / NULLIF(total_articles, 0)), 4) AS idx_war_act,
    ROUND((count_terror_act       * 100.0 / NULLIF(total_articles, 0)), 4) AS idx_terror_act,

    /* --- Composite indices --- */
    ROUND(((count_war_threat + count_peace_threat + count_military_buildup) * 100.0
        / NULLIF(total_articles, 0)), 4) AS gpr_threats_index,

    ROUND(((count_war_act + count_terror_act) * 100.0
        / NULLIF(total_articles, 0)), 4) AS gpr_acts_index,

    ROUND(((count_war_threat + count_peace_threat + count_military_buildup
            + count_war_act  + count_terror_act) * 100.0
        / NULLIF(total_articles, 0)), 4) AS total_gpr_index

FROM daily_aggregates