from __future__ import annotations

import argparse

from edge_agent.api_client import EdgeAPIError
from edge_agent.config import EdgeAgentConfig
from edge_agent.runtime import EdgeAgent, diagnose


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Smart Classroom Real Edge AI Agent"
        )
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--diagnose",
        action="store_true",
        help="Load local AI models and report readiness.",
    )
    mode.add_argument(
        "--run",
        action="store_true",
        help="Run real camera, LBPH, YOLO and Edge API sync.",
    )

    parser.add_argument(
        "--camera-test",
        action="store_true",
        help="Include one real camera frame in diagnosis.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run without the OpenCV preview window.",
    )
    parser.add_argument(
        "--max-seconds",
        type=int,
        default=None,
        help="Stop live mode after this many seconds.",
    )

    return parser


def warn_env_overrides(config: EdgeAgentConfig) -> None:
    for name in config.env_overrides:
        # Never print the value: it may be the Device Key.
        print(
            f"WARNING: {name} is set in this terminal and differs "
            "from backend/.env.edge. The terminal value is used. "
            f"Run 'Remove-Item Env:{name}' to use .env.edge."
        )


def main() -> int:
    args = build_parser().parse_args()
    config = EdgeAgentConfig.load()
    warn_env_overrides(config)

    if args.headless:
        config = config.with_show_window(False)

    if args.run:
        try:
            agent = EdgeAgent(config)
            agent.run(max_seconds=args.max_seconds)
        except (EdgeAPIError, RuntimeError, ValueError) as exc:
            print(f"Edge Agent stopped: {exc}")
            return 1
        return 0

    return diagnose(
        config,
        camera_test=args.camera_test,
    )


if __name__ == "__main__":
    raise SystemExit(main())
