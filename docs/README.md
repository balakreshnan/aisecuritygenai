# Documentation Index — AI Security GenAI Testing Framework

This folder contains detailed technical and business documentation for the AI Security GenAI testing framework. All documentation is based on the source files in the repository root.

---

## Documents

| Document | Description |
|---|---|
| [technical-architecture.md](technical-architecture.md) | Detailed technical architecture with Mermaid diagrams covering `test_azure_openai_responses.py` and `processoutput.py` — data flow, component interactions, logging design, and data structures |
| [why-microsoft-foundry.md](why-microsoft-foundry.md) | Why this framework is best suited for Microsoft Azure AI Foundry security testing, including competitive analysis vs. Promptfoo, garak, Azure AI Foundry UI, and manual red-teaming |
| [dataset-selection-guide.md](dataset-selection-guide.md) | Which PyRIT datasets to use for each testing category (content safety, jailbreak, over-refusal, geopolitical bias, cybersecurity, medical/CBRN, multilingual, dark patterns) with tiered configurations |
| [business-case.md](business-case.md) | Business case value documentation, ROI analysis, 6 use cases, full dataset runbook with tasks for every dataset, results documentation template, and stakeholder value summary |

---

## Source Files Documented

| File | Role |
|---|---|
| `test_azure_openai_responses.py` | Test harness — loads PyRIT datasets, calls Azure OpenAI Responses API, logs all request/response data |
| `processoutput.py` | Log post-processor — parses the combined log file and emits a Markdown summary with per-row verdicts (pass / needinfo / fail) |
| `requirements.txt` | Python dependencies: `python-dotenv`, `httpx`, `pyrit`, `azure-identity` |
| `ai-safety-datasets-report.md` | Reference guide cataloguing ~35 red-team datasets with sources and use cases |
| `test_azure_openai_responses_summary.md` | Example output from `processoutput.py` — a real run summary |

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
export MS_OPENAI_GUARDRAILS_ENDPOINT="https://YOUR-RESOURCE.openai.azure.com"
export MS_OPENAI_GUARDRAILS_DEPLOYMENT="gpt-4.1-mini"

# 3. Authenticate
az login

# 4. Run smoke test
python test_azure_openai_responses.py   # generates logs/

# 5. Generate report
python processoutput.py --stdout         # generates summary .md
```

See [business-case.md](business-case.md) for the full dataset runbook.
