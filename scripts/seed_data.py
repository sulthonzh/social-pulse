"""Seed realistic synthetic social media data into Bronze layer.

Creates search requests, completed crawl runs, and raw posts
so the full pipeline (AI enrichment → Gold build → Streamlit UI)
can be tested end-to-end without live API credentials.

Usage:
    uv run python scripts/seed_data.py
"""

from __future__ import annotations

import json
import random
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

CAMPAIGNS = [
    {"keyword": "data engineering", "platform": "twitter"},
    {"keyword": "machine learning", "platform": "twitter"},
    {"keyword": "python programming", "platform": "twitter"},
    {"keyword": "cloud computing", "platform": "twitter"},
    {"keyword": "cybersecurity", "platform": "twitter"},
]

AUTHORS = [
    {"handle": "@dataengineer_pro", "name": "Data Engineer Pro"},
    {"handle": "@ml_researcher", "name": "ML Research Hub"},
    {"handle": "@pythondaily", "name": "Python Daily"},
    {"handle": "@cloudnative_dev", "name": "Cloud Native Dev"},
    {"handle": "@secops_analyst", "name": "SecOps Analyst"},
    {"handle": "@techlead_sarah", "name": "Sarah Chen"},
    {"handle": "@devops_mike", "name": "Mike Rodriguez"},
    {"handle": "@ai_startup_ceo", "name": "AI Startup CEO"},
    {"handle": "@opensource_fan", "name": "Open Source Fan"},
    {"handle": "@database_nerd", "name": "Database Nerd"},
    {"handle": "@infra_engineer", "name": "Infra Engineer"},
    {"handle": "@ml_ops_pete", "name": "MLOps Pete"},
    {"handle": "@sre_clara", "name": "Clara SRE"},
    {"handle": "@analytics_joe", "name": "Analytics Joe"},
    {"handle": "@platform_eng", "name": "Platform Eng"},
]

POST_TEMPLATES: dict[str, list[str]] = {
    "data engineering": [
        "Just migrated our entire ETL pipeline from Airflow to Dagster. The asset-centric approach is a game changer for data lineage tracking. #dataengineering #dagster",
        "Hot take: dbt is not a data transformation tool, it's a data quality framework. If you're only using it for SELECT statements, you're missing the point. #dbt #analytics",
        "Our team reduced pipeline failures by 80% after implementing proper data contracts. Schema evolution doesn't have to be painful. #dataengineering",
        "Spent the weekend benchmarking DuckDB vs ClickHouse for our analytics workload. Results were surprising — DuckDB handled 100M rows in under 3 seconds on a single node. #olap #duckdb",
        "Building a real-time data lakehouse with Apache Iceberg and Spark. The time-travel queries are incredibly useful for debugging data issues. #datalakehouse #iceberg",
        "Data quality is not a feature, it's a foundation. Every pipeline should have automated anomaly detection from day one. #dataquality #engineering",
        "Just published our open-source data catalog tool. 6 months of work, 2K stars in the first week. Check it out! #opensource #datacatalog",
        "The medallion architecture pattern (bronze → silver → gold) has completely changed how we think about data pipelines. Separation of concerns at its best. #dataengineering #medallion",
        "Migrated 50TB of data from PostgreSQL to BigQuery using a custom CDC pipeline. Zero downtime, full consistency. Here's the architecture thread 🧵 #cdc #bigquery",
        "Pro tip: Always version your data schemas. Semantic versioning for APIs is standard — why not for data? #dataengineering #governance",
    ],
    "machine learning": [
        "Our BERT fine-tuning on domain-specific data just hit 94% accuracy on the test set. Transfer learning is incredible. #nlp #machinelearning",
        "Released our new open-source model for sentiment analysis on social media. 12 languages, 92% accuracy. Try it out! #nlp #sentimentanalysis",
        "Feature stores are the most underrated ML infrastructure. Real-time + batch features in one place. #mlops #featurestore",
        "Just finished training a GNN for fraud detection. Graph-based approaches catch 3x more suspicious transactions than traditional ML. #graphml #fraud",
        "The key to production ML is not the model — it's the data pipeline. Garbage in, garbage out still holds. #machinelearning #datapipeline",
        "Experimenting with LoRA for fine-tuning LLMs on consumer hardware. You can get great results with just 8GB VRAM. #llm #lora",
        "Our ML model monitoring caught a data drift issue 2 hours before it would have impacted production predictions. Monitoring saves lives (and revenue). #mlops",
        "Built a real-time recommendation engine using vector similarity search. 50ms latency at 10K QPS. FAISS is incredible. #recommendations #faiss",
        "Reminder: Your ML model's performance in production depends more on data quality than model architecture. Invest in your data team. #machinelearning",
        "Deployed our first ML model on edge devices. TensorRT optimization brought inference time from 200ms to 15ms. #edgeai #tensorrt",
    ],
    "python programming": [
        "Python 3.13 is blazing fast. Our numerical code runs 30% faster without any changes. The free-threading GIL removal is a huge milestone. #python",
        "Just refactored 10K lines of Python using pydantic v2 strict mode. Caught 47 type errors that were hiding in production. Type safety matters. #python #pydantic",
        "uv is now my default Python package manager. 10x faster than pip, lockfiles by default, and drop-in compatible. #python #uv",
        "Built a custom ASGI middleware that reduced our API response times by 40%. Sometimes the best optimization is removing unnecessary processing. #python #async",
        "Structlog + rich = the best Python logging setup. Structured logs for machines, beautiful output for humans. #python #logging",
        "Pattern matching in Python 3.10+ is so underrated. Just replaced a 50-line if/elif chain with a clean match statement. #python",
        "Our team's Python coding standards: strict mypy, ruff for linting, pytest with 90% coverage minimum. Code quality is not negotiable. #python #bestpractices",
        "Just discovered Python's walrus operator is perfect for list comprehensions with expensive function calls. Clean and efficient. #python #tips",
        "FastAPI + SQLAlchemy 2.0 + Alembic is the modern Python web stack. Async everything, type-safe queries, auto migrations. #python #fastapi",
        "Python's dataclasses + Pydantic = the perfect combo for domain models. Immutable, validated, serializable. #python #architecture",
    ],
    "cloud computing": [
        "Migrated our monolith to microservices on Kubernetes. 6 months of work, but the scalability improvement is incredible. #kubernetes #microservices",
        "AWS Lambda cold starts are a thing of the past with SnapStart. Our Java functions now start in under 200ms. #aws #serverless",
        "Terraform vs Pulumi? We chose Pulumi for our IaC because type-safe infrastructure is just better. No more YAML nightmares. #infrastructure #pulumi",
        "Our multi-cloud strategy: GCP for AI/ML, AWS for compute, Azure for enterprise integrations. Each cloud has its strengths. #multicloud",
        "Just set up a service mesh with Istio. Canary deployments, mutual TLS, and observability — all at the platform level. #istio #servicemesh",
        "Cloud cost optimization is not about using fewer resources — it's about using the right resources at the right time. Spot instances saved us 70%. #finops",
        "Building a multi-region active-active architecture on GCP. Global load balancing + Cloud Spanner = sub-100ms reads worldwide. #gcp #architecture",
        "Our Docker image sizes went from 2GB to 150MB after switching to distroless base images. Smaller images = faster deployments = lower costs. #docker",
        "AWS announced Graviton4 instances. ARM-based compute is now price-performance competitive with x86 for almost all workloads. #aws #arm",
        "Infrastructure as Code is non-negotiable. If you're clicking through a console to create resources, you're doing it wrong. #devops #iac",
    ],
    "cybersecurity": [
        "Just uncovered a supply chain attack affecting 3 npm packages with 2M+ weekly downloads. Always audit your dependencies. #supplychain #security",
        "Zero Trust Architecture is not a product you buy — it's a strategy you implement. Identity-based access, microsegmentation, continuous verification. #zerotrust",
        "Our SOC team reduced MTTR from 4 hours to 20 minutes using automated incident response playbooks. Automation saves the day. #soc #automation",
        "Implemented passwordless auth for our entire org. FIDO2 keys + biometrics = no more phishing. #passwordless #fido2",
        "Ransomware attacks increased 150% this quarter. Offline backups + immutable storage + tested recovery plans are essential. #ransomware #backup",
        "Container security checklist: minimal base images, non-root user, read-only filesystem, no secrets in env vars, signed images. #containers #security",
        "Our bug bounty program just crossed 1000 valid reports. Community-driven security testing is incredibly effective. #bugbounty",
        "API security is the most neglected attack surface. Rate limiting, input validation, and proper auth are table stakes. #apisecurity",
        "Threat modeling should happen before any code is written. Security by design is 10x cheaper than security by patching. #threatmodeling",
        "Just passed our SOC 2 Type II audit. The key was building compliance into our CI/CD pipeline from the start. #compliance #soc2",
    ],
}


def _random_date_in_range(start: date, end: date) -> datetime:
    delta = (end - start).days
    random_day = start + timedelta(days=random.randint(0, max(delta, 1)))  # noqa: S311
    random_hour = random.randint(6, 23)  # noqa: S311
    random_minute = random.randint(0, 59)  # noqa: S311
    return datetime(random_day.year, random_day.month, random_day.day, random_hour, random_minute, tzinfo=UTC)


def seed(conn: Any) -> dict[str, int]:
    start_date = date(2025, 1, 1)
    end_date = date(2025, 5, 15)
    total_posts = 0
    total_requests = 0

    for campaign in CAMPAIGNS:
        request_id = str(uuid.uuid4())
        keyword = campaign["keyword"]
        platform = campaign["platform"]

        conn.execute(
            """INSERT INTO bronze.search_requests
               (id, keyword, start_date, end_date, platform, status, posts_found, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 'completed', ?, ?, ?)""",
            [request_id, keyword, start_date, end_date, platform, 0,
             datetime.now(UTC), datetime.now(UTC)],
        )

        crawl_run_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO bronze.bronze_crawl_runs
               (id, search_request_id, platform, status, posts_fetched, error_message, started_at, completed_at)
               VALUES (?, ?, ?, 'completed', ?, NULL, ?, ?)""",
            [crawl_run_id, request_id, platform, 0,
             datetime.now(UTC) - timedelta(minutes=5), datetime.now(UTC)],
        )

        templates = POST_TEMPLATES[keyword]
        num_posts = random.randint(8, len(templates))  # noqa: S311

        for i in range(num_posts):
            post_id = str(uuid.uuid4())
            author = random.choice(AUTHORS)  # noqa: S311
            text = templates[i % len(templates)]
            posted_at = _random_date_in_range(start_date, end_date)

            like_count = random.randint(5, 500)  # noqa: S311
            share_count = random.randint(0, 100)  # noqa: S311
            reply_count = random.randint(0, 50)  # noqa: S311
            view_count = random.randint(100, 50000)  # noqa: S311

            payload = {
                "id": post_id[:15],
                "text": text,
                "created_at": posted_at.isoformat(),
                "author_id": author["handle"].replace("@", "") + str(random.randint(1, 999)),  # noqa: S311
                "public_metrics": {
                    "like_count": like_count,
                    "retweet_count": share_count,
                    "reply_count": reply_count,
                    "impression_count": view_count,
                },
                "lang": "en",
            }

            conn.execute(
                """INSERT INTO bronze.bronze_posts
                   (id, search_request_id, crawl_run_id, platform, platform_id,
                    author_handle, raw_payload, fetched_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [post_id, request_id, crawl_run_id, platform,
                 f"tweet_{post_id[:8]}", author["handle"],
                 json.dumps(payload), posted_at],
            )
            total_posts += 1

        conn.execute(
            "UPDATE bronze.search_requests SET posts_found = ? WHERE id = ?",
            [num_posts, request_id],
        )
        conn.execute(
            "UPDATE bronze.bronze_crawl_runs SET posts_fetched = ? WHERE id = ?",
            [num_posts, crawl_run_id],
        )
        total_requests += 1

    return {"requests": total_requests, "posts": total_posts}


if __name__ == "__main__":
    import duckdb
    from src.infrastructure.persistence.migrations import create_all_tables
    from src.shared.config import settings

    conn = duckdb.connect(str(settings.db_path))
    create_all_tables(conn)

    existing = conn.execute("SELECT COUNT(*) FROM bronze.search_requests").fetchone()
    if existing and existing[0] > 0:
        print(f"Database already has {existing[0]} search requests. Skipping seed.")
    else:
        result = seed(conn)
        print(f"Seeded {result['requests']} search requests with {result['posts']} posts.")

    conn.close()
