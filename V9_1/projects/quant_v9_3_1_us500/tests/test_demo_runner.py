from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.run_demo import latest_signal


def test_latest_signal_shape():
    root = Path(__file__).resolve().parents[1]
    signal = latest_signal(root)
    assert signal['symbol'] == 'US500'
    assert 'direction' in signal
    assert 'score' in signal
