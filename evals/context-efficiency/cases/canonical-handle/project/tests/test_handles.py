import unittest

from handles import canonical_handle


class HandleTests(unittest.TestCase):
    def test_basic_name(self) -> None:
        self.assertEqual(canonical_handle("Alice"), "@alice")

    def test_existing_prefix_and_outer_space(self) -> None:
        self.assertEqual(canonical_handle("  @BOB_9 "), "@bob_9")


if __name__ == "__main__":
    unittest.main()
