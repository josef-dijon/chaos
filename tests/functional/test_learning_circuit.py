from chaos.cli.main import app
import json
from pathlib import Path


def test_learning_circuit(cli_runner, workspace, vcr_cassette):
    # Initialize
    cli_runner.invoke(app, ["init"])

    # 1. Provide feedback for the subconscious to learn
    # We first do a task so there are logs to analyze
    cli_runner.invoke(app, ["do", "Say hello"])

    result = cli_runner.invoke(app, ["learn", "Always respond like a pirate"])
    assert result.exit_code == 0
    assert "Learned:" in result.output

    # 2. Verify identity.json was updated
    identity_data = json.loads(
        (Path(".chaos") / "identities" / "default.identity.json").read_text()
    )
    notes = identity_data["instructions"]["operational_notes"]
    assert len(notes) > 0

    # 3. Verify the Actor now behaves like a pirate
    result = cli_runner.invoke(app, ["do", "Say hello again"])
    assert result.exit_code == 0

    # Common pirate indicators
    pirate_indicators = [
        "AHOY",
        "MATEY",
        "ARR",
        "YAR",
        "SCURVY",
        "SEA",
        "PIRATE",
        "YE ",
        "THAR",
    ]
    output_upper = result.output.upper()
    assert any(word in output_upper for word in pirate_indicators)
