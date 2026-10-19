#!/usr/bin/env python3
"""Summarize Dependabot candidates and specialized upstream drift (read only)."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = "https://api.github.com"
USER_AGENT = "pick-your-pic-third-party-monitor"
WATCHLIST = (
    {
        "name": "LightCraft",
        "source": "github-release",
        "url": "https://api.github.com/repos/storytold/lightcraft/releases/latest",
        "source_url": "https://github.com/storytold/lightcraft/releases",
        "risk": "Pode alterar decodificação, cor, formatos e suporte por câmera; exige corpus autorizado e comparação visual.",
    },
    {
        "name": "RawTherapee",
        "source": "github-release",
        "url": "https://api.github.com/repos/RawTherapee/RawTherapee/releases/latest",
        "source_url": "https://github.com/RawTherapee/RawTherapee/releases",
        "risk": "Pode alterar renderização RAW, codecs e comportamento do perfil; validar imagem e formatos/câmeras.",
    },
    {
        "name": "EmbeddingGemma 2",
        "source": "huggingface-model",
        "url": "https://huggingface.co/api/models/google/embeddinggemma-2",
        "source_url": "https://huggingface.co/google/embeddinggemma-2",
        "risk": "Mudança de pesos exige benchmark facial autorizado, avaliação de licença, qualidade, recursos e reindexação; nunca propor automaticamente.",
    },
)


class SourceError(RuntimeError):
    """Uma fonte não pôde ser consultada ou validada."""

    def __init__(self, message: str, *, state: str = "failed") -> None:
        super().__init__(message)
        self.state = state


def read_text(path: str) -> str:
    try:
        return (ROOT / path).read_text(encoding="utf-8")
    except OSError as exc:
        raise SourceError(f"declaração local indisponível: {path}") from exc


def pinned_versions() -> dict[str, str]:
    raw = read_text("backend/Dockerfile.raw-development")
    raw_match = re.search(r"^ARG LIGHTCRAFT_VERSION=([^\s]+)", raw, re.MULTILINE)
    rt_match = re.search(r"rawtherapee=([0-9][^\s\\]+)", raw)
    gemma = read_text("backend/app/facial/gemma_provider.py")
    gemma_match = re.search(r'^GEMMA_MODEL_REVISION\s*=\s*["\']([^"\']+)', gemma, re.MULTILINE)
    if not (raw_match and rt_match and gemma_match):
        raise SourceError("pin especializado ausente ou ilegível")
    return {
        "LightCraft": raw_match.group(1),
        "RawTherapee": rt_match.group(1).split("-")[0],
        "EmbeddingGemma 2": gemma_match.group(1),
    }


def inventory_count() -> int:
    document = read_text("docs/THIRD-PARTY-INVENTORY.md")
    records = re.findall(r"^\|\s*(\d{2})\s*\|", document, re.MULTILINE)
    expected = [f"{index:02d}" for index in range(1, 69)]
    if records != expected:
        raise SourceError("contagem/ordem do inventário local divergente")
    return len(records)


def fetch_json(url: str, token: str, opener: Callable = urlopen) -> object:
    headers = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if "huggingface.co" in url:
        headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    request = Request(url, headers=headers)
    try:
        with opener(request, timeout=30) as response:
            body = response.read()
    except HTTPError as exc:
        # Never include request headers, environment variables, or response body in diagnostics.
        code = exc.code
        state = "forbidden" if code == 403 else "failed"
        try:
            error_body = json.loads(exc.read(2048))
            message = error_body.get("message", "") if isinstance(error_body, dict) else ""
            if message == "Dependabot alerts are disabled for this repository.":
                state = "disabled"
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            pass
        raise SourceError(f"consulta falhou (HTTP {code})", state=state) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise SourceError(f"consulta falhou ({type(exc).__name__})") from exc
    try:
        return json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SourceError("resposta JSON inválida") from exc


def paginate_github(url: str, token: str, fetch: Callable = fetch_json) -> list[dict]:
    items: list[dict] = []
    for page in range(1, 21):
        separator = "&" if "?" in url else "?"
        result = fetch(f"{url}{separator}per_page=100&page={page}", token)
        if not isinstance(result, list) or any(not isinstance(item, dict) for item in result):
            raise SourceError("formato inesperado na paginação GitHub")
        items.extend(result)
        if len(result) < 100:
            return items
    raise SourceError("limite de páginas excedido; resultado incompleto")


def parse_release(value: object) -> str:
    if not isinstance(value, dict) or not isinstance(value.get("tag_name"), str):
        raise SourceError("release upstream não contém tag_name")
    return value["tag_name"].removeprefix("v")


def parse_image_reference(reference: str) -> tuple[str, str, str | None]:
    """Return image, declared tag (or latest), and an optional sha256 digest."""
    if not reference or any(char.isspace() for char in reference):
        raise SourceError("referência de imagem Docker inválida")
    image_and_tag, separator, digest_value = reference.partition("@")
    digest = digest_value if separator else None
    if digest is not None and not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise SourceError("digest Docker inválido")
    last_component = image_and_tag.rsplit("/", 1)[-1]
    if ":" in last_component:
        image, tag = image_and_tag.rsplit(":", 1)
    else:
        image, tag = image_and_tag, "latest"
    if not image or not tag:
        raise SourceError("referência de imagem Docker incompleta")
    return image, tag, digest


def parse_specialized_candidate(item: dict, current: str, remote: object) -> dict:
    if item["source"] == "huggingface-model":
        if not isinstance(remote, dict) or not isinstance(remote.get("sha"), str):
            raise SourceError("revisão Hugging Face ausente")
        candidate = remote["sha"]
        newer = candidate != current
        return {"candidate": candidate, "newer": newer, "kind": "revisão upstream"}
    candidate = parse_release(remote)
    old_numbers = tuple(int(part) for part in re.findall(r"\d+", current))
    new_numbers = tuple(int(part) for part in re.findall(r"\d+", candidate))
    if not old_numbers or not new_numbers:
        raise SourceError("versão de release não pôde ser comparada com segurança")
    return {"candidate": candidate, "newer": new_numbers > old_numbers, "kind": "release"}


def _version_transition(title: str) -> tuple[str, str] | None:
    match = re.search(r"\bfrom\s+([^\s]+)\s+to\s+([^\s]+)", title, re.IGNORECASE)
    return (match.group(1), match.group(2)) if match else None


def _priority(package: str, transition: tuple[str, str] | None, security: str | None) -> tuple[str, str, str]:
    name = package.lower()
    if security:
        level = security.lower()
        priority = {"critical": "P0", "high": "P1", "moderate": "P2", "low": "P3"}.get(level, "P2")
        return priority, "Corrigir vulnerabilidade indicada pela fonte", "Validar patch e regressões antes do merge"
    specialized = any(token in name for token in (
        "torch", "transformers", "gemma", "opencv", "numpy", "rawtherapee", "lightcraft", "onnx"
    ))
    if specialized:
        return "P1", "Correções upstream podem melhorar manutenção e compatibilidade", "Avaliação especializada; não atualizar automaticamente"
    if transition:
        old, new = transition
        old_major = re.match(r"\D*(\d+)", old)
        new_major = re.match(r"\D*(\d+)", new)
        if old_major and new_major and old_major.group(1) != new_major.group(1):
            return "P2", "Acesso a correções e melhorias upstream", "Testar API, build e migração compatível antes do merge"
    return "P3", "Correções e manutenção upstream", "Revisar changelog e executar testes do ecossistema"


def _package_from_title(title: str) -> str:
    match = re.search(r"\b(?:Bump|Update)\s+(.+?)\s+from\s+", title, re.IGNORECASE)
    return match.group(1) if match else "Dependência (ver título do PR)"


def _safe_url(value: object) -> str:
    if not isinstance(value, str) or not value.startswith("https://github.com/"):
        return "fonte GitHub"
    return value


def _md(value: object) -> str:
    """Escape untrusted upstream text before including it in a job summary."""
    text = " ".join(str(value).split())
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace("|", "&#124;").replace("`", "&#96;").replace("[", "&#91;").replace("]", "&#93;"))


def build_report(repo: str, token: str, fetch: Callable = fetch_json, now: datetime | None = None) -> tuple[str, bool]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise SourceError("identificador do repositório ausente ou inválido")
    if not token:
        raise SourceError("GITHUB_TOKEN ausente; fontes de PR/alertas não foram consultadas")
    generated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(timespec="seconds")
    sections: list[str] = [
        "# Revisão semanal de dependências externas",
        "",
        f"Verificação: `{generated_at}` (UTC). Repositório: `{repo}`.",
        f"Inventário no checkout: {inventory_count()} itens rastreáveis (`docs/THIRD-PARTY-INVENTORY.md`).",
        "Fontes: GitHub REST API (PRs abertos do Dependabot e alertas Dependabot); GitHub Releases e Hugging Face para componentes especializados.",
        "Este relatório avalia candidatos; não aplica versões, não cria PRs/issues e não prova versões instaladas em produção.",
        "",
    ]
    errors: list[str] = []
    pending_configuration = False
    prs: list[dict] = []
    alerts: list[dict] = []
    for label, endpoint, destination in (
        ("PRs Dependabot", f"{API_ROOT}/repos/{repo}/pulls?state=open", "prs"),
        ("Alertas Dependabot", f"{API_ROOT}/repos/{repo}/dependabot/alerts?state=open", "alerts"),
    ):
        try:
            value = paginate_github(endpoint, token, fetch)
            if destination == "prs":
                prs = [item for item in value if (item.get("user") or {}).get("login", "").lower() == "dependabot[bot]"]
            else:
                alerts = value
            sections.append(f"- {label}: consulta concluída; {len(prs) if destination == 'prs' else len(alerts)} item(ns) aberto(s).")
        except SourceError as exc:
            if label == "Alertas Dependabot" and exc.state in {"disabled", "forbidden"}:
                pending_configuration = True
                state = "DESABILITADO" if exc.state == "disabled" else "SEM PERMISSÃO"
                sections.append(f"- {label}: **{state} / NÃO CONFIRMADO** ({exc}); requer habilitação/permissão do proprietário.")
            else:
                errors.append(f"{label}: {exc}")
                sections.append(f"- {label}: **NÃO CONFIRMADO** ({exc}).")

    sections.extend(["", "## Alertas críticos e de segurança", ""])
    if alerts:
        alert_rows: dict[str, list[str]] = {"P0": [], "P1": [], "P2": [], "P3": []}
        for alert in alerts:
            dependency = alert.get("dependency") or {}
            package = dependency.get("package") or {}
            vulnerability = alert.get("security_vulnerability") or {}
            advisory = alert.get("security_advisory") or {}
            name = package.get("name", "pacote não identificado")
            ecosystem = package.get("ecosystem", "ecossistema não informado")
            severity = advisory.get("severity", "não informada")
            affected = vulnerability.get("vulnerable_version_range", "intervalo não informado")
            patched = vulnerability.get("first_patched_version") or {}
            candidate = patched.get("identifier", "não informada")
            priority, benefit, recommendation = _priority(name, None, severity)
            url = _safe_url(alert.get("html_url"))
            alert_rows[priority].append(
                f"- **{priority} · {_md(severity).upper()} · {_md(name)} ({_md(ecosystem)})** — afetadas `{_md(affected)}`; correção `{_md(candidate)}`. "
                f"Benefício: {benefit}. Risco: validar compatibilidade e regressões. Recomendação: {recommendation}. Origem: {url}."
            )
        for priority, heading in (("P0", "Críticos"), ("P1", "Altos"), ("P2", "Moderados"), ("P3", "Baixos")):
            if alert_rows[priority]:
                sections.extend([f"### {heading}", "", *alert_rows[priority], ""])
    elif pending_configuration:
        sections.append("A lista de alertas não pôde ser consultada; estado e quantidade de vulnerabilidades são desconhecidos.")
    else:
        sections.append("Nenhum alerta aberto foi retornado pela API consultada; isso não afirma que alertas estejam habilitados se a fonte estiver não confirmada.")

    sections.extend(["", "## Candidatos de versão Dependabot", ""])
    if prs:
        pr_rows: dict[str, list[str]] = {"P0": [], "P1": [], "P2": [], "P3": []}
        for pr in prs:
            title = str(pr.get("title", "PR Dependabot"))
            package = _package_from_title(title)
            transition = _version_transition(title)
            priority, benefit, recommendation = _priority(package, transition, None)
            versions = f"`{_md(transition[0])}` → `{_md(transition[1])}`" if transition else "versões no título do PR"
            url = _safe_url(pr.get("html_url"))
            pr_rows[priority].append(
                f"- **{priority} · {_md(package)}** — {versions}. Benefício: {benefit}. "
                f"Risco: conferir changelog, lockfile e compatibilidade do fluxo dependente. "
                f"Recomendação: {recommendation}. Origem: {url}."
            )
        for priority, heading in (("P1", "Oportunidades relevantes"), ("P2", "Atualizações para avaliar"), ("P3", "Baixa prioridade / acompanhar"), ("P0", "Urgentes")):
            if pr_rows[priority]:
                sections.extend([f"### {heading}", "", *pr_rows[priority], ""])
    else:
        sections.append("Nenhum PR aberto do Dependabot foi retornado. Isso indica apenas o estado desta consulta; não comprova que todos os registries foram verificados com sucesso.")

    sections.extend(["", "## Motores especializados e modelos", ""])
    try:
        current_versions = pinned_versions()
    except SourceError as exc:
        current_versions = {}
        errors.append(f"Pins especializados: {exc}")
    for item in WATCHLIST:
        current = current_versions.get(item["name"])
        if not current:
            sections.append(f"- **{item['name']}** — pin atual não confirmado; fonte upstream: {item['source_url']}. Recomendação: investigar a declaração local.")
            continue
        try:
            remote = fetch(item["url"], token)
            candidate = parse_specialized_candidate(item, current, remote)
            if candidate["newer"]:
                status = f"candidato upstream `{candidate['candidate']}`"
                recommendation = "avaliar manualmente; nenhuma atualização/PR automática"
                priority = "P1"
            else:
                status = f"nenhuma versão/revisão diferente observada (`{current}`)"
                recommendation = "acompanhar"
                priority = "P3"
            sections.append(
                f"- **{priority} · {item['name']}** — declarado `{current}` em `{item['source_url']}`; {status}. "
                f"Benefício: acompanhar manutenção upstream. Risco: {item['risk']} Recomendação: {recommendation}."
            )
        except SourceError as exc:
            errors.append(f"{item['name']}: {exc}")
            sections.append(
                f"- **{item['name']}** — declarado `{current}`; versão disponível **NÃO CONFIRMADA**. "
                f"Falha da fonte `{item['source_url']}`: {exc}. Risco: {item['risk']} Recomendação: retentar a consulta."
            )

    sections.extend([
        "",
        "## Estado da verificação",
        "",
        "- Fontes sem erro significam somente que os endpoints consultados responderam; ausência de PR/alerta não substitui a execução interna do Dependabot.",
        "- Atualizações ficam sob revisão humana. Não existe automerge. Modelos e motores especializados não geram PR automático.",
        "- Runtime Oracle e versões instaladas: não consultados por este workflow e não confirmados por tags ou candidatos.",
    ])
    if pending_configuration:
        sections.append("- Ação pendente: habilitar Dependabot alerts/security updates nas configurações de Security do repositório. Este relatório não interpreta API 403 como zero vulnerabilidades.")
    return "\n".join(sections) + "\n", bool(errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="escreve o relatório neste arquivo local")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""))
    args = parser.parse_args(argv)
    try:
        report, failed = build_report(args.repo, os.getenv("GITHUB_TOKEN", ""))
    except SourceError as exc:
        report, failed = f"# Revisão semanal de dependências externas\n\nConsulta **NÃO CONFIRMADA**: {exc}\n", True
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write(report)
    if not args.output and not summary_path:
        sys.stdout.write(report)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
