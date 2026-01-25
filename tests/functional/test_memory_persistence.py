from chaos.cli.main import app


def test_memory_persistence(cli_runner, workspace, vcr_cassette):
    # Initialize
    cli_runner.invoke(app, ["init"])

    # 1. Tell the agent something non-sensitive
    cli_runner.invoke(
        app, ["do", "My favorite book is 'The Hitchhiker's Guide to the Galaxy'"]
    )

    # 2. Ask the agent about it in a new session
    result = cli_runner.invoke(app, ["do", "What is my favorite book?"])

    assert result.exit_code == 0
    assert "HITCHHIKER" in result.output.upper()
