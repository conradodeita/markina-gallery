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

## Validação posterior em homologação — 30/09/2026

Esta seção complementa o escopo local acima com a validação remota concluída depois da implementação e do arquivo.

- PR de implementação #127 integrado em `95db26d7ef725582914e28b8f53201311548f8d1`; PR de sincronização/arquivo #128 integrado em `32fc8f5ad07184bbe6e2ea61fc504e29ab70cfd5`.
- GitHub Actions [36745688654](https://github.com/conradodeita/markina-gallery/actions/runs/36745688654): OpenSpec, backend, frontend, gitleaks e `deploy-homolog` concluídos com `success`, SHA `32fc8f5ad07184bbe6e2ea61fc504e29ab70cfd5`. Deploy concluído às 16:54:43 UTC.
- Destino: projeto `markina-gallery`, subdomínio `markina-homolog.duckdns.org`, entrada `127.0.0.1:8080`; `/healthz` e `/api/health` retornaram HTTP 200 após a publicação. Nenhuma segunda conta ou dado de negócio foi criado para este teste.
- Validação autenticada pela interface: **Consultar diagnóstico**, **Copiar relatório**, **Atualizar agora** e nova cópia apresentaram resultado e feedback acessível de sucesso.
- Primeiro snapshot: `collection_started_at=2026-09-30T16:50:11.732555Z`, `cached=false`, pool `checked_in=4`, `checked_out=0`, estimativa aberta 4; PostgreSQL 1 ativa e 8 ociosas; cinco filas com contagens observadas zeradas. Texto copiado continha formato/versão, 5 seções de fila e 21 campos nulos com motivo; busca por marcadores sensíveis no relatório não encontrou segredo, token, sessão ou contato pessoal.
- Segundo snapshot: `collection_started_at=2026-09-30T16:54:12.914458Z`, `cached=false`, pool `checked_in=1`, `checked_out=0`, estimativa aberta 1; PostgreSQL 1 ativa e 5 ociosas; cinco filas com contagens observadas zeradas. Leitura do clipboard da aba confirmou relatório atualizado de 13.155 caracteres, versão `capacity-report/v1` e horário correspondente à tela.
- A leitura inicial do clipboard do Windows após a segunda cópia mostrou a amostra anterior; o clipboard da aba confirmou a nova. A divergência entre superfícies foi esclarecida sem alteração de código e não constitui evidência de snapshot retido pelo componente.
- Orçamento global continua indisponível; espera medida/timeouts do pool e campos sem fonte permanecem nulos com motivos. Filas vazias não comprovam saúde de workers nem capacidade sob carga. Este teste foi funcional em instalação vazia, não o piloto com vários fotógrafos/clientes.

## Continuidade

O proprietário solicitou ensaio posterior pequeno com vários fotógrafos e clientes, aproveitando o monitor. Em 30/09/2026 confirmou cadastros independentes por fotógrafo, inclusive para o mesmo telefone. Planejamento separado em `openspec/changes/add-small-multi-photographer-pilot/`; não habilitar segunda conta pela simples remoção do gate de instalação única. Essa etapa ainda não foi implementada ou testada.
