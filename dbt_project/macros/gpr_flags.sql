-- =====================================================================
-- gpr_flags.sql
-- =====================================================================
-- Computes all 5 GPR component flags from a title_cleaned column.
-- Single source of truth for the CASE WHEN logic itself — both
-- mart_gpr_daily.sql and mart_gpr_audit.sql call this one macro,
-- so a fix to the flag logic only needs to happen here.
--
-- Usage:
--     SELECT *, {{ gpr_flags() }}
--     FROM staging
-- =====================================================================

{% macro gpr_flags() %}

    CASE WHEN
        {{ match_keywords('title_cleaned', war_threat_triggers()) }}
        AND NOT {{ match_keywords('title_cleaned', war_threat_excludes()) }}
    THEN 1 ELSE 0 END AS is_war_threat,

    CASE WHEN
        {{ match_keywords('title_cleaned', peace_threat_triggers()) }}
        AND {{ match_keywords('title_cleaned', peace_threat_requires()) }}
    THEN 1 ELSE 0 END AS is_peace_threat,

    CASE WHEN
        {{ match_keywords('title_cleaned', military_buildup_triggers()) }}
        AND {{ match_keywords('title_cleaned', military_buildup_requires()) }}
    THEN 1 ELSE 0 END AS is_military_buildup,

    CASE WHEN
        {{ match_keywords('title_cleaned', war_act_unconditional_triggers()) }}
        OR (
            title_cleaned ILIKE '%korban%'
            AND {{ match_keywords('title_cleaned', war_act_korban_requires()) }}
        )
    THEN 1 ELSE 0 END AS is_war_act,

    CASE WHEN
        {{ match_keywords('title_cleaned', terror_act_triggers()) }}
    THEN 1 ELSE 0 END AS is_terror_act

{% endmacro %}