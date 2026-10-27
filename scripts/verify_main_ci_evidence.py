"""Verify reusable CI evidence for an exact main SHA, without mutating GitHub."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

SHA = re.compile(r'^[0-9a-f]{40}$')
REQUIRED_JOBS = frozenset({
    'ci-scope', 'backend-quality', 'backend-tests (0)', 'backend-tests (1)',
    'backend-tests (2)', 'backend', 'frontend', 'runtime-images (ubuntu-latest, amd64)',
    'runtime-images (ubuntu-24.04-arm, arm64)', 'openspec', 'gitleaks',
    'homolog-inventory-policy', 'gemma-runtime',
})
API = 'https://api.github.com/repos/conradodeita/markina-gallery'


class EvidenceError(ValueError):
    """Fail-closed CI evidence error with no credentials or remote response body."""


class NoRedirect(HTTPRedirectHandler):
    """Never forward the GitHub token to a redirect destination."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def select_run(runs: list[dict], sha: str) -> dict:
    if not SHA.fullmatch(sha):
        raise EvidenceError('sha_invalido')
    candidates = [run for run in runs if run.get('path') == '.github/workflows/ci.yml'
                  and run.get('head_sha') == sha and run.get('event') == 'push'
                  and run.get('head_branch') == 'main']
    if not candidates:
        raise EvidenceError('ci_push_main_ausente')
    for item in candidates:
        if any(type(item.get(key)) is not int or item[key] < 1
               for key in ('id', 'run_number', 'run_attempt')):
            raise EvidenceError('ci_metadados_invalidos')
    latest = max(candidates, key=lambda item: (item['run_number'], item['run_attempt']))
    if latest.get('status') != 'completed' or latest.get('conclusion') != 'success':
        raise EvidenceError('ci_mais_recente_nao_verde')
    return latest


def verify_jobs(jobs: list[dict]) -> None:
    indexed: dict[str, list[dict]] = {}
    for job in jobs:
        if isinstance(job.get('name'), str):
            indexed.setdefault(job['name'], []).append(job)
    for name in REQUIRED_JOBS:
        matches = indexed.get(name, [])
        if len(matches) != 1 or matches[0].get('status') != 'completed' or matches[0].get('conclusion') != 'success':
            raise EvidenceError('job_obrigatorio_nao_verde:' + name)


def request_json(url: str, token: str) -> dict:
    if not url.startswith(API + '/'):
        raise EvidenceError('url_api_invalida')
    request = Request(url, headers={'Accept': 'application/vnd.github+json',
                                    'Authorization': 'Bearer ' + token,
                                    'X-GitHub-Api-Version': '2022-11-28'})
    try:
        with build_opener(NoRedirect()).open(request, timeout=20) as response:
            if not response.geturl().startswith(API + '/'):
                raise EvidenceError('redirecionamento_api_recusado')
            payload = response.read(4 * 1024 * 1024 + 1)
        if len(payload) > 4 * 1024 * 1024:
            raise EvidenceError('resposta_api_excessiva')
        result = json.loads(payload)
    except EvidenceError:
        raise
    except (HTTPError, URLError, OSError, ValueError, TimeoutError):
        raise EvidenceError('consulta_api_falhou') from None
    if not isinstance(result, dict):
        raise EvidenceError('resposta_api_invalida')
    return result


def paginate(path: str, key: str, token: str, params: dict[str, str] | None = None) -> list[dict]:
    items: list[dict] = []
    expected = None
    for page in range(1, 11):
        query = urlencode({**(params or {}), 'per_page': 100, 'page': page})
        result = request_json(f'{API}/{path}?{query}', token)
        total, batch = result.get('total_count'), result.get(key)
        if type(total) is not int or total < 0 or not isinstance(batch, list):
            raise EvidenceError('paginacao_invalida')
        if expected is None:
            expected = total
        elif total != expected:
            raise EvidenceError('paginacao_mudou')
        if any(not isinstance(item, dict) for item in batch):
            raise EvidenceError('paginacao_invalida')
        items.extend(batch)
        if len(items) == expected:
            return items
        if len(items) > expected or not batch:
            raise EvidenceError('paginacao_incompleta')
    raise EvidenceError('paginacao_excessiva')


def verify_remote(sha: str, token: str) -> dict:
    if not SHA.fullmatch(sha) or not token:
        raise EvidenceError('sha_ou_token_ausente')
    main = request_json(API + '/commits/main', token).get('sha')
    if main != sha:
        raise EvidenceError('sha_nao_e_main_atual')
    runs = paginate('actions/workflows/ci.yml/runs', 'workflow_runs', token,
                    {'event': 'push', 'branch': 'main', 'head_sha': sha})
    run = select_run(runs, sha)
    jobs = paginate(f"actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs", 'jobs', token)
    verify_jobs(jobs)
    if request_json(API + '/commits/main', token).get('sha') != sha:
        raise EvidenceError('main_mudou_durante_consulta')
    return {'sha': sha, 'run_id': run['id'], 'run_attempt': run['run_attempt'], 'conclusion': 'success'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sha', required=True)
    args = parser.parse_args()
    try:
        evidence = verify_remote(args.sha, os.environ.get('GITHUB_TOKEN', ''))
    except EvidenceError as error:
        print(f'ci_evidence_ready=false;criterio={error}', file=sys.stderr)
        return 1
    print(json.dumps(evidence, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
