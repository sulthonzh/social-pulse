-- Gold: Campaign Summary
-- Source: ref('gold_post_search')
-- Target: gold.gold_campaign_summary
-- Screen: Cross-Campaign Comparison
-- Medallion Layer: Gold (Gold → Gold aggregation)
-- Description: Per-campaign summary with sentiment percentages, engagement totals, and platform breakdown

SELECT
    md5(search_request_id || keyword) AS id,
    search_request_id,
    keyword,
    MIN(CAST(posted_at AS DATE)) AS start_date,
    MAX(CAST(posted_at AS DATE)) AS end_date,
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
    flatten(list(COALESCE(hashtags, ARRAY[]))) AS top_hashtags,
    list_filter(list(COALESCE(topic_label, '')), x -> x IS NOT NULL AND x != '') AS top_topics,
    ARRAY_SORT(list(DISTINCT platform)) AS platforms,
    MAX(ai_version) AS ai_version,
    current_timestamp AS created_at
FROM {{ ref('gold_post_search') }}
GROUP BY search_request_id, keyword
ORDER BY search_request_id
