# Generated examples

Regenerate from the project root with `python scripts/generate_examples.py`. This uses the offline provider and fresh temporary memory. Session IDs and timestamps vary.

| Scenario | Purpose |
|---|---|
| client_101 | Cash, concentration and a flagged wire |
| client_102 | Allocation drift before retirement |
| client_103 | Reserve deficit and concentrated holdings |
| crm_degraded | No invented target allocation; independent checks continue |
| rejected | Rejected proposals exported only as an audit |
| modified | Explicit removal of every proposed action |
| pending | No approval recorded |

Each scenario includes a JSON dossier and a Markdown report. `sample_input.json`, `sample_output.json`, and `sample_advisor_report.md` form the short submission example.
