from dataclasses import dataclass
from typing import Protocol


@dataclass
class EnrichmentResult:
    country_code: str = ""
    region: str = ""
    city: str = ""
    timezone: str = ""
    isp: str = ""
    asn: str = ""
    is_proxy: bool | None = None
    is_hosting: bool | None = None
    is_mobile: bool | None = None


class GeoProvider(Protocol):
    def enrich(self, ips: list[str]) -> dict[str, EnrichmentResult]: ...
