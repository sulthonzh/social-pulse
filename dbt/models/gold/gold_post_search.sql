-- Gold: Post Search
-- Source: ref('silver_posts') + ref('silver_ai_enrichment')
-- Target: gold.gold_post_search
-- Screen: Post Explorer
-- Medallion Layer: Gold (Silver → Gold transformation)
-- Description: Flat, filterable post records with AI enrichment.
--   STRICT: reads ONLY from Silver layer models (no bronze sources).

SELECT
    sp.id AS id,
    sp.search_request_id,
    sp.keyword,
    sp.platform,
    sp.author_handle,
    sp.author_name,
    sp.post_text,
    sp.posted_at,
    sp.post_url,
    ae.sentiment,
    ae.sentiment_confidence,
    ae.topic_label,
    ae.topic_confidence,
    ae.language,
    COALESCE(ae.hashtags, ARRAY[]) AS hashtags,
    COALESCE(ae.mentions, ARRAY[]) AS mentions,
    sp.like_count,
    sp.share_count,
    sp.reply_count,
    sp.view_count,
    COALESCE(ae.ai_version, 1) AS ai_version,
    current_timestamp AS created_at
FROM {{ ref('silver_posts') }} sp
LEFT JOIN {{ ref('silver_ai_enrichment') }} ae
    ON sp.id = ae.silver_post_id
