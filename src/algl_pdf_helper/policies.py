"""
Formal Policies for Trace Replay - Deterministic Escalation Decision Rules.

This module defines 3+ formal policies for replay comparison:
1. fast_escalator - Aggressive escalation on early signs of struggle
2. slow_escalator - Conservative escalation, favors independent solving
3. adaptive_escalator - Context-aware escalation based on learner history

Each policy has EXPLICIT decision rules, not vague prose.
Rules use: error count, time stuck, hint count, repeated subtypes, prior recovery.

Usage:
    from policies import get_default_policies, EscalationPolicy

    policies = get_default_policies()
    for policy in policies:
        decision = policy.should_escalate(learner_state)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


# =============================================================================
# Enums and Types
# =============================================================================

class EscalationLevel(str, Enum):
    """Escalation levels from L0 (none) to L4 (max)."""

    L0_NONE = "L0"           # No escalation, learner working independently
    L1_HINT = "L1"           # Light hint (Socratic, nudge)
    L2_EXPLANATION = "L2"    # Direct explanation
    L3_DEEP_EXPLANATION = "L3"  # Detailed explanation with examples
    L4_MAX = "L4"            # Maximum support (worked example, concept review)


class EscalationAction(str, Enum):
    """Specific actions the policy can recommend."""

    WAIT = "wait"                           # Do nothing, observe
    OFFER_HINT = "offer_hint"               # Make hint available
    SHOW_HINT = "show_hint"                 # Display hint automatically
    OFFER_EXPLANATION = "offer_explanation"
    SHOW_EXPLANATION = "show_explanation"
    ESCALATE_TO_L3 = "escalate_to_l3"
    ESCALATE_TO_L4 = "escalate_to_l4"
    SWITCH_CONCEPT = "switch_concept"       # Recommend concept switch
    END_SESSION = "end_session"             # Recommend break


# =============================================================================
# Learner State (input to policy decisions)
# =============================================================================

@dataclass
class LearnerState:
    """
    Current learner state for policy decision-making.

    This is computed from trace history during replay.
    """

    # Identifiers
    learner_id: str = ""
    session_id: str = ""
    problem_id: str = ""
    concept_id: str | None = None

    # Error tracking
    total_errors: int = 0
    consecutive_errors: int = 0
    current_error_subtype: str | None = None
    error_subtypes_seen: list[str] = field(default_factory=list)
    repeated_same_subtype: bool = False  # Same error twice in a row

    # Time tracking (seconds)
    time_on_problem: float = 0.0
    time_since_last_action: float = 0.0
    time_stuck: float = 0.0  # Time without progress

    # Hint/escalation history
    hints_requested: int = 0
    hints_shown: int = 0
    explanations_shown: int = 0
    current_escalation_level: str = EscalationLevel.L0_NONE.value

    # Recovery tracking
    prior_recovery_count: int = 0  # How many times recovered from errors
    prior_escalation_success: bool = True  # Did past escalations help

    # Session context
    problems_attempted: int = 0
    problems_solved: int = 0
    concepts_attempted: set[str] = field(default_factory=set)

    # Experimental flags (from session config)
    flags: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "learner_id": self.learner_id,
            "problem_id": self.problem_id,
            "concept_id": self.concept_id,
            "total_errors": self.total_errors,
            "consecutive_errors": self.consecutive_errors,
            "current_error_subtype": self.current_error_subtype,
            "repeated_same_subtype": self.repeated_same_subtype,
            "time_on_problem": self.time_on_problem,
            "time_stuck": self.time_stuck,
            "hints_requested": self.hints_requested,
            "hints_shown": self.hints_shown,
            "explanations_shown": self.explanations_shown,
            "current_escalation_level": self.current_escalation_level,
        }


# =============================================================================
# Policy Decision Output
# =============================================================================

@dataclass
class EscalationDecision:
    """Output from a policy decision."""

    # What action to take
    action: str  # EscalationAction value
    target_level: str  # EscalationLevel value

    # Policy metadata
    policy_id: str = ""
    policy_version: str = "1.0.0"

    # Decision explanation (for logging/research)
    trigger_reason: str = ""  # Why this decision was made
    rule_applied: str = ""    # Which rule triggered

    # Metrics at decision time
    error_count_at_decision: int = 0
    time_to_escalation: float = 0.0  # Seconds from problem start

    # Flag fields for research logging
    strategy_assigned: str = ""  # Label for strategy group
    reward_value: float | None = None  # Simulated reward (for replay comparison)
    strategy_updated: bool = False  # Whether strategy changed

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action": self.action,
            "target_level": self.target_level,
            "policy_id": self.policy_id,
            "policy_version": self.policy_version,
            "trigger_reason": self.trigger_reason,
            "rule_applied": self.rule_applied,
            "error_count_at_decision": self.error_count_at_decision,
            "time_to_escalation": self.time_to_escalation,
            "strategy_assigned": self.strategy_assigned,
            "reward_value": self.reward_value,
            "strategy_updated": self.strategy_updated,
        }


# =============================================================================
# Policy Base Class
# =============================================================================

@dataclass
class EscalationPolicy:
    """
    A formal escalation policy with deterministic decision rules.

    Each policy has:
    - policy_id / version for tracking
    - description for humans
    - decision_function that implements the rules
    """

    policy_id: str
    version: str
    description: str
    strategy_label: str  # e.g., "aggressive", "conservative", "adaptive"

    # The core decision function
    decision_function: Callable[[LearnerState], EscalationDecision] = field(
        default=lambda state: EscalationDecision(
            action=EscalationAction.WAIT.value,
            target_level=EscalationLevel.L0_NONE.value,
        )
    )

    def should_escalate(self, state: LearnerState) -> EscalationDecision:
        """Apply this policy to learner state."""
        decision = self.decision_function(state)
        decision.policy_id = self.policy_id
        decision.policy_version = self.version
        decision.strategy_assigned = self.strategy_label
        return decision

    def to_dict(self) -> dict[str, Any]:
        """Policy metadata (not the function)."""
        return {
            "policy_id": self.policy_id,
            "version": self.version,
            "description": self.description,
            "strategy_label": self.strategy_label,
        }


# =============================================================================
# Policy 1: Fast Escalator (Aggressive)
# =============================================================================

def _fast_escalator_decision(state: LearnerState) -> EscalationDecision:
    """
    FAST ESCALATOR - Aggressive escalation rules.

    Strategy: Intervene early to prevent frustration. Speed over independence.

    EXPLICIT RULES:
    1. First error (any) -> L1 hint
    2. Second consecutive error -> L2 explanation
    3. Third consecutive error OR repeated subtype -> L3 deep explanation
    4. Time stuck > 60s -> Escalate one level
    5. Hint already requested once -> Show next level automatically
    6. Fourth error OR time stuck > 120s -> L4 max support
    """

    current_level = state.current_escalation_level
    base_time = state.time_on_problem

    # Rule 3/6: Check for repeated same subtype (high priority)
    if state.repeated_same_subtype and state.consecutive_errors >= 2:
        return EscalationDecision(
            action=EscalationAction.ESCALATE_TO_L3.value,
            target_level=EscalationLevel.L3_DEEP_EXPLANATION.value,
            trigger_reason="repeated_same_error_subtype",
            rule_applied="fast_escalator_rule_3",
            error_count_at_decision=state.total_errors,
            time_to_escalation=base_time,
        )

    # Rule 6: Max support triggers
    if state.consecutive_errors >= 4 or state.time_stuck > 120:
        return EscalationDecision(
            action=EscalationAction.ESCALATE_TO_L4.value,
            target_level=EscalationLevel.L4_MAX.value,
            trigger_reason="max_strain_detected",
            rule_applied="fast_escalator_rule_6",
            error_count_at_decision=state.total_errors,
            time_to_escalation=base_time,
        )

    # Rule 3: Third error
    if state.consecutive_errors >= 3:
        return EscalationDecision(
            action=EscalationAction.ESCALATE_TO_L3.value,
            target_level=EscalationLevel.L3_DEEP_EXPLANATION.value,
            trigger_reason="third_consecutive_error",
            rule_applied="fast_escalator_rule_3",
            error_count_at_decision=state.total_errors,
            time_to_escalation=base_time,
        )

    # Rule 4: Time stuck > 60s
    if state.time_stuck > 60 and current_level == EscalationLevel.L0_NONE.value:
        return EscalationDecision(
            action=EscalationAction.SHOW_HINT.value,
            target_level=EscalationLevel.L1_HINT.value,
            trigger_reason="time_stuck_threshold",
            rule_applied="fast_escalator_rule_4",
            error_count_at_decision=state.total_errors,
            time_to_escalation=base_time,
        )

    # Rule 5: Hint requested -> auto-escalate
    if state.hints_requested > 0 and current_level == EscalationLevel.L0_NONE.value:
        return EscalationDecision(
            action=EscalationAction.SHOW_HINT.value,
            target_level=EscalationLevel.L1_HINT.value,
            trigger_reason="hint_requested",
            rule_applied="fast_escalator_rule_5",
            error_count_at_decision=state.total_errors,
            time_to_escalation=base_time,
        )

    # Rule 2: Second error
    if state.consecutive_errors >= 2:
        return EscalationDecision(
            action=EscalationAction.SHOW_EXPLANATION.value,
            target_level=EscalationLevel.L2_EXPLANATION.value,
            trigger_reason="second_consecutive_error",
            rule_applied="fast_escalator_rule_2",
            error_count_at_decision=state.total_errors,
            time_to_escalation=base_time,
        )

    # Rule 1: First error
    if state.consecutive_errors >= 1 and current_level == EscalationLevel.L0_NONE.value:
        return EscalationDecision(
            action=EscalationAction.OFFER_HINT.value,
            target_level=EscalationLevel.L1_HINT.value,
            trigger_reason="first_error",
            rule_applied="fast_escalator_rule_1",
            error_count_at_decision=state.total_errors,
            time_to_escalation=base_time,
        )

    # Default: wait
    return EscalationDecision(
        action=EscalationAction.WAIT.value,
        target_level=current_level,
        trigger_reason="no_escalation_trigger",
        rule_applied="fast_escalator_default",
        error_count_at_decision=state.total_errors,
        time_to_escalation=base_time,
    )


FAST_ESCALATOR = EscalationPolicy(
    policy_id="fast_escalator",
    version="1.0.0",
    description="Aggressive early escalation: first error triggers hint, rapid progression to explanation",
    strategy_label="aggressive_escalation",
    decision_function=_fast_escalator_decision,
)


# =============================================================================
# Policy 2: Slow Escalator (Conservative)
# =============================================================================

def _slow_escalator_decision(state: LearnerState) -> EscalationDecision:
    """
    SLOW ESCALATOR - Conservative escalation rules.

    Strategy: Maximize independent problem-solving. Only escalate after clear struggle.

    EXPLICIT RULES:
    1. First 2 errors -> Wait (no escalation)
    2. Third error OR time stuck > 120s -> Offer hint (not automatic)
    3. Fifth error OR 2 hints requested -> Show explanation
    4. Repeated same subtype 3+ times -> Show deep explanation
    5. Time stuck > 300s (5 min) -> Max support
    6. If prior_recovery_count >= 2 (history of recovery) -> Delay escalation by 1 error
    """

    current_level = state.current_escalation_level
    base_time = state.time_on_problem

    # History bonus: learners with recovery history get more patience
    patience_bonus = 1 if state.prior_recovery_count >= 2 else 0

    # Rule 5: Max support only after very long struggle
    if state.time_stuck > 300:
        return EscalationDecision(
            action=EscalationAction.ESCALATE_TO_L4.value,
            target_level=EscalationLevel.L4_MAX.value,
            trigger_reason="extended_struggle_5min",
            rule_applied="slow_escalator_rule_5",
            error_count_at_decision=state.total_errors,
            time_to_escalation=base_time,
        )

    # Rule 4: Repeated same subtype 3+ times
    subtype_repeats = sum(
        1 for s in state.error_subtypes_seen[-3:]
        if s == state.current_error_subtype
    )
    if subtype_repeats >= 3:
        return EscalationDecision(
            action=EscalationAction.SHOW_EXPLANATION.value,
            target_level=EscalationLevel.L3_DEEP_EXPLANATION.value,
            trigger_reason="repeated_subtype_3x",
            rule_applied="slow_escalator_rule_4",
            error_count_at_decision=state.total_errors,
            time_to_escalation=base_time,
        )

    # Rule 3: Fifth error OR 2 hints requested
    if state.consecutive_errors >= (5 + patience_bonus) or state.hints_requested >= 2:
        return EscalationDecision(
            action=EscalationAction.SHOW_EXPLANATION.value,
            target_level=EscalationLevel.L2_EXPLANATION.value,
            trigger_reason="persistent_struggle",
            rule_applied="slow_escalator_rule_3",
            error_count_at_decision=state.total_errors,
            time_to_escalation=base_time,
        )

    # Rule 2: Third error OR time stuck > 120s
    if state.consecutive_errors >= (3 + patience_bonus) or state.time_stuck > 120:
        if current_level == EscalationLevel.L0_NONE.value:
            return EscalationDecision(
                action=EscalationAction.OFFER_HINT.value,
                target_level=EscalationLevel.L1_HINT.value,
                trigger_reason="multiple_errors_or_time",
                rule_applied="slow_escalator_rule_2",
                error_count_at_decision=state.total_errors,
                time_to_escalation=base_time,
            )

    # Rule 1: First 2 errors - wait (implicit in falling through)
    # Log explicitly for research
    if 1 <= state.consecutive_errors <= 2:
        return EscalationDecision(
            action=EscalationAction.WAIT.value,
            target_level=current_level,
            trigger_reason=f"early_error_patience_{state.consecutive_errors}",
            rule_applied="slow_escalator_rule_1",
            error_count_at_decision=state.total_errors,
            time_to_escalation=base_time,
        )

    # Default: wait
    return EscalationDecision(
        action=EscalationAction.WAIT.value,
        target_level=current_level,
        trigger_reason="no_escalation_trigger",
        rule_applied="slow_escalator_default",
        error_count_at_decision=state.total_errors,
        time_to_escalation=base_time,
    )


SLOW_ESCALATOR = EscalationPolicy(
    policy_id="slow_escalator",
    version="1.0.0",
    description="Conservative escalation: waits for clear struggle, prioritizes independence",
    strategy_label="conservative_escalation",
    decision_function=_slow_escalator_decision,
)


# =============================================================================
# Policy 3: Adaptive Escalator (Context-Aware)
# =============================================================================

def _adaptive_escalator_decision(state: LearnerState) -> EscalationDecision:
    """
    ADAPTIVE ESCALATOR - Context-aware escalation rules.

    Strategy: Adjust based on learner history and current context.

    EXPLICIT RULES:
    1. Calculate learner "strain score":
       - +1 per consecutive error
       - +2 if repeated_same_subtype
       - +1 per 60s time_stuck
       - -1 if prior_recovery_count >= 2 (resilient learner)
       - -1 if prior_escalation_success is False (escalation didn't help before)

    2. Strain score >= 5 -> L3 deep explanation
    3. Strain score == 4 -> L2 explanation
    4. Strain score == 3 -> Offer hint
    5. Strain score <= 2 -> Wait (unless explicit hint request)

    6. Explicit hint request overrides wait (but respect history):
       - If prior_escalation_success: Show hint immediately
       - If not prior_escalation_success: Offer hint (don't auto-show)

    7. New concept (first 2 problems on concept) -> Be more patient (+1 threshold)
    """

    current_level = state.current_escalation_level
    base_time = state.time_on_problem

    # Rule 1: Calculate strain score
    strain_score = 0
    strain_score += state.consecutive_errors
    if state.repeated_same_subtype:
        strain_score += 2
    strain_score += int(state.time_stuck // 60)  # +1 per 60s

    # Adjustments based on history
    if state.prior_recovery_count >= 2:
        strain_score -= 1  # Resilient learner
    if not state.prior_escalation_success:
        strain_score -= 1  # Escalation hasn't helped before

    # Rule 7: New concept bonus (more patience)
    concept_count = len(state.concepts_attempted)
    if concept_count <= 2:
        strain_score -= 1

    # Ensure non-negative for threshold logic
    strain_score = max(0, strain_score)

    # Rules 2-5: Strain-based escalation
    if strain_score >= 5:
        return EscalationDecision(
            action=EscalationAction.SHOW_EXPLANATION.value,
            target_level=EscalationLevel.L3_DEEP_EXPLANATION.value,
            trigger_reason=f"high_strain_score_{strain_score}",
            rule_applied="adaptive_escalator_rule_2",
            error_count_at_decision=state.total_errors,
            time_to_escalation=base_time,
        )

    if strain_score == 4:
        return EscalationDecision(
            action=EscalationAction.SHOW_EXPLANATION.value,
            target_level=EscalationLevel.L2_EXPLANATION.value,
            trigger_reason=f"medium_strain_score_{strain_score}",
            rule_applied="adaptive_escalator_rule_3",
            error_count_at_decision=state.total_errors,
            time_to_escalation=base_time,
        )

    if strain_score == 3:
        return EscalationDecision(
            action=EscalationAction.OFFER_HINT.value,
            target_level=EscalationLevel.L1_HINT.value,
            trigger_reason=f"low_strain_score_{strain_score}",
            rule_applied="adaptive_escalator_rule_4",
            error_count_at_decision=state.total_errors,
            time_to_escalation=base_time,
        )

    # Rule 6: Hint request handling
    if state.hints_requested > 0:
        if state.prior_escalation_success:
            return EscalationDecision(
                action=EscalationAction.SHOW_HINT.value,
                target_level=EscalationLevel.L1_HINT.value,
                trigger_reason="hint_request_with_success_history",
                rule_applied="adaptive_escalator_rule_6a",
                error_count_at_decision=state.total_errors,
                time_to_escalation=base_time,
            )
        else:
            return EscalationDecision(
                action=EscalationAction.OFFER_HINT.value,
                target_level=EscalationLevel.L1_HINT.value,
                trigger_reason="hint_request_no_success_history",
                rule_applied="adaptive_escalator_rule_6b",
                error_count_at_decision=state.total_errors,
                time_to_escalation=base_time,
            )

    # Rule 5: Wait for low strain
    return EscalationDecision(
        action=EscalationAction.WAIT.value,
        target_level=current_level,
        trigger_reason=f"low_strain_wait_{strain_score}",
        rule_applied="adaptive_escalator_rule_5",
        error_count_at_decision=state.total_errors,
        time_to_escalation=base_time,
    )


ADAPTIVE_ESCALATOR = EscalationPolicy(
    policy_id="adaptive_escalator",
    version="1.0.0",
    description="Context-aware escalation: adjusts based on learner history, resilience, and concept familiarity",
    strategy_label="adaptive_escalation",
    decision_function=_adaptive_escalator_decision,
)


# =============================================================================
# Policy Registry
# =============================================================================

def get_default_policies() -> list[EscalationPolicy]:
    """Get the 3 required policies for replay comparison."""
    return [FAST_ESCALATOR, SLOW_ESCALATOR, ADAPTIVE_ESCALATOR]


def get_policy_by_id(policy_id: str) -> EscalationPolicy | None:
    """Get a policy by its ID."""
    for policy in get_default_policies():
        if policy.policy_id == policy_id:
            return policy
    return None


def list_policy_definitions() -> list[dict[str, Any]]:
    """List all policy definitions (for documentation/export)."""
    return [p.to_dict() for p in get_default_policies()]


# =============================================================================
# Utility: Compute learner state from trace events
# =============================================================================

def compute_learner_state(
    events: list[Any],
    current_index: int,
    flags: dict[str, Any] | None = None,
) -> LearnerState:
    """
    Compute learner state from trace events up to current index.

    This reconstructs the state that policies use for decision-making.

    Args:
        events: List of trace events
        current_index: Current position in the event list
        flags: Optional experimental flags

    Returns:
        LearnerState at the current point in the trace
    """
    state = LearnerState(flags=flags or {})

    if not events or current_index >= len(events):
        return state

    current_event = events[current_index]

    # Set identifiers from current event
    state.learner_id = current_event.learner_id
    state.session_id = getattr(current_event, "session_id", "")
    state.problem_id = current_event.problem_id
    state.concept_id = getattr(current_event, "concept_id", None)

    # Process all events up to current
    prev_error_subtype: str | None = None
    recovery_streak = 0

    for i, evt in enumerate(events[: current_index + 1]):
        event_type = getattr(evt, "event_type", "")
        error_subtype = getattr(evt, "error_subtype", None)

        # Track concepts
        concept = getattr(evt, "concept_id", None)
        if concept:
            state.concepts_attempted.add(concept)

        # Track problems
        if event_type == "problem_attempt":
            state.problems_attempted += 1
        elif event_type == "problem_solved":
            state.problems_solved += 1
            recovery_streak += 1
            if recovery_streak >= 1 and state.consecutive_errors > 0:
                state.prior_recovery_count += 1
            state.consecutive_errors = 0
        elif event_type == "problem_abandoned":
            state.consecutive_errors = 0
            recovery_streak = 0

        # Track errors
        if error_subtype:
            state.total_errors += 1
            state.consecutive_errors += 1
            state.error_subtypes_seen.append(error_subtype)

            # Check for repeated subtype
            if prev_error_subtype == error_subtype:
                state.repeated_same_subtype = True
            prev_error_subtype = error_subtype
            recovery_streak = 0

        # Track hints/escalation
        if event_type in ("hint_requested", "hint_shown"):
            state.hints_requested += 1
        if event_type in ("hint_shown", "explanation_shown"):
            state.hints_shown += 1
        if event_type == "explanation_shown":
            state.explanations_shown += 1

        # Track escalation level
        escalation = getattr(evt, "escalation_level", None)
        if escalation:
            state.current_escalation_level = escalation

        # Track time
        time_stuck = getattr(evt, "time_stuck", 0.0)
        if time_stuck:
            state.time_stuck = time_stuck
        time_on = getattr(evt, "time_since_start", 0.0)
        if time_on:
            state.time_on_problem = time_on

    state.current_error_subtype = getattr(current_event, "error_subtype", None)

    return state
