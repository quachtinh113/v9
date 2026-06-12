import unittest
from utils.frequency import normalize_pandas_frequency

class TestFrequencyNormalizer(unittest.TestCase):
    def test_pandas_aliases(self):
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
        for inp, exp in mapping.items():
            with self.subTest(inp=inp):
                self.assertEqual(normalize_pandas_frequency(inp), exp)

    def test_mt5_constants_unchanged(self):
        for const in ["H1", "H4", "M1", "M5", "M15", "M30"]:
            with self.subTest(const=const):
                self.assertEqual(normalize_pandas_frequency(const), const)

if __name__ == "__main__":
    unittest.main()
