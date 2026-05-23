"""SocialPulse admin CLI — typer-based command-line tooling."""

from __future__ import annotations

import asyncio
from datetime import date
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from src.shared.config import settings

app = typer.Typer(
    name="socialpulse",
    help="SocialPulse admin CLI — manage crawls, enrichment, gold tables, and maintenance.",
    no_args_is_help=True,
)
gold_app = typer.Typer(help="Gold table operations.")
app.add_typer(gold_app, name="gold")
config_app = typer.Typer(help="Configuration management.")
app.add_typer(config_app, name="config")

console = Console()

_SECRET_PATTERNS = (
    "token",
    "secret",
    "api_key",
    "bearer",
    "password",
)

_REDACT_PREFIX_LEN = 4


def _redact_value(key: str, value: str) -> str:
    if not value:
        return ""
    key_lower = key.lower()
    if any(pattern in key_lower for pattern in _SECRET_PATTERNS):
        return value[:_REDACT_PREFIX_LEN] + "****" if len(value) > _REDACT_PREFIX_LEN else "****"
    return value


@app.command()
def status() -> None:
    """Show system status — DB size, table row counts, recent jobs."""
    import duckdb  # noqa: PLC0415

    db_path = Path(settings.db_path)
    if not db_path.exists():
        console.print(f"[red]Database not found:[/red] {db_path}")
        raise typer.Exit(code=1)

    db_size_mb = db_path.stat().st_size / (1024 * 1024)
    console.print("\n[bold]SocialPulse Status[/bold]")
    console.print(f"  Database: {db_path}")
    console.print(f"  Size: {db_size_mb:.2f} MB")
    console.print(f"  Environment: {settings.env}\n")

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        tables_table = Table(title="Table Row Counts")
        tables_table.add_column("Schema.Table", style="cyan")
        tables_table.add_column("Rows", justify="right", style="green")

        rows = conn.execute(
            "SELECT table_schema, table_name FROM information_schema.tables "
            "WHERE table_schema IN ('bronze', 'silver', 'gold') "
            "ORDER BY table_schema, table_name"
        ).fetchall()

        for schema, table_name in rows:
            qualified = f"{schema}.{table_name}"
            try:
                result = conn.execute(f'SELECT COUNT(*) FROM "{schema}"."{table_name}"').fetchone()
                count = result[0] if result else 0
                tables_table.add_row(qualified, f"{count:,}")
            except Exception:
                tables_table.add_row(qualified, "[dim]error[/dim]")

        console.print(tables_table)

        jobs_table = Table(title="Recent AI Jobs (last 5)")
        jobs_table.add_column("ID", style="dim")
        jobs_table.add_column("Type", style="cyan")
        jobs_table.add_column("Status", style="green")
        jobs_table.add_column("Created")

        try:
            recent = conn.execute(
                "SELECT id, job_type, status, created_at "
                "FROM silver.ai_jobs ORDER BY created_at DESC LIMIT 5"
            ).fetchall()
            for row in recent:
                jobs_table.add_row(str(row[0])[:8], str(row[1]), str(row[2]), str(row[3]))
        except Exception:
            jobs_table.add_row("—", "no ai_jobs table yet", "—", "—")

        console.print(jobs_table)
    finally:
        conn.close()


@app.command()
def crawl(
    keyword: Annotated[str, typer.Argument(help="Search keyword")],
    platform: Annotated[
        str,
        typer.Argument(help="Platform: twitter, facebook, instagram, youtube, reddit"),
    ],
    start_date: Annotated[
        str,
        typer.Argument(help="Start date (YYYY-MM-DD)"),
    ],
    end_date: Annotated[
        str,
        typer.Argument(help="End date (YYYY-MM-DD)"),
    ],
) -> None:
    """Trigger a crawl for a keyword on a specific platform."""
    from src.domain.value_objects.platform import Platform  # noqa: PLC0415

    valid_platforms = [p.value for p in Platform]
    if platform not in valid_platforms:
        console.print(
            f"[red]Invalid platform '{platform}'. Choose: {', '.join(valid_platforms)}[/red]"
        )
        raise typer.Exit(code=1)

    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    if end < start:
        console.print("[red]end_date must be on or after start_date[/red]")
        raise typer.Exit(code=1)

    import duckdb  # noqa: PLC0415

    from src.application.use_cases.ingest_pipeline import IngestPipeline  # noqa: PLC0415
    from src.shared.logging_config import configure_logging  # noqa: PLC0415

    configure_logging()
    console.print(
        f"[bold]Starting crawl:[/bold] keyword='{keyword}' platform={platform} "
        f"range={start_date}..{end_date}"
    )

    conn = duckdb.connect(settings.db_path)
    try:

        def on_progress(stage: str, current: int, total: int) -> None:
            if total > 0:
                console.print(f"  [{stage}] {current}/{total}")
            else:
                console.print(f"  [{stage}] started...")

        pipeline = IngestPipeline(conn, progress_callback=on_progress)
        result = asyncio.run(
            pipeline.execute(
                keyword=keyword,
                platform=Platform(platform),
                start_date=start,
                end_date=end,
            )
        )

        console.print(
            f"\n[bold green]Pipeline complete[/bold green] "
            f"(request={result.search_request_id[:8]}…, "
            f"crawled={result.posts_crawled}, "
            f"enriched={result.posts_enriched}, "
            f"gold_built={result.gold_built})"
        )
    except Exception as exc:
        console.print(f"[red]Pipeline failed:[/red] {exc}")
        raise typer.Exit(code=1) from None
    finally:
        conn.close()


@app.command()
def enrich(
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max posts to enrich")] = 100,
) -> None:
    """Run AI enrichment on pending (unenriched) posts."""
    import duckdb  # noqa: PLC0415

    from src.shared.logging_config import configure_logging  # noqa: PLC0415

    configure_logging()

    from src.application.use_cases.run_enrichment import _run_enrichment  # noqa: PLC0415

    console.print(f"[bold]Running enrichment[/bold] (limit={limit})")

    conn = duckdb.connect(settings.db_path)
    try:
        asyncio.run(_run_enrichment(conn, limit))
        console.print("[green]Enrichment complete[/green]")
    except Exception as exc:
        console.print(f"[red]Enrichment failed:[/red] {exc}")
        raise typer.Exit(code=1) from None
    finally:
        conn.close()


@gold_app.command("rebuild")
def gold_rebuild(
    search_request_id: Annotated[
        str | None,
        typer.Option("--search-request-id", "-s", help="Specific search request to rebuild"),
    ] = None,
    keyword: Annotated[
        str | None,
        typer.Option("--keyword", "-k", help="Keyword (needed with --search-request-id)"),
    ] = None,
) -> None:
    """Rebuild gold tables from enriched data."""
    import duckdb  # noqa: PLC0415

    from src.shared.logging_config import configure_logging  # noqa: PLC0415

    configure_logging()

    from src.application.use_cases.build_gold import _build_for_request  # noqa: PLC0415

    console.print("[bold]Rebuilding gold tables[/bold]")

    conn = duckdb.connect(settings.db_path)
    try:
        if search_request_id:
            rows = conn.execute(
                "SELECT keyword, start_date, end_date FROM bronze.search_requests WHERE id = ?",
                [search_request_id],
            ).fetchall()

            if not rows:
                console.print(f"[red]Search request not found:[/red] {search_request_id}")
                raise typer.Exit(code=1)

            row_keyword, start_date_val, end_date_val = rows[0]
            kw = keyword or str(row_keyword)

            sd = (
                start_date_val
                if isinstance(start_date_val, date)
                else date.fromisoformat(str(start_date_val))
            )
            ed = (
                end_date_val
                if isinstance(end_date_val, date)
                else date.fromisoformat(str(end_date_val))
            )

            console.print(f"  Building for request {search_request_id[:8]}… (keyword='{kw}')")
            asyncio.run(_build_for_request(conn, search_request_id, kw, sd, ed))
        else:
            rows = conn.execute(
                "SELECT id, keyword, start_date, end_date "
                "FROM bronze.search_requests "
                "WHERE status = 'completed'"
            ).fetchall()

            if not rows:
                console.print("[dim]No completed search requests to build[/dim]")
                return

            for request_id, kw, start_date_val, end_date_val in rows:
                sd = (
                    start_date_val
                    if isinstance(start_date_val, date)
                    else date.fromisoformat(str(start_date_val))
                )
                ed = (
                    end_date_val
                    if isinstance(end_date_val, date)
                    else date.fromisoformat(str(end_date_val))
                )
                console.print(f"  Building request {str(request_id)[:8]}… (keyword='{kw}')")
                try:
                    asyncio.run(_build_for_request(conn, str(request_id), str(kw), sd, ed))
                except Exception:
                    console.print(f"[red]  Failed for request {request_id}[/red]")

        console.print("[green]Gold rebuild complete[/green]")
    except SystemExit:
        raise
    except Exception as exc:
        console.print(f"[red]Gold rebuild failed:[/red] {exc}")
        raise typer.Exit(code=1) from None
    finally:
        conn.close()


@config_app.command("show")
def config_show() -> None:
    """Show current configuration (secrets are redacted)."""
    console.print("\n[bold]SocialPulse Configuration[/bold]\n")

    table = Table(show_header=True)
    table.add_column("Setting", style="cyan")
    table.add_column("Value")

    for field_name in settings.model_fields:
        value = getattr(settings, field_name, "")
        display = _redact_value(field_name, str(value))
        table.add_row(field_name, display)

    console.print(table)
    console.print()


@app.command()
def maintenance(
    operation: Annotated[
        str,
        typer.Option(
            "--operation",
            "-o",
            help="Operation: checkpoint, vacuum, analyze, all",
        ),
    ] = "all",
) -> None:
    """Run DB maintenance — checkpoint, vacuum, and/or analyze."""
    from src.shared.db_maintenance import (  # noqa: PLC0415
        run_all_maintenance,
        run_analyze,
        run_checkpoint,
        run_vacuum,
    )

    valid_operations = ("checkpoint", "vacuum", "analyze", "all")
    if operation not in valid_operations:
        console.print(
            f"[red]Invalid operation '{operation}'. Choose: {', '.join(valid_operations)}[/red]"
        )
        raise typer.Exit(code=1)

    db_path = settings.db_path
    console.print(f"[bold]Running maintenance[/bold] (operation={operation}, db={db_path})")

    if operation == "all":
        results = run_all_maintenance(db_path)
        for name, ok in results.items():
            status_label = "[green]OK[/green]" if ok else "[red]FAILED[/red]"
            console.print(f"  {name}: {status_label}")
    elif operation == "checkpoint":
        ok = run_checkpoint(db_path)
        console.print(f"checkpoint: {'[green]OK[/green]' if ok else '[red]FAILED[/red]'}")
    elif operation == "vacuum":
        ok = run_vacuum(db_path)
        console.print(f"vacuum: {'[green]OK[/green]' if ok else '[red]FAILED[/red]'}")
    elif operation == "analyze":
        ok = run_analyze(db_path)
        console.print(f"analyze: {'[green]OK[/green]' if ok else '[red]FAILED[/red]'}")


if __name__ == "__main__":
    app()
