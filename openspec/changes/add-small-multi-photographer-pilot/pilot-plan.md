# Plano do ensaio pequeno futuro

## Estado

Preparação 7.1, prontidão de engenharia 7.2 e jornadas locais 7.3 validadas em 2026-10-01; resultados em `pilot-results.md`. Homologação depende ainda do pacote/autorização 8.1–8.2. Fixture e ensaio local não autorizam provisionamento operacional.

## Corpus e confinamento

Ferramenta `backend/tests/pilot_fixture.py`, sem API/importação de produção. Duas contas e admins sintéticos distintos; três clientes por conta, primeiro telefone igual com UUID/nome separados; uma galeria e duas pastas por conta, comum e restrita ao primeiro cadastro; três fotos por pasta, total 12 JPEGs abstratos 256 × 192 sem pessoas. Conta A tem permissão técnica sintética explícita; B não. PIX de teste é marcador sem cobrança. Credenciais constantes são somente fixtures e jamais se aplicam a conta existente.

Preparação idempotente conserva IDs, arquivos, senha/TOTP e configurações. Não cria sessão, desafio, job ou pedido; verificações confirmam contagens zero. Adaptador `RecordingWhatsApp` implementa contrato de envio mas registra somente intenção em memória. No ensaio futuro, fornecer somente adaptadores sintéticos e impedir conexão externa; nenhum e-mail/push/WhatsApp financeiro/biométrico real.

CLI aceita exatamente `PHOTOGRAPHER_TEST_DATABASE_URL` do banco próprio em `127.0.0.1:15470/pyp_photographer_test`, cria schema `pilot_preparation_<UUID>` e diretório temporário próprios; no encerramento remove somente esses recursos criados pela mesma invocação. Não edita env/secrets/configurações existentes, não remove container/volume ou recursos vizinhos.

## Comandos de preparação validados

A partir de `backend/`, com URL sintética do container próprio fornecida ao processo:

```text
python -m pytest tests/test_tenant_pilot_preparation.py -q
python -m tests.pilot_fixture --verify-preparation
```

Saída comprovada da CLI:

```json
{"clients": 6, "journeys_executed": false, "jpeg_files": 12, "max_concurrency": 6, "photographers": 2, "same_phone_independent": true}
```

Comandos não fazem login nem chamam jornadas. Evidência XML externa em `validation.md`; não versionar mídia, banco, tokens, caches ou relatórios contendo dados reais.

## Roteiro futuro condicionado a 7.2

1. Iniciar instância local e PostgreSQL/mídia exclusivos; aplicar cadeia Alembic validada, preparar corpus e adaptadores sintéticos. Confirmar isolamento, permissões e ausência de envio externo.
2. Autenticar ambos os admins com senha/TOTP sintéticos, provar monitor exclusivo de A e recusa comercial cruzada. Coletar/copy snapshot antes, registrar UTC/cache/cobertura.
3. Autenticar cada cadastro pelo link próprio/OTP contextual em sessão independente; no máximo seis jornadas concorrentes. Conferir biblioteca/pasta comum e restrita, seleção, checkout PIX sintético/finalização, confirmação e entrega; mesmo telefone A/B mantém sessão/estado/histórico distintos.
4. Exercitar negativas diretas de clientes, galerias, fotos/arquivos, carrinhos, pedidos e configurações entre contas. Qualquer acesso/efeito cruzado reprova e interrompe ensaio, abre correção verificável.
5. Processar somente jobs da fixture com serviços/adaptadores locais; medir durante e depois, respeitar TTL de 30 s e distinguir cache da nova amostra. Registrar conclusão por evidência separada caso job transitório não apareça no monitor.
6. Consolidar `pilot-results.md` com instantes UTC, origem/versão/schema, valores observados, pendências e limitações. Filas faciais vazias não comprovam worker/biometria; leituras não comprovam capacidade máxima, fairness, p95, SLO ou orçamento global.

Não iniciar este roteiro enquanto 7.2 estiver pendente. A publicação remota não está autorizada por este plano.

## Executor local 7.3

Prontidão 7.2 registrada. O ensaio usa database UUID descartável no PostgreSQL próprio 15470, aplica Alembic até 0071 e associa explicitamente a conta vazia criada por 0069 ao fotógrafo sintético A (sem apagar/recriar o legado); B é criada pela ferramenta offline. A fixture de preparação aceita esse UUID somente como argumento do executor de teste.

API Uvicorn somente em loopback 8000 e frontend Next já compilado somente em loopback 3038, portas verificadas livres antes da inicialização; se ocupadas, não interromper processos alheios. Perfis Chromium/Edge headless independentes para dois admins e seis clientes, com APIs reais locais, sem interceptar respostas do produto. Login pela interface, OTP lido exclusivamente da mensagem entregue ao adaptador sintético em memória. Nenhum segredo persistente ou configuração .env será alterado.

Monitor consultado e copiado na interface de A; relatório confrontado com o formatter real capacity-report/v1. B recebe capability falsa/403 e painel ausente. Worker de mídia inicia sem atrasos artificiais; amostra durante pode estar em cache e não mostrar jobs curtos. A amostra final espera o TTL real de 30 s, com execução registrada. Artefatos somente em diretório de evidência externo explícito; processos/db próprios encerrados no finally. Ensaios sintéticos não substituem OTP/canais ou jornadas reais autorizadas em homologação.
