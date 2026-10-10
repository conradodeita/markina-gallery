# Validação — 10/10/2026

## Escopo e orientação final

Retirar Diagnóstico sob demanda / Capacidade e filas da Visão Geral e manter no Monitor do Sistema. Identificar fotógrafo apenas pelo e-mail existente. A proposta intermediária de adicionar nome foi cancelada pelo proprietário antes de alterar modelos; nenhum nome, migration ou configuração foi criado. E-mail permanece restrito à árvore do proprietário com grant tree; relatórios/métricas continuam sanitizados.

## Implementação e regressões

- Removidos import e montagem de InstallationDiagnostics somente da página de Visão Geral. Componente, autorização, consulta manual e cópia no Monitor preservados.
- Projeção SQL correlacionada identifica o único administrador com vínculo ativo. Zero/múltiplos vínculos indicam e-mail indisponível, mantendo a conta. Pesquisa por e-mail, UUID de paginação/expansão e isolamento de clientes preservados. Não cria consulta por linha, sessão, grant ou alteração de domínio.
- Antes da correção: regressão da Visão Geral falhou por consulta installation-capabilities indesejada (17 passed, 1 failed); as duas regressões de e-mail falharam porque os rótulos continham UUID (29 passed, 2 failed). O teste de ambiguidade foi corrigido para selecionar explicitamente a conta sintética por UUID em vez da primeira conta, que podia ser a conta de legado inserida pela fixture.
- Após correção: quatro arquivos frontend **40 passed**, 6,10 s; backend monitor + contratos de capacidade **35 passed**, 4,26 s. Inclui autorização/revogação, ausência de dados pessoais no relatório, vínculos ausentes/ambíguos e pesquisa isolada.
- Ruff nos dois arquivos backend alterados: aprovado. Lint frontend completo: 0 erros, 37 avisos preexistentes. Build Next/TypeScript: aprovado, 23 páginas. Nenhum servidor local iniciado; somente Vitest/jsdom, ORM SQLite em memória, funções e build estático.
- OpenSpec da change em modo estrito: válida; git diff --check aprovado. Suite frontend completa: **470 passed**, 59 arquivos, 81,41 s; ESLint direcionado aos três arquivos frontend alterados também aprovado.

Validação adicional global `openspec validate --changes --strict`: 50 changes aprovadas e 20 com avisos preexistentes de extensão de requisitos; a change atual passou isoladamente em modo estrito. Esses avisos globais não foram corrigidos fora do escopo. A consolidação anterior também documenta os avisos antigos das specs principais.

## Comandos reproduzíveis

Na raiz: `npm --prefix frontend test -- app/admin/page.test.tsx app/admin/system-monitor/monitor.test.tsx app/admin/installation-diagnostics.test.tsx app/admin/capacity-diagnostics.test.tsx --maxWorkers=2`; `npm --prefix frontend run lint`; `npm --prefix frontend run build`; `openspec validate keep-capacity-diagnostics-in-system-monitor --strict`; `git diff --check`.

Na pasta backend, com DATABASE_URL=sqlite:// somente no processo de teste: `python -m pytest tests/test_system_monitor.py tests/test_capacity_observability_contracts.py -q --tb=short`; `python -m ruff check app/system_monitor/activity.py tests/test_system_monitor.py`.

## Publicação e pendência remota

Task 2.2 permanece aberta. Publicação será pelo PR para develop, CI e deploy existentes. Pausar depois do push enquanto o CI executa, conforme orientação humana; não mesclar sem resultado verde confirmado. Validar depois no servidor autorizado https://markina-homolog.duckdns.org, sessão normal do proprietário, a ausência do card em /admin, presença em /admin/system-monitor e rótulos por e-mail. Registrar SHA e resultado sanitizado, sem guardar e-mails reais nas evidências. Nenhuma carga, limpeza, migration, alteração de secrets ou recurso de terceiros nesta change.
