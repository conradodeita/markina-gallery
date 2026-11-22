# Pausa solicitada para troca de modelo — 04/11/2026

## Direção DNS vigente — 05/11/2026

- Proprietário escolheu Cloudflare Free para a zona inteira, mantendo Registro.br como registrador e o destino de markina. Continuidade operacional em [migrate-pickyourpic-dns-to-cloudflare](../migrate-pickyourpic-dns-to-cloudflare/migration-plan.md).
- Zona atual autenticada: somente A raiz e A markina para 132.145.193.169; DNSSEC ativo. Não alterar delegação/DS sem plano e revisão específicos; nada pode ser desligado em produção. A proposta Registro.br-primeiro foi substituída.
- Subdomínio automático por tenant e remetente e-mail continuam em avaliação/escopo posterior; trocar DNS não os implementa.

## Decisão mais recente de canais — 05/11/2026

- O proprietário confirmou manter **WhatsApp obrigatório** para uploads por sua dependência no login OTP de clientes. A ideia de torná-lo opcional foi retirada antes de alterar código de onboarding/upload. Essa decisão prevalece sobre qualquer intenção intermediária registrada na conversa.
- Implementação local em Notificações: capacidade de personalizar WhatsApp somente com conexão/identidade próprias confirmadas; bloqueio UI e API/rota legada, com push editável e independente. Campos WhatsApp persistidos são mantidos no salvamento de push após falha de conexão. Rótulo técnico removido da tela Configurações.
- Avaliação por tenant em `email-channel-assessment.md`: escolha exclusiva WhatsApp/e-mail futura, remetente próprio requer autorização de caixa/domínio, clientes precisam de e-mail verificado e OTP/convites exigem decisão específica. Nenhuma opção de e-mail foi implementada ou ativada. Push não integra a escolha exclusiva.
- Evidências e limites atuais no final de `validation.md`; tasks 6.1–6.4 acrescentadas para esta decisão. A revisão humana 5.3 segue pendente, sem sync/arquivo nem produção. O estado histórico de 19/20 tarefas abaixo antecede essas quatro tarefas.

## Atualização prioritária — prova concluída e queda de energia em 05/11/2026

Esta seção e o final de `validation.md` substituem o estado histórico abaixo. O proprietário retomou a execução: não há pedido de pausa vigente. `tasks.md` registra 19/20 tarefas, restando revisão humana (5.3), sem autorização de sincronização/arquivamento ou deploy.

- A jornada no Chrome foi concluída até o upload: conta sintética `ui-flow-20261104@example.test`, senha definida pessoalmente pelo proprietário, perfil com CPF **e endereço obrigatório para compra**, termos sintéticos, 25 créditos simulados, PIX/WhatsApp sandbox e checklist 5/5. Nome/e-mail do ingresso são reutilizados. A indicação antiga de endereço opcional abaixo está superada.
- Checkout local abriu com endereço/e-mail/CPF preenchidos; edição do endereço restrita ao formulário não mudou o perfil. Existe uma compra somente `prepared`; nenhum pagamento foi enviado. Cartão indisponível é intencional na fixture sem Public Key externa.
- A galeria `6e331962-8294-4630-a80c-44f51168576f` recebeu um JPEG geométrico pelo seletor da UI. Worker local processou uma única mídia; UI e SQL confirmaram foto disponível, três prévias prontas e carteira com 24 disponíveis/1 consumido/0 reservados.
- Evidência fora do Git: `C:/codex-data/test-runs/onboarding-ui-20261105-browser/`, especialmente `checkout-prefilled.png` e `upload-available.png`. Sem senha, OTP ou chave em documentação.
- Achado pendente de revisão: painel agregado da pasta ainda mostra Em andamento por etapas opcionais de facial/ajuste, embora a foto esteja disponível. O canal real exige conexão Evolution e identidade de número compatível; sandbox não comprova isso.
- Nova queda de energia parou o container `pyp-photographer-demo-20261104` (Exited 255) e os serviços locais 3039/8000. Capturas persistiram; banco em tmpfs pode ter perdido a conta. Não presumir sessão, não tentar a senha do proprietário e não repetir como pendente a prova já documentada. Se uma nova sessão de demonstração for necessária, conferir isolamento e bootstrap pelo runner existente; definição de senha pela UI exige ação do usuário.
- Nenhuma produção, `.env`, configuração real, canal Evolution real ou outro projeto foi alterado. Próximo passo da change é revisão humana dos resultados e do achado visual, não publicação automática.

## Estado e autorização

- Proprietário pediu: “Quando puder pausar, pause, vou trocar de modelo”. Execução pausada em ponto seguro; aguardar solicitação de retomada. Não há comando de teste/build pendente conhecido.
- Worktree obrigatório: `C:/codex-data/worktrees/saas-release-candidate/Photo Delivery`, branch `feature/saas-release-candidate`. Preservar o amplo diff preexistente. Não trocar para Documents nem outro checkout, não limpar/stash/reset, não fazer commit indiscriminado.
- HEAD observado na pausa: `855be42b826c61c8ebdb2bd1e471ca1d28147061`.
- Change ativa: `add-progressive-photographer-onboarding`, schema spec-driven, **10/18 tasks concluídas localmente**. Produção não foi alterada. Sem autorização de deploy, migration remota, mudança de `.env`/segredos ou interrupção de produção.
- Próxima execução deve ler as instruções da raiz, os artefatos desta change e `validation.md`. As tasks restantes continuam acionáveis; a pausa é pedido do usuário, não bloqueio técnico geral.

## Decisões do proprietário

- Website ativa conta exploratória automaticamente após e-mail verificado e senha, sem TOTP nem aceite operacional no ingresso.
- Cadastro completo: nome completo e CPF; telefone/endereço não são exigidos. **Resposta expressa mais recente: um único tenant por CPF**, mesmo com e-mail diferente. Regra já registrada no design/delta e alinhada ao metadata; a constraint global da migration 0099 foi preservada.
- TOTP voluntário; após ativação torna-se obrigatório no login. Proprietário pode revogar em atendimento com motivo, senha + TOTP, auditoria e aviso ao e-mail verificado.
- WhatsApp próprio por tenant, com autoconfiguração pelo fotógrafo. Sandbox local não comprova pareamento/entrega real. Mercado Pago próprio é opcional; termos são sintéticos locais sem validade contratual.

## Implementado e validado

- Login da UI foi corrigido para seguir `destination: /admin` sem mostrar TOTP indevido. Retorno administrativo passa pela validação interna existente. Proprietário/legados mantêm MFA.
- Perfil usa CPF validado/cifrado, fingerprint global único, payload `SecretStr`, sanitização de validação, respostas `no-store`, filtro explícito por tenant e erro neutro para duplicidade. Aceite de teste é idempotente e append-only; requisitos falham fechados fora do ambiente local.
- Enrollment TOTP: `backend/app/photographer_totp.py`, tabela dedicada da migration 0100, QR/chave somente na resposta inicial, senha atual, expiração de cinco minutos, limite de cinco erros, vínculo de sessão/tenant, consumo do passo, novos códigos Argon2id e revogação das sessões. Limpeza existente do worker minimiza envelopes expirados.
- AAD temporário foi reforçado com administrador real + contexto da tentativa/tenant/sessão. `TotpSecretCipher` aceita contexto opcional; formato/AAD dos fatores ativos anteriores permanece compatível. Teste independente do wire format anterior cobre leitura e escrita compatíveis.
- Recuperação assistida: `backend/app/photographer_totp_support.py`, `frontend/app/admin/platform/photographer-totp-support.tsx` e migration 0102. Consulta específica owner-only preserva resumo genérico do console; motivo controlado, versão opaca do fator, request-id idempotente, reautenticação forte e transação que revoga fator/sessões/códigos/desafios/tokens/enrollment e insere aviso na outbox cifrada. Falha do aviso reverte alterações; replay antigo não revoga fator novo.
- Migrations: 0099 perfil/aceite; 0100 enrollment; 0101 FKs compostas perfil/aceite para `tenant_admin`; 0102 auditoria da recuperação assistida. Sem correção automática de dados incompatíveis. Rollbacks com histórico/dados protegidos são recusados.
- Runner `scripts/local_photographer_demo.py` agora exige schema 0102 e deriva chaves sintéticas por propósito da credencial aleatória do PostgreSQL descartável, em memória. Permite reinício consistente. Somente o proprietário de bootstrap com identidade/ref exatas e senha de login desabilitada pode ter seu envelope de teste reconstruído.

## Prova do fluxo e serviços deixados disponíveis

- Docker: contexto `desktop-linux`; container exclusivo `pyp-photographer-demo-20261104`, PostgreSQL 17.11, `127.0.0.1:15472/pyp_ui_demo`. Porta 15470 para `pyp_photographer_test`. Dados em **tmpfs**: desligar/reiniciar esse container perde os dados sintéticos. Não alterar containers Evolution ou outros projetos.
- API local `127.0.0.1:8000`, **sessão de execução da ferramenta 1586** (não é PID). Next `127.0.0.1:3039`, sessão de execução 41397. Ambos ficaram disponíveis. Schema real local atualizado para **0102**; API foi reiniciada por último e informou pronta.
- Último teste HTTP de TOTP real e preservação de perfil/saldo foi antes do último reinício/AAD reforçado. Código atual passou nos testes focados; ainda é útil um smoke de runtime após esse último reinício, sem modificar contas reais.
- Conta da prova: `ui-flow-20261104@example.test`. Senha é a fixture sintética do runner/testes; não copiar credenciais para chat/documentação. Outra conta sintética `totp-runtime-20261104@example.test` ativou TOTP no teste HTTP anterior; segredos/códigos não foram registrados.
- Galeria local: `3fdbec8a-728c-46ab-8a0a-dc9d04729eb7`, pasta “JPEGs sintéticos”. Primeiro JPEG enviado por HTTP; segundo (`pyp-ui-upload-manual.jpg`) enviado manualmente pelo proprietário. Worker local gerou prévias, sem inferência facial.
- Banco e Chrome confirmaram **2 fotos disponíveis, saldo 23, 0 reservas e 0 operações pendentes**; partiu de concessão sintética de 25 créditos. Não houve cobrança nem mensagem externa.
- Chrome reconectou como browser **4**, extensão `9d8c3ad7-0734-464c-9cfd-ebfc3b42b3ba`; browser 3 está obsoleto. Aba local de imagens `1714871018`; carteira `1714871006`. Há abas de produção no mesmo Chrome: operar somente localhost nesta task. Última parte CUA encerrada com `completion_summary` (“Confirmou upload e crédito”).
- Permissão de upload automatizado da extensão não foi confirmada. O proprietário realizou o envio manual. Não automatizar alterações de segurança do Chrome para contornar isso.

## Evidências e limites

- Cadastro anterior: 12 passed/2 skips PostgreSQL opcionais. Dois testes focados de perfil/validação após proteção do CPF: 2 passed em 32.47 s.
- Enrollment + toda segurança administrativa + runner unitário: 35 passed/1 skipped em 547.77 s. Smoke opt-in executado depois separadamente: runner 4 passed em 4.66 s.
- Formato TOTP: 8 passed para replay/janela/Unicode inválido. Após AAD adicional e CPF global, seleção focada: **8 passed/25 deselected em 38.61 s**, cobrindo ciphertext anterior, contexto/rotação, ativação, sessão diferente e CPF A/B duplicado/distinto.
- Login sem fator para tenant suspenso ou vínculo inativo: **2 passed em 28.24 s**.
- Recuperação assistida: primeiro grupo **9 passed em 122.20 s**; HTTP novo + resumo legado **4 passed em 54.07 s**; replay com fator novo **1 passed em 18.43 s**. Essas execuções, juntas, cobrem os 13 casos atuais do novo arquivo. Regressão de status/suspensão após extrair helper de reautenticação: **4 passed em 47.06 s**.
- PostgreSQL: onboarding até 0102 + teste histórico 0096: **2 passed em 54.20 s**. Cobre upgrade/downgrade vazio, bloqueio com dados, isolamento, triggers append-only, recusa de vínculo inválido e histórico preservado. O teste histórico 0096 usa INSERT SQL daquele contrato, sem exigir colunas futuras do modelo ORM.
- UI de entrada/segurança/recuperação/enrollment: **42 passed**; componente de enrollment repetiu com **3 passed** após ajuste. UI de suporte + console: **7 passed**, ESLint e typecheck passaram.
- Build do frontend passou antes do novo componente de suporte do console. Esse novo componente passou em testes/typecheck, mas a build final dele ainda deve ser executada no checkpoint 5.1. Ruff focado e OpenSpec passaram antes das últimas adições; repetir revisão/validação final. Não declarar suite global/CI/publicação executada.
- Avisos históricos: FastAPI `on_event` deprecado e ciclo de FKs em DROP SQLite nas fixtures. Não houve limpeza/refatoração geral.

## Próximos passos seguros

1. Revisar o diff da área afetada, repetir Ruff/OpenSpec/build no checkpoint adequado e verificar o runtime local 0102 após o último reinício. Se necessário, reautenticar apenas a conta sintética no Chrome; o teste HTTP anterior pode ter revogado a sessão do navegador.
2. Task **1.4**: autoprovisionamento real idempotente do WhatsApp por tenant e credenciais protegidas, preservando aliases/canal legado. `whatsapp_binding.py` ainda usa configuração de servidor. Foi observada corrida na criação de `whatsapp_channel_settings` em GETs paralelos (violação de unicidade tenant/ambiente); corrigir nesse escopo. Implementar/testar com adaptador falso; não operar Evolution real nem alterar segredos sem autorização.
3. Tasks **4.1/4.2**: completar testes de bypass, webhook/reconciliação, saldo/revisão financeira, concorrência e tenant cruzado. Os gates existentes ainda são chamados antes de procurar uploads/reservas já aceitos; revisar retomada quando PIX/WhatsApp mudam para preservar reconciliação. Conferir também capa/lotes e a regra de saldo sem cobrar crédito de ativo técnico indevidamente.
4. Task **4.3**: finalizar retorno contextual seguro de compra/upload para Configurações; não colocar CPF/senha/OTP/chave em URL ou armazenamento persistente do browser. UI básica e TOTP já existem.
5. Task **4.4**: caminho positivo foi provado com upload manual; faltam negativas integrais de todos os gates. Não marcar completa apenas pelo resultado positivo.
6. Fechar **5.1/5.2** com evidências proporcionais. Documento jurídico/identidade do provedor, retenção, transporte/anti-bot reais e publicação continuam gates externos. Aviso de revogação foi validado como outbox, não como entrega SMTP real.
7. **5.3** exige revisão humana antes de sync/archive. Não fazer deploy nem alterar produção.

## Continuidade de ferramentas

Skill `ai-memory-handoff` consultada; `memory_handoff_begin` não está exposta nesta sessão. O handoff está neste repositório; não foi gravado em memória externa. Jev foi usado para selecionar evidência do console (sessão `15069a77-509d-4c18-8462-be73ba0838bd`). Não é necessário repetir buscas amplas.

---

# Pausa atual por limite de tokens — 04/11/2026

## Estado vigente

- O proprietário pediu pausa porque os tokens estão se esgotando. Não continuar até novo pedido.
- Mesmo worktree `C:\codex-data\worktrees\saas-release-candidate\Photo Delivery`, branch `feature/saas-release-candidate`, HEAD conhecido `855be42b826c61c8ebdb2bd1e471ca1d28147061`; diff amplo preexistente, preservar. Produção permaneceu fechada e intocada.
- Change `add-progressive-photographer-onboarding`: **13/18 tasks concluídas**. 4.2 foi validada e marcada; 4.3 está em andamento e NÃO está marcada. 4.4 e 5.1–5.3 permanecem pendentes.
- Para retomar: reler este checkpoint e a seção mais recente de `validation.md`; revisar diff antes de continuar. Não repetir a suíte backend de 455 s sem necessidade.

## Concluído nesta retomada

- Task 4.2: `require_upload_ready` permite replay/reconciliação apenas quando existe `PhotoCreditOperation` do mesmo tenant/foto com storage key + fingerprint coincidentes e status `reserved`, `reconciliation_required` ou `consumed`. Registro idempotente e importação agora localizam o ativo antes do gate; novas identidades continuam bloqueadas sem onboarding. Nenhuma alteração no ledger/worker.
- Task 4.2 validada: quatro módulos backend (`test_photographer_credits.py`, `test_tenant_acervo.py`, `test_private_upload_batches.py`, `test_photographer_signup.py`) tiveram **70 passed, 13 warnings em 455.32 s** no PostgreSQL descartável local. Depois, três cenários focados repetidos com teste HTTP real para upload novo: **3 passed, 26 deselected em 22.29 s**. Ruff focado passou. OpenSpec strict válido.
- Task 4.3: adicionado link de ingresso “Criar conta de fotógrafo” em `auth-entry.tsx`, sem exibi-lo no contexto cliente.
- Implementado retorno contextual da gate: `photographer-onboarding-gate.ts` valida caminho `/admin/...`, remove query/hash e recusa traversal; `upload-jpeg.ts`, registro da galeria e `credits/page.tsx` disparam evento apenas para código/URL canônicos; `OnboardingGateNotice` no layout admin abre Configurações em nova aba e mantém original em memória; onboarding-panel valida `return_to` e oferece voltar à rota interna. Nada é salvo no localStorage/sessionStorage.
- Adicionados testes unitários para retorno/aviso, onboarding-panel e integração do upload JPEG; atualizado o mock do checkout de créditos para responder a `checkout-identity`.

## Validações frontend e pendências exatas

- Depois do aviso, a seleção de 8 arquivos frontend teve **59 passed em 16.60 s**: helper/aviso do gate, painel onboarding, login, cadastro, TOTP, upload JPEG e créditos. O teste 4.2 já foi validado independentemente no backend.
- ESLint focado apontou um erro `react-hooks/set-state-in-effect` no sync do `return_to` e um import `describe` não usado no teste; ambos foram corrigidos imediatamente antes da pausa, mas ESLint **não foi repetido**. Reexecute `npx eslint` nos arquivos alterados.
- `npx tsc --noEmit` não foi repetido após o novo helper/evento/layout. O teste completo de `gallery-editor.test.tsx` e build frontend também estão pendentes. `onboarding-panel.test.tsx` usa um comentário de supressão ESLint justificado pela leitura pós-hidratação de `window.location.search`; revisar no lint.
- Os warning de `<img>` em `gallery-editor.tsx` são anteriores/fora do escopo e não foram alterados.
- Uma execução focal anterior falhou em três provas; causas corrigidas: mock de 503 sem `.json()`, `act()` ausente no teste do aviso e teste do checkout sem fixture de `/api/admin/onboarding/checkout-identity`. A execução posterior acima passou.
- `signup_services()` ainda não tem adaptador de provedor configurado e responde 503. A UI pública manda `anti_bot_proof: ""`; não implementar bypass sem documentação/contrato local separado. Isso é gate externo de produção, não justificativa para abrir a rota pública.

## Próxima sequência de trabalho

1. Rerun ESLint focado e `npx tsc --noEmit`; corrigir toda falha atribuível ao diff.
2. Rodar `app/admin/galleries/gallery-editor.test.tsx` e os testes de aviso/checkout se o escopo de execução tiver mudado.
3. Confirmar segurança e contrato do gate, completar provas HTTP positivas/negativas necessárias; então decidir se 4.3 pode ser marcada e documentar evidência atualizada.
4. Prosseguir para 4.4: jornada sintética local no browser. Primeiro inventariar processos/portas e container tmpfs; reinício pode apagar banco sintético. Não tocar em processos/serviços que não sejam comprovadamente desta demonstração.
5. Depois, executar 5.1 e 5.2. 5.3 requer revisão humana. Nenhuma etapa autoriza production, migrations remotas, deploy, mudança de segredo ou parar o sistema de clientes.

## Arquivos tocados nesta parte

- Backend 4.2: `backend/app/main.py`, novo `backend/app/photographer_onboarding.py`, `backend/tests/test_photographer_credits.py` (estes arquivos já possuem diffs preexistentes amplos, não restaurar).
- Frontend 4.3: `frontend/app/auth-entry.tsx`, `frontend/app/auth-entry.test.tsx`, `frontend/app/upload-jpeg.ts`, `frontend/app/upload-jpeg.test.ts`, `frontend/app/admin/layout.tsx`, `frontend/app/admin/onboarding-gate-notice.tsx` + teste, `frontend/app/photographer-onboarding-gate.ts` + teste, `frontend/app/admin/settings/onboarding-panel.tsx` + teste, `frontend/app/admin/credits/page.tsx` + atualização de fixture em teste.
- OpenSpec: `tasks.md` 4.2 marcado após validação; `validation.md` contém checkpoint atual; `pause-handoff.md` registra esta pausa. Todos os artefatos permanecem em português.
