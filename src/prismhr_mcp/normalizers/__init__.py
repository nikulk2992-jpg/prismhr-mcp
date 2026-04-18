"""Pure functions that transform raw PrismHR payloads into structured insights.

These live outside `tools/` so they can be unit-tested without respx or async
boilerplate. Each normalizer takes plain dict/Decimal data and returns
Pydantic models defined under `models/`.
"""
