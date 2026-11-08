"""Strict, local-only price data and clearly labelled reproducible synthetic data."""
from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np

MAX_ROWS = 100_000
MAX_ASSETS = 100
MAX_BYTES = 20_000_000
_SYMBOL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,31}\Z")


def _positive_int(value: int, name: str, upper: int) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or not 1 <= value <= upper:
        raise ValueError(f"{name} must be an integer between 1 and {upper}")
    return int(value)


@dataclass(frozen=True)
class PriceDataset:
    """Prices are adjusted closes in one common currency on one shared calendar.

    Adjustments and currency cannot be verified from a CSV. The caller is
    responsible for both and for avoiding survivorship-biased asset selection.
    Dates need not be consecutive trading days. No missing-value fill is done.
    Direct price arrays must use real integer or floating-point values;
    complex, boolean, textual and object arrays are not coerced into prices.
    """

    dates: tuple[str, ...]
    symbols: tuple[str, ...]
    prices: np.ndarray
    source: str
    synthetic: bool = False

    def __post_init__(self) -> None:
        dates = tuple(self.dates)
        symbols = tuple(self.symbols)
        if not 2 <= len(dates) <= MAX_ROWS:
            raise ValueError(f"between 2 and {MAX_ROWS} dated observations are required")
        if not 1 <= len(symbols) <= MAX_ASSETS:
            raise ValueError(f"between 1 and {MAX_ASSETS} symbols are required")
        if any(not isinstance(s, str) or not _SYMBOL.fullmatch(s) for s in symbols) or len(set(symbols)) != len(symbols):
            raise ValueError("symbols must be unique, nonempty safe identifiers of at most 32 characters")
        try:
            parsed = [date.fromisoformat(d) for d in dates]
        except (ValueError, TypeError) as exc:
            raise ValueError("dates must use YYYY-MM-DD") from exc
        if any(d.isoformat() != s for d, s in zip(parsed, dates)):
            raise ValueError("dates must use canonical YYYY-MM-DD")
        if any(a >= b for a, b in zip(parsed, parsed[1:])):
            raise ValueError("dates must be unique and strictly increasing")
        try:
            supplied = np.asarray(self.prices)
            if supplied.dtype.kind not in "iuf":
                raise ValueError("prices must contain real numbers without coercion")
            if supplied.shape != (len(dates), len(symbols)):
                raise ValueError("prices must have one complete row per date and column per symbol")
            prices = np.array(supplied, dtype=float, copy=True)
        except (ValueError, TypeError, OverflowError) as exc:
            raise ValueError("prices must be a real numeric rectangular matrix without coercion") from exc
        if prices.shape != (len(dates), len(symbols)):
            raise ValueError("prices must have one complete row per date and column per symbol")
        if not np.isfinite(prices).all() or (prices <= 0).any():
            raise ValueError("prices must be finite and strictly positive; missing values are not filled")
        if not isinstance(self.source, str) or not self.source.strip() or len(self.source) > 500:
            raise ValueError("source must be a nonempty label of at most 500 characters")
        if any(ord(char) < 32 for char in self.source):
            raise ValueError("source must not contain control characters")
        if not isinstance(self.synthetic, bool):
            raise ValueError("synthetic must be a boolean")
        prices.setflags(write=False)
        object.__setattr__(self, "dates", dates)
        object.__setattr__(self, "symbols", symbols)
        object.__setattr__(self, "prices", prices)

    @property
    def sha256(self) -> str:
        """Hash date/symbol order and canonical little-endian float64 prices."""
        digest = hashlib.sha256()
        digest.update(("\n".join(self.dates) + "\n" + ",".join(self.symbols) + "\n").encode())
        digest.update(self.prices.astype("<f8", copy=False).tobytes(order="C"))
        return digest.hexdigest()

    def metadata(self) -> dict:
        return {"source": self.source, "synthetic": self.synthetic, "sha256": self.sha256,
                "symbols": list(self.symbols), "observations": len(self.dates),
                "first_date": self.dates[0], "last_date": self.dates[-1],
                "price_convention": "caller-supplied adjusted closes in a common currency"}


def load_prices_csv(path: str | Path, *, max_rows: int = MAX_ROWS, max_assets: int = MAX_ASSETS) -> PriceDataset:
    """Read UTF-8 CSV: date,ASSET_A,ASSET_B,... . Empty cells fail closed.

    The 20 MB limit bounds memory before CSV parsing. Narrower limits may be
    selected, but callers cannot raise the process-wide limits.
    """
    max_rows = _positive_int(max_rows, "max_rows", MAX_ROWS)
    max_assets = _positive_int(max_assets, "max_assets", MAX_ASSETS)
    path = Path(path)
    if not path.is_file():
        raise ValueError("CSV path must name a regular file")
    with path.open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError(f"CSV exceeds the {MAX_BYTES} byte limit")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8") from exc
    try:
        reader = csv.reader(io.StringIO(text), strict=True)
        header = next(reader, None)
        if not header or header[0] != "date" or not 2 <= len(header) <= max_assets + 1:
            raise ValueError("CSV header must be date followed by one or more unique symbols")
        rows, dates = [], []
        for line, row in enumerate(reader, start=2):
            if len(rows) >= max_rows:
                raise ValueError(f"CSV exceeds the {max_rows} row limit")
            if len(row) != len(header) or any(not cell.strip() for cell in row):
                raise ValueError(f"CSV row {line} is incomplete or has extra columns")
            dates.append(row[0])
            try:
                rows.append([float(cell) for cell in row[1:]])
            except ValueError as exc:
                raise ValueError(f"CSV row {line} contains a non-numeric price") from exc
    except csv.Error as exc:
        raise ValueError("malformed CSV") from exc
    return PriceDataset(tuple(dates), tuple(header[1:]), np.asarray(rows), f"CSV:{path.name}")


def synthetic_prices(days: int = 504, assets: int = 4, seed: int = 42) -> PriceDataset:
    """Generate illustrative correlated lognormal paths, never market evidence.

    Weekdays are used only as a convenient calendar; exchange holidays are not
    represented. The fixed seed and start date make tutorials reproducible.
    """
    days = _positive_int(days, "days", MAX_ROWS)
    assets = _positive_int(assets, "assets", MAX_ASSETS)
    if days < 2:
        raise ValueError("days must be at least 2")
    if isinstance(seed, bool) or not isinstance(seed, (int, np.integer)) or not 0 <= seed < 2**64:
        raise ValueError("seed must be an integer in [0, 2**64)")
    rng = np.random.default_rng(int(seed))
    market = rng.normal(size=(days - 1, 1))
    specific = rng.normal(size=(days - 1, assets))
    volatility = np.linspace(0.10, 0.28, assets)
    drift = np.linspace(0.02, 0.08, assets)
    innovations = 0.55 * market + np.sqrt(1.0 - 0.55**2) * specific
    log_returns = (drift - 0.5 * volatility**2) / 252 + innovations * volatility / np.sqrt(252)
    prices = np.vstack([np.full(assets, 100.0), 100.0 * np.exp(np.cumsum(log_returns, axis=0))])
    dates = []
    current = date(2020, 1, 2)
    while len(dates) < days:
        if current.weekday() < 5:
            dates.append(current.isoformat())
        current += timedelta(days=1)
    return PriceDataset(tuple(dates), tuple(f"SYNTH_{i + 1}" for i in range(assets)), prices,
                        f"synthetic-lognormal-v1:seed={seed}", True)
