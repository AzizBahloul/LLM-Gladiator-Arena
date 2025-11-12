#utils/logger.py
"""Rich terminal logging for the arena."""
import logging
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.layout import Layout

console = Console()

class ArenaLogger:
    """Handles all logging and terminal output."""
    
    def __init__(self, log_file: str = "logs/arena.log"):
        Path(log_file).parent.mkdir(exist_ok=True)
        
        # File logger
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger("Arena")
        
        self.events = []
        
    def header(self, text: str, style: str = "bold magenta"):
        """Print a dramatic header."""
        console.print(Panel(text, style=style, expand=False))
        self.logger.info(f"HEADER: {text}")
        
    def round_start(self, round_num: int):
        """Announce round start."""
        text = f"⚔️  ROUND {round_num} BEGINS ⚔️"
        console.print(f"\n[bold yellow]{text}[/bold yellow]")
        console.print("=" * 60)
        self.logger.info(f"Round {round_num} started")
        
    def task_announcement(self, task_description: str):
        """Announce the challenge."""
        console.print(f"\n[cyan]📜 CHALLENGE:[/cyan] {task_description}\n")
        self.logger.info(f"Task: {task_description}")
        
    def agent_action(self, agent_name: str, action: str, detail: str = ""):
        """Log agent action."""
        msg = f"[green]{agent_name}[/green]: {action}"
        if detail:
            msg += f" [dim]({detail})[/dim]"
        console.print(msg)
        self.logger.info(f"{agent_name} - {action} - {detail}")
        
    def alliance_formed(self, agents: list[str]):
        """Announce alliance."""
        names = ", ".join(agents)
        console.print(f"\n[blue]🤝 ALLIANCE FORMED:[/blue] {names}")
        self.logger.info(f"Alliance: {names}")
        
    def coup_attempt(self, agents: list[str], target: str):
        """Dramatic coup announcement."""
        console.print(f"\n[red]⚠️  COUP ATTEMPT![/red]")
        console.print(f"[yellow]Conspirators:[/yellow] {', '.join(agents)}")
        console.print(f"[yellow]Target:[/yellow] {target}\n")
        self.logger.warning(f"Coup attempt against {target} by {agents}")
        
    def elimination(self, agent_name: str, reason: str):
        """Announce elimination."""
        console.print(f"\n[red]💀 ELIMINATED:[/red] [bold]{agent_name}[/bold]")
        console.print(f"   Reason: {reason}")
        self.logger.info(f"ELIMINATED: {agent_name} - {reason}")
        
    def ruler_crowned(self, agent_name: str):
        """Crown a new ruler."""
        console.print(f"\n[gold1]👑 NEW RULER CROWNED: {agent_name}[/gold1]\n")
        self.logger.info(f"Ruler: {agent_name}")
        
    def scoreboard(self, scores: dict):
        """Display round scores."""
        table = Table(title="Round Results", show_header=True)
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
        """Log dramatic events."""
        console.print(f"\n[magenta]🎭 {event}[/magenta]\n")
        self.logger.warning(f"DRAMA: {event}")
        self.events.append(event)
        
    def final_summary(self, winner: str, rounds: int, events: list):
        """Print final season summary."""
        console.print("\n" + "=" * 60)
        console.print(Panel.fit(
            f"[bold gold1]🏆 SEASON COMPLETE 🏆[/bold gold1]\n\n"
            f"Victor: [green]{winner}[/green]\n"
            f"Rounds: {rounds}\n"
            f"Dramatic Events: {len(events)}",
            border_style="gold1"
        ))
        
        console.print("\n[yellow]Notable Events:[/yellow]")
        for event in events[-5:]:  # Last 5 events
            console.print(f"  • {event}")
        
        self.logger.info(f"Season complete. Winner: {winner}")

logger = ArenaLogger()