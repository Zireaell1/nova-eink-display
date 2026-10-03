from dataclasses import dataclass
from enum import IntEnum


class State(IntEnum):
    BAD = 0
    UNKNOWN = 1
    OK = 2


@dataclass(frozen=True)
class Check:
    label: str
    state: State
    detail: str
    notice: bool = False

    @property
    def known(self) -> bool:
        return self.state is not State.UNKNOWN


def _age(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "--"

    hours = int(seconds // 3600)
    if hours < 48:
        return f"{hours}h"

    return f"{hours // 24}d"


def _backup(stats):
    status = stats.get("backup_status")
    age = stats.get("backup_age")

    if status is None and age is None:
        return Check("BKP", State.UNKNOWN, "--")

    stale = age is not None and age >= 30 * 3600
    if status == 0 or stale:
        return Check("BKP", State.BAD, _age(age))

    if status is None:
        return Check("BKP", State.UNKNOWN, _age(age))

    return Check("BKP", State.OK, _age(age))


def _updates(stats):
    pending = stats.get("updates_pending")
    security = stats.get("updates_security")

    if pending is None and security is None:
        return Check("UPD", State.UNKNOWN, "--")

    total = int(pending or 0)
    secure = int(security or 0)
    detail = f"{total}" if not secure else f"{total} +{secure}!"

    return Check("UPD", State.OK, detail, notice=total > 0)


def _reboot(stats):
    required = stats.get("reboot_required")
    if required is None:
        return Check("REBOOT", State.UNKNOWN, "--")

    if required < 1:
        return Check("REBOOT", State.OK, "NO")

    return Check("REBOOT", State.OK, "PENDING", notice=True)


def _services(stats):
    total = stats.get("services_total")
    bad = stats.get("services_bad")

    if total is None:
        return Check("SVC", State.UNKNOWN, "--")

    bad = int(bad or 0)
    state = State.OK if bad == 0 else State.BAD
    return Check("SVC", state, f"{int(total) - bad}/{int(total)}")


def _certs(stats):
    days = stats.get("cert_days")
    if days is None:
        return Check("SSL", State.UNKNOWN, "--")

    state = State.OK if days >= 14 else State.BAD
    return Check("SSL", state, f"{int(days)}d")


BUILDERS = (_services, _backup, _updates, _reboot, _certs)


def evaluate_checks(stats) -> list[Check]:
    checks = (build(stats) for build in BUILDERS)
    return sorted(checks, key=lambda c: (c.state, not c.notice))


def summarise(checks) -> tuple[int, int]:
    known = [c for c in checks if c.known]
    return sum(1 for c in known if c.state is State.BAD), len(known)
