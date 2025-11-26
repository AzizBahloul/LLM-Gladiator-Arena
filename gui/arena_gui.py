# gui/arena_gui.py
"""Terminal-style GUI for LLM Gladiator Arena using Textual."""
from datetime import datetime
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, Label, ProgressBar, DataTable, Log, Button, Input
from textual.reactive import reactive
from textual.message import Message as TextualMessage
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich.console import RenderableType
from rich.align import Align
from typing import List, Dict, Any

class AgentCard(Static):
    """Display card for an agent with status."""
    
    def __init__(self, agent_data: Dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        self.agent_data = agent_data
    
    def render(self) -> RenderableType:
        """Render the agent card."""
        name = self.agent_data.get('name', 'Unknown')
        personality = self.agent_data.get('personality', 'unknown')
        tokens = self.agent_data.get('tokens', 0)
        is_alive = self.agent_data.get('is_alive', True)
        is_ruler = self.agent_data.get('is_ruler', False)
        alliances = self.agent_data.get('alliances', [])
        model = self.agent_data.get('model', 'unknown')
        
        # Status symbol
        status = "💀" if not is_alive else "👑" if is_ruler else "⚔️"
        
        # Color based on status
        color = "red" if not is_alive else "yellow" if is_ruler else "cyan"
        
        # Build card content
        content = Text()
        content.append(f"{status} {name}\n", style=f"bold {color}")
        content.append(f"  Model: {model}\n", style="magenta")
        content.append(f"  Personality: {personality}\n", style="dim")
        content.append(f"  Tokens: {tokens} BB\n", style="green" if tokens > 10 else "red")
        
        if alliances:
            content.append(f"  Allies: {', '.join(alliances[:2])}\n", style="blue")
        
        if not is_alive:
            content.append("  [ELIMINATED]", style="bold red")
        
        return Panel(content, border_style=color, padding=(0, 1))


class StatusPanel(Static):
    """Display overall game status."""
    
    round_num = reactive(0)
    alive_count = reactive(0)
    total_tokens = reactive(0)
    ruler_name = reactive("None")
    
    def render(self) -> RenderableType:
        """Render the status panel."""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="cyan bold")
        table.add_column(style="white")
        
        table.add_row("🎮 Round:", f"{self.round_num}")
        table.add_row("⚔️  Alive:", f"{self.alive_count}")
        table.add_row("💰 Total Tokens:", f"{self.total_tokens} BB")
        table.add_row("👑 Ruler:", self.ruler_name)
        table.add_row("⏰ Time:", datetime.now().strftime("%H:%M:%S"))
        
        return Panel(table, title="[bold cyan]Game Status[/]", border_style="cyan")


class EventLog(Static):
    """Scrollable event log with dramatic narration."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.events = []
    
    def add_event(self, event: str, style: str = "white"):
        """Add an event to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.events.append((timestamp, event, style))
        if len(self.events) > 100:  # Keep last 100 events
            self.events.pop(0)
        self.refresh()
    
    def render(self) -> RenderableType:
        """Render the event log."""
        text = Text()
        for timestamp, event, style in self.events[-20:]:  # Show last 20
            text.append(f"[{timestamp}] ", style="dim")
            text.append(f"{event}\n", style=style)
        
        return Panel(text, title="[bold red]Arena Chronicle[/]", border_style="red", height=15)


class ChatPanel(Static):
    """Real-time chat panel showing agent discussions."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messages = []
        self.max_messages = 50
    
    def add_chat_message(self, sender: str, content: str, msg_type: str = "public"):
        """Add a chat message to the display."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color and emoji based on message type
        type_styles = {
            "public": ("💬", "white"),
            "private": ("🔒", "blue"),
            "alliance": ("🤝", "cyan"),
            "broadcast": ("📢", "yellow"),
            "taunt": ("🔥", "red"),
            "strategy": ("🎯", "magenta"),
            "whisper": ("👂", "dim"),
            "system": ("⚡", "green"),
        }
        
        emoji, style = type_styles.get(msg_type, ("💬", "white"))
        
        self.messages.append({
            'timestamp': timestamp,
            'sender': sender,
            'content': content,
            'emoji': emoji,
            'style': style,
            'type': msg_type
        })
        
        # Keep only recent messages
        if len(self.messages) > self.max_messages:
            self.messages.pop(0)
        
        self.refresh()
    
    def render(self) -> RenderableType:
        """Render the chat panel."""
        text = Text()
        
        if not self.messages:
            text.append("💬 Waiting for agents to speak...\n", style="dim italic")
            text.append("\nModels will discuss strategies,\n", style="dim")
            text.append("form alliances, and taunt rivals\n", style="dim")
            text.append("in real-time here!", style="dim")
        else:
            for msg in self.messages[-15:]:  # Show last 15 messages
                # Timestamp
                text.append(f"[{msg['timestamp']}] ", style="dim")
                # Emoji and sender
                text.append(f"{msg['emoji']} ", style=msg['style'])
                text.append(f"{msg['sender']}", style=f"bold {msg['style']}")
                text.append(": ", style="dim")
                # Content
                text.append(f"{msg['content']}\n", style=msg['style'])
        
        return Panel(
            text, 
            title="[bold cyan]💬 Agent Chat[/]", 
            subtitle="[dim]Real-time discussions[/]",
            border_style="cyan", 
            height=20
        )
    
    def clear(self):
        """Clear all messages."""
        self.messages = []
        self.refresh()


class ResourceBar(Static):
    """Display resource utilization."""
    
    cpu_usage = reactive(0)
    gpu_usage = reactive(0)
    token_pool = reactive(100)
    
    def render(self) -> RenderableType:
        """Render resource bars."""
        text = Text()
        
        # CPU Bar
        text.append("CPU ", style="bold cyan")
        cpu_bar = "█" * int(self.cpu_usage / 5) + "░" * (20 - int(self.cpu_usage / 5))
        text.append(f"[{cpu_bar}] {self.cpu_usage}%\n", style="cyan")
        
        # GPU Bar
        text.append("GPU ", style="bold magenta")
        gpu_bar = "█" * int(self.gpu_usage / 5) + "░" * (20 - int(self.gpu_usage / 5))
        text.append(f"[{gpu_bar}] {self.gpu_usage}%\n", style="magenta")
        
        # Token Pool
        text.append("Pool ", style="bold yellow")
        token_bar = "💰" * int(self.token_pool / 10) + "·" * (10 - int(self.token_pool / 10))
        text.append(f"[{token_bar}] {self.token_pool} BB\n", style="yellow")
        
        return Panel(text, title="[bold]Resources[/]", border_style="white")


class ArenaGUI(App):
    """Main Textual GUI application for the Arena."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    Header {
        dock: top;
        height: 3;
        background: $error 50%;
        color: $text;
    }
    
    Footer {
        dock: bottom;
        height: 1;
        background: $panel;
    }
    
    #main-container {
        layout: horizontal;
        height: 100%;
    }
    
    #left-panel {
        width: 22%;
        height: 100%;
        layout: vertical;
    }
    
    #center-panel {
        width: 38%;
        height: 100%;
        layout: vertical;
    }
    
    #chat-panel {
        width: 25%;
        height: 100%;
        layout: vertical;
    }
    
    #right-panel {
        width: 15%;
        height: 100%;
        layout: vertical;
    }
    
    AgentCard {
        height: auto;
        margin: 1;
    }
    
    StatusPanel {
        height: auto;
        margin: 1;
    }
    
    EventLog {
        height: 50%;
        margin: 1;
    }
    
    ChatPanel {
        height: 100%;
        margin: 1;
    }
    
    ResourceBar {
        height: auto;
        margin: 1;
    }
    
    #agents-container {
        height: 100%;
        overflow-y: auto;
    }
    """
    
    TITLE = "🏛️  LLM GLADIATOR ARENA  🏛️"
    SUB_TITLE = "Where AI Agents Fight for Survival"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orchestrator = None
        self.config = None
        self.restore_state = None
        self.status_panel = None
        self.event_log = None
        self.chat_panel = None
        self.resource_bar = None
        self.agents_container = None
        self.game_thread = None
        self.game_running = False
    
    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header(show_clock=True)
        
        with Container(id="main-container"):
            # Left panel: Agents
            with Vertical(id="left-panel"):
                yield Static("[bold cyan]═══ GLADIATORS ═══[/]", classes="panel-title")
                with ScrollableContainer(id="agents-container"):
                    pass  # Agent cards will be added dynamically
            
            # Center panel: Events and action
            with Vertical(id="center-panel"):
                self.event_log = EventLog()
                yield self.event_log
            
            # Chat panel: Real-time agent discussions
            with Vertical(id="chat-panel"):
                self.chat_panel = ChatPanel()
                yield self.chat_panel
            
            # Right panel: Status and resources
            with Vertical(id="right-panel"):
                self.status_panel = StatusPanel()
                yield self.status_panel
                
                self.resource_bar = ResourceBar()
                yield self.resource_bar
                
                yield Static(
                    "[dim]💀 Dark stories...\n"
                    "⚔️  Alliances shift\n"
                    "🔥 Survival...[/]",
                    classes="flavor-text"
                )
        
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app starts."""
        self.add_welcome_events()
        
        # Start the game in a background thread
        if self.config:
            import threading
            self.game_thread = threading.Thread(target=self._run_game, daemon=True)
            self.game_thread.start()
    
    def _run_game(self):
        """Run the game orchestrator in background thread."""
        try:
            from core.orchestrator import ArenaOrchestrator
            
            # Create orchestrator with GUI reference
            self.orchestrator = ArenaOrchestrator(
                self.config, 
                restore_state=self.restore_state, 
                gui=self
            )
            
            self.game_running = True
            
            # Initial update after orchestrator is created
            self.call_from_thread(self._update_gui)
            
            # Run the season
            self.orchestrator.run_season()
            
            self.game_running = False
            self.add_event("🏆 SEASON COMPLETE!", "bold yellow")
            
        except Exception as e:
            self.add_event(f"❌ Error: {e}", "bold red")
            import traceback
            traceback.print_exc()
    
    def _update_gui(self):
        """Update GUI from orchestrator data."""
        if self.orchestrator:
            agent_data = [a.to_dict() for a in self.orchestrator.agents]
            self.update_agents(agent_data)
            self.update_round(self.orchestrator.round_num)
    
    def add_welcome_events(self):
        """Add welcome messages to the event log."""
        if self.event_log:
            self.event_log.add_event("🏛️  THE ARENA AWAKENS", "bold red")
            self.event_log.add_event("Ancient AI rituals begin...", "dim")
            self.event_log.add_event("Gladiators prepare for battle!", "yellow")
    
    def update_agents(self, agents: List[Dict[str, Any]]):
        """Update the agent display."""
        try:
            container = self.query_one("#agents-container")
            container.remove_children()
            
            for agent_data in agents:
                container.mount(AgentCard(agent_data))
            
            # Update status
            alive = [a for a in agents if a.get('is_alive', True)]
            ruler = next((a for a in agents if a.get('is_ruler', False)), None)
            
            if self.status_panel:
                self.status_panel.alive_count = len(alive)
                self.status_panel.total_tokens = sum(a.get('tokens', 0) for a in alive)
                self.status_panel.ruler_name = ruler['name'] if ruler else "None"
        except Exception:
            pass  # Ignore errors if GUI not ready
    
    def update_round(self, round_num: int):
        """Update the current round number."""
        if self.status_panel:
            self.status_panel.round_num = round_num
    
    def update_resources(self, cpu: int, gpu: int, tokens: int):
        """Update resource bars."""
        if self.resource_bar:
            self.resource_bar.cpu_usage = cpu
            self.resource_bar.gpu_usage = gpu
            self.resource_bar.token_pool = tokens
    
    def add_event(self, event: str, style: str = "white"):
        """Add an event to the log."""
        if self.event_log:
            self.event_log.add_event(event, style)
    
    def add_chat_message(self, sender: str, content: str, msg_type: str = "public"):
        """Add a chat message to the chat panel."""
        if self.chat_panel:
            self.chat_panel.add_chat_message(sender, content, msg_type)
    
    def add_discussion_message(self, sender: str, content: str):
        """Add a discussion message (shorthand for public chat)."""
        self.add_chat_message(sender, content, "public")
    
    def add_taunt_message(self, sender: str, content: str):
        """Add a taunt message to chat."""
        self.add_chat_message(sender, content, "taunt")
    
    def add_strategy_message(self, sender: str, content: str):
        """Add a strategic message to chat."""
        self.add_chat_message(sender, content, "strategy")
    
    def add_alliance_chat(self, sender: str, content: str):
        """Add an alliance chat message."""
        self.add_chat_message(sender, content, "alliance")
    
    def add_system_message(self, content: str):
        """Add a system message to chat."""
        self.add_chat_message("ARENA", content, "system")
    
    def add_drama_event(self, event: str):
        """Add a dramatic event."""
        self.add_event(f"🔥 {event}", "bold red")
    
    def add_alliance_event(self, event: str):
        """Add an alliance event."""
        self.add_event(f"🤝 {event}", "blue")
    
    def add_combat_event(self, event: str):
        """Add a combat event."""
        self.add_event(f"⚔️  {event}", "yellow")
    
    def add_elimination_event(self, agent_name: str):
        """Add an elimination event."""
        self.add_event(f"💀 {agent_name} HAS BEEN ELIMINATED!", "bold red")
    
    def add_victory_event(self, agent_name: str):
        """Add a victory event."""
        self.add_event(f"👑 {agent_name} CLAIMS VICTORY!", "bold yellow")


def run_gui_with_orchestrator(orchestrator):
    """Run the GUI with the game orchestrator."""
    app = ArenaGUI(orchestrator=orchestrator)
    app.run()
