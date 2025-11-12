#utils/logger.py
import logging
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.spinner import Spinner
from rich.layout import Layout
from rich import box

console = Console()

class ArenaLogger:
    def __init__(self, log_file: str = "logs/arena.log"):
        Path(log_file).parent.mkdir(exist_ok=True)
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("Arena")
        self.events = []

    def header(self, text: str, style: str = "bold magenta"):
        console.print(Panel(text, style=style, expand=False, box=box.DOUBLE))
        self.logger.info(f"HEADER: {text}")

    def round_start(self, round_num: int):
        text = f"⚔️  ROUND {round_num} BEGINS ⚔️"
        console.print(f"\n[bold yellow]{text}[/bold yellow]")
        console.print("=" * 60)
        self.logger.info(f"Round {round_num} started")

    def task_announcement(self, task_description: str):
        console.print(f"\n[cyan]📜 CHALLENGE:[/cyan] {task_description}\n")
        self.logger.info(f"Task: {task_description}")

    def agent_action(self, agent_name: str, action: str, detail: str = ""):
        msg = f"[green]{agent_name}[/green]: {action}"
        if detail:
            msg += f" [dim]({detail})[/dim]"
        console.print(msg)
        self.logger.info(f"{agent_name} - {action} - {detail}")

    def alliance_formed(self, agents: list):
        names = ", ".join(agents)
        console.print(f"\n[blue]🤝 ALLIANCE FORMED:[/blue] {names}")
        self.logger.info(f"Alliance: {names}")

    def coup_attempt(self, agents: list, target: str):
        console.print(f"\n[red]⚠️  COUP ATTEMPT![/red]")
        console.print(f"[yellow]Conspirators:[/yellow] {', '.join(agents)}")
        console.print(f"[yellow]Target:[/yellow] {target}\n")
        self.logger.warning(f"Coup attempt against {target} by {agents}")

    def elimination(self, agent_name: str, reason: str):
        console.print(f"\n[red]💀 ELIMINATED:[/red] [bold]{agent_name}[/bold]")
        console.print(f"   Reason: {reason}")
        self.logger.info(f"ELIMINATED: {agent_name} - {reason}")

    def ruler_crowned(self, agent_name: str):
        console.print(f"\n[gold1]👑 NEW RULER CROWNED: {agent_name}[/gold1]\n")
        self.logger.info(f"Ruler: {agent_name}")

    def scoreboard(self, scores: dict):
        table = Table(title="Round Results", show_header=True, box=box.SIMPLE)
        table.add_column("Agent", style="cyan")
        table.add_column("Score", style="magenta")
        table.add_column("Tokens", style="green")
        table.add_column("Status", style="yellow")
        for agent, data in sorted(scores.items(), key=lambda x: x[1]['score'], reverse=True):
            status = "👑 RULER" if data.get('is_ruler') else ""
            if data.get('in_danger'):
                status = "⚠️  DANGER"
            table.add_row(
                agent,
                f"{data['score']:.2f}",
                str(data['tokens']),
                status
            )
        console.print(table)

    def drama(self, event: str):
        console.print(f"\n[magenta]🎭 {event}[/magenta]\n")
        self.logger.warning(f"DRAMA: {event}")
        self.events.append(event)

    def final_summary(self, winner: str, rounds: int, events: list):
        console.print("\n" + "=" * 60)
        console.print(Panel.fit(
            f"[bold gold1]🏆 SEASON COMPLETE 🏆[/bold gold1]\n\n"
            f"Victor: [green]{winner}[/green]\n"
            f"Rounds: {rounds}\n"
            f"Dramatic Events: {len(events)}",
            border_style="gold1"
        ))
        console.print("\n[yellow]Notable Events:[/yellow]")
        for event in events[-5:]:
            console.print(f"  • {event}")
        self.logger.info(f"Season complete. Winner: {winner}")

    def show_intro_animation(self):
        dark_title = Text(" LLM GLADIATOR ARENA ", justify="center", style="bold white on black")
        subtitle = Text("Tokens. Treachery. Triumph.", style="italic dim white")
        frames = [
            "[black on white] ] ◼ ◼ ◼ ◼ ◼[/black on white]",
            "[black on white] ◼ ] ◼ ◼ ◼ ◼[/black on white]",
            "[black on white] ◼ ◼ ] ◼ ◼ ◼[/black on white]",
            "[black on white] ◼ ◼ ◼ ] ◼ ◼[/black on white]",
            "[black on white] ◼ ◼ ◼ ◼ ] ◼[/black on white]",
            "[black on white] ◼ ◼ ◼ ◼ ◼ ][/black on white]"
        ]
        layout = Layout()
        layout.split_column(
            Layout(name="title", size=3),
            Layout(name="anim", ratio=1),
            Layout(name="footer", size=3)
        )
        layout["title"].update(Panel(dark_title + "\n" + subtitle, style="on black"))
        with Live(layout, refresh_per_second=8, transient=True) as live:
            for i in range(12):
                bar = frames[i % len(frames)]
                p = Panel(Align.center(bar + "\n\n" + "Prepare for the carnage...", vertical="middle"), style="bold white on black")
                layout["anim"].update(p)
                layout["footer"].update(Panel("Press Ctrl+C to abort", style="dim"))
        console.print(Panel("Welcome to the Arena", style="bold white on black"))

    def prompt_slot_menu(self, storage):
        console.print("\n[bold white on black]Save Slots[/bold white on black]\n")
        slots = storage.list_slots()
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Slot")
        table.add_column("Status")
        table.add_column("Info")
        for s in range(1, storage.max_slots + 1):
            meta = slots.get(s, {})
            if meta.get("exists"):
                info = f"round {meta.get('round')} saved at {meta.get('saved_at')}"
                table.add_row(str(s), "[green]Occupied[/green]", info)
            else:
                table.add_row(str(s), "[dim]Empty[/dim]", "No save")
        console.print(table)
        console.print("\nChoose: [n] New run  [1-3] Load slot  [d1-d3] Delete slot  [q] Quit\n")
        choice = console.input("[bold]> [/bold]")
        return choice.strip()
        
logger = ArenaLogger()
