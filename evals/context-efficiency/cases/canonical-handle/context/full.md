Raw chronological product discussion:

1. An early sketch proposed preserving case and allowing hyphens. This was exploratory, not final.
2. Another participant suggested accepting any object with `str(value)`. Security review rejected that because accidental numeric identifiers must not silently become accounts.
3. The first length proposal was 2 through 30 characters. UI and database owners later replaced it with 3 through 20.
4. One prototype stripped every `@` character. Review found that malformed double prefixes should be rejected instead.
5. Internationalization review requested Unicode NFKC before case normalization so compatibility-width Latin input behaves consistently.
6. Search indexing requires Unicode `casefold()`, not only `lower()`.
7. The storage key remains intentionally narrow: after normalization it permits only ASCII lowercase letters, digits, and underscore. Hyphens and internal spaces are not accepted.
8. Outer whitespace may be trimmed. Internal whitespace remains invalid.
9. The API returns exactly one `@` prefix. It may consume at most one optional input prefix.
10. Non-string input raises `TypeError`; malformed or length-invalid string input raises `ValueError`.
11. Final length is measured after prefix removal, NFKC, and case folding. Bounds are inclusive at 3 and 20.
12. The helper must remain dependency-free and the existing tests must not be edited.

The decisions above are final where they explicitly replace earlier proposals. The remaining meeting transcript below is retained for audit history but does not change this helper's contract.
