"""
Replay Metrics - Deterministic Research Metrics for Policy Comparison.

This module implements deterministic derived metrics for research:
- HDI: Hint Dependency Index
- CSI: Cognitive Strain Index
- APS: Affective Persistence Score
- Persistence Score
- Simulated Coverage Score
- Time-to-Success Proxy
- RQS: Reflection Quality Score (when note text exists)

IMPORTANT: These are deterministic calculations from trace data.
No live online bandit optimization is implemented here.

Usage:
    from replay_metrics import compute_all_metrics, HDIMetric

    metrics = compute_all_metrics(trace, policy_decisions)
    print(metrics.hdi.value)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .trace_schema import LearnerTrace, TraceEvent, EventType


# =============================================================================
# Individual Metric Classes
# =============================================================================

@dataclass
class HDIMetric:
    """
    HDI: Hint Dependency Index

    Measures learner's reliance on hints and escalations.

    COMPUTATION RULES (explicit):
    1. Base hint frequency = hints_requested / total_attempts
    2. Escalation depth factor = average escalation_level / 4 (max)
    3. Explanation rate = explanations_shown / total_problems
    4. Post-explanation penalty = +0.2 per error after explanation
    5. Independent recovery bonus = -0.1 per recovery without hint

    Normalized to 0-1 scale where:
    - 0 = fully independent, no hints needed
    - 1 = fully dependent on hints/explanations

    Formula:
        HDI = (0.3 * hint_freq + 0.3 * escalation_depth + 0.2 * explanation_rate
               + 0.2 * post_explanation_penalty - independent_recovery_bonus)
        clipped to [0, 1]
    """

    value: float = 0.0
    hint_frequency: float = 0.0
    escalation_depth_factor: float = 0.0
    explanation_rate: float = 0.0
    post_explanation_penalty: float = 0.0
    independent_recovery_bonus: float = 0.0

    @classmethod
    def compute(cls, trace: LearnerTrace, decisions: list[dict] | None = None) -> HDIMetric:
        """Compute HDI from trace and optional policy decisions."""
        events = trace.events

        # Count hint requests
        hint_requests = sum(
            1 for e in events
            if e.event_type in (EventType.HINT_REQUESTED.value, EventType.HINT_SHOWN.value)
        )

        # Count explanations
        explanations = sum(
            1 for e in events
            if e.event_type in (EventType.EXPLANATION_REQUESTED.value, EventType.EXPLANATION_SHOWN.value)
        )

        # Count attempts (approximated by problem attempts + errors)
        attempts = sum(
            1 for e in events
            if e.event_type in (EventType.PROBLEM_ATTEMPT.value, EventType.ERROR_RECORDED.value)
        )
        attempts = max(attempts, 1)  # Avoid div by zero

        # Hint frequency
        hint_freq = min(hint_requests / attempts, 1.0)

        # Escalation depth factor
        escalation_levels = []
        for e in events:
            level = e.escalation_level
            if level and level.startswith("L"):
                try:
                    escalation_levels.append(int(level[1:]))
                except ValueError:
                    pass

        avg_escalation = sum(escalation_levels) / max(len(escalation_levels), 1)
        escalation_depth = avg_escalation / 4.0  # Normalize to max L4

        # Explanation rate
        unique_problems = len(trace.get_unique_problems())
        explanation_rate = explanations / max(unique_problems, 1)

        # Post-explanation penalty: errors after explanation
        post_exp_errors = 0
        had_explanation = False
        for e in events:
            if e.event_type == EventType.EXPLANATION_SHOWN.value:
                had_explanation = True
            elif had_explanation and e.error_subtype:
                post_exp_errors += 1

        post_exp_penalty = min(post_exp_errors * 0.2, 0.5)  # Cap at 0.5

        # Independent recovery: solved without hint after error
        independent_recoveries = 0
        in_error = False
        for e in events:
            if e.error_subtype:
                in_error = True
            elif e.event_type == EventType.HINT_REQUESTED.value:
                in_error = False  # Used hint, not independent
            elif e.event_type == EventType.PROBLEM_SOLVED.value and in_error:
                independent_recoveries += 1
                in_error = False

        recovery_bonus = min(independent_recoveries * 0.1, 0.3)  # Cap at 0.3

        # Compute final HDI
        hdi = (
            0.3 * hint_freq +
            0.3 * escalation_depth +
            0.2 * explanation_rate +
            0.2 * post_exp_penalty -
            recovery_bonus
        )
        hdi = max(0.0, min(1.0, hdi))

        return cls(
            value=round(hdi, 4),
            hint_frequency=round(hint_freq, 4),
            escalation_depth_factor=round(escalation_depth, 4),
            explanation_rate=round(explanation_rate, 4),
            post_explanation_penalty=round(post_exp_penalty, 4),
            independent_recovery_bonus=round(recovery_bonus, 4),
        )


@dataclass
class CSIMetric:
    """
    CSI: Cognitive Strain Index

    Normalized strain proxy from learner behavior patterns.

    COMPUTATION RULES (explicit):
    1. Burst error factor: +0.15 per error within 30s of previous error
    2. Rapid retry factor: +0.1 per retry within 10s
    3. Pause penalty: +0.05 per second of pause before escalation (capped at 0.3)
    4. Escalation density: (escalations / problems) * 0.3
    5. Consecutive error bonus: +0.05 per consecutive error beyond 2

    Normalized to 0-1 scale where:
    - 0 = no cognitive strain detected
    - 1 = high cognitive strain

    Formula:
        CSI = (burst_errors * 0.15 + rapid_retries * 0.1 + pause_penalty
               + escalation_density + consecutive_bonus)
        clipped to [0, 1]
    """

    value: float = 0.0
    burst_error_factor: float = 0.0
    rapid_retry_factor: float = 0.0
    pause_penalty: float = 0.0
    escalation_density: float = 0.0
    consecutive_error_bonus: float = 0.0

    @classmethod
    def compute(cls, trace: LearnerTrace, decisions: list[dict] | None = None) -> CSIMetric:
        """Compute CSI from trace."""
        events = trace.events

        # Burst errors: errors within 30s of each other
        burst_errors = 0
        last_error_time = None
        for e in events:
            if e.error_subtype and e.time_since_start is not None:
                if last_error_time is not None:
                    gap = e.time_since_start - last_error_time
                    if gap < 30:
                        burst_errors += 1
                last_error_time = e.time_since_start

        burst_factor = burst_errors * 0.15

        # Rapid retries: actions within 10s
        rapid_retries = 0
        last_action_time = None
        for e in events:
            if e.time_since_start is not None:
                if last_action_time is not None:
                    gap = e.time_since_start - last_action_time
                    if gap < 10:
                        rapid_retries += 1
                last_action_time = e.time_since_start

        retry_factor = rapid_retries * 0.1

        # Pause penalty: long time stuck before escalation
        pause_penalty = 0.0
        for e in events:
            if e.is_escalation_event() and e.time_stuck:
                # Penalty increases with time stuck before escalating
                pause_penalty += min(e.time_stuck * 0.001, 0.1)  # Cap per event
        pause_penalty = min(pause_penalty, 0.3)  # Overall cap

        # Escalation density
        escalations = len(trace.get_escalation_events())
        problems = len(trace.get_unique_problems())
        escalation_dens = (escalations / max(problems, 1)) * 0.3

        # Consecutive error bonus
        max_consecutive = 0
        current_consecutive = 0
        for e in events:
            if e.error_subtype:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            elif e.event_type == EventType.PROBLEM_SOLVED.value:
                current_consecutive = 0

        consecutive_bonus = max(0, (max_consecutive - 2)) * 0.05

        # Compute CSI
        csi = burst_factor + retry_factor + pause_penalty + escalation_dens + consecutive_bonus
        csi = max(0.0, min(1.0, csi))

        return cls(
            value=round(csi, 4),
            burst_error_factor=round(burst_factor, 4),
            rapid_retry_factor=round(retry_factor, 4),
            pause_penalty=round(pause_penalty, 4),
            escalation_density=round(escalation_dens, 4),
            consecutive_error_bonus=round(consecutive_bonus, 4),
        )


@dataclass
class APSMetric:
    """
    APS: Affective Persistence Score

    Measures learner's emotional persistence through struggle.

    COMPUTATION RULES (explicit):
    1. Repeated identical errors: -0.15 per repeat (frustration indicator)
    2. Rapid escalation: -0.1 per escalation within 20s (giving up quickly)
    3. Problem switching: -0.2 per switch without solving (avoidance)
    4. Idle periods: -0.05 per 60s idle (disengagement)
    5. Burst clusters: -0.1 per 3+ errors in 60s window (overwhelm)
    6. Recovery streak: +0.1 per recovery after 2+ errors (resilience)

    Normalized to 0-1 scale where:
    - 0 = low persistence (frequent giving up, avoidance)
    - 1 = high persistence (resilient through struggle)

    Formula:
        APS = 0.5 + (recovery_streak * 0.1 - repeated_errors * 0.15
                     - rapid_escalations * 0.1 - problem_switches * 0.2
                     - idle_penalty - burst_penalty)
        clipped to [0, 1]
    """

    value: float = 0.5
    repeated_error_penalty: float = 0.0
    rapid_escalation_penalty: float = 0.0
    problem_switch_penalty: float = 0.0
    idle_penalty: float = 0.0
    burst_penalty: float = 0.0
    recovery_bonus: float = 0.0

    @classmethod
    def compute(cls, trace: LearnerTrace, decisions: list[dict] | None = None) -> APSMetric:
        """Compute APS from trace."""
        events = trace.events

        # Repeated identical errors
        repeated_errors = 0
        last_subtype = None
        for e in events:
            if e.error_subtype:
                if e.error_subtype == last_subtype:
                    repeated_errors += 1
                last_subtype = e.error_subtype

        repeated_penalty = repeated_errors * 0.15

        # Rapid escalations (within 20s of error)
        rapid_escalations = 0
        last_error_time = None
        for e in events:
            if e.error_subtype:
                last_error_time = e.time_since_start
            elif e.is_escalation_event() and last_error_time:
                if e.time_since_start and (e.time_since_start - last_error_time) < 20:
                    rapid_escalations += 1

        escalation_penalty = rapid_escalations * 0.1

        # Problem switching without solving
        switches = 0
        solved_problems = set()
        current_problem = None
        for e in events:
            if e.problem_id != current_problem:
                if current_problem and current_problem not in solved_problems:
                    switches += 1
                current_problem = e.problem_id
            if e.event_type == EventType.PROBLEM_SOLVED.value:
                solved_problems.add(e.problem_id)

        switch_penalty = switches * 0.2

        # Idle periods (time_since_last_action > 60s)
        idle_periods = sum(
            1 for e in events
            if e.time_since_last_action and e.time_since_last_action > 60
        )
        idle_penalty = idle_periods * 0.05

        # Burst clusters (3+ errors in 60s window)
        burst_penalty = 0.0
        error_times = [
            e.time_since_start for e in events
            if e.error_subtype and e.time_since_start is not None
        ]
        for i, t1 in enumerate(error_times):
            window_errors = sum(1 for t2 in error_times if 0 <= (t2 - t1) <= 60)
            if window_errors >= 3:
                burst_penalty += 0.1
                break  # Only count once per trace

        # Recovery streaks (solved after 2+ errors on same problem)
        recoveries = 0
        problem_errors: dict[str, int] = {}
        for e in events:
            if e.error_subtype:
                problem_errors[e.problem_id] = problem_errors.get(e.problem_id, 0) + 1
            elif e.event_type == EventType.PROBLEM_SOLVED.value:
                if problem_errors.get(e.problem_id, 0) >= 2:
                    recoveries += 1

        recovery_bonus = recoveries * 0.1

        # Compute APS starting from neutral 0.5
        aps = 0.5 + recovery_bonus - repeated_penalty - escalation_penalty - switch_penalty - idle_penalty - burst_penalty
        aps = max(0.0, min(1.0, aps))

        return cls(
            value=round(aps, 4),
            repeated_error_penalty=round(repeated_penalty, 4),
            rapid_escalation_penalty=round(escalation_penalty, 4),
            problem_switch_penalty=round(switch_penalty, 4),
            idle_penalty=round(idle_penalty, 4),
            burst_penalty=round(burst_penalty, 4),
            recovery_bonus=round(recovery_bonus, 4),
        )


@dataclass
class PersistenceScoreMetric:
    """
    Persistence Score: Consecutive repeated subtype behavior.

    Simple metric tracking how long a learner persists with the same
    error pattern before changing strategy.

    COMPUTATION RULES:
    - Count consecutive identical error subtypes
    - Normalize to 0-1 based on max observed (capped at 5)
    - Higher = more persistence with same error pattern
    """

    value: float = 0.0
    max_consecutive_repeats: int = 0
    total_unique_subtypes: int = 0

    @classmethod
    def compute(cls, trace: LearnerTrace) -> PersistenceScoreMetric:
        """Compute persistence score from trace."""
        events = trace.events

        max_repeats = 0
        current_repeats = 0
        last_subtype = None
        unique_subtypes = set()

        for e in events:
            if e.error_subtype:
                unique_subtypes.add(e.error_subtype)
                if e.error_subtype == last_subtype:
                    current_repeats += 1
                    max_repeats = max(max_repeats, current_repeats)
                else:
                    current_repeats = 1
                    last_subtype = e.error_subtype

        # Normalize (capped at 5 repeats = 1.0)
        score = min(max_repeats / 5.0, 1.0)

        return cls(
            value=round(score, 4),
            max_consecutive_repeats=max_repeats,
            total_unique_subtypes=len(unique_subtypes),
        )


@dataclass
class SimulatedCoverageScoreMetric:
    """
    Simulated Coverage Score: Concept/unit exposure from replay decisions.

    Estimates coverage based on concept exposure and note-taking.

    COMPUTATION RULES:
    - Base: unique_concepts / total_available_concepts
    - Bonus: +0.1 per saved unit (capped at 0.3)
    - Bonus: +0.1 if notes taken (capped at 0.2)
    - Penalty: -0.1 per concept abandoned without solving
    """

    value: float = 0.0
    unique_concepts_exposed: int = 0
    saved_units_count: int = 0
    notes_taken_count: int = 0
    concepts_abandoned: int = 0

    @classmethod
    def compute(
        cls,
        trace: LearnerTrace,
        total_available_concepts: int = 10,
    ) -> SimulatedCoverageScoreMetric:
        """Compute simulated coverage from trace."""
        events = trace.events

        unique_concepts = trace.get_unique_concepts()
        concepts_exposed = len(unique_concepts)

        # Count saved units
        saved_units = sum(
            1 for e in events
            if e.event_type == EventType.SAVE_UNIT.value
        )

        # Count notes
        notes_count = sum(
            1 for e in events
            if e.event_type == EventType.SAVE_NOTE.value and e.note_text
        )

        # Count abandoned concepts (problems without solve)
        attempted = set()
        solved = set()
        for e in events:
            if e.concept_id:
                attempted.add(e.concept_id)
            if e.event_type == EventType.PROBLEM_SOLVED.value and e.concept_id:
                solved.add(e.concept_id)
        abandoned = len(attempted - solved)

        # Compute score
        base_coverage = concepts_exposed / max(total_available_concepts, 1)
        saved_bonus = min(saved_units * 0.1, 0.3)
        notes_bonus = min(notes_count * 0.1, 0.2)
        abandon_penalty = min(abandoned * 0.1, 0.3)

        score = base_coverage + saved_bonus + notes_bonus - abandon_penalty
        score = max(0.0, min(1.0, score))

        return cls(
            value=round(score, 4),
            unique_concepts_exposed=concepts_exposed,
            saved_units_count=saved_units,
            notes_taken_count=notes_count,
            concepts_abandoned=abandoned,
        )


@dataclass
class TimeToSuccessMetric:
    """
    Time-to-Success Proxy: Deterministic from timestamps.

    Measures time to solve problems successfully.

    COMPUTATION RULES:
    - For each solved problem: time from first attempt to solve
    - Average across all solved problems
    - Normalized: <60s = 1.0, >600s = 0.0, linear in between
    """

    value: float = 0.0  # Normalized score (higher = faster)
    average_seconds: float = 0.0
    total_solved: int = 0
    problem_times: dict[str, float] = field(default_factory=dict)

    @classmethod
    def compute(cls, trace: LearnerTrace) -> TimeToSuccessMetric:
        """Compute time-to-success from trace."""
        events = trace.events

        # Track first attempt and solve time per problem
        problem_first_attempt: dict[str, float] = {}
        problem_solve_time: dict[str, float] = {}

        for e in events:
            if e.problem_id and e.time_since_start is not None:
                if e.problem_id not in problem_first_attempt:
                    problem_first_attempt[e.problem_id] = e.time_since_start

                if e.event_type == EventType.PROBLEM_SOLVED.value:
                    problem_solve_time[e.problem_id] = e.time_since_start

        # Calculate times
        solve_times = []
        for prob, solve_t in problem_solve_time.items():
            if prob in problem_first_attempt:
                duration = solve_t - problem_first_attempt[prob]
                if duration >= 0:
                    solve_times.append(duration)

        if not solve_times:
            return cls(value=0.0, average_seconds=0.0, total_solved=0)

        avg_time = sum(solve_times) / len(solve_times)

        # Normalize: <60s = 1.0, >600s = 0.0
        normalized = 1.0 - ((avg_time - 60) / 540)
        normalized = max(0.0, min(1.0, normalized))

        return cls(
            value=round(normalized, 4),
            average_seconds=round(avg_time, 2),
            total_solved=len(solve_times),
            problem_times={k: round(v, 2) for k, v in problem_solve_time.items()},
        )


@dataclass
class RQSMetric:
    """
    RQS: Reflection Quality Score (when note text exists)

    Analyzes note text quality for reflection depth.

    COMPUTATION RULES:
    - Null if no note text exists
    - Word count: 1-5 words = 0.2, 6-20 = 0.5, 21+ = 0.8
    - Question marks: +0.1 per question (capped at 0.2)
    - Keywords: +0.1 per reflective keyword ("why", "because", "understand", "realize")
    - Code snippets: +0.2 if contains code-like content

    Formula: base_word_score + questions_bonus + keywords_bonus + code_bonus
    capped at [0, 1]
    """

    value: float | None = None
    note_count: int = 0
    avg_word_count: float = 0.0
    question_count: int = 0
    reflective_keyword_count: int = 0
    has_code_snippet: bool = False

    REFLECTIVE_KEYWORDS = frozenset([
        "why", "because", "understand", "realize", "realized",
        "think", "thought", "learned", "confused", "clarified",
        "mistake", "error", "fix", "solution", "approach",
    ])

    @classmethod
    def compute(cls, trace: LearnerTrace) -> RQSMetric:
        """Compute RQS from note text in trace."""
        events = trace.events

        # Extract notes with text
        notes = [
            e.note_text for e in events
            if e.event_type == EventType.SAVE_NOTE.value and e.note_text
        ]

        if not notes:
            return cls(value=None, note_count=0)

        total_score = 0.0
        total_questions = 0
        total_keywords = 0
        has_code = False

        for note in notes:
            words = note.lower().split()
            word_count = len(words)

            # Base word score
            if word_count <= 5:
                word_score = 0.2
            elif word_count <= 20:
                word_score = 0.5
            else:
                word_score = 0.8

            # Question bonus
            questions = note.count("?")
            total_questions += questions
            question_bonus = min(questions * 0.1, 0.2)

            # Keyword bonus
            keyword_hits = sum(1 for kw in cls.REFLECTIVE_KEYWORDS if kw in note.lower())
            total_keywords += keyword_hits
            keyword_bonus = min(keyword_hits * 0.1, 0.3)

            # Code detection (simple heuristic: semicolons, brackets, code-like words)
            code_indicators = [";", "{", "}", "select", "from", "where", "="]
            if any(ind in note for ind in code_indicators):
                has_code = True
                code_bonus = 0.2
            else:
                code_bonus = 0.0

            note_score = word_score + question_bonus + keyword_bonus + code_bonus
            total_score += min(note_score, 1.0)

        avg_score = total_score / len(notes)
        avg_words = sum(len(n.split()) for n in notes) / len(notes)

        return cls(
            value=round(avg_score, 4),
            note_count=len(notes),
            avg_word_count=round(avg_words, 2),
            question_count=total_questions,
            reflective_keyword_count=total_keywords,
            has_code_snippet=has_code,
        )


# =============================================================================
# Combined Metrics
# =============================================================================

@dataclass
class AllMetrics:
    """Container for all computed metrics."""

    hdi: HDIMetric
    csi: CSIMetric
    aps: APSMetric
    persistence: PersistenceScoreMetric
    coverage: SimulatedCoverageScoreMetric
    time_to_success: TimeToSuccessMetric
    rqs: RQSMetric

    # Metadata
    trace_id: str = ""
    policy_id: str = ""
    computed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert all metrics to nested dictionary."""
        return {
            "trace_id": self.trace_id,
            "policy_id": self.policy_id,
            "computed_at": self.computed_at,
            "metrics": {
                "hdi": {
                    "value": self.hdi.value,
                    "hint_frequency": self.hdi.hint_frequency,
                    "escalation_depth": self.hdi.escalation_depth_factor,
                    "explanation_rate": self.hdi.explanation_rate,
                },
                "csi": {
                    "value": self.csi.value,
                    "burst_error": self.csi.burst_error_factor,
                    "rapid_retry": self.csi.rapid_retry_factor,
                    "pause_penalty": self.csi.pause_penalty,
                },
                "aps": {
                    "value": self.aps.value,
                    "recovery_bonus": self.aps.recovery_bonus,
                    "repeated_error_penalty": self.aps.repeated_error_penalty,
                },
                "persistence": {
                    "value": self.persistence.value,
                    "max_consecutive": self.persistence.max_consecutive_repeats,
                },
                "coverage": {
                    "value": self.coverage.value,
                    "concepts_exposed": self.coverage.unique_concepts_exposed,
                    "saved_units": self.coverage.saved_units_count,
                },
                "time_to_success": {
                    "value": self.time_to_success.value,
                    "avg_seconds": self.time_to_success.average_seconds,
                    "problems_solved": self.time_to_success.total_solved,
                },
                "rqs": {
                    "value": self.rqs.value,
                    "note_count": self.rqs.note_count,
                },
            },
        }


def compute_all_metrics(
    trace: LearnerTrace,
    policy_decisions: list[dict] | None = None,
    total_available_concepts: int = 10,
) -> AllMetrics:
    """
    Compute all metrics for a trace.

    Args:
        trace: The learner trace
        policy_decisions: Optional policy decisions from replay
        total_available_concepts: Total concepts available for coverage calc

    Returns:
        AllMetrics containing all computed values
    """
    return AllMetrics(
        hdi=HDIMetric.compute(trace, policy_decisions),
        csi=CSIMetric.compute(trace, policy_decisions),
        aps=APSMetric.compute(trace, policy_decisions),
        persistence=PersistenceScoreMetric.compute(trace),
        coverage=SimulatedCoverageScoreMetric.compute(trace, total_available_concepts),
        time_to_success=TimeToSuccessMetric.compute(trace),
        rqs=RQSMetric.compute(trace),
        trace_id=trace.trace_id,
    )
