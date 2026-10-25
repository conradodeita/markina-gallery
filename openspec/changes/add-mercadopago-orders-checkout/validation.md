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
