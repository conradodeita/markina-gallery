# Plano de publicação e ensaio restrito — Mercado Pago Orders

## Estado e autorização

Preparação solicitada em 24/10/2026: revisão, commit/PR e plano operacional. O proprietário informou que não possui homologação privada e escolheu fazer o aceite final na instalação de produção, com seu administrador e seu próprio cliente, **exclusivamente com credenciais de Teste**. Reforçou que cada fotógrafo configura sua própria conta pela UI. Esta decisão substitui a previsão de homologação privada como destino do aceite; não substitui o inventário e a autorização concreta de publicação/migration exigidos pelo AGENTS.md.

**Checkout Orders ainda não publicado: sem migration0088 operacional ou cobrança real.** Em25/10/2026 foram feitos inventários SSH e ensaios isolados/backup/restore. A correção Pillow foi autorizada e publicada separadamente pelo PR258, sem DDL. O piloto Orders continua sujeito ao CI da revisão atual e à aprovação concreta de seu próprio release. A tabela inicial abaixo é histórica; o inventário e os recibos atuais estão na seção de reconciliação de25/10/2026 ao final.

**Atualização de escopo em 25/10/2026:** a correção de compras simultâneas adiciona migration 0089, que substitui o índice de tentativa ativa por cliente por unicidade da revisão ativa. A preparação/recibo existente foi ensaiada somente para 0088 e está supersedida para publicação. Nenhuma migration ou release é autorizado por esta mudança; antes de novo release será necessário reconstruir o candidato incluindo 0089 e repetir inventário, backup/restore e validações do procedimento de publicação.

## Escopo candidato

| Item | Alvo a revisar | Estado |
|---|---|---|
| Repositório | `conradodeita/markina-gallery`; branch `feature/mercadopago-orders` → `main` | main conferida em `cef5bdf8` antes da preparação; confirmar novamente no release |
| Instalação esperada | host `clearbudget-vnic`, checkout `/opt/markina-gallery` | referência histórica; inventário live pendente |
| Projeto/Compose | `-p markina-gallery -f docker/docker-compose.yml`, mantendo todos os overlays operacionais atuais | overlays e hashes efetivos pendentes de inventário |
| Origem e porta esperadas | `https://markina.pickyourpic.com.br`, Nginx `127.0.0.1:8080 → 80/tcp` | conferir sem criar portas/subdomínios/DNS/certificados |
| Schema | pré-requisito da migration: `20261022_0087`; alvo: `20261024_0088` | cadeia ensaiada localmente; revisão do banco ativo pendente |
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
3. Aplicar somente 0088 após backup/restore comprovados e interrupção dos escritores verificada. Não carimbar schema nem fazer downgrade para contornar divergência. Subir os binários compatíveis e retomar filas; conferir schema, hashes carregados, saúde e logs sem dados sensíveis.
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
- Depois de 0088: manter schema/evidência; não restaurar dump antigo sobre novas operações e não executar downgrade destrutivo. A migration recusa perda de dados financeiros.
- Depois da primeira tentativa Orders: um binário anterior sem Orders pode classificar esses pedidos incorretamente. **Não voltar automaticamente para 0087.** Recuperação precisa de versão compatível com 0088 e os novos registros, ou correção para frente, previamente ensaiada e aprovada.
- Se for necessário retirar disponibilidade, fechar somente novas emissões e manter receiver/worker/consulta compatíveis para as tentativas existentes. Dados de teste permanecem identificados e não geram receita real.
- Sem prova de compatibilidade de recuperação e sem operação de release específica testada, publicação permanece bloqueada. Este documento prepara a revisão; não alega impacto zero já comprovado no host.

## Inventário live após aprovação — 25/10/2026

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

## Procedimento pontual implementado e ensaios de preparação

`scripts/orders_pilot_release.py` não altera os gates antigos e não adiciona deploy automático. O inventário padrão foi executado via SSH com sucesso e passou a cobrir 13 filas/outboxes, digests minimizados de 12 tabelas financeiras/de mensagens, identidade dos serviços e comparação entre o arquivo do cofre e a configuração efetivamente carregada pela API, sem imprimir valores. Corrigida a distinção `external_status` da outbox de membros. Nenhum trabalho queued/pending/processing encontrado; unknown não é elegível à drenagem/reenvio.

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

## Continuidade

Concluídos nesta retomada: CI atual reconfirmado, inventário SSH read-only, schema, topologia, imagens, identificação exata do cliente/tenant, validação booleana do cofre e consultas minimizadas de filas/contagens. Não houve merge/deploy/migration, backup de dados operacionais, mudança de segredo/configuração, parada/restart de container ou cobrança.

Pendentes antes da execução: fechamento da revisão/CI do mecanismo, vinculação do recibo à main integrada, inventário/fingerprint renovados e autorização da operação concreta, seguida do login acompanhado. A janela já foi aceita, o procedimento/backup/recuperação foram ensaiados e os UUIDs estão conferidos; não pedir novamente dados pessoais. Não sincronizar specs principais nem arquivar esta change como publicada antes de evidência e aceite.

## Reconciliação de25/10/2026 após Pillow

- Produção: checkout/API1f4483bd, schema0087,15 saudáveis, HTTPS200/200/200. Seis especializados agora usam os IDs Pillow13 aprovados e o overlay persistente de pillow-prepare-20261025-01/active.compose.json. Preservar esse overlay em todos os comandos; novo preflight exige published.json e IDs, não apenas um pin.
- Fonte: main3d2ac6e7 integrado na branch Orders, snapshotcbb2362f; única diferença de backend/frontend/docker versus47af72bd é pin13. O gate permanece congelado. Head do coordenador b89c352d/PR283, CI40209291187 em andamento; não é autorização de aplicação.
- Nova preparação privada: `/var/lib/markina-gallery/deploy-state/orders-prepare-ed5c1242020a45ce8772d68756a4c363/prepared.json`, fingerprint74e83c2682aa2af92ac6bc0f3c8ec8794219a0eef148488a6987910baabcc000. API0b4d4fcd1f0a23f958c18db5d4dd661739dc027fdccd5c3692861c132bfd6aa8; web360f1ca8d6422d4a61adade971acb849a0d73c95b0a25cc2d5cf05443d4b5f10. Candidatos ARM64, SDK somente adicional, código completo da aplicação e distribuições idênticos à candidata financeira anterior validada em60 contratos nativos PostgreSQL; apenas manifest corrigido. Não repetir esses60 como nova execução.
- Backup110.898.809bytes e cópia protegida do cofre, restore/migration0088/cifragem ensaiados em PostgreSQL isolado; shutdown/restart/callback503 e barreira aprovados. Schema de produção permaneceu0087. Nenhum segredo/UUID real é incluído no Git.
- Após CI/revisão: integrar main, seal com equivalência estrita de runtimes, revalidar inventário e aprovação concreta da operação Orders. Nova janela pausa os mesmos seis corrigidos, substitui somente API/web/worker geral, aplica somente0088 com backup final restaurado em ensaio e retoma os mesmos seis IDs. PIX preservado; conta real bloqueada e teste limitado ao par autenticado do proprietário. Cofre existente entregue ao worker sem rotação.
- Saúde pública após nginx reload usa polling limitado15s;503 persistente mantém bloqueio. Não remover journal por uma leitura de sucesso no frontend nem usar saúde HTTP como prova financeira.
