from __future__ import annotations

import argparse
import json

try:
    from services.agents.config import load_settings
    from services.agents.coordinator.agent import CareCoordinatorPipeline
    from services.agents.tooling import ToolProvider
except ImportError:
    from config import load_settings
    from coordinator.agent import CareCoordinatorPipeline
    from tooling import ToolProvider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the NüMe coordinator pipeline.")
    parser.add_argument("--user-id", required=True, help="User identifier for the run.")
    parser.add_argument(
        "--scenario",
        default="stressed_student",
        choices=["stressed_student", "exhausted_caregiver", "older_adult"],
        help="Seeded scenario to execute in stub mode.",
    )
    parser.add_argument(
        "--use-real-tools",
        action="store_true",
        help="Attempt to load Person 3's tool layer instead of local development stubs.",
    )
    parser.add_argument("--run-id", type=int, default=1, help="Run id for trace logging.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = load_settings()
    tool_provider = ToolProvider(use_stubs=not args.use_real_tools)
    pipeline = CareCoordinatorPipeline(settings=settings, tool_provider=tool_provider)
    result = pipeline.run(user_id=args.user_id, scenario=args.scenario, run_id=args.run_id)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
