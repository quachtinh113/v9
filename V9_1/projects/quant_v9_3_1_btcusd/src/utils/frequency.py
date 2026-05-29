"""Utility module for normalising pandas frequency strings.

The project historically used deprecated pandas aliases like "1H" or "5T".
These strings are no longer accepted by pandas and must be converted to
their modern equivalents ("1h", "5min", etc.).  MT5‑specific timeframe
constants such as "H1", "M15" are deliberately left untouched.
"""

def normalize_pandas_frequency(freq: str) -> str:
    """Return the pandas‑compatible frequency string.

    Args:
        freq: The original frequency token (e.g. "1H", "15T").

    Returns:
        The updated token (e.g. "1h", "15min") if a mapping exists,
        otherwise the original value unchanged.
    """
    mapping = {
        "1H": "1h",
        "2H": "2h",
        "4H": "4h",
        "6H": "6h",
        "8H": "8h",
        "12H": "12h",
        "1T": "1min",
        "5T": "5min",
        "15T": "15min",
        "30T": "30min",
    }
    return mapping.get(freq, freq)

__all__ = ["normalize_pandas_frequency"]
