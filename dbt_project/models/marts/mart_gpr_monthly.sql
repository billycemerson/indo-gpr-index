{{ config(
    materialized='table'
) }}

/*
 * mart_gpr_monthly.sql
 * =====================
 * Monthly rollup of mart_gpr_daily — closest match to Caldara & Iacoviello's
 * original publication granularity. Same aggregate-then-divide approach as
 * the weekly mart: sum raw counts first, compute percentage last.
 */

WITH daily AS (
    SELECT * FROM {{ ref('mart_gpr_daily') }}
),

monthly_counts AS (
    SELECT
        DATE_TRUNC('month', published_date) AS month_start,
        MIN(published_date) AS first_day_in_month,
        MAX(published_date) AS last_day_in_month,
        COUNT(DISTINCT published_date) AS days_with_data,

        SUM(total_articles) AS total_articles,

        SUM(ROUND(idx_war_threat       * total_articles / 100.0)) AS count_war_threat,
        SUM(ROUND(idx_peace_threat     * total_articles / 100.0)) AS count_peace_threat,
        SUM(ROUND(idx_military_buildup * total_articles / 100.0)) AS count_military_buildup,
        SUM(ROUND(idx_war_act          * total_articles / 100.0)) AS count_war_act,
        SUM(ROUND(idx_terror_act       * total_articles / 100.0)) AS count_terror_act

    FROM daily
    GROUP BY 1
)

SELECT
    month_start,
    first_day_in_month,
    last_day_in_month,
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

FROM monthly_counts
ORDER BY month_start