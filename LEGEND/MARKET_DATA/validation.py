"""
LEGEND MARKET DATA VALIDATION

Structural validation of incoming market data.

This module checks whether the data is internally
consistent enough to enter the normalized LEGEND
market-data state.

It does not determine whether the market is bullish,
bearish, safe, profitable, or tradable.
"""

from __future__ import annotations

from typing import Any, Dict, List


class MarketDataValidator:

    VERSION = "0.1.0"

    REQUIRED_FIELDS = (
        "instrument",
        "timestamp",
    )

    def validate(
        self,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:

        errors: List[str] = []
        warnings: List[str] = []

        for field in self.REQUIRED_FIELDS:

            value = data.get(field)

            if value is None:

                errors.append(
                    f"Required field '{field}' is missing."
                )

            elif isinstance(value, str) and not value.strip():

                errors.append(
                    f"Required field '{field}' is empty."
                )

        numeric_fields = (
            "open",
            "high",
            "low",
            "close",
            "volume",
        )

        for field in numeric_fields:

            value = data.get(field)

            if value is None:
                continue

            try:
                numeric = float(value)

                if numeric != numeric:
                    errors.append(
                        f"Field '{field}' is NaN."
                    )

            except (
                TypeError,
                ValueError,
            ):

                errors.append(
                    f"Field '{field}' is not numeric."
                )

        o = data.get("open")
        h = data.get("high")
        l = data.get("low")
        c = data.get("close")

        try:

            if (
                h is not None
                and l is not None
                and float(h) < float(l)
            ):
                errors.append(
                    "High price is lower than low price."
                )

            if (
                h is not None
                and o is not None
                and float(o) > float(h)
            ):
                errors.append(
                    "Open price exceeds high price."
                )

            if (
                h is not None
                and c is not None
                and float(c) > float(h)
            ):
                errors.append(
                    "Close price exceeds high price."
                )

            if (
                l is not None
                and o is not None
                and float(o) < float(l)
            ):
                errors.append(
                    "Open price is below low price."
                )

            if (
                l is not None
                and c is not None
                and float(c) < float(l)
            ):
                errors.append(
                    "Close price is below low price."
                )

        except (
            TypeError,
            ValueError,
        ):
            pass

        volume = data.get("volume")

        if volume is not None:

            try:

                if float(volume) < 0:
                    errors.append(
                        "Volume cannot be negative."
                    )

            except (
                TypeError,
                ValueError,
            ):
                pass

        if data.get("source") is None:
            warnings.append(
                "Data source is not specified."
            )

        valid = not errors

        return {
            "valid": valid,
            "status": (
                "VALID"
                if valid
                else "INVALID"
            ),
            "errors": errors,
            "warnings": warnings,
      }
