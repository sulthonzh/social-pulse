-- Script: 01_bronze_to_silver_posts.sql
-- Source: bronze.bronze_posts → Target: silver.silver_posts
-- Description: Transform raw bronze posts into structured silver posts with extracted metrics

-- Source-to-target mapping:
-- | Target Column (silver.silver_posts) | Source | Transformation |
-- |---|---|---|
-- | id | gen_random_uuid() | Auto-generated |
-- | bronze_post_id | bronze.bronze_posts.id | Direct |
-- | search_request_id | bronze.bronze_posts.search_request_id | Direct |
-- | platform | bronze.bronze_posts.platform | Direct |
-- | platform_id | bronze.bronze_posts.platform_id | Direct |
-- | author_handle | bronze.bronze_posts.author_handle | Direct |
-- | author_name | COALESCE(raw_payload->>author_name, author, channel, uploader) | Multi-source |
-- | post_text | COALESCE(raw_payload->>text, title + selftext/description) | Multi-source |
-- | posted_at | COALESCE(raw_payload->>posted_at, created_at, created_utc, upload_date) | Multi-source + CAST |
-- | like_count | public_metrics.like_count OR raw_payload.like_count | COALESCE, default 0 |
-- | share_count | public_metrics.retweet_count OR raw_payload.share_count | COALESCE, default 0 |
-- | reply_count | public_metrics.reply_count OR raw_payload.reply_count | COALESCE, default 0 |
-- | view_count | public_metrics.impression_count OR raw_payload.view_count | COALESCE, default 0 |
-- | post_url | COALESCE(raw_payload.post_url, raw_payload.url) | Multi-source |
-- | is_retweet | raw_payload.is_retweet | CAST BOOLEAN, default FALSE |
-- | created_at | current_timestamp | Auto |

-- Insert new posts from bronze to silver, avoiding duplicates
INSERT INTO silver.silver_posts (
    id,
    bronze_post_id,
    search_request_id,
    platform,
    platform_id,
    author_handle,
    author_name,
    post_text,
    posted_at,
    like_count,
    share_count,
    reply_count,
    view_count,
    post_url,
    is_retweet,
    created_at
)
SELECT 
    gen_random_uuid() AS id,
    bp.id AS bronze_post_id,
    bp.search_request_id,
    bp.platform,
    bp.platform_id,
    bp.author_handle,
    COALESCE(bp.raw_payload->>'author_name', bp.raw_payload->>'author', bp.raw_payload->>'channel', bp.raw_payload->>'uploader') AS author_name,
    COALESCE(bp.raw_payload->>'text', CONCAT(bp.raw_payload->>'title', ' ', COALESCE(bp.raw_payload->>'selftext', bp.raw_payload->>'description', ''))) AS post_text,
    CAST(COALESCE(
        bp.raw_payload->>'posted_at',
        bp.raw_payload->>'created_at',
        CASE WHEN bp.platform = 'reddit' AND bp.raw_payload->>'created_utc' IS NOT NULL
             THEN strftime(CAST(bp.raw_payload->>'created_utc' AS DOUBLE) * 1000, '%Y-%m-%dT%H:%M:%S')
             ELSE NULL END,
        CASE WHEN bp.platform = 'youtube' AND bp.raw_payload->>'upload_date' IS NOT NULL
             THEN CONCAT(SUBSTRING(bp.raw_payload->>'upload_date', 1, 4), '-', SUBSTRING(bp.raw_payload->>'upload_date', 5, 2), '-', SUBSTRING(bp.raw_payload->>'upload_date', 7, 2), 'T00:00:00')
             ELSE NULL END
    ) AS TIMESTAMP) AS posted_at,
    COALESCE(CAST(bp.raw_payload->'public_metrics'->>'like_count' AS INTEGER), CAST(bp.raw_payload->>'like_count' AS INTEGER), 0) AS like_count,
    COALESCE(CAST(bp.raw_payload->'public_metrics'->>'retweet_count' AS INTEGER), CAST(bp.raw_payload->>'share_count' AS INTEGER), 0) AS share_count,
    COALESCE(CAST(bp.raw_payload->'public_metrics'->>'reply_count' AS INTEGER), CAST(bp.raw_payload->>'reply_count' AS INTEGER), 0) AS reply_count,
    COALESCE(CAST(bp.raw_payload->'public_metrics'->>'impression_count' AS INTEGER), CAST(bp.raw_payload->>'view_count' AS INTEGER), 0) AS view_count,
    COALESCE(bp.raw_payload->>'post_url', bp.raw_payload->>'url') AS post_url,
    COALESCE(CAST(bp.raw_payload->>'is_retweet' AS BOOLEAN), FALSE) AS is_retweet,
    current_timestamp AS created_at
FROM bronze.bronze_posts bp
LEFT JOIN silver.silver_posts sp ON bp.id = sp.bronze_post_id
WHERE sp.id IS NULL;

-- Run with: duckdb data/socialpulse.duckdb < scripts/transformations/01_bronze_to_silver_posts.sql