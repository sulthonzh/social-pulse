-- Silver: AI Enrichment
-- Source: ref('silver_posts') + silver.silver_ai_enrichment (AI-generated table)
-- Medallion Layer: Silver (AI enrichment of structured posts)
-- Description: AI enrichment results from Python pipeline. Joins through bronze_post_id
--   as a stable bridge key between pipeline's silver_posts and dbt's silver_posts views.

SELECT
    ae.id,
    sp.id AS silver_post_id,
    ae.ai_version,
    ae.hashtags,
    ae.mentions,
    ae.language,
    ae.topic_label,
    ae.topic_confidence,
    ae.reach_estimate,
    ae.sentiment,
    ae.sentiment_confidence,
    ae.metadata_model_name,
    ae.metadata_model_version,
    ae.sentiment_model_name,
    ae.sentiment_model_version,
    ae.created_at
FROM silver.silver_ai_enrichment ae
INNER JOIN silver.silver_posts pipeline_sp
    ON ae.silver_post_id = pipeline_sp.id
INNER JOIN {{ ref('silver_posts') }} sp
    ON sp.bronze_post_id = pipeline_sp.bronze_post_id
