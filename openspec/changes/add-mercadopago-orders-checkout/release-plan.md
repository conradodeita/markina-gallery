# Plano de publicação e ensaio restrito — Mercado Pago Orders

## Estado e autorização

Preparação solicitada em 24/10/2026: revisão, commit/PR e plano operacional. O proprietário informou que não possui homologação privada e escolheu fazer o aceite final na instalação de produção, com seu administrador e seu próprio cliente, **exclusivamente com credenciais de Teste**. Reforçou que cada fotógrafo configura sua própria conta pela UI. Esta decisão substitui a previsão de homologação privada como destino do aceite; não substitui o inventário e a autorização concreta de publicação/migration exigidos pelo AGENTS.md.

**Nenhum deploy, migration operacional, alteração de configuração/segredo remoto ou cobrança real foi executado nesta preparação.** Não houve SSH no servidor. As referências históricas abaixo não são um inventário atual nem uma autorização de execução. O PR permanece separado do merge e da publicação.

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

## Continuidade

Pendentes antes da execução: revisão humana/CI, mecanismo de release deste escopo, inventário live, backup/restore e recuperação compatível, UUIDs do proprietário, autorização concreta e login acompanhado. Não sincronizar specs principais nem arquivar esta change como publicada antes de evidência e aceite.
