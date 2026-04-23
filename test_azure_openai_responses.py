"""
Send a PyRit dataset (same dataset used in test_ms_content_safety_prompt_shields.py)
to an Azure OpenAI deployment via the Responses API, log each request to its own
file in logs/, and print/export a results table summarizing input + parsed output
(model output, content-safety filter result, or error).
"""

import asyncio
import csv
import json
import logging
import os
import re
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from pyrit.setup import IN_MEMORY, initialize_pyrit_async
from pyrit.datasets import SeedDatasetProvider
from pyrit.memory.central_memory import CentralMemory


load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# ACTIVE_DATASETS = [
#     "ccp_sensitive_prompts",
# ]
# Define active datasets (small selection for testing)
ACTIVE_DATASETS = [
    #"airt_fairness", 
    #"psfuzz_steal_system_prompt",
    #"jbb_behaviors",
    #"tdc23_redteaming",
    #"pyrit_example_dataset",
    #"harmbench_multimodal",
    #"mlcommons_ailuminate",
    "ccp_sensitive_prompts",
    #"garak_web_html_js",
    #"airt_hate",
    #"airt_fairness_yes_no",
    #"airt_harassment",
    #"airt_misinformation",
    #"airt_sexual",
    #"airt_violence",
    #"airt_leakage", 
    #"sosbench",
    #"forbidden_questions",
    #"airt_malware",
    #"harmbench",
    #"xstest",
    #"llm_lat_harmful",
    #"airt_illegal",
    #"adv_bench",
    #"garak_slur_terms_en",
    #"garak_access_shell_commands",        
    #"dark_bench",
    #"multilingual_vulnerability",        
    #"librai_do_not_answer",
    #"aya_redteaming",
    
    # payload list too large to test.        
    #=========================================================
    #"red_team_social_bias",
    #"mental_health_crisis_multiturn_example",
    #"medsafetybench",
    #"equitymedqa",
    #"aegis_content_safety",
    #"pku_safe_rlhf",
    #"sorry_bench",
    #"babelscape_alert",        
]

# Optional cap on number of prompts to send. Set to None for all rows.
MAX_PROMPTS: Optional[int] = None

AOAI_ENDPOINT = (os.getenv("MS_OPENAI_GUARDRAILS_ENDPOINT")
                 or os.getenv("AZURE_OPENAI_ENDPOINT", "")).rstrip("/")
# strip any /openai/v1 suffix that may be in the env value
if "/openai" in AOAI_ENDPOINT:
    AOAI_ENDPOINT = AOAI_ENDPOINT[:AOAI_ENDPOINT.index("/openai")]

AOAI_DEPLOYMENT = (os.getenv("MS_OPENAI_GUARDRAILS_DEPLOYMENT")
                   or os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini"))

AOAI_API_VERSION = os.getenv("AZURE_OPENAI_RESPONSES_API_VERSION",
                             "2025-03-01-preview")

REQUEST_TIMEOUT = 60.0
SYSTEM_PROMPT = os.getenv("MS_OPENAI_GUARDRAILS_SYSTEM_PROMPT",
                          "You are a helpful assistant.")

LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
RUN_DIR = LOGS_DIR  # results artifacts go directly under logs/

# ---------------------------------------------------------------------------
# Logging setup -- ONE combined log file under logs/ captures everything
# (root logger DEBUG -> file, INFO -> console; stdout/stderr also tee'd in).
# ---------------------------------------------------------------------------

RUN_LOG_PATH = LOGS_DIR / "test_azure_openai_responses.log"

_combined_file_handler = logging.FileHandler(RUN_LOG_PATH, mode="w", encoding="utf-8")
_combined_file_handler.setLevel(logging.DEBUG)
_combined_file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
)

_console_handler = logging.StreamHandler(stream=sys.stdout)
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

_root = logging.getLogger()
_root.setLevel(logging.DEBUG)
# remove any handlers added by libraries before us
for _h in list(_root.handlers):
    _root.removeHandler(_h)
_root.addHandler(_combined_file_handler)
_root.addHandler(_console_handler)

# Silence noisy third-party loggers (Azure SDK + urllib3 emit large DEBUG
# tracebacks when DefaultAzureCredential probes each credential in turn).
for _noisy in (
    "azure",
    "azure.identity",
    "azure.core",
    "azure.core.pipeline.policies.http_logging_policy",
    "msal",
    "msrest",
    "urllib3",
    "httpx",
    "httpcore",
    "asyncio",
):
    logging.getLogger(_noisy).setLevel(logging.WARNING)
    logging.getLogger(_noisy).propagate = True

log = logging.getLogger("aoai_responses")


class _StreamToLogger:
    """File-like wrapper that forwards writes to a logger (so print() lands in the log)."""

    def __init__(self, logger: logging.Logger, level: int, mirror) -> None:
        self._logger = logger
        self._level = level
        self._mirror = mirror
        self._buffer = ""

    def write(self, msg: str) -> int:
        if not msg:
            return 0
        try:
            self._mirror.write(msg)
            self._mirror.flush()
        except Exception:
            pass
        self._buffer += msg
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip():
                self._logger.log(self._level, line)
        return len(msg)

    def flush(self) -> None:
        if self._buffer.strip():
            self._logger.log(self._level, self._buffer)
        self._buffer = ""
        try:
            self._mirror.flush()
        except Exception:
            pass

    def isatty(self) -> bool:  # some libs probe this
        try:
            return self._mirror.isatty()
        except Exception:
            return False


_stdout_logger = logging.getLogger("stdout")
_stderr_logger = logging.getLogger("stderr")
sys.stdout = _StreamToLogger(_stdout_logger, logging.INFO, sys.__stdout__)
sys.stderr = _StreamToLogger(_stderr_logger, logging.ERROR, sys.__stderr__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_filename(text: str, idx: int) -> str:
    snippet = re.sub(r"[^A-Za-z0-9]+", "_", text)[:40].strip("_") or "prompt"
    return f"row_{idx:04d}_{snippet}.log"


def _make_row_logger(idx: int) -> logging.Logger:
    """Per-row logger. Propagates to the single combined log file (no per-row file)."""
    logger = logging.getLogger(f"row.{idx:04d}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = True
    for h in list(logger.handlers):
        logger.removeHandler(h)
    return logger


def _truncate(text: str, n: int = 120) -> str:
    text = (text or "").replace("\n", " ").replace("\r", " ").strip()
    return text if len(text) <= n else text[: n - 1] + "\u2026"


def _filtered_categories(filter_results: Dict[str, Any], prefix: str) -> List[str]:
    out: List[str] = []
    if not isinstance(filter_results, dict):
        return out
    for category, result in filter_results.items():
        if isinstance(result, dict) and result.get("filtered"):
            sev = result.get("severity") or result.get("detected") or True
            out.append(f"{prefix}:{category}={sev}")
    return out


def _parse_response(status: int, body: Any) -> Dict[str, Any]:
    """Normalize either a successful Responses API payload or an error body."""
    parsed: Dict[str, Any] = {
        "http_status": status,
        "model_output": "",
        "finish_reason": "",
        "content_filter_triggered": False,
        "filter_categories": [],
        "error_code": "",
        "error_message": "",
    }

    if not isinstance(body, dict):
        parsed["error_message"] = str(body)
        return parsed

    # --- Error path (e.g. 400 content_filter) ---
    if "error" in body and status >= 400:
        err = body.get("error") or {}
        parsed["error_code"] = str(err.get("code", "") or status)
        parsed["error_message"] = err.get("message", "")
        inner = err.get("innererror") or {}
        cf = inner.get("content_filter_result") or inner.get("content_filter_results") or {}
        cats = _filtered_categories(cf, "prompt")
        if cats or inner.get("code") == "ResponsibleAIPolicyViolation":
            parsed["content_filter_triggered"] = True
        parsed["filter_categories"] = cats
        return parsed

    # --- Success path: Azure OpenAI Responses API ---
    # Convenience: "output_text" sometimes present (SDK style); fall back to walking output.
    if isinstance(body.get("output_text"), str):
        parsed["model_output"] = body["output_text"]

    output = body.get("output") or []
    if isinstance(output, list):
        chunks: List[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "message":
                for c in item.get("content", []) or []:
                    if isinstance(c, dict):
                        # text fields may be {"type":"output_text","text":"..."}
                        text = c.get("text")
                        if isinstance(text, str):
                            chunks.append(text)
                        elif isinstance(text, dict) and isinstance(text.get("value"), str):
                            chunks.append(text["value"])
            if item.get("status"):
                parsed["finish_reason"] = item.get("status") or parsed["finish_reason"]
        if chunks and not parsed["model_output"]:
            parsed["model_output"] = "".join(chunks)

    parsed["finish_reason"] = (
        body.get("status") or parsed["finish_reason"] or ""
    )

    # Azure content filter results may also appear on success
    cf_results = body.get("content_filter_results") or {}
    cats = _filtered_categories(cf_results, "response")
    prompt_filter = body.get("prompt_filter_results") or []
    for pf in prompt_filter:
        cats.extend(_filtered_categories(
            (pf or {}).get("content_filter_results", {}), "prompt"))
    if cats:
        parsed["content_filter_triggered"] = True
        parsed["filter_categories"] = cats

    return parsed


# ---------------------------------------------------------------------------
# Azure OpenAI Responses API call
# ---------------------------------------------------------------------------

async def call_responses_api(
    client: httpx.AsyncClient,
    credential: DefaultAzureCredential,
    prompt: str,
    row_log: logging.Logger,
) -> Dict[str, Any]:
    url = f"{AOAI_ENDPOINT}/openai/responses?api-version={AOAI_API_VERSION}"
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token.token}",
    }
    payload = {
        "model": AOAI_DEPLOYMENT,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    }

    row_log.debug("URL: %s", url)
    row_log.debug("Deployment: %s | api-version: %s", AOAI_DEPLOYMENT, AOAI_API_VERSION)
    row_log.debug("Payload: %s", json.dumps(payload, ensure_ascii=False))

    started = time.time()
    try:
        resp = await client.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
        elapsed_ms = int((time.time() - started) * 1000)
        try:
            body = resp.json()
        except Exception:
            body = {"raw_text": resp.text}

        row_log.info("HTTP status: %s (%d ms)", resp.status_code, elapsed_ms)
        row_log.debug("Response headers: %s", dict(resp.headers))
        row_log.info("Raw response body:\n%s",
                     json.dumps(body, ensure_ascii=False, indent=2))

        parsed = _parse_response(resp.status_code, body)
        parsed["elapsed_ms"] = elapsed_ms
        parsed["raw_body"] = body
        return parsed

    except httpx.TimeoutException as e:
        row_log.error("Timeout after %ss: %s", REQUEST_TIMEOUT, e)
        return {
            "http_status": 0, "error_code": "timeout", "error_message": str(e),
            "model_output": "", "finish_reason": "", "filter_categories": [],
            "content_filter_triggered": False,
            "elapsed_ms": int((time.time() - started) * 1000),
            "raw_body": None,
        }
    except Exception as e:
        row_log.error("Exception: %s\n%s", e, traceback.format_exc())
        return {
            "http_status": 0, "error_code": type(e).__name__, "error_message": str(e),
            "model_output": "", "finish_reason": "", "filter_categories": [],
            "content_filter_triggered": False,
            "elapsed_ms": int((time.time() - started) * 1000),
            "raw_body": None,
        }


# ---------------------------------------------------------------------------
# Dataset loading (mirrors the prompt-shield test)
# ---------------------------------------------------------------------------

async def load_prompts() -> List[str]:
    log.info("Initializing PyRit (in-memory)...")
    await initialize_pyrit_async(memory_db_type=IN_MEMORY)

    log.info("Loading datasets: %s", ACTIVE_DATASETS)
    datasets = await SeedDatasetProvider.fetch_datasets_async(dataset_names=ACTIVE_DATASETS)

    memory = CentralMemory().get_memory_instance()
    await memory.add_seed_datasets_to_memory_async(
        datasets=datasets, added_by="aoai_responses_test"
    )

    prompts: List[str] = []
    for ds_name in ACTIVE_DATASETS:
        groups = memory.get_seed_groups(dataset_name=ds_name)
        for group in groups:
            for seed in group.seeds:
                if seed.value and seed.value.strip():
                    prompts.append(seed.value)

    log.info("Loaded %d prompts", len(prompts))
    if MAX_PROMPTS is not None:
        prompts = prompts[:MAX_PROMPTS]
        log.info("Limiting to %d prompts (MAX_PROMPTS)", len(prompts))
    return prompts


# ---------------------------------------------------------------------------
# Table rendering
# ---------------------------------------------------------------------------

def _render_table(rows: List[Dict[str, Any]]) -> str:
    headers = ["#", "Status", "ms", "Filter", "Filter cats",
               "Error", "Input", "Model output"]
    table = [headers]
    for r in rows:
        table.append([
            str(r["idx"]),
            str(r["http_status"]),
            str(r["elapsed_ms"]),
            "YES" if r["content_filter_triggered"] else "no",
            _truncate(",".join(r["filter_categories"]), 30),
            _truncate(f'{r["error_code"]} {r["error_message"]}'.strip(), 40),
            _truncate(r["input"], 60),
            _truncate(r["model_output"], 80),
        ])

    widths = [max(len(row[c]) for row in table) for c in range(len(headers))]
    line = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    out = [line]
    for i, row in enumerate(table):
        out.append("| " + " | ".join(cell.ljust(widths[c])
                                     for c, cell in enumerate(row)) + " |")
        if i == 0:
            out.append(line)
    out.append(line)
    return "\n".join(out)


def _write_markdown(rows: List[Dict[str, Any]], path: Path) -> None:
    headers = ["#", "HTTP", "ms", "ContentFilter", "FilterCategories",
               "Error", "Input", "ModelOutput"]
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join("---" for _ in headers) + " |"]
    for r in rows:
        lines.append("| " + " | ".join([
            str(r["idx"]),
            str(r["http_status"]),
            str(r["elapsed_ms"]),
            "YES" if r["content_filter_triggered"] else "no",
            ",".join(r["filter_categories"]).replace("|", "\\|"),
            f'{r["error_code"]} {r["error_message"]}'.strip().replace("|", "\\|"),
            _truncate(r["input"], 200).replace("|", "\\|"),
            _truncate(r["model_output"], 400).replace("|", "\\|"),
        ]) + " |")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    fieldnames = ["idx", "http_status", "elapsed_ms",
                  "content_filter_triggered", "filter_categories",
                  "error_code", "error_message", "finish_reason",
                  "input", "model_output"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            row = {k: r.get(k, "") for k in fieldnames}
            row["filter_categories"] = ",".join(r.get("filter_categories", []))
            w.writerow(row)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    if not AOAI_ENDPOINT:
        log.error("Azure OpenAI endpoint is not set "
                  "(MS_OPENAI_GUARDRAILS_ENDPOINT or AZURE_OPENAI_ENDPOINT).")
        sys.exit(1)

    log.info("Run dir: %s", RUN_DIR.resolve())
    log.info("Combined run log: %s", RUN_LOG_PATH.resolve())
    log.info("Endpoint: %s", AOAI_ENDPOINT)
    log.info("Deployment: %s", AOAI_DEPLOYMENT)
    log.info("API version: %s", AOAI_API_VERSION)

    prompts = await load_prompts()
    if not prompts:
        log.warning("No prompts found in dataset(s).")
        return

    credential = DefaultAzureCredential()
    rows: List[Dict[str, Any]] = []

    async with httpx.AsyncClient() as client:
        for idx, prompt in enumerate(prompts, start=1):
            row_log = _make_row_logger(idx)

            row_log.info("=" * 80)
            row_log.info("Row %d / %d", idx, len(prompts))
            row_log.info("=" * 80)
            row_log.info("INPUT (%d chars):\n%s", len(prompt), prompt)

            log.info("=" * 80)
            log.info("[%d/%d] INPUT: %s", idx, len(prompts), _truncate(prompt, 200))
            log.debug("[%d/%d] FULL INPUT:\n%s", idx, len(prompts), prompt)

            parsed = await call_responses_api(client, credential, prompt, row_log)

            parsed_summary = {k: v for k, v in parsed.items() if k != "raw_body"}
            parsed_json = json.dumps(parsed_summary, ensure_ascii=False, indent=2)
            row_log.info("PARSED RESULT:\n%s", parsed_json)

            # Also surface parsed output in the combined run log
            log.info("[%d/%d] HTTP=%s ms=%s filter=%s cats=%s err=%s",
                     idx, len(prompts),
                     parsed.get("http_status"), parsed.get("elapsed_ms"),
                     parsed.get("content_filter_triggered"),
                     ",".join(parsed.get("filter_categories", [])) or "-",
                     (parsed.get("error_code") or "") + " " + (parsed.get("error_message") or ""))
            log.info("[%d/%d] MODEL OUTPUT: %s", idx, len(prompts),
                     _truncate(parsed.get("model_output", ""), 400))
            log.debug("[%d/%d] PARSED:\n%s", idx, len(prompts), parsed_json)
            if parsed.get("raw_body") is not None:
                log.debug("[%d/%d] RAW BODY:\n%s", idx, len(prompts),
                          json.dumps(parsed["raw_body"], ensure_ascii=False, indent=2))

            row = {
                "idx": idx,
                "input": prompt,
                **parsed,
            }
            rows.append(row)

    # ---------- Output table ----------
    table_str = _render_table(rows)
    log.info("Results table:\n%s", table_str)
    print("\n" + table_str + "\n")

    md_path = RUN_DIR / "results.md"
    csv_path = RUN_DIR / "results.csv"
    json_path = RUN_DIR / "results.json"

    _write_markdown(rows, md_path)
    _write_csv(rows, csv_path)
    json_path.write_text(
        json.dumps(
            [{k: v for k, v in r.items() if k != "raw_body"} for r in rows],
            ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Summary
    total = len(rows)
    ok = sum(1 for r in rows if 200 <= r["http_status"] < 300)
    filtered = sum(1 for r in rows if r["content_filter_triggered"])
    errors = sum(1 for r in rows if r["http_status"] == 0 or r["http_status"] >= 400)
    log.info("Summary: total=%d  ok=%d  content_filter=%d  errors=%d",
             total, ok, filtered, errors)
    log.info("Markdown table: %s", md_path.resolve())
    log.info("CSV: %s", csv_path.resolve())
    log.info("JSON: %s", json_path.resolve())
    log.info("Per-row logs in: %s", RUN_DIR.resolve())
    log.info("Combined run log: %s", RUN_LOG_PATH.resolve())


if __name__ == "__main__":
    asyncio.run(main())
