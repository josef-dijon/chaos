import typer
from rich.console import Console
from pathlib import Path
from agent_of_chaos.core.agent import Agent

app = typer.Typer()
console = Console()

CHAOS_DIR = Path(".chaos")
IDENTITIES_DIR = CHAOS_DIR / "identities"


def _identity_path(agent_id: str) -> Path:
    """Returns the path to an agent identity file."""

    return IDENTITIES_DIR / f"{agent_id}.identity.json"


@app.command()
def init(
    agent: str = typer.Option(
        "default",
        "--agent",
        "-a",
        help="Agent id (stored as .chaos/identities/<agent>.identity.json).",
    ),
):
    """
    Initialize a new agent Identity in the current directory.
    """
    IDENTITY_PATH = _identity_path(agent)

    IDENTITIES_DIR.mkdir(parents=True, exist_ok=True)

    if IDENTITY_PATH.exists():
        console.print("[yellow]Identity already exists.[/yellow]")
        return
    Agent(IDENTITY_PATH)  # Creates default identity via __init__ logic
    console.print(
        f"[green]Initialized new Chaos Agent identity at {IDENTITY_PATH}.[/green]"
    )


@app.command()
def do(
    task: str,
    agent: str = typer.Option(
        "default",
        "--agent",
        "-a",
        help="Agent id (stored as .chaos/identities/<agent>.identity.json).",
    ),
):
    """
    Assign a task to the agent's Actor.
    """
    try:
        identity_path = _identity_path(agent)
        agent_obj = Agent(identity_path)
        console.print(f"[bold green]Actor:[/bold green] working on '{task}'...")
        response = agent_obj.do(task)
        console.print(f"[green]{response}[/green]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def learn(
    feedback: str,
    agent: str = typer.Option(
        "default",
        "--agent",
        "-a",
        help="Agent id (stored as .chaos/identities/<agent>.identity.json).",
    ),
):
    """
    Trigger the Subconscious to learn from recent logs and feedback.
    """
    try:
        identity_path = _identity_path(agent)
        agent_obj = Agent(identity_path)
        console.print(
            f"[bold blue]Subconscious:[/bold blue] reflecting on '{feedback}'..."
        )
        note = agent_obj.learn(feedback)
        console.print(f"[blue]Learned:[/blue] {note}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def dream(
    agent: str = typer.Option(
        "default",
        "--agent",
        "-a",
        help="Agent id (stored as .chaos/identities/<agent>.identity.json).",
    ),
):
    """
    Trigger the dreaming maintenance cycle.
    """
    try:
        identity_path = _identity_path(agent)
        agent_obj = Agent(identity_path)
        console.print("[bold blue]Subconscious:[/bold blue] dreaming...")
        result = agent_obj.dream()
        console.print(f"[blue]{result}[/blue]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


if __name__ == "__main__":
    app()
