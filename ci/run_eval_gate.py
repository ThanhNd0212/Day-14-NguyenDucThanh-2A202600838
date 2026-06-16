# -*- coding: utf-8 -*-
"""
CI/CD Evaluation Quality Gate — Bonus: CI/CD Integration
=========================================================
Runs a 5-question fast eval on the golden dataset and enforces metric
thresholds defined via environment variables. Used by GitHub Actions
job "eval-quality-gate". Exits non-zero to block merge on failure.

Usage:
    python ci/run_eval_gate.py

Environment variables (all optional, sensible defaults provided):
    EVAL_FAITH_MIN       Minimum acceptable avg faithfulness  (default 0.35)
    EVAL_RELEV_MIN       Minimum acceptable avg relevance     (default 0.35)
    EVAL_COMP_MIN        Minimum acceptable avg completeness  (default 0.50)
    EVAL_PASS_RATE_MIN   Minimum acceptable pass rate         (default 0.05)
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Load solution module
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
RAGASEvaluator = mod.RAGASEvaluator
BenchmarkRunner = mod.BenchmarkRunner

# ---------------------------------------------------------------------------
# Fast golden dataset — 5 easy pairs from Sports domain
# (Full 20-pair benchmark would be in the full eval run)
# ---------------------------------------------------------------------------
FAST_QA = [
    QAPair(
        question="Who did Carlos Alcaraz defeat to win Roland Garros 2025?",
        expected_answer="Carlos Alcaraz defeated Jannik Sinner to win Roland Garros 2025 with score 4-6 6-7 6-4 7-6 7-6.",
        context="Alcaraz defeated Sinner 4-6, 6-7(4), 6-4, 7-6(3), 7-6(2) in the longest Roland Garros final ever.",
    ),
    QAPair(
        question="Which team won the NBA championship in 2025?",
        expected_answer="The Oklahoma City Thunder won the 2025 NBA championship defeating the Indiana Pacers 103-91 in Game 7.",
        context="Oklahoma City Thunder won the 2025 NBA championship defeating the Indiana Pacers 103-91 in Game 7 on June 22 2025.",
    ),
    QAPair(
        question="What world record did Leon Marchand break in 2025?",
        expected_answer="Leon Marchand broke the 200m individual medley world record with 1 minute 52.69 seconds.",
        context="Leon Marchand broke the 200m IM world record at World Aquatics Championships 2025 Singapore with 1 minute 52.69 seconds.",
    ),
    QAPair(
        question="How many times has Armand Duplantis broken the pole vault world record?",
        expected_answer="Armand Duplantis has broken the pole vault world record 15 times since 2020.",
        context="Duplantis broke the pole vault world record for the 15th time at Mondo Classic 2026 Uppsala Sweden clearing 6.31m.",
    ),
    QAPair(
        question="Who did Oleksandr Usyk defeat to become undisputed heavyweight champion?",
        expected_answer="Oleksandr Usyk defeated Tyson Fury by split decision on May 18 2024 in Riyadh.",
        context="Usyk defeated Fury by split decision 115-112 113-114 114-113 on May 18 2024 in Riyadh Saudi Arabia.",
    ),
]

# ---------------------------------------------------------------------------
# Mock agent: echoes context keywords (realistic stand-in for unit CI runs)
# ---------------------------------------------------------------------------

def mock_sports_agent(question: str) -> str:
    for qa in FAST_QA:
        if qa.question == question:
            words = qa.context.split()
            return " ".join(words[:min(20, len(words))])
    return "I don't know."

# ---------------------------------------------------------------------------
# Thresholds from env
# ---------------------------------------------------------------------------

FAITH_MIN = float(os.getenv("EVAL_FAITH_MIN", "0.35"))
RELEV_MIN = float(os.getenv("EVAL_RELEV_MIN", "0.35"))
COMP_MIN = float(os.getenv("EVAL_COMP_MIN", "0.50"))
PASS_RATE_MIN = float(os.getenv("EVAL_PASS_RATE_MIN", "0.05"))

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

evaluator = RAGASEvaluator()
runner = BenchmarkRunner()

results = runner.run(FAST_QA, mock_sports_agent, evaluator)
report = runner.generate_report(results)

print("\n=== Evaluation Quality Gate Report ===")
print(f"Pass rate:       {report['pass_rate']:.1%}  (min: {PASS_RATE_MIN:.1%})")
print(f"Avg Faithfulness:{report['avg_faithfulness']:.3f}  (min: {FAITH_MIN:.3f})")
print(f"Avg Relevance:   {report['avg_relevance']:.3f}  (min: {RELEV_MIN:.3f})")
print(f"Avg Completeness:{report.get('avg_completeness', 0):.3f}  (min: {COMP_MIN:.3f})")

# Save JSON report for artifact upload
report_path = ROOT / "ci" / "eval_report.json"
with open(report_path, "w", encoding="utf-8") as f:
    json.dump({**report, "thresholds": {
        "faith_min": FAITH_MIN,
        "relev_min": RELEV_MIN,
        "comp_min": COMP_MIN,
        "pass_rate_min": PASS_RATE_MIN,
    }}, f, indent=2)

# Gate check
failures: list[str] = []
if report["avg_faithfulness"] < FAITH_MIN:
    failures.append(f"Faithfulness {report['avg_faithfulness']:.3f} < {FAITH_MIN}")
if report["avg_relevance"] < RELEV_MIN:
    failures.append(f"Relevance {report['avg_relevance']:.3f} < {RELEV_MIN}")
if report.get("avg_completeness", 0) < COMP_MIN:
    failures.append(f"Completeness {report.get('avg_completeness', 0):.3f} < {COMP_MIN}")
if report["pass_rate"] < PASS_RATE_MIN:
    failures.append(f"Pass rate {report['pass_rate']:.1%} < {PASS_RATE_MIN:.1%}")

if failures:
    print("\n[GATE FAILED] Metric threshold(s) not met:")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("\n[GATE PASSED] All metrics within acceptable thresholds.")
    sys.exit(0)
