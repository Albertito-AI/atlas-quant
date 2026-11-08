"""Malformed inputs must be rejected before research begins."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from atlas_quant.data import PriceDataset, load_prices_csv, synthetic_prices


class DataTests(unittest.TestCase):
    def write_csv(self, content):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "prices.csv"
        path.write_text(content, encoding="utf-8")
        return path

    def test_csv_valid(self):
        data = load_prices_csv(self.write_csv("date,A,B\n2024-01-02,100,50\n2024-01-03,101,49\n"))
        self.assertEqual(data.symbols, ("A", "B"))
        self.assertEqual(data.prices.shape, (2, 2))
        self.assertFalse(data.synthetic)

    def test_missing_and_extra_columns_rejected(self):
        for row in ("2024-01-03,101", "2024-01-03,101,", "2024-01-03,101,40,50"):
            with self.subTest(row=row), self.assertRaises(ValueError):
                load_prices_csv(self.write_csv("date,A,B\n2024-01-02,100,50\n" + row + "\n"))

    def test_bad_numbers_rejected(self):
        for value in ("nan", "inf", "-1", "0", "hello", "=IMPORTXML(x)"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                load_prices_csv(self.write_csv("date,A\n2024-01-02,100\n2024-01-03," + value + "\n"))

    def test_dates_must_be_unique_increasing_canonical(self):
        for value in ("2024-01-02", "2024-01-01", "20240103", "2024-13-03", "yesterday"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                load_prices_csv(self.write_csv("date,A\n2024-01-02,100\n" + value + ",101\n"))

    def test_symbols_reject_duplicates_and_formula_markers(self):
        for header in ("date,A,A", "date,=SUM(A1),B", "date,A, B", "date,,B"):
            with self.subTest(header=header), self.assertRaises(ValueError):
                load_prices_csv(self.write_csv(header + "\n2024-01-02,100,50\n2024-01-03,101,51\n"))

    def test_no_mutation_through_original_input(self):
        prices = np.array([[100.], [101.]])
        data = PriceDataset(("2024-01-02", "2024-01-03"), ("A",), prices, "fixture")
        prices[0, 0] = 1
        self.assertEqual(data.prices[0, 0], 100)
        with self.assertRaises(ValueError):
            data.prices[0, 0] = 1

    def test_dataset_shape_and_types(self):
        for prices in ([1, 2], [[1, 2], [3, 4]], [[1], [float('nan')]]):
            with self.subTest(prices=prices), self.assertRaises(ValueError):
                PriceDataset(("2024-01-02", "2024-01-03"), ("A",), prices, "fixture")

    def test_dataset_rejects_coerced_prices(self):
        # Complex arrays previously lost their imaginary part with only a
        # warning. Boolean, textual and object arrays are also not real prices.
        for prices in (np.array([[100 + 2j], [101 + 3j]]),
                       np.array([[100 + 0j], [101 + 0j]]),
                       np.array([[True], [True]]),
                       np.array([["100"], ["101"]]),
                       np.array([[100.], [101.]], dtype=object)):
            with self.subTest(dtype=prices.dtype), self.assertRaises(ValueError):
                PriceDataset(("2024-01-02", "2024-01-03"), ("A",), prices, "fixture")

    def test_dataset_preserves_supported_real_price_dtypes(self):
        for dtype in (np.int32, np.uint32, np.float32, np.float64):
            with self.subTest(dtype=dtype):
                data = PriceDataset(("2024-01-02", "2024-01-03"), ("A",),
                                    np.array([[100], [101]], dtype=dtype), "fixture")
                np.testing.assert_array_equal(data.prices, [[100.], [101.]])
                self.assertEqual(data.prices.dtype, np.dtype(float))

    def test_limits(self):
        path = self.write_csv("date,A,B\n2024-01-02,100,50\n2024-01-03,101,51\n")
        for kwargs in ({"max_rows": 1}, {"max_assets": 1}, {"max_assets": 101}, {"max_rows": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                load_prices_csv(path, **kwargs)

    def test_synthetic_reproducible_and_labelled(self):
        one, two = synthetic_prices(20, 3, 42), synthetic_prices(20, 3, 42)
        np.testing.assert_array_equal(one.prices, two.prices)
        self.assertEqual(one.sha256, two.sha256)
        self.assertNotEqual(one.sha256, synthetic_prices(20, 3, 43).sha256)
        self.assertTrue(one.synthetic)
        self.assertEqual(one.metadata()["observations"], 20)
        self.assertTrue(all(s.startswith("SYNTH_") for s in one.symbols))

    def test_synthetic_validation(self):
        for args in ((1, 3, 1), (20, 0, 1), (20, 3, -1), (20.5, 3, 1), (20, 3, True)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                synthetic_prices(*args)

    def test_digest_changes_with_calendar_or_symbol(self):
        a = PriceDataset(("2024-01-02", "2024-01-03"), ("A",), [[1], [2]], "fixture")
        b = PriceDataset(("2024-01-02", "2024-01-04"), ("A",), [[1], [2]], "fixture")
        c = PriceDataset(a.dates, ("B",), a.prices, "fixture")
        self.assertNotEqual(a.sha256, b.sha256)
        self.assertNotEqual(a.sha256, c.sha256)

    def test_byte_limit_and_encoding_fail_closed(self):
        path = self.write_csv("date,A\n2024-01-02,100\n2024-01-03,101\n")
        with patch("atlas_quant.data.MAX_BYTES", 20), self.assertRaisesRegex(ValueError, "byte limit"):
            load_prices_csv(path)
        path.write_bytes(b"\xff\xfe")
        with self.assertRaisesRegex(ValueError, "UTF-8"):
            load_prices_csv(path)

    def test_provenance_label_and_symbol_type_validation(self):
        for source in ("\ninvalid", "   ", 1, "x" * 501):
            with self.subTest(source=source), self.assertRaises(ValueError):
                PriceDataset(("2024-01-02", "2024-01-03"), ("A",), [[1], [2]], source)
        with self.assertRaises(ValueError):
            PriceDataset(("2024-01-02", "2024-01-03"), (["A"],), [[1], [2]], "fixture")

    def test_empty_file_and_blank_row_rejected(self):
        for text in ("", "date,A\n", "date,A\n2024-01-02,10\n\n2024-01-03,20\n"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                load_prices_csv(self.write_csv(text))


if __name__ == "__main__":
    unittest.main()
