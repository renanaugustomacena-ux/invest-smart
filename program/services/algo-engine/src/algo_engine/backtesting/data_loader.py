"""Load historical OHLCV data from CSV and Parquet files.

Converts raw rows into OHLCVBar dataclass instances compatible with the
production AlgoEngine.process_bar() interface. All price and volume fields
are parsed as Decimal to maintain financial precision throughout the pipeline.
"""

from __future__ import annotations

import csv
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Iterator

from moneymaker_common.logging import get_logger

from algo_engine.features.pipeline import OHLCVBar

logger = get_logger(__name__)

# Default column mapping for CSV/Parquet files
_DEFAULT_COLUMNS = {
    "timestamp": "timestamp",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "volume": "volume",
}


def _to_decimal(value: str | float | int | Decimal) -> Decimal:
    """Convert a value to Decimal with banker's rounding."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value)).quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN)


def _row_to_bar(row: dict[str, str | float | int], columns: dict[str, str]) -> OHLCVBar:
    """Convert a single data row into an OHLCVBar."""
    return OHLCVBar(
        timestamp=int(row[columns["timestamp"]]),
        open=_to_decimal(row[columns["open"]]),
        high=_to_decimal(row[columns["high"]]),
        low=_to_decimal(row[columns["low"]]),
        close=_to_decimal(row[columns["close"]]),
        volume=_to_decimal(row[columns["volume"]]),
    )


def load_bars_from_csv(
    file_path: str | Path,
    *,
    columns: dict[str, str] | None = None,
) -> list[OHLCVBar]:
    """Load all OHLCV bars from a CSV file.

    Args:
        file_path: Path to the CSV file.
        columns: Optional mapping from canonical names (timestamp, open, high,
            low, close, volume) to actual column names in the file.

    Returns:
        List of OHLCVBar instances sorted by timestamp ascending.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If required columns are missing.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    col_map = {**_DEFAULT_COLUMNS, **(columns or {})}
    bars: list[OHLCVBar] = []

    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)

        if reader.fieldnames is None:
            raise ValueError(f"CSV file has no header row: {path}")

        missing = [
            canonical
            for canonical, actual in col_map.items()
            if actual not in reader.fieldnames
        ]
        if missing:
            raise ValueError(
                f"Missing columns in {path}: expected {missing} "
                f"(mapped from {[col_map[m] for m in missing]}), "
                f"found {reader.fieldnames}"
            )

        for row_num, row in enumerate(reader, start=2):
            try:
                bars.append(_row_to_bar(row, col_map))
            except (KeyError, ValueError, ArithmeticError) as exc:
                logger.warning(
                    "Skipping invalid row",
                    file=str(path),
                    row=row_num,
                    error=str(exc),
                )

    bars.sort(key=lambda b: b.timestamp)
    logger.info("Loaded bars from CSV", file=str(path), count=len(bars))
    return bars


def load_bars_from_parquet(
    file_path: str | Path,
    *,
    columns: dict[str, str] | None = None,
) -> list[OHLCVBar]:
    """Load all OHLCV bars from a Parquet file.

    Requires pyarrow to be installed. Parquet is preferred for large datasets
    due to columnar compression and faster I/O.

    Args:
        file_path: Path to the Parquet file.
        columns: Optional mapping from canonical names to actual column names.

    Returns:
        List of OHLCVBar instances sorted by timestamp ascending.

    Raises:
        FileNotFoundError: If the file does not exist.
        ImportError: If pyarrow is not installed.
    """
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise ImportError(
            "pyarrow is required to load Parquet files. "
            "Install it with: pip install pyarrow"
        ) from exc

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Parquet file not found: {path}")

    col_map = {**_DEFAULT_COLUMNS, **(columns or {})}
    table = pq.read_table(str(path), columns=list(col_map.values()))
    df_dict = table.to_pydict()

    row_count = len(df_dict[col_map["timestamp"]])
    bars: list[OHLCVBar] = []

    for i in range(row_count):
        try:
            bars.append(
                OHLCVBar(
                    timestamp=int(df_dict[col_map["timestamp"]][i]),
                    open=_to_decimal(df_dict[col_map["open"]][i]),
                    high=_to_decimal(df_dict[col_map["high"]][i]),
                    low=_to_decimal(df_dict[col_map["low"]][i]),
                    close=_to_decimal(df_dict[col_map["close"]][i]),
                    volume=_to_decimal(df_dict[col_map["volume"]][i]),
                )
            )
        except (KeyError, ValueError, ArithmeticError) as exc:
            logger.warning(
                "Skipping invalid Parquet row",
                file=str(path),
                row=i,
                error=str(exc),
            )

    bars.sort(key=lambda b: b.timestamp)
    logger.info("Loaded bars from Parquet", file=str(path), count=len(bars))
    return bars


def iter_bars_from_csv(
    file_path: str | Path,
    *,
    columns: dict[str, str] | None = None,
) -> Iterator[OHLCVBar]:
    """Stream OHLCV bars from a CSV file one at a time.

    Memory-efficient alternative for very large datasets. Bars are yielded
    in file order; caller is responsible for ensuring chronological ordering.

    Args:
        file_path: Path to the CSV file.
        columns: Optional column name mapping.

    Yields:
        OHLCVBar instances one at a time.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    col_map = {**_DEFAULT_COLUMNS, **(columns or {})}

    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row_num, row in enumerate(reader, start=2):
            try:
                yield _row_to_bar(row, col_map)
            except (KeyError, ValueError, ArithmeticError) as exc:
                logger.warning(
                    "Skipping invalid row in stream",
                    file=str(path),
                    row=row_num,
                    error=str(exc),
                )
