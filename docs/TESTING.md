# Testing

Use pytest for unit and CLI contract tests. Keep fixtures synthetic and isolated from user repositories. Test observable behavior, including exit codes, stable model serialization, and privacy boundaries. API tests use recorded responses; standard test runs must not require network access or credentials.

Follow test-first development: add a focused failing test, run it, implement the minimum behavior, then run the focused test and full suite. Cross-platform behavior is checked by CI on Windows and Linux.
