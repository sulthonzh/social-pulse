"""E2E test fixtures: seeded DuckDB, Streamlit subprocess, Playwright browser."""

from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from uuid import uuid4

import duckdb
import pytest
from playwright.sync_api import sync_playwright

from src.infrastructure.persistence.migrations import create_all_tables

STREAMLIT_PORT = 8502
BASE_URL = f"http://localhost:{STREAMLIT_PORT}"
HEALTH_URL = f"{BASE_URL}/_stcore/health"
STARTUP_TIMEOUT_S = 45


def _make_search_requests() -> list[dict]:
    return [
        {
            "id": str(uuid4()),
            "keyword": "data engineering",
            "start_date": "2025-01-15",
            "end_date": "2025-01-25",
            "platform": "twitter",
            "status": "completed",
            "posts_found": 5,
        },
        {
            "id": str(uuid4()),
            "keyword": "machine learning",
            "start_date": "2025-01-10",
            "end_date": "2025-01-20",
            "platform": "facebook",
            "status": "completed",
            "posts_found": 5,
        },
        {
            "id": str(uuid4()),
            "keyword": "cloud computing",
            "start_date": "2025-01-05",
            "end_date": "2025-01-15",
            "platform": "instagram",
            "status": "completed",
            "posts_found": 4,
        },
    ]


def _make_gold_posts(search_requests: list[dict]) -> list[dict]:
    posts = []
    # Campaign 1: data engineering / twitter - 5 posts
    sr1 = search_requests[0]
    tweets = [
        ("positive", 0.92, "Data pipelines are the backbone of modern analytics #dataengineering"),
        ("positive", 0.88, "Building ETL with Apache Spark is incredibly rewarding #dataengineering"),
        ("negative", 0.75, "Data quality issues are destroying our pipeline reliability #dataengineering"),
        ("neutral", 0.60, "Interesting discussion on batch vs streaming architectures #dataengineering"),
        ("positive", 0.85, "Excited about the future of real-time data processing #dataengineering"),
    ]
    authors_tw = ["dataeng_guru", "spark_dev", "pipeline_pro", "architect_jane", "streamlord"]
    for i, (sent, conf, text) in enumerate(tweets):
        posts.append({
            "search_request_id": sr1["id"],
            "keyword": sr1["keyword"],
            "platform": "twitter",
            "author_handle": authors_tw[i],
            "author_name": authors_tw[i].replace("_", " ").title(),
            "post_text": text,
            "sentiment": sent,
            "sentiment_confidence": conf,
            "topic_label": "data engineering",
            "language": "en",
            "hashtags": ["dataengineering"],
            "like_count": [120, 95, 55, 78, 151][i],
            "share_count": [35, 28, 18, 22, 64][i],
            "reply_count": [12, 9, 25, 15, 28][i],
            "view_count": [2500, 1800, 1200, 1500, 3690][i],
            "posted_at": f"2025-01-{15 + i} 10:00:00",
        })

    # Campaign 2: machine learning / facebook - 5 posts
    sr2 = search_requests[1]
    fb_posts = [
        ("positive", 0.89, "Just trained a model with 98% accuracy! ML is amazing #machinelearning"),
        ("negative", 0.78, "Overfitting is the bane of every ML engineer #machinelearning"),
        ("positive", 0.82, "Transfer learning saved us months of work #machinelearning"),
        ("negative", 0.71, "GPU costs for training are getting out of hand #machinelearning"),
        ("neutral", 0.65, "Comparing TensorFlow vs PyTorch for production workloads #machinelearning"),
    ]
    authors_fb = ["ml_researcher", "ai_enthusiast", "deeplearn_fan", "gpu_hoarder", "tf_pt_user"]
    for i, (sent, conf, text) in enumerate(fb_posts):
        posts.append({
            "search_request_id": sr2["id"],
            "keyword": sr2["keyword"],
            "platform": "facebook",
            "author_handle": authors_fb[i],
            "author_name": authors_fb[i].replace("_", " ").title(),
            "post_text": text,
            "sentiment": sent,
            "sentiment_confidence": conf,
            "topic_label": "machine learning",
            "language": "en",
            "hashtags": ["machinelearning"],
            "like_count": [200, 130, 168, 85, 170][i],
            "share_count": [55, 38, 48, 22, 66][i],
            "reply_count": [30, 22, 18, 15, 43][i],
            "view_count": [3200, 2100, 2800, 1500, 3580][i],
            "posted_at": f"2025-01-{10 + i} 14:30:00",
        })

    # Campaign 3: cloud computing / instagram - 4 posts
    sr3 = search_requests[2]
    ig_posts = [
        ("positive", 0.86, "Migrated our entire infra to AWS, so much faster now #cloudcomputing"),
        ("negative", 0.79, "Cloud vendor lock-in is a serious problem #cloudcomputing"),
        ("positive", 0.83, "Kubernetes makes container orchestration a breeze #cloudcomputing"),
        ("neutral", 0.62, "Comparing serverless vs containers for microservices #cloudcomputing"),
    ]
    authors_ig = ["cloud_ninja", "devops_sam", "k8s_master", "serverless_sara"]
    for i, (sent, conf, text) in enumerate(ig_posts):
        posts.append({
            "search_request_id": sr3["id"],
            "keyword": sr3["keyword"],
            "platform": "instagram",
            "author_handle": authors_ig[i],
            "author_name": authors_ig[i].replace("_", " ").title(),
            "post_text": text,
            "sentiment": sent,
            "sentiment_confidence": conf,
            "topic_label": "cloud computing",
            "language": "en",
            "hashtags": ["cloudcomputing"],
            "like_count": [310, 145, 220, 180][i],
            "share_count": [80, 42, 68, 63][i],
            "reply_count": [35, 28, 32, 21][i],
            "view_count": [6200, 2800, 4500, 4500][i],
            "posted_at": f"2025-01-{5 + i} 09:15:00",
        })

    return posts


def _create_seed_db(db_path: str) -> None:
    conn = duckdb.connect(db_path)
    create_all_tables(conn)

    search_requests = _make_search_requests()

    for sr in search_requests:
        conn.execute(
            "INSERT INTO bronze.search_requests (id, keyword, start_date, end_date, platform, status, posts_found) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [sr["id"], sr["keyword"], sr["start_date"], sr["end_date"],
             sr["platform"], sr["status"], sr["posts_found"]],
        )

    gold_posts = _make_gold_posts(search_requests)

    for gp in gold_posts:
        # bronze crawl run
        crawl_id = str(uuid4())
        conn.execute(
            "INSERT INTO bronze.bronze_crawl_runs (id, search_request_id, platform, status, posts_fetched) "
            "VALUES (?, ?, ?, 'completed', 1)",
            [crawl_id, gp["search_request_id"], gp["platform"]],
        )

        # bronze post
        bronze_id = str(uuid4())
        conn.execute(
            "INSERT INTO bronze.bronze_posts (id, search_request_id, crawl_run_id, platform, platform_id, author_handle) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [bronze_id, gp["search_request_id"], crawl_id, gp["platform"],
             f"pid_{bronze_id[:8]}", gp["author_handle"]],
        )

        # silver post
        silver_id = str(uuid4())
        conn.execute(
            "INSERT INTO silver.silver_posts "
            "(id, bronze_post_id, search_request_id, platform, platform_id, author_handle, author_name, "
            "post_text, posted_at, like_count, share_count, reply_count, view_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [silver_id, bronze_id, gp["search_request_id"], gp["platform"],
             f"pid_{bronze_id[:8]}", gp["author_handle"], gp["author_name"],
             gp["post_text"], gp["posted_at"], gp["like_count"], gp["share_count"],
             gp["reply_count"], gp["view_count"]],
        )

        # silver ai enrichment
        conn.execute(
            "INSERT INTO silver.silver_ai_enrichment "
            "(silver_post_id, ai_version, hashtags, language, topic_label, "
            "sentiment, sentiment_confidence) "
            "VALUES (?, 1, ?, ?, ?, ?, ?)",
            [silver_id, gp["hashtags"], gp["language"], gp["topic_label"],
             gp["sentiment"], gp["sentiment_confidence"]],
        )

        # gold post search
        conn.execute(
            "INSERT INTO gold.gold_post_search "
            "(search_request_id, keyword, platform, author_handle, author_name, post_text, "
            "posted_at, sentiment, sentiment_confidence, topic_label, language, hashtags, "
            "like_count, share_count, reply_count, view_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [gp["search_request_id"], gp["keyword"], gp["platform"],
             gp["author_handle"], gp["author_name"], gp["post_text"],
             gp["posted_at"], gp["sentiment"], gp["sentiment_confidence"],
             gp["topic_label"], gp["language"], gp["hashtags"],
             gp["like_count"], gp["share_count"], gp["reply_count"], gp["view_count"]],
        )

    # gold_campaign_daily - 3 days per campaign
    for sr in search_requests:
        sr_posts = [p for p in gold_posts if p["search_request_id"] == sr["id"]]
        for day_offset in range(3):
            day_posts = sr_posts[day_offset:day_offset + 2] if day_offset < 2 else sr_posts[2:]
            if not day_posts:
                continue
            total = len(day_posts)
            pos = sum(1 for p in day_posts if p["sentiment"] == "positive")
            neg = sum(1 for p in day_posts if p["sentiment"] == "negative")
            neu = sum(1 for p in day_posts if p["sentiment"] == "neutral")
            avg_conf = sum(p["sentiment_confidence"] for p in day_posts) / total
            conn.execute(
                "INSERT INTO gold.gold_campaign_daily "
                "(search_request_id, keyword, platform, date, total_posts, "
                "positive_count, negative_count, neutral_count, avg_confidence, "
                "top_hashtags, top_topics, total_likes, total_shares, total_replies, total_views) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [sr["id"], sr["keyword"], sr["platform"],
                 f"2025-01-{15 + day_offset * 3}",
                 total, pos, neg, neu, round(avg_conf, 3),
                 [sr["keyword"].replace(" ", "")],
                 [sr["keyword"]],
                 sum(p["like_count"] for p in day_posts),
                 sum(p["share_count"] for p in day_posts),
                 sum(p["reply_count"] for p in day_posts),
                 sum(p["view_count"] for p in day_posts)],
            )

    # gold_campaign_summary - 1 per campaign
    for sr in search_requests:
        sr_posts = [p for p in gold_posts if p["search_request_id"] == sr["id"]]
        total = len(sr_posts)
        pos = sum(1 for p in sr_posts if p["sentiment"] == "positive")
        neg = sum(1 for p in sr_posts if p["sentiment"] == "negative")
        neu = sum(1 for p in sr_posts if p["sentiment"] == "neutral")
        avg_conf = sum(p["sentiment_confidence"] for p in sr_posts) / total
        conn.execute(
            "INSERT INTO gold.gold_campaign_summary "
            "(search_request_id, keyword, start_date, end_date, total_posts, "
            "positive_pct, negative_pct, neutral_pct, avg_confidence, "
            "total_likes, total_shares, total_replies, total_views, "
            "top_hashtags, top_topics, platforms) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [sr["id"], sr["keyword"], sr["start_date"], sr["end_date"], total,
             round(pos / total * 100, 1), round(neg / total * 100, 1), round(neu / total * 100, 1),
             round(avg_conf, 3),
             sum(p["like_count"] for p in sr_posts),
             sum(p["share_count"] for p in sr_posts),
             sum(p["reply_count"] for p in sr_posts),
             sum(p["view_count"] for p in sr_posts),
             [sr["keyword"].replace(" ", "")],
             [sr["keyword"]],
             [sr["platform"]]],
        )

    conn.close()


@pytest.fixture(scope="session")
def _seed_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    db_dir = tmp_path_factory.mktemp("e2e_db")
    db_path = db_dir / "socialpulse_e2e.duckdb"
    _create_seed_db(str(db_path))
    return db_path


@pytest.fixture(scope="session")
def streamlit_process(_seed_db: Path):  # type: ignore[no-untyped-def]
    env = os.environ.copy()
    env["SOCIALPULSE_DB_PATH"] = str(_seed_db)

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run",
            "src/presentation/app.py",
            "--server.headless=true",
            f"--server.port={STREAMLIT_PORT}",
            "--server.fileWatcherType=none",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    deadline = time.time() + STARTUP_TIMEOUT_S
    while time.time() < deadline:
        try:
            resp = urllib.request.urlopen(HEALTH_URL, timeout=2)
            if resp.status == 200:
                break
        except Exception:
            time.sleep(0.5)
    else:
        proc.terminate()
        proc.wait(timeout=5)
        raise RuntimeError("Streamlit failed to start within timeout")

    yield proc

    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


@pytest.fixture(scope="session")
def _playwright_instance():
    pw = sync_playwright().start()
    yield pw
    pw.stop()


@pytest.fixture(scope="session")
def browser(_playwright_instance):
    chromium = _playwright_instance.chromium.launch(headless=True)
    yield chromium
    chromium.close()


@pytest.fixture
def page(browser, streamlit_process):  # type: ignore[no-untyped-def]
    ctx = browser.new_context()
    pg = ctx.new_page()
    pg.goto(BASE_URL, wait_until="networkidle", timeout=30000)
    # Wait for Streamlit to fully render
    pg.wait_for_selector('[data-testid="stSidebar"]', timeout=15000)
    yield pg
    ctx.close()


def navigate_to(page, screen_name: str) -> None:
    """Select a screen from the sidebar navigation selectbox."""
    sb = page.query_selector('[data-baseweb="select"]')
    sb.click()

    option = page.wait_for_selector(
        f'li[role="option"]:has-text("{screen_name}")', timeout=5000
    )
    option.click()

    page.wait_for_timeout(2000)
