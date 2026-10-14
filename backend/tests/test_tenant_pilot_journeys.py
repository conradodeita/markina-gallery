"""Ensaio opt-in, navegador/API/worker reais, somente corpus e PostgreSQL próprios."""

import asyncio
import base64
import json
import os
import re
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path
from uuid import UUID

import pyotp
import pytest
import uvicorn
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app import auth, main, media, notification_delivery, worker
from app.capacity_observability import collector
from app.global_pix import normalize_configuration
from tests.pilot_fixture import (
    SYNTHETIC_PASSWORD,
    SYNTHETIC_TOTP,
    RecordingWhatsApp,
    prepare_pilot,
    verify_preparation,
)
from tests.test_tenant_photographer_migration import baseline_template as _baseline_template
from tests.test_tenant_photographer_migration import migrate
from tests.test_tenant_photographer_migration import migration_db as _migration_db

baseline_template, migration_db = _baseline_template, _migration_db
BACKEND = Path(__file__).resolve().parents[1]
FRONTEND = BACKEND.parent / "frontend"
ORIGIN = "http://127.0.0.1:3038"


def expected_report(snapshot):
    """Formatter do produto, sem reimplementar ou normalizar o texto copiado."""
    script = """
const fs = require('fs'); const Module = require('module');
const ts = require('./node_modules/typescript');
const code = ts.transpileModule(fs.readFileSync('app/admin/capacity-report.ts','utf8'),
 {compilerOptions:{module:ts.ModuleKind.CommonJS}}).outputText;
const mod = new Module('pilot-capacity-report'); mod._compile(code,'pilot-capacity-report.js');
process.stdout.write(mod.exports.formatCapacityReport(JSON.parse(fs.readFileSync(0,'utf8'))));
"""
    return subprocess.check_output([shutil.which("node"), "-e", script], cwd=FRONTEND,
        input=json.dumps(snapshot), text=True, encoding="utf-8")


def wait_ready(predicate, *, timeout=45):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            raise AssertionError("Servidor próprio não iniciou dentro do prazo.")
        time.sleep(0.1)


@pytest.mark.skipif(os.getenv("PYP_RUN_LOCAL_PILOT") != "1",
                    reason="Ensaio opt-in exige PostgreSQL próprio, build Next e Edge/Playwright.")
def test_piloto_local_2_por_3_com_monitor_real(migration_db, monkeypatch, tmp_path):
    pytest.importorskip("playwright.async_api")
    url, _migration_engine = migration_db
    migrate(url, "20261001_0071")
    engine = create_engine(url, pool_size=5, max_overflow=10)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    output = Path(os.environ["PILOT_EVIDENCE_DIR"]).resolve()
    assert output.is_relative_to(Path("C:/codex-data/test-runs").resolve())
    assert not output.exists(), "Evidência anterior deve ser preservada. Use outro diretório."
    output.mkdir()
    for name, value in {
        "APP_ENV": "development", "PUBLIC_APP_ORIGIN": ORIGIN,
        "WHATSAPP_PROVIDER": "sandbox", "TRANSACTIONAL_WHATSAPP_ENABLED": "true",
        "AUTH_PII_FINGERPRINT_SALT": "synthetic-local-pilot-only",
        "WHATSAPP_OTP_ENCRYPTION_KEY": base64.urlsafe_b64encode(os.urandom(32)).decode(),
        "MEDIA_SOURCE_ROOT": str(tmp_path / "source"),
        "MEDIA_DERIVATIVES_ROOT": str(tmp_path / "derivatives"),
    }.items():
        monkeypatch.setenv(name, value)
    for module in (auth, main, worker, notification_delivery, collector):
        monkeypatch.setattr(module, "SessionLocal", factory)
    monkeypatch.setattr(collector, "engine", engine)
    # Uma instância nova tem cache vazio. Nenhum reset será feito durante o ensaio.
    monkeypatch.setattr(collector, "_cached", None)
    monkeypatch.setattr(collector, "_collecting", False)
    with Session(engine) as db:
        initial = db.scalar(select(auth.Tenant.id))
        assert db.scalar(select(func.count()).select_from(auth.Tenant)) == 1
        assert db.scalar(select(func.count()).select_from(auth.AdminUser)) == 0
        accounts = prepare_pilot(db, tmp_path, initial_tenant_id=initial)
        assert prepare_pilot(db, tmp_path, initial_tenant_id=initial) == accounts
        verify_preparation(db, tmp_path, accounts)
        for label, account in zip(("A", "B"), accounts, strict=True):
            pix = db.scalar(select(auth.GlobalPixSettings).where(
                auth.GlobalPixSettings.tenant_id == account.tenant_id))
            for key, value in normalize_configuration({"copy_paste": f"synthetic-{label}@example.test",
                    "receiver_name": f"SINTETICO {label}", "receiver_city": "SAO PAULO"}).items():
                setattr(pix, key, value)
        db.commit()
        clients = [[(db.get(auth.Client, client_id).full_name, db.get(auth.Client, client_id).phone_e164)
                    for client_id in account.client_ids] for account in accounts]
    monkeypatch.setenv("WHATSAPP_TENANT_BINDINGS", json.dumps({str(a.tenant_id): label
                        for a, label in zip(accounts, ("A", "B"), strict=True)}))
    for label in ("A", "B"):
        monkeypatch.setenv(f"WHATSAPP_BINDING_{label}_PROVIDER", "sandbox")
        monkeypatch.setenv(f"WHATSAPP_BINDING_{label}_CREDENTIAL_ENV", "development")
    adapter = RecordingWhatsApp()
    # Não toma porta ocupada; socket pertence exclusivamente a esta invocação.
    api_socket = socket.socket()
    api_socket.bind(("127.0.0.1", 8000))
    api_socket.listen(128)
    with socket.socket() as check:
        check.bind(("127.0.0.1", 3038))
    manifest = json.loads((FRONTEND / ".next/routes-manifest.json").read_text())
    assert manifest["rewrites"]["afterFiles"][0]["destination"] == "http://127.0.0.1:8000/:path*"
    server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=8000, log_level="error"))
    api_thread = threading.Thread(target=server.run, kwargs={"sockets": [api_socket]}, daemon=True)
    frontend_process = None
    media_thread = None
    media_errors = []
    started = auth.now().isoformat()
    try:
        api_thread.start()
        wait_ready(lambda: server.started)
        with (output / "frontend.log").open("w", encoding="utf-8") as log:
            frontend_process = subprocess.Popen([shutil.which("node"),
                str(FRONTEND / "node_modules/next/dist/bin/next"), "start", "--hostname", "127.0.0.1",
                "--port", "3038"], cwd=FRONTEND, stdout=log, stderr=subprocess.STDOUT)
            import httpx

            def frontend_ready():
                assert frontend_process.poll() is None, "Next próprio terminou; conferir log externo."
                try:
                    return httpx.get(ORIGIN, timeout=1).status_code == 200
                except httpx.RequestError:
                    return False

            wait_ready(frontend_ready)
            def process_media():
                try:
                    while worker.process_next_media_job():
                        pass
                except Exception as exc:  # noqa: BLE001 -- falha da thread reprova o ensaio abaixo.
                    media_errors.append(type(exc).__name__)

            async def exercise():
                from playwright.async_api import async_playwright

                external_requests = []
                results = []
                snapshots = []
                async with async_playwright() as playwright:
                    browser = await playwright.chromium.launch(headless=True, channel="msedge")
                    async def profile():
                        context = await browser.new_context(viewport={"width": 390, "height": 844},
                            permissions=["clipboard-read", "clipboard-write"], service_workers="block")
                        async def confined(route):
                            from urllib.parse import urlparse
                            if urlparse(route.request.url).hostname not in ("127.0.0.1", None):
                                external_requests.append(urlparse(route.request.url).hostname)
                                await route.abort()
                            else:
                                await route.continue_()
                        await context.route("**/*", confined)
                        return context, await context.new_page()

                    async def api(context, method, path, data=None, *, status=200):
                        response = await context.request.fetch(ORIGIN + "/api" + path, method=method,
                            data=data, headers={"Origin": ORIGIN} if method != "GET" else {})
                        assert response.status == status, (method, path, response.status, await response.text())
                        return await response.json() if "json" in response.headers.get("content-type", "") else response

                    admins = []
                    try:
                        for index, account in enumerate(accounts):
                            context, page = await profile()
                            await page.goto(ORIGIN)
                            await page.get_by_role("tab", name="Fotógrafo", exact=True).click()
                            await page.get_by_label("E-mail", exact=True).fill(f"synthetic-pilot-{'ab'[index]}@example.test")
                            await page.get_by_label("Senha", exact=True).fill(SYNTHETIC_PASSWORD)
                            await page.get_by_role("button", name="Continuar", exact=True).click()
                            await page.get_by_label("Código do autenticador", exact=True).fill(pyotp.TOTP(SYNTHETIC_TOTP).now())
                            await page.get_by_role("button", name="Entrar", exact=True).click()
                            await page.wait_for_url(ORIGIN + "/admin")
                            capability = await api(context, "GET", "/admin/installation-capabilities")
                            assert capability["capacity_diagnostics"] is (index == 0)
                            await api(context, "PUT", f"/admin/parent-galleries/{account.parent_id}/pricing",
                                {"pricing_mode": "fixed", "fixed_unit_price_cents": 700 + index * 100})
                            other = accounts[1-index]
                            await api(context, "PATCH", f"/admin/clients/{other.client_ids[0]}",
                                {"full_name": "Tentativa sintética cruzada"}, status=404)
                            await api(context, "PUT", f"/admin/parent-galleries/{other.parent_id}/pricing",
                                {"pricing_mode": "fixed", "fixed_unit_price_cents": 1}, status=404)
                            catalog = await api(context, "GET", "/admin/parent-galleries")
                            assert [g["id"] for g in catalog["parent_galleries"]] == [str(account.parent_id)]
                            admins.append((context, page))
                        await api(admins[1][0], "GET", "/admin/capacity-observability", status=403)
                        assert await admins[1][1].get_by_role("button", name="Consultar diagnóstico", exact=True).count() == 0

                        async def snapshot(label, first=False):
                            page = admins[0][1]
                            async with page.expect_response(lambda r: r.url.endswith("/api/admin/capacity-observability")) as pending:
                                await page.get_by_role("button", name="Consultar diagnóstico" if first else "Atualizar agora", exact=True).click()
                            response = await pending.value
                            assert response.status == 200
                            value = await response.json()
                            await page.get_by_role("button", name="Copiar relatório", exact=True).click()
                            await page.get_by_text("Relatório copiado para a área de transferência.", exact=True).wait_for()
                            copied = await page.evaluate("navigator.clipboard.readText()")
                            # Windows materializa LF do writeText como CRLF no clipboard.
                            # Conferir conteúdo integral, permitindo somente essa conversão do SO.
                            assert copied.replace("\r\n", "\n") == expected_report(value)
                            assert all(str(a.tenant_id) not in copied for a in accounts)
                            (output / f"capacity-{label}.txt").write_bytes(copied.encode("utf-8"))
                            (output / f"capacity-{label}.json").write_text(json.dumps(value, indent=2), encoding="utf-8")
                            snapshots.append({"label": label, "requested_at": auth.now().isoformat(), "snapshot": value})
                            return value

                        await snapshot("before", first=True)
                        # A mesma UI compilada deve manter rótulos legíveis nos
                        # cartões estreitos de tablet/desktop, além do mobile.
                        page = admins[0][1]
                        layout_results = []
                        for width in (390, 768, 1280):
                            await page.set_viewport_size({"width": width, "height": 900})
                            await page.locator(".capacity-diagnostics").wait_for()
                            layout = await page.evaluate("""() => ({
                                viewport: innerWidth,
                                documentWidth: document.documentElement.scrollWidth,
                                labels: Array.from(document.querySelectorAll('.capacity-diagnostics dt')).map(e => {
                                    const range = document.createRange();
                                    range.selectNodeContents(e);
                                    return {
                                        text: e.textContent, width: e.getBoundingClientRect().width,
                                        height: e.getBoundingClientRect().height,
                                        lines: new Set(Array.from(range.getClientRects(), r => r.top)).size
                                    };
                                })
                            })""")
                            assert layout["documentWidth"] <= width, layout
                            assert layout["labels"], "Monitor precisa exibir suas métricas"
                            for label in layout["labels"]:
                                assert label["width"] >= 80, label
                                assert 1 <= label["lines"] <= 5, label
                            layout_results.append(layout)
                            await page.get_by_role("heading", name="Filas cobertas", exact=True).scroll_into_view_if_needed()
                            await page.screenshot(path=str(output / f"monitor-layout-{width}.png"))
                        (output / "monitor-layout.json").write_text(
                            json.dumps(layout_results, indent=2), encoding="utf-8")
                        await page.set_viewport_size({"width": 390, "height": 844})
                        before_mono = time.monotonic()
                        with Session(engine) as db:
                            for account in accounts:
                                for photo_id in account.photo_ids:
                                    media.enqueue_derivatives(db, db.get(auth.PhotoAsset, photo_id))
                            db.commit()
                        nonlocal media_thread
                        media_thread = threading.Thread(target=process_media, daemon=True)
                        media_thread.start()
                        delivery_lock = asyncio.Lock()
                        contexts = []
                        async def journey(index, number):
                            account, other = accounts[index], accounts[1-index]
                            context, page = await profile()
                            contexts.append(context)
                            name, phone = clients[index][number]
                            await page.goto(ORIGIN + "/?access_token=" + account.access_token)
                            await page.get_by_label("Nome completo", exact=True).fill(name)
                            await page.get_by_label("WhatsApp", exact=True).fill(phone[3:])
                            async with page.expect_response(lambda r: r.url.endswith("/api/auth/client/challenge")) as pending:
                                await page.get_by_role("button", name="Receber código", exact=True).click()
                            challenge_response = await pending.value
                            assert challenge_response.status == 202
                            challenge_id = (await challenge_response.json())["challenge_id"]
                            async with delivery_lock:
                                while worker.process_next_whatsapp_delivery(kind="otp", adapter=adapter):
                                    pass
                                messages = [m for recipient, m, key in adapter.calls
                                    if key == f"tenant:{account.tenant_id}:otp:{challenge_id}:0" and recipient == phone]
                                assert len(messages) == 1
                                code = re.search(r"(?<!\d)\d{6}(?!\d)", messages[0]).group()
                            await api(context, "POST", "/auth/client/verify",
                                {"challenge_id": challenge_id, "code": code, "access_token": other.access_token}, status=401)
                            await page.get_by_label("Código enviado por WhatsApp", exact=True).fill(code)
                            await page.get_by_role("button", name="Entrar", exact=True).click()
                            await page.wait_for_url(ORIGIN + f"/public-galleries/{account.parent_id}")
                            library = await api(context, "GET", "/library")
                            assert str(other.parent_id) not in json.dumps(library)
                            photos = await api(context, "GET", f"/public-galleries/{account.parent_id}/photos")
                            expected_ids = account.photo_ids if number == 0 else account.photo_ids[:3]
                            assert {p["id"] for p in photos["photos"]} == {str(p) for p in expected_ids}
                            assert await page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                            await api(context, "GET", f"/public-galleries/{other.parent_id}/photos", status=403)
                            await api(context, "GET", f"/public-galleries/{account.parent_id}/photos/{other.photo_ids[0]}/preview", status=404)
                            if number:
                                await api(context, "GET", f"/public-galleries/{account.parent_id}/photos/{account.photo_ids[3]}/preview", status=404)
                            chosen = [account.photo_ids[number]] + ([account.photo_ids[3]] if number == 0 else [])
                            for photo_id in chosen:
                                await api(context, "GET", f"/public-galleries/{account.parent_id}/photos/{photo_id}/preview")
                                await api(context, "POST", f"/public-galleries/{account.parent_id}/photos/{photo_id}/selection", status=201)
                            await api(context, "POST", f"/public-galleries/{other.parent_id}/photos/{other.photo_ids[0]}/selection", status=409)
                            await api(context, "DELETE", f"/library/cart/{other.parent_id}", status=403)
                            prepared = await api(context, "POST", "/library/cart/prepare")
                            payment = prepared["payment"]
                            assert payment["total_cents"] == (700 + index*100) * len(chosen)
                            communication = await api(context, "POST", f"/library/payments/{payment['id']}/report",
                                {"revision": payment["revision"], "idempotency_key": f"synthetic-{index}-{number}"})
                            return {"account": index, "client": number, "context": context,
                                "payment": payment, "communication": communication, "chosen_count": len(chosen)}

                        concurrency = {"active": 0, "peak": 0}
                        intervals = []
                        async def timed_journey(index, number):
                            concurrency["active"] += 1
                            concurrency["peak"] = max(concurrency["peak"], concurrency["active"])
                            interval = {"account": "AB"[index], "client_index": number,
                                        "started_at": auth.now().isoformat()}
                            try:
                                return await journey(index, number)
                            finally:
                                interval["finished_at"] = auth.now().isoformat()
                                intervals.append(interval)
                                concurrency["active"] -= 1

                        tasks = [asyncio.create_task(timed_journey(i, n)) for i in range(2) for n in range(3)]
                        try:
                            await snapshot("during")
                            results = await asyncio.gather(*tasks)
                            media_thread.join(timeout=30)
                            assert not media_thread.is_alive() and not media_errors
                            for result in results:
                                index, payment, communication = result["account"], result["payment"], result["communication"]
                                admin, foreign_admin = admins[index][0], admins[1-index][0]
                                await api(foreign_admin, "POST", f"/admin/payment-communications/{communication['id']}/decision",
                                    {"decision": "confirmed", "payment_group_id": payment["id"]}, status=409)
                                await api(admin, "POST", f"/admin/payment-communications/{communication['id']}/decision",
                                    {"decision": "confirmed", "payment_group_id": payment["id"]})
                                with Session(engine) as db:
                                    order = db.scalar(select(auth.SaleOrder).where(auth.SaleOrder.payment_group_id == UUID(payment["id"])))
                                    order_id = order.id
                                    assert order.tenant_id == accounts[index].tenant_id
                                    assert order.client_id == accounts[index].client_ids[result["client"]]
                                    assert order.pix_configuration_snapshot["receiver_name"] == f"SINTETICO {'AB'[index]}"
                                await api(foreign_admin, "PUT", f"/admin/orders/{order_id}/delivery",
                                    {"album_url": "https://photos.app.goo.gl/synthetic-local", "version": 0}, status=404)
                                await api(admin, "PUT", f"/admin/orders/{order_id}/delivery",
                                    {"album_url": f"https://photos.app.goo.gl/synthetic-{index}-{result['client']}", "version": 0})
                                history = await api(result["context"], "GET", "/library/purchases")
                                own_orders = [o["id"] for group in history["payment_groups"] for o in group["orders"]]
                                assert own_orders == [str(order_id)]
                                own_history = history["payment_groups"][0]["orders"][0]
                                assert own_history["payment_status"] == "confirmed"
                                assert own_history["delivery_album_url"] == f"https://photos.app.goo.gl/synthetic-{index}-{result['client']}"
                            await asyncio.sleep(max(0, collector.CACHE_TTL_SECONDS + 0.5 - (time.monotonic()-before_mono)))
                            after = await snapshot("after")
                            assert after["cached"] is False
                            assert after["collection_started_at"] != snapshots[0]["snapshot"]["collection_started_at"]
                            assert after["queues"][0]["queued_total"]["value"] == 0
                            assert not external_requests
                            assert concurrency == {"active": 0, "peak": 6}
                            with Session(engine) as db:
                                assert db.scalar(select(func.count()).select_from(auth.MediaJob).where(auth.MediaJob.status == "completed")) == 12
                                assert db.scalar(select(func.count()).select_from(auth.MediaDerivative).where(auth.MediaDerivative.status == "ready")) == 36
                                assert db.scalar(select(func.count()).select_from(auth.SaleOrder)) == 6
                                assert db.scalar(select(func.count()).select_from(auth.SaleOrderItem)) == 8
                                assert db.scalar(select(text("version_num")).select_from(text("alembic_version"))) == "20261001_0071"
                            summary = {"started_at": started, "finished_at": auth.now().isoformat(),
                                "schema": "20261001_0071", "photographers": 2, "clients": 6,
                                "max_client_journeys": concurrency["peak"], "journey_intervals": intervals,
                                "orders": 6, "order_items": 8,
                                "media_jobs_completed": 12, "derivatives_ready": 36,
                                "otp_delivered_to_memory": len(adapter.calls), "external_requests": len(external_requests),
                                "clipboard_exact": True, "snapshots": snapshots}
                            (output / "pilot-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
                            await admins[0][1].screenshot(path=str(output / "operator-after.png"), full_page=True)
                        finally:
                            for task in tasks:
                                if not task.done():
                                    task.cancel()
                            await asyncio.gather(*tasks, return_exceptions=True)
                            for context in contexts:
                                await context.close()
                    finally:
                        await browser.close()

            asyncio.run(exercise())
    finally:
        if media_thread:
            media_thread.join(timeout=30)
        if frontend_process is not None:
            frontend_process.terminate()
            frontend_process.wait(timeout=20)
        server.should_exit = True
        api_thread.join(timeout=20)
        api_socket.close()
        engine.dispose()
