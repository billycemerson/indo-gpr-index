-- =====================================================================
-- gpr_keyword_lists.sql
-- =====================================================================
-- Single source of truth for all GPR classification keywords.
-- Both mart_gpr_daily.sql and mart_gpr_audit.sql call these macros
-- instead of hardcoding keyword lists. Change a list here once,
-- both marts pick it up automatically with zero drift risk.
--
-- Each category may have up to 3 lists:
--   - triggers : keywords that turn the flag ON
--   - excludes : if present in the title, the flag is forced OFF
--                even if a trigger matched (e.g. 'solusi' cancels 'konflik')
--   - requires : trigger must co-occur with at least one of these
--                for the flag to turn ON (e.g. military noun + action verb)
-- =====================================================================


-- ── WAR THREAT ───────────────────────────────────────────────────────
-- Audit finding: 'konflik' alone fires on both real threats AND
-- proposed-solution headlines ("usulkan solusi bagi konflik dunia").
-- Excludes resolution wording to remove that false-positive class.

{% macro war_threat_triggers() %}
    {{ return([
        'konflik', 'perang', 'ancaman', 'ketegangan', 'provokasi', 'eskalasi',
        'sengketa', 'krisis', 'ultimatum', 'blokade', 'sanksi', 'embargo',
        'intervensi', 'agresi', 'perbatasan'
    ]) }}
{% endmacro %}

{% macro war_threat_excludes() %}
    {{ return([
        'solusi', 'usulkan solusi', 'tawarkan solusi'
    ]) }}
{% endmacro %}


-- ── PEACE THREAT ─────────────────────────────────────────────────────
-- Audit finding: original keywords fired on SUCCESSFUL diplomacy too
-- ("diplomasi RI berjalan efektif", "sepakat dorong perdamaian").
-- Per Caldara & Iacoviello this category means the peace process is
-- FAILING, not merely mentioned — require a negative-outcome word
-- to co-occur.

{% macro peace_threat_triggers() %}
    {{ return([
        'gencatan', 'perdamaian', 'perundingan', 'negosiasi', 'mediasi',
        'diplomasi', 'rekonsiliasi', 'kesepakatan damai', 'perjanjian',
        'normalisasi'
    ]) }}
{% endmacro %}

{% macro peace_threat_requires() %}
    {{ return([
        'gagal', 'gugur', 'macet', 'batal', 'tegang', 'tolak', 'mundur',
        'kandas', 'mentah', 'buntu'
    ]) }}
{% endmacro %}


-- ── MILITARY BUILDUP ─────────────────────────────────────────────────
-- Audit finding: most over-triggered category, ~65% false-positive
-- rate in 1-month sample. Bare 'militer'/'tentara'/'tni'/'pasukan'
-- fired on any sentence merely mentioning a military entity as a
-- diplomatic/reporting subject (e.g. "9 WNI Ditangkap Tentara Israel").
-- Now requires a buildup-specific action term to co-occur.

{% macro military_buildup_triggers() %}
    {{ return([
        'militer', 'tentara', 'pasukan', 'tni', 'panglima', 'pertahanan',
        'alutsista', 'persenjataan', 'senjata', 'kapal perang', 'jet tempur'
    ]) }}
{% endmacro %}

{% macro military_buildup_requires() %}
    {{ return([
        'latihan', 'manuver', 'mobilisasi', 'pengerahan', 'siaga', 'perkuat',
        'tingkatkan kesiapan', 'beli', 'akuisisi', 'kerahkan', 'kirim pasukan',
        'gelar latihan'
    ]) }}
{% endmacro %}


-- ── WAR ACT ──────────────────────────────────────────────────────────
-- Audit finding: bare 'korban' also fires on natural disasters
-- (earthquake victims) and drug-trafficking victims — neither is a
-- geopolitical act. 'korban' now requires a conflict-specific term to
-- co-occur. Added disekap/disandera/dianiaya/diculik/cegat/intersepsi
-- to catch genuine WNI-endangerment-abroad cases the original list
-- missed (Malaysia tin-mining trafficking, Israel flotilla interception).

{% macro war_act_unconditional_triggers() %}
    {{ return([
        'serangan', 'baku tembak', 'bentrok', 'tembak', 'ledakan', 'penembakan',
        'kekerasan', 'insiden', 'penyerangan', 'pembantaian', 'invasi',
        'pendudukan', 'pemboman', 'disekap', 'disandera', 'dianiaya', 'aniaya',
        'diculik', 'cegat', 'intersepsi'
    ]) }}
{% endmacro %}

{% macro war_act_korban_requires() %}
    {{ return([
        'serangan', 'bentrok', 'tembak', 'ledakan', 'kekerasan', 'penyerangan',
        'pemboman', 'konflik'
    ]) }}
{% endmacro %}


-- ── TERROR ACT ───────────────────────────────────────────────────────
-- No false positives found in 1-month audit; category never triggered
-- in the sample. Kept unchanged pending more data — absence may reflect
-- a genuinely quiet month rather than a coverage gap.

{% macro terror_act_triggers() %}
    {{ return([
        'teror', 'teroris', 'terorisme', 'bnpt', 'densus', 'radikal',
        'radikalisme', 'ekstremis', 'bom', 'peledak', 'penangkapan terduga',
        'jaringan teroris', 'deradikalisasi'
    ]) }}
{% endmacro %}