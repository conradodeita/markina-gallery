"""Real browser journeys against the explicitly authorized homologation host."""

from __future__ import annotations

import asyncio
import json
import math
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from urllib.parse import quote, urlsplit
from uuid import NAMESPACE_URL, UUID, uuid5

import pytest

from tests.remote_campaign_policy import ALLOWED_BASE_URL, CampaignPolicyError, validate_target
from tests.remote_functional_policy import validate_functional_request

pytestmark = pytest.mark.skipif(
    os.getenv("PYP_REMOTE_CAMPAIGN") != "1" or os.getenv("PYP_REMOTE_FUNCTIONAL") != "1",
    reason="Authenticated browser journeys run only against the approved remote homologation target.",
)

TENANTS = (
    UUID("7f1f8b5a-905c-4c35-9cd8-87759af31c01"),
    UUID("b67d881d-d577-40d8-af5e-0a4368ea6002"),
)
MAX_FUNCTIONAL_API_REQUESTS = 80


class FunctionalJourneyError(AssertionError):
    """A sanitized functional expectation failed."""


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise FunctionalJourneyError("functional_credential_or_gate_missing")
    return value


def _fixture_ids(tenant_id: UUID) -> dict[str, UUID]:
    namespace = uuid5(NAMESPACE_URL, f"pyp-remote-campaign-v1:{tenant_id}")
    return {
        "gallery": uuid5(namespace, "gallery"),
        "client_1": uuid5(namespace, "client:1"),
        "client_2": uuid5(namespace, "client:2"),
    }


def _percentile(samples: list[float], percentile: int) -> float | None:
    if not samples:
        return None
    ordered = sorted(samples)
    return round(ordered[max(0, math.ceil(len(ordered) * percentile / 100) - 1)], 3)


def _write_sanitized_report(report_path: str | None, report: dict) -> None:
    if not report_path:
        return
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, sort_keys=True, indent=2), encoding="utf-8")
    temporary.replace(path)


def test_remote_browser_authentication_and_tenant_isolation():
    origin = validate_target(_required("PYP_REMOTE_TARGET_URL"))
    if (
        os.getenv("PYP_REMOTE_ENVIRONMENT") != "homolog"
        or os.getenv("PYP_FUNCTIONAL_AUTHORIZED") != "1"
        or not _required("PYP_FUNCTIONAL_AUTHORIZATION_REFERENCE")
        or os.getenv("PYP_AB_TEST_CLOSED") != "1"
    ):
        raise FunctionalJourneyError("functional_preflight_failed")
    otp_secret = _required("PYP_REMOTE_TEST_OTP_SECRET")
    if len(otp_secret) < 32:
        raise FunctionalJourneyError("functional_otp_gate_invalid")

    started_at = datetime.now(UTC)
    started = perf_counter()
    api_requests = 0
    api_latencies: list[float] = []
    observed_api_paths: list[str] = []
    checks: list[str] = []
    screenshots: list[str] = []
    blocked_operations = 0
    revoked_sessions = 0
    revocation_failures = 0
    selection_cleanup_failures = 0
    outcome = "failed"
    failure_code = None
    last_stage = "preflight"
    contexts = []
    authenticated_contexts = []
    pending_selections = []

    async def exercise() -> None:
        nonlocal api_requests, blocked_operations, revoked_sessions, revocation_failures
        nonlocal selection_cleanup_failures
        nonlocal last_stage
        import pyotp
        from playwright.async_api import Error as PlaywrightError
        from playwright.async_api import async_playwright

        async def guard_route(route):
            nonlocal api_requests, blocked_operations
            request = route.request
            try:
                validate_functional_request(request.method, request.url)
                if "/api/" in request.url:
                    api_requests += 1
                    observed_api_paths.append(
                        f"{request.method.upper()} {urlsplit(request.url).path}"
                    )
                if api_requests > MAX_FUNCTIONAL_API_REQUESTS:
                    blocked_operations += 1
                    await route.abort()
                    return
                await route.continue_()
            except CampaignPolicyError:
                blocked_operations += 1
                await route.abort()

        async def api(context, method: str, path: str, *, data=None, headers=None):
            nonlocal api_requests
            url = origin + path
            validate_functional_request(method, url)
            api_requests += 1
            if api_requests > MAX_FUNCTIONAL_API_REQUESTS:
                raise FunctionalJourneyError("functional_api_request_cap_exceeded")
            before = perf_counter()
            response = await context.request.fetch(
                url,
                method=method,
                data=data,
                headers={"Content-Type": "application/json", **(headers or {})},
                timeout=20_000,
                max_redirects=0,
            )
            api_latencies.append((perf_counter() - before) * 1000)
            return response

        async def client_login(browser, tenant_index: int, client_number: int):
            nonlocal last_stage
            tenant_id = TENANTS[tenant_index]
            ids = _fixture_ids(tenant_id)
            phone = (
                ("(11) 99999-1001" if client_number == 1 else "(11) 99999-1002")
                if tenant_index == 0
                else ("(11) 99999-2001" if client_number == 1 else "(11) 99999-2002")
            )
            full_name = f"Cliente sintético {tenant_id.hex[:6]} {client_number}"
            return_to = f"/public-galleries/{ids['gallery']}"
            context = await browser.new_context()
            contexts.append(context)
            await context.route("**/*", guard_route)
            page = await context.new_page()
            last_stage = f"client_{client_number}_navigation"
            last_stage = f"client_{client_number}_branding_hydration"
            async with page.expect_response(
                lambda response: response.request.method == "GET"
                and urlsplit(response.url).path == "/api/branding",
                timeout=10_000,
            ) as branding_response:
                await page.goto(
                    f"{origin}/?reauth=client&return_to={quote(return_to, safe='/')}",
                    wait_until="domcontentloaded",
                    timeout=30_000,
                )
            if (await branding_response.value).status != 200:
                raise FunctionalJourneyError("client_branding_hydration_failed")
            checks.append("client_form_hydrated")
            last_stage = f"client_{client_number}_name_field"
            await page.get_by_label("Nome completo").fill(full_name)
            last_stage = f"client_{client_number}_phone_field"
            await page.get_by_label("WhatsApp").fill(phone)
            if not await page.locator("#client-phone").evaluate("input => input.checkValidity()"):
                raise FunctionalJourneyError("synthetic_client_phone_format_invalid")
            last_stage = f"client_{client_number}_challenge"
            challenge_button = page.get_by_role("button", name="Receber código", exact=True)
            if await challenge_button.count() != 1:
                raise FunctionalJourneyError("client_challenge_button_missing")
            if not await challenge_button.is_enabled():
                raise FunctionalJourneyError("client_challenge_button_disabled")
            async with page.expect_response(
                lambda response: response.url.endswith("/api/auth/client/challenge"),
                timeout=10_000,
            ) as challenge_response:
                await challenge_button.click(timeout=5_000)
            challenge_http = await challenge_response.value
            if challenge_http.status != 202:
                raise FunctionalJourneyError("client_challenge_failed")
            challenge_id = (await challenge_http.json()).get("challenge_id")
            if not isinstance(challenge_id, str) or not re.fullmatch(
                r"[0-9a-fA-F-]{36}", challenge_id
            ):
                raise FunctionalJourneyError("client_challenge_response_invalid")
            last_stage = f"client_{client_number}_otp_sink"
            otp_response = await api(
                context,
                "POST",
                "/api/auth/test/client-otp/consume",
                data={"challenge_id": challenge_id},
                headers={"x-pyp-test-otp-secret": otp_secret},
            )
            if otp_response.status != 200:
                raise FunctionalJourneyError("client_test_otp_unavailable")
            code = (await otp_response.json()).get("code")
            if not isinstance(code, str) or not re.fullmatch(r"\d{6}", code):
                raise FunctionalJourneyError("client_test_otp_invalid")
            last_stage = f"client_{client_number}_otp_verify"
            await page.get_by_label("Código de acesso").fill(code)
            async with page.expect_response(
                lambda response: response.url.endswith("/api/auth/client/verify")
            ) as verify_response:
                await page.get_by_role("button", name="Entrar", exact=True).click()
            verified = await verify_response.value
            if verified.status != 200:
                raise FunctionalJourneyError("client_otp_verification_failed")
            last_stage = f"client_{client_number}_gallery_navigation"
            await page.wait_for_url(f"{origin}{return_to}", timeout=20_000)
            authenticated_contexts.append(context)
            checks.append("client_otp_login")
            return context, page, ids

        async def photographer_login(browser, index: int):
            nonlocal last_stage
            suffix = "A" if index == 0 else "B"
            email = _required(f"PYP_PHOTOGRAPHER_{suffix}_EMAIL")
            password = _required(f"PYP_PHOTOGRAPHER_{suffix}_PASSWORD")
            totp_secret = _required(f"PYP_PHOTOGRAPHER_{suffix}_TOTP_SECRET")
            context = await browser.new_context()
            contexts.append(context)
            await context.route("**/*", guard_route)
            page = await context.new_page()
            last_stage = f"photographer_{suffix}_branding_hydration"
            async with page.expect_response(
                lambda response: response.request.method == "GET"
                and urlsplit(response.url).path == "/api/branding",
                timeout=10_000,
            ) as branding_response:
                await page.goto(f"{origin}/?reauth=admin", wait_until="domcontentloaded", timeout=30_000)
            if (await branding_response.value).status != 200:
                raise FunctionalJourneyError("photographer_branding_hydration_failed")
            last_stage = f"photographer_{suffix}_tab"
            await page.get_by_role("tab", name="Fotógrafo").click()
            last_stage = f"photographer_{suffix}_password_fields"
            await page.get_by_label("E-mail").fill(email)
            await page.get_by_label("Senha").fill(password)
            last_stage = f"photographer_{suffix}_password_challenge"
            async with page.expect_response(
                lambda response: response.url.endswith("/api/auth/admin/password")
            ) as password_response:
                await page.get_by_role("button", name="Continuar").click()
            challenge_http = await password_response.value
            if challenge_http.status != 202:
                raise FunctionalJourneyError("photographer_password_step_failed")
            challenge_id = (await challenge_http.json()).get("challenge_id")
            if not isinstance(challenge_id, str) or not re.fullmatch(
                r"[0-9a-fA-F-]{36}", challenge_id
            ):
                raise FunctionalJourneyError("photographer_challenge_response_invalid")
            last_stage = f"photographer_{suffix}_totp"
            code = pyotp.TOTP(totp_secret).now()
            await page.get_by_label("Código do autenticador").fill(code)
            async with page.expect_response(
                lambda response: response.url.endswith("/api/auth/admin/totp")
            ) as totp_response:
                await page.get_by_role("button", name="Entrar", exact=True).click()
            verified = await totp_response.value
            if verified.status != 200:
                raise FunctionalJourneyError("photographer_totp_verification_failed")
            last_stage = f"photographer_{suffix}_admin_navigation"
            await page.wait_for_url(f"{origin}/admin", timeout=20_000)
            authenticated_contexts.append(context)
            checks.append("photographer_totp_login")
            return context, page

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                client_a1, page_a1, gallery_a = await client_login(browser, 0, 1)
                client_a2, _page_a2, _gallery_a2 = await client_login(browser, 0, 2)
                client_b1, _page_b1, gallery_b = await client_login(browser, 1, 1)
                client_b2, _page_b2, _gallery_b2 = await client_login(browser, 1, 2)

                photos_a1_response = await api(client_a1, "GET", f"/api/public-galleries/{gallery_a['gallery']}/photos")
                photos_a2_response = await api(client_a2, "GET", f"/api/public-galleries/{gallery_a['gallery']}/photos")
                photos_b1_response = await api(client_b1, "GET", f"/api/public-galleries/{gallery_b['gallery']}/photos")
                photos_b2_response = await api(client_b2, "GET", f"/api/public-galleries/{gallery_b['gallery']}/photos")
                if any(response.status != 200 for response in (photos_a1_response, photos_a2_response, photos_b1_response, photos_b2_response)):
                    raise FunctionalJourneyError("authorized_gallery_read_failed")
                photos_a1 = (await photos_a1_response.json()).get("photos", [])
                photos_a2 = (await photos_a2_response.json()).get("photos", [])
                photos_b1 = (await photos_b1_response.json()).get("photos", [])
                photos_b2 = (await photos_b2_response.json()).get("photos", [])
                if not (len(photos_a1) == len(photos_a2) == len(photos_b1) == len(photos_b2) == 2):
                    raise FunctionalJourneyError("synthetic_gallery_inventory_mismatch")
                if any(
                    item.get("folder_name") != "Fotos sintéticas"
                    or not isinstance(item.get("preview_url"), str)
                    for item in (*photos_a1, *photos_a2, *photos_b1, *photos_b2)
                ):
                    raise FunctionalJourneyError("synthetic_folder_metadata_invalid")
                for context, gallery, photos in (
                    (client_a1, gallery_a, photos_a1),
                    (client_a2, gallery_a, photos_a2),
                    (client_b1, gallery_b, photos_b1),
                    (client_b2, gallery_b, photos_b2),
                ):
                    for photo in photos:
                        preview = await api(
                            context,
                            "GET",
                            f"/api/public-galleries/{gallery['gallery']}/photos/{photo['id']}/preview",
                        )
                        if preview.status != 200 or not preview.headers.get("content-type", "").startswith("image/jpeg"):
                            raise FunctionalJourneyError("synthetic_client_preview_unavailable")
                checks.extend(("client_gallery_read", "client_folder_metadata", "client_preview_read"))

                photo_a = photos_a1[0]["id"]
                selected_a1 = await api(
                    client_a1, "POST",
                    f"/api/public-galleries/{gallery_a['gallery']}/photos/{photo_a}/selection",
                    data={},
                )
                if selected_a1.status != 201:
                    raise FunctionalJourneyError("client_selection_create_failed")
                pending_selections.append((client_a1, gallery_a["gallery"], photo_a))
                client_a2_after = await api(client_a2, "GET", f"/api/public-galleries/{gallery_a['gallery']}/photos")
                a2_state = (await client_a2_after.json()).get("photos", [])
                if client_a2_after.status != 200 or next(item for item in a2_state if item["id"] == photo_a).get("selected"):
                    raise FunctionalJourneyError("client_selection_leaked_between_sessions")
                selected_a2 = await api(
                    client_a2, "POST",
                    f"/api/public-galleries/{gallery_a['gallery']}/photos/{photo_a}/selection",
                    data={},
                )
                if selected_a2.status != 201:
                    raise FunctionalJourneyError("second_client_selection_failed")
                pending_selections.append((client_a2, gallery_a["gallery"], photo_a))
                a1_state_response = await api(client_a1, "GET", f"/api/public-galleries/{gallery_a['gallery']}/photos")
                a1_state = (await a1_state_response.json()).get("photos", [])
                if a1_state_response.status != 200 or not next(item for item in a1_state if item["id"] == photo_a).get("selected"):
                    raise FunctionalJourneyError("client_selection_state_not_isolated")
                for context in (client_a1, client_a2):
                    removed = await api(
                        context, "DELETE",
                        f"/api/public-galleries/{gallery_a['gallery']}/photos/{photo_a}/selection",
                    )
                    if removed.status not in {200, 204}:
                        raise FunctionalJourneyError("synthetic_selection_cleanup_failed")
                    pending_selections[:] = [
                        entry for entry in pending_selections if entry[0] is not context
                    ]
                checks.append("client_selection_isolation")

                cross_tenant = await api(client_a1, "GET", f"/api/public-galleries/{gallery_b['gallery']}/photos")
                if cross_tenant.status not in {403, 404}:
                    raise FunctionalJourneyError("cross_tenant_client_access_not_denied")
                foreign_preview = await api(
                    client_a1,
                    "GET",
                    f"/api/public-galleries/{gallery_b['gallery']}/photos/{photos_b1[0]['id']}/preview",
                )
                if foreign_preview.status not in {403, 404}:
                    raise FunctionalJourneyError("cross_tenant_client_preview_not_denied")
                checks.append("client_cross_tenant_denial")

                admin_a, _page_admin_a = await photographer_login(browser, 0)
                admin_b, _page_admin_b = await photographer_login(browser, 1)
                galleries_a = await api(admin_a, "GET", "/api/admin/parent-galleries")
                galleries_b = await api(admin_b, "GET", "/api/admin/parent-galleries")
                if galleries_a.status != 200 or galleries_b.status != 200:
                    raise FunctionalJourneyError("photographer_gallery_read_failed")
                own_a = (await galleries_a.json()).get("parent_galleries", [])
                own_b = (await galleries_b.json()).get("parent_galleries", [])
                if not any(item.get("id") == str(gallery_a["gallery"]) for item in own_a):
                    raise FunctionalJourneyError("photographer_a_gallery_missing")
                if not any(item.get("id") == str(gallery_b["gallery"]) for item in own_b):
                    raise FunctionalJourneyError("photographer_b_gallery_missing")
                foreign_gallery = await api(
                    admin_a,
                    "GET",
                    f"/api/admin/parent-galleries/{gallery_b['gallery']}/details",
                )
                if foreign_gallery.status not in {403, 404}:
                    raise FunctionalJourneyError("cross_tenant_photographer_access_not_denied")
                checks.extend(("photographer_gallery_read", "photographer_cross_tenant_denial"))

                screenshot_path = os.getenv("PYP_FUNCTIONAL_SCREENSHOT_PATH", "").strip()
                if screenshot_path:
                    await page_a1.screenshot(path=screenshot_path, full_page=False)
                    screenshots.append(Path(screenshot_path).name)
            finally:
                for context, gallery_id, photo_id in pending_selections[:]:
                    try:
                        response = await api(
                            context,
                            "DELETE",
                            f"/api/public-galleries/{gallery_id}/photos/{photo_id}/selection",
                        )
                        if response.status in {200, 204}:
                            pending_selections.remove((context, gallery_id, photo_id))
                        else:
                            selection_cleanup_failures += 1
                    except PlaywrightError:
                        selection_cleanup_failures += 1
                for context in authenticated_contexts:
                    try:
                        response = await api(context, "POST", "/api/auth/logout")
                        if response.status == 204:
                            revoked_sessions += 1
                            checks.append("synthetic_session_revoked")
                    except PlaywrightError:
                        revocation_failures += 1
                for context in contexts:
                    await context.close()
                await browser.close()
        if revoked_sessions != len(authenticated_contexts) or revocation_failures:
            raise FunctionalJourneyError("synthetic_session_revocation_failed")
        if selection_cleanup_failures or pending_selections:
            raise FunctionalJourneyError("synthetic_selection_cleanup_failed")

    report_path = os.getenv("PYP_FUNCTIONAL_REPORT_PATH", "").strip() or None
    source_revision = os.getenv("PYP_SOURCE_REVISION", "unknown").strip()
    try:
        asyncio.run(exercise())
        if blocked_operations:
            raise FunctionalJourneyError("functional_request_policy_blocked_operation")
        outcome = "passed"
    except Exception as exc:  # noqa: BLE001 -- redact all browser, network, and auth details.
        if isinstance(exc, FunctionalJourneyError):
            failure_code = str(exc)
        else:
            failure_code = f"functional_browser_run_failed_at_{last_stage}"
        raise FunctionalJourneyError(failure_code) from None
    finally:
        duration = perf_counter() - started
        _write_sanitized_report(
            report_path,
            {
                "schema": "pyp-remote-functional-report/v1",
                "source_revision": source_revision,
                "environment": "homolog",
                "target": ALLOWED_BASE_URL,
                "profile": "authenticated_browser_journeys",
                "started_at": started_at.isoformat(),
                "duration_seconds": round(duration, 3),
                "virtual_users": 1,
                "photographers": 2,
                "clients": 4,
                "api_requests": api_requests,
                "observed_api_paths": observed_api_paths,
                "api_operations_per_second": round(api_requests / duration, 3) if duration else None,
                "api_latency_ms": {
                    "p50": _percentile(api_latencies, 50),
                    "p95": _percentile(api_latencies, 95),
                    "p99": _percentile(api_latencies, 99),
                    "sample_count": len(api_latencies),
                },
                "checks": sorted(set(checks)),
                "failure_code": failure_code,
                "last_stage": last_stage,
                "errors": 0 if outcome == "passed" else 1,
                "screenshots": screenshots,
                "traces": [],
                "server_metrics": "unavailable_not_collected",
                "load_capacity_claim": False,
            },
        )
