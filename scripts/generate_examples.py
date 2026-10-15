"""Rebuild committed demo artifacts using isolated memory and no network calls."""

import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.orchestrator import OrchestratorAgent
from src.config import BASE_DIR, SAMPLE_CLIENTS_DIR
from src.memory.long_term import LongTermMemoryStore
from src.models.advisory import HITLDecision
from src.observability.logger import AgentLogger


def generate():
    destination = BASE_DIR / "examples"
    destination.mkdir(exist_ok=True)
    shutil.copyfile(SAMPLE_CLIENTS_DIR / "client_101_alex_chen.json", destination / "sample_input.json")
    scenarios = [
        ("client_101", "101", {}),
        ("client_102", "102", {}),
        ("client_103", "103", {}),
        ("crm_degraded", "101", {"simulate_crm_error": True}),
        (
            "rejected",
            "101",
            {
                "hitl_callback": lambda *_: HITLDecision(
                    status="REJECTED",
                    reviewer_name="Demo reviewer",
                    override_reason="Verify the flagged transfer before distribution.",
                )
            },
        ),
        (
            "modified",
            "101",
            {
                "hitl_callback": lambda *_: HITLDecision(
                    status="MODIFIED",
                    reviewer_name="Demo reviewer",
                    modified_actions=[],
                    override_reason="No proposals retained pending further client discussion.",
                )
            },
        ),
        (
            "pending",
            "101",
            {
                "hitl_callback": lambda *_: HITLDecision(
                    status="PENDING_APPROVAL", override_reason="Awaiting advisor review."
                )
            },
        ),
    ]
    with tempfile.TemporaryDirectory(prefix="wealth-examples-") as temporary:
        root = Path(temporary)
        for name, client, options in scenarios:
            runner = OrchestratorAgent(
                output_dir=root / "output",
                memory_store=LongTermMemoryStore(root / name),
                logger=AgentLogger(root / "events.jsonl", verbose=False),
                auto_approve_hitl=True,
            )
            result = runner.execute_workflow(client_id=client, **options)
            if result["status"] == "FAILED":
                raise RuntimeError(result["error"])
            target = destination / name
            target.mkdir(exist_ok=True)
            shutil.copyfile(result["output_json"], target / "advisory_dossier.json")
            shutil.copyfile(result["output_markdown"], target / "advisory_report.md")
            if name == "client_101":
                shutil.copyfile(result["output_json"], destination / "sample_output.json")
                shutil.copyfile(result["output_markdown"], destination / "sample_advisor_report.md")
            print(f"{name}: {result['status']}; {result['actions_count']} retained proposals")
    (destination / "README.md").write_text(
        "# Generated examples\n\n"
        "Regenerate from the project root with `python scripts/generate_examples.py`. "
        "This uses the offline provider and fresh temporary memory. Session IDs and timestamps vary.\n\n"
        "| Scenario | Purpose |\n|---|---|\n"
        "| client_101 | Cash, concentration and a flagged wire |\n"
        "| client_102 | Allocation drift before retirement |\n"
        "| client_103 | Reserve deficit and concentrated holdings |\n"
        "| crm_degraded | No invented target allocation; independent checks continue |\n"
        "| rejected | Rejected proposals exported only as an audit |\n"
        "| modified | Explicit removal of every proposed action |\n"
        "| pending | No approval recorded |\n\n"
        "Each scenario includes a JSON dossier and a Markdown report. "
        "`sample_input.json`, `sample_output.json`, and `sample_advisor_report.md` form the short submission example.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    generate()
