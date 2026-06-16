import json
import urllib.error
import urllib.parse
import urllib.request
from urllib.request import Request

from django.conf import settings

from .base import EnrichmentResult

# Free HTTP-only endpoint (HTTPS requires a paid key). Server-to-server only.
_FIELDS = "countryCode,regionName,city,timezone,isp,as,proxy,hosting,mobile,query,status"


class IpApiProvider:
    def __init__(self):
        self._base_url = getattr(settings, "METRICS_GEO_BASE_URL", "http://ip-api.com/batch")

    def enrich(self, ips: list[str]) -> dict[str, EnrichmentResult]:
        if not ips:
            return {}
        url = f"{self._base_url}?fields={_FIELDS}"
        payload = json.dumps(ips).encode()
        req = Request(
            url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
        except (urllib.error.URLError, OSError, ValueError):
            return {}

        results: dict[str, EnrichmentResult] = {}
        for entry in data:
            if entry.get("status") != "success":
                continue
            ip = entry.get("query", "")
            if not ip:
                continue
            results[ip] = EnrichmentResult(
                country_code=entry.get("countryCode", ""),
                region=entry.get("regionName", ""),
                city=entry.get("city", ""),
                timezone=entry.get("timezone", ""),
                isp=entry.get("isp", "") or entry.get("org", ""),
                asn=entry.get("as", ""),
                is_proxy=entry.get("proxy"),
                is_hosting=entry.get("hosting"),
                is_mobile=entry.get("mobile"),
            )
        return results
