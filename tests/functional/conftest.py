from pathlib import Path
from typing import Any, Iterator, cast
import os

import pytest
from typer.testing import CliRunner
import vcr
from vcr.record_mode import RecordMode

from agent_of_chaos.config import Config
from agent_of_chaos.config_provider import ConfigProvider


CASSETTE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "vcr"
SENSITIVE_HEADERS = (
    "authorization",
    "openai-api-key",
    "openai-organization",
    "x-api-key",
)


def _resolve_record_mode() -> RecordMode:
    """
    Returns the vcrpy record mode for functional tests.

    Returns:
        The resolved VCR record mode.
    """
    value = os.environ.get("CHAOS_VCR_RECORD", "").lower()
    if value in {"all", "once", "new_episodes", "none"}:
        return RecordMode(value)
    if value in {"1", "true", "yes"}:
        return RecordMode.ALL
    return RecordMode.NONE


def _build_vcr() -> vcr.VCR:
    """
    Builds the configured VCR instance for functional tests.

    Returns:
        A configured VCR instance.
    """
    CASSETTE_DIR.mkdir(parents=True, exist_ok=True)
    return vcr.VCR(
        cassette_library_dir=str(CASSETTE_DIR),
        record_mode=_resolve_record_mode(),
        match_on=["method", "scheme", "host", "port", "path", "query"],
        filter_headers=list(SENSITIVE_HEADERS),
        filter_query_parameters=["api_key"],
        filter_post_data_parameters=["api_key"],
    )


@pytest.fixture
def cli_runner():
    """
    Provides a Typer CLI runner for functional tests.
    """
    return CliRunner()


@pytest.fixture
def vcr_cassette(request) -> Iterator[None]:
    """
    Wraps a functional test in a named VCR cassette.

    Args:
        request: The pytest request object for naming the cassette.

    Yields:
        None.
    """
    vcr_instance = _build_vcr()
    cassette_name = f"{request.node.name}.yaml"
    cassette_context = vcr_instance.use_cassette(cassette_name)
    with cast(Any, cassette_context):
        yield


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    """
    Creates an isolated workspace for functional tests.
    """
    config = Config(
        openai_api_key=os.environ.get("OPENAI_API_KEY", "test-key"),
        model_name="gpt-4o",
        chaos_dir=tmp_path / ".chaos",
        tool_root=tmp_path,
    )
    monkeypatch.setattr(ConfigProvider, "load", lambda self: config)

    # Change CWD to tmp_path
    monkeypatch.chdir(tmp_path)

    return tmp_path
