"""CLI and human interface to ATHENA."""

import argparse
import os
from datetime import datetime
from pathlib import Path

from athena.core import ATHENA
from athena.types import Priority


class AthenaCommander:
    def __init__(self, athena: ATHENA):
        self.athena = athena

    def issue_objective(self, objective: str, deadline: str, priority: str = "NORMAL"):
        try:
            deadline_dt = datetime.fromisoformat(deadline)
        except ValueError as exc:
            raise ValueError(f"Invalid deadline format: {deadline}") from exc

        try:
            priority_enum = Priority[priority.upper()]
        except KeyError as exc:
            allowed = ", ".join([p.name for p in Priority])
            raise ValueError(
                f"Invalid priority '{priority}'. Allowed: {allowed}"
            ) from exc

        mission_id = self.athena.receive_objective(
            description=objective, deadline=deadline_dt, priority=priority_enum
        )

        return mission_id

    def status_report(self) -> str:
        return self.athena.generate_sitrep()

    def recall_division(self, olympian: str):
        self.athena.recall_olympian(olympian)


def main():
    parser = argparse.ArgumentParser(description="ATHENA command interface")
    parser.add_argument("--objective", help="Mission objective to execute")
    parser.add_argument(
        "--deadline", help="Deadline in ISO format, e.g. 2026-02-19T23:59:59"
    )
    parser.add_argument(
        "--priority", default="NORMAL", help="ROUTINE|NORMAL|HIGH|CRITICAL|EMERGENCY"
    )
    parser.add_argument(
        "--garrison-path",
        default=os.getenv(
            "ATHENA_GARRISON_PATH", str(Path.home() / "Eregion" / "athena-garrison")
        ),
        help="ATHENA garrison path",
    )
    parser.add_argument(
        "--core-mode",
        default=os.getenv("CORE_MODE", "local"),
        choices=["local", "cloud"],
        help="Core persistence mode: local sqlite or cloud API",
    )
    parser.add_argument(
        "--core-base-url", default=None, help="RedPlanet Core API base URL"
    )
    parser.add_argument(
        "--core-api-key",
        default=None,
        help="RedPlanet Core API key (or CORE_API_KEY env)",
    )
    parser.add_argument(
        "--core-score-threshold",
        type=float,
        default=float(os.getenv("ATHENA_CORE_SCORE_THRESHOLD", "0.35")),
    )
    parser.add_argument(
        "--core-template-score-threshold",
        type=float,
        default=float(os.getenv("ATHENA_CORE_TEMPLATE_SCORE_THRESHOLD", "0.50")),
    )
    parser.add_argument(
        "--core-refresh-timeout",
        type=int,
        default=int(os.getenv("ATHENA_CORE_REFRESH_TIMEOUT", "8")),
    )
    parser.add_argument(
        "--core-refresh-before-plan",
        action="store_true",
        default=os.getenv("ATHENA_CORE_REFRESH_BEFORE_PLAN", "1").strip()
        not in {"0", "false", "False"},
    )
    parser.add_argument(
        "--no-core-refresh-before-plan",
        action="store_false",
        dest="core_refresh_before_plan",
    )
    parser.add_argument(
        "--require-core",
        action="store_true",
        default=os.getenv("ATHENA_REQUIRE_CORE", "1").strip()
        not in {"0", "false", "False"},
    )
    parser.add_argument(
        "--no-require-core",
        action="store_false",
        dest="require_core",
    )
    parser.add_argument(
        "--status", action="store_true", help="Print current SITREP and exit"
    )
    parser.add_argument(
        "--no-auto-register",
        action="store_true",
    )
    args = parser.parse_args()

    try:
        athena = ATHENA(
            garrison_path=args.garrison_path,
            core_base_url=args.core_base_url,
            core_api_key=args.core_api_key,
            core_mode=args.core_mode,
            require_core=args.require_core,
            core_score_threshold=args.core_score_threshold,
            core_template_score_threshold=args.core_template_score_threshold,
            core_refresh_before_plan=args.core_refresh_before_plan,
            core_refresh_timeout_seconds=args.core_refresh_timeout,
        )
    except RuntimeError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(3) from exc
    if not args.no_auto_register:
        athena.register_default_olympians()
    commander = AthenaCommander(athena)

    if args.status:
        print(commander.status_report())
        raise SystemExit(0)

    if not args.objective:
        parser.error("--objective is required unless --status is used")

    deadline = args.deadline or datetime.now().replace(microsecond=0).isoformat()

    try:
        mission_id = commander.issue_objective(
            objective=args.objective,
            deadline=deadline,
            priority=args.priority,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(2) from exc

    print(mission_id)
    print(commander.status_report())


if __name__ == "__main__":
    main()
