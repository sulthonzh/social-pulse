-- Script: 02_silver_to_gold_post_search.sql
-- Source: silver.silver_posts + silver.silver_ai_enrichment + bronze.search_requests → Target: gold.gold_post_search
-- Description: Transform silver posts with AI enrichment into gold post search records

-- Source-to-target mapping:
-- | Target Column (gold.gold_post_search) | Source | Transformation |
-- |---|---|---|
-- | id | gen_random_uuid() | Auto |
-- | search_request_id | sp.search_request_id | Direct |
-- | keyword | sr.keyword | JOIN bronze.search_requests |
-- | platform | sp.platform | Direct |
-- | author_handle | sp.author_handle | Direct |
-- | author_name | sp.author_name | Direct |
-- | post_text | sp.post_text | Direct |
-- | posted_at | sp.posted_at | Direct |
-- | post_url | sp.post_url | Direct |
-- | sentiment | ae.sentiment | Direct, NULL if no enrichment |
-- | sentiment_confidence | ae.sentiment_confidence | Direct, NULL if no enrichment |
-- | topic_label | ae.topic_label | Direct, NULL if no enrichment |
-- | language | ae.language | Direct, NULL if no enrichment |
-- | hashtags | ae.hashtags | Direct, empty array if no enrichment |
-- | mentions | ae.mentions | Direct, empty array if no enrichment |
-- | like_count | sp.like_count | Direct |
-- | share_count | sp.share_count | Direct |
-- | reply_count | sp.reply_count | Direct |
-- | view_count | sp.view_count | Direct |
-- | ai_version | ae.ai_version | Direct, default 1 if no enrichment |
-- | created_at | current_timestamp | Auto |

-- Insert new post search records from silver posts with AI enrichment, avoiding duplicates
INSERT INTO gold.gold_post_search (
    id,
    search_request_id,
    keyword,
    platform,
    author_handle,
    author_name,
    post_text,
    posted_at,
    post_url,
    sentiment,
    sentiment_confidence,
    topic_label,
    language,
    hashtags,
    mentions,
    like_count,
    share_count,
    reply_count,
    view_count,
    ai_version,
    created_at
)
SELECT 
    gen_random_uuid() AS id,
    sp.search_request_id,
    sr.keyword,
    sp.platform,
    sp.author_handle,
    sp.author_name,
    sp.post_text,
    sp.posted_at,
    sp.post_url,
    ae.sentiment,
    ae.sentiment_confidence,
    ae.topic_label,
    ae.language,
    COALESCE(ae.hashtags, ARRAY[]) AS hashtags,
    COALESCE(ae.mentions, ARRAY[]) AS mentions,
    sp.like_count,
    sp.share_count,
    sp.reply_count,
    sp.view_count,
    COALESCE(ae.ai_version, 1) AS ai_version,
    current_timestamp AS created_at
FROM silver.silver_posts sp
LEFT JOIN silver.silver_ai_enrichment ae ON sp.id = ae.silver_post_id
LEFT JOIN bronze.search_requests sr ON sp.search_request_id = sr.id
WHERE NOT EXISTS (
    SELECT 1 FROM gold.gold_post_search gps 
    WHERE gps.search_request_id = sp.search_request_id 
    AND gps.platform = sp.platform 
    AND gps.posted_at = sp.posted_at
    AND gps.author_handle = sp.author_handle
    AND gps.post_text = sp.post_text
);

-- Run with: duckdb data/socialpulse.duckdb < scripts/transformations/02_silver_to_gold_post_search.sql