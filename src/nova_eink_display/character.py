import random

IDLE_POOL = ("happy", "music", "smug")


def choose_pose(stats, sys_error, active_alerts, now) -> str:
    if sys_error:
        return "disconnected"

    if active_alerts:
        return "concerned"  # TODO: panicked

    cpu = stats.get("cpu", 0)
    mem = stats.get("mem", 0)

    if cpu > 85 or mem > 90:
        return "working"

    if cpu > 75 or mem > 80:
        return "concerned"

    if stats.get("uptime", 3600) < 300:
        return "salute"

    hour = now.hour

    if hour >= 23 or hour < 6:
        return "sleep"

    if 6 <= hour < 9:
        return "coffee"

    minute_block = now.minute // 10
    seed = f"{now.date()}_{hour}_{minute_block}"
    return random.Random(seed).choice(IDLE_POOL)
