import unittest

from handles import canonical_handle


class HiddenHandleTests(unittest.TestCase):
    def test_non_string_rejected(self) -> None:
        with self.assertRaises(TypeError):
            canonical_handle(42)  # type: ignore[arg-type]

    def test_full_width_unicode_is_normalized(self) -> None:
        self.assertEqual(canonical_handle("Ａｌｉｃｅ"), "@alice")

    def test_casefold_occurs_before_validation(self) -> None:
        self.assertEqual(canonical_handle("Straße"), "@strasse")

    def test_hyphen_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            canonical_handle("alice-smith")

    def test_internal_space_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            canonical_handle("alice smith")

    def test_double_prefix_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            canonical_handle("@@alice")

    def test_too_short_after_normalization(self) -> None:
        with self.assertRaises(ValueError):
            canonical_handle("ab")

    def test_too_long_after_normalization(self) -> None:
        with self.assertRaises(ValueError):
            canonical_handle("abcdefghijklmnopqrstu")

    def test_inclusive_length_boundaries(self) -> None:
        self.assertEqual(canonical_handle("abc"), "@abc")
        self.assertEqual(canonical_handle("abcdefghijklmnopqrst"), "@abcdefghijklmnopqrst")

    def test_empty_after_optional_prefix_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            canonical_handle(" @ ")


if __name__ == "__main__":
    unittest.main()
