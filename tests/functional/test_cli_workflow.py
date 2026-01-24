from agent_of_chaos.cli.main import app
from pathlib import Path


def test_init_and_do_workflow(cli_runner, workspace):
    # 1. Init
    result = cli_runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "Initialized new Chaos Agent identity" in result.output
    assert Path("identity.json").exists()

    # 2. Do (Write file)
    # Using a simple task to verify tool execution
    task = "Write 'Functional Test' to a file named func_test.txt"
    result = cli_runner.invoke(app, ["do", task])
    assert result.exit_code == 0
    assert "Actor:" in result.output

    # Verify file was created
    output_file = Path("func_test.txt")
    assert output_file.exists()
    assert "Functional Test" in output_file.read_text()
