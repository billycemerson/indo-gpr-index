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
 * This model intentionally duplicates the keyword logic from
 * mart_gpr_daily.sql. They must be kept in sync — if you change a
 * keyword list in one, change it in the other.
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

    CASE WHEN {{ match_keywords('title_cleaned', [
        'konflik', 'perang', 'ancaman', 'ketegangan', 'provokasi',
        'eskalasi', 'sengketa', 'krisis', 'ultimatum', 'blokade',
        'sanksi', 'embargo', 'intervensi', 'agresi', 'perbatasan'
    ]) }} THEN 1 ELSE 0 END AS is_war_threat,

    CASE WHEN {{ match_keywords('title_cleaned', [
        'gencatan', 'perdamaian', 'perundingan', 'negosiasi', 'mediasi',
        'diplomasi', 'rekonsiliasi', 'kesepakatan damai', 'perjanjian',
        'normalisasi'
    ]) }} THEN 1 ELSE 0 END AS is_peace_threat,

    CASE WHEN {{ match_keywords('title_cleaned', [
        'militer', 'tentara', 'pasukan', 'tni', 'panglima', 'pertahanan',
        'alutsista', 'persenjataan', 'senjata', 'kapal perang',
        'jet tempur', 'latihan militer', 'manuver', 'mobilisasi', 'pengerahan'
    ]) }} THEN 1 ELSE 0 END AS is_military_buildup,

    CASE WHEN {{ match_keywords('title_cleaned', [
        'serangan', 'baku tembak', 'bentrok', 'tembak', 'ledakan',
        'penembakan', 'kekerasan', 'korban', 'insiden', 'penyerangan',
        'pembantaian', 'invasi', 'pendudukan', 'pemboman'
    ]) }} THEN 1 ELSE 0 END AS is_war_act,

    CASE WHEN {{ match_keywords('title_cleaned', [
        'teror', 'teroris', 'terorisme', 'bnpt', 'densus', 'radikal',
        'radikalisme', 'ekstremis', 'bom', 'peledak',
        'penangkapan terduga', 'jaringan teroris', 'deradikalisasi'
    ]) }} THEN 1 ELSE 0 END AS is_terror_act

FROM staging
ORDER BY published_date DESC