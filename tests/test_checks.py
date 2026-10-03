import pytest

from nova_eink_display.checks import Check, State, evaluate_checks, summarise
from nova_eink_display.screens.main_screen import MainScreen

OK = {
    "backup_status": 1.0,
    "backup_age": 14400.0,
    "updates_pending": 0.0,
    "updates_security": 0.0,
    "reboot_required": 0.0,
    "services_total": 18.0,
    "services_bad": 0.0,
    "cert_days": 41.0,
}

SECURITY = {"updates_pending": 14.0, "updates_security": 3.0}


def by_label(stats) -> dict[str, Check]:
    return {c.label: c for c in evaluate_checks(stats)}


def test_a_healthy_homelab_has_nothing_bad() -> None:
    checks = evaluate_checks(OK)

    assert summarise(checks) == (0, 5)
    assert all(c.state is State.OK and not c.notice for c in checks)


@pytest.mark.parametrize(
    ("description", "stats", "label", "detail"),
    [
        ("a failed backup", {**OK, "backup_status": 0.0}, "BKP", "4h"),
        ("a stale backup", {**OK, "backup_age": 180000.0}, "BKP", "2d"),
        ("an unhealthy container", {**OK, "services_bad": 2.0}, "SVC", "16/18"),
        ("a cert about to expire", {**OK, "cert_days": 6.0}, "SSL", "6d"),
    ],
)
def test_each_failure_is_detected(
    description: str, stats: dict, label: str, detail: str
) -> None:
    check = by_label(stats)[label]

    assert check.state is State.BAD, description
    assert check.detail == detail


@pytest.mark.parametrize(
    ("stats", "label", "detail"),
    [
        ({**OK, **SECURITY}, "UPD", "14 +3!"),
        ({**OK, "reboot_required": 1.0}, "REBOOT", "PENDING"),
    ],
)
def test_updates_and_reboots_are_only_notices(
    stats: dict, label: str, detail: str
) -> None:
    check = by_label(stats)[label]

    assert check.state is State.OK
    assert check.notice
    assert check.detail == detail


def test_a_successful_but_stale_backup_is_still_bad() -> None:
    assert by_label({**OK, "backup_age": 180000.0})["BKP"].state is State.BAD


@pytest.mark.parametrize(
    ("description", "stats", "state"),
    [
        ("flag absent, run fresh", {"backup_age": 14400.0}, State.UNKNOWN),
        ("flag absent, run stale", {"backup_age": 180000.0}, State.BAD),
        ("flag ok, age absent", {"backup_status": 1.0}, State.OK),
        ("flag failed, age absent", {"backup_status": 0.0}, State.BAD),
    ],
)
def test_backup_with_one_metric_missing(
    description: str, stats: dict, state: State
) -> None:
    base = {k: v for k, v in OK.items() if k not in ("backup_status", "backup_age")}

    assert by_label({**base, **stats})["BKP"].state is state, description


def test_non_security_updates_are_a_notice() -> None:
    check = by_label({**OK, "updates_pending": 42.0})["UPD"]

    assert check.state is State.OK
    assert check.notice
    assert check.detail == "42"


@pytest.mark.parametrize("label", ["BKP", "UPD", "REBOOT", "SVC", "SSL"])
def test_a_check_with_no_data_is_unknown_not_bad(label: str) -> None:
    check = by_label({})[label]

    assert check.state is State.UNKNOWN
    assert check.known is False
    assert check.detail == "--"


def test_unknown_checks_count_as_neither() -> None:
    assert summarise(evaluate_checks({})) == (0, 0)


def test_order_is_bad_then_unknown_then_notices_then_quiet() -> None:
    stats = {k: v for k, v in OK.items() if k != "cert_days"}
    stats = {**stats, **SECURITY, "reboot_required": 1.0, "services_bad": 1.0}

    order = [c.label for c in evaluate_checks(stats)]

    assert order == ["SVC", "SSL", "UPD", "REBOOT", "BKP"]


@pytest.mark.parametrize(
    ("stats", "banner"),
    [
        (OK, "ALL 5 OK"),
        ({**OK, **SECURITY, "reboot_required": 1.0}, "ALL 5 OK"),
        ({**OK, **SECURITY, "services_bad": 1.0}, "1 OF 5 BAD"),
        ({k: v for k, v in OK.items() if k != "cert_days"}, "4 OF 5 OK"),
        (
            {k: v for k, v in OK.items() if k != "cert_days"} | {"services_bad": 1.0},
            "1 OF 5 BAD",
        ),
        ({}, "NO DATA"),
    ],
)
def test_banner_counts_out_of_every_check(stats: dict, banner: str) -> None:
    assert MainScreen.status_banner(evaluate_checks(stats)) == banner


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0.0, "0h"), (3599.0, "0h"), (14400.0, "4h"), (172800.0, "2d"), (-1.0, "--")],
)
def test_ages_read_as_hours_then_days(seconds: float, expected: str) -> None:
    assert by_label({**OK, "backup_age": seconds})["BKP"].detail == expected
