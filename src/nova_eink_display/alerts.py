from dataclasses import dataclass


@dataclass(frozen=True)
class Rule:
    threshold: float
    op: str
    message: str
    fmt: str | None = None


ALERT_RULES = {
    "cpu": Rule(90.0, ">", "CPU Usage CRITICAL", "{v:.0f}%"),
    "mem": Rule(90.0, ">", "RAM Usage CRITICAL", "{v:.0f}%"),
    "ups_charge": Rule(95.0, "<", "UPS on Battery Power!", "{v:.0f}%"),
    "backup_status": Rule(1, "<", "BACKUP FAILED"),
}


def evaluate_alerts(stats):
    active_alerts = []

    for key, rule in ALERT_RULES.items():
        if key not in stats:
            continue

        val = stats[key]
        if (rule.op == ">" and val > rule.threshold) or (
            rule.op == "<" and val < rule.threshold
        ):
            if rule.fmt:
                active_alerts.append(f"{rule.message} {rule.fmt.format(v=val)}")
            else:
                active_alerts.append(rule.message)

    return active_alerts
