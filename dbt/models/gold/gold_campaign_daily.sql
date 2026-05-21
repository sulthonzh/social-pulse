-- Gold: Campaign Daily
-- Source: ref('gold_post_search')
-- Target: gold.gold_campaign_daily
-- Screen: Campaign Analytics
-- Medallion Layer: Gold (Gold → Gold aggregation)
-- Description: Daily aggregation of post metrics by search request, keyword, and platform

SELECT
    md5(search_request_id || keyword || platform || CAST(CAST(posted_at AS DATE) AS VARCHAR)) AS id,
    search_request_id,
    keyword,
    platform,
    CAST(posted_at AS DATE) AS date,
    COUNT(*) AS total_posts,
    COUNT(*) FILTER (WHERE sentiment = 'positive') AS positive_count,
    COUNT(*) FILTER (WHERE sentiment = 'negative') AS negative_count,
    COUNT(*) FILTER (WHERE sentiment = 'neutral') AS neutral_count,
    ROUND(AVG(COALESCE(sentiment_confidence, 0)), 4) AS avg_confidence,
    flatten(list(COALESCE(hashtags, ARRAY[]))) AS top_hashtags,
    list_filter(list(COALESCE(topic_label, '')), x -> x IS NOT NULL AND x != '') AS top_topics,
    SUM(like_count) AS total_likes,
    SUM(share_count) AS total_shares,
    SUM(reply_count) AS total_replies,
    SUM(view_count) AS total_views,
    MAX(ai_version) AS ai_version,
    current_timestamp AS created_at
FROM {{ ref('gold_post_search') }}
GROUP BY search_request_id, keyword, platform, CAST(posted_at AS DATE)
ORDER BY search_request_id, platform, CAST(posted_at AS DATE)
