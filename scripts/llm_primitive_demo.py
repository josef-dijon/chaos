import argparse

from pydantic import BaseModel

from chaos.config import Config
from chaos.domain.llm_primitive import LLMPrimitive
from chaos.domain.messages import Request


class DemoResponse(BaseModel):
    """Schema for the demo LLM response."""

    response: str


def _build_system_prompt() -> str:
    """Return the system prompt used for the demo."""

    return (
        "You are a JSON generator. "
        'Return ONLY valid JSON that matches: {"response": "..."}.'
    )


def run_demo(prompt: str) -> int:
    """Execute the LLM primitive demo with the given prompt.

    Args:
        prompt: Prompt text sent to the LLM.

    Returns:
        Process exit code (0 for success).
    """

    config = Config.load()
    api_key = config.get_openai_api_key()
    if not api_key:
        print("Missing OpenAI API key. Set OPENAI_API_KEY or .chaos/config.json")
        return 1

    block = LLMPrimitive(
        name="llm_demo",
        system_prompt=_build_system_prompt(),
        output_data_model=DemoResponse,
        config=config,
    )

    response = block.execute(Request(payload={"prompt": prompt}))

    if response.success() is True:
        print("Success:")
        print(response.data)
        return 0
    if response.success() is False:
        print("Failure:")
        print({"reason": response.reason, "details": response.details})
        return 2

    print("Unexpected response type.")
    return 3


def main() -> None:
    """Entry point for the LLM primitive demo script."""

    parser = argparse.ArgumentParser(description="Run LLMPrimitive demo")
    parser.add_argument(
        "--prompt",
        default="Say hello in JSON.",
        help="User prompt to send to the LLM.",
    )
    args = parser.parse_args()
    raise SystemExit(run_demo(args.prompt))


if __name__ == "__main__":
    main()
