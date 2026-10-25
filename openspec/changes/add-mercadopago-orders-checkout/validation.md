# Validação em desenvolvimento

- Base: origin/main cef5bdf8; branch feature/mercadopago-orders em worktree isolado.
- OpenSpec estrito: aprovado antes do código.
- SDK oficial mercadopago 3.6.0 instalado após autorização explícita do proprietário; frontend npm ci preservou lockfile.
- Schema SQLite descartável: 2 testes aprovados, preservação de histórico e FKs/uniqueness.
- Configuração: 4 testes aprovados, 11 avisos preexistentes/depreciações, 56,51s. Cofre contextual, senha/OTP vinculado, replay/versão, flags, bloqueio conta real, dados inválidos sem eco de segredos, limite de corpo e origem. Ruff aprovado.
- Primeira execução encontrou RequestOptions exigindo timeout float; corrigido para 15.0 e repetido com sucesso.

## Checkpoint anterior à disponibilização de credenciais

MCP Mercado Pago e ai-memory não expõem tools nesta sessão. Nenhum webhook HTTPS de desenvolvimento foi registrado. O proprietário confirmou acesso ao Developers e Public Key/Access Token no ambiente Teste. Foi solicitado apenas o caminho de um JSON externo ao repositório para receber os valores com segurança. O browser controlado retornou `Local browser use is disabled in Work settings`; não foi contornado para acessar o painel/perfil pessoal. Nenhum teste externo ou cobrança foi realizado até este registro.

A documentação atual dispensa comprador separado para o teste básico Orders; a exigência antiga da skill foi corrigida nas instruções do guia. Não criar contas extras sem necessidade (a documentação informa limite e ausência de exclusão).

## Checkpoint local final

| Validação | Resultado verificável |
|---|---|
| PostgreSQL: schema + checkout + webhook/estados + projeções + fairness do worker | **41 aprovados**, 7 avisos, 138,14s |
| Configuração sensível/cofre/OTP/flags | **4 aprovados**, 10 avisos, 79,14s; teste de resposta segura/caminho público repetido após ajuste: 1 aprovado, 21,03s |
| Regressões: unified_checkout, payment_shortcut_projection, notification_payments, order_delivery, admin_client_directory, homolog_cleanup, tenant_ownership_schema | **97 aprovados, 7 ignorados**, 72 avisos, 896,37s; itens dependentes de ambiente específico mantêm skip explícito |
| Regressões: payment_operations_redesign, checkout_retirement, payment_availability | **16 aprovados**, 209,98s |
| Frontend checkpoint integrado | **66 aprovados em 10 arquivos**, 29,57s |
| Frontend repetição focal: checkout/produto/carrinho/entrega | **23 aprovados em 5 arquivos**, 14,45s; alteração de mensagem de entrega revalidada: 11 aprovados em 2 arquivos, 4,61s |
| Build Next.js | **Aprovado**, compilação/typecheck e rotas, inclusive /library/checkout |
| TypeScript | `npx tsc --noEmit`: sem erros |
| ESLint frontend completo | **0 erros, 36 avisos**; avisos de imagem e padrões já presentes, inclusive imagem de QR no checkout |
| Ruff de todos os Python modificados/novos | **Aprovado**; parênteses do DDL ajustados com AST idêntica antes/depois |
| OpenSpec | `openspec validate add-mercadopago-orders-checkout --strict`: aprovado |
| Whitespace | `git diff --check`: aprovado |
| CTA oficial | `validate-checkout-cta.mjs checkout-api .../cart/page.tsx /library/checkout`: aprovado |
| Visual Edge/Playwright isolado com API/SDK sintéticos | **6 combinações**: 390/768/1440 px, claro/escuro; 25 capturas, sem overflow horizontal ou erro JS; cartão, Pix pendente, Compras, painel parcial e falha do SDK |

As contagens de repetições não devem ser somadas como testes distintos. Nenhum resultado local substitui o teste externo.

## Cenários financeiros cobertos

Valor e método da Orders, chave estável/UUID, cotação autoritativa, alteração de revisão antes do envio, snapshots após envio, abandono preparado, recusa e restauração, tentativa nova, cancelamento confirmado, resposta perdida/busca vazia, envio concorrente PostgreSQL com um único POST, acesso cruzado, validação de valor/referência/conta, assinatura inválida/conta/ID divergente, callback repetido, eventos fora de ordem, lease expirado, backoff/falha transitória, recuperação de ID perdido, polling ativo e após confirmação, reembolso integral/parcial, contestação, aprovação antiga com nova tentativa preparada e com nova cobrança pendente, sobreposição em revisão, rotação para o mesmo recebedor e recusa de outro, tenant suspenso, dados inconsistentes sem loop imediato, proteção de exclusão/reset, CSV anterior/detalhado, filtros/indicadores/histórico e passagem pelas filas existentes.

## Achados corrigidos durante validação

- Timeout do SDK requeria float: corrigido para 15.0.
- Histórico legado vazio exigia contrato sem chave adicional vazia: emissão MP agora condicional, como a projeção legada.
- Recurso inconsistente precisava de backoff para não monopolizar o worker; teste específico aprovado.
- Polling precisava continuar após estado final; detecção de refund sem callback comprovada localmente.
- Rotação de credenciais precisava reconhecer compra antiga do mesmo recebedor sem trocar sua FK.
- Inbox recebeu fencing e lock de processamento; ciclo de worker garante passagem por filas existentes.
- Caminho público do webhook precisava incluir /api, conforme rewrites/NGINX existentes.
- Mensagem de entrega MP não orienta confirmação manual.
- O ensaio da guarda de reset usa inspector na conexão do schema privado; primeiro ajuste de ambiente e depois de search_path corrigiram a fixture, sem executar limpeza ou alterar a política operacional.

## Recursos locais e preservação

PostgreSQL dedicado `markina-gallery-mp-orders-test`, porta loopback 55888, imagem observada `sha256:18cfe3ef5e6815560c98237d6216d1e5119702fb0f3894c8785dd58b8bbe5d73`, volume tmpfs e schemas aleatórios. Nenhum container preexistente foi alterado. Next de QA na porta 3117 foi encerrado depois das capturas; a mudança automática em frontend/AGENTS.md foi restaurada pontualmente.

Artefatos locais ignorados: `.codex-tmp/mercadopago-visual/report.json` e PNGs, logs de lint/build, venv/node_modules e bancos descartáveis. Não integram o diff versionável. Worktree inicial divergente foi preservado. Não houve commit/push, deploy, migration operacional, leitura/modificação de credencial de produção, operação financeira real ou execução de reset.

Continuidade: container PostgreSQL dedicado permanece disponível para o próximo ensaio externo; demais processos de teste/Next de QA foram encerrados. O proprietário recebeu modelo JSON com apenas access_token/public_key e exemplo de caminho externo ao repositório; nenhum valor foi recebido/lido até este checkpoint. A única task de execução pendente é 5.2, dependente dessa configuração e do webhook HTTPS.

## Validação externa concluída e checkpoint posterior

O checkpoint anterior foi superado: o proprietário forneceu caminho do JSON de Teste, identidade `/users/me` foi validada como MLB/test_user, e SDK/tokenização/Orders/GET foram executados contra o provedor de teste. Resultado detalhado, IDs e limites estão em **external-validation.md**.

- APRO R$ 21 aprovado; FUND recusado por insufficient_amount após recuperação conservadora do HTTP 402; CONT mantido em processing com cancelamento recusado pelo provedor.
- MP Pix R$ 21 gerou QR/copia e cola; cancelamento confirmado restaurou seleção; alteração subsequente criou revisão de R$ 14 preservando a cobrança antiga e abandono local preservou as fotos.
- Simulador oficial Pix APRO R$ 50 foi confirmado por GET e banco. O campo do simulador existe só no harness do teste.
- Refund parcial/integral confirmou estados por GET, banco, Compras e painel; CSV filtrado comprovou 4/12 colunas e 2 linhas.
- Duas notificações genuínas do Mercado Pago, da mesma order (partial → full refund), tiveram HMAC válido e inbox done/attempts=1. O worker aplicou cada estado, preservando valor/IDs e um único evento de confirmação.
- Resposta perdida foi testada no browser com tokenização oficial e um único POST. Achado do contador foi corrigido; repetição comprovou Carrinho (0). Teste de regressão reproduziu falha antes da correção.
- Teste HTTP 402 acrescentado; checkout PostgreSQL repetido com **10 aprovados**, 59,73s.
- Frontend final: **84 aprovados em 13 arquivos**, 19,01s; checkout isolado 6 aprovados; `npx tsc --noEmit` sem erros. ESLint dos arquivos alterados sem erros, um aviso de imagem QR.
- Build de produção repetido após a correção: aprovado. Uma tentativa adicional de iniciar o frontend local com `npm run start` foi rejeitada pela revisão automática de aprovação com a mensagem genérica `blocked by policy`; não houve contorno. As verificações externas anteriores de UI/contador e os testes/build posteriores permanecem válidos; o webhook foi comprovado diretamente na API/worker, sem depender dessa inicialização adicional.
- Túnel Cloudflare oficial 2026.10.3 foi autorizado explicitamente, limitado a gateway POST do callback exato e encerrado após o ensaio. TLS público/401 para assinatura inválida/404 para demais rotas comprovados. Indisponibilidade do túnel após parada: HTTP 530.
- Cadastro exclusivamente no ambiente Teste foi executado por computer-use após autorização do proprietário. Verificações de identidade foram realizadas pelo próprio proprietário; assinatura ficou oculta e foi salva somente no arquivo local de testes autorizado, sem eco em tool outputs/relatórios.

Matriz final Orders PostgreSQL repetida após os achados externos: **42 aprovados**, 7 avisos, 156,18s. Verificação de segredos no diff: 57 arquivos modificados/novos examinados, nenhuma ocorrência do Access Token/segredo de webhook reais do arquivo de teste e nenhum .env alterado.

A verificação de identidade adicional foi concluída, mas a retirada da URL temporária ficou bloqueada pelo formulário: URL vazia recusada e Salvar desabilitado sem eventos. Nenhuma alteração parcial ficou salva. O túnel e os servidores locais foram encerrados (sem listeners em 18117/18118/3117); PostgreSQL dedicado/histórico permanecem para revisão. A URL encerrada permanece apenas em Teste e deve ser substituída antes de novo ensaio. A revisão humana da change continua pendente; nenhuma operação de produção foi executada e a medição de qualidade com pagamento produtivo não foi acionada.

## Revisão e preparação do ensaio restrito — 24/10/2026

- Decisão do proprietário: aceite final na instalação de produção, com administrador/cliente próprios e credenciais exclusivamente de teste. Execução operacional ainda depende dos gates de `release-plan.md`; não houve SSH, deploy, migration ou configuração remota.
- Corrigidos dois achados da preparação: disponibilidade de conta de teste antes era geral por fotógrafo; agora é restrita por par tenant/cliente no servidor fora de desenvolvimento/teste. O worker geral não recebia o cofre necessário a inbox/consulta; o binding genérico agora tem somente API e worker como consumidores.
- Compras/painel marcam TESTE; receita/vendas reais e CSV padrão excluem simulações; CSV detalhado preserva identificação e doze colunas. Conta real sintética comprova que a receita/CSV reais continuam válidos. `live_mode` externo divergente da conta verificada é recusado.
- Matriz PostgreSQL/contratos operacionais: **58 aprovados**, 7 avisos, 131,17s. Configuração/PIX/painel/estatísticas legadas: **22 aprovados**, 21 avisos, 230,78s, em SQLite privado; configuração ampliada para dois fotógrafos: **5 aprovados**, 12 avisos, 64,95s. Repetição do contrato operacional sem dependência YAML: **13 aprovados**, 0,46s. As repetições não são somadas.
- Um relacionamento ORM inicialmente ficou ambíguo por FKs simples/compostas; corrigido com join explícito de conta **e tenant**, somente leitura. A matriz completa repetida passou. A fixture legada de configuração não suporta drop de constraints cíclicas em PostgreSQL; repetida no SQLite privado previsto, sem alterar migrations ou dados operacionais.
- Card refinado com tokens visuais existentes, status, escolhas independentes, hints associados por aria-describedby, credenciais sem preenchimento de valores salvos, URL completa copiável e senha/OTP preservados. Três testes novos verificam dicas, segredo, origem da cópia e falha de clipboard. Teste HTTP com dois fotógrafos verifica contas, flags, versões e desafio de confirmação isolados.
- Frontend integrado: **87 aprovados em 14 arquivos**, 16,51s; testes focados de hints/cópia e produto: 6 aprovados, 3,34s.
- Inspeção visual do DOM dos componentes reais com API sintética, sem servidor/túnel: **24 capturas** (configuração nova/conectada/OTP e opções do carrinho × 390/768/1200px × claro/escuro), sem overflow/erro JS e com todas as imagens carregadas. Screenshots inspecionados; bloco PIX manteve grid após nova identificação visual. Evidência local ignorada: `.codex-tmp/payment-ui-review/`; não equivale a login nem ensaio no servidor.
- ESLint dos arquivos afetados: 0 erros, 3 avisos existentes de ref/QR; TypeScript aprovado. OpenSpec estrito aprovado após repartir requisito excessivamente longo. Ruff aprovado. Build final e CI remoto são registrados no checkpoint seguinte.
- Refatoração proporcional: join de conta explícito/eager para projeção sem consulta por item; binding apenas aos consumidores reais; sem limpeza geral, troca de credenciais, descarte de histórico ou alteração de outros projetos.

### Checkpoint final do diff/PR

Build Next.js final aprovado (compilação, TypeScript e rotas); ESLint completo: 0 erros/36 avisos, mesmos avisos do checkpoint anterior. Ruff dos Python modificados/novos aprovado; git diff --check aprovado. 67 arquivos relacionados revisados; nenhum token/segredo real do JSON externo encontrado nos arquivos versionáveis; SVGs estáticos sem scripts/eventos/rede. Nenhum artefato de captura/banco/cache foi incluído.

A consulta autenticada read-only de alertas Dependabot da **main**, após aviso do push, retornou 50 abertos: 5 críticos, 25 altos, 19 médios, 1 baixo. Nenhum dos retornados é de mercadopago/httpx/requests/urllib3/cryptography; isso não constitui auditoria integral nem prova de ausência de vulnerabilidade do candidato. A fonte agora responde com itens, diferentemente da observação histórica de alertas desabilitados em 19/10; não alteramos a configuração nem resolvemos alertas fora do escopo. Reavaliar aplicabilidade/exposição antes de publicação, em trabalho próprio quando necessário.

O OpenSpec local 1.14.1, executado globalmente com --strict --all --no-interactive, encontrou **107 aprovados/31 recusados**. Comparação com export íntegro somente do openspec da main cef5bdf8, usando o mesmo binário/comando, resultou em **106 aprovados/31 recusados**: os 31 itens recusados já pertencem à base, por avisos de requisitos longos. A nova change passa isoladamente. Nenhuma spec alheia foi reescrita para contornar isso. CI usa explicitamente OpenSpec **1.14.0**; o run da base 40125512307 estava aprovado. Resultado do CI do candidato é registrado separadamente, sem chamar o comando global local de aprovado.

### CI do PR #283 — correção do consumidor de inventário

Run 40145339494 do SHA 5dfce1fd: OpenSpec 1.14.0, gitleaks, frontend e imagens AMD64/ARM64 aprovados; backend interrompido no teste do relatório de terceiros porque o consumidor ainda exigia 68 itens e as entradas novas estavam antes de 57–68. Inventário ordenado 01–72, resumo/expectativa/testes sincronizados sem relaxar a validação. Manutenção local usa alias UTC equivalente nos dois scripts afetados. **11 testes unittest aprovados**, 0,022s; Ruff aprovado. Nenhum workflow de deploy, gate operacional, fonte externa ou configuração foi alterado. O novo CI precisa validar o SHA corrigido.

### Ponto de retomada solicitado pelo proprietário

O proprietário pediu interromper o acompanhamento do CI e informou que trará o resultado. PR #283 em https://github.com/conradodeita/markina-gallery/pull/283; SHA candidato bda3751a8600e024cbc40895c4ded0f76b82376c; run 40145688931. Na última consulta anterior ao pedido, OpenSpec/gitleaks/escopo/frontend/Gemma/imagens AMD64 e ARM64 estavam aprovados; backend executava pytest. Não consultar novamente nem cancelar o run neste encerramento; confirmar o resultado e o SHA ao retomar. Task 6.2 permanece pendente dessa evidência.

O proprietário identificou seu cadastro de cliente já existente em produção no chat; nome/telefone não foram copiados ao repositório. UUID de cliente/tenant ainda não conferido no painel. Nenhum cadastro, carrinho, seleção ou compra operacional foi alterado; não reutilizar os clientes sintéticos locais como identidade produtiva. Consulta HTTPS pública read-only em 24/10/2026 às 21:14:24 de São Paulo retornou 200 em /healthz e /api/health (status ok, TLS verificado); não identifica SHA/schema/UUIDs nem substitui inventário operacional. Nenhum SSH/deploy/migration/configuração remota foi executado.

A nota de continuidade é local e ainda não foi commitada/enviada, para não iniciar outro CI enquanto o proprietário acompanha o resultado. Após o CI do código, registrar evidência final e concluir a preparação do PR; execução operacional continua dependendo dos gates de release-plan.md.

### Acompanhamento retomado — correções do CI integral

O proprietário pediu retomar o acompanhamento. Run 40145688931 (bda3751a) terminou com OpenSpec/gitleaks/escopo/frontend/Gemma/imagens AMD64 e ARM64 aprovados. Pytest integral: **9 falhas, 1648 aprovados, 23 skips**, 665 avisos, 1316,07s. O gate agregado recusou corretamente o resultado; nenhum job de deploy foi executado.

Correções: expectativa explícita do campo aditivo payment_provider no histórico PIX; catálogos históricos 0069/0070 excluem as quatro tabelas e a FK posteriores de 0088; ensaios que usam ORM/inventário atuais agora migram até 0088. Nenhuma migration histórica foi editada. Reset proprietário classifica configuração Orders por tenant, preserva conta/envelopes/preferências do proprietário e pode remover somente preparações locais não enviadas; predicado compartilhado impede inventário/execução com tentativa enviada ou inbox de qualquer tenant, inclusive outra conta. A execução verifica novamente sob locks.

Validação dirigida: **21 aprovados, 2 skips, 7 avisos**, 159,99s, cobrindo as nove falhas e quatro casos novos de evidência financeira (envio/inbox × proprietário/outro tenant). Skips: limpeza SQLite não aplicável e symlink não disponível neste Windows; CI Linux cobre o symlink. Guarda de limpeza integral repetida: **1 aprovado**, 7 avisos, 6,28s. Política estática owner-reset, Ruff dos afetados, OpenSpec da change e git diff --check aprovados.

O PostgreSQL adicional é exclusivamente local e descartável: container markina-gallery-mp-migration-ci, loopback 15470, banco pyp_photographer_test, imagem já disponível sha256:18cfe3ef5e6815560c98237d6216d1e5119702fb0f3894c8785dd58b8bbe5d73, tmpfs. Fixtures usam schemas/bancos UUID próprios. Nenhum reset/migration operacional, SSH ou recurso de terceiros foi alterado. O container original 55888 com histórico externo de teste foi preservado.

### CI integral aprovado — encerramento da preparação

Run https://github.com/conradodeita/markina-gallery/actions/runs/40148076942, SHA **47af72bdf503295e93b1ee8e68bef97da2d9d947**, concluído em **24/10/2026 às 22:10:17 (São Paulo)** com resultado success. Confirmado novamente após o pedido de continuação do proprietário. PR #283 continua apontando para esse SHA.

Backend: pytest integral **1661 aprovados, 23 skips, 665 avisos**, 1141,66s; regressões adicionais de concorrência PostgreSQL, 4 aprovadas; inventário de exclusão PostgreSQL, 1 aprovado. Frontend (lint/testes/build), OpenSpec global com versão 1.14.0 fixada no CI, gitleaks, escopo, Gemma offline, imagens AMD64/ARM64 e gate agregado homolog-inventory-policy aprovados. Não somar repetições ou subetapas como testes distintos. Jobs de deploy/preflight operacional ignorados; nenhuma publicação foi executada. A limitação do OpenSpec global local 1.14.1 permanece documentada, sem contradizer o resultado remoto da versão 1.14.0.

Preparação do PR/plano (task 6.2) concluída e evidência incluída na descrição do PR, sem modificar o SHA já validado. Este fechamento documental fica no worktree e não foi enviado como novo commit, evitando outro CI idêntico somente para registrar o recibo. Próximos gates permanecem em release-plan.md: operação específica de release, inventário atual, backup/recuperação, identificação autenticada dos UUIDs do cliente/tenant do proprietário e autorização concreta antes de qualquer alteração operacional. Task 6.3 não executada; task 5.4 mantém bloqueio externo da URL temporária de Teste.

### Inventário de preparação — 25/10/2026

Seguimento após aceite explícito da janela: procedimento próprio implementado e testado, sem aplicar produção. **32 testes novos** de política/sequência aprovados; regressões 21 API/web, 15 classificação, 6 preparador anterior e política do workflow aprovadas. Inventário read-only do novo código passou no host, incluindo 13 filas/outboxes, 12 tabelas de digests financeiros/mensagens e equivalência entre cofre no host/API. Preparação nativa ARM64 aprovou SDK somente adicional, API sintética, npm ci/build/Node idêntico, parada do loop geral atual/candidato, seis interpretadores legados e frontend, backup 110.898.909 bytes/restore/0088 em PostgreSQL isolado, cifragem da cópia protegida da chave, callback Evolution 503/recusa/400 e barreira Nginx 200/503. Configuração Nginx de fixture 0600 exigiu corrigir capabilities apenas do container de ensaio; repetição aprovada. Recibos/limites/imagens em release-plan.md. Containers descartáveis encerrados/removidos por identidade própria, sem afetar os 15 serviços ativos. Nenhuma migration operacional, configuração, parada de serviço ativo, merge ou cobrança executada. CI do commit operacional ainda pendente.

Após aprovação do proprietário, SSH autenticado e consultas read-only com transações `READ ONLY`, timeout de 10s e resultados minimizados. Host/checkout `clearbudget-vnic`/1f4483bd limpo, Alembic 0087, 15 serviços saudáveis, única porta Nginx loopback 8080, HTTPS healthz/api-health 200. IDs reais de imagens, runtimes e hashes/metadados dos seis arquivos Compose registrados em release-plan.md e evidência local ignorada. Probe booleano: `IntegrationCipher` válido na API em staging, indisponível no worker. Binding existente resolve para arquivo regular `600`, sem impressão de chave/conteúdo.

Um único cliente retornado pela consulta exata, nome conferente e tenant ativo do proprietário; UUIDs ficam fora do Git. Oito tabelas de filas consultadas: sem queued/processing no instante, com 68 notification_delivery `unknown` preservados; não é prova de ausência de outboxes/callbacks. Consulta de contagens financeiras sem escrita e sem copiar linhas de clientes. Nenhum build remoto, backup/restore de produção, criação/alteração de segredo, parada/restart, migration, merge ou pagamento executado.

Revisão documental proporcional: nenhum código funcional alterado ou refatoração elegível. OpenSpec da change com `--strict` e `git diff --check` aprovados; CI integral do código no SHA 47af72bd reconfirmado verde, sem repetir testes de aplicação por alteração exclusivamente documental. Novo bloqueio operacional detalhado: mecanismo protegido Orders e interrupção controlada ainda não implementados/ensaiados; não usar o executor InfinitePay com schema/overlay antigos nem ampliar allowlist do caminho API/web. Task 6.3 permanece aberta.


### Ensaios financeiros nativos e prioridade de segurança — 25/10/2026

Na imagem ARM64 candidata exata 4eb82fa5, PostgreSQL 17 temporário sem rede externa/portas e somente dados sintéticos: 56 testes Orders aprovados; quatro cenários de configuração pararam no setup legado `test_global_pix.clean_database` (`drop_all` com FKs use_alter sem nome no PostgreSQL). O primeiro ajuste do harness não foi aplicado pela coleta padrão do pytest; diagnóstico de collection confirmou a seleção. Repetição dos cinco testes de configuração com `--import-mode=importlib`, alias do módulo coletado e a fixture PostgreSQL já existente `test_unified_checkout.isolated_cart_database`: **5 aprovados**, 1 aviso, 9,85s. Um desses testes já integrava os 56 anteriores: **60 cenários únicos aprovados**, sem alterar assertions, código da aplicação ou imagem. A coleta verificou explicitamente a origem da fixture antes de executar. Logs protegidos no mesmo diretório dos recibos: native-orders-tests.log, native-settings-tests.log e native-settings-pg-importlib.log. Não ocultar os erros iniciais de setup nem atribuí-los ao fluxo financeiro. Databases descartáveis encerrados/removidos com saída 0; nenhuma comunicação financeira externa ou mensagem.

Triagem read-only atual: 50 alertas abertos GitHub (5 críticos/25 altos/19 médios/1 baixo); 41 referem-se a Pillow no manifest face_spike, todos com correção em 13.0.0; demais são Vite, @vitest/mocker e Undici em dependências de desenvolvimento. Runtime confirmado: API/worker geral/candidato Pillow13.0.0; **seis workers especializados Pillow12.3.0**, nas faixas dos alertas, sem declarar explorabilidade comprovada ou ausência de risco. Node candidato24.22.1 inclui Undici7.30.1; o alerta consultado refere-se ao ramo >=8.0.0/<8.12.2. Não resolver/fechar alertas manualmente nem chamar a imagem inteira de livre de vulnerabilidades.

O proprietário pediu explicação simples e depois decidiu explicitamente **corrigir primeiro os seis processos de fotos, antes de retomar a publicação do Mercado Pago**. Preparar essa dependência em worktree/change próprios; manter PR#283, imagens e backups Orders preservados, sem iniciar a janela. Corrigir essa biblioteca não autoriza trocar modelos/pesos, processar fotos reais ou reindexar acervo. A precedência foi escolhida pelo proprietário, não é abandono da integração. CI do commit53959492 (run40194974055) ainda executava backend na última consulta; demais checks concluídos verdes.

### Continuidade após priorização Pillow — 25/10/2026

CI do SHA operacional5395949276be25ad359aa30d37752cb10546536b confirmado verde no run40194974055: backend1661 aprovados/23 skips, jobs técnicos e gate agregado aprovados; jobs de publicação ignorados. A referência47af72bd acima permanece histórica, não o head atual do PR283.

Após decisão explícita do proprietário, correção Pillow em worktree/change próprios e PR258 reutilizado. Seis candidatos ARM6413.0.0 preparados dos IDs atuais; Python/demais pacotes/fontes/modelos iguais, pip check, JPEG/EXIF/normalização/proteção/thumbnails7MP, imports e sinais/restart em containers descartáveis aprovados.83 testes de mídia locais com13 e política de aplicação/recuperação aprovados. Barreira/restauração nginx ensaiadas offline, env Compose comparado sem imprimir valores;15 serviços ativos permanecem idênticos/saudáveis e schema0087. Nenhum serviço, dado, migration ou credencial ativa alterado.

PR258 aguarda CI da revisão final e revisão humana antes da publicação pontual. Task7.1 permanece aberta até prova efetiva dos seis ativos. Depois disso, renovar inventário/overlay/backup/recibo Orders e reconciliar explicitamente o pin13 na fonte; fingerprint anterior não autoriza novo runtime. PR283 e seu trabalho preservados. Nenhuma cobrança real autorizada.

Revisão humana da correção Pillow concluída: proprietário aprovou explicitamente PR258/head48fabf17 e publicação dos seis após CI verde. Run40203301396: Gemma offline, frontend, imagens nativas, gitleaks e OpenSpec aprovados; backend pendente no momento deste registro. Janela de manutenção aceita. Não há nova autorização de cobrança real; o piloto Orders permanece somente para o par proprietário/teste já definido.

### Dependência Pillow concluída — retomada Orders

PR258 integrado em main3d2ac6e7 após aprovação humana e CI verde de PR/main; run40206489337 backend1597 aprovados/20 skips e todos os gates. Publicação pontual autorizada concluída nos seis especializados em25/10/2026, novos containers iniciados15:45:48UTC (12:45:48São Paulo); todos Python3.13.16/Pillow13.0.0/healthy/unless-stopped, fontes/modelos/demais pacotes preservados. API/worker geral retomados nos mesmos IDs/imagens; sete não pausados preservaram StartedAt.15 saudáveis, schema0087, HTTPS200/200/200, digest financeiro idêntico e nenhum marker pendente. Alertas Pillow encerrados no GitHub;9 alertas nãoPillow fora do escopo.

O smoke imediato pós-reload retornou503 transitório: barreira rearmada corretamente. Sob o mesmo lock/recibo, versões/config/schema/digest reconferidos e restauração original repetida com espera limitada; observações [200,200,503]→[200,200,200], bytes nginx originais preservados. Nenhum rollback, SIGKILL, DDL, mudança de segredo ou fotografia real. Followup técnico/documental PR285 adiciona a espera a futuras operações; cópia de produção segue main3d2ac6e7 e o desvio está documentado na change Pillow.

Provas privadas: /var/lib/markina-gallery/deploy-state/pillow-prepare-20261025-01/published.json e post-release-runtime.json. Overlay persistente active.compose.json nessa pasta precisa entrar nos novos gates/Compose Orders. Task7.1 cumprida; retomar6.3 com novo inventário e fonte pin13 reconciliada explicitamente, sem reutilizar o fingerprint Orders anterior. O checkout ainda NÃO foi publicado.

### Revalidação do coordenador Orders após Pillow

Integração local de main3d2ac6e7 produziu snapshotcbb2362f. Conferido diff completo de backend/frontend/docker versus47af72bd: somente pin Pillow>=10.0→13.0.0. Coordenador mantém igualdade estrita com o novo snapshot, adiciona overlay persistente a CONFIGS/EXTRAS, exige published.json/fingerprint/IDs exatos e rejeita retorno de imagem ou ausência de overlay.36 testes do procedimento passaram, Ruff e OpenSpec strict passaram. Polling público limitado cobre503 transitório/persistente também no release/recuperação Orders.

Inventário real do coordenador renovado/read-only:15 saudáveis, schema0087, HTTPS200/200/200, sem pending marker, fonte da correção3d2ac6e7/receipt hash2ee7521fb07fc2d29a61a0a78ee7ee810c1b987db5a30e455a3c5f1f30e84249 e fingerprint63119d5cb9869685db32b288cf315756fbb9ac440b84f5c98e5d21be3d0076bc. Manifestos/overlay e imagens atuais conferidos; nenhum comando de aplicação Orders executado. Preparação/backup/restore e fingerprint de aplicação ainda precisam ser refeitos neste novo baseline.

### Nova preparação Orders concluída no baseline Pillow13

Headb89c352dc2a35a418728ee4dcd8d21b40a171670; nova pasta privada orders-prepare-ed5c1242020a45ce8772d68756a4c363, prepared.json/fingerprint74e83c2682aa2af92ac6bc0f3c8ec8794219a0eef148488a6987910baabcc000. API0b4d4fcd1f0a23f958c18db5d4dd661739dc027fdccd5c3692861c132bfd6aa8 e web360f1ca8d6422d4a61adade971acb849a0d73c95b0a25cc2d5cf05443d4b5f10, ARM64. Backup110.898.809bytes, cofre copiado0600 em0700 sem rotacionar, restore/0088/cifragem/financeiro aprovados em PG isolado. Sinais/restart/callback503 e Nginxguard aprovados;15 ativos saudáveis e schema0087 preservados.

Comparação explícita de todo /app/app e distribuições com a candidata4eb82fa5 anteriormente ensaiada em60 contratos Orders PostgreSQL nativos: idênticos bit a bit/versões. Somente manifest Pillow13 mudou. Mantém válida aquela evidência financeira de60 cenários; não é nova execução desses60. Nova imagem fez seu próprio startup/restore/migration em banco isolado. Prova privada prior-native-financial-tests-parity.json.36 testes locais do coordenador,21 API/web e15 classificação aprovados; Ruff/OpenSpec strict verdes. Task7.2 cumprida;6.3 aguarda CI40209291187, revisão/aprovação concreta, merge/CI main/recibo selado e login acompanhado. Nenhuma publicação Orders ou cobrança real executada.

### Autorização concreta Orders recebida

O proprietário aprovou explicitamente no chat integrar/publicar o PR283 após CI verde, aplicar a migration aditiva0088 e atualizar API/site/worker geral durante manutenção temporária, preservando os seis especializados corrigidos. Escopo do piloto: somente seu cliente/tenant verificado, credenciais de teste, cobranças reais bloqueadas. Backup/restore já ensaiados. Não pedir novamente autorização para esse mesmo escopo; continuar condicionado aos gates de CI/main/selagem e inventário. Head revisável b89c352d, CI40209291187 em execução. Não autoriza pagamentos reais, outros clientes, rotação de chave, modelo/engine ou publicação de outro projeto.

### Pré-checagem visual da sessão do proprietário

Chrome já tinha sessão administrativa autenticada em /admin/payments. Aplicado apenas filtro reversível pelo cadastro do proprietário; a UI confirmou exatamente um cliente no resultado. Nenhum pedido/status/entrega foi alterado. O histórico legado visível foi preservado; valores/nomes/IDs não foram copiados para artefatos versionados. Essa leitura não valida ainda a UI nova, pois o piloto Orders não foi publicado. Autenticação adicional para configuração sensível será feita pelo proprietário quando a interface exigir; não extrair cookies nem pedir OTP/senha pelo chat.
## Piso mínimo Mercado Pago — 25/10/2026

- Decisão do proprietário: mínimo uniforme de R$ 1,00 para novas tentativas Mercado Pago, sem configuração por fotógrafo; PIX manual do sistema permanece inalterado. A API oficial `GET /v1/payment_methods` informa `min_allowed_amount` por método/bandeira; a documentação Orders também lista esse endpoint. O Card Payment Brick valida o mínimo permitido para o método selecionado. Fontes: https://www.mercadopago.com.br/developers/pt/reference/online-payments/checkout-api-payments/payment-methods/get ; https://www.mercadopago.com.br/developers/en/docs/checkout-bricks/card-payment-brick/advanced-features/update-data?scope=prod ; https://www.mercadopago.com.br/developers/en/reference/online-payments/checkout-api/overview.
- Consulta HTTPS somente de leitura com Access Token exclusivamente de Teste, sem imprimir/carregar o token nos logs: cinco meios ativos de crédito retornaram mínimo R$ 0,50 (Mastercard, Visa, Elo, Amex e carteira de cartão). Nenhum pedido ou pagamento foi criado por essa consulta. Isso confirma o limiar da conta de Teste consultada, não a paridade com credenciais de Produção.
- Chrome na sessão autenticada do cliente de teste: tentativa preparada de R$ 0,05 encerrada sem chamada de pagamento; seleção preservada. O Brick exibiu erro genérico sem montar campos. Após selecionar 20 fotos de teste (R$ 1,00), a preparação foi aberta e o formulário oficial montou seus campos seguros. A evidência é consistente com o mínimo retornado (R$ 0,50), mas o Brick não expôs um código de erro causal. Nenhum formulário foi enviado, token de cartão gerado ou cobrança/pedido externo criado. A confirmação final do pagamento permanece em handoff ao proprietário.
- Implementação local: piso de 100 centavos validado em preparação e envio, antes de congelar seleção; consulta de limite por SDK oficial precede o congelamento e a criação Orders; valores inferiores preservam fotos; erro HTTP de validação é mostrado sem marcar tentativa como incerta. PIX manual não recebe esse bloqueio.
- Validação local inicial: `pytest tests/test_mercadopago_checkout.py -q` — 14 aprovados, 1 skip (concorrência depende de PostgreSQL); `npm test -- --run app/library/checkout/checkout.test.tsx app/library/cart/cart.test.tsx --reporter=dot` — 10 aprovados; `npx tsc --noEmit` aprovado; ESLint sem erros (4 avisos já existentes nas áreas de imagem/hook); `openspec validate add-mercadopago-orders-checkout --strict` aprovado. Ruff identificou import order nos testes, corrigido antes da repetição final.

## Cancelamento enquanto a Orders está processando — 25/10/2026

- Ajuste de UX e segurança financeira após observação do proprietário: cancelamento só fica disponível para estados internos `prepared`, `initiated` e `pending`, correspondentes a ordens ainda canceláveis. Depois de conciliar, o backend revalida o estado e não chama cancelamento do Mercado Pago para `processing`, `in_review` ou estado desconhecido.
- Em `processing`, o checkout informa: “Esta tentativa está em processamento. Aguarde o resultado; a seleção vinculada não pode ser cancelada ou editada agora.” O link de retorno ao carrinho continua, mas não altera o snapshot financeiro desta tentativa. Referência oficial de cancelamento Orders: https://www.mercadopago.com.br/developers/pt/reference/online-payments/checkout-api/cancel-order/post.
- Validação focada: backend `pytest tests/test_mercadopago_checkout.py -q` — 15 aprovados, 1 skip de concorrência PostgreSQL; frontend `npm test -- --run app/library/checkout/checkout.test.tsx app/library/cart/cart.test.tsx --reporter=dot` — 11 aprovados; `npx tsc --noEmit`, Ruff nos arquivos alterados e `openspec validate add-mercadopago-orders-checkout --strict` aprovados. Warnings emitidos pelo pytest são depreciações preexistentes e avisos SQLAlchemy da fixture SQLite.

## Compras simultâneas Orders com fotos disjuntas — 25/10/2026

- Causa corrigida: a tentativa ativa única por cliente no índice parcial, no serviço de preparação e no contrato da API impedia um segundo checkout mesmo quando o cliente havia selecionado fotos diferentes. Agora o índice permite uma tentativa ativa por revisão; sob lock do cliente, fotos incluídas em snapshots enviados permanecem reservadas e sobreposição é recusada antes de uma nova tentativa. Preparações locais não enviadas podem ser substituídas ao editar.
- API `/library/mercadopago/active` lista as tentativas do próprio cliente. O carrinho exibe cada compra enviada com seu estado/valor e link de acompanhamento; `/library/checkout` retoma a tentativa da revisão atual e prepara um pedido próprio para uma seleção disjunta. Uma aprovação tardia altera somente os pedidos e itens do snapshot original. Consultas de exibição não bloqueiam linhas de SaleOrder.
- Schema: migration aditiva `20261025_0089` substitui a unicidade global pelo índice parcial `(tenant_id, client_id, cart_revision)`. Downgrade recusa quando há múltiplas tentativas ativas, para não perder representação financeira. `alembic heads` aponta `20261025_0089`; migration exercitada em SQLite descartável. Não aplicada a nenhum ambiente operacional.
- Backend: `pytest tests/test_mercadopago_checkout.py tests/test_mercadopago_schema.py -q` — 20 aprovados, 2 ignorados por dependerem de PostgreSQL; repetição direcionada após o ajuste final do payload — 3 aprovados (proteção contra sobreposição, duas tentativas disjuntas com aprovação tardia e retomada após carrinho vazio). O teste de API confirma as duas tentativas na resposta ativa. Os skips PostgreSQL permanecem cobertos pelo gate de CI.
- Frontend: checkout/carrinho — 13 aprovados; `npx tsc --noEmit` e build Next passaram. `npm run lint` passou sem erros (36 avisos preexistentes de `<img>`, hooks e mocks); ESLint focalizado também sem erros. Ruff nos arquivos Python alterados, `git diff --check` e `openspec validate add-mercadopago-orders-checkout --type change --strict --no-interactive` passaram. Não houve teste visual autenticado nesta alteração, chamada financeira real, deploy ou migration operacional.
- Preparação de release exclusivamente 0088 registrada anteriormente ficou supersedida: qualquer release futuro deve reconstruir candidato e repetir os gates operacionais incluindo 0089. Esta alteração local ainda precisa passar pelo CI da revisão antes de merge.
