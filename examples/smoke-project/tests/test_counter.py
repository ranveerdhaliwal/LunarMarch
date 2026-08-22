import unittest

from counter import clamp_count, increment


class CounterTests(unittest.TestCase):
    def test_increment(self) -> None:
        self.assertEqual(increment(2), 3)

    def test_clamp_inside_range(self) -> None:
        self.assertEqual(clamp_count(5, 1, 10), 5)

    def test_clamp_below_range(self) -> None:
        self.assertEqual(clamp_count(-2, 1, 10), 1)

    def test_clamp_above_range(self) -> None:
        self.assertEqual(clamp_count(12, 1, 10), 10)

    def test_invalid_range(self) -> None:
        with self.assertRaises(ValueError):
            clamp_count(4, 10, 1)


if __name__ == "__main__":
    unittest.main()
