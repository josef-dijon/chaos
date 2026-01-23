import typer
from rich.console import Console
from pathlib import Path
from agent_of_chaos.core.agent import Agent

app = typer.Typer()
console = Console()
IDENTITY_PATH = Path("identity.json")


@app.command()
def init():
    """
    Initialize a new agent Identity in the current directory.
    """
    if IDENTITY_PATH.exists():
        console.print("[yellow]Identity already exists.[/yellow]")
        return
    Agent(IDENTITY_PATH)  # Creates default identity via __init__ logic
    console.print(
        f"[green]Initialized new Chaos Agent identity at {IDENTITY_PATH}.[/green]"
    )


@app.command()
def do(task: str):
    """
    Assign a task to the agent's Actor.
    """
    try:
        agent = Agent(IDENTITY_PATH)
        console.print(f"[bold green]Actor:[/bold green] working on '{task}'...")
        response = agent.do(task)
        console.print(f"[green]{response}[/green]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def learn(feedback: str):
    """
    Trigger the Subconscious to learn from recent logs and feedback.
    """
    try:
        agent = Agent(IDENTITY_PATH)
        console.print(
            f"[bold blue]Subconscious:[/bold blue] reflecting on '{feedback}'..."
        )
        note = agent.learn(feedback)
        console.print(f"[blue]Learned:[/blue] {note}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@app.command()
def dream():
    """
    Trigger the dreaming maintenance cycle.
    """
    try:
        agent = Agent(IDENTITY_PATH)
        console.print("[bold blue]Subconscious:[/bold blue] dreaming...")
        result = agent.dream()
        console.print(f"[blue]{result}[/blue]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


if __name__ == "__main__":
    app()
