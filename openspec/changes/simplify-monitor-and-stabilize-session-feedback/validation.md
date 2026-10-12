# Validação — 11/10/2026

## Escopo e base

Branch feature/monitor-human-hints-and-session-feedback, base origin/develop 0292e2d. Preservadas as alterações recentes dos motores faciais e a recuperação automática d6df74f. O deploy do PR #155 (38055691323, SHA e9b89c6) foi confirmado SUCCESS. Inspeção SSH somente leitura desta execução encontrou o servidor em 6453eab, Git limpo; não presume publicação do merge 0292e2d. A nota local preexistente de keep-capacity-diagnostics-in-system-monitor/validation.md foi preservada e excluída dos commits desta change. Sua task visual segue pendente.

## Diagnóstico e regressões

Seleção Jev em duas passagens retornou histórico e testes, mas não o mecanismo atual; leitura direcionada do componente delimitou key=pathname e feedback genérico. Após atualizar a base, identificada correção d6df74f de reconexão automática já existente. Ela foi mantida; não se atribui ao novo trabalho a recuperação automática entregue por outra change.

- Teste dos seis blocos/dicas/exportações falhou antes (11 passed, 1 failed), por ausência de ajuda. Depois, três arquivos do monitor/capacidade/gate: 34 passed. Ajuda inicialmente alterou a ordem de Tab; sua posição foi corrigida preservando o primeiro foco em Consultar diagnóstico e a regressão existente passou.
- Cores: active/inactive falharam antes (15 passed, 2 failed); depois 17 passed no arquivo do monitor. recent/valid_session/unknown permanecem neutros, nome/e-mail apenas na árvore privilegiada. Contraste calculado contra as cinco superfícies sólidas dos temas/acabamentos existentes (10 combinações): mínimo 5,98:1. Isso valida a paleta declarada; não substitui inspeção visual real depois da publicação.
- Sessão: regressão de rota perdeu o rascunho e voltou ao gate; leitura com probe 503 apresentou aviso de compra/envio incerto. Após corrigir o fixture Request para usar a origem real do jsdom, a nova semântica da mutação ficou coberta. Preservados gate inicial/papel novo, 401/403, retorno permitido, cancelamento intencional, deduplicação/follow-up, timeout, backoff, pausa em aba oculta e ausência de replay.
- Regressões adicionais de 401/403 e recusa de API durante rota pendente: 33 passed no arquivo de sessão. Sinal automático POST /api/auth/activity falhou no teste de aviso comercial; excluído da semântica de ação incerta sem retirar checagem de conectividade, a regressão passou.
- Última execução direcionada: **73 passed**, quatro arquivos, 6,33 s. Apenas Vitest/jsdom; nenhum servidor/container/backend/banco local iniciado.
- Lint inicialmente delimitou uma leitura de ref no render; corrigida por estado explícito do aviso, sem desativar a regra. ESLint dos arquivos alterados aprovado antes da rodada final.

## Implementação e limites

Seis blocos com details/summary acessíveis; detalhes HTTP/histogramas/qualidade removidos somente da UI principal. Contrato/backend de relatórios não alterado: JSON e texto técnico contêm fontes, métricas, versão, qualidade, histórico e incidentes autorizados; árvore/e-mails ficam excluídos. Workers Gemma e demais fontes permanecem no bloco operacional, sem alterar coleta.

SessionBoundary estável por papel, sem autorização persistida em storage; a validação inicial e as revalidações de rota/foco/período continuam. Backend autoriza cada operação. Falha de leitura gera aviso específico, removido após confirmação; mutação com resultado incerto gera status próprio, não aviso de conexão sem evidência, e após confirmação preserva orientação fechável de conferir resultado. O aviso de indisponibilidade continua dependendo da falha da própria leitura de sessão, conforme auto-recover-session-connectivity-notice.

## Comandos reproduzíveis

Na raiz: `npm --prefix frontend test -- app/session-boundary.test.tsx app/admin/system-monitor/monitor.test.tsx app/admin/capacity-diagnostics.test.tsx app/admin/installation-diagnostics.test.tsx --maxWorkers=2`; `npm --prefix frontend test -- --maxWorkers=2`; `npm --prefix frontend run lint`; `npm --prefix frontend run build`; `npx -y @fission-ai/openspec@1.14.0 validate --strict --all --json`; `git diff --check`.

OpenSpec na versão exata do CI: **94 passed, 0 failed** (75 changes e 19 specs). Suíte frontend completa: **494 passed**, 60 arquivos, 84,14 s. Lint completo: **0 erros, 37 avisos preexistentes**. Build Next/TypeScript: **aprovado**, 23 páginas; sem servidor local. O refinamento final explicita que as cores representam a última consulta da árvore sob demanda e apenas atualiza o nome do teste Gemma para o bloco operacional preservado, sem alterar comportamento coberto pela suíte. Logs locais em TEMP, fora do Git.

## Pendência operacional

Task 3.2 permanece aberta. Após CI/deploy verde, conferir no servidor autorizado as dicas, ausência de seções técnicas principais, relatórios sanitizados, cores/estados, navegação e retorno ao foco usando login normal do proprietário. Não fabricar sessão ou extrair credenciais; registrar SHA/evidência sanitizada. Sem carga, limpeza, alterações de configuração/secrets, migration ou recursos de terceiros. Pausar depois do push enquanto CI roda, conforme instrução humana vigente. Sincronização/arquivamento desta change exigem revisão humana própria após validação completa.
