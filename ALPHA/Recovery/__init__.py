"""
VALE AI - ALPHA Recovery Package

Execution timeout, failure handling, and recovery infrastructure.
"""

from .timeout_manager import (
    TimeoutAction,
    TimeoutCheckResult,
    TimeoutConfigurationError,
    TimeoutEvent,
    TimeoutManager,
    TimeoutManagerConfig,
    TimeoutManagerError,
    TimeoutRecord,
    TimeoutState,
    TimeoutStateError,
)

from .recovery_manager import (
    FailureClass,
    FailureClassification,
    RecoveryAction,
    RecoveryConfigurationError,
    RecoveryCycleResult,
    RecoveryDecision,
    RecoveryManager,
    RecoveryManagerConfig,
    RecoveryManagerError,
    RecoveryPolicyError,
    RecoveryRecord,
    RecoveryState,
    RecoveryStateError,
    RetryDisposition,
)

__all__ = [
    # Timeout Manager
    "TimeoutAction",
    "TimeoutCheckResult",
    "TimeoutConfigurationError",
    "TimeoutEvent",
    "TimeoutManager",
    "TimeoutManagerConfig",
    "TimeoutManagerError",
    "TimeoutRecord",
    "TimeoutState",
    "TimeoutStateError",

    # Recovery Manager
    "FailureClass",
    "FailureClassification",
    "RecoveryAction",
    "RecoveryConfigurationError",
    "RecoveryCycleResult",
    "RecoveryDecision",
    "RecoveryManager",
    "RecoveryManagerConfig",
    "RecoveryManagerError",
    "RecoveryPolicyError",
    "RecoveryRecord",
    "RecoveryState",
    "RecoveryStateError",
    "RetryDisposition",
]
