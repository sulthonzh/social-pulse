-- Silver: Structured Posts
-- Source: bronze.bronze_posts + bronze.search_requests
-- Medallion Layer: Silver (Bronze → Silver transformation)
-- Description: Transforms raw bronze posts into structured silver posts
--   by extracting fields from JSON raw_payload and joining with search_requests
--   to include the campaign keyword. Uses bp.id (bronze post UUID) as a
--   deterministic primary key — views with gen_random_uuid() produce different
--   IDs per evaluation, breaking downstream JOINs.

SELECT
    bp.id AS id,
    bp.id AS bronze_post_id,
    bp.search_request_id,
    sr.keyword,
    bp.platform,
    bp.platform_id,
    bp.author_handle,
    bp.raw_payload->>'author_name' AS author_name,
    bp.raw_payload->>'text' AS post_text,
    CAST(bp.raw_payload->>'posted_at' AS TIMESTAMP) AS posted_at,
    COALESCE(CAST(bp.raw_payload->'public_metrics'->>'like_count' AS INTEGER), 0) AS like_count,
    COALESCE(CAST(bp.raw_payload->'public_metrics'->>'retweet_count' AS INTEGER), 0) AS share_count,
    COALESCE(CAST(bp.raw_payload->'public_metrics'->>'reply_count' AS INTEGER), 0) AS reply_count,
    COALESCE(CAST(bp.raw_payload->'public_metrics'->>'impression_count' AS INTEGER), 0) AS view_count,
    bp.raw_payload->>'post_url' AS post_url,
    COALESCE(CAST(bp.raw_payload->>'is_retweet' AS BOOLEAN), FALSE) AS is_retweet,
    current_timestamp AS created_at
FROM {{ source('bronze', 'bronze_posts') }} bp
LEFT JOIN {{ source('bronze', 'search_requests') }} sr
    ON bp.search_request_id = sr.id
