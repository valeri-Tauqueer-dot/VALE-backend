from __future__ import annotations

from typing import Iterable, List, Optional

from .dependency_state import (
    DependencyStatus,
    HeroicDependencyState,
)


class HeroicDependencyEngine:
    """
    Manages HEROIC dependency states.

    The engine tracks whether dependencies are pending,
    satisfied, blocked, or failed. It does not execute
    dependent tasks.
    """

    def __init__(
        self,
        dependencies: Optional[
            Iterable[HeroicDependencyState]
        ] = None,
    ) -> None:
        self._dependencies: List[
            HeroicDependencyState
        ] = []

        if dependencies:
            for dependency in dependencies:
                self.add_dependency(dependency)

    def add_dependency(
        self,
        dependency: HeroicDependencyState,
    ) -> HeroicDependencyState:
        if not isinstance(
            dependency,
            HeroicDependencyState,
        ):
            raise TypeError(
                "dependency must be a "
                "HeroicDependencyState instance."
            )

        existing = self.get_dependency(
            dependency.dependency_id
        )

        if existing is not None:
            index = self._dependencies.index(
                existing
            )
            self._dependencies[index] = dependency
        else:
            self._dependencies.append(
                dependency
            )

        return dependency

    def remove_dependency(
        self,
        dependency_id: str,
    ) -> Optional[HeroicDependencyState]:
        dependency = self.get_dependency(
            dependency_id
        )

        if dependency is None:
            return None

        self._dependencies.remove(dependency)

        return dependency

    def get_dependency(
        self,
        dependency_id: str,
    ) -> Optional[HeroicDependencyState]:
        for dependency in self._dependencies:
            if dependency.dependency_id == dependency_id:
                return dependency

        return None

    def list_all(
        self,
    ) -> List[HeroicDependencyState]:
        return list(self._dependencies)

    def pending(
        self,
    ) -> List[HeroicDependencyState]:
        return [
            dependency
            for dependency in self._dependencies
            if dependency.status
            == DependencyStatus.PENDING
        ]

    def satisfied(
        self,
    ) -> List[HeroicDependencyState]:
        return [
            dependency
            for dependency in self._dependencies
            if dependency.status
            == DependencyStatus.SATISFIED
        ]

    def blocked(
        self,
    ) -> List[HeroicDependencyState]:
        return [
            dependency
            for dependency in self._dependencies
            if dependency.status
            in {
                DependencyStatus.BLOCKED,
                DependencyStatus.FAILED,
            }
        ]

    def unsatisfied(
        self,
    ) -> List[HeroicDependencyState]:
        return [
            dependency
            for dependency in self._dependencies
            if dependency.status
            != DependencyStatus.SATISFIED
        ]

    def all_satisfied(
        self,
    ) -> bool:
        required_dependencies = [
            dependency
            for dependency in self._dependencies
            if dependency.required
        ]

        return all(
            dependency.is_satisfied()
            for dependency in required_dependencies
        )

    def has_blocking_dependencies(
        self,
    ) -> bool:
        return any(
            dependency.required
            and dependency.is_blocked()
            for dependency in self._dependencies
        )

    def mark_pending(
        self,
        dependency_id: str,
    ) -> HeroicDependencyState:
        dependency = self._require(
            dependency_id
        )

        dependency.mark_pending()

        return dependency

    def satisfy(
        self,
        dependency_id: str,
    ) -> HeroicDependencyState:
        dependency = self._require(
            dependency_id
        )

        dependency.satisfy()

        return dependency

    def block(
        self,
        dependency_id: str,
    ) -> HeroicDependencyState:
        dependency = self._require(
            dependency_id
        )

        dependency.block()

        return dependency

    def fail(
        self,
        dependency_id: str,
    ) -> HeroicDependencyState:
        dependency = self._require(
            dependency_id
        )

        dependency.fail()

        return dependency

    def clear(self) -> None:
        self._dependencies.clear()

    def _require(
        self,
        dependency_id: str,
    ) -> HeroicDependencyState:
        dependency = self.get_dependency(
            dependency_id
        )

        if dependency is None:
            raise KeyError(
                f"Unknown HEROIC dependency: "
                f"{dependency_id}"
            )

        return dependency

    def to_dict(self) -> List[dict]:
        return [
            dependency.to_dict()
            for dependency in self._dependencies
        ]
