import argparse
import datetime
import pathlib
import sys
from zoneinfo import ZoneInfo

from PIL import Image, ImageChops

from nova_eink_display.alerts import evaluate_alerts
from nova_eink_display.config import BASE_DIR, QUERIES
from nova_eink_display.renderer import UIRenderer

DEFAULT_OUT = pathlib.Path(BASE_DIR) / "frames"

RENDER_TZ = ZoneInfo("Europe/Warsaw")
DAY = datetime.datetime(2026, 3, 17, 14, 5, tzinfo=RENDER_TZ)

OK = {
    "cpu": 12.3,
    "mem": 41.7,
    "ups_charge": 100.0,
    "uptime": 950000.0,
    "backup_status": 1.0,
}


def state(name, stats, error=None, now=DAY):
    missing = sorted(set(QUERIES) - set(stats))
    return name, {"stats": stats, "error": error, "missing": missing}, now


STATES = [
    # --- values -----------------------------------------------------------
    state("nominal", OK),
    state("zero", {**OK, "cpu": 0.0, "mem": 0.0, "uptime": 60.0}),
    state("full", {**OK, "cpu": 100.0, "mem": 99.6}),
    # --- absent metrics ---------------------------------------------------
    state("missing-ups", {k: v for k, v in OK.items() if k != "ups_charge"}),
    state("missing-backup", {k: v for k, v in OK.items() if k != "backup_status"}),
    state("missing-uptime", {k: v for k, v in OK.items() if k != "uptime"}),
    state("missing-all", {}),
    # --- alerts -----------------------------------------------------------
    state("alert-backup", {**OK, "backup_status": 0.0}),
    state("alert-ups", {**OK, "ups_charge": 82.0}),
    state("alert-many", {**OK, "cpu": 97.0, "mem": 95.0, "backup_status": 0.0}),
    # --- transport failures ----------------------------------------------
    state("err-unreachable", {}, "Prometheus Unreachable"),
    state("err-query", {}, "Query Error"),
    # --- character moods, pinned by clock ---------------------------------
    state("mood-sleep", OK, now=DAY.replace(hour=2)),
    state("mood-coffee", OK, now=DAY.replace(hour=7)),
    state("mood-salute", {**OK, "uptime": 120.0}),
    state("mood-working", {**OK, "cpu": 88.0}),
    state("mood-concerned", {**OK, "cpu": 78.0}),
    state("mood-idle", OK, now=DAY.replace(hour=15, minute=25)),
    # The idle pool is picked by random.Random(f"{date}_{hour}_{minute//10}"),
    # so a pinned clock pins the reaction. These three cover the whole pool.
    state("mood-happy", OK, now=DAY.replace(hour=9, minute=55)),
    state("mood-music", OK, now=DAY.replace(hour=9, minute=5)),
    state("mood-smug", OK, now=DAY.replace(hour=9, minute=25)),
    # --- hostile values ---------------------------------------------------
    state("odd-values", {**OK, "cpu": 80.0, "mem": -3.0, "uptime": -5.0}),
    state("threshold-edge", {**OK, "cpu": 90.0, "mem": 89.9}),
]


def extra_frames(invert=False):
    return {
        "offline": UIRenderer(296, 128).render_offline_frame(DAY, invert=invert),
    }


def render(out_dir, blink=False, invert=False):
    ui = UIRenderer(296, 128)
    out_dir.mkdir(parents=True, exist_ok=True)

    frames = {}
    for name, data, now in STATES:
        alerts = evaluate_alerts(data["stats"])
        if data["error"]:
            alerts.insert(0, f"API ERR: {data['error']}")
        image = ui.render_frame(data, alerts, is_blinking=blink, now=now, invert=invert)
        image.save(out_dir / f"{name}.png")
        frames[name] = image

    for name, image in extra_frames(invert=invert).items():
        image.save(out_dir / f"{name}.png")
        frames[name] = image

    return frames


def build_overview(frames, path, cols=3, pad=6, scale=2):
    w, h = 296, 128
    rows = (len(frames) + cols - 1) // cols
    overview = Image.new("L", (cols * (w + pad) + pad, rows * (h + pad) + pad), 150)

    for i, image in enumerate(frames.values()):
        xy = (pad + (i % cols) * (w + pad), pad + (i // cols) * (h + pad))
        overview.paste(image.convert("L"), xy)

    overview.resize(
        (overview.width * scale, overview.height * scale), Image.Resampling.NEAREST
    ).save(path)


def compare(frames, golden_dir):
    failures = []

    for name, image in frames.items():
        path = golden_dir / f"{name}.png"
        if not path.exists():
            failures.append(f"{name}: no golden frame at {path}")
            continue
        if ImageChops.difference(
            image.convert("L"), Image.open(path).convert("L")
        ).getbbox():
            failures.append(f"{name}: differs from golden frame")

    for path in sorted(golden_dir.glob("*.png")):
        if path.stem not in frames and path.stem != "all-states":
            failures.append(f"{path.stem}: golden frame has no matching state")

    return failures


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Render every dashboard state to PNG, with no hardware and no "
            "Prometheus. Nothing here reads the environment: the clock is "
            "pinned per state, the output directory is repo-rooted and "
            "inversion is a flag, so no .env edit can move a pixel."
        )
    )
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        default=DEFAULT_OUT,
        help=f"output directory (default: {DEFAULT_OUT})",
    )
    parser.add_argument("--blink", action="store_true", help="render blink variants")
    parser.add_argument(
        "--invert",
        action="store_true",
        help="render the inverted look",
    )
    parser.add_argument(
        "--golden",
        type=pathlib.Path,
        help="compare against golden frames in this directory and exit non-zero on drift",
    )
    parser.add_argument("--no-overview", action="store_true")
    args = parser.parse_args()

    out = args.out.resolve()

    frames = render(out, blink=args.blink, invert=args.invert)
    print(f"rendered {len(frames)} states -> {out}")

    if not args.no_overview:
        build_overview(frames, out / "all-states.png")
        print(f"overview         -> {out / 'all-states.png'}")

    if args.golden:
        failures = compare(frames, args.golden)
        for line in failures:
            print(f"  FAIL {line}")
        if failures:
            print(f"\n{len(failures)} frame(s) drifted. Review the uploaded artifact;")
            print(f"if the change is intended: cp {out}/*.png {args.golden}/")
            return 1
        print(f"all {len(frames)} frames match {args.golden}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
