"""Prova opt-in com Next/FastAPI/PostgreSQL/Edge reais e e-mail sintético."""

import json
import os
import shutil
import socket
import subprocess
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app import auth, main, photographer_onboarding, photographer_signup, platform_console
from app.auth import AdminUser, Tenant, TenantAdmin, TenantCreditWallet, password_hasher
from app.system_monitor.models import PlatformOwner
from tests.test_tenant_client_isolation import client_db as _client_db

client_db = _client_db
ORIGIN = "http://127.0.0.1:3039"
PASSWORD = "IsolatedFlow!47Alpha"
OWNER_TOTP = "JBSWY3DPEHPK3PXP"


def wait_ready(predicate):
    deadline = time.monotonic() + 45
    while not predicate():
        assert time.monotonic() < deadline, "Serviço próprio não iniciou."
        time.sleep(0.1)


@pytest.mark.skipif(os.getenv("PYP_RUN_SIGNUP_JOURNEY") != "1", reason="Prova opt-in exige PostgreSQL próprio, build Next e driver Edge/Playwright.")
def test_real_website_signup_two_tenants_and_owner_suspension(client_db, monkeypatch, tmp_path):
    assert client_db.bind.dialect.name == "postgresql"
    output = Path(os.environ["SIGNUP_EVIDENCE_DIR"]).resolve()
    assert output.is_relative_to(Path("C:/codex-data/test-runs").resolve()) and not output.exists()
    output.mkdir()
    frontend = Path(__file__).parents[2] / "frontend"
    manifest = json.loads((frontend / ".next/routes-manifest.json").read_text())
    assert manifest["rewrites"]["afterFiles"][0]["destination"] == "http://127.0.0.1:8000/:path*"
    for key, value in {"APP_ENV": "development", "PUBLIC_APP_ORIGIN": ORIGIN,
                       "PHOTOGRAPHER_SIGNUP_LOCAL_PROOF_ENABLED": "true",
                       "SYSTEM_MONITOR_ENABLED": "false",
                       "MEDIA_SOURCE_ROOT": str(tmp_path / "source"),
                       "MEDIA_DERIVATIVES_ROOT": str(tmp_path / "derivatives"),
                       "MEDIA_HISTORY_ROOT": str(tmp_path / "history")}.items():
        monkeypatch.setenv(key, value)
    factory = sessionmaker(bind=client_db.get_bind(), expire_on_commit=False)
    for module in (auth, main, photographer_onboarding, photographer_signup, platform_console):
        monkeypatch.setattr(module, "SessionLocal", factory)
    owner_tenant = client_db.scalar(select(Tenant))
    owner = AdminUser(email="journey-owner@example.test", email_verified=True,
                      password_hash=password_hasher.hash(PASSWORD), totp_secret=OWNER_TOTP)
    owner.tenant_memberships.append(TenantAdmin(tenant_id=owner_tenant.id))
    client_db.add(owner)
    client_db.flush()
    client_db.add_all([PlatformOwner(singleton=1, admin_user_id=owner.id, authorization_reference="synthetic-journey"),
                       TenantCreditWallet(tenant_id=owner_tenant.id, mode="unmetered")])
    client_db.commit()
    mailbox = tmp_path / "synthetic-mail.json"
    messages = {}

    class Services:
        def verify_bot(self, proof, _address): return proof == ""
        def send_code(self, _db, signup_row, code):
            email = signup_row.email
            assert email in {"web-a@example.test", "web-b@example.test"}
            messages[email] = code
            mailbox.write_text(json.dumps(messages), encoding="utf-8")

    previous_override = main.app.dependency_overrides.get(photographer_signup.signup_services)
    main.app.dependency_overrides[photographer_signup.signup_services] = Services
    api_socket = socket.socket()
    api_socket.bind(("127.0.0.1", 8000))
    api_socket.listen(128)
    with socket.socket() as check:
        check.bind(("127.0.0.1", 3039))
    server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=8000, log_level="error"))
    api_thread = threading.Thread(target=server.run, kwargs={"sockets": [api_socket]}, daemon=True)
    driver = tmp_path / "browser.py"
    driver.write_text(BROWSER_DRIVER, encoding="utf-8")
    frontend_process = None
    try:
        api_thread.start()
        wait_ready(lambda: server.started)
        with (output / "frontend.log").open("w", encoding="utf-8") as log:
            frontend_process = subprocess.Popen([shutil.which("node"), str(frontend / "node_modules/next/dist/bin/next"),
                "start", "--hostname", "127.0.0.1", "--port", "3039"], cwd=frontend, stdout=log,
                stderr=subprocess.STDOUT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            import httpx

            def ready():
                assert frontend_process.poll() is None
                try: return httpx.get(ORIGIN + "/photographer-signup", timeout=1).status_code == 200
                except httpx.RequestError: return False

            wait_ready(ready)
            browser_python = os.environ["SIGNUP_BROWSER_PYTHON"]
            completed = subprocess.run([browser_python, str(driver), str(mailbox), str(output)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=150, check=False,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            assert completed.returncode == 0, (completed.stderr or "Driver sem diagnóstico")[-4000:]
            browser_evidence = json.loads(completed.stdout)
        client_db.expire_all()
        assert client_db.scalar(select(func.count()).select_from(AdminUser)) == 3
        assert client_db.scalar(select(func.count()).select_from(Tenant)) == 3
        assert list(client_db.scalars(select(TenantCreditWallet.mode).where(TenantCreditWallet.tenant_id != owner_tenant.id))) == ["finite", "finite"]
        (output / "result.json").write_text(json.dumps({"signup": "2 real browser contexts", "owner_console": "read/suspend/reactivate",
            "database": "isolated PostgreSQL", "external_email": "simulated", "external_requests": 0,
            "http_denials": browser_evidence["http_denials"],
            "production": "unchanged"}, indent=2), encoding="utf-8")
    finally:
        server.should_exit = True
        api_thread.join(timeout=10)
        if frontend_process:
            frontend_process.terminate()
            try: frontend_process.wait(timeout=10)
            except subprocess.TimeoutExpired: frontend_process.kill()
        api_socket.close()
        mailbox.unlink(missing_ok=True)
        if previous_override is None: main.app.dependency_overrides.pop(photographer_signup.signup_services, None)
        else: main.app.dependency_overrides[photographer_signup.signup_services] = previous_override


BROWSER_DRIVER = r'''
import json, sys, time
from pathlib import Path
from urllib.parse import urlparse
import pyotp
from playwright.sync_api import sync_playwright
origin = "http://127.0.0.1:3039"
mailbox, output = Path(sys.argv[1]), Path(sys.argv[2])
password = "IsolatedFlow!47Alpha"
external = []
denied = []
profile_names = iter(("photographer-a", "photographer-b", "platform-owner"))
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    def profile():
        profile_name = next(profile_names)
        c = browser.new_context(viewport={"width":390,"height":844}, service_workers="block")
        def confined(route):
            from urllib.parse import urlparse
            host = urlparse(route.request.url).hostname
            if host not in ("127.0.0.1", None):
                external.append(host); route.abort()
            else: route.continue_()
        c.route("**/*", confined)
        page = c.new_page()
        page.on("response", lambda response: denied.append({"profile": profile_name,
            "status": response.status, "path": urlparse(response.url).path}) if response.status in (401, 403)
            and urlparse(response.url).hostname == "127.0.0.1" else None)
        return c, page
    accounts = []
    expected_hosts = []
    for suffix in ("a", "b"):
        c, page = profile()
        page.goto(origin + "/photographer-signup")
        page.get_by_label("Nome do fotógrafo", exact=True).fill("Web " + suffix.upper())
        page.get_by_label("E-mail", exact=True).fill("web-" + suffix + "@example.test")
        page.get_by_role("button", name="Receber código", exact=True).click()
        page.get_by_label("Código recebido por e-mail", exact=True).wait_for()
        code = json.loads(mailbox.read_text())["web-" + suffix + "@example.test"]
        page.get_by_label("Código recebido por e-mail", exact=True).fill(code)
        page.get_by_role("button", name="Verificar e-mail", exact=True).click()
        page.get_by_role("heading", name="Crie sua senha", exact=True).wait_for()
        page.get_by_label("Senha", exact=True).fill(password)
        page.get_by_role("button", name="Criar minha conta", exact=True).click()
        page.get_by_role("heading", name="Conta criada", exact=True).wait_for()
        assert not page.locator("code").count()
        page.screenshot(path=str(output / ("signup-" + suffix + ".png")), full_page=True)
        page.get_by_role("link", name="Entrar no painel", exact=True).click()
        page.get_by_role("heading", name="Seu próximo passo está à vista.", exact=True).wait_for()
        assert c.request.get(origin + "/api/admin/credits/wallet").status == 200
        assert c.request.get(origin + "/api/admin/platform/console/tenants?mode=all").status == 403
        assert not page.get_by_role("link", name="Plataforma", exact=True).count()
        page.get_by_role("link", name="Escolher link da minha marca", exact=True).wait_for()
        assert not page.get_by_text(
            "Acesso negado para esta operação ou área. Confira suas permissões ou os dados informados.", exact=True
        ).count()
        page.screenshot(path=str(output / ("dashboard-" + suffix + ".png")), full_page=True)
        page.get_by_role("link", name="Escolher link da minha marca", exact=True).click()
        page.wait_for_url(origin + "/admin/settings#tenant-address")
        page.get_by_role("heading", name="Link da sua marca no Pick-your-Pic", exact=True).wait_for()
        page.get_by_label("Nome para o link da marca", exact=True).fill("marca-compartilhada")
        page.get_by_role("button", name="Reservar meu link", exact=True).click()
        if suffix == "b":
            page.get_by_text("Este nome de link não está disponível. Escolha outro nome.", exact=True).wait_for()
            page.screenshot(path=str(output / "address-b-conflict.png"), full_page=True)
            page.get_by_label("Nome para o link da marca", exact=True).fill("marca-teste-b")
            page.get_by_role("button", name="Reservar meu link", exact=True).click()
            expected_host = "marca-teste-b.pickyourpic.com.br"
        else:
            expected_host = "marca-compartilhada.pickyourpic.com.br"
        page.get_by_text("Link da marca reservado para sua conta.", exact=True).wait_for()
        page.locator("#tenant-address details summary").click()
        page.get_by_text(expected_host, exact=True).wait_for()
        assert not page.get_by_role("link", name="Acessar meu espaço", exact=True).count()
        page.screenshot(path=str(output / ("address-" + suffix + ".png")), full_page=True)
        address = c.request.get(origin + "/api/admin/onboarding/address")
        assert address.status == 200 and address.json()["hostname"] == expected_host
        assert address.json()["state"] == "reserved" and address.json()["public_url"] is None
        expected_hosts.append(expected_host)
        accounts.append(c)
    assert len(expected_hosts) == 2 and len(set(expected_hosts)) == 2
    owner, page = profile()
    page.goto(origin)
    page.get_by_role("tab", name="Fotógrafo", exact=True).click()
    page.get_by_label("E-mail", exact=True).fill("journey-owner@example.test")
    page.get_by_label("Senha", exact=True).fill(password)
    page.get_by_role("button", name="Continuar", exact=True).click()
    page.get_by_label("Código do autenticador ou de recuperação", exact=True).fill(pyotp.TOTP("JBSWY3DPEHPK3PXP").now())
    page.get_by_role("button", name="Entrar", exact=True).click()
    page.wait_for_url(origin + "/admin")
    page.get_by_role("link", name="Plataforma", exact=True).click()
    page.wait_for_url(origin + "/admin/platform")
    assert not page.get_by_text(
        "Acesso negado para esta operação ou área. Confira suas permissões ou os dados informados.", exact=True
    ).count()
    page.get_by_label("Nome ou e-mail do fotógrafo", exact=True).fill("Web")
    page.get_by_role("button", name="Pesquisar", exact=True).click()
    page.get_by_text("Web A", exact=True).wait_for()
    page.get_by_role("button", name="Consultar web-a@example.test", exact=True).click()
    page.get_by_role("heading", name="Suspender conta", exact=True).wait_for()
    page.get_by_label("Senha atual", exact=True).fill(password)
    used = int(time.time()) // 30 + 1
    page.get_by_label("Código do autenticador", exact=True).fill(pyotp.TOTP("JBSWY3DPEHPK3PXP").at(used*30))
    page.get_by_label("Confirmo a alteração do estado desta conta", exact=True).check()
    page.get_by_role("button", name="Confirmar suspensão", exact=True).click()
    page.get_by_role("heading", name="Reativar conta", exact=True).wait_for()
    assert accounts[0].request.get(origin + "/api/admin/credits/wallet").status == 403
    assert accounts[1].request.get(origin + "/api/admin/credits/wallet").status == 200
    while int(time.time())//30 < used: time.sleep(.2)
    page.get_by_label("Senha atual", exact=True).fill(password)
    page.get_by_label("Código do autenticador", exact=True).fill(pyotp.TOTP("JBSWY3DPEHPK3PXP").at((used+1)*30))
    page.get_by_label("Confirmo a alteração do estado desta conta", exact=True).check()
    page.get_by_role("button", name="Confirmar reativação", exact=True).click()
    page.get_by_role("heading", name="Suspender conta", exact=True).wait_for()
    assert accounts[0].request.get(origin + "/api/admin/credits/wallet").status == 200
    page.get_by_role("button", name="Consultar ações recentes", exact=True).click()
    page.get_by_text("Concluída", exact=False).first.wait_for()
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(150)
    page.screenshot(path=str(output / "owner-console.png"), full_page=True)
    assert not external
    print(json.dumps({"http_denials": denied}))
    browser.close()
'''
