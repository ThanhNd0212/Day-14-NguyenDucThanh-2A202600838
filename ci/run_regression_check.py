# -*- coding: utf-8 -*-
"""
CI/CD Regression Check — Bonus: CI/CD Integration
==================================================
Loads a stored baseline from ci/baseline.json (if it exists), runs the
same fast eval, and calls BenchmarkRunner.run_regression() to detect
metric drops > 0.05. Writes a plain-text summary to ci/regression_report.txt.

If no baseline exists yet, saves the current results as the new baseline
and exits 0 (first run always passes).

Usage:
    python ci/run_regression_check.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Load solution module (same as run_eval_gate.py)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
solution_path = ROOT / "solution" / "solution.py"
template_path = ROOT / "template.py"

src = solution_path if solution_path.exists() else template_path
spec = importlib.util.spec_from_file_location("eval_module", str(src))
mod = importlib.util.module_from_spec(spec)
sys.modules["eval_module"] = mod
spec.loader.exec_module(mod)

QAPair = mod.QAPair
EvalResult = mod.EvalResult
RAGASEvaluator = mod.RAGASEvaluator
BenchmarkRunner = mod.BenchmarkRunner

# ---------------------------------------------------------------------------
# Inline fast QA dataset (same 5 pairs as run_eval_gate.py)
# ---------------------------------------------------------------------------
FAST_QA = [
    QAPair("Who did Alcaraz defeat at RG 2025?",
           "Alcaraz defeated Sinner 4-6 6-7 6-4 7-6 7-6.",
           "Alcaraz defeated Sinner 4-6 6-7 6-4 7-6 7-6 in the longest Roland Garros final."),
    QAPair("Which team won NBA 2025?",
           "Oklahoma City Thunder defeated Indiana Pacers 103-91 in Game 7.",
           "Oklahoma City Thunder won the 2025 NBA championship defeating Indiana Pacers 103-91 Game 7."),
    QAPair("What record did Marchand break?",
           "Marchand broke the 200m IM world record with 1 minute 52.69 seconds.",
           "Leon Marchand broke the 200m IM world record at World Aquatics 2025 with 1 minute 52.69 seconds."),
    QAPair("How many WRs has Duplantis broken?",
           "Duplantis broke the pole vault world record 15 times since 2020.",
           "Duplantis broke the pole vault world record 15 times since 2020 most recently 6.31m Mondo Classic 2026."),
    QAPair("Who did Usyk defeat to become undisputed champ?",
           "Usyk defeated Fury by split decision in Riyadh.",
           "Usyk defeated Fury split decision 115-112 113-114 114-113 Riyadh May 18 2024."),
]

def mock_agent(question: str) -> str:
    for qa in FAST_QA:
        if qa.question == question:
            words = qa.context.split()
            return " ".join(words[:min(20, len(words))])
    return ""

# ---------------------------------------------------------------------------
# Run current evaluation
# ---------------------------------------------------------------------------
evaluator = RAGASEvaluator()
runner = BenchmarkRunner()

current_results = runner.run(FAST_QA, mock_agent, evaluator)
current_report = runner.generate_report(current_results)

BASELINE_PATH = ROOT / "ci" / "baseline.json"
REPORT_PATH = ROOT / "ci" / "regression_report.txt"

# ---------------------------------------------------------------------------
# Helper: results from saved avg scores as stub EvalResult list
# ---------------------------------------------------------------------------
def _stub_results(report: dict) -> list[EvalResult]:
    """Create stub EvalResult list matching avg scores for regression comparison."""
    qa = QAPair("stub", "stub", "stub")
    avg_f = report.get("avg_faithfulness", 0.5)
    avg_r = report.get("avg_relevance", 0.5)
    avg_c = report.get("avg_completeness", 0.5)
    return [EvalResult(qa, "stub", avg_f, avg_r, avg_c, True)]

# ---------------------------------------------------------------------------
# First run — save baseline and exit
# ---------------------------------------------------------------------------
if not BASELINE_PATH.exists():
    with open(BASELINE_PATH, "w") as f:
        json.dump(current_report, f, indent=2)
    report_text = (
        "=== Regression Check ===\n"
        "No baseline found. Saving current results as baseline.\n"
        f"Faithfulness: {current_report['avg_faithfulness']:.3f}\n"
        f"Relevance:    {current_report['avg_relevance']:.3f}\n"
        f"Completeness: {current_report.get('avg_completeness', 0):.3f}\n"
        "Status: BASELINE SAVED (first run)\n"
    )
    REPORT_PATH.write_text(report_text)
    print(report_text)
    sys.exit(0)

# ---------------------------------------------------------------------------
# Compare against baseline
# ---------------------------------------------------------------------------
with open(BASELINE_PATH) as f:
    baseline_report = json.load(f)

baseline_results = _stub_results(baseline_report)
regression = runner.run_regression(current_results, baseline_results)

lines = ["=== Regression Check vs Baseline ==="]
lines.append(f"Faithfulness:  baseline={regression['baseline_avg_faithfulness']:.3f}  "
             f"current={regression['new_avg_faithfulness']:.3f}")
lines.append(f"Regressions detected: {regression['regressions']}")
lines.append(f"Status: {'PASSED' if regression['passed'] else 'REGRESSION DETECTED'}")

report_text = "\n".join(lines) + "\n"
REPORT_PATH.write_text(report_text)
print(report_text)

sys.exit(0 if regression["passed"] else 1)
