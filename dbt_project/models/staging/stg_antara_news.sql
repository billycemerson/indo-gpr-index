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
        -- Assuming scraper runs daily to fetch 'Kemarin', we assign yesterday's date
        (CURRENT_DATE - INTERVAL 1 DAY)::DATE AS published_date
    FROM source_data
),

deduplicated AS (
    SELECT 
        *,
        -- Assign row numbers to find duplicates based on the URL
        ROW_NUMBER() OVER (PARTITION BY link ORDER BY published_date DESC) AS row_num
    FROM cleaned_data
)

-- Only keep the first instance of any article
SELECT * EXCLUDE (row_num)
FROM deduplicated
WHERE row_num = 1