# Plano de publicação e ensaio restrito — Mercado Pago Orders

## Estado e autorização

**Diretriz/autorização mais recente — 25/10/2026:** o proprietário determinou validação proporcional ao piloto Mercado Pago sandbox restrito ao seu próprio cliente, com acompanhamento manual. Baterias rígidas adicionais e testes opcionais não condicionam este deploy; reaproveitar evidências válidas e manter apenas CI aplicável, preservação/recuperação da migration e smoke. Evitar sucessivos pushes sem publicação, especialmente para testes opcionais ou documentação. Merge e deploy estão explicitamente autorizados durante sua ausência; conferir e apresentar inventário, portas/serviços e recuperação antes de aplicar, sem pedir outra confirmação do mesmo escopo. Verificar CI pendente a cada 30 minutos e continuar até publicação/verificação final. Essa autorização substitui os pedidos históricos de novo aceite neste plano; não abrange cobranças reais, liberação geral nem alterações em outros projetos.

Preparação solicitada em 24/10/2026: revisão, commit/PR e plano operacional. O proprietário informou que não possui homologação privada e escolheu fazer o aceite final na instalação de produção, com seu administrador e seu próprio cliente, **exclusivamente com credenciais de Teste**. Reforçou que cada fotógrafo configura sua própria conta pela UI. Esta decisão substitui a previsão de homologação privada como destino do aceite; não substitui o inventário e a autorização concreta de publicação/migration exigidos pelo AGENTS.md.

**Piloto atualizado e verificado em `f9091a7b`/0089 em 26/10/2026 02:02 UTC.** As nove tentativas foram preservadas; PIX segue disponível e Mercado Pago permanece sandbox, restrito ao mesmo par proprietário, com cobranças reais bloqueadas. CI exato da main `40251917299` aprovado, backup final recuperado e 15 serviços saudáveis após aplicação. Ver a seção final de publicação concluída. As tabelas e seções abaixo de 0087/0088 são evidências históricas; não executar novamente esses procedimentos como se a publicação estivesse pendente.

**Atualização de escopo em 25/10/2026:** a correção de compras simultâneas adiciona migration 0089, que substitui o índice de tentativa ativa por cliente por unicidade da revisão ativa. O recibo anterior comprova a publicação inicial e deve ser preservado; não serve como preparação do novo release. Antes de aplicar 0089 é necessário reconstruir o candidato, ensaiar o backup atual preservando os registros Orders e apresentar os novos inventário/fingerprint/recibo para aprovação.

## Escopo candidato

### Baseline integrado após PR #286

- Código funcional a preparar: `main` em `b69a95c526912d725863a57a13f8735a62f671ed`, CI pós-merge `40229694785` verde; nenhum job de deploy/release foi executado. A versão preserva o PIX e permite tentativas Orders distintas para seleções disjuntas.
- Instalação observada anteriormente: checkout `1f4483bd`, schema `20261022_0087`, API/Web/worker geral anteriores e seis imagens especializadas com Pillow 13. Isso é somente o inventário histórico de 25/10; exige confirmação live antes de preparar.
- O script anterior, recibos, backup e restauração pararam em `20261024_0088` e não são válidos para o candidato atual. A cadeia necessária é `20261022_0087 → 20261024_0088 → 20261025_0089`.
- A preparação local atualiza `scripts/orders_pilot_release.py` para alvo 0089 e runtime integrado acima. Antes de usar o modo `inventory` ou `prepare` no host, validar esse diff, testes, OpenSpec e CI; isso não autoriza `apply`.

| Item | Alvo a revisar | Estado |
|---|---|---|
| Repositório | `conradodeita/markina-gallery`; `main` | candidato integrado `b69a95c526912d725863a57a13f8735a62f671ed`; atualizar candidato e CI antes da preparação |
| Instalação esperada | host `clearbudget-vnic`, checkout `/opt/markina-gallery` | referência histórica; inventário live pendente |
| Projeto/Compose | `-p markina-gallery -f docker/docker-compose.yml`, mantendo todos os overlays operacionais atuais | overlays e hashes efetivos pendentes de inventário |
| Origem e porta esperadas | `https://markina.pickyourpic.com.br`, Nginx `127.0.0.1:8080 → 80/tcp` | conferir sem criar portas/subdomínios/DNS/certificados |
| Schema | baseline `20261022_0087`; aplicar cadeia Alembic até `20261025_0089` (0088 + 0089) | procedimento e preparação atuais ainda esperam 0088; substituir antes de inventariar/preparar |
| Aplicações afetadas | API, web e worker geral/financeiro; imagem de migrate compatível | construir e fixar IDs/digests por serviço antes da janela |
| Cofre | binding genérico existente da API entregue também a `worker` | arquivo/owner/permissões/ambiente/backup precisam de prova no alvo |
| Emissão real | `MERCADOPAGO_ALLOW_LIVE_PAYMENTS=false` | condição obrigatória de todo este ensaio |
| Emissão simulada | `MERCADOPAGO_TEST_CUSTOMERS` com somente UUID do tenant e UUID do cliente do proprietário | identificadores atuais ainda não coletados; não usar telefone como autorização |

Os demais fotógrafos continuam configurando aplicação, Public Key, Access Token e assinatura próprios em Configurações → Meios de pagamento, sob senha/OTP. Não existe token global de recebedor no servidor. A lista operacional controla somente quem pode emitir com conta de teste; não substitui a configuração individual nem concede acesso a outro tenant.

## Inventário anterior à solicitação de publicação

1. Identificar checkout, SHA de main/alvo e runtime real de **cada serviço**; worker legado pode estar em outra imagem. Registrar IDs/digests, saúde, comandos, labels Compose, dependências, schema/Alembic e espaço disponível. Não inferir runtime por tag, nome de container ou estado do checkout.
2. Inventariar todos os escritores/filas do projeto e jobs em execução, estados ambíguos e notificações em trânsito. Provar drenagem/interrupção/retomada sem duplicar mensagem ou perder callback. Não utilizar a política de manutenção de outra change ainda não publicada.
3. Conferir domínio/porta/overlays reais, isolamento de outros projetos e metadata dos bindings, sem imprimir conteúdo de env/config resolvida. Conferir presença e compatibilidade do cofre em API e worker; preservar `APP_ENV` e o ambiente de AAD existentes, mesmo que o nome legado seja `staging`. Trocar esse rótulo poderia invalidar credenciais cifradas.
4. Identificar os UUIDs de tenant, administrador e cliente do proprietário com autenticação, sem divulgar listas de clientes. Confirmar galeria restrita somente a esse cliente e fotos sintéticas ou de teste já autorizadas, sem ingestão biométrica. Inventariar parâmetros atuais de PIX para comprovar preservação.
5. Registrar contagens e digests minimizados do histórico financeiro/IDs anteriores e filas relevantes. Não copiar dados de clientes para relatórios públicos. Preparar backup lógico consistente e metadados de cofre; testar restauração em ambiente descartável sem canais externos. Preservar a chave mestra e o backup sob controle do proprietário.
6. Vincular inventário a SHA/schema/digests/configuração, horário de São Paulo e fingerprint. Apresentar esse resultado, escopo da eventual pausa, serviços/portas e rollback ao proprietário **antes de solicitar autorização operacional**.

### Restrição dos fluxos de release atuais

Este candidato modifica migration, dependência, worker e Compose: o classificador existente o trata como `protected`. Abrir PR não publica; não habilitar automerge. Os fluxos API/web/facial não autorizam este delta. O fluxo de aposentadoria InfinitePay tem contratos, schema e hashes próprios e também não pode ser reutilizado para Orders.

Preparar uma operação de release específica e revisável, com gates e testes para este escopo, antes da publicação. Não relaxar allowlists, alterar fingerprints antigos ou usar um script genérico para contornar o bloqueio. O plano não declara esse mecanismo implementado nem substitui seu ensaio. A necessidade está registrada como gate operacional, separado da funcionalidade testada em desenvolvimento.

## Avisos de dependências antes da publicação

Consulta GitHub read-only em 24/10/2026 retornou 50 alertas abertos na main (5 críticos, 25 altos, 19 médios, 1 baixo). Não são uma avaliação completa deste candidato e não foram corrigidos nesta integração. Antes da publicação, identificar aplicabilidade/exposição e responsável pelas pendências relevantes ao runtime selecionado; não tratar a mera passagem do CI ou ausência de alerta de um pacote como prova de segurança. A evidência distingue a resposta atual da observação histórica de fonte desabilitada.

## Sequência proposta após revisão e autorização concreta

1. Conferir CI integral do SHA candidato e compatibilidade do SHA integrado; fixar imagens de API/web/worker/migrate e preservar as referências saudáveis anteriores. Construir antes da janela; não alterar imagens/containers/volumes de terceiros.
2. Sob o lock exclusivo de release já previsto no projeto, renovar inventário e recusar divergência. Iniciar a barreira específica e drenar/interromper somente os escritores Markina inventariados. Responder de modo recuperável a novas ações durante a pausa e manter a prova das operações em curso. Não executar `compose down`, prune ou reset.
3. Aplicar a cadeia 0088→0089 partindo de 0087 somente após backup/restore e ensaio isolado da mesma cadeia, com interrupção dos escritores verificada. Não carimbar schema nem fazer downgrade para contornar divergência. Subir os binários compatíveis e retomar filas; conferir schema 0089, hashes carregados, saúde e logs sem dados sensíveis.
4. Habilitar no servidor apenas o par tenant/cliente do proprietário. Manter cobrança real bloqueada e PIX atual habilitado. Não criar lista de clientes no frontend. Confirmar por API autenticada que um cliente não permitido não recebe o método e não consegue preparar/enviar por acesso direto.
5. O proprietário acompanha o login administrativo e conclui senha/TOTP/OTP quando solicitados. Configurar **sua** aplicação com credenciais Teste pela UI segura, sem enviá-las ao chat ou ao Git. Verificar identidade MLB/test_user, conta, flags e URL de webhook pertencentes ao mesmo tenant.
6. Registrar no ambiente **Teste** do Mercado Pago a URL HTTPS completa retornada nessa instalação, evento `order`. Substituir o túnel encerrado: a versão de conta local anterior não deve ser reaproveitada no servidor. Não editar o ambiente Produção do provedor nem registrar token/assinatura em documentação.
7. Executar a matriz abaixo com o cliente do proprietário, conferindo API, banco e painéis. Nenhum outro cliente deve comprar com essa conta de teste. Mensagens de autenticação/compra do ensaio devem se restringir ao proprietário; não disparar ações em massa.
8. Fechar o ensaio: conciliar todas as tentativas; cancelar somente o que o provedor aceitar e manter resultados pendentes verdadeiros. Desabilitar novas emissões de teste/retirar o par quando apropriado, preservando conciliação, webhook e histórico. Não apagar pedidos para “limpar” a validação. Liberação ampla com credenciais reais é outra decisão explícita.

## Matriz de aceite na instalação

| Cenário | Evidência necessária |
|---|---|
| Configuração por fotógrafo | sessão/tenant próprios, flags, cofre disponível, senha/OTP, outro fotógrafo não lê/usa credenciais |
| Restrição do ensaio | proprietário disponível; outro cliente sem CTA e prepare/submit negados; PIX manual intacto |
| Cartão APRO/FUND/CONT de teste | `live_mode=false`, Orders/GET e banco coerentes; somente um POST por tentativa |
| Pix Mercado Pago de teste | QR/cópia, pendência e cancelamento comprovados; simulador de aprovação se aplicável |
| Carrinho | retorno, remover/adicionar fotos, nova revisão, falha e resposta perdida sem reaproveitar cobrança antiga |
| Webhook/worker | callback genuíno HMAC com ACK/inbox; worker processa sem navegador; retry/duplicidade preservados |
| Histórico/painel/CSV | marca TESTE visível, estados corretos, simulações fora da receita/vendas reais e CSV padrão; detalhes preservados no CSV detalhado |
| Reembolso de teste | parcial/integral confirmados por API; entrega interna suspensa; nenhum refund real |
| Regressões operacionais | health/HTTPS, PIX atual, autenticação, filas, privacidade, outros projetos e histórico anterior preservados |

Chargeback/expiração e aprovações tardias que dependam de tempo/evento não disponível no provedor continuam cobertos pelos contratos locais; não forjar sucesso operacional nem transformar isso em cobrança real. O ensaio no domínio operacional com conta de teste não comprova liquidação produtiva nem certificação oficial.

## Recuperação e rollback

- Antes de schema/qualquer tentativa: preservar o estado anterior e interromper a operação se inventário, backup, filas ou gate divergirem.
- Depois da cadeia 0088→0089: manter schema/evidência; não restaurar dump antigo sobre novas operações e não executar downgrade destrutivo. A migration 0089 recusa perda de representação financeira.
- Depois da primeira tentativa Orders: um binário anterior sem Orders pode classificar esses pedidos incorretamente. **Não voltar automaticamente para 0087.** Recuperação precisa de versão compatível com schema 0089 e os novos registros, ou correção para frente, previamente ensaiada e aprovada.
- Se for necessário retirar disponibilidade, fechar somente novas emissões e manter receiver/worker/consulta compatíveis para as tentativas existentes. Dados de teste permanecem identificados e não geram receita real.
- Sem prova de compatibilidade de recuperação e sem operação de release específica testada, publicação permanece bloqueada. Este documento prepara a revisão; não alega impacto zero já comprovado no host.

## Inventário live anterior — 25/10/2026 (histórico, não usar como atual)

O proprietário respondeu “Aprovado” ao encaminhamento de inventário e preparação. Esse encaminhamento foi executado por SSH autenticado, exclusivamente com consultas de leitura, entre **03:39 e 03:45 de São Paulo**. A aprovação foi registrada; não executa por si só um procedimento ainda inexistente nem comprova seus gates.

| Verificação | Evidência atual |
|---|---|
| Host/raiz | `clearbudget-vnic`, `/opt/markina-gallery`; checkout limpo |
| Checkout/API ativos | `1f4483bd620071a15ccfc6bc1f2b7e2a3fd0cea8`; APP_VERSION da API confere |
| Main/candidato | main `cef5bdf82e254ec908d238aa3a5d09f1069e3cfd`; PR #283 aberto/draft, candidato `47af72bdf503295e93b1ee8e68bef97da2d9d947`, CI integral verde reconfirmado |
| Schema | `20261022_0087`; tabelas Orders ainda ausentes; alvo aditivo `20261024_0088` |
| Saúde | 15 serviços ativos/saudáveis; migrate antigo encerrado, sem tratá-lo como serviço ativo saudável; sem marcadores de release pendente |
| Porta/origem | somente Nginx `127.0.0.1:8080`; `/healthz` e `/api/health` HTTPS 200 |
| Disco | 57 GiB disponíveis, 71% ocupado; capacidade de build/backup precisa ser reavaliada na janela |
| Runtime API/worker/web | Python 3.13.17 em API e worker geral; Node v24.22.1 no web; imagens distintas registradas abaixo |
| Workers especializados | imagens preservadas, Python 3.13.16; não presumir a mesma capacidade de parada graciosa do worker geral |
| Cofre | API configurada e `IntegrationCipher` válido, ambiente `staging` coerente; worker geral sem configuração e com validação recusada, conforme a lacuna que o Compose candidato corrige |
| Binding | `docker/.env.integration-secrets` é symlink para `/var/lib/markina-gallery/deploy-state/integration-secrets.env`; alvo regular, UID/GID 1001, permissão `600`; não imprimir conteúdo nem substituir a chave |
| Cliente do ensaio | consulta exata dos dados fornecidos retornou um único cadastro, nome conferente, tenant ativo pertencente ao proprietário; UUIDs guardados somente em evidência local ignorada, sem reproduzir dados pessoais neste documento |
| PIX/histórico | 64 sale_order, 64 payment_group, 12 provider_payment e uma configuração PIX ativa; consulta de contagem, sem alterar registros; ainda não é digest de preservação nem backup |

Imagens ativas conferidas por ID real, não por tag:

- API: `sha256:c2f16d9d94903b0dd0da8f75b6b3cbbee635b0b162d904cc027a241e8d8b8175`.
- Worker geral: `sha256:24547390f9072815d7fa56479c27da22ee7b4a3fdf75709830c480ac6975a583`.
- Web: `sha256:13ba2e7232cf367f057b214fe765512c7330089a4ce760dbe0713451390e6de4`.

Base Compose mais cinco overlays observados: branding, raw-development, preview-adjustment, system-monitor e o segundo binding system-monitor em deploy-state. Nenhum overlay ativo de imagens 0086 foi observado nas labels atuais; não reutilizar a exigência específica desse overlay do executor antigo. Metadados completos/minimizados e IDs dos demais serviços ficam em `.codex-tmp/mp-production-readonly-inventory-20261025.json`, ignorado pelo Git. SHA-256 do conteúdo canônico capturado: `2becf639755e49fefe7cacaf261953ce5a59b9b8074ffedf17a1303c35bd997b`. Este hash identifica **a captura**, não uma aprovação de release nem um fingerprint operacional completo.

As consultas de filas não encontraram `queued`/`processing` nas oito tabelas verificadas (`media_job`, `whatsapp_delivery`, `email_delivery`, `notification_delivery`, `gallery_lifecycle_operation`, `asset_file_cleanup`, `facial_job`, `raw_development_job`). **Há 68 notification_delivery em `unknown`**, além de falhas históricas. Não reclassificar esses registros como concluídos, não reenviar, apagar ou resolver automaticamente. A captura não prova ausência de callbacks externos em trânsito, outboxes elegíveis ou trabalho que surgiu depois; a barreira operacional ainda precisa ser ensaiada e reconferida sob lock.

### Decisão operacional e aceite da janela

Após receber o inventário acima, o proprietário respondeu **“Sim, aceito”** à pergunta explícita sobre janela de manutenção com indisponibilidade temporária do Pick-your-Pic, preservando os outros projetos. Essa decisão permite concluir a implementação/ensaio do procedimento próprio descrito abaixo. Não solicitar novamente a mesma decisão sobre a janela; os gates técnicos continuam obrigatórios.

O inventário confirma que o novo checkout pode usar a cadeia de schema esperada e o cofre existente, mas **não torna os executores atuais compatíveis com este release**. O caminho de API/web exclui migrations/worker/dependência; o executor InfinitePay aceita schema 0086 e overlay/hashes próprios que divergem do host atual. Não alterar essas exigências para fazer Orders passar.

A próxima unidade operacional deve especificar e ensaiar um procedimento próprio, sob o lock compartilhado, com estes contratos revisáveis:

1. Candidato imutável e CI verde após integração; inventário renovado vinculado a SHA, schema, imagens, overlays, cofre e portas. Construir/fixar somente API/web/worker/migrate antes da interrupção, avaliando mudanças de dependências resolvidas; não reconstruir os seis workers especializados.
2. Janela explícita de indisponibilidade da API/checkout do Pick-your-Pic durante a migration. Drenagem e parada **verificadas** da API, do worker geral e dos seis workers especializados que escrevem no mesmo banco, mantendo as imagens/configurações especializadas. Não usar SIGKILL ou pressupor que workers legados tratam SIGTERM. Provar recuperação de falha na parada e continuidade de filas/callbacks, preservando os 68 resultados desconhecidos. Evolution, bancos, Redis, proxy e outros projetos não entram na parada.
3. Backup consistente, restauração ensaiada em destino descartável sem canais externos e recuperação do cofre comprovada antes de 0088. Um backup de banco sem a chave existente não é prova de recuperação das credenciais.
4. Migration exclusivamente 0087→0088; novos binários compatíveis; binding existente também no worker; `APP_ENV=staging` preservado, cobrança real bloqueada e lista de teste com o único par verificado. Reconferir isolamento, PIX, histórico financeiro, HTTPS e workers sem usar credenciais reais do Mercado Pago.
5. Antes da primeira tentativa Orders, ensaiar a recuperação compatível com 0088. Depois de envio, falha não permite downgrade/restauração do banco antigo; fechamento de novas emissões deve manter reconciliação e webhook dos registros existentes. Retomar workers especializados pelas imagens anteriores e comprovar saúde.

Estado ao apresentar o inventário: procedimento ainda não implementado/testado. A janela foi aceita posteriormente, conforme o registro acima. A implementação e seus ensaios estão descritos a seguir; não executar o roteiro antigo nem declarar publicação concluída a partir do aceite da janela.

## Procedimento pontual e ensaios de preparação — alvo 0088 (histórico/supersedido)

`scripts/orders_pilot_release.py` não altera os gates antigos e não adiciona deploy automático. O procedimento foi implementado e testado para 0087→0088, com inventário que cobre 13 filas/outboxes, digests minimizados de 12 tabelas financeiras/de mensagens, identidade dos serviços e comparação entre o arquivo do cofre e a configuração efetivamente carregada pela API, sem imprimir valores. A distinção `external_status` da outbox de membros foi corrigida. Nenhum trabalho queued/pending/processing foi encontrado naquele inventário; unknown não é elegível à drenagem/reenvio. **Esse procedimento/recibo não serve para 0089 até atualização e novo ensaio.**

Preparação nativa ARM64, usando exclusivamente fontes de runtime do SHA `47af72bdf503295e93b1ee8e68bef97da2d9d947`, já aprovado no CI:

- API candidata `sha256:4eb82fa5d305f3920854a000341279f6545f399203159a0beae320265a3bf9c7`. Mesma imagem base, mesma versão Python e todas as distribuições anteriores idênticas, acrescentando somente `mercadopago==3.6.0`; pip check e inicialização sintética da API aprovados sem rede externa.
- Web candidato `sha256:4115c9670bad7ff49fffcab880885c39c5da687f6c9041e9b5ca08e7586c5d3d`. Compilado em container limitado a 2 GiB/1 CPU, com Node ativo e npm ci/lockfile; versão Node comparada e preservada. Nenhuma tag dos serviços ativos foi substituída.
- Parada exercitada em containers descartáveis, sem filas, sem rede externa e sem carregar modelos: SIGTERM/saída 0 do loop real do worker atual e candidato; SIGINT/saída 130 nos seis interpretadores das imagens especializadas atuais. Frontend candidato iniciado, health 200 e SIGTERM confirmado. Os seis workers reais usam `unless-stopped`: ensaio adicional comprovou suspender/restaurar exatamente essa política em containers descartáveis antes/depois da parada. Nenhuma política dos containers ativos foi alterada nesta preparação. Containers de ensaio encerrados/removidos exclusivamente por identidade/label próprias, sem SIGKILL.
- Backup customizado de **110.898.909 bytes**, arquivo e cópia de recuperação do cofre em modo 0600, diretório 0700 no mesmo host. Restauração executada em PostgreSQL temporário sem portas ou saída externa; migration 0087→0088 aplicada apenas nessa cópia. Digests financeiros/PIX e mensagens preservados e cifragem validada com a cópia protegida da chave. PostgreSQL de ensaio encerrado/removido; backup e recibos preservados para a publicação.
- Callback Evolution exercitado isoladamente na imagem efetiva `sha256:5cf854f2eb3af149ed87841c2c882d8eecff68d278aa87e765e88f7541a36409`, extraindo apenas o método já instalado, sem iniciar a aplicação/conectar instância/contatos. Servidor loopback sintético retornou 503 e conexão recusada antes da recuperação: retentativa confirmou um único recibo. HTTP 400 não foi reenviado. Método SHA-256 `6f71b669adaecc765e62d89634cda43fbf26bc4a6d30c0a50e0bbb2a573c978a`. O container Evolution real não foi alterado/reiniciado, nem houve envio de mensagem.

Recibos privados em `/var/lib/markina-gallery/deploy-state/orders-prepare-219bc85d9f5d40d0bcfcb3b9150a83d6/`: `prepared.json`, `prepared-tested.json`, `prepared-validated.json` e `prepared-reviewed.json`. O último incorpora callbacks, StartedAt, barreira Nginx, parada do web e suspensão/restauração de restart policy; baseline/inventário foram renovados com esses metadados. Não copiar esses arquivos ao Git: contêm o par UUID operacional. Logs locais minimizados ficam sob `.codex-tmp/`, ignorados. O fingerprint deste recibo é de **preparação**, não prova de publicação.

Barreira Nginx testada na imagem ativa, em namespace sem rede externa/portas, com health 200 e ações administrativas/checkout 503. O primeiro ensaio isolado detectou que root sem DAC_OVERRIDE não lia o arquivo de fixture 0600 pertencente ao operador; corrigido somente o conjunto de capabilities do container descartável, sem alterar permissões dos arquivos ou do Nginx real. Novo ensaio passou; logs sintéticos de diagnóstico preservados no diretório protegido.

### Uso e limites do executor

1. `inventory`: consultas read-only; baseline fixado em `1f4483bd`, schema 0087, 15 serviços saudáveis, porta/origem atuais e cofre válido. Não faz fetch no checkout ativo.
2. `prepare --sha <SHA> --pair <arquivo-0600>`: artefatos isolados, clone próprio, fontes Git sem links/traversal, imagens imutáveis, ensaios de sinais/callbacks e backup/restore. Não substitui serviços/configuração operacional.
3. `seal --receipt <recibo> --sha <merge-main>`: depois de CI integral da main, confere que backend/frontend/docker inteiros continuam idênticos ao runtime preparado; vincula os mesmos binários ao merge, sem rebuild. Recusa runtime diferente e produz `prepared-main.json` e fingerprint novos para a aplicação.
4. `apply --receipt <recibo-main> --approval-fingerprint <fingerprint> --allow-legacy-interruption`: verifica CI público da main, imagens, backup, dono/tenant, inventário atual e lock. Ativa barreira 503 no Nginx exclusivo, finaliza requests da API, para API/worker/web e os seis escritores especializados sem SIGKILL e confirma ausência de transações ativas. Journal durável registra cada pedido de sinal antes do envio; políticas `unless-stopped` são suspensas somente nos containers pausados e restauradas na retomada. Cria **outro backup atualizado** sob a barreira e repete restore/migration/validação financeira nessa cópia antes da migration real. Orçamento de comandos da manutenção: 300s; falha antes de DDL recupera os mesmos containers/checkout, sem confundir processo ainda terminando com recuperação saudável. Não alterar o proxy compartilhado, DNS, portas ou outros projetos.
5. Depois de 0088, confere digests antes de iniciar escritores, sobe somente API/web/worker pelas imagens preparadas, valida cofre/API/worker e gates de emissão, retoma os mesmos seis containers especializados e comprova que DB/Redis/Nginx/Evolution não foram reiniciados. Abre o ingresso após saúde e restaura a configuração Nginx original.
6. `resume --receipt <recibo-main> --approval-fingerprint <fingerprint>`: recuperação específica depois de DDL, apenas com schema 0088 e o mesmo candidato. Fecha a lista de testes, mantém cobrança real bloqueada e receiver/conciliação, não executa migration/downgrade/restore de dados e não volta a 0087. Falha mantém marcador/evidência para diagnóstico.
7. `recover --receipt <recibo-main> --approval-fingerprint <fingerprint>`: após interrupção abrupta do executor antes de DDL, confere journal/schema 0087 e retoma os mesmos containers anteriores, sem consulta externa de CI. Recusa 0088. A recuperação de um legado ainda ativo continua exigindo ociosidade/filas quiescentes; nunca forçar SIGKILL.

O retry Evolution observado é em memória e limitado; não é uma inbox durável e não comprova entrega se o provedor reiniciar ou uma indisponibilidade exceder todas as retentativas. O procedimento não reinicia esse serviço e verifica seu StartedAt; deve manter a janela dentro do orçamento ensaiado. Não declarar garantia absoluta de callbacks nem substituir `unknown` por sucesso. Mercado Pago recebe 503/sem ACK durante a barreira e suas notificações continuam dependendo do receiver assinado e da conciliação oficial; antes desta primeira migration não há tabelas/tentativas Orders no destino.

### Validação local do procedimento

32 testes de política/sequência aprovados, incluindo falhas antes/depois de DDL, timeout sem SIGKILL, inventário/CI divergente, alteração de runtime na integração, fechamento de emissão na recuperação, recusa de 0087 após DDL, recuperação de conexão interrompida, processo ainda terminando, legado ocupado, restart policy alterada/restaurada, SQL read-only e sanitização de erros. Regressões dos gates preservados: 21 API/web, 15 classificação, 6 preparação anterior e política de workflow aprovadas. Ruff e validação OpenSpec da change aprovados. Ainda validar no CI o novo commit operacional, revisar diff e reconciliar o recibo com o SHA integrado antes de qualquer aplicação.

## Continuidade após preparação 0088 (histórica)

Concluídos nesta retomada: CI atual reconfirmado, inventário SSH read-only, schema, topologia, imagens, identificação exata do cliente/tenant, validação booleana do cofre e consultas minimizadas de filas/contagens. Não houve merge/deploy/migration, backup de dados operacionais, mudança de segredo/configuração, parada/restart de container ou cobrança.

Pendentes antes da execução: fechamento da revisão/CI do mecanismo, vinculação do recibo à main integrada, inventário/fingerprint renovados e autorização da operação concreta, seguida do login acompanhado. A janela já foi aceita, o procedimento/backup/recuperação foram ensaiados e os UUIDs estão conferidos; não pedir novamente dados pessoais. Não sincronizar specs principais nem arquivar esta change como publicada antes de evidência e aceite.

## Reconciliação de25/10/2026 após Pillow

- Produção: checkout/API1f4483bd, schema0087,15 saudáveis, HTTPS200/200/200. Seis especializados agora usam os IDs Pillow13 aprovados e o overlay persistente de pillow-prepare-20261025-01/active.compose.json. Preservar esse overlay em todos os comandos; novo preflight exige published.json e IDs, não apenas um pin.
- Fonte: main3d2ac6e7 integrado na branch Orders, snapshotcbb2362f; única diferença de backend/frontend/docker versus47af72bd é pin13. O gate permanece congelado. Head do coordenador b89c352d/PR283, CI40209291187 em andamento; não é autorização de aplicação.
- Nova preparação privada: `/var/lib/markina-gallery/deploy-state/orders-prepare-ed5c1242020a45ce8772d68756a4c363/prepared.json`, fingerprint74e83c2682aa2af92ac6bc0f3c8ec8794219a0eef148488a6987910baabcc000. API0b4d4fcd1f0a23f958c18db5d4dd661739dc027fdccd5c3692861c132bfd6aa8; web360f1ca8d6422d4a61adade971acb849a0d73c95b0a25cc2d5cf05443d4b5f10. Candidatos ARM64, SDK somente adicional, código completo da aplicação e distribuições idênticos à candidata financeira anterior validada em60 contratos nativos PostgreSQL; apenas manifest corrigido. Não repetir esses60 como nova execução.
- Backup110.898.809bytes e cópia protegida do cofre, restore/migration0088/cifragem ensaiados em PostgreSQL isolado; shutdown/restart/callback503 e barreira aprovados. Schema de produção permaneceu0087. Nenhum segredo/UUID real é incluído no Git.
- Após CI/revisão: integrar main, seal com equivalência estrita de runtimes, revalidar inventário e aprovação concreta da operação Orders. Nova janela pausa os mesmos seis corrigidos, substitui somente API/web/worker geral, aplica somente0088 com backup final restaurado em ensaio e retoma os mesmos seis IDs. PIX preservado; conta real bloqueada e teste limitado ao par autenticado do proprietário. Cofre existente entregue ao worker sem rotação.
- **Supersedido por PR #286:** os pontos acima descrevem a preparação antiga 0088 e não autorizam nem devem ser usados para a nova execução. O script atualizado não foi ainda validado/CI e não foi executado remotamente. Para a próxima etapa: fechar task 10.1 com testes e CI, então usar inventário read-only na versão compatível, revalidar os gates e preparar novo recibo/backup/restore `0087→0089`. Parar antes de DDL/deploy e apresentar inventário, portas, escopo de manutenção e impacto zero para uma autorização específica da migração/publicação.
- Saúde pública após nginx reload usa polling limitado15s;503 persistente mantém bloqueio. Não remover journal por uma leitura de sucesso no frontend nem usar saúde HTTP como prova financeira.

## Repreparação operacional — cadeia 0087→0089

- O procedimento local foi atualizado para `TARGET_SCHEMA=20261025_0089`, preservando `SCHEMA=20261022_0087` como baseline e fixando `APPROVED_RUNTIME=b69a95c526912d725863a57a13f8735a62f671ed`, commit integrado do PR #286. O `alembic upgrade 20261025_0089` aplica a cadeia 0088→0089 a partir de 0087.
- Validação local da atualização: 37 testes sintéticos de `scripts/test_orders_pilot_release.py` aprovados; OpenSpec estrito válido; `git diff --check` aprovado. Nenhum comando de inventário, preparação, backup, migration, deploy ou cobrança foi executado no host nesta etapa. A alteração operacional ainda precisa de revisão/CI.
- Depois do CI verde e integração desta atualização, o próximo passo técnico é executar somente `inventory` read-only e recusar qualquer diferença frente ao baseline. Só então preparar imagens/backup e ensaiar restauração e migração até 0089 em banco isolado. A preparação não autoriza `apply`; antes da janela, apresentar inventário atual, serviços/portas, escopo de manutenção e plano de recuperação para autorização específica.

### Gate do SSH restrito

- O forced-command root-owned instalado em `/usr/local/sbin/markina-gallery-preflight-ssh-wrapper` não reconhece `MARKINA_ORDERS_TARGET_SHA`; aceita somente os comandos facial, API/web, rollback e InfinitePay. Portanto, ainda não há canal autorizado para executar o helper Orders remoto. Nenhum comando SSH arbitrário será usado como fallback.
- Esta revisão prepara um modo manual `orders-pilot-inventory` pela chave `production-preflight`, enviando somente o SHA completo da main. O wrapper validará o blob do helper e forçará o modo `inventory`; o próprio helper recusará SHA que não corresponda à ponta atual da main. O job não recebe credencial de deploy nem habilita prepare/apply.
- A atualização da cópia root-owned no host é uma operação separada. Mesmo com CI verde, só pode ser feita após autorização específica e conferência de conteúdo/hash, owner `root:root`, modo `0755` e preservação das rotas/restrições existentes.

### Contrato CLI antes da instalação

- O PR #288 passou no CI `40240294423` e foi integrado em `e79263c9359f9f7037070e05754d2005cd752dcd`. Na revisão operacional anterior à instalação foi identificado que a rota Python enviava `--mode inventory`, enquanto o parser Orders recebe `inventory` como argumento posicional. O wrapper desse commit não foi instalado nem executado no host.
- O teste da fronteira wrapper/helper foi reforçado para encaminhar os argumentos capturados ao parser real com Host simulado; reproduziu `SystemExit: 2 / unrecognized arguments: --mode`. A correção usa `inventory --sha <SHA>`, preservando o modo fixo e o blob do helper. A instalação operacional aguarda o CI dessa correção.
- A avaliação proporcional de refatoração não identificou limpeza adicional segura neste ajuste; apenas o contrato de chamada, o teste e a documentação foram alterados.

## Baseline operacional confirmado após PR #289

A inspeção autoritativa salva em 25/10/2026 23:58 UTC substitui o baseline histórico 0087 descrito nas seções anteriores. O piloto já está publicado em `9bd66c48d7d43462886652b8fe85fdcbff877f64`, schema `20261024_0088`, com checkout limpo, API/web/worker saudáveis e os 15 serviços ativos. As quatro tabelas Orders existem: uma conta, uma configuração e nove tentativas; inbox com zero registros no instante da leitura. Os estados existentes não foram alterados.

A identidade `/var/lib/markina-gallery/deploy-state/orders-current.identity.json` confirmou SHA/schema/imagens e recibo anterior completo, com restauração, barreira, callbacks, restart policy e stage concluídos. SHA-256 da identidade: `bb4998f77656691b2436c1d5ec635a9cf0e914c1d453eb4ad7595f2f318c8438`. O overlay publicado é `orders-prepare-ed5c1242020a45ce8772d68756a4c363/active.compose.json`, SHA-256 `d7458bb91b221de791692efe4d09f86fd7e3916c4610234a9edfc010277ed490`. Emissão continua limitada ao mesmo par do proprietário e cobranças reais estão bloqueadas. Nenhum UUID ou segredo foi registrado aqui.

O PR #289 foi integrado em `5b9600f67000407cc1cd129629488c09dc2970ab` após CI `40243665721` aprovado. O wrapper foi instalado atomicamente: SHA-256 `98514bc5c7712637b69c1c6b3219f6704c78b2bffd6310f872f15020f97c2733`, `root:root 0755`, backup em `/var/backups/markina-gallery/preflight-ssh-wrapper-20261025T235604Z-pr289`. A chave restrita recusou comando arbitrário. O inventário com o helper ainda histórico recusou `checkout_divergente`; não foi contornado e não houve preparação, backup operacional, manutenção ou migration.

A próxima preparação SHALL partir de 0088 e aplicar somente 0089 no ensaio isolado. SHALL exigir a identidade/overlay existentes, manter exatamente as distribuições Python ativas, copiar a identidade para recuperação e incluir as quatro tabelas Orders completas na comparação de preservação financeira. O recibo Pillow original continua preso ao schema 0087 em que a correção foi publicada; esse campo histórico não muda com o schema atual. A aplicação operacional continua sujeita ao plano concreto e à aprovação específica após a preparação.

Contratos locais da atualização: 44 aprovados/1 skip de permissão Linux no Windows; 43 contratos do helper e dois contratos reais do wrapper aprovados em Linux ARM64 sob emulação local, sem skips. A suíte do CI agora executa também a fronteira wrapper/parser real e os dois contratos CLI pelo runner unittest. Política do workflow, Ruff, sintaxe Bash e OpenSpec estrito aprovados. O ensaio nativo com backup operacional atual permanece pendente na task 10.3; não é substituído por esses testes sintéticos. A limpeza proporcional ficou limitada à remoção da instalação duplicada do SDK, já presente na imagem ativa.

## Continuidade autorizada — preparação concluída de 0089

- PR #290 aprovado no CI `40248904439` e integrado como `f9091a7be60314285e2c19b762c62eb5b64183e5`. Backend/frontend/docker iguais ao runtime revisado `b69a95c5`. O CI da main a acompanhar é **CI / push / f9091a7b**, run `40251917299`; não confundir com outros workflows de monitoramento que podem concluir antes dele.
- Wrapper instalado atomicamente com SHA-256 `70573e11c190801069e007182fba1c9725c6b2817487b0107c14124ec71b45a0`, `root:root 0755`, backup `/var/backups/markina-gallery/preflight-ssh-wrapper-20261026T005958Z-pr290`; helper pin `13371d50abfdeedbe02408546a685277b3e7f042`.
- Inventário pela chave restrita aprovado: baseline `9bd66c48`/0088, 15 serviços saudáveis, HTTPS `[200,200,200]`, apenas `127.0.0.1:8080` publicado e fingerprint de consulta `884f49b09bfe410d9c9375eb6f306cc72d7737c326ac8d6809c82656abe49b46`.
- Operador protegido: `/var/lib/markina-gallery/deploy-state/orders-upgrade-operator-f9091a7b/`. `operation.json` e `result.json` registram a preparação iniciada em `2026-10-26T01:04:41Z` e concluída com exit code 0. Não iniciar outra preparação: o recibo válido é `/var/lib/markina-gallery/deploy-state/orders-prepare-a7acbccbc6aa4e41a29bb59eece91136/prepared.json`.
- Fingerprint preparado `3bd1e26355c76676d5c61239e8702503b9018e6b1a171809f4991f3df76bff38`; fingerprint do baseline interno `8917141dcfb0d2e2d41e59514a91622b667d25b3411a34efac6837b5d67106ad`. API/worker candidatos `sha256:f1715fb18dacbcf24e23bef75546729c9aeebc8ac2ade7c40c0f8aa5bb41ec49`; web `sha256:4538c63e6beba1bcc7b926ccbcd27685b7ac05d47a524d8831c8a2e3be91b606`.
- Backup 110.968.499 bytes, SHA-256 `9b57a436cbea81fda3dc094217aa8d3235029298b256a48abccff6828a323772`. Restore isolado, decifragem das credenciais existentes, migration 0088→0089 e preservação financeira aprovados; guard, callbacks e restart policy aprovados. Auditoria confirmou produção ainda em 0088 e nove tentativas. Cópias do cofre/par/identidade ficam apenas no host protegido; nenhum valor pessoal foi registrado.
- Próxima ação: após o CI **da main** passar, usar o helper protegido acima para `seal --receipt <prepared.json> --sha f9091a7be60314285e2c19b762c62eb5b64183e5`; conferir o novo fingerprint/recibo `prepared-main.json`, apresentar inventário/portas/plano e executar `apply` já autorizado. Conferir filas quiescentes pelo helper antes de iniciar manutenção; se houver trabalho ativo, aguardar sua conclusão sem interrompê-lo. A opção de interrupção legada permanece limitada aos seis processos conferidos, sem SIGKILL. Somente API/web/worker geral serão substituídos; os seis especializados conservam seus IDs/imagens, e os demais projetos não são alterados.
- Antes de DDL, falha retoma os mesmos containers/0088; depois de iniciar DDL, manter evidência/manutenção e recuperar com o candidato compatível, sem rollback financeiro automático. O procedimento faz backup final restaurado sob a barreira antes da migration. Verificar schema 0089, saúde, SHA/imagens, isolamento ao mesmo par e preservação dos registros ao terminar.
- Autorização de merge/deploy já dada pelo proprietário enquanto dorme, com acompanhamento a cada 30 minutos até conclusão. Sem nova confirmação ou baterias opcionais. As alterações locais de OpenSpec sobre essa diretriz ficam preservadas para consolidar com a evidência **depois da publicação**, evitando outro push/CI que altere o alvo agora.

## Publicação concluída — verificação de 26/10/2026 02:02 UTC

O CI `40251917299` foi confirmado como workflow **CI**, evento `push`, branch `main`, SHA `f9091a7be60314285e2c19b762c62eb5b64183e5`, conclusão `success`. O recibo foi selado em `prepared-main.json` sem trocar imagens/fingerprint e a aplicação ocorreu sob a autorização explícita do proprietário, sem nova solicitação de confirmação.

Antes da manutenção, filas quiescentes e inventário foram conferidos. O procedimento preservou os containers antigos, aplicou a barreira, fez backup final e restaurou/validou esse backup em PostgreSQL isolado antes de DDL. A migration operacional alcançou `20261025_0089`; a comparação financeira integral entre antes/depois da migration passou antes da retomada dos escritores. Backup final: 110.965.719 bytes, SHA-256 `10bf127c681025f902a3aca87c9ba7847236042e6f525e6e69a05caa10b577bf`, em `orders-prepare-a7acbccbc6aa4e41a29bb59eece91136/pre-migration.custom`, protegido no host.

Resultado pós-publicação, persistido em `/var/lib/markina-gallery/deploy-state/orders-upgrade-operator-f9091a7b/verified.json`:

- Checkout/API/worker em `f9091a7b`, schema 0089 e identidade publicada coerente com as imagens candidatas já registradas; checkout limpo.
- 15 serviços running/healthy e HTTPS `[200,200,200]`; Nginx permanece em `127.0.0.1:8080`. Manutenção removida e sem marcador de operação pendente.
- Seis especializados preservaram os mesmos IDs e imagens Pillow. Containers de banco, Redis, Evolution e Nginx conservaram IDs/imagens/StartedAt; nenhum outro projeto foi alterado pelo procedimento.
- Índice `uq_mp_active_client_revision` presente e índice global `uq_mp_active_client` ausente. Nove tentativas, uma conta, uma preferência e zero registros de inbox no instante do smoke. Preservação financeira da migration confirmada; digests de configuração PIX/conta/preferências iguais após retomada.
- Disponibilidade verificada pelo código da API em transação somente leitura: cliente proprietário com cartão e PIX disponíveis, outra identidade de cliente bloqueada para Mercado Pago, conta de teste e cobranças reais bloqueadas. A comparação do par permitido com o recibo confirmou a restrição existente, sem expor UUIDs.

Esta conclusão publica o ajuste de mínimo/processamento/compras simultâneas no piloto sandbox. Não foi criada nova cobrança pelo deploy. Os cenários visuais e as novas compras manuais serão retomados pelo proprietário, conforme a validação proporcional solicitada; tasks 6.3/8.2 e a pendência externa 5.4 não são marcadas como executadas. A change permanece ativa, sem sincronização/arquivo automático. O acompanhamento periódico desta publicação pode ser encerrado por conclusão; as evidências/documentação são consolidadas após o deploy, sem outra publicação ou bateria opcional.

## Decisão posterior — liberação geral em produção, 27/10/2026

O proprietário decidiu ampliar o Mercado Pago para todos os fotógrafos, preservando o isolamento por fotógrafo, as credenciais próprias, a habilitação individual, a restrição do cliente de teste ao par previamente autorizado e o PIX independente. Essa decisão substitui, a partir desta data, a limitação de escopo do piloto que vedava a liberação geral e cobranças reais; não altera nem reinterpreta os resultados históricos do Sandbox ou a publicação do piloto descrita acima. A execução e a evidência da ativação do gate operacional estão rastreadas em `openspec/changes/enable-mercadopago-production/`. O gate global permanece fechado até inventário atualizado, plano operacional aprovado e execução pelo fluxo autorizado. Nenhuma cobrança de teste ou real foi criada por esta decisão documental.
