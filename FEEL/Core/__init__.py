"""
VALE FEELING Brain
Core Package

The core package contains the shared data models, state management,
and subsystem contracts used throughout the FEELING Brain.
"""

from .models import (
    EpistemicType,
    ConfidenceLevel,
    EvidenceStrength,
    EmotionalSignalType,
    IdeaStatus,
    EvidenceReference,
    EpistemicClaim,
    EmotionalSignal,
    HumanContext,
    PsychologicalSignal,
    PsychologicalState,
    ImaginationCandidate,
    Idea,
    Perspective,
    CommunicationProfile,
    FeelingAssessment,
)

from .state import (
    FeelingState,
    FeelingStateSnapshot,
)

from .contracts import (
    EvidenceItem,
    CognitiveContext,
    EngineResult,
    PsychologicalResult,
    HumanUnderstandingResult,
    CreativityResult,
    MCVLChallenge,
    MCVLChallengeResult,
    InterBrainContext,
    FeelingEngineRequest,
    FeelingEngineResponse,
)


__all__ = [
    # Models
    "EpistemicType",
    "ConfidenceLevel",
    "EvidenceStrength",
    "EmotionalSignalType",
    "IdeaStatus",
    "EvidenceReference",
    "EpistemicClaim",
    "EmotionalSignal",
    "HumanContext",
    "PsychologicalSignal",
    "PsychologicalState",
    "ImaginationCandidate",
    "Idea",
    "Perspective",
    "CommunicationProfile",
    "FeelingAssessment",

    # State
    "FeelingState",
    "FeelingStateSnapshot",

    # Contracts
    "EvidenceItem",
    "CognitiveContext",
    "EngineResult",
    "PsychologicalResult",
    "HumanUnderstandingResult",
    "CreativityResult",
    "MCVLChallenge",
    "MCVLChallengeResult",
    "InterBrainContext",
    "FeelingEngineRequest",
    "FeelingEngineResponse",
]
