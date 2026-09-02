#!/usr/bin/env python3
"""
Executes the workflow from the n8n UI and captures the screenshots the No-Code
track submission needs: full canvas with green success ticks, key node configs,
and the output data table.

Every screenshot is viewport-sized (1600x900) - never full_page.
"""
import os
import time

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:15678"
WF = "23f5f402-f881-4ce8-8769-1c5e2bdea3a7"
OUT = "/mnt/freelancer-projects/40678618/build/screenshots"
os.makedirs(OUT, exist_ok=True)
VIEWPORT = {"width": 1600, "height": 900}


def shot(page, name, wait=1.5):
    time.sleep(wait)
    page.screenshot(path=os.path.join(OUT, name))
    print(f"  saved {name}")


def close_overlays(page):
    for sel in ["button:has-text('Got it')", "button:has-text('Close')",
                "[data-test-id='close-button']", "button[aria-label='Close']"]:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=800):
                loc.click()
                time.sleep(0.6)
        except Exception:
            pass


def open_node(page, title, filename, wait=2.5):
    """Double-click a node by its canvas label and screenshot its parameter panel."""
    try:
        node = page.locator(f"[data-test-id='canvas-node']:has-text('{title}')").first
        node.dblclick()
        time.sleep(wait)
        shot(page, filename, wait=1.0)
        page.keyboard.press("Escape")
        time.sleep(1.2)
        return True
    except Exception as e:
        print(f"  ! could not open '{title}': {type(e).__name__}")
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return False


def sign_in(page):
    """A fresh browser context has no session cookie, so n8n shows /signin."""
    page.goto(f"{BASE}/signin", wait_until="networkidle")
    time.sleep(2)
    if page.locator("button:has-text('Sign in')").count() == 0:
        print("  already signed in")
        return
    print("  signing in...")
    page.fill("input[type='email']", "owner@shopnest.local")
    page.fill("input[type='password']", "ShopnestDemo1")
    page.click("button:has-text('Sign in')")
    page.wait_for_url(lambda u: "/signin" not in u, timeout=30000)
    time.sleep(3)
    print("  signed in")


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport=VIEWPORT)
        page.set_default_timeout(30000)

        sign_in(page)

        print("opening canvas...")
        page.goto(f"{BASE}/workflow/{WF}", wait_until="networkidle")
        time.sleep(4)
        close_overlays(page)
        page.keyboard.press("1")   # zoom to fit
        time.sleep(2)
        shot(page, "01_full_workflow_canvas.png", wait=1.5)

        print("executing workflow from the UI...")
        # Two buttons match the text: the trigger node's inline one (which the
        # canvas pane intercepts) and the main toolbar one. Target the toolbar.
        page.locator("[data-test-id='execute-workflow-button']").click()

        # Wait for the run to finish: the button flips back out of its running
        # state. Poll rather than sleeping a fixed amount.
        finished = False
        for _ in range(120):
            time.sleep(3)
            try:
                btn = page.locator("[data-test-id='execute-workflow-button']")
                if btn.is_visible(timeout=1500) and "Execute workflow" in (btn.inner_text() or ""):
                    finished = True
                    break
            except Exception:
                pass
        print(f"  execution finished: {finished}")
        time.sleep(4)
        close_overlays(page)
        page.keyboard.press("1")
        time.sleep(2)
        shot(page, "02_canvas_after_successful_run.png", wait=2)

        print("capturing node configurations...")
        open_node(page, "Summarise Ticket", "03_node_summarise_ticket.png", wait=3)
        open_node(page, "Judge Summary", "04_node_judge_summary.png", wait=3)
        open_node(page, "Generate Response", "05_node_generate_response.png", wait=3)
        open_node(page, "Judge Response", "06_node_judge_response.png", wait=3)
        open_node(page, "Consolidate Ticket Record", "07_node_consolidate.png", wait=3)
        open_node(page, "Pipeline Quality Stats", "08_node_quality_stats.png", wait=3)
        open_node(page, "Pipeline Config", "09_node_pipeline_config.png", wait=3)

        print("capturing execution list...")
        page.goto(f"{BASE}/workflow/{WF}/executions", wait_until="networkidle")
        shot(page, "10_execution_list.png", wait=4)

        browser.close()
    print("done")


if __name__ == "__main__":
    main()
