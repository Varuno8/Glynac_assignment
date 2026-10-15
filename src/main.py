"""CLI and batch entrypoint. A terminal failure returns a nonzero exit code."""

import argparse
import sys
from pathlib import Path

# Preserve the assignment's original `python src/main.py` invocation.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from rich.table import Table

from src.agents.orchestrator import OrchestratorAgent
from src.config import BASE_DIR, OUTPUT_DIR, SAMPLE_CLIENTS_DIR, STORAGE_DIR
from src.llm import get_llm_client
from src.memory.long_term import LongTermMemoryStore
from src.observability.logger import AgentLogger, console


def build_parser():
    parser = argparse.ArgumentParser(description="Wealth Advisor Assistant — simulated assignment demo")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--client", "-c", help="Sample client ID (default: 101)")
    source.add_argument("--input", type=Path, help="Client financial JSON file")
    source.add_argument("--batch", "-b", action="store_true", help="Analyze all sample files")
    parser.add_argument(
        "--auto-approve", action="store_true", help="Explicitly bypass human approval for demo automation"
    )
    parser.add_argument("--simulate-crm-error", action="store_true")
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress stage logs; retain results and review prompts"
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--storage-dir", type=Path, default=STORAGE_DIR)
    parser.add_argument("--llm-provider", choices=["mock", "openai"], default="mock")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    load_dotenv(BASE_DIR / ".env", override=False)
    try:
        runner = OrchestratorAgent(
            logger=AgentLogger(args.output_dir / "agent_execution.jsonl", verbose=not args.quiet),
            output_dir=args.output_dir,
            memory_store=LongTermMemoryStore(args.storage_dir),
            llm=get_llm_client(args.llm_provider),
            auto_approve_hitl=args.auto_approve,
        )
    except (ValueError, OSError) as exc:
        console.print(f"Configuration error: {exc}", markup=False)
        return 1
    if args.batch:
        files = sorted(SAMPLE_CLIENTS_DIR.glob("client_*.json"))
        if not files:
            console.print("No sample financial files found.")
            return 1
        requests = [{"file_path": str(path)} for path in files]
    elif args.input:
        requests = [{"file_path": str(args.input)}]
    else:
        requests = [{"client_id": args.client or "101"}]
    results = [
        runner.execute_workflow(**request, simulate_crm_error=args.simulate_crm_error) for request in requests
    ]
    table = Table(title="Wealth advisory assessment results")
    for column in ("Client", "Outcome", "Review", "Signals", "Actions"):
        table.add_column(column)
    for result in results:
        table.add_row(
            result.get("client_id") or "unresolved",
            result["status"],
            result.get("hitl_status") or "N/A",
            str(result["anomalies_detected"]),
            str(result["actions_count"]),
        )
    console.print(table)
    for result in results:
        if result["status"] == "FAILED":
            console.print(f"Failed at {result['stage']}: {result['error']}", markup=False)
        elif result["output_markdown"]:
            console.print(f"{result['status']}: {result['output_markdown']}", markup=False)
    if any(r["status"] == "FAILED" for r in results):
        return 1
    if any(r["status"] in {"PENDING_REVIEW", "REJECTED"} for r in results):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
