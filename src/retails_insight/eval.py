from __future__ import annotations

import argparse
import os
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from retails_insight.judge import DEFAULT_GOLDEN_SET_PATH, DEFAULT_REPORT_PATH, PASS_THRESHOLD, evaluate_golden_set
from retails_insight.llm import LLMClient, LLMUnavailableError

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main(argv: list[str] | None = None) -> int:
    load_dotenv(PROJECT_ROOT / ".env", override=False)

    parser = argparse.ArgumentParser(description="Run the Retails Insight golden-set evaluation.")
    parser.add_argument("--golden-set", default=str(DEFAULT_GOLDEN_SET_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument(
        "--require-llm",
        action="store_true",
        help="Exit non-zero if the LLM client could not be built.",
    )
    args = parser.parse_args(argv)

    narrative_client = _build_narrative_client()
    judge_client = _build_judge_client()

    if args.require_llm and narrative_client is None:
        print("ERROR: --require-llm was set but no LLM client could be built (check OPENAI_API_KEY).")
        return 2

    report = evaluate_golden_set(
        args.golden_set,
        narrative_client=narrative_client,
        judge_client=judge_client,
        report_path=args.report_path,
    )

    sources = Counter(result.narrative_source for result in report.scenario_results)
    source_summary = ", ".join(f"{name}={count}" for name, count in sorted(sources.items()))
    print(f"Deterministic pass rate: {report.deterministic_pass_rate:.1%}")
    print(f"Narrative sources: {source_summary or 'none'}")
    print(f"Report written to: {report.report_path}")
    return 0 if report.deterministic_pass_rate >= PASS_THRESHOLD else 1


def _build_narrative_client() -> object | None:
    try:
        return LLMClient()
    except LLMUnavailableError:
        return None


def _build_judge_client() -> object | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    judge_model = os.getenv("JUDGE_MODEL")
    if not judge_model:
        return None

    openai_model = os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
    if judge_model == openai_model:
        return None

    try:
        return LLMClient(api_key=api_key, model=judge_model)
    except LLMUnavailableError:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
