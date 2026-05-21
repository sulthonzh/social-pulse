-- Script: 04_silver_to_gold_campaign_summary.sql
-- Source: gold.gold_post_search → Target: gold.gold_campaign_summary
-- Description: Transform gold post search data into campaign summary records

-- Source-to-target mapping:
-- | Target Column (gold.gold_campaign_summary) | Source | Transformation |
-- |---|---|---|
-- | id | gen_random_uuid() | Auto |
-- | search_request_id | gps.search_request_id | GROUP BY |
-- | keyword | MIN(gps.keyword) | GROUP BY (all same) |
-- | start_date | MIN(CAST(gps.posted_at AS DATE)) | Min date |
-- | end_date | MAX(CAST(gps.posted_at AS DATE)) | Max date |
-- | total_posts | COUNT(*) | Aggregate |
-- | positive_pct | ROUND(COUNT(*) FILTER (WHERE sentiment = 'positive') * 100.0 / COUNT(*), 2) | Percentage |
-- | negative_pct | ROUND(COUNT(*) FILTER (WHERE sentiment = 'negative') * 100.0 / COUNT(*), 2) | Percentage |
-- | neutral_pct | ROUND(COUNT(*) FILTER (WHERE sentiment = 'neutral') * 100.0 / COUNT(*), 2) | Percentage |
-- | avg_confidence | ROUND(AVG(sentiment_confidence), 4) | Average |
-- | total_engagement | SUM(like_count + share_count + reply_count) | Aggregate |
-- | total_likes | SUM(like_count) | Aggregate |
-- | total_shares | SUM(share_count) | Aggregate |
-- | total_replies | SUM(reply_count) | Aggregate |
-- | total_views | SUM(view_count) | Aggregate |
-- | top_hashtags | list_flatten(list(hashtags)) | Collected array |
-- | top_topics | list_filter(list(topic_label), x -> x IS NOT NULL) | Collected array |
-- | platforms | ARRAY_SORT(list(DISTINCT platform)) | Unique sorted platforms |
-- | ai_version | MAX(ai_version) | Max |
-- | created_at | current_timestamp | Auto |

-- Insert campaign summaries, handling duplicates by deleting existing data first
-- DuckDB doesn't support ON CONFLICT, so use DELETE + INSERT pattern

-- First, delete existing records for the search requests we're about to insert
DELETE FROM gold.gold_campaign_summary
WHERE search_request_id IN (
    SELECT DISTINCT search_request_id
    FROM gold.gold_post_search
);

-- Insert new campaign summaries
INSERT INTO gold.gold_campaign_summary (
    id,
    search_request_id,
    keyword,
    start_date,
    end_date,
    total_posts,
    positive_pct,
    negative_pct,
    neutral_pct,
    avg_confidence,
    total_engagement,
    total_likes,
    total_shares,
    total_replies,
    total_views,
    top_hashtags,
    top_topics,
    platforms,
    ai_version,
    created_at
)
SELECT 
    gen_random_uuid() AS id,
    gps.search_request_id,
    gps.keyword,
    MIN(CAST(gps.posted_at AS DATE)) AS start_date,
    MAX(CAST(gps.posted_at AS DATE)) AS end_date,
    COUNT(*) AS total_posts,
    ROUND(COUNT(*) FILTER (WHERE sentiment = 'positive') * 100.0 / COUNT(*), 2) AS positive_pct,
    ROUND(COUNT(*) FILTER (WHERE sentiment = 'negative') * 100.0 / COUNT(*), 2) AS negative_pct,
    ROUND(COUNT(*) FILTER (WHERE sentiment = 'neutral') * 100.0 / COUNT(*), 2) AS neutral_pct,
    ROUND(AVG(COALESCE(sentiment_confidence, 0)), 4) AS avg_confidence,
    SUM(like_count + share_count + reply_count) AS total_engagement,
    SUM(like_count) AS total_likes,
    SUM(share_count) AS total_shares,
    SUM(reply_count) AS total_replies,
    SUM(view_count) AS total_views,
    list_flatten(list(COALESCE(hashtags, ARRAY[]))) AS top_hashtags,
    list_filter(list(COALESCE(topic_label, '')), x -> x IS NOT NULL AND x != '') AS top_topics,
    ARRAY_SORT(list(DISTINCT gps.platform)) AS platforms,
    MAX(ai_version) AS ai_version,
    current_timestamp AS created_at
FROM gold.gold_post_search gps
GROUP BY gps.search_request_id, gps.keyword
ORDER BY gps.search_request_id;

-- Run with: duckdb data/socialpulse.duckdb < scripts/transformations/04_silver_to_gold_campaign_summary.sql