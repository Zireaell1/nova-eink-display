import pytest

from nova_eink_display.alerts import ALERT_RULES, evaluate_alerts
from nova_eink_display.screens.main_screen import MainScreen

WIDTH = 14


@pytest.mark.parametrize(
    ("cpu", "expected"),
    [
        (90.0, []),
        (90.4, []),
        (90.5, []),
        (90.6, ["CPU 91%"]),
        (97.0, ["CPU 97%"]),
    ],
)
def test_the_threshold_is_judged_on_the_value_shown(
    cpu: float, expected: list[str]
) -> None:
    assert evaluate_alerts({"cpu": cpu}) == expected


def test_alerts_keep_rule_order() -> None:
    stats = {"cpu": 97.0, "mem": 95.0, "backup_status": 0.0, "ups_on_battery": 1.0}

    assert evaluate_alerts(stats) == [
        "UPS ON BATTERY",
        "CPU 97%",
        "MEM 95%",
        "BACKUP FAILED",
    ]


def test_every_message_fits_one_line() -> None:
    worst = {"cpu": 100.0, "mem": 100.0, "backup_status": 0.0, "ups_on_battery": 1.0}

    assert len(ALERT_RULES) == 4
    assert all(len(f"{a}") <= WIDTH for a in evaluate_alerts(worst))
    assert len(MainScreen.alert_lines(evaluate_alerts(worst), WIDTH)) == 4


def test_overflow_cuts_between_alerts_never_inside_one() -> None:
    alerts = ["PROMETHEUS UNREACHABLE", "BACKUP FAILED", "CPU 97%", "MEM 95%"]

    assert MainScreen.alert_lines(alerts, WIDTH) == [
        "> PROMETHEUS",
        "  UNREACHABLE",
        "> BACKUP FAILED",
        "+ 2 MORE",
    ]


def test_a_single_overlong_alert_is_still_shown() -> None:
    alerts = ["A" * 14 + " " + "B" * 14 + " " + "C" * 14 + " " + "D" * 14, "CPU 97%"]
    lines = MainScreen.alert_lines(alerts, WIDTH)

    assert lines[0] == "> " + "A" * 14
    assert lines[-1] == "+ 1 MORE"
    assert len(lines) == 4
