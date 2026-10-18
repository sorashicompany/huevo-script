"""Headless Linux runner for HuevoBottle.

Requires Playwright and a Chromium browser installed by the host.
Set PLAYWRIGHT_BROWSERS_PATH if the host stores browsers in a custom location.
The first run may require interactive login; this script does not bypass CAPTCHAs.
"""
from __future__ import annotations

import os
import sys
import time
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

BOTTLE_URL = "https://huevo.su/apps/3"
PROFILE_DIR = Path(os.environ.get("BOTTLE_PROFILE_DIR", "./bottle-profile"))
POLL_SECONDS = float(os.environ.get("POLL_SECONDS", "1.0"))
SWITCH_TABLES = os.environ.get("SWITCH_TABLES", "0").lower() in {"1", "true", "yes"}
HEADLESS = os.environ.get("HEADLESS", "1").lower() not in {"0", "false", "no"}


def log(message: str) -> None:
    print(time.strftime("[%Y-%m-%d %H:%M:%S]"), message, flush=True)


def main() -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        # Download Playwright's Chromium on first boot if the host image lacks it.
        browser_executable = Path(p.chromium.executable_path)
        if not browser_executable.exists():
            log("Chromium headless shell is missing; downloading the smaller headless browser (first start may take a while).")
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium", "--only-shell"],
                check=True,
                timeout=600,
            )
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=HEADLESS,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
            viewport={"width": 1280, "height": 800},
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(BOTTLE_URL, wait_until="domcontentloaded", timeout=60000)
            log("Opened HuevoBottle page. If login or verification is required, complete it through a supported interactive session.")
            while True:
                try:
                    frame = page.frame_locator("iframe#apps-game-frame")
                    if SWITCH_TABLES:
                        empty = frame.locator(".btg-card.is-empty[data-sit-seat]")
                        occupied = frame.locator(".btg-card[data-seat][data-seat-uid]")
                        seats = frame.locator(".btg-card.is-empty[data-sit-seat], .btg-card[data-seat][data-seat-uid]")
                        if seats.count() == 8:
                            empty_count = empty.count()
                            occupied_count = occupied.count()
                            if occupied_count <= 1 and empty_count == 8 - occupied_count:
                                switch = frame.locator("#bt-switch")
                                if switch.count() and switch.is_visible() and switch.is_enabled():
                                    switch.click(timeout=2000)
                                    log(f"Switched table (occupied seats: {occupied_count})")
                                    time.sleep(1.2)
                                    continue

                    play = frame.locator("#bt-play")
                    yes = frame.locator("#bt-yes")
                    spin = frame.locator("#bt-spin")
                    if play.count() and play.is_visible() and play.is_enabled():
                        play.click(timeout=2000)
                        log("Clicked Play")
                    elif yes.count() and yes.is_visible() and yes.is_enabled():
                        yes.click(timeout=2000)
                        log("Clicked Yes/Kiss")
                    elif spin.count() and spin.is_visible() and spin.is_enabled():
                        spin.click(timeout=2000)
                        log("Clicked Spin")
                except PlaywrightTimeoutError:
                    log("A game action timed out; will retry.")
                except Exception as exc:
                    # Keep the process alive through temporary page/network errors.
                    log(f"Temporary error: {type(exc).__name__}: {exc}")
                time.sleep(POLL_SECONDS)
        finally:
            context.close()


if __name__ == "__main__":
    main()
