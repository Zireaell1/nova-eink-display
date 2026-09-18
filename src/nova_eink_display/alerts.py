import logging

from nova_eink_display.config import ALERT_RULES

logger = logging.getLogger(__name__)


def evaluate_alerts(stats):
    active_alerts = []

    for key, (threshold, operator, message) in ALERT_RULES.items():
        if key not in stats:
            continue

        val = stats[key]
        if (operator == ">" and val > threshold) or (
            operator == "<" and val < threshold
        ):
            active_alerts.append(f"{message} ({int(val)})")

    return active_alerts
