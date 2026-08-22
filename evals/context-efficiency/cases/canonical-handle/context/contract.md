Resolved product contract:

- Reject non-string inputs with `TypeError`.
- Trim outer whitespace, then remove at most one optional leading `@`.
- Normalize the remaining username with Unicode NFKC, then apply `casefold()`.
- The normalized username must contain only ASCII lowercase letters, digits, and underscore.
- Its length after normalization must be between 3 and 20 characters inclusive.
- Reject empty, malformed, too-short, or too-long usernames with `ValueError`.
- Return exactly one leading `@` followed by the normalized username.
- Do not add dependencies or change tests.
