from .base import EnrichmentResult


class StubProvider:
    """No-op provider for tests and disabled enrichment."""

    def enrich(self, ips: list[str]) -> dict[str, EnrichmentResult]:
        return {}
