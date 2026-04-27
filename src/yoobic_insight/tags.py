from __future__ import annotations

from dataclasses import dataclass
import re

from yoobic_insight.payload import StoreWeekPayload

STRONG_DECLINE_THRESHOLD = -0.1
DOMINANT_DRIVER_THRESHOLD = 50.0

SEVERITY_HIGH = 1
SEVERITY_MEDIUM = 2
SEVERITY_LOW = 3


@dataclass(frozen=True)
class Tag:
    id: str
    severity: int
    kpi: str | None
    message_template: str


def generate_tags(payload: StoreWeekPayload) -> list[Tag]:
    tags: list[Tag] = []

    tags.extend(_sales_decline_tags(payload))
    tags.extend(_ly_baseline_tags(payload))
    tags.extend(_dq_caveat_tags(payload))
    tags.extend(_network_underperformance_tags(payload))

    return sorted(tags, key=lambda tag: (tag.severity, tag.id))


def _sales_decline_tags(payload: StoreWeekPayload) -> list[Tag]:
    net_sales_yoy = payload.yoy.get("net_sales")
    if net_sales_yoy is None or net_sales_yoy > STRONG_DECLINE_THRESHOLD:
        return []

    tags = [
        Tag(
            id="sales_yoy_strong_decline",
            severity=SEVERITY_HIGH,
            kpi="net_sales",
            message_template="Net sales fell sharply year over year.",
        )
    ]

    driver = _dominant_negative_driver(payload.driver_attribution)
    if driver is not None:
        tags.append(
            Tag(
                id=f"{driver}_drove_decline",
                severity=SEVERITY_MEDIUM,
                kpi=driver,
                message_template=f"{_label(driver)} was the dominant driver of the sales decline.",
            )
        )

    return tags


def _ly_baseline_tags(payload: StoreWeekPayload) -> list[Tag]:
    tags: list[Tag] = []
    for flag in payload.flags:
        prefix = "ly_baseline_abnormal_"
        if not flag.startswith(prefix):
            continue

        kpi = flag[len(prefix) :]
        tags.append(
            Tag(
                id=f"ly_baseline_suspect_{kpi}",
                severity=SEVERITY_HIGH,
                kpi=kpi,
                message_template=f"Last year's {_label(kpi)} baseline may be abnormal.",
            )
        )
    return tags


def _dq_caveat_tags(payload: StoreWeekPayload) -> list[Tag]:
    tags: list[Tag] = []
    for caveat in payload.dq_caveats:
        kind = caveat.split(":", 1)[0].strip()
        slug = _slugify(kind or caveat)
        tags.append(
            Tag(
                id=f"dq_caveat_{slug}",
                severity=SEVERITY_HIGH,
                kpi=None,
                message_template=f"Data quality caveat: {kind or caveat}.",
            )
        )
    return tags


def _network_underperformance_tags(payload: StoreWeekPayload) -> list[Tag]:
    tags: list[Tag] = []
    for kpi, gap in payload.store_vs_network.items():
        if gap is None:
            continue

        mad = payload.network_mad.get(kpi)
        if _is_underperforming(float(gap), mad):
            tags.append(
                Tag(
                    id=f"network_underperform_{kpi}",
                    severity=SEVERITY_LOW,
                    kpi=kpi,
                    message_template=f"{_label(kpi)} was below the weekly network benchmark.",
                )
            )
    return tags


def _dominant_negative_driver(driver_attribution: dict[str, float | None]) -> str | None:
    strongest_driver: str | None = None
    strongest_share = DOMINANT_DRIVER_THRESHOLD
    for driver, share in driver_attribution.items():
        if share is None or share < strongest_share:
            continue
        strongest_driver = driver
        strongest_share = float(share)
    return strongest_driver


def _is_underperforming(gap: float, mad: float | None) -> bool:
    if gap >= 0:
        return False
    if mad is None:
        return True
    if mad <= 0:
        return True
    return abs(gap) >= mad


def _label(value: str) -> str:
    return value.replace("_", " ")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "unknown"
