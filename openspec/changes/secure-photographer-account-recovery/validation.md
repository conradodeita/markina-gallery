# Validação local — checkpoint de pausa em 11/11/2026

Pausa explícita do proprietário por orçamento de tokens. Código em implementação; não há commit, push, migration persistente, Oracle, transporte de e-mail real ou alteração de produção. Não confundir este checkpoint com conclusão integral.

## Resultados confirmados

- Backend inicial: 11 aprovados após corrigir normalização UTC do retorno idempotente.
- PostgreSQL Linux descartável R3-A: **25 aprovados**, zero falhas/skips (222,57 s). R3-B: **37 aprovados**, zero falhas/skips (350,49 s). Fontes R3: manifesto SHA-256 `71d7f595da02c5c084d79a4661362f15981d9c950fff65c444b1c5686e50bc7b`. Incluem recuperação assistida, identidade tardia, revogação isolada de TOTP e catálogo/isolamento.
- PostgreSQL complementar R4: **3 aprovados**, zero falhas/skips (44,91 s): dois commits concorrentes, rollback integral ao falhar aviso e limpeza de material expirado. Fontes R4: manifesto `4203e235137f5663d1ff4f8ca9a63a48301ef0cd65f3a21e10fa8cda7448716e`. Nenhuma nova alteração funcional de backend após esse snapshot; posteriores foram de UI/testes documentais.
- Frontend focal final: **30 aprovados em 5 arquivos** (16,91 s): confirmação pública, console de recuperação, revogação de TOTP, encerramento e página da plataforma. Uma expectativa de texto da reabertura foi atualizada para a orientação operacional nova; não se afrouxou o bloqueio de acesso.
- `next build` passou; typecheck passou nos checkpoints registrados. Os últimos ajustes CSS (alinhamento/escopo de select e foco de summary) são posteriores ao build; repetir build final proporcionalmente na retomada. Ruff focal passou antes da pausa; OpenSpec strict e diff --check passaram antes dos últimos ajustes documentais/visuais. Revalidar no fechamento.
- Bateria frontend integral iniciada (sessão 99274), interrompida na pausa sem relatório JSON final confirmado; **não alegar aprovação integral**. A suíte ampla anterior de 687 casos é histórica, anterior a esta implementação.

## Jornada visual

Chrome, frontend Next real em `127.0.0.1:3039`, API sintética em `127.0.0.1:18049`, SQLite exclusiva fora do Git. API do harness injeta sessão de proprietário sintético: a jornada prova componentes/rotas de recuperação e confirmação final, **não prova login real/SMTP/produção**. Não configurou nem enviou mensagens externas.

Fotógrafo abriu link de uso único, escolheu senha própria e recebeu confirmação de aguardar proprietário. E-mail/senha só foram aplicados após senha/TOTP do proprietário. O painel mostrou contato mascarado atualizado e recuperação concluída. Nenhum segredo de usuário real foi usado. Dados e SQLite sintéticos permanecem fora do Git.

Revisados 390/768/1440 px, temas claro e escuro. Sem transbordamento horizontal nos tamanhos medidos. Formulário mobile em coluna, tablet/desktop em duas colunas, botões e checkboxes legíveis; passos com responsáveis, ajuda e novo atendimento recolhíveis. Tema/viewport restaurados ao final. Capturas `recovery-{mobile,tablet,desktop}-{light,dark}.png` no diretório externo. Corrigida leitura dupla de token em StrictMode com teste de regressão.

## Falhas investigadas, sem ocultar limitações

- Primeiro pacote PostgreSQL foi lido antes de concluir compactação: EOF antes de testes; repetido somente após pacote completo.
- R2: 49 aprovados, uma falha de redaction e quatro erros de DiskFull no tmpfs de 512 MiB. Dividido em dois bancos novos R3; nenhum recurso compartilhado foi limpo. A falha real de validação foi corrigida incluindo a nova rota na proteção de corpos inválidos.
- Windows ampliado: 34 aprovados/uma falha de redaction antes da correção. Repetição focal corrigida passou 1/1, seguida de R3 PostgreSQL aprovado.
- Avisos FastAPI on_event/compatibilidade são preexistentes; não confundir com falhas nem iniciar refatoração de lifespan nesta change.

## Pendências de fechamento

1. Provar FK específica de target/tenant e closure/tenant por inserts cruzados e regressão dos resets comuns, worker/limpeza; ampliar testes sem criar mecanismos paralelos.
2. Atualizar somente fixtures de **schema corrente** para 0124. Não trocar revisões congeladas históricas indiscriminadamente. `test_tenant_photographer_migration.CURRENT_SCHEMA`, catálogo/limpezas que exigem schema corrente e fixtures que usam modelos atuais precisam avaliação.
3. Regressão explícita de exclusão definitiva de mídia e reabertura tardia; gate continua no serviço, sem remoção do bloqueio.
4. Revisar diff da change (muitos arquivos já tinham trabalho SaaS anterior); checks finais, frontend integral, build final e documentação. Não usar diff inteiro de auth/main como autoria desta change.
5. Não sincronizar/arquivar sem revisão humana. Não interpretar testes locais como autorização de release; primeiro push continua condicionado ao checklist global completo.

Relatórios e harnesses: `C:/codex-data/visualizations/2026/11/10/closure-review/`. Scripts `run-access-recovery-pg-r3-a.ps1`, `-r3-b.ps1`, `-r4.ps1`, relatórios `access-recovery-pg-r3-a`, `-r3-b`, `-r4`. Todos os PostgreSQL próprios foram removidos por cleanup com label verificada.

## Retomada — 11/11/2026

Pausa revogada pelo pedido explícito de retomada. Novos testes de FKs cruzadas aprovados em SQLite (2/2) e PostgreSQL descartável (2/2); terceira prova PostgreSQL de limpeza legada com schema0124 aprovada, incluindo serialização de inserção concorrente. Relatório `access-recovery-pg-resume/results.xml`:3 aprovados, zero falhas/skips,90,46s, cleanup0. Nenhum PostgreSQL compartilhado foi usado.

Fixtures de schema corrente atualizadas para0124: CURRENT_SCHEMA do catálogo/limpeza de fotógrafos, limpeza de histórico retido, notificações privadas, compras de créditos e rotina corrente de limpeza da migration. Teste específico de redução do perfil continua congelado em0123. As fixtures atualizadas exigem regressão proporcional no fechamento; não declarar todos os consumidores validados só pela edição.

Build frontend repetido com todos os ajustes visuais finais: compilação, TypeScript e geração de páginas passaram. Ruff focal, OpenSpec strict e diff --check passaram na retomada. Mapa central confrontado com design/rotas e todos os links Markdown locais resolvidos. Naquele checkpoint, a retenção do cadastro operacional de clientes ainda estava em aberto; a decisão posterior do proprietário, registrada em `add-photographer-signup-portal/retention-privacy-matrix.md`, removeu o expurgo automático por inatividade e preservou a remoção explícita/auditada quando elegível.

Regressão de exclusão definitiva passou1/1: mesmo simulando atendimento de identidade concluído, `reopen_account` recusa quando a mídia foi eliminada. A prova complementa os testes anteriores de conta encerrada/suspensa e CPF+contato insuficientes; task3.3 concluída. Limpeza técnica nova passou1/1, apagando somente material transitório expirado, preservando ator/alvo/motivo/declaração e sendo idempotente. Não houve alteração de runtime nesta retomada; testes e fixtures foram reforçados.

## Fechamento local — 11/11/2026

- `resume-security.xml`: **26 aprovados**, zero falhas/skips,507,12s. Cobre primitivas, reset comum legado e website sem/com TOTP, códigos de recuperação, worker/outbox, expiração e regressão de exclusão definitiva. Somente SQLite sintética com DATABASE_URL apontada para arquivo externo de QA; sem uso de dados locais operacionais.
- `access-recovery-pg-consumers/results.xml`: **4 aprovados**, zero falhas/skips,104,09s. Catálogo `head=0124` e downgrade vazio seguro; histórico financeiro append-only usando ORM corrente; notificação privada com schema corrente; limpeza legada preservando conta/sessão/canal no schema0124. Cleanup0 dos containers próprios.
- `access-recovery-resume-frontend.json`: **692 testes,691 aprovados/1 falha**, zero pendentes. Falha no monitor em espera de árvore de usuários, fora dos módulos alterados, durante carga concorrente. `resume-monitor-repeat.json`: **21/21 aprovados** na repetição isolada do mesmo arquivo, sem alterar teste/runtime nem aumentar timeout. Evidência compatível com falha temporal sob carga; não chamar a primeira execução de integral verde. Sem falha reproduzida pendente nos módulos da change.
- Lint frontend completo: **0 erros,38 avisos** nas áreas preexistentes de imagens/hooks/variáveis. Nenhum aviso novo no componente de recuperação. Build final e TypeScript aprovados; Ruff focal e strict OpenSpec aprovados; diff --check sem erros (avisos Git de conversão LF/CRLF não foram tratados como alteração de produto).

Revisão de diff proporcional: preservados fluxos comuns e históricos; reaproveitados cifra, hash de senha, outbox, reautenticação, revogação, autorização e componentes visuais. Não há remoção funcional segura adicional exigida nesta change. Nova tabela/migration não modifica nem elimina histórico preexistente. FKs dedicadas testadas contra alvo/encerramento de outro tenant; auditoria mantida após limpeza. Declaração externa permanece decisão humana do proprietário, sem prova automática de identidade ou upload documental.

As dez tarefas da change estão implementadas e validadas localmente. Esta conclusão não é prontidão global para primeiro push, CI remota, SMTP real, autorização de deploy ou publicação. Sync/archive aguardam revisão humana. A revisão geral do candidato e os gates operacionais conservam seus próprios critérios.

## Revisão estática de segurança — 13/11/2026

- Reinspecionados o serviço `photographer_access_recovery.py`, as rotas do console e a prova tardia de conta encerrada. A abertura exige proprietário, declaração explícita, alvo único do tenant, versão atual do fotógrafo, endereço não conflitado e idempotência; o token público é armazenado por hash e o payload transitório com e-mail/senha hash fica cifrado e expira em 15 minutos.
- A confirmação do endereço não cria sessão nem altera credenciais vigentes. A efetivação exige reautenticação do proprietário, revalida ator/sessão/alvo antes do commit, invalida sessões e materiais anteriores, preserva TOTP salvo escolha explícita, revoga códigos/challenges antigos e registra auditoria sem payload secreto. Lifecycle `closed` e status suspenso não são alterados pelo fluxo.
- A prova usada para reabertura tardia só reconhece atendimento concluído, e-mail efetivamente verificado e mesmo fotógrafo/encerramento; ela não reverte exclusão definitiva de mídia. A leitura não encontrou um caminho que transforme nome/CPF ou declaração isolada em login automático.
- Não encontrei regressão de autorização/tenant nessa inspeção. As evidências de testes SQLite/PostgreSQL e da jornada visual sintética estão nas seções anteriores; não foram repetidas nesta revisão estática. SMTP real, credenciais reais e produção não foram usados.

## Reexecução PostgreSQL de recuperação — 15/11/2026

Após autorização de início local, `test_photographer_access_recovery.py -k postgres` executou no PostgreSQL 17.11 descartável em loopback 15470: **4 passed, 19 deselected**, seis avisos FastAPI preexistentes, 93,93 s. Inclui DDL/roundtrip e as três fases de concorrência de uso único; nenhum e-mail externo foi enviado. JUnit externo em `C:/codex-data/local-review/prepush-access-recovery-20261115.xml`. As quatro provas antes ignoradas por falta de banco estão agora executadas.
