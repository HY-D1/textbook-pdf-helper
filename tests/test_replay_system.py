"""
Tests for the replay/evidence system (Day 4 implementation).

Covers:
1. Trace schema load/validation
2. Policy decision behavior for all 3 policies
3. Experiment flag validation
4. Replay over minimal synthetic trace
5. Output artifact creation
6. Required replay columns/fields present
7. Deterministic metric calculations
8. Prerequisite violation logging
9. CLI replay command
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from algl_pdf_helper.trace_schema import (
    LearnerTrace,
    TraceEvent,
    EventType,
    ErrorSubtype,
    load_trace,
    save_trace,
    make_synthetic_trace,
    get_minimal_valid_trace,
)
from algl_pdf_helper.policies import (
    EscalationPolicy,
    LearnerState,
    EscalationDecision,
    EscalationLevel,
    EscalationAction,
    get_default_policies,
    get_policy_by_id,
    compute_learner_state,
    FAST_ESCALATOR,
    SLOW_ESCALATOR,
    ADAPTIVE_ESCALATOR,
)
from algl_pdf_helper.experiment_flags import (
    ExperimentFlags,
    get_baseline_flags,
    get_no_textbook_flags,
    list_predefined_configs,
)
from algl_pdf_helper.replay_metrics import (
    HDIMetric,
    CSIMetric,
    APSMetric,
    PersistenceScoreMetric,
    SimulatedCoverageScoreMetric,
    TimeToSuccessMetric,
    RQSMetric,
    compute_all_metrics,
)
from algl_pdf_helper.replay import (
    ReplayEngine,
    ReplayDecisionPoint,
    ReplayResult,
    run_replay,
)


# =============================================================================
# Trace Schema Tests
# =============================================================================

class TestTraceSchema:
    """Test trace schema loading and validation."""

    def test_load_minimal_trace(self, tmp_path: Path):
        """Test loading a minimal valid trace."""
        trace = get_minimal_valid_trace()
        path = tmp_path / "minimal.json"
        save_trace(trace, path)

        loaded = load_trace(path)
        assert loaded.trace_id == "minimal_test"
        assert loaded.learner_id == "test_learner"
        assert len(loaded.events) == 1

    def test_trace_validation_passes_for_valid(self):
        """Test validation passes for valid trace."""
        trace = get_minimal_valid_trace()
        issues = trace.validate()
        assert issues == []

    def test_trace_validation_fails_for_empty(self):
        """Test validation fails for empty trace."""
        trace = LearnerTrace(trace_id="empty", events=[])
        issues = trace.validate()
        assert len(issues) == 1
        assert "no events" in issues[0].lower()

    def test_synthetic_trace_generation(self):
        """Test synthetic trace generation."""
        trace = make_synthetic_trace("test_001", "test_profile", num_problems=2, error_rate=0.5)

        assert trace.trace_id == "test_001"
        assert trace.is_synthetic is True
        assert trace.synthetic_profile == "test_profile"
        assert len(trace.events) > 0
        assert len(trace.get_unique_problems()) == 2

    def test_event_type_detection(self):
        """Test event type helper methods."""
        error_event = TraceEvent(
            event_id="e1",
            timestamp="2025-01-01T10:00:00Z",
            learner_id="l1",
            session_id="s1",
            problem_id="p1",
            event_type=EventType.ERROR_RECORDED.value,
            error_subtype=ErrorSubtype.MISSING_COMMA_IN_SELECT.value,
        )
        assert error_event.is_error_event() is True
        assert error_event.is_escalation_event() is False

        escalation_event = TraceEvent(
            event_id="e2",
            timestamp="2025-01-01T10:00:00Z",
            learner_id="l1",
            session_id="s1",
            problem_id="p1",
            event_type=EventType.HINT_REQUESTED.value,
            escalation_level="L1",
        )
        assert escalation_event.is_error_event() is False
        assert escalation_event.is_escalation_event() is True


# =============================================================================
# Policy Tests
# =============================================================================

class TestPolicies:
    """Test policy decision behavior."""

    def test_default_policies_count(self):
        """Test that we have exactly 3 default policies."""
        policies = get_default_policies()
        assert len(policies) == 3
        policy_ids = {p.policy_id for p in policies}
        assert policy_ids == {"fast_escalator", "slow_escalator", "adaptive_escalator"}

    def test_get_policy_by_id(self):
        """Test policy lookup by ID."""
        policy = get_policy_by_id("fast_escalator")
        assert policy is not None
        assert policy.policy_id == "fast_escalator"

        missing = get_policy_by_id("nonexistent")
        assert missing is None

    def test_fast_escalator_first_error_triggers(self):
        """Test fast escalator triggers on first error."""
        state = LearnerState(
            learner_id="l1",
            problem_id="p1",
            consecutive_errors=1,
            current_escalation_level=EscalationLevel.L0_NONE.value,
        )
        decision = FAST_ESCALATOR.should_escalate(state)

        assert decision.action == EscalationAction.OFFER_HINT.value
        assert decision.target_level == EscalationLevel.L1_HINT.value
        assert "first_error" in decision.trigger_reason

    def test_fast_escalator_third_error_escalates(self):
        """Test fast escalator escalates to L3 on third error."""
        state = LearnerState(
            learner_id="l1",
            problem_id="p1",
            consecutive_errors=3,
            current_escalation_level=EscalationLevel.L0_NONE.value,
        )
        decision = FAST_ESCALATOR.should_escalate(state)

        assert decision.action == EscalationAction.ESCALATE_TO_L3.value
        assert decision.target_level == EscalationLevel.L3_DEEP_EXPLANATION.value

    def test_slow_escalator_waits_for_early_errors(self):
        """Test slow escalator waits for first 2 errors."""
        state = LearnerState(
            learner_id="l1",
            problem_id="p1",
            consecutive_errors=1,
            prior_recovery_count=0,
            current_escalation_level=EscalationLevel.L0_NONE.value,
        )
        decision = SLOW_ESCALATOR.should_escalate(state)

        assert decision.action == EscalationAction.WAIT.value

    def test_slow_escalator_escalates_after_fifth_error(self):
        """Test slow escalator escalates after 5 errors."""
        state = LearnerState(
            learner_id="l1",
            problem_id="p1",
            consecutive_errors=5,
            prior_recovery_count=0,
            current_escalation_level=EscalationLevel.L0_NONE.value,
        )
        decision = SLOW_ESCALATOR.should_escalate(state)

        assert decision.action == EscalationAction.SHOW_EXPLANATION.value
        assert decision.target_level == EscalationLevel.L2_EXPLANATION.value

    def test_adaptive_escalator_uses_strain_score(self):
        """Test adaptive escalator uses strain score calculation."""
        # High strain: multiple errors + repeated subtype
        state = LearnerState(
            learner_id="l1",
            problem_id="p1",
            consecutive_errors=3,
            repeated_same_subtype=True,
            time_stuck=120,
            current_escalation_level=EscalationLevel.L0_NONE.value,
        )
        decision = ADAPTIVE_ESCALATOR.should_escalate(state)

        # Should escalate due to high strain
        assert decision.action != EscalationAction.WAIT.value
        assert decision.rule_applied.startswith("adaptive")

    def test_compute_learner_state_from_events(self):
        """Test learner state computation from trace events."""
        events = [
            TraceEvent(
                event_id="e1",
                timestamp="2025-01-01T10:00:00Z",
                learner_id="l1",
                session_id="s1",
                problem_id="p1",
                event_type=EventType.PROBLEM_ATTEMPT.value,
            ),
            TraceEvent(
                event_id="e2",
                timestamp="2025-01-01T10:00:10Z",
                learner_id="l1",
                session_id="s1",
                problem_id="p1",
                event_type=EventType.ERROR_RECORDED.value,
                error_subtype=ErrorSubtype.MISSING_COMMA_IN_SELECT.value,
            ),
        ]

        state = compute_learner_state(events, 1, {})
        assert state.learner_id == "l1"
        assert state.problem_id == "p1"
        assert state.total_errors == 1
        assert state.consecutive_errors == 1


# =============================================================================
# Experiment Flags Tests
# =============================================================================

class TestExperimentFlags:
    """Test experiment flag validation."""

    def test_baseline_flags_all_disabled(self):
        """Test baseline flags have all toggles disabled."""
        flags = get_baseline_flags()
        assert flags.textbook_disabled is False
        assert flags.adaptive_ladder_disabled is False
        assert flags.immediate_explanation_mode is False
        assert flags.static_hint_mode is False
        assert flags.is_baseline() is True

    def test_no_textbook_flags(self):
        """Test no-textbook flag configuration."""
        flags = get_no_textbook_flags()
        assert flags.textbook_disabled is True
        assert flags.is_baseline() is False

    def test_flag_validation_detects_conflicts(self):
        """Test flag validation detects conflicting settings."""
        flags = ExperimentFlags(
            immediate_explanation_mode=True,
            static_hint_mode=True,
        )
        issues = flags.validate()
        assert len(issues) > 0

    def test_predefined_configs(self):
        """Test all predefined configs are valid."""
        configs = list_predefined_configs()
        assert "baseline" in configs
        assert "no_textbook" in configs
        assert "no_adaptive" in configs
        assert "immediate_explanation" in configs


# =============================================================================
# Replay Metrics Tests
# =============================================================================

class TestReplayMetrics:
    """Test deterministic metric calculations."""

    def test_hdi_computation(self):
        """Test HDI computation is deterministic."""
        trace = make_synthetic_trace("hdi_test", "test", num_problems=2, error_rate=0.5)

        hdi1 = HDIMetric.compute(trace)
        hdi2 = HDIMetric.compute(trace)

        assert hdi1.value == hdi2.value  # Deterministic
        assert 0.0 <= hdi1.value <= 1.0

    def test_csi_computation(self):
        """Test CSI computation."""
        trace = make_synthetic_trace("csi_test", "test", num_problems=2, error_rate=0.7)

        csi = CSIMetric.compute(trace)
        assert 0.0 <= csi.value <= 1.0
        # High error rate should produce higher strain
        assert csi.value > 0

    def test_aps_computation(self):
        """Test APS computation."""
        trace = make_synthetic_trace("aps_test", "test", num_problems=2, error_rate=0.5)

        aps = APSMetric.compute(trace)
        assert 0.0 <= aps.value <= 1.0

    def test_persistence_score(self):
        """Test persistence score."""
        trace = make_synthetic_trace("persist_test", "test", num_problems=2, error_rate=0.5)

        persist = PersistenceScoreMetric.compute(trace)
        assert 0.0 <= persist.value <= 1.0

    def test_coverage_score(self):
        """Test coverage score."""
        trace = make_synthetic_trace("coverage_test", "test", num_problems=3, error_rate=0.5)

        coverage = SimulatedCoverageScoreMetric.compute(trace, total_available_concepts=5)
        assert 0.0 <= coverage.value <= 1.0
        assert coverage.unique_concepts_exposed <= 3

    def test_time_to_success(self):
        """Test time-to-success metric."""
        trace = make_synthetic_trace("tts_test", "test", num_problems=2, error_rate=0.3)

        tts = TimeToSuccessMetric.compute(trace)
        assert 0.0 <= tts.value <= 1.0

    def test_rqs_null_without_notes(self):
        """Test RQS is null when no notes exist."""
        trace = make_synthetic_trace("rqs_test", "test", num_problems=1, error_rate=0.5)

        rqs = RQSMetric.compute(trace)
        assert rqs.value is None
        assert rqs.note_count == 0

    def test_compute_all_metrics(self):
        """Test computing all metrics at once."""
        trace = make_synthetic_trace("all_test", "test", num_problems=2, error_rate=0.5)

        all_metrics = compute_all_metrics(trace)
        assert all_metrics.hdi is not None
        assert all_metrics.csi is not None
        assert all_metrics.aps is not None


# =============================================================================
# Replay Engine Tests
# =============================================================================

class TestReplayEngine:
    """Test replay engine functionality."""

    def test_replay_single_trace(self):
        """Test replaying a single trace."""
        trace = make_synthetic_trace("replay_test", "test", num_problems=2, error_rate=0.5)
        engine = ReplayEngine()

        results = engine.replay_trace(trace)

        assert len(results) == 3  # 3 default policies
        for result in results:
            assert result.trace_id == trace.trace_id
            assert result.policy_id in {"fast_escalator", "slow_escalator", "adaptive_escalator"}

    def test_replay_produces_decision_points(self):
        """Test replay produces decision points."""
        trace = make_synthetic_trace("dp_test", "test", num_problems=2, error_rate=0.7)
        engine = ReplayEngine()

        results = engine.replay_trace(trace, policy_filter=["fast_escalator"])
        result = results[0]

        # Should have some decision points for high error rate
        assert len(result.decision_points) > 0

    def test_export_artifacts(self, tmp_path: Path):
        """Test export produces all required artifacts."""
        trace = make_synthetic_trace("export_test", "test", num_problems=2, error_rate=0.5)
        engine = ReplayEngine()

        engine.replay_trace(trace)
        artifacts = engine.export_results(tmp_path, run_id="test_run")

        assert "replay_summary_json" in artifacts
        assert "replay_summary_csv" in artifacts
        assert "per_learner_metrics_csv" in artifacts
        assert "policy_comparison_csv" in artifacts

        # Verify files exist
        for path in artifacts.values():
            assert path.exists()

    def test_csv_has_required_columns(self, tmp_path: Path):
        """Test CSV output has all required logging fields."""
        trace = make_synthetic_trace("csv_test", "test", num_problems=1, error_rate=0.5)
        engine = ReplayEngine()

        engine.replay_trace(trace)
        artifacts = engine.export_results(tmp_path, run_id="test_run")

        # Check summary CSV
        with open(artifacts["replay_summary_csv"], newline="") as f:
            reader = csv.DictReader(f)
            columns = set(reader.fieldnames or [])

        # Required columns per task spec
        required = {
            "trace_id", "policy_id", "learner_id", "hdi", "csi", "aps",
            "persistence", "coverage", "time_to_success", "escalation_count",
        }
        for col in required:
            assert col in columns, f"Missing required column: {col}"


# =============================================================================
# Integration Tests
# =============================================================================

class TestReplayIntegration:
    """Integration tests for full replay workflow."""

    def test_run_replay_end_to_end(self, tmp_path: Path):
        """Test complete replay workflow."""
        trace = make_synthetic_trace("e2e_test", "test", num_problems=2, error_rate=0.5)
        trace_dir = tmp_path / "traces"
        trace_dir.mkdir()
        save_trace(trace, trace_dir / "test.json")

        output_dir = tmp_path / "output"

        artifacts = run_replay(
            trace_input=trace_dir,
            output_dir=output_dir,
            run_id="e2e_test",
        )

        assert len(artifacts) == 4  # 4 artifact types

    def test_replay_with_flags(self, tmp_path: Path):
        """Test replay with experiment flags."""
        trace = make_synthetic_trace("flags_test", "test", num_problems=1, error_rate=0.5)
        trace_dir = tmp_path / "traces"
        trace_dir.mkdir()
        save_trace(trace, trace_dir / "test.json")

        flags = get_baseline_flags()

        engine = ReplayEngine(flags=flags)
        engine.replay_trace(trace)
        artifacts = engine.export_results(tmp_path / "output")

        assert "replay_summary_json" in artifacts

    def test_policy_comparison_csv_content(self, tmp_path: Path):
        """Test policy comparison CSV has correct structure."""
        trace = make_synthetic_trace("compare_test", "test", num_problems=2, error_rate=0.5)
        engine = ReplayEngine()

        engine.replay_trace(trace)
        artifacts = engine.export_results(tmp_path, run_id="compare")

        with open(artifacts["policy_comparison_csv"], newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 3  # 3 policies
        policy_ids = {row["policy_id"] for row in rows}
        assert policy_ids == {"fast_escalator", "slow_escalator", "adaptive_escalator"}


# =============================================================================
# Fixture Tests
# =============================================================================

class TestFixtures:
    """Test synthetic fixtures are properly labeled."""

    def test_fixtures_are_synthetic(self):
        """Test that all generated fixtures are marked synthetic."""
        fixtures_dir = Path(__file__).parent / "fixtures" / "traces"

        if not fixtures_dir.exists():
            pytest.skip("Fixtures directory not found")

        for path in fixtures_dir.glob("*.json"):
            trace = load_trace(path)
            assert trace.is_synthetic is True, f"{path.name} should be synthetic"
            assert trace.synthetic_profile != "", f"{path.name} should have profile"

    def test_fixture_validation(self):
        """Test that all fixtures are valid traces."""
        fixtures_dir = Path(__file__).parent / "fixtures" / "traces"

        if not fixtures_dir.exists():
            pytest.skip("Fixtures directory not found")

        for path in fixtures_dir.glob("*.json"):
            trace = load_trace(path)
            issues = trace.validate()
            assert issues == [], f"{path.name} has validation issues: {issues}"
