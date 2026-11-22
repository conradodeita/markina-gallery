# Validação local — 04/11/2026

## Demonstração ativa

Um container PostgreSQL 17 Alpine exclusivo foi iniciado com `--rm`, `tmpfs` e porta `127.0.0.1:15472`. O runner validou banco vazio e aplicou Alembic `0093`, criou proprietário sintético com login desabilitado e aplicou a revisão explícita `20261103_0098`. API em `127.0.0.1:8000` e Next em `127.0.0.1:3039` foram iniciados localmente; `GET /photographer-signup` e `GET /api/local-demo/mailbox` retornaram 200. `SELECT version_num FROM alembic_version` confirmou `20261103_0098`.

A primeira tentativa de ir diretamente de banco vazio a `0098` falhou fechada na pré-condição real de `0094` (tenant inicial sem proprietário). O banco permaneceu sem tabelas após a transação falha; o runner foi corrigido para criar o proprietário sintético entre `0093` e `0094`. Nenhum dado operacional foi lido ou alterado.

`PYP_RUN_LOCAL_DEMO_SMOKE=1` com `scripts/test_local_photographer_demo.py`: **2 passed**. O teste criou uma identidade `example.test`, leu o código da caixa local, verificou e-mail, configurou senha/TOTP e confirmou HTTP 200 no endpoint da carteira do tenant e HTTP 403 no console global. O teste de guards recusou ambiente de produção, origem pública e banco/host fora do alvo. O e-mail e o TOTP não foram impressos no relatório.

Captura headless em viewport 390×844 encontrou rótulos desalinhados; CSS escopado corrigiu campos e botão. Nova captura local fora do repositório foi inspecionada visualmente, sem sobreposição. `npx vitest run app/photographer-signup/page.test.tsx`: **2 passed**. ESLint do componente, `tsc --noEmit`, build Next, Ruff dos scripts e OpenSpec strict passaram. O teste de fluxo foi repetido após o build com **2 passed**. A refatoração proporcional não encontrou código antigo seguro para remover; o ajuste CSS atinge somente o cadastro.

## Limites

A demonstração permanece aberta localmente para inspeção do proprietário. Ela não tem e-mail/anti-bot reais, não persiste as contas após parar o container e não constitui homologação ou autorização de produção. Nenhum serviço Oracle, cliente, credencial real ou recurso Docker preexistente foi alterado. O encerramento deve mirar apenas as sessões API/Next próprias e o container exclusivo.

## Prova assistida no navegador — 04/11/2026

Após o encerramento das sessões API/Next entre turnos, o frontend foi reaberto localmente e a API foi retomada em primeiro plano com `--serve-existing-disposable-db`. O teste de retomada passou (**2 passed, 1 skipped** sem serviço opt-in) e Ruff passou; a revisão do banco foi conferida sem migration. A aba no navegador deste ambiente mostrou o cadastro real do candidato. Foi solicitado código sintético para uma nova identidade `example.test`, lido pela caixa local e verificado na UI. O proprietário digitou pessoalmente a nova senha e o código TOTP; a UI confirmou **Conta criada**.

Na sessão resultante, `/admin` encaminhou ao painel de créditos do tenant com saldo **0**. A navegação não ofereceu link de plataforma; acesso direto a `/admin/platform` mostrou **Console indisponível — É necessário acesso de proprietário da plataforma**. A lista inicial de galerias estava vazia e a UI criou **Galeria Sintética Navegador**, abrindo sua etapa de Ajustes com título, evento e descrição sintéticos. O navegador foi deixado nessa tela. Nenhum upload, crédito, pagamento, dado de cliente, e-mail externo ou recurso de produção foi usado.

A API foi executada em sessão de terminal da prova, não como serviço persistente; sua disponibilidade depois do encerramento do turno não é garantida. A tentativa de iniciar a API em segundo plano com variáveis de ambiente no comando foi recusada pelo controle automático, e não foi contornada. A recuperação da chave TOTP de sessões anteriores é intencionalmente impossível nesta demonstração sem persistir segredo, o que não foi autorizado.

## Revalidação estática dos guards do runner — 15/11/2026

- A revisão da URL encontrou que parâmetros PostgreSQL `hostaddr` e defaults herdados `PGHOSTADDR`/`PGSERVICE` podem redirecionar uma conexão cujo host aparente é loopback. Os dois runners locais agora recusam query parameters, serviço herdado e endereço `PGHOSTADDR` que não seja `127.0.0.1`; o código de inicialização continua exigindo ambiente, origem, porta, banco e revisão exatos.
- `backend/.venv/Scripts/python.exe -m pytest scripts/test_local_photographer_demo.py scripts/test_local_tenant_closure_demo.py -q`: **4 passed, 1 skipped**. O skip é o smoke opt-in que exige API/Next/PostgreSQL locais ativos. Ruff nos quatro arquivos Python passou. Nenhum runner, serviço, container ou migration foi iniciado nesta revalidação.
- Revisados os arquivos de design e a documentação da demonstração: a revisão atual configurada no runner é `20261105_0105`; as referências operacionais antigas a `20261103_0098` foram atualizadas. A comprovação visual do console de encerramento permanece em sua própria change e continua dependendo da sessão local autenticada.

### Compatibilidade dos runners com o schema atual — 15/11/2026

A leitura dos runners encontrou revisão nomeada antiga em ambos. Duas provas PostgreSQL reais reproduziram a falha: cadastro em0105 não tinha `photographer_signup.adult_attested_at`; seed de encerramento em0123 não tinha `tenant_closure_request.biometric_cleanup_started_at`. JUnit inicial `C:/codex-data/local-review/prepush-demo-schema-before-20261115.xml`: **2 failed**, 24,77 s, preservado.

Os runners agora preparam explicitamente `20261113_0126`, conservando os destinos/portas independentes, banco vazio e recusa de ambiente protegido, query/libpq override e retomada com schema antigo. Não há `upgrade head` implícito nem migration de banco existente. O smoke de cadastro passa a declarar maioridade como a UI/API já exigem; a regra do produto permanece intacta. Os documentos atuais foram reconciliados e snapshots históricos preservados.

Após a correção, as duas provas passaram: inserção/leitura do modelo real de cadastro, seed completo de encerramento e conferência das colunas dos modelos presentes no schema. **2 passed**, 27,60 s, JUnit `C:/codex-data/local-review/prepush-demo-schema-after-20261115.xml`. Execução em schemas exclusivos do PostgreSQL17.11 sintético15470; não foram iniciados outra API, Next ou workers, nem migrados os bancos de UI existentes.

Guards dos scripts: **5 passed, 1 skipped**, 1,60 s, `prepush-demo-guards-final-20261115.xml`; o skip é o smoke interativo opt-in, que não foi executado contra o runner externo já ativo. A regressão de retomada também verifica que a revisão antiga0105 permanece sem escrita após a recusa. Ruff dos quatro Python e `git diff --check` passaram. Revisão proporcional limitada ao runner/testes/docs; nenhuma limpeza geral ou alteração de produto. Estas provas não fecham o visual autenticado.
