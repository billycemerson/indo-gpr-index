{{ config(
    materialized='table'
) }}

/*
 * mart_gpr_audit.sql
 * ===================
 * Persists every article flagged as is_indonesia_relevant = 1, along with
 * which specific GPR component(s) it matched. This is the audit trail
 * behind every number in mart_gpr_daily / weekly / monthly — for any
 * given index spike, you can trace back to the exact articles that
 * caused it.
 *
 * Keyword/flag logic is NOT duplicated here — both this model and
 * mart_gpr_daily.sql call the same {{ gpr_flags() }} macro (defined in
 * macros/gpr_flags.sql, backed by keyword lists in
 * macros/gpr_keyword_lists.sql). Fixing a keyword in one place fixes
 * it everywhere automatically.
 */

WITH staging AS (
    SELECT * FROM {{ ref('stg_scraped_news') }}
    WHERE is_indonesia_relevant = 1
)

SELECT
    published_date,
    source,
    category,
    link,
    title,
    title_cleaned,
    {{ gpr_flags() }}
FROM staging
ORDER BY published_date DESC