"""
Learner Trace Schema - Minimal deterministic event schema for replay.

This module defines a small, explicit schema for learner interaction traces
that can be replayed under different policies for comparison.

IMPORTANT: Traces are synthetic/minimal fixtures unless explicitly labeled otherwise.
No real learner data is stored in this repository.

Usage:
    from trace_schema import TraceEvent, LearnerTrace, load_trace, save_trace

    trace = load_trace(Path("traces/learner_001.json"))
    for event in trace.events:
        print(event.event_type, event.problem_id)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


# =============================================================================
# Enums
# =============================================================================

class EventType(str, Enum):
    """Types of learner interaction events."""

    PROBLEM_ATTEMPT = "problem_attempt"
    PROBLEM_SOLVED = "problem_solved"
    PROBLEM_ABANDONED = "problem_abandoned"
    HINT_REQUESTED = "hint_requested"
    HINT_SHOWN = "hint_shown"
    EXPLANATION_REQUESTED = "explanation_requested"
    EXPLANATION_SHOWN = "explanation_shown"
    ESCALATION_TRIGGERED = "escalation_triggered"
    ERROR_RECORDED = "error_recorded"
    SAVE_NOTE = "save_note"
    SAVE_UNIT = "save_unit"
    CONCEPT_SWITCH = "concept_switch"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    IDLE_TIMEOUT = "idle_timeout"


class ErrorSubtype(str, Enum):
    """Common error subtypes for SQL/problem-solving contexts."""

    # Syntax errors
    MISSING_COMMA_IN_SELECT = "missing_comma_in_select"
    SELECT_STAR_MISUSE = "select_star_misuse"
    UNCLOSED_PARENTHESIS = "unclosed_parenthesis"
    MISSING_SEMICOLON = "missing_semicolon"
    QUOTE_MISMATCH = "quote_mismatch"

    # Logic errors
    WRONG_TABLE = "wrong_table"
    WRONG_COLUMN = "wrong_column"
    WRONG_CONDITION = "wrong_condition"
    MISSING_WHERE_CLAUSE = "missing_where_clause"
    INCORRECT_AGGREGATE = "incorrect_aggregate"

    # Concept errors
    JOIN_CONFUSION = "join_confusion"
    GROUP_BY_MISUNDERSTANDING = "group_by_misunderstanding"
    SUBQUERY_CONFUSION = "subquery_confusion"
    ALIAS_MISUSE = "alias_misuse"

    # Unknown/other
    UNKNOWN_ERROR = "unknown_error"
    RUNTIME_ERROR = "runtime_error"
    TIMEOUT_ERROR = "timeout_error"


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class TraceEvent:
    """
    A single learner interaction event in a trace.

    This is the atomic unit of replay analysis. Events are ordered and
    contain all context needed to reconstruct learner state at any point.
    """

    # Unique identifier for this event
    event_id: str

    # ISO 8601 timestamp (UTC)
    timestamp: str

    # Learner and session identifiers
    learner_id: str
    session_id: str

    # Problem context
    problem_id: str
    concept_id: str | None = None

    # Event classification
    event_type: str = "problem_attempt"  # EventType value

    # Error context (nullable when not applicable)
    error_subtype: str | None = None
    error_message: str | None = None

    # Attempt tracking
    attempt_index: int = 0

    # Hint/escalation tracking
    hint_count: int = 0
    escalation_level: str = "L0"  # L0=none, L1=hint, L2=explanation, L3=deep-explanation

    # Time tracking (seconds since problem start or last event)
    time_since_start: float = 0.0
    time_since_last_action: float = 0.0
    time_stuck: float = 0.0  # Time without progress (for escalation decisions)

    # Content references
    unit_id: str | None = None
    note_text: str | None = None

    # Extended metadata for replay-specific fields
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TraceEvent:
        """Create from dictionary with validation."""
        # Filter to only known fields
        known_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    def is_error_event(self) -> bool:
        """Check if this event represents an error state."""
        return self.error_subtype is not None or self.event_type in {
            EventType.ERROR_RECORDED.value,
            EventType.PROBLEM_ABANDONED.value,
        }

    def is_escalation_event(self) -> bool:
        """Check if this event represents an escalation."""
        return self.event_type in {
            EventType.HINT_REQUESTED.value,
            EventType.HINT_SHOWN.value,
            EventType.EXPLANATION_REQUESTED.value,
            EventType.EXPLANATION_SHOWN.value,
            EventType.ESCALATION_TRIGGERED.value,
        }

    def get_timestamp_dt(self) -> datetime:
        """Parse timestamp to datetime object."""
        # Handle various ISO formats
        ts = self.timestamp.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(ts)
        except ValueError:
            # Fallback to current time if parsing fails
            return datetime.now(timezone.utc)


@dataclass
class LearnerTrace:
    """
    A complete learner trace containing ordered events.

    This is the top-level container for replay analysis.
    All events are ordered by timestamp for deterministic replay.
    """

    # Schema version for compatibility
    schema_version: str = "1.0.0"

    # Trace metadata
    trace_id: str = ""
    learner_id: str = "anonymous"
    session_id: str = ""

    # Source labeling (IMPORTANT: all fixtures are synthetic unless labeled)
    is_synthetic: bool = True
    synthetic_profile: str = ""  # e.g., "struggling_with_joins", "fast_learner"
    source_system: str = "pdf_helper_fixture"

    # Creation timestamp
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # Ordered event sequence
    events: list[TraceEvent] = field(default_factory=list)

    # Session-level configuration (merged with flags during replay)
    session_config: dict[str, Any] = field(default_factory=dict)

    # Trace-level annotations for research
    annotations: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert events to dicts
        data["events"] = [e.to_dict() for e in self.events]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LearnerTrace:
        """Create from dictionary with event reconstruction."""
        events_data = data.pop("events", [])
        trace = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        trace.events = [TraceEvent.from_dict(e) for e in events_data]
        return trace

    def save(self, path: Path) -> None:
        """Save trace to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    def get_events_for_problem(self, problem_id: str) -> list[TraceEvent]:
        """Get all events for a specific problem."""
        return [e for e in self.events if e.problem_id == problem_id]

    def get_error_events(self) -> list[TraceEvent]:
        """Get all error events in this trace."""
        return [e for e in self.events if e.is_error_event()]

    def get_escalation_events(self) -> list[TraceEvent]:
        """Get all escalation events in this trace."""
        return [e for e in self.events if e.is_escalation_event()]

    def get_unique_problems(self) -> set[str]:
        """Get set of unique problem IDs in this trace."""
        return {e.problem_id for e in self.events if e.problem_id}

    def get_unique_concepts(self) -> set[str]:
        """Get set of unique concept IDs in this trace."""
        return {e.concept_id for e in self.events if e.concept_id}

    def get_duration_seconds(self) -> float:
        """Calculate total trace duration in seconds."""
        if len(self.events) < 2:
            return 0.0
        first = self.events[0].get_timestamp_dt()
        last = self.events[-1].get_timestamp_dt()
        return (last - first).total_seconds()

    def validate(self) -> list[str]:
        """Validate trace and return list of issues (empty if valid)."""
        issues = []

        if not self.events:
            issues.append("Trace has no events")
            return issues

        # Check required fields on all events
        for i, event in enumerate(self.events):
            if not event.event_id:
                issues.append(f"Event {i}: missing event_id")
            if not event.timestamp:
                issues.append(f"Event {i}: missing timestamp")
            if not event.learner_id:
                issues.append(f"Event {i}: missing learner_id")
            # problem_id is optional for session-level events
            if not event.problem_id and event.event_type not in (
                EventType.SESSION_START.value,
                EventType.SESSION_END.value,
            ):
                issues.append(f"Event {i}: missing problem_id")

        # Check timestamp ordering
        timestamps = [e.get_timestamp_dt() for e in self.events]
        for i in range(1, len(timestamps)):
            if timestamps[i] < timestamps[i - 1]:
                issues.append(f"Event {i}: timestamp out of order")

        return issues


# =============================================================================
# I/O Functions
# =============================================================================

def load_trace(path: Path) -> LearnerTrace:
    """Load a learner trace from JSON file."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return LearnerTrace.from_dict(data)


def save_trace(trace: LearnerTrace, path: Path) -> None:
    """Save a learner trace to JSON file."""
    trace.save(path)


def load_traces_from_directory(dir_path: Path) -> list[LearnerTrace]:
    """Load all traces from a directory (JSON files only)."""
    traces = []
    if not dir_path.exists():
        return traces

    for path in dir_path.glob("*.json"):
        try:
            trace = load_trace(path)
            traces.append(trace)
        except (json.JSONDecodeError, KeyError) as e:
            # Skip invalid files
            continue

    return traces


# =============================================================================
# Synthetic Fixture Builders
# =============================================================================

def make_synthetic_trace(
    trace_id: str,
    profile: str,
    num_problems: int = 3,
    error_rate: float = 0.5,
) -> LearnerTrace:
    """
    Create a synthetic trace for testing and replay.

    Args:
        trace_id: Unique identifier for this trace
        profile: Profile name (e.g., "struggling", "fast_learner")
        num_problems: Number of problems to simulate
        error_rate: Probability of error per attempt (0-1)

    Returns:
        A synthetic LearnerTrace with labeled synthetic data
    """
    from random import Random

    rng = Random(42)  # Deterministic seed
    base_time = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    events = []
    learner_id = f"synthetic_{profile}_{trace_id}"
    session_id = f"session_{trace_id}"

    problems = [f"problem_{i:03d}" for i in range(num_problems)]
    concepts = [f"concept_{i:03d}" for i in range(num_problems)]

    event_counter = 0

    # Session start
    events.append(
        TraceEvent(
            event_id=f"evt_{event_counter:04d}",
            timestamp=base_time.isoformat(),
            learner_id=learner_id,
            session_id=session_id,
            problem_id="",
            event_type=EventType.SESSION_START.value,
        )
    )
    event_counter += 1

    for prob_idx, (problem_id, concept_id) in enumerate(zip(problems, concepts)):
        problem_start = base_time.timestamp() + prob_idx * 300  # 5 min per problem

        # Problem attempt
        has_error = rng.random() < error_rate
        num_attempts = rng.randint(2, 5) if has_error else 1

        for attempt in range(num_attempts):
            attempt_time = problem_start + attempt * 30  # 30 sec per attempt

            # Record error on all but last attempt if struggling
            current_error = None
            if has_error and attempt < num_attempts - 1:
                error_types = [e.value for e in ErrorSubtype if e != ErrorSubtype.UNKNOWN_ERROR]
                current_error = rng.choice(error_types)

            events.append(
                TraceEvent(
                    event_id=f"evt_{event_counter:04d}",
                    timestamp=datetime.fromtimestamp(attempt_time, tz=timezone.utc).isoformat(),
                    learner_id=learner_id,
                    session_id=session_id,
                    problem_id=problem_id,
                    concept_id=concept_id,
                    event_type=EventType.ERROR_RECORDED.value if current_error else EventType.PROBLEM_ATTEMPT.value,
                    error_subtype=current_error,
                    attempt_index=attempt,
                    time_since_start=attempt * 30,
                )
            )
            event_counter += 1

            # Maybe request hint
            if current_error and rng.random() < 0.7:
                hint_time = attempt_time + 10
                events.append(
                    TraceEvent(
                        event_id=f"evt_{event_counter:04d}",
                        timestamp=datetime.fromtimestamp(hint_time, tz=timezone.utc).isoformat(),
                        learner_id=learner_id,
                        session_id=session_id,
                        problem_id=problem_id,
                        concept_id=concept_id,
                        event_type=EventType.HINT_REQUESTED.value,
                        attempt_index=attempt,
                        hint_count=1,
                        escalation_level="L1",
                        time_since_start=attempt * 30 + 10,
                        time_since_last_action=10,
                    )
                )
                event_counter += 1

        # Problem solved or abandoned
        final_time = problem_start + num_attempts * 30 + 10
        solved = not has_error or rng.random() < 0.6  # 60% eventually solve

        events.append(
            TraceEvent(
                event_id=f"evt_{event_counter:04d}",
                timestamp=datetime.fromtimestamp(final_time, tz=timezone.utc).isoformat(),
                learner_id=learner_id,
                session_id=session_id,
                problem_id=problem_id,
                concept_id=concept_id,
                event_type=EventType.PROBLEM_SOLVED.value if solved else EventType.PROBLEM_ABANDONED.value,
                attempt_index=num_attempts - 1,
                time_since_start=num_attempts * 30 + 10,
            )
        )
        event_counter += 1

    # Session end
    final_timestamp = datetime.fromtimestamp(
        base_time.timestamp() + num_problems * 300 + 60,
        tz=timezone.utc
    )
    events.append(
        TraceEvent(
            event_id=f"evt_{event_counter:04d}",
            timestamp=final_timestamp.isoformat(),
            learner_id=learner_id,
            session_id=session_id,
            problem_id="",
            event_type=EventType.SESSION_END.value,
        )
    )

    return LearnerTrace(
        trace_id=trace_id,
        learner_id=learner_id,
        session_id=session_id,
        is_synthetic=True,
        synthetic_profile=profile,
        source_system="pdf_helper_synthetic_generator",
        events=events,
        annotations={
            "generated_profile": profile,
            "num_problems": num_problems,
            "target_error_rate": error_rate,
            "generation_seed": 42,
        },
    )


def get_minimal_valid_trace() -> LearnerTrace:
    """Return a minimal valid trace for testing validation."""
    base_time = datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    return LearnerTrace(
        trace_id="minimal_test",
        learner_id="test_learner",
        session_id="test_session",
        is_synthetic=True,
        synthetic_profile="minimal",
        events=[
            TraceEvent(
                event_id="evt_0001",
                timestamp=base_time.isoformat(),
                learner_id="test_learner",
                session_id="test_session",
                problem_id="test_problem",
                concept_id="test_concept",
                event_type=EventType.PROBLEM_ATTEMPT.value,
                attempt_index=0,
            ),
        ],
    )
