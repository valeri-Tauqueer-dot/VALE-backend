from future import annotations

from collections import defaultdict, deque
from typing import Dict, Iterable, List, Optional, Set

from HEROIC.dependencies.dependency_state import (
DependencyStatus,
HeroicDependencyState,
)

class HeroicDependencyEngine:
"""
Manages and evaluates directed dependencies between HEROIC
mission components.

A dependency is represented as:

    source_id -> target_id

meaning the source depends on the target.
"""

def __init__(
    self,
    dependencies: Optional[
        Iterable[HeroicDependencyState]
    ] = None,
) -> None:
    self._dependencies: Dict[
        str,
        HeroicDependencyState,
    ] = {}

    if dependencies:
        for dependency in dependencies:
            self.register(dependency)

def register(
    self,
    dependency: HeroicDependencyState,
    overwrite: bool = True,
) -> HeroicDependencyState:
    """Register a dependency."""
    if (
        dependency.dependency_id in self._dependencies
        and not overwrite
    ):
        raise ValueError(
            f"Dependency already exists: "
            f"{dependency.dependency_id}"
        )

    self._dependencies[
        dependency.dependency_id
    ] = dependency

    return dependency

def get(
    self,
    dependency_id: str,
) -> Optional[HeroicDependencyState]:
    """Return a dependency if registered."""
    return self._dependencies.get(dependency_id)

def require(
    self,
    dependency_id: str,
) -> HeroicDependencyState:
    """Return a dependency or raise an explicit error."""
    dependency = self.get(dependency_id)

    if dependency is None:
        raise KeyError(
            f"Unknown HEROIC dependency: {dependency_id}"
        )

    return dependency

def unregister(
    self,
    dependency_id: str,
) -> bool:
    """Remove a dependency."""
    if dependency_id not in self._dependencies:
        return False

    del self._dependencies[dependency_id]
    return True

def dependencies_for(
    self,
    source_id: str,
) -> List[HeroicDependencyState]:
    """Return dependencies required by a source entity."""
    if not source_id:
        return []

    return [
        dependency
        for dependency in self._dependencies.values()
        if dependency.source_id == source_id
    ]

def dependents_of(
    self,
    target_id: str,
) -> List[HeroicDependencyState]:
    """Return dependencies whose source depends on a target."""
    if not target_id:
        return []

    return [
        dependency
        for dependency in self._dependencies.values()
        if dependency.target_id == target_id
    ]

def blocking_for(
    self,
    source_id: str,
) -> List[HeroicDependencyState]:
    """Return mandatory dependencies currently blocking a source."""
    return [
        dependency
        for dependency in self.dependencies_for(source_id)
        if dependency.is_blocking()
    ]

def is_satisfied(
    self,
    source_id: str,
) -> bool:
    """
    Determine whether all mandatory dependencies of a source
    are satisfied.
    """
    for dependency in self.dependencies_for(source_id):
        if dependency.mandatory and not dependency.is_satisfied():
            return False

    return True

def mark_satisfied(
    self,
    dependency_id: str,
) -> HeroicDependencyState:
    """Mark a dependency as satisfied."""
    dependency = self.require(dependency_id)
    dependency.mark_satisfied()
    return dependency

def mark_unsatisfied(
    self,
    dependency_id: str,
    reason: str = "",
) -> HeroicDependencyState:
    """Mark a dependency as unsatisfied."""
    dependency = self.require(dependency_id)
    dependency.mark_unsatisfied(reason)
    return dependency

def mark_blocked(
    self,
    dependency_id: str,
    blocker: str = "",
) -> HeroicDependencyState:
    """Mark a dependency as blocked."""
    dependency = self.require(dependency_id)
    dependency.mark_blocked(blocker)
    return dependency

def mark_failed(
    self,
    dependency_id: str,
    reason: str = "",
) -> HeroicDependencyState:
    """Mark a dependency as failed."""
    dependency = self.require(dependency_id)
    dependency.mark_failed(reason)
    return dependency

def validate(
    self,
) -> List[str]:
    """
    Validate dependency references.

    Returns a list of dependency IDs containing invalid
    self-references or malformed relationships.
    """
    invalid: List[str] = []

    for dependency in self._dependencies.values():
        if not dependency.source_id:
            invalid.append(dependency.dependency_id)
            continue

        if not dependency.target_id:
            invalid.append(dependency.dependency_id)
            continue

        if dependency.source_id == dependency.target_id:
            invalid.append(dependency.dependency_id)

    return invalid

def has_cycles(
    self,
) -> bool:
    """
    Detect whether the registered dependency graph contains
    a directed cycle.
    """
    graph: Dict[str, Set[str]] = defaultdict(set)
    indegree: Dict[str, int] = defaultdict(int)

    nodes: Set[str] = set()

    for dependency in self._dependencies.values():
        source = dependency.source_id
        target = dependency.target_id

        nodes.add(source)
        nodes.add(target)

        if target not in graph[source]:
            graph[source].add(target)
            indegree[target] += 1

    queue = deque(
        node
        for node in nodes
        if indegree[node] == 0
    )

    visited = 0

    while queue:
        node = queue.popleft()
        visited += 1

        for target in graph[node]:
            indegree[target] -= 1

            if indegree[target] == 0:
                queue.append(target)

    return visited != len(nodes)

def topological_order(self) -> List[str]:
    """
    Return a dependency-respecting ordering of entity IDs.

    Raises ValueError if a directed cycle exists.
    """
    if self.has_cycles():
        raise ValueError(
            "Cannot build dependency order: "
            "dependency cycle detected."
        )

    graph: Dict[str, Set[str]] = defaultdict(set)
    indegree: Dict[str, int] = defaultdict(int)
    nodes: Set[str] = set()

    for dependency in self._dependencies.values():
        source = dependency.source_id
        target = dependency.target_id

        nodes.add(source)
        nodes.add(target)

        if target not in graph[source]:
            graph[source].add(target)
            indegree[target] += 1

    queue = deque(
        sorted(
            node
            for node in nodes
            if indegree[node] == 0
        )
    )

    ordered: List[str] = []

    while queue:
        node = queue.popleft()
        ordered.append(node)

        for target in sorted(graph[node]):
            indegree[target] -= 1

            if indegree[target] == 0:
                queue.append(target)

    if len(ordered) != len(nodes):
        raise ValueError(
            "Dependency graph could not be ordered."
        )

    return ordered

def active(
    self,
) -> List[HeroicDependencyState]:
    """Return unresolved dependencies."""
    return [
        dependency
        for dependency in self._dependencies.values()
        if dependency.status
        in {
            DependencyStatus.UNKNOWN,
            DependencyStatus.IDENTIFIED,
            DependencyStatus.UNSATISFIED,
            DependencyStatus.BLOCKED,
        }
    ]

def satisfied(
    self,
) -> List[HeroicDependencyState]:
    """Return satisfied dependencies."""
    return [
        dependency
        for dependency in self._dependencies.values()
        if dependency.is_satisfied()
    ]

def clear(self) -> None:
    """Remove all registered dependencies."""
    self._dependencies.clear()

def __len__(self) -> int:
    return len(self._dependencies)

def __contains__(
    self,
    dependency_id: str,
) -> bool:
    return dependency_id in self._dependencies

def to_dict(self) -> Dict[str, Dict]:
    """Serialize all registered dependencies."""
    return {
        dependency_id: dependency.to_dict()
        for dependency_id, dependency
        in self._dependencies.items()
  }
