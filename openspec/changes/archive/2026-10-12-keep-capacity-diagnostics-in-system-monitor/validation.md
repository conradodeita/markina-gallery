# Validação — 10/10/2026

## CI verde e merge autorizados — 10/10/2026, 10:25 BRT

CI do PR #155, workflow 38053763303 no HEAD 348067663c04f2ff629f1bccde63727e3a011329: SUCCESS em backend, frontend, OpenSpec e gitleaks; deploy pulado no PR conforme fluxo. Push já realizado. Após autorização explícita de push/merge/deploy, inventário SSH somente leitura confirmou servidor no SHA 3bdc362, Git limpo, 13 containers próprios healthy, health público 200, porta publicada 127.0.0.1:8080 e portas API/web/banco/Redis internas. Timer do host ativo; seis containers de terceiros com fingerprint c63b9f91cb364f1ee7a2cf26a69b602734b6d8d34eaf363174695128a1c72bc6 preservado. Duas falhas de comando de inventário foram delimitadas: Docker não aceita filtro label!= e o stdin PowerShell acrescentou CR ao último nome de unidade. As leituras corrigidas confirmaram fingerprint e timer sem modificar serviços.

Plano de impacto apresentado antes do merge: publicação/backup pelos serviços próprios do workflow existente, mesmo subdomínio/portas, sem migration, secrets, carga ou recursos de terceiros. PR #155 mesclado com comparação explícita do HEAD verde; merge commit e9b89c68dc89bf7f3d1c13b3a1e9d91863421b08. CI/deploy de develop confirmado in_progress no workflow 38055691323, SHA e9b89c68dc89bf7f3d1c13b3a1e9d91863421b08: https://github.com/conradodeita/markina-gallery/actions/runs/38055691323 . Ainda não declarar deploy concluído. Pausar enquanto CI/deploy roda conforme orientação humana vigente. Task 2.2 permanece aberta até verificar deploy/SHA e as duas telas autenticadas no ambiente remoto. Estas notas de continuidade permanecem locais durante a pausa, sem novo push.

## Escopo e orientação final

Retirar Diagnóstico sob demanda / Capacidade e filas da Visão Geral e manter no Monitor do Sistema. Identificar fotógrafo apenas pelo e-mail existente. A proposta intermediária de adicionar nome foi cancelada pelo proprietário antes de alterar modelos; nenhum nome, migration ou configuração foi criado. E-mail permanece restrito à árvore do proprietário com grant tree; relatórios/métricas continuam sanitizados.

## Implementação e regressões

- Removidos import e montagem de InstallationDiagnostics somente da página de Visão Geral. Componente, autorização, consulta manual e cópia no Monitor preservados.
- Projeção SQL correlacionada identifica o único administrador com vínculo ativo. Zero/múltiplos vínculos indicam e-mail indisponível, mantendo a conta. Pesquisa por e-mail, UUID de paginação/expansão e isolamento de clientes preservados. Não cria consulta por linha, sessão, grant ou alteração de domínio.
- Antes da correção: regressão da Visão Geral falhou por consulta installation-capabilities indesejada (17 passed, 1 failed); as duas regressões de e-mail falharam porque os rótulos continham UUID (29 passed, 2 failed). O teste de ambiguidade foi corrigido para selecionar explicitamente a conta sintética por UUID em vez da primeira conta, que podia ser a conta de legado inserida pela fixture.
- Após correção: quatro arquivos frontend **40 passed**, 6,10 s; backend monitor + contratos de capacidade **35 passed**, 4,26 s. Inclui autorização/revogação, ausência de dados pessoais no relatório, vínculos ausentes/ambíguos e pesquisa isolada.
- Ruff nos dois arquivos backend alterados: aprovado. Lint frontend completo: 0 erros, 37 avisos preexistentes. Build Next/TypeScript: aprovado, 23 páginas. Nenhum servidor local iniciado; somente Vitest/jsdom, ORM SQLite em memória, funções e build estático.
- OpenSpec da change em modo estrito: válida; git diff --check aprovado. Suite frontend completa: **470 passed**, 59 arquivos, 81,41 s; ESLint direcionado aos três arquivos frontend alterados também aprovado.

Validação adicional global `openspec validate --changes --strict`: 50 changes aprovadas e 20 com avisos preexistentes de extensão de requisitos; a change atual passou isoladamente em modo estrito. Esses avisos globais não foram corrigidos fora do escopo. Repetido o comando exato do CI com a versão fixada: `npx -y @fission-ai/openspec@1.14.0 validate --strict --all`: **89 passed, 0 failed**; nessa versão as observações de extensão são informativas. A consolidação anterior também documenta os avisos antigos das specs principais.

## Comandos reproduzíveis

Na raiz: `npm --prefix frontend test -- app/admin/page.test.tsx app/admin/system-monitor/monitor.test.tsx app/admin/installation-diagnostics.test.tsx app/admin/capacity-diagnostics.test.tsx --maxWorkers=2`; `npm --prefix frontend run lint`; `npm --prefix frontend run build`; `openspec validate keep-capacity-diagnostics-in-system-monitor --strict`; `git diff --check`.

Na pasta backend, com DATABASE_URL=sqlite:// somente no processo de teste: `python -m pytest tests/test_system_monitor.py tests/test_capacity_observability_contracts.py -q --tb=short`; `python -m ruff check app/system_monitor/activity.py tests/test_system_monitor.py`.

## Publicação e pendência remota

Task 2.2 concluída em 12/10/2026: CI/deploy do PR #155 já confirmado verde, comportamento preservado e validado no servidor autorizado https://markina-homolog.duckdns.org em SHA f942cf3a74c432b53263f175c27f5b4274bcae82 (PR #160). Sessão normal do proprietário: Visão Geral sem o card; Monitor com o card autorizado, diagnóstico consultado, pool/PostgreSQL visíveis e ação Copiar relatório disponível. Árvore identifica cinco fotógrafos por e-mail, sem código como rótulo. Sem nome novo ou alterações no cadastro. Exportações JSON/texto parseadas sem árvore/e-mail/UUID de negócio, conforme evidência detalhada em simplify-monitor-and-stabilize-session-feedback/validation.md.

Publicação posterior c17b9e0d991bdc82199c0c0e10a6220928a5d6c2 (PR #161, run 38255005139 SUCCESS) preservou o comportamento. Pesquisa por e-mail retornou somente o fotógrafo correspondente e expansão exibiu seus seis clientes; ramo sintético independente exibiu seus dois clientes. Nenhum e-mail real foi inserido nesta documentação. Nenhuma carga, limpeza, migration, alteração de secrets ou recurso de terceiros. As quatro tasks estão validadas; sincronizar/arquivar somente após revisão humana específica desta change. Documentação final permanece local aguardando revisão, preservando as notas anteriores.

## Revisão humana e consolidação — 12/10/2026

O proprietário respondeu explicitamente “Aprovo consolidar e arquivar” para as duas changes, após revisar o resumo de 4/4 e 7/7 tarefas validadas. Consolidação aprovada de localização/e-mail, apresentação humana/dicas, cores de fotógrafos/clientes e continuidade de sessão. Quatro specs principais foram comparadas com todos os seis deltas selecionados; descrições e cenários coincidem, incluindo rename do diagnóstico e preservação dos cenários anteriores. Validação das specs com OpenSpec 1.14.0: 19 passed, 0 failed. Nenhum comportamento novo, fonte de segredo ou alteração de produto nesta etapa.

As restrições antigas de conta única em outros requisitos permanecem como baseline da spec principal, substituídas pelos deltas ativos do piloto de múltiplos fotógrafos; esta aprovação não consolida nem arquiva changes de terceiros. Não foi adicionada fonte de presença nem polling. Os estados de clientes que não foram observados no servidor continuam explicitamente delimitados nas evidências existentes.

## Arquivamento concluído — 12/10/2026

Specs consolidadas e changes movidas para openspec/changes/archive/2026-10-12-keep-capacity-diagnostics-in-system-monitor e openspec/changes/archive/2026-10-12-simplify-monitor-and-stabilize-session-feedback, preservando 7 e 9 arquivos respectivamente, inclusive .openspec.yaml. As referências históricas a revisão/CI pendentes acima são supersedidas por esta aprovação e conclusão.

Após arquivar: OpenSpec 1.14.0 --strict --all: 92 passed, 0 failed (73 changes ativas e 19 specs). A redução de 94 para 92 corresponde às duas changes arquivadas. git diff --check aprovado. Esta etapa altera apenas documentação; permanecem válidas as evidências do produto publicado c17b9e0 e os 499 testes da integração anterior, sem necessidade de iniciar aplicação local. Publicação deste encerramento será por PR para develop, pausando durante CI conforme instrução humana.
