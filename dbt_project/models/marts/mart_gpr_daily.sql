{{ config(
    materialized='incremental',
    unique_key='published_date'
) }}

WITH staging AS (
    SELECT * FROM {{ ref('stg_antara_news') }}

    {% if is_incremental() %}
        WHERE published_date >= (SELECT COALESCE(MAX(published_date), '1970-01-01') FROM {{ this }})
    {% endif %}
),

flagged_articles AS (
    SELECT
        published_date,

        /*
         * WAR THREAT — geopolitical tension, hostile rhetoric, conflict risk.
         * Keywords: short tokens so ILIKE substring match catches compound phrases.
         * e.g. 'konflik' hits konflik bersenjata, konflik perbatasan, konflik laut china, etc.
         */
        CASE WHEN {{ match_keywords('title_cleaned', [
            'konflik',
            'perang',
            'ancaman',
            'ketegangan',
            'provokasi',
            'eskalasi',
            'sengketa',
            'krisis',
            'ultimatum',
            'blokade',
            'sanksi',
            'embargo',
            'intervensi',
            'agresi',
            'perbatasan'
        ]) }} THEN 1 ELSE 0 END AS is_war_threat,

        /*
         * PEACE THREAT — failed diplomacy, ceasefire breakdown, stalled negotiations.
         */
        CASE WHEN {{ match_keywords('title_cleaned', [
            'gencatan',
            'perdamaian',
            'perundingan',
            'negosiasi',
            'mediasi',
            'diplomasi',
            'rekonsiliasi',
            'kesepakatan damai',
            'perjanjian',
            'normalisasi'
        ]) }} THEN 1 ELSE 0 END AS is_peace_threat,

        /*
         * MILITARY BUILDUP — arms, troop movements, defence procurement, exercises.
         * Includes TNI / Polri since they are the Indonesian national forces.
         */
        CASE WHEN {{ match_keywords('title_cleaned', [
            'militer',
            'tentara',
            'pasukan',
            'tni',
            'panglima',
            'pertahanan',
            'alutsista',
            'persenjataan',
            'senjata',
            'kapal perang',
            'jet tempur',
            'latihan militer',
            'manuver',
            'mobilisasi',
            'pengerahan'
        ]) }} THEN 1 ELSE 0 END AS is_military_buildup,

        /*
         * WAR ACT — active armed clashes, strikes, casualties, incidents.
         */
        CASE WHEN {{ match_keywords('title_cleaned', [
            'serangan',
            'baku tembak',
            'bentrok',
            'tembak',
            'ledakan',
            'penembakan',
            'kekerasan',
            'korban',
            'insiden',
            'penyerangan',
            'pembantaian',
            'invasi',
            'pendudukan',
            'pemboman'
        ]) }} THEN 1 ELSE 0 END AS is_war_act,

        /*
         * TERROR ACT — terrorism, extremism, counter-terror operations.
         * Includes Indonesian agencies: BNPT (counter-terror bureau), Densus 88.
         */
        CASE WHEN {{ match_keywords('title_cleaned', [
            'teror',
            'teroris',
            'terorisme',
            'bnpt',
            'densus',
            'radikal',
            'radikalisme',
            'ekstremis',
            'bom',
            'peledak',
            'penangkapan terduga',
            'jaringan teroris',
            'deradikalisasi'
        ]) }} THEN 1 ELSE 0 END AS is_terror_act

    FROM staging
),

daily_aggregates AS (
    SELECT
        published_date,
        COUNT(*) AS total_articles,
        SUM(is_war_threat)       AS count_war_threat,
        SUM(is_peace_threat)     AS count_peace_threat,
        SUM(is_military_buildup) AS count_military_buildup,
        SUM(is_war_act)          AS count_war_act,
        SUM(is_terror_act)       AS count_terror_act
    FROM flagged_articles
    GROUP BY 1
)

SELECT
    published_date,
    total_articles,

    /* --- Sub-category indices (% of total articles) --- */
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