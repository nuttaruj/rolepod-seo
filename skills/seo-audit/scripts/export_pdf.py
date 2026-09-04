#!/usr/bin/env python3
"""rolepod-seo — turn the HTML report into a real PDF with a browser already on the machine.

Usage:
  export_pdf.py <report.html> [--out report.pdf] [--find-only] [--timeout 90]

Uses the print engine of a Chromium-family browser that is already
installed — Google Chrome, Chromium, Microsoft Edge, Brave, Arc, or the
Chromium that rolepod-uiproof's Playwright keeps in its cache — via
`--headless=new --print-to-pdf`. The output is the same page the browser
would print: embedded fonts, colours, page breaks from the report's
@media print rules. No pip package, no Node, no LibreOffice.

Exit 0 and the PDF path on success; exit 2 with a one-line hint when no
browser is found (the report still opens in any browser: ⌘P / Ctrl+P →
Save as PDF). Set ROLEPOD_SEO_CHROME to a binary path to force one.
"""
from __future__ import annotations

import argparse
import glob
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MAC_APPS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Arc.app/Contents/MacOS/Arc",
    "~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]
PATH_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge", "microsoft-edge", "microsoft-edge-stable", "brave-browser", "brave"]
WIN_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]
PLAYWRIGHT_GLOBS = [
    "~/Library/Caches/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-mac-*/chrome-headless-shell",
    "~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium",
    "~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell",
    "~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome",
    os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright\chromium_headless_shell-*\chrome-headless-shell-win*\chrome-headless-shell.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\ms-playwright\chromium-*\chrome-win*\chrome.exe"),
]


def find_browser() -> str | None:
    forced = os.environ.get("ROLEPOD_SEO_CHROME")
    if forced and os.path.exists(forced):
        return forced
    system = platform.system()
    candidates: list[str] = []
    if system == "Darwin":
        candidates += [os.path.expanduser(p) for p in MAC_APPS]
    if system == "Windows":
        candidates += WIN_PATHS
    for name in PATH_NAMES:
        p = shutil.which(name)
        if p:
            candidates.append(p)
    for pattern in PLAYWRIGHT_GLOBS:
        candidates += sorted(glob.glob(os.path.expanduser(pattern)), reverse=True)
    for c in candidates:
        if c and os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return None


def export(html_path: str, out_path: str, timeout: float = 90.0, browser: str | None = None) -> str:
    browser = browser or find_browser()
    if not browser:
        raise FileNotFoundError("no Chromium-family browser found")
    html_abs = Path(html_path).resolve()
    out_abs = Path(out_path).resolve()
    out_abs.parent.mkdir(parents=True, exist_ok=True)
    if out_abs.exists():
        out_abs.unlink()
    with tempfile.TemporaryDirectory(prefix="rolepod-seo-pdf-") as profile:
        cmd = [
            browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--no-default-browser-check",
            "--disable-extensions", "--disable-background-networking", f"--user-data-dir={profile}",
            "--no-pdf-header-footer", f"--print-to-pdf={out_abs}", html_abs.as_uri(),
        ]
        if platform.system() == "Linux" and hasattr(os, "geteuid") and os.geteuid() == 0:
            cmd.insert(1, "--no-sandbox")
        # Chrome's new headless mode writes the PDF within seconds but does not always exit afterwards:
        # wait for the file to appear and stop growing, then end the process ourselves.
        t0 = time.time()
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        last, stable = -1, 0
        try:
            while time.time() - t0 < timeout:
                if proc.poll() is not None:
                    break
                if out_abs.exists():
                    size = out_abs.stat().st_size
                    stable = stable + 1 if (size > 500 and size == last) else 0
                    last = size
                    if stable >= 3:
                        break
                time.sleep(0.3)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        if not out_abs.exists() or out_abs.stat().st_size < 1000:
            err = ""
            try:
                err = (proc.stderr.read() if proc.stderr else "")[-400:]
            except Exception:
                pass
            raise RuntimeError(f"no PDF after {time.time() - t0:.1f}s (browser exit {proc.returncode}): {err}")
    with open(out_abs, "rb") as f:
        if f.read(5) != b"%PDF-":
            raise RuntimeError("output is not a PDF")
    return str(out_abs)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("html", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--find-only", action="store_true", help="print the browser that would be used and exit")
    ap.add_argument("--timeout", type=float, default=90.0)
    a = ap.parse_args(argv)
    browser = find_browser()
    if a.find_only:
        print(browser or "none")
        return 0 if browser else 2
    if not a.html:
        ap.error("html path required")
    if not browser:
        print("no Chromium-family browser found — open the HTML report in any browser and use ⌘P / Ctrl+P → Save as PDF, or set ROLEPOD_SEO_CHROME", file=sys.stderr)
        return 2
    out = a.out or (a.html[:-5] if a.html.endswith(".html") else a.html) + ".pdf"
    try:
        path = export(a.html, out, a.timeout, browser)
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        print(f"pdf export failed with {os.path.basename(browser)}: {e}", file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
