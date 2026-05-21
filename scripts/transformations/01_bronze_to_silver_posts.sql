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
-- | author_name | bronze.bronze_posts.raw_payload->>'author_name' | JSON extract |
-- | post_text | bronze.bronze_posts.raw_payload->>'text' | JSON extract |
-- | posted_at | bronze.bronze_posts.raw_payload->>'posted_at' | JSON extract + CAST to TIMESTAMP |
-- | like_count | bronze.bronze_posts.raw_payload->'public_metrics'->>'like_count' | JSON extract + CAST INTEGER, default 0 |
-- | share_count | bronze.bronze_posts.raw_payload->'public_metrics'->>'retweet_count' | JSON extract + CAST INTEGER, default 0 |
-- | reply_count | bronze.bronze_posts.raw_payload->'public_metrics'->>'reply_count' | JSON extract + CAST INTEGER, default 0 |
-- | view_count | bronze.bronze_posts.raw_payload->'public_metrics'->>'impression_count' | JSON extract + CAST INTEGER, default 0 |
-- | post_url | bronze.bronze_posts.raw_payload->>'post_url' | JSON extract |
-- | is_retweet | bronze.bronze_posts.raw_payload->>'is_retweet' | JSON extract + CAST BOOLEAN, default FALSE |
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
FROM bronze.bronze_posts bp
LEFT JOIN silver.silver_posts sp ON bp.id = sp.bronze_post_id
WHERE sp.id IS NULL;

-- Run with: duckdb data/socialpulse.duckdb < scripts/transformations/01_bronze_to_silver_posts.sql