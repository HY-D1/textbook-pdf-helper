"""
Replay Engine and Evidence Export - Policy Comparison Layer.

This module provides replay functionality for comparing policy decisions
across traces. It produces research-ready artifacts:
- replay_summary.csv / replay_summary.json
- per_learner_metrics.csv
- policy_comparison.csv

IMPORTANT: This is replay evidence, NOT live online adaptation.
All outputs are deterministic from trace data + policy rules.

Usage:
    from replay import ReplayEngine, run_replay

    engine = ReplayEngine(policies=get_default_policies())
    results = engine.replay_trace(trace)
    engine.export_results(output_dir)
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .trace_schema import LearnerTrace, TraceEvent, EventType, load_traces_from_directory
from .policies import (
    EscalationPolicy,
    LearnerState,
    EscalationDecision,
    compute_learner_state,
    get_default_policies,
)
from .experiment_flags import ExperimentFlags, flags_from_trace_context
from .replay_metrics import compute_all_metrics, AllMetrics


# =============================================================================
# Replay Result Data Classes
# =============================================================================

@dataclass
class ReplayDecisionPoint:
    """
    A single decision point from replay.

    Captures what the policy decided at a specific point in the trace.
    """

    # Positioning
    event_index: int
    event_id: str
    timestamp: str

    # Context
    learner_id: str
    problem_id: str
    concept_id: str | None = None
    event_type: str = ""

    # Policy output
    policy_id: str = ""
    action: str = ""  # EscalationAction
    target_level: str = ""  # EscalationLevel
    trigger_reason: str = ""
    rule_applied: str = ""

    # Metrics at decision time
    error_count_at_escalation: int = 0
    time_to_escalation: float = 0.0
    strategy_assigned: str = ""

    # Simulated contract fields (for replay completeness)
    reward_value: float | None = None
    strategy_updated: bool = False

    # Reinforcement fields (placeholder for contract completeness)
    reinforcement_prompt_shown: bool = False
    reinforcement_response: str | None = None
    reinforcement_correct: bool | None = None

    # Prerequisite detection
    prerequisite_violation_detected: bool = False
    missing_prerequisites: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    def to_csv_row(self) -> dict[str, Any]:
        """Convert to flat dictionary for CSV export."""
        return {
            "event_index": self.event_index,
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "learner_id": self.learner_id,
            "problem_id": self.problem_id,
            "concept_id": self.concept_id or "",
            "event_type": self.event_type,
            "policy_id": self.policy_id,
            "action": self.action,
            "target_level": self.target_level,
            "trigger_reason": self.trigger_reason,
            "rule_applied": self.rule_applied,
            "error_count_at_escalation": self.error_count_at_escalation,
            "time_to_escalation": self.time_to_escalation,
            "strategy_assigned": self.strategy_assigned,
            "reward_value": self.reward_value if self.reward_value is not None else "",
            "strategy_updated": self.strategy_updated,
            "reinforcement_prompt_shown": self.reinforcement_prompt_shown,
            "reinforcement_response": self.reinforcement_response or "",
            "reinforcement_correct": (
                "true" if self.reinforcement_correct else
                "false" if self.reinforcement_correct is False else ""
            ),
            "prerequisite_violation_detected": self.prerequisite_violation_detected,
            "missing_prerequisites": "|".join(self.missing_prerequisites),
        }


@dataclass
class ReplayResult:
    """Complete replay result for a single trace under one policy."""

    trace_id: str
    policy_id: str
    learner_id: str
    session_id: str

    # Replay configuration
    flags: dict[str, Any] = field(default_factory=dict)
    is_synthetic: bool = True

    # Decision history
    decision_points: list[ReplayDecisionPoint] = field(default_factory=list)

    # Metrics
    metrics: AllMetrics | None = None

    # Summary statistics
    total_events: int = 0
    escalation_count: int = 0
    unique_problems: int = 0

    # Timing
    replay_started_at: str = ""
    replay_completed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "policy_id": self.policy_id,
            "learner_id": self.learner_id,
            "session_id": self.session_id,
            "flags": self.flags,
            "is_synthetic": self.is_synthetic,
            "total_events": self.total_events,
            "escalation_count": self.escalation_count,
            "unique_problems": self.unique_problems,
            "replay_started_at": self.replay_started_at,
            "replay_completed_at": self.replay_completed_at,
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "decision_points": [dp.to_dict() for dp in self.decision_points],
        }


@dataclass
class ReplaySummary:
    """Summary across all replayed traces and policies."""

    replay_run_id: str
    total_traces: int
    total_policies: int
    traces: list[str] = field(default_factory=list)
    policies: list[str] = field(default_factory=list)

    # Aggregated metrics by policy
    policy_metrics: dict[str, dict[str, float]] = field(default_factory=dict)

    # Timestamp
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "replay_run_id": self.replay_run_id,
            "generated_at": self.generated_at,
            "total_traces": self.total_traces,
            "total_policies": self.total_policies,
            "traces": self.traces,
            "policies": self.policies,
            "policy_metrics": self.policy_metrics,
        }


# =============================================================================
# Replay Engine
# =============================================================================

class ReplayEngine:
    """
    Engine for replaying traces under multiple policies.

    This reconstructs decision points from trace events and applies
    formal policies to produce comparable decision outputs.
    """

    def __init__(
        self,
        policies: list[EscalationPolicy] | None = None,
        flags: ExperimentFlags | None = None,
    ):
        self.policies = policies or get_default_policies()
        self.flags = flags or ExperimentFlags()
        self.results: list[ReplayResult] = []

    def replay_trace(
        self,
        trace: LearnerTrace,
        policy_filter: list[str] | None = None,
    ) -> list[ReplayResult]:
        """
        Replay a single trace under all (or filtered) policies.

        Args:
            trace: The learner trace to replay
            policy_filter: Optional list of policy IDs to use

        Returns:
            List of ReplayResult, one per policy
        """
        results = []

        # Get flags from trace context if available
        trace_flags = flags_from_trace_context({"session_config": trace.session_config})
        merged_flags = self.flags  # Engine flags take precedence

        policies_to_run = self.policies
        if policy_filter:
            policies_to_run = [p for p in self.policies if p.policy_id in policy_filter]

        for policy in policies_to_run:
            result = self._replay_single_policy(trace, policy, merged_flags)
            results.append(result)
            self.results.append(result)

        return results

    def _replay_single_policy(
        self,
        trace: LearnerTrace,
        policy: EscalationPolicy,
        flags: ExperimentFlags,
    ) -> ReplayResult:
        """Replay trace under a single policy."""
        started_at = datetime.now(timezone.utc).isoformat()

        result = ReplayResult(
            trace_id=trace.trace_id,
            policy_id=policy.policy_id,
            learner_id=trace.learner_id,
            session_id=trace.session_id,
            flags=flags.to_dict(),
            is_synthetic=trace.is_synthetic,
            total_events=len(trace.events),
            unique_problems=len(trace.get_unique_problems()),
            replay_started_at=started_at,
        )

        # Track prerequisite violations for this replay
        concept_attempts: dict[str, int] = {}  # concept -> count
        concept_successes: dict[str, int] = {}

        # Process each event
        for i, event in enumerate(trace.events):
            # Compute learner state at this point
            flags_dict = flags.apply_to_policy_context()
            learner_state = compute_learner_state(trace.events, i, flags_dict)

            # Apply policy
            decision = policy.should_escalate(learner_state)

            # Track concept attempts for prerequisite checking
            if event.concept_id:
                concept_attempts[event.concept_id] = concept_attempts.get(event.concept_id, 0) + 1
                if event.event_type == EventType.PROBLEM_SOLVED.value:
                    concept_successes[event.concept_id] = concept_successes.get(event.concept_id, 0) + 1

            # Check for prerequisite violation (simplified: if concept has many errors)
            prereq_violation = False
            missing_prereqs: list[str] = []
            if event.concept_id and flags.enforce_prerequisites:
                errors_on_concept = sum(
                    1 for e in trace.events[:i+1]
                    if e.concept_id == event.concept_id and e.error_subtype
                )
                if errors_on_concept >= 3:
                    prereq_violation = True
                    missing_prereqs.append(f"prereq_for_{event.concept_id}")

            # Only record decision points for escalation-related events
            if decision.action != "wait" or event.is_escalation_event():
                dp = ReplayDecisionPoint(
                    event_index=i,
                    event_id=event.event_id,
                    timestamp=event.timestamp,
                    learner_id=event.learner_id,
                    problem_id=event.problem_id,
                    concept_id=event.concept_id,
                    event_type=event.event_type,
                    policy_id=policy.policy_id,
                    action=decision.action,
                    target_level=decision.target_level,
                    trigger_reason=decision.trigger_reason,
                    rule_applied=decision.rule_applied,
                    error_count_at_escalation=decision.error_count_at_decision,
                    time_to_escalation=decision.time_to_escalation,
                    strategy_assigned=decision.strategy_assigned,
                    reward_value=decision.reward_value,
                    strategy_updated=decision.strategy_updated,
                    prerequisite_violation_detected=prereq_violation,
                    missing_prerequisites=missing_prereqs,
                )
                result.decision_points.append(dp)

                if decision.action != "wait":
                    result.escalation_count += 1

        # Compute metrics
        result.metrics = compute_all_metrics(trace)
        result.metrics.policy_id = policy.policy_id
        result.metrics.trace_id = trace.trace_id
        result.metrics.computed_at = datetime.now(timezone.utc).isoformat()

        result.replay_completed_at = datetime.now(timezone.utc).isoformat()

        return result

    def export_results(
        self,
        output_dir: Path,
        run_id: str | None = None,
    ) -> dict[str, Path]:
        """
        Export all replay results to research-ready artifacts.

        Produces:
        - replay_summary.json
        - replay_summary.csv
        - per_learner_metrics.csv
        - policy_comparison.csv

        Returns:
            Dict mapping artifact name to file path
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        run_id = run_id or f"replay_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        exported: dict[str, Path] = {}

        # 1. replay_summary.json
        summary_json = self._export_summary_json(output_dir, run_id)
        exported["replay_summary_json"] = summary_json

        # 2. replay_summary.csv
        summary_csv = self._export_summary_csv(output_dir, run_id)
        exported["replay_summary_csv"] = summary_csv

        # 3. per_learner_metrics.csv
        learner_csv = self._export_per_learner_metrics(output_dir, run_id)
        exported["per_learner_metrics_csv"] = learner_csv

        # 4. policy_comparison.csv
        comparison_csv = self._export_policy_comparison(output_dir, run_id)
        exported["policy_comparison_csv"] = comparison_csv

        return exported

    def _export_summary_json(self, output_dir: Path, run_id: str) -> Path:
        """Export replay_summary.json."""
        # Group results by trace
        traces_by_id: dict[str, list[ReplayResult]] = {}
        for r in self.results:
            traces_by_id.setdefault(r.trace_id, []).append(r)

        summary = ReplaySummary(
            replay_run_id=run_id,
            total_traces=len(traces_by_id),
            total_policies=len(self.policies),
            traces=list(traces_by_id.keys()),
            policies=[p.policy_id for p in self.policies],
        )

        # Aggregate metrics by policy
        for policy in self.policies:
            policy_results = [r for r in self.results if r.policy_id == policy.policy_id]
            if policy_results:
                hdi_values = [r.metrics.hdi.value for r in policy_results if r.metrics]
                csi_values = [r.metrics.csi.value for r in policy_results if r.metrics]
                aps_values = [r.metrics.aps.value for r in policy_results if r.metrics]

                summary.policy_metrics[policy.policy_id] = {
                    "avg_hdi": round(sum(hdi_values) / len(hdi_values), 4) if hdi_values else 0,
                    "avg_csi": round(sum(csi_values) / len(csi_values), 4) if csi_values else 0,
                    "avg_aps": round(sum(aps_values) / len(aps_values), 4) if aps_values else 0,
                    "total_decisions": sum(len(r.decision_points) for r in policy_results),
                }

        path = output_dir / "replay_summary.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2, ensure_ascii=False)

        return path

    def _export_summary_csv(self, output_dir: Path, run_id: str) -> Path:
        """Export replay_summary.csv with one row per trace-policy pair."""
        path = output_dir / "replay_summary.csv"

        fieldnames = [
            "run_id",
            "trace_id",
            "policy_id",
            "learner_id",
            "is_synthetic",
            "total_events",
            "escalation_count",
            "unique_problems",
            "hdi",
            "csi",
            "aps",
            "persistence",
            "coverage",
            "time_to_success",
            "rqs",
            "replay_started",
            "replay_completed",
        ]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for r in self.results:
                row = {
                    "run_id": run_id,
                    "trace_id": r.trace_id,
                    "policy_id": r.policy_id,
                    "learner_id": r.learner_id,
                    "is_synthetic": r.is_synthetic,
                    "total_events": r.total_events,
                    "escalation_count": r.escalation_count,
                    "unique_problems": r.unique_problems,
                    "replay_started": r.replay_started_at,
                    "replay_completed": r.replay_completed_at,
                }

                if r.metrics:
                    row["hdi"] = r.metrics.hdi.value
                    row["csi"] = r.metrics.csi.value
                    row["aps"] = r.metrics.aps.value
                    row["persistence"] = r.metrics.persistence.value
                    row["coverage"] = r.metrics.coverage.value
                    row["time_to_success"] = r.metrics.time_to_success.value
                    row["rqs"] = r.metrics.rqs.value if r.metrics.rqs.value is not None else ""

                writer.writerow(row)

        return path

    def _export_per_learner_metrics(self, output_dir: Path, run_id: str) -> Path:
        """Export per_learner_metrics.csv."""
        path = output_dir / "per_learner_metrics.csv"

        fieldnames = [
            "run_id",
            "trace_id",
            "learner_id",
            "policy_id",
            "total_problems",
            "problems_solved",
            "total_errors",
            "hints_requested",
            "explanations_shown",
            "hdi",
            "csi",
            "aps",
            "persistence",
            "coverage",
            "time_to_success_norm",
            "avg_solve_time_seconds",
            "has_notes",
            "rqs",
        ]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for r in self.results:
                row = {
                    "run_id": run_id,
                    "trace_id": r.trace_id,
                    "learner_id": r.learner_id,
                    "policy_id": r.policy_id,
                    "total_problems": r.unique_problems,
                }

                if r.metrics:
                    row["hdi"] = round(r.metrics.hdi.value, 4)
                    row["csi"] = round(r.metrics.csi.value, 4)
                    row["aps"] = round(r.metrics.aps.value, 4)
                    row["persistence"] = round(r.metrics.persistence.value, 4)
                    row["coverage"] = round(r.metrics.coverage.value, 4)
                    row["time_to_success_norm"] = round(r.metrics.time_to_success.value, 4)
                    row["avg_solve_time_seconds"] = r.metrics.time_to_success.average_seconds
                    row["has_notes"] = r.metrics.rqs.note_count > 0
                    row["rqs"] = round(r.metrics.rqs.value, 4) if r.metrics.rqs.value is not None else ""

                    # Derive additional counts from trace if available
                    # (These would come from actual trace analysis)
                    row["problems_solved"] = r.metrics.time_to_success.total_solved
                    row["total_errors"] = r.metrics.hdi.post_explanation_penalty  # proxy

                writer.writerow(row)

        return path

    def _export_policy_comparison(self, output_dir: Path, run_id: str) -> Path:
        """Export policy_comparison.csv."""
        path = output_dir / "policy_comparison.csv"

        fieldnames = [
            "run_id",
            "policy_id",
            "strategy_label",
            "total_traces_replayed",
            "avg_hdi",
            "avg_csi",
            "avg_aps",
            "avg_persistence",
            "avg_coverage",
            "avg_time_to_success",
            "total_escalations",
            "avg_escalations_per_trace",
            "total_decision_points",
        ]

        # Aggregate by policy
        policy_stats: dict[str, dict[str, Any]] = {}
        for r in self.results:
            if r.policy_id not in policy_stats:
                policy_stats[r.policy_id] = {
                    "traces": 0,
                    "hdi_sum": 0.0,
                    "csi_sum": 0.0,
                    "aps_sum": 0.0,
                    "persistence_sum": 0.0,
                    "coverage_sum": 0.0,
                    "tts_sum": 0.0,
                    "escalations": 0,
                    "decision_points": 0,
                    "strategy_label": "",
                }

            stats = policy_stats[r.policy_id]
            stats["traces"] += 1
            stats["escalations"] += r.escalation_count
            stats["decision_points"] += len(r.decision_points)

            if r.metrics:
                stats["hdi_sum"] += r.metrics.hdi.value
                stats["csi_sum"] += r.metrics.csi.value
                stats["aps_sum"] += r.metrics.aps.value
                stats["persistence_sum"] += r.metrics.persistence.value
                stats["coverage_sum"] += r.metrics.coverage.value
                stats["tts_sum"] += r.metrics.time_to_success.value

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for policy_id, stats in policy_stats.items():
                count = stats["traces"]
                row = {
                    "run_id": run_id,
                    "policy_id": policy_id,
                    "strategy_label": stats["strategy_label"],
                    "total_traces_replayed": count,
                    "avg_hdi": round(stats["hdi_sum"] / count, 4) if count else 0,
                    "avg_csi": round(stats["csi_sum"] / count, 4) if count else 0,
                    "avg_aps": round(stats["aps_sum"] / count, 4) if count else 0,
                    "avg_persistence": round(stats["persistence_sum"] / count, 4) if count else 0,
                    "avg_coverage": round(stats["coverage_sum"] / count, 4) if count else 0,
                    "avg_time_to_success": round(stats["tts_sum"] / count, 4) if count else 0,
                    "total_escalations": stats["escalations"],
                    "avg_escalations_per_trace": round(stats["escalations"] / count, 2) if count else 0,
                    "total_decision_points": stats["decision_points"],
                }
                writer.writerow(row)

        return path


# =============================================================================
# High-level API
# =============================================================================

def run_replay(
    trace_input: Path,
    output_dir: Path,
    policies: list[EscalationPolicy] | None = None,
    flags: ExperimentFlags | None = None,
    policy_filter: list[str] | None = None,
    run_id: str | None = None,
) -> dict[str, Path]:
    """
    Run replay on traces and export results.

    Args:
        trace_input: Path to trace file or directory
        output_dir: Directory for output artifacts
        policies: Optional custom policies (defaults to 3 standard)
        flags: Optional experiment flags
        policy_filter: Optional list of policy IDs to run
        run_id: Optional run identifier

    Returns:
        Dict mapping artifact names to file paths
    """
    engine = ReplayEngine(policies=policies, flags=flags)

    # Load traces
    traces: list[LearnerTrace] = []
    trace_path = Path(trace_input)

    if trace_path.is_dir():
        traces = load_traces_from_directory(trace_path)
    elif trace_path.exists():
        traces = [LearnerTrace.from_dict(json.loads(trace_path.read_text(encoding="utf-8")))]

    if not traces:
        raise ValueError(f"No traces found at {trace_input}")

    # Replay each trace
    for trace in traces:
        engine.replay_trace(trace, policy_filter=policy_filter)

    # Export results
    return engine.export_results(output_dir, run_id)


# Re-export for convenience
from .trace_schema import EventType as _EventType  # noqa: F401
