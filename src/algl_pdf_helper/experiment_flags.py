"""
Experiment Flags - Session-level baseline toggles for replay comparison.

This module defines validated configuration for experimental session flags.
These flags control which features are active during a replay session.

Required toggles:
- textbook_disabled: Disable textbook assembly/recommendations
- adaptive_ladder_disabled: Disable adaptive hint ladder
- immediate_explanation_mode: Show explanations immediately (no hints first)
- static_hint_mode: Use static hints instead of adaptive

Usage:
    from experiment_flags import ExperimentFlags, load_flags

    flags = ExperimentFlags(textbook_disabled=True)
    if flags.textbook_disabled:
        # Skip textbook assembly
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ExperimentFlags:
    """
    Session-level experimental flags for replay comparison.

    These flags allow comparing outcomes with different feature sets
    enabled or disabled (baseline vs treatment).
    """

    # Schema version for compatibility checking
    schema_version: str = "1.0.0"

    # ==========================================================================
    # Required Toggles (from task specification)
    # ==========================================================================

    # Disable textbook assembly and recommendations
    # When True: No learner textbook is built, no saved units tracked
    # Baseline: False (textbook features enabled)
    textbook_disabled: bool = False

    # Disable adaptive hint ladder
    # When True: Hints shown in fixed order, no adaptation to learner state
    # Baseline: False (adaptive ladder enabled)
    adaptive_ladder_disabled: bool = False

    # Immediate explanation mode (skip hints, go straight to explanation)
    # When True: First escalation shows explanation instead of hint
    # Baseline: False (hints first, then explanation)
    immediate_explanation_mode: bool = False

    # Static hint mode (non-adaptive, pre-defined hints)
    # When True: Use static hint bank instead of generated/contextual hints
    # Baseline: False (adaptive/generated hints)
    static_hint_mode: bool = False

    # ==========================================================================
    # Additional Research Flags
    # ==========================================================================

    # Disable all escalation (pure independent solving)
    # When True: No hints or explanations offered automatically
    # Use case: Measuring pure learner persistence
    escalation_disabled: bool = False

    # Force concept mastery display
    # When True: Always show mastery progress even if low
    force_mastery_display: bool = False

    # Reduced hint verbosity
    # When True: Shorter, more concise hints
    concise_hints: bool = False

    # Enable reinforcement prompts
    # When True: Show reinforcement questions after explanations
    reinforcement_enabled: bool = True

    # Prerequisite enforcement
    # When True: Block advanced concepts until prerequisites met
    enforce_prerequisites: bool = False

    # Session timeout override (seconds, 0 = default)
    session_timeout_seconds: int = 0

    # Maximum hints per problem (0 = unlimited)
    max_hints_per_problem: int = 0

    # ==========================================================================
    # Metadata
    # ==========================================================================

    # Human-readable description of this flag configuration
    description: str = ""

    # Which experimental condition this represents
    condition_label: str = "control"  # e.g., "control", "treatment_A", "baseline"

    # Extended flags for custom experiments
    extended_flags: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert flags to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExperimentFlags:
        """Create flags from dictionary with validation."""
        # Filter to known fields
        known = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in known}

        # Handle extended_flags separately
        extended = {}
        for k, v in data.items():
            if k not in known:
                extended[k] = v

        if extended:
            filtered["extended_flags"] = extended

        return cls(**filtered)

    def validate(self) -> list[str]:
        """
        Validate flag combinations and return list of issues.

        Returns empty list if valid.
        """
        issues = []

        # Check for conflicting flags
        if self.immediate_explanation_mode and self.static_hint_mode:
            issues.append(
                "immediate_explanation_mode conflicts with static_hint_mode: "
                "immediate explanation will override static hints"
            )

        if self.escalation_disabled and self.immediate_explanation_mode:
            issues.append(
                "escalation_disabled conflicts with immediate_explanation_mode: "
                "no escalation means no explanations"
            )

        if self.adaptive_ladder_disabled and not self.static_hint_mode:
            issues.append(
                "adaptive_ladder_disabled without static_hint_mode: "
                "hint source undefined when adaptive is disabled"
            )

        return issues

    def is_baseline(self) -> bool:
        """Check if this represents a baseline/control configuration."""
        return (
            not self.textbook_disabled
            and not self.adaptive_ladder_disabled
            and not self.immediate_explanation_mode
            and not self.static_hint_mode
            and self.condition_label in ("control", "baseline", "default")
        )

    def get_active_toggles(self) -> dict[str, bool]:
        """Get all boolean toggles that are enabled."""
        return {
            k: v
            for k, v in self.to_dict().items()
            if isinstance(v, bool) and v
        }

    def get_summary(self) -> str:
        """Get human-readable summary of flag configuration."""
        parts = []
        if self.textbook_disabled:
            parts.append("no-textbook")
        if self.adaptive_ladder_disabled:
            parts.append("no-adaptive")
        if self.immediate_explanation_mode:
            parts.append("immediate-explanation")
        if self.static_hint_mode:
            parts.append("static-hints")
        if self.escalation_disabled:
            parts.append("no-escalation")

        if not parts:
            return "full-features"
        return "|".join(parts)

    def apply_to_policy_context(self) -> dict[str, Any]:
        """
        Convert flags to policy context dictionary.

        This is used when computing learner state for policy decisions.
        """
        return {
            "textbook_disabled": self.textbook_disabled,
            "adaptive_ladder_disabled": self.adaptive_ladder_disabled,
            "immediate_explanation_mode": self.immediate_explanation_mode,
            "static_hint_mode": self.static_hint_mode,
            "escalation_disabled": self.escalation_disabled,
            "reinforcement_enabled": self.reinforcement_enabled,
            "enforce_prerequisites": self.enforce_prerequisites,
            "max_hints_per_problem": self.max_hints_per_problem,
            "condition_label": self.condition_label,
        }


# =============================================================================
# I/O Functions
# =============================================================================

def load_flags(path: Path) -> ExperimentFlags:
    """Load experiment flags from JSON file."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return ExperimentFlags.from_dict(data)


def save_flags(flags: ExperimentFlags, path: Path) -> None:
    """Save experiment flags to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(flags.to_dict(), f, indent=2, ensure_ascii=False)


def flags_from_trace_context(trace_context: dict[str, Any]) -> ExperimentFlags:
    """
    Extract flags from trace session_config.

    This bridges trace_schema session_config with ExperimentFlags.
    """
    config = trace_context.get("session_config", {})
    return ExperimentFlags.from_dict(config)


# =============================================================================
# Predefined Flag Configurations
# =============================================================================

def get_baseline_flags() -> ExperimentFlags:
    """Get baseline/control flag configuration."""
    return ExperimentFlags(
        description="Baseline configuration with all features enabled",
        condition_label="baseline",
    )


def get_no_textbook_flags() -> ExperimentFlags:
    """Get flags with textbook features disabled."""
    return ExperimentFlags(
        textbook_disabled=True,
        description="Textbook assembly disabled",
        condition_label="no_textbook",
    )


def get_no_adaptive_flags() -> ExperimentFlags:
    """Get flags with adaptive ladder disabled."""
    return ExperimentFlags(
        adaptive_ladder_disabled=True,
        static_hint_mode=True,  # Must enable static when adaptive is off
        description="Adaptive ladder disabled, static hints only",
        condition_label="no_adaptive",
    )


def get_immediate_explanation_flags() -> ExperimentFlags:
    """Get flags for immediate explanation mode."""
    return ExperimentFlags(
        immediate_explanation_mode=True,
        description="Explanations shown immediately, no hints first",
        condition_label="immediate_explanation",
    )


def get_minimal_flags() -> ExperimentFlags:
    """Get minimal flags configuration (most features disabled)."""
    return ExperimentFlags(
        textbook_disabled=True,
        adaptive_ladder_disabled=True,
        static_hint_mode=True,
        escalation_disabled=True,
        description="Minimal configuration, most features disabled",
        condition_label="minimal",
    )


def list_predefined_configs() -> dict[str, ExperimentFlags]:
    """List all predefined flag configurations."""
    return {
        "baseline": get_baseline_flags(),
        "no_textbook": get_no_textbook_flags(),
        "no_adaptive": get_no_adaptive_flags(),
        "immediate_explanation": get_immediate_explanation_flags(),
        "minimal": get_minimal_flags(),
    }
