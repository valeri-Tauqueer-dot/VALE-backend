from future import annotations

from typing import Dict, Iterable, List, Optional

from HEROIC.activation.activation_state import (
ActivationMode,
ActivationStatus,
HeroicActivationState,
)

class HeroicBrainActivation:
"""
Builds and manages HEROIC brain-activation requirements.

This component plans activation state only. It does not directly
instantiate, execute, or control another VALE brain.
"""

def __init__(self) -> None:
    self._activations: Dict[str, HeroicActivationState] = {}

def create_activation(
    self,
    activation_id: str,
    brain_name: str,
    *,
    mode: ActivationMode = ActivationMode.SINGLE,
    reason: str = "",
    priority: float = 0.0,
    confidence: float = 1.0,
) -> HeroicActivationState:
    """
    Create a new brain activation requirement.

    Raises:
        ValueError:
            If activation_id already exists.
    """
    if not activation_id:
        raise ValueError("Activation ID cannot be empty.")

    if not brain_name:
        raise ValueError("Brain name cannot be empty.")

    if activation_id in self._activations:
        raise ValueError(
            f"Activation already exists: {activation_id}"
        )

    activation = HeroicActivationState(
        activation_id=activation_id,
        brain_name=brain_name,
        mode=mode,
        reason=reason,
        priority=priority,
        confidence=confidence,
    )

    self._activations[activation_id] = activation

    return activation

def register(
    self,
    activation: HeroicActivationState,
    *,
    overwrite: bool = False,
) -> HeroicActivationState:
    """Register an existing activation state."""
    if not activation.activation_id:
        raise ValueError("Activation ID cannot be empty.")

    if (
        activation.activation_id in self._activations
        and not overwrite
    ):
        raise ValueError(
            f"Activation already exists: "
            f"{activation.activation_id}"
        )

    self._activations[activation.activation_id] = activation

    return activation

def get(
    self,
    activation_id: str,
) -> Optional[HeroicActivationState]:
    """Retrieve an activation by ID."""
    return self._activations.get(activation_id)

def require(
    self,
    activation_id: str,
) -> HeroicActivationState:
    """Retrieve an activation or raise an explicit error."""
    activation = self.get(activation_id)

    if activation is None:
        raise KeyError(
            f"Unknown HEROIC activation: {activation_id}"
        )

    return activation

def list_all(self) -> List[HeroicActivationState]:
    """Return all registered activation states."""
    return list(self._activations.values())

def active(self) -> List[HeroicActivationState]:
    """Return currently active brain activations."""
    return [
        activation
        for activation in self._activations.values()
        if activation.status == ActivationStatus.ACTIVE
    ]

def pending(self) -> List[HeroicActivationState]:
    """
    Return activations that still require lifecycle progression.
    """
    terminal = {
        ActivationStatus.COMPLETED,
        ActivationStatus.CANCELLED,
        ActivationStatus.FAILED,
    }

    return [
        activation
        for activation in self._activations.values()
        if activation.status not in terminal
    ]

def add_capabilities(
    self,
    activation_id: str,
    capability_ids: Iterable[str],
) -> HeroicActivationState:
    """Attach required capabilities to an activation."""
    activation = self.require(activation_id)

    for capability_id in capability_ids:
        activation.add_capability(capability_id)

    return activation

def add_dependency(
    self,
    activation_id: str,
    dependency_activation_id: str,
) -> HeroicActivationState:
    """Add an activation dependency."""
    activation = self.require(activation_id)

    if activation_id == dependency_activation_id:
        raise ValueError(
            "An activation cannot depend on itself."
        )

    activation.add_dependency(dependency_activation_id)

    return activation

def can_activate(
    self,
    activation_id: str,
) -> bool:
    """
    Determine whether an activation is ready to become active.

    Dependencies must be completed before activation.
    """
    activation = self.require(activation_id)

    if activation.status in {
        ActivationStatus.ACTIVE,
        ActivationStatus.COMPLETED,
    }:
        return False

    if activation.status in {
        ActivationStatus.BLOCKED,
        ActivationStatus.FAILED,
        ActivationStatus.CANCELLED,
    }:
        return False

    if activation.blockers:
        return False

    for dependency_id in activation.dependencies:
        dependency = self.get(dependency_id)

        if dependency is None:
            return False

        if dependency.status != ActivationStatus.COMPLETED:
            return False

    return True

def ready(
    self,
) -> List[HeroicActivationState]:
    """Return all activations currently eligible for activation."""
    return [
        activation
        for activation in self._activations.values()
        if self.can_activate(activation.activation_id)
    ]

def mark_active(
    self,
    activation_id: str,
) -> HeroicActivationState:
    """Mark an eligible activation as active."""
    activation = self.require(activation_id)

    if not self.can_activate(activation_id):
        raise ValueError(
            f"Activation is not ready: {activation_id}"
        )

    activation.mark_activating()
    activation.mark_active()

    return activation

def mark_completed(
    self,
    activation_id: str,
) -> HeroicActivationState:
    """Mark an active activation as completed."""
    activation = self.require(activation_id)

    if activation.status != ActivationStatus.ACTIVE:
        raise ValueError(
            f"Activation is not active: {activation_id}"
        )

    activation.mark_completed()

    return activation

def mark_blocked(
    self,
    activation_id: str,
    blocker: str,
) -> HeroicActivationState:
    """Block an activation."""
    activation = self.require(activation_id)
    activation.mark_blocked(blocker)
    return activation

def clear(self) -> None:
    """Remove all activation states."""
    self._activations.clear()

def to_dict(self) -> Dict[str, dict]:
    """Serialize all activation states."""
    return {
        activation_id: activation.to_dict()
        for activation_id, activation
        in self._activations.items()
  }
