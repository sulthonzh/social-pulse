from __future__ import annotations

from typing import Any

import streamlit.components.v1 as components

_SPIDER = "\U0001f577\ufe0f"
_BRAIN = "\U0001f9e0"
_CHART = "\U0001f4ca"
_CHECK = "\u2705"
_CROSS = "\u274c"
_TIMER = "\u23f1\ufe0f"
_WARN = "\u26a0\ufe0f"


def render_pipeline_progress(
    run_id: str,
    api_base_url: str = "http://localhost:8000",
) -> dict[str, Any] | None:
    """Render an HTML component that streams pipeline progress via SSE."""
    html = f"""
    <div id="progress-container" style="font-family: 'Source Sans Pro', sans-serif; padding: 10px;">
        <div id="status-text" style="font-size: 16px; margin-bottom: 8px; color: #31333F;">
            Connecting to pipeline...
        </div>
        <div style="background: #f0f2f6; border-radius: 8px; overflow: hidden; height: 24px;">
            <div id="progress-bar" style="background: linear-gradient(90deg, #7c3aed, #2563eb); height: 100%; width: 0%; transition: width 0.3s ease;"></div>
        </div>
        <div id="detail-text" style="font-size: 13px; margin-top: 6px; color: #6c7380;"></div>
    </div>
    <script>
    const runId = "{run_id}";
    const apiBase = "{api_base_url}";
    const statusEl = document.getElementById("status-text");
    const barEl = document.getElementById("progress-bar");
    const detailEl = document.getElementById("detail-text");

    const es = new EventSource(apiBase + "/api/pipeline/" + runId + "/stream");

    es.addEventListener("message", function(e) {{
        try {{
            const data = JSON.parse(e.data);
            let pct = 0;

            if (data.stage === "crawling") {{
                if (data.current === 0) {{
                    pct = 10;
                    statusEl.textContent = "{_SPIDER} " + data.message;
                }} else {{
                    pct = 20;
                    statusEl.textContent = "{_CHECK} " + data.message;
                }}
            }} else if (data.stage === "enriching") {{
                pct = 20 + Math.round(70 * data.current / Math.max(data.total, 1));
                statusEl.textContent = "{_BRAIN} " + data.message;
            }} else if (data.stage === "gold") {{
                pct = 95;
                statusEl.textContent = "{_CHART} " + data.message;
            }} else if (data.stage === "complete") {{
                pct = 100;
                statusEl.textContent = "{_CHECK} Pipeline complete!";
                detailEl.innerHTML = "<b>" + (data.posts_crawled || 0) + "</b> posts crawled, <b>"
                    + (data.posts_enriched || 0) + "</b> enriched"
                    + (data.gold_built ? ", gold tables built" : "");
                es.close();
                setTimeout(function() {{
                    window.parent.postMessage({{type: 'streamlit:rerunScript'}}, '*');
                }}, 1500);
            }} else if (data.stage === "error") {{
                statusEl.style.color = "#dc2626";
                statusEl.textContent = "{_CROSS} " + (data.message || "Pipeline failed");
                detailEl.textContent = data.error || "";
                es.close();
            }}

            barEl.style.width = pct + "%";
        }} catch(err) {{
            console.error("Parse error:", err);
        }}
    }});

    es.addEventListener("done", function() {{
        es.close();
        setTimeout(function() {{
            window.parent.postMessage({{type: 'streamlit:rerunScript'}}, '*');
        }}, 1500);
    }});

    es.addEventListener("timeout", function() {{
        statusEl.style.color = "#dc2626";
        statusEl.textContent = "{_TIMER} Connection timed out";
        es.close();
    }});

    es.onerror = function() {{
        statusEl.style.color = "#dc2626";
        statusEl.textContent = "{_WARN} Connection lost. Retrying...";
    }};
    </script>
    """
    components.html(html, height=120)
    return None
