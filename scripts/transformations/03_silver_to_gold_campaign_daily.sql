-- Script: 03_silver_to_gold_campaign_daily.sql
-- Source: gold.gold_post_search → Target: gold.gold_campaign_daily
-- Description: Aggregate gold post search data into daily campaign metrics

-- Source-to-target mapping:
-- | Target Column (gold.gold_campaign_daily) | Source | Transformation |
-- |---|---|---|
-- | id | gen_random_uuid() | Auto |
-- | search_request_id | gps.search_request_id | GROUP BY |
-- | keyword | gps.keyword | GROUP BY |
-- | platform | gps.platform | GROUP BY |
-- | date | CAST(gps.posted_at AS DATE) | GROUP BY |
-- | total_posts | COUNT(*) | Aggregate |
-- | positive_count | COUNT(*) FILTER (WHERE sentiment = 'positive') | Conditional count |
-- | negative_count | COUNT(*) FILTER (WHERE sentiment = 'negative') | Conditional count |
-- | neutral_count | COUNT(*) FILTER (WHERE sentiment = 'neutral') | Conditional count |
-- | avg_confidence | ROUND(AVG(sentiment_confidence), 4) | Average |
-- | top_hashtags | list_flatten(list(hashtags)) | List aggregate |
-- | top_topics | list_filter(list(topic_label), x -> x IS NOT NULL) | List aggregate |
-- | total_likes | SUM(like_count) | Aggregate |
-- | total_shares | SUM(share_count) | Aggregate |
-- | total_replies | SUM(reply_count) | Aggregate |
-- | total_views | SUM(view_count) | Aggregate |
-- | ai_version | MAX(ai_version) | Max |
-- | created_at | current_timestamp | Auto |

-- Insert daily campaign aggregates, handling duplicates by deleting existing data first
-- DuckDB doesn't support ON CONFLICT, so use DELETE + INSERT pattern

-- First, delete existing records for the date ranges we're about to insert
DELETE FROM gold.gold_campaign_daily
WHERE (search_request_id, platform, date) IN (
    SELECT search_request_id, platform, CAST(posted_at AS DATE) AS date
    FROM gold.gold_post_search
    WHERE posted_at >= (SELECT MIN(CAST(posted_at AS DATE)) FROM gold.gold_post_search)
    AND posted_at <= (SELECT MAX(CAST(posted_at AS DATE)) FROM gold.gold_post_search)
);

-- Insert new daily aggregates
INSERT INTO gold.gold_campaign_daily (
    id,
    search_request_id,
    keyword,
    platform,
    date,
    total_posts,
    positive_count,
    negative_count,
    neutral_count,
    avg_confidence,
    top_hashtags,
    top_topics,
    total_likes,
    total_shares,
    total_replies,
    total_views,
    ai_version,
    created_at
)
SELECT 
    gen_random_uuid() AS id,
    gps.search_request_id,
    gps.keyword,
    gps.platform,
    CAST(gps.posted_at AS DATE) AS date,
    COUNT(*) AS total_posts,
    COUNT(*) FILTER (WHERE sentiment = 'positive') AS positive_count,
    COUNT(*) FILTER (WHERE sentiment = 'negative') AS negative_count,
    COUNT(*) FILTER (WHERE sentiment = 'neutral') AS neutral_count,
    ROUND(AVG(COALESCE(sentiment_confidence, 0)), 4) AS avg_confidence,
    list_flatten(list(COALESCE(hashtags, ARRAY[]))) AS top_hashtags,
    list_filter(list(COALESCE(topic_label, '')), x -> x IS NOT NULL AND x != '') AS top_topics,
    SUM(like_count) AS total_likes,
    SUM(share_count) AS total_shares,
    SUM(reply_count) AS total_replies,
    SUM(view_count) AS total_views,
    MAX(ai_version) AS ai_version,
    current_timestamp AS created_at
FROM gold.gold_post_search gps
GROUP BY gps.search_request_id, gps.keyword, gps.platform, CAST(gps.posted_at AS DATE)
ORDER BY gps.search_request_id, gps.platform, CAST(gps.posted_at AS DATE);



-- Run with: duckdb data/socialpulse.duckdb < scripts/transformations/03_silver_to_gold_campaign_daily.sql