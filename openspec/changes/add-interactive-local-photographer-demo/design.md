# Design

## Isolamento

O runner exige `APP_ENV=development`, URL PostgreSQL `127.0.0.1:15472/pyp_ui_demo`, origem `http://127.0.0.1:3039` e opção explícita `--initialize-disposable-db-and-serve`. Recusa parâmetros de query na URL, `PGSERVICE` herdado e `PGHOSTADDR` fora de `127.0.0.1`, pois podem redirecionar uma conexão apesar do host aparente. Ele confere banco vazio, aplica Alembic até `20261026_0090`, cria um proprietário sintético sem login utilizável para satisfazer a pré-condição da migration de créditos `0094`, e aplica a revisão nomeada `20261113_0126`. Usa chaves sintéticas criadas somente em memória do processo. API e Next escutam apenas em loopback; o PostgreSQL fica em container temporário com `--tmpfs` e porta local.

Para restaurar apenas a UI após encerramento do processo, `--serve-existing-disposable-db` exige o mesmo alvo local e a revisão `20261113_0126` por leitura, sem migration ou exclusão. Como as chaves do primeiro processo não são persistidas, contas criadas em execução anterior podem não autenticar; cadastros novos na sessão atual continuam sintéticos. A demonstração permanece descartável.

O processo FastAPI injeta `signup_services` para aceitar somente prova anti-bot vazia da UI local e e-mails `@example.test`. Os códigos aparecem em `/api/local-demo/mailbox`, rota presente apenas no runner; a aplicação normal permanece com 503. O usuário configura a própria senha e TOTP pela UI. A caixa de teste não persiste códigos nem dados de clientes.

A revisão visual mobile de 390 px encontrou rótulos desalinhados na tela existente de cadastro. O formulário recebe um estilo CSS escopado de campos em coluna e alvos de toque de 44 px, sem alterar outros formulários.

## Operação e limites

O executor registra PIDs e nome do container em diretório de evidência local fora do Git. O encerramento deve atingir apenas esses identificadores, sem comandos globais de Docker. A demonstração não substitui teste de provedor real, anti-bot, domínio, contrato/termos ou release. Ao reiniciar, o banco descartável é reconstruído; contas de demonstração não são preservadas.

## Compatibilidade dos runners com o runtime atual

A revisão nomeada atual dos dois runners é `20261113_0126`. Os destinos continuam distintos (cadastro 15472/pyp_ui_demo; encerramento 15478/pyp_closure_ui), sem migrar bancos existentes nem iniciar outra API durante os testes de compatibilidade. A atualização substitui a fixação histórica em 0105/0123: o ORM atual usa declaração de maioridade, catálogo e marcadores de limpeza biométrica posteriores. A retomada de cadastro recusa schemas antigos sem escrita. O smoke usa o mesmo campo explícito de maioridade exigido pela UI/API; não altera a validação do produto. Duas regressões aplicam as migrations nomeadas em schemas PostgreSQL descartáveis e exercitam os modelos/seeds reais.
