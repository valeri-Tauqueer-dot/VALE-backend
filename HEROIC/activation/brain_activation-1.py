from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from .activation_state import (
    ActivationMode,
    ActivationStatus,
    HeroicActivationState,
)


class HeroicBrainActivation:
    """
    Manages HEROIC brain activation states.

    This layer is declarative: it records which VALE brains HEROIC
    intends to activate and whether those activations are ready.
    It does not execute the brains itself.
    """

    def __init__(
        self,
        activations: Optional[Iterable[HeroicActivationState]] = None,
    ) -> None:
        self._activations: Dict[str, HeroicActivationState] = {}

        if activations:
            for activation in activations:
                self.register(activation)

    def create_activation(
        self,
        brain_name: str,
        mode: ActivationMode = ActivationMode.SINGLE,
        reason: str = "",
        priority: float = 0.0,
        confidence: float = 1.0,
    ) -> HeroicActivationState:
        activation = HeroicActivationState(
            brain_name=brain_name,
            mode=mode,
            reason=reason,
            priority=priority,
            confidence=confidence,
        )

        self.register(activation)
        return activation

    def register(
        self,
        activation: HeroicActivationState,
        overwrite: bool = False,
    ) -> HeroicActivationState:
        if not isinstance(activation, HeroicActivationState):
            raise TypeError(
                "activation must be a HeroicActivationState instance."
            )

        if (
            activation.activation_id in self._activations
            and not overwrite
        ):
            raise ValueError(
                f"Activation already registered: "
                f"{activation.activation_id}"
            )

        self._activations[activation.activation_id] = activation
        return activation

    def get(
        self,
        activation_id: str,
    ) -> Optional[HeroicActivationState]:
        return self._activations.get(activation_id)

    def require(
        self,
        activation_id: str,
    ) -> HeroicActivationState:
        activation = self.get(activation_id)

        if activation is None:
            raise KeyError(
                f"Unknown activation: {activation_id}"
            )

        return activation

    def list_all(self) -> List[HeroicActivationState]:
        return list(self._activations.values())

    def active(self) -> List[HeroicActivationState]:
        return [
            activation
            for activation in self._activations.values()
            if activation.status
            in {
                ActivationStatus.ACTIVATING,
                ActivationStatus.ACTIVE,
            }
        ]

    def pending(self) -> List[HeroicActivationState]:
        return [
            activation
            for activation in self._activations.values()
            if activation.status
            in {
                ActivationStatus.REQUESTED,
                ActivationStatus.PLANNED,
                ActivationStatus.READY,
            }
        ]

    def add_capabilities(
        self,
        activation_id: str,
        capability_ids: Iterable[str],
    ) -> HeroicActivationState:
        activation = self.require(activation_id)

        for capability_id in capability_ids:
            activation.add_capability(capability_id)

        return activation

    def add_dependency(
        self,
        activation_id: str,
        dependency_id: str,
    ) -> HeroicActivationState:
        activation = self.require(activation_id)
        activation.add_dependency(dependency_id)
        return activation

    def can_activate(
        self,
        activation_id: str,
    ) -> bool:
        activation = self.require(activation_id)

        if activation.is_blocked():
            return False

        for dependency_id in activation.dependencies:
            dependency = self.get(dependency_id)

            if dependency is None:
                return False

            if dependency.status not in {
                ActivationStatus.ACTIVE,
                ActivationStatus.COMPLETED,
            }:
                return False

        return True

    def ready(
        self,
        activation_id: str,
    ) -> bool:
        activation = self.require(activation_id)

        if activation.is_blocked():
            return False

        if not self.can_activate(activation_id):
            return False

        if activation.status == ActivationStatus.REQUESTED:
            activation.mark_planned()

        if activation.status == ActivationStatus.PLANNED:
            activation.mark_ready()

        return activation.status == ActivationStatus.READY

    def mark_active(
        self,
        activation_id: str,
    ) -> HeroicActivationState:
        activation = self.require(activation_id)

        if not self.can_activate(activation_id):
            raise RuntimeError(
                f"Activation cannot become active: "
                f"{activation_id}"
            )

        activation.mark_activating()
        activation.mark_active()

        return activation

    def mark_completed(
        self,
        activation_id: str,
    ) -> HeroicActivationState:
        activation = self.require(activation_id)
        activation.mark_completed()
        return activation

    def mark_blocked(
        self,
        activation_id: str,
        reason: str = "",
    ) -> HeroicActivationState:
        activation = self.require(activation_id)
        activation.mark_blocked(reason)
        return activation

    def clear(self) -> None:
        self._activations.clear()

    def to_dict(self) -> Dict[str, object]:
        return {
            activation_id: activation.to_dict()
            for activation_id, activation
            in self._activations.items()
        }

    def __len__(self) -> int:
        return len(self._activations)

    def __contains__(self, activation_id: str) -> bool:
        return activation_id in self._activations
