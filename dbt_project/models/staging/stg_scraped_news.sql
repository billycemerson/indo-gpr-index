WITH source_data AS (
    SELECT * FROM {{ source('gpr_raw', 'raw_news') }}
),

cleaned_data AS (
    SELECT
        title,
        -- Lowercase for easier keyword matching later
        LOWER(title) AS title_cleaned,
        link,
        category,
        date_text,
        source,
        -- Force the string from Python into a pure DATE type for DuckDB
        CAST(published_date AS DATE) AS published_date
    FROM source_data
),

deduplicated AS (
    SELECT 
        *,
        -- Assign row numbers to find duplicates based on the URL
        ROW_NUMBER() OVER (PARTITION BY link ORDER BY published_date DESC) AS row_num
    FROM cleaned_data
),

deduped_final AS (
    -- Only keep the first instance of any article
    SELECT * EXCLUDE (row_num)
    FROM deduplicated
    WHERE row_num = 1
)

SELECT
    *,
    CASE WHEN
        -- Must mention a foreign state, cross-border body, or international actor
        (
            {{ match_keywords('title_cleaned', [
                'amerika', 'china', 'tiongkok', 'rusia', 'israel', 'palestina',
                'iran', 'korea utara', 'korea selatan', 'malaysia', 'filipina',
                'asean', 'pbb', 'nato', 'pentagon', 'gaza', 'ukraina',
                'laut china selatan', 'taiwan', 'hamas',
                'turkiye', 'turki', 'zionis', 'kuwait', 'somalia',
                'kirgistan', 'selat hormuz'
            ]) }}
            -- Word-boundary match for 'AS' as a standalone abbreviation for
            -- the United States. ILIKE '%as%' alone would match inside
            -- 'asean', 'asing', 'biasa', etc.
            OR REGEXP_MATCHES(title_cleaned, '\bas\b')
        )
        AND
        -- AND must show Indonesia is a party/stake, not just a bystander reporter
        (
            title_cleaned ILIKE '%indonesia%'
            OR title_cleaned ILIKE '%wni%'
            OR title_cleaned ILIKE '%tni%'
            OR title_cleaned ILIKE '%natuna%'
            OR title_cleaned ILIKE '%kbri%'
            OR title_cleaned ILIKE '%kedutaan%'
            OR title_cleaned ILIKE '%menteri luar negeri%'
            OR title_cleaned ILIKE '%dubes%'
        )
    THEN 1 ELSE 0 END AS is_indonesia_relevant

FROM deduped_final