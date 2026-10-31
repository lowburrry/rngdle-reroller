"""RNGdle reroller: does real guest rolls through the site's own Generate button.

Guest rolls are stored in localStorage (rngdle_guest_roll_data), so each attempt
clears storage, reloads, clicks Generate and reads back the stored result.

Usage:
  python reroll.py                 # roll until Ctrl+C
  python reroll.py -n 200 -w 4     # 200 rolls across 4 parallel tabs
  python reroll.py --headed        # show the browser windows
  python reroll.py --headed --watch     # show each full result for 3s
  python reroll.py --headed --watch 3   # shorter pause
  python reroll.py --headed --target 1500000   # stop at first roll over 1.5M XP
"""
import argparse
import asyncio
import json
import time

from playwright.async_api import async_playwright

URL = "https://www.rngdle.com/"
KEY = "rngdle_guest_roll_data"


class Tracker:
    def __init__(self, limit, target):
        self.limit = limit
        self.target = target
        self.hit = None  # (roll, context) of the first roll above target
        self.count = 0
        self.done = 0
        self.best = None
        self.log = None
        self.start = time.time()

    def claim(self):
        if self.hit or (self.limit and self.count >= self.limit):
            return False
        self.count += 1
        return True

    def record(self, roll):
        self.done += 1
        rate = self.done / (time.time() - self.start)
        new_best = self.best is None or roll["totalScore"] > self.best["totalScore"]
        if new_best:
            self.best = roll
        tag = "  <-- NEW BEST" if new_best else ""
        print(f"#{self.done:>5}  {roll['number']:>6}  {roll['totalScore']:>9,} XP  ({rate:.2f}/s){tag}")
        if self.log:
            self.log.write(f"{self.done},{roll['number']},{roll['totalScore']}\n")
            self.log.flush()
        return new_best


async def roll_once(page):
    # The site also keeps rngdle_guest_roll_date, so wipe everything to look like a fresh visitor.
    await page.evaluate("localStorage.clear(); sessionStorage.clear()")
    await page.goto(URL, wait_until="domcontentloaded")
    await page.get_by_role("button", name="Generate a new number").click()
    handle = await page.wait_for_function(f"localStorage.getItem('{KEY}')", timeout=30000)
    return json.loads(await handle.json_value())


async def wait_for_reveal(page, total):
    # The digits animate in, then the XP counter ticks up (the site labels it 'EP').
    try:
        await page.wait_for_function(
            "t => document.body.innerText.includes(t + ' EP')", arg=f"{total:,}", timeout=60000)
        await asyncio.sleep(1)  # let the badge cards finish fading in
    except Exception:
        pass


async def capture_full(page, total, path):
    await wait_for_reveal(page, total)
    try:
        # Rarity/percentile and "next roll in" show up after the counter finishes.
        await page.wait_for_function(
            "document.body.innerText.toUpperCase().includes('NEXT ROLL')", timeout=15000)
    except Exception:
        pass
    # The site scrolls inside an inner element, so full_page alone only gets the first screen.
    # Grow the viewport to the full content height, screenshot, then put it back.
    height = await page.evaluate("""Math.max(document.documentElement.scrollHeight,
        ...[...document.querySelectorAll('*')]
            .filter(e => e.scrollHeight > e.clientHeight + 10 &&
                         /auto|scroll/.test(getComputedStyle(e).overflowY))
            .map(e => e.scrollHeight + e.getBoundingClientRect().top))""")
    original = page.viewport_size
    await page.set_viewport_size({"width": original["width"], "height": min(int(height) + 40, 12000)})
    await asyncio.sleep(2)  # let the newly visible badge cards fade in
    await page.screenshot(path=path, full_page=True)
    await page.set_viewport_size(original)


async def worker(context, tracker, shot_path, watch):
    page = await context.new_page()
    await page.goto(URL, wait_until="domcontentloaded")
    while tracker.claim():
        try:
            roll = await roll_once(page)
        except Exception as e:
            print(f"  roll failed ({type(e).__name__}), retrying")
            tracker.count -= 1
            continue
        new_best = tracker.record(roll)
        if tracker.target and roll["totalScore"] > tracker.target and not tracker.hit:
            tracker.hit = (roll, context)
            print(f"\n*** TARGET HIT: {roll['number']}  {roll['totalScore']:,} XP. Stopping. ***")
            path = f"target_{roll['number']}.png"
            await capture_full(page, roll["totalScore"], path)
            print(f"*** Full-page screenshot saved: {path}  (window left open; Ctrl+C to quit) ***")
            return
        if tracker.hit:
            return
        shoot = new_best and shot_path
        if watch or shoot:
            await wait_for_reveal(page, roll["totalScore"])
        if shoot:
            await page.screenshot(path=shot_path)
        if watch:
            await asyncio.sleep(watch)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--rolls", type=int, default=0, help="total rolls (0 = until Ctrl+C)")
    ap.add_argument("-w", "--workers", type=int, default=2, help="parallel tabs")
    ap.add_argument("--headed", action="store_true", help="show the browser")
    ap.add_argument("--shot", default="best.png", help="screenshot of best roll ('' to skip)")
    ap.add_argument("--watch", type=float, nargs="?", const=3, default=0,
                    help="after each roll finishes revealing, hold it N seconds (default 3)")
    ap.add_argument("--light", action="store_true", help="use the site's light theme")
    ap.add_argument("--target", type=int, default=0,
                    help="stop at the first roll above this XP, full-page screenshot it, keep it open")
    ap.add_argument("--log", default="", help="append every roll to this CSV (roll,number,xp)")
    args = ap.parse_args()

    tracker = Tracker(args.rolls, args.target)
    if args.log:
        tracker.log = open(args.log, "a")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not args.headed)
        # Separate incognito-style context per worker so their storage never collides.
        scheme = "light" if args.light else "dark"
        contexts = [await browser.new_context(color_scheme=scheme) for _ in range(args.workers)]
        try:
            await asyncio.gather(*(worker(c, tracker, args.shot, args.watch) for c in contexts))
            if tracker.hit:
                # Close the other windows and leave the winning page exactly as it is.
                for c in contexts:
                    if c is not tracker.hit[1]:
                        await c.close()
                await asyncio.Event().wait()
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            b = tracker.best
            if b:
                badges = ", ".join(x["label"] for x in b["badges"] if x.get("isScoring"))
                print(f"\nBEST of {tracker.done}: {b['number']}  {b['totalScore']:,} XP\n  {badges}")
            await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
