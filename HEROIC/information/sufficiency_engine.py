from __future__ import annotations

from typing import Iterable, List, Optional

from .information_state import (
    HeroicInformationState,
    InformationImportance,
)
from .missing_information import HeroicMissingInformation


class HeroicInformationSufficiencyEngine:
    """
    Evaluates whether the available information is sufficient
    for a HEROIC mission to proceed safely and coherently.

    Missing, stale, or conflicting required information is
    never treated as verified information.
    """

    def __init__(
        self,
        information: Optional[
            Iterable[HeroicInformationState]
        ] = None,
    ) -> None:
        self._information: List[
            HeroicInformationState
        ] = []

        if information:
            for item in information:
                self.add_information(item)

    def add_information(
        self,
        information: HeroicInformationState,
    ) -> HeroicInformationState:
        if not isinstance(
            information,
            HeroicInformationState,
        ):
            raise TypeError(
                "information must be a "
                "HeroicInformationState instance."
            )

        existing = self.get_information(
            information.information_id
        )

        if existing is not None:
            index = self._information.index(existing)
            self._information[index] = information
        else:
            self._information.append(information)

        return information

    def remove_information(
        self,
        information_id: str,
    ) -> Optional[HeroicInformationState]:
        information = self.get_information(
            information_id
        )

        if information is None:
            return None

        self._information.remove(information)
        return information

    def get_information(
        self,
        information_id: str,
    ) -> Optional[HeroicInformationState]:
        for information in self._information:
            if information.information_id == information_id:
                return information

        return None

    def list_all(
        self,
    ) -> List[HeroicInformationState]:
        return list(self._information)

    def required(
        self,
    ) -> List[HeroicInformationState]:
        return [
            information
            for information in self._information
            if information.required
        ]

    def missing(
        self,
    ) -> List[HeroicInformationState]:
        return [
            information
            for information in self._information
            if not information.is_usable()
        ]

    def missing_required(
        self,
    ) -> List[HeroicInformationState]:
        return [
            information
            for information in self.required()
            if not information.is_usable()
        ]

    def blocking(
        self,
    ) -> List[HeroicInformationState]:
        return [
            information
            for information in self._information
            if information.is_blocking()
        ]

    def is_sufficient(self) -> bool:
        return not self.missing_required()

    def is_sufficient_for_execution(self) -> bool:
        return (
            self.is_sufficient()
            and not self.blocking()
        )

    def missing_information_records(
        self,
    ) -> List[HeroicMissingInformation]:
        return [
            HeroicMissingInformation.from_information(
                information
            )
            for information in self.missing()
        ]

    def critical_missing(
        self,
    ) -> List[HeroicInformationState]:
        return [
            information
            for information in self.missing_required()
            if information.importance
            == InformationImportance.CRITICAL
        ]

    def resolve(
        self,
        information_id: str,
        value: object,
        source: str = "",
        verified: bool = False,
    ) -> HeroicInformationState:
        information = self._require(information_id)

        information.set_value(value, source)

        if verified:
            information.mark_verified()

        return information

    def _require(
        self,
        information_id: str,
    ) -> HeroicInformationState:
        information = self.get_information(
            information_id
        )

        if information is None:
            raise KeyError(
                f"Unknown HEROIC information: "
                f"{information_id}"
            )

        return information

    def clear(self) -> None:
        self._information.clear()

    def to_dict(self) -> List[dict]:
        return [
            information.to_dict()
            for information in self._information
            ]
