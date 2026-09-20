"""
HEROIC MISSION IDENTITY

Foundational identity model for HEROIC missions.

This module is intentionally lightweight.

It does not:
- understand user intent
- plan tasks
- select brains
- execute work
- verify results
- make decisions

It only provides stable identity and traceability for a mission.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any, Dict, Optional


@dataclass
class HeroicMissionIdentity:
    """
    Stable identity information for a HEROIC mission.
    """

    mission_id: str = field(
        default_factory=lambda: f"heroic-{uuid4().hex}"
    )

    parent_mission_id: Optional[str] = None

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    source: str = "user"

    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert mission identity into a serializable dictionary.
        """

        return {
            "mission_id": self.mission_id,
            "parent_mission_id": self.parent_mission_id,
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "metadata": dict(self.metadata),
        }
