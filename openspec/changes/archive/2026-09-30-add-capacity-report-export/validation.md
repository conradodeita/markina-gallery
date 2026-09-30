# Validation

## Contexto

- Data local: 2026-09-30.
- Branch: `feature/add-capacity-report-export`.
- Base da implementação: `5a9444d3d375c86b8532a4e61d3469fbc1d7369b` (`origin/develop` no início da change).
- Escopo: serialização e cópia local do snapshot administrativo existente; nenhuma validação remota, deploy, migration ou alteração de infraestrutura.

## Evidência direcionada

- `npm test -- capacity-report.test.ts`: 1 arquivo, 2 testes aprovados. Comprovou formato `capacity-report/v1`, ordem canônica, valores brutos, evidências, nulidade explícita, motivos e exclusão de campos extras com sentinelas.
- `npm test -- capacity-diagnostics.test.tsx capacity-report.test.ts`: 2 arquivos, 11 testes aprovados. Comprovou cópia exata sem novo `fetch`, bloqueio de cópias concorrentes, feedback acessível, falha do clipboard sem perda do snapshot ou fallback, e retirada da ação após perda de autorização.
- Revisão de `docs/admin-capacity-diagnostics.md` com busca pelos termos do contrato confirmou exemplo com UTC, cache, zero observado, estimativa e indisponibilidade, além dos limites de privacidade, histórico, fotógrafo e SLO.

## Integração do frontend

- `npm test`: 52 arquivos, 374 testes aprovados. O jsdom emitiu o aviso conhecido `Not implemented: navigation to another Document`, sem falha.
- `npm run lint`: concluído com 0 erros e 37 avisos em arquivos não alterados; nenhum aviso aponta para os arquivos desta change.
- `npx tsc --noEmit`: concluído sem diagnósticos.
- `npm run build`: build Next.js 16.3.2 concluído, TypeScript aprovado e 22 páginas estáticas geradas.

## Revisão final

- `git diff --name-status` apresentou somente 12 arquivos da change: componente/testes/estilo do diagnóstico, serializador/teste, documentação e artefatos OpenSpec. Não há endpoint, backend, migration, `.env`, segredo, telemetria, storage ou infraestrutura no diff.
- `git diff --check`: sem erro de whitespace; Git apenas informou a normalização LF/CRLF configurada para novos arquivos na cópia de trabalho Windows.
- Revisão do diff confirmou projeção por allowlist, ausência de serialização genérica, nova requisição, download ou persistência e preservação do tratamento de autorização existente.
- Após o ajuste defensivo para remontagem em React Strict Mode, `npm test -- capacity-report.test.ts capacity-diagnostics.test.tsx` aprovou novamente os 11 testes direcionados.
- `openspec validate add-capacity-report-export --strict`: change válida.
