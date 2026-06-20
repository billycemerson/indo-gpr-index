{{ config(
    materialized='table'
) }}

/*
 * mart_gpr_weekly.sql
 * ====================
 * Weekly rollup of mart_gpr_daily. Reduces noise from single-digit daily
 * denominators (e.g. 1 article/day swinging the index 0% <-> 100%) by
 * aggregating counts BEFORE computing percentages — not averaging the
 * daily percentages themselves, which would double-distort already
 * noisy small-sample daily rates.
 *
 * Week start = Monday (DuckDB default for DATE_TRUNC('week', ...)).
 */

WITH daily AS (
    SELECT * FROM {{ ref('mart_gpr_daily') }}
),

weekly_counts AS (
    SELECT
        DATE_TRUNC('week', published_date) AS week_start,
        MIN(published_date) AS first_day_in_week,
        MAX(published_date) AS last_day_in_week,
        COUNT(DISTINCT published_date) AS days_with_data,

        SUM(total_articles) AS total_articles,

        -- Re-derive raw counts from daily percentages × daily total_articles,
        -- rounding to nearest integer since the daily mart only stores %s.
        -- This recovers the original article counts without re-querying staging.
        SUM(ROUND(idx_war_threat       * total_articles / 100.0)) AS count_war_threat,
        SUM(ROUND(idx_peace_threat     * total_articles / 100.0)) AS count_peace_threat,
        SUM(ROUND(idx_military_buildup * total_articles / 100.0)) AS count_military_buildup,
        SUM(ROUND(idx_war_act          * total_articles / 100.0)) AS count_war_act,
        SUM(ROUND(idx_terror_act       * total_articles / 100.0)) AS count_terror_act

    FROM daily
    GROUP BY 1
)

SELECT
    week_start,
    first_day_in_week,
    last_day_in_week,
    days_with_data,
    total_articles,

    ROUND(count_war_threat       * 100.0 / NULLIF(total_articles, 0), 4) AS idx_war_threat,
    ROUND(count_peace_threat     * 100.0 / NULLIF(total_articles, 0), 4) AS idx_peace_threat,
    ROUND(count_military_buildup * 100.0 / NULLIF(total_articles, 0), 4) AS idx_military_buildup,
    ROUND(count_war_act          * 100.0 / NULLIF(total_articles, 0), 4) AS idx_war_act,
    ROUND(count_terror_act       * 100.0 / NULLIF(total_articles, 0), 4) AS idx_terror_act,

    ROUND((count_war_threat + count_peace_threat + count_military_buildup) * 100.0
        / NULLIF(total_articles, 0), 4) AS gpr_threats_index,

    ROUND((count_war_act + count_terror_act) * 100.0
        / NULLIF(total_articles, 0), 4) AS gpr_acts_index,

    ROUND((count_war_threat + count_peace_threat + count_military_buildup
           + count_war_act + count_terror_act) * 100.0
        / NULLIF(total_articles, 0), 4) AS total_gpr_index

FROM weekly_counts
ORDER BY week_start