import typer
from rich.console import Console
from pathlib import Path
from agent_of_chaos.config import Config, DEFAULT_CHAOS_DIR
from agent_of_chaos.config_provider import ConfigProvider
from agent_of_chaos.core.agent import Agent

app = typer.Typer()
console = Console()
IDENTITY_PATH_HELP = (
    "Agent id (stored as "
    f"{DEFAULT_CHAOS_DIR.as_posix()}/identities/<agent>.identity.json)."
)


def _identity_path(agent_id: str, config: Config) -> Path:
    """Returns the path to an agent identity file."""

    return config.get_identity_path(agent_id)


@app.command()
def init(
    agent: str = typer.Option(
        "default",
        "--agent",
        "-a",
        help=IDENTITY_PATH_HELP,
    ),
):
    """
    Initialize a new agent Identity in the current directory.
    """
    config = ConfigProvider().load()
    identity_path = _identity_path(agent, config)

    identity_path.parent.mkdir(parents=True, exist_ok=True)

    if identity_path.exists():
        console.print("[yellow]Identity already exists.[/yellow]")
        return
    agent_obj = Agent(identity_path, config=config)  # Creates default identity
    try:
        console.print(
            f"[green]Initialized new Chaos Agent identity at {identity_path}.[/green]"
        )
    finally:
        agent_obj.close()


@app.command()
def do(
    task: str,
    agent: str = typer.Option(
        "default",
        "--agent",
        "-a",
        help=IDENTITY_PATH_HELP,
    ),
):
    """
    Assign a task to the agent's Actor.
    """
    agent_obj = None
    try:
        config = ConfigProvider().load()
        identity_path = _identity_path(agent, config)
        agent_obj = Agent(identity_path, config=config)
        console.print(f"[bold green]Actor:[/bold green] working on '{task}'...")
        response = agent_obj.do(task)
        console.print(f"[green]{response}[/green]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
    finally:
        if agent_obj:
            agent_obj.close()


@app.command()
def learn(
    feedback: str,
    agent: str = typer.Option(
        "default",
        "--agent",
        "-a",
        help=IDENTITY_PATH_HELP,
    ),
):
    """
    Trigger the Subconscious to learn from recent logs and feedback.
    """
    agent_obj = None
    try:
        config = ConfigProvider().load()
        identity_path = _identity_path(agent, config)
        agent_obj = Agent(identity_path, config=config)
        console.print(
            f"[bold blue]Subconscious:[/bold blue] reflecting on '{feedback}'..."
        )
        note = agent_obj.learn(feedback)
        console.print(f"[blue]Learned:[/blue] {note}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
    finally:
        if agent_obj:
            agent_obj.close()


@app.command()
def dream(
    agent: str = typer.Option(
        "default",
        "--agent",
        "-a",
        help=IDENTITY_PATH_HELP,
    ),
):
    """
    Trigger the dreaming maintenance cycle.
    """
    agent_obj = None
    try:
        config = ConfigProvider().load()
        identity_path = _identity_path(agent, config)
        agent_obj = Agent(identity_path, config=config)
        console.print("[bold blue]Subconscious:[/bold blue] dreaming...")
        result = agent_obj.dream()
        console.print(f"[blue]{result}[/blue]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
    finally:
        if agent_obj:
            agent_obj.close()


if __name__ == "__main__":
    app()
