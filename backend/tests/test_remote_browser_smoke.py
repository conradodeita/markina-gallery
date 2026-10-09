"""One-request, read-only browser smoke against homologation."""

import asyncio
import json
import os
from time import perf_counter

import pytest

from tests.test_remote_campaign_smoke import smoke_target
from tests.remote_campaign_policy import validate_smoke_url
from tests.remote_smoke_reporting import record_smoke_check


pytestmark = pytest.mark.skipif(
    os.getenv("PYP_REMOTE_CAMPAIGN") != "1",
    reason="Remote browser smoke runs only from the approved external runner.",
)


def test_remote_homolog_page_in_isolated_browser_context():
    from playwright.async_api import async_playwright

    async def exercise():
        started = perf_counter()
        outcome = "failed"
        request_count = 0
        status = None
        request_duration = None
        try:
            target = smoke_target()
            endpoint = f"{target}/api/health"
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch()
                try:
                    context = await browser.new_context(service_workers="block")
                    try:
                        page = await context.new_page()
                        request_started = None

                        def observe_response(response):
                            nonlocal request_duration
                            if response.url == endpoint and request_started is not None:
                                request_duration = (perf_counter() - request_started) * 1000

                        async def confine(route):
                            nonlocal request_count
                            nonlocal request_started
                            try:
                                validate_smoke_url(route.request.method, route.request.url)
                            except ValueError:
                                await route.abort()
                            else:
                                request_count += 1
                                request_started = perf_counter()
                                await route.continue_()

                        await page.route("**/*", confine)
                        page.on("response", observe_response)
                        response = await page.goto(endpoint, wait_until="domcontentloaded", timeout=10_000)
                        status = response.status if response is not None else None
                        assert response is not None and status == 200
                        assert page.url == endpoint
                        assert json.loads(await page.locator("body").inner_text()) == {
                            "status": "ok",
                            "service": "api",
                        }
                        assert request_count == 1
                        assert await context.cookies() == []
                        outcome = "passed"
                    finally:
                        await context.close()
                finally:
                    await browser.close()
        finally:
            record_smoke_check(
                check="playwright_api_health",
                outcome=outcome,
                duration_ms=(perf_counter() - started) * 1000,
                request_duration_ms=request_duration,
                request_count=request_count,
                http_status=status,
            )

    asyncio.run(exercise())
