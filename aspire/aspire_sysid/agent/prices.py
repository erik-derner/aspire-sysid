"""Price schedule and cost computation for language-model requests.

The record contains the cost computed from a dated price schedule, and the round budget
includes a limit on monetary cost. The schedule is the file
``aspire/configs/prices.yaml``. Every table and every entry carries the date on which the price
was verified and its source; a table or an entry without a verification date is rejected, and a
model without an entry has no cost and is rejected by :func:`cost_usd`.

The cost of one request with ``n_in`` input tokens and ``n_out`` output tokens is

    cost = n_in * c_in / 1e6 + n_out * c_out / 1e6,

where ``c_in`` and ``c_out`` are the input and output prices in USD per 1,000,000 tokens.
Cached input tokens are part of ``n_in`` and are charged at the full input price ``c_in``,
because no cached-input price has been verified; this overestimates and never underestimates
the cost. Reasoning tokens are part of ``n_out``.
"""

from __future__ import annotations

import datetime as _dt
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

import yaml

from ..paths import config_path

__all__ = [
    "PriceTableError",
    "UnknownModelPriceError",
    "ModelPrice",
    "PriceTable",
    "load_price_table",
    "default_price_table",
    "cost_usd",
]

TOKENS_PER_UNIT = 1_000_000
"""Prices are stated per this number of tokens."""


class PriceTableError(ValueError):
    """The price schedule is malformed, for example undated or with a non-numeric price."""


class UnknownModelPriceError(LookupError):
    """The price schedule has no entry for the requested model identifier."""


class _UsageLike(Protocol):
    input_tokens: int
    output_tokens: int  # an optional attribute ``web_search_calls`` is read when present


@dataclass(frozen=True)
class ModelPrice:
    """Price of one pinned model, in USD per 1,000,000 tokens, with its verification."""

    model: str
    input_usd_per_mtok: float
    output_usd_per_mtok: float
    verified: _dt.date
    source: str
    vendor: str | None = None
    web_search_usd_per_call: float | None = None
    web_search_verified: _dt.date | None = None


@dataclass(frozen=True)
class PriceTable:
    """A dated price schedule. Construct with :meth:`from_mapping` or :func:`load_price_table`."""

    prices: Mapping[str, ModelPrice]
    verified: _dt.date
    origin: str

    @classmethod
    def from_mapping(cls, data: Any, *, origin: str = "<mapping>") -> "PriceTable":
        """Validate a parsed schedule and build the table. 

        Required: a table-level ``verified`` date and a ``models`` mapping in which every entry
        has numeric, finite, non-negative ``input`` and ``output`` prices, a ``verified`` date and
        a non-empty ``source``. Raises :class:`PriceTableError` naming the origin and the entry.
        """
        if not isinstance(data, Mapping):
            raise PriceTableError(f"price table {origin}: expected a mapping at the top level")
        table_date = _parse_date(data.get("verified"), f"price table {origin}")
        models = data.get("models")
        if not isinstance(models, Mapping) or not models:
            raise PriceTableError(f"price table {origin}: 'models' must be a non-empty mapping")
        prices: dict[str, ModelPrice] = {}
        for model, entry in models.items():
            where = f"price table {origin}, model {model!r}"
            if not isinstance(entry, Mapping):
                raise PriceTableError(f"{where}: entry must be a mapping")
            source = entry.get("source")
            if not isinstance(source, str) or not source.strip():
                raise PriceTableError(f"{where}: missing 'source' of the price")
            vendor = entry.get("vendor")
            ws = entry.get("web_search_call")
            prices[str(model)] = ModelPrice(
                model=str(model),
                input_usd_per_mtok=_parse_price(entry.get("input"), f"{where}, 'input'"),
                output_usd_per_mtok=_parse_price(entry.get("output"), f"{where}, 'output'"),
                verified=_parse_date(entry.get("verified"), where),
                source=source.strip(),
                vendor=str(vendor) if vendor is not None else None,
                web_search_usd_per_call=None if ws is None else _parse_price(ws, f"{where}, 'web_search_call'"),
                web_search_verified=None if ws is None else _parse_date(entry.get("web_search_verified"), f"{where}, 'web_search_verified'"),
            )
        return cls(prices=prices, verified=table_date, origin=origin)

    def price(self, model: str) -> ModelPrice:
        """Return the price entry of ``model``. 

        Raises :class:`UnknownModelPriceError` when the model is not listed; no price is ever
        assumed or borrowed from another model.
        """
        try:
            return self.prices[model]
        except KeyError:
            listed = ", ".join(sorted(self.prices)) or "none"
            raise UnknownModelPriceError(
                f"no verified price for model {model!r} in {self.origin} (listed: {listed}); "
                "add an entry with its verification date and source before using this model"
            ) from None

    def cost_usd(self, model: str, usage: _UsageLike) -> float:
        """Cost in USD of the token usage ``usage`` of one or more requests to ``model``. 

        Cached input tokens are included in ``usage.input_tokens`` and charged at the full input
        price (module docstring). Web search calls that the vendor executed (``usage.web_search_calls``)
        are charged at the verified fee per call of the model's entry; the content that a search
        returns to the model is part of the input tokens. A usage with web search calls and a
        model without a verified fee raises :class:`UnknownModelPriceError`: no fee is assumed.
        """
        entry = self.price(model)
        n_in = _parse_count(getattr(usage, "input_tokens", None), "input_tokens")
        n_out = _parse_count(getattr(usage, "output_tokens", None), "output_tokens")
        n_ws = _parse_count(getattr(usage, "web_search_calls", 0) or 0, "web_search_calls")
        fee = 0.0
        if n_ws:
            if entry.web_search_usd_per_call is None:
                raise UnknownModelPriceError(
                    f"no verified fee per web search call for model {model!r} in {self.origin}; add 'web_search_call' and "
                    "'web_search_verified' to its entry before using the vendor's web search tool"
                )
            fee = n_ws * entry.web_search_usd_per_call
        return (
            n_in * entry.input_usd_per_mtok + n_out * entry.output_usd_per_mtok
        ) / TOKENS_PER_UNIT + fee


def load_price_table(path: str | Path | None = None) -> PriceTable:
    """Load and validate the price schedule, by default ``aspire/configs/prices.yaml``. """
    p = Path(path) if path is not None else config_path("prices.yaml")
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise PriceTableError(f"price table {p}: cannot be read ({exc})") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PriceTableError(f"price table {p}: invalid YAML ({exc})") from exc
    return PriceTable.from_mapping(data, origin=str(p))


_DEFAULT_TABLE: PriceTable | None = None


def default_price_table() -> PriceTable:
    """The price schedule ``aspire/configs/prices.yaml``, loaded once per process. """
    global _DEFAULT_TABLE
    if _DEFAULT_TABLE is None:
        _DEFAULT_TABLE = load_price_table()
    return _DEFAULT_TABLE


def cost_usd(model: str, usage: _UsageLike, table: PriceTable | None = None) -> float:
    """Cost in USD of ``usage`` on ``model`` from the dated price schedule. 

    ``table`` defaults to :func:`default_price_table`. Raises :class:`UnknownModelPriceError` for
    a model without a verified price.
    """
    return (table or default_price_table()).cost_usd(model, usage)


def _parse_date(value: Any, where: str) -> _dt.date:
    if value is None or value == "":
        raise PriceTableError(f"{where}: missing verification date 'verified' (ISO 8601, YYYY-MM-DD)")
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, str):
        try:
            return _dt.date.fromisoformat(value.strip())
        except ValueError:
            pass
    raise PriceTableError(f"{where}: verification date {value!r} is not an ISO 8601 date (YYYY-MM-DD)")


def _parse_price(value: Any, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PriceTableError(f"{where}: price must be a number of USD per 1,000,000 tokens, got {value!r}")
    v = float(value)
    if not math.isfinite(v) or v < 0:
        raise PriceTableError(f"{where}: price must be finite and non-negative, got {value!r}")
    return v


def _parse_count(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"usage.{name} must be a non-negative integer, got {value!r}")
    return value
