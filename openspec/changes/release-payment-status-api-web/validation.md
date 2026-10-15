# Evidência de preparação

## Inventário somente-leitura — 2026-10-15, 19:49 UTC

- SSH validado: `ubuntu@132.145.193.169`, host `clearbudget-vnic`, projeto `/opt/markina-gallery`, checkout limpo `71be3b29659143293351968e15fb4886c2d72bf0`.
- Main remota: `200859a0df0a1943b8c09ddc0f8f206e54dec851`. O comparativo remove a migration 0081 e código implantado de entrega/autenticação; candidato ainda não publicável sem integração.
- API saudável: container `6c2e64582b0bc56d642f2a228ca0619ca8984ec7ff06e7b87f0c17c48aa47744`, imagem `sha256:1efd40743c34fbf31f2b435942a4e78a8f31501928ea02ab2e238f8ba9155279`.
- Web saudável: container `611f86c0d5159e3a7543cbdf7631b3c5f49c91d82884d42c0ace82e19e5dfc34`, imagem `sha256:6941be2068c9143f4a54331da2c9bac1511e8d1998b16986bfdbf631284ec560`.
- Hashes SHA256 de `app/main.py`, `app/auth.py` e `app/tenant_hosts.py` dentro da API iguais aos blobs Git de `71be3b2`. `APP_VERSION` da API = SHA completo desse commit.
- Consulta SQL em transação READ ONLY: `alembic_version = 20261014_0081`; nenhuma alteração de dados.
- API 8000 e web 3000 apenas internos; nginx Markina saudável publica somente `127.0.0.1:8080`. Domínio `https://markina.pickyourpic.com.br`. `/healthz`, `/api/health` e `/` retornam 200; `/api/admin/payment-communications` retorna 403 sem sessão.
- Manifesto ativo: compose base, overlay branding, raw-development, preview-adjustment, system-monitor e override externo system-monitor. Arquivo de ambiente identificado: `docker/.env.homolog`; nenhum valor foi registrado.
- Docker Compose 2.35.1. Configuração resolvida com APP_VERSION ativo produz hashes idênticos aos labels: API `8c68c183a87bfdc14ea473faf7612780184934bc010d93e363c21fa39a1334a1`; web `ab41c5052a1fb5d1f46f676de565ddef92ad8127c6c8d2775433f3745b94ae05`.
- Diagnóstico do hash: `compose config --hash` usa `WithoutEnvironmentResolution` nesta versão e não resolve o `env_file` adicional da API. Calcular o hash passando a configuração JSON resolvida apenas em memória a `compose -f - config --no-interpolate --hash api,web` reproduz exatamente os labels, sem imprimir segredos ou criar arquivo. Não relaxar o gate por causa desse comportamento do Compose.
- Demais serviços Markina saudáveis; outros projetos Firefly, Nginx Proxy Manager e Portainer identificados e fora do escopo. Disco do host: 194 GiB total, 73 GiB livres (63% utilizado).
- `web-last-healthy.sha=faafe14…` é registro antigo, não versão atual comprovada; rollback usará os IDs de imagem acima.

## Estado

Somente leitura no servidor. Reconciliação Git e runbook em preparação local. Nenhum deploy, migration, envio de mensagem ou alteração de configuração executados.

## Validação da integração local

- Conflitos reconciliados em CI (preservada a origem Docker Hub validada no PR #188) e no cabeçalho do pedido (cores novas e referência agrupada já implantada preservadas).
- Regressão reproduzida: o teste do download passa com `confirmed` e falha com `confirmed_undelivered` antes da correção. Após admitir ambos os estados confirmados, a suíte frontend passou: 524 testes em 60 arquivos.
- `ruff check backend/app backend/tests`: aprovado.
- `openspec validate release-payment-status-api-web --strict`: aprovado; `openspec validate --specs`: 21 specs aprovadas, com avisos já existentes de requisitos longos.
- Blocos Bash do runbook analisados por `bash -n`: sintaxe válida; revisão de escopo confirma comandos explícitos para API/web e recarga apenas do nginx Markina.
- Diff contra `71be3b2` em migrations, Compose, Dockerfiles, manifests e lockfile de dependências: vazio. Código de runtime difere somente em `backend/app/main.py`, página de pagamentos, cores e badge da interface.
- `git diff --cached --check` informa apenas duas linhas em branco ao final de documentos da change de download, trazidas do commit já implantado; nenhuma reformatação desses artefatos foi feita.
- Testes locais direcionados: backend — 88 passaram; painel — 3 passaram; frontend — 524 passaram em 60 arquivos. `ruff check backend/app backend/tests`, `npx tsc --noEmit`, `npm run build`, `npm run lint` (0 erros; 31 avisos existentes), 21 specs OpenSpec e CI completo do PR #190 passaram. CI: backend, frontend, gemma-runtime, OpenSpec, gitleaks e política de inventário aprovados; deploy-homolog ignorado.
- PR #190 mergeado em 2026-10-15 às 20:31 UTC: `d9c8d3b118fc367af26cfa2b47772d7bff1ccd47`. O checkout da produção é ancestral da candidata. Testes automatizados verdes; inspeção visual autenticada ainda exige uma sessão legítima.

## Inventário final para aprovação — 2026-10-15, 20:32 UTC

- Host `clearbudget-vnic` (`132.145.193.169`), caminho `/opt/markina-gallery`, checkout limpo em `71be3b29659143293351968e15fb4886c2d72bf0`. Candidato integrado e ancestral de `origin/main`: `d9c8d3b118fc367af26cfa2b47772d7bff1ccd47`.
- Revisão Alembic lida em transação read-only: `20261014_0081`; migrations, banco e dependências não mudam no candidato.
- API saudável: container `6c2e64582b0bc56d642f2a228ca0619ca8984ec7ff06e7b87f0c17c48aa47744`, imagem anterior `sha256:1efd40743c34fbf31f2b435942a4e78a8f31501928ea02ab2e238f8ba9155279`, configuração `8c68c183a87bfdc14ea473faf7612780184934bc010d93e363c21fa39a1334a1`.
- Web saudável: container `611f86c0d5159e3a7543cbdf7631b3c5f49c91d82884d42c0ace82e19e5dfc34`, imagem anterior `sha256:6941be2068c9143f4a54331da2c9bac1511e8d1998b16986bfdbf631284ec560`, configuração `ab41c5052a1fb5d1f46f676de565ddef92ad8127c6c8d2775433f3745b94ae05`.
- Nginx Markina saudável: container `ab350661ce6db0beb4e97cc82c56f76366bab966453fe85932d31259acfe97bb`; única porta publicada pelo projeto `127.0.0.1:8080`. API 8000/web 3000 são internos. Manifesto Compose é idêntico ao inventário anterior.
- Configuração alvo difere somente no metadado `services.api.environment.APP_VERSION`, de `71be3b2…` para o SHA aprovado; hashes atuais reproduzem os labels dos containers. Ambiente mantém rótulo `docker/.env.homolog`, sem valores registrados.
- Testes HTTPS atuais: `/healthz` 200, `/api/health` 200, `/` 200, `/admin/payments` 200; endpoint de pagamentos sem sessão 403. Os mesmos checks serão executados após a troca.
- Projeto Markina tem 15 containers. Outros projetos/containers no host serão preservados. A aplicação de `API/web` pode causar breve interrupção; o nginx da Markina recebe apenas `nginx -t` e reload, sem recriação ou alteração do proxy compartilhado. Rollback usa os IDs de imagem anteriores acima. Os comandos de release e recuperação estão no runbook.
- Código que vincula a aprovação a este inventário: `08c19e0e6041a5bf3c50a2da80a4add082ea7447fe8cbb6b362bd5b5a82c1865`.

Esta aprovação operacional final e específica foi concedida, mas seu inventário foi supersedido após a tentativa de publicação e rollback abaixo.

## Tentativa de publicação e rollback — 2026-10-15, 20:44 UTC

- A aprovação para `d9c8d3b118fc367af26cfa2b47772d7bff1ccd47`, inventário `08c19e0e6041a5bf3c50a2da80a4add082ea7447fe8cbb6b362bd5b5a82c1865`, abrangia explicitamente API/web e rollback pelas imagens anteriores.
- O preflight conferiu novamente o código aprovado. Build das imagens API/web concluiu; a troca foi revertida durante smoke test porque o verificador tentou executar Python dentro da imagem frontend, que contém Node.js e não Python. A falha foi no script de verificação, não no build da aplicação.
- O rollback restaurou as imagens anteriores, checkout limpo `71be3b29659143293351968e15fb4886c2d72bf0` e recarregou apenas o nginx da Markina. Nenhuma migration ou escrita no banco ocorreu. Verificação independente posterior confirmou API/web/nginx saudáveis, Alembic `20261014_0081`, HTTPS `/healthz`, `/api/health`, `/` e `/admin/payments` em 200, e endpoint administrativo sem sessão em 403.
- Docker recriou os containers de API e web durante o rollback: API `2f417d580a249e367f358b8fb5d685a509fa6eff9b8d5f6454ac26cf17fcfd67`; web `ac23005592768cde490a7c5b685dbefd89b319349253db0523c57fb112868556`. Nginx permaneceu `ab350661ce6db0beb4e97cc82c56f76366bab966453fe85932d31259acfe97bb`. As imagens anteriores e hashes de configuração continuam iguais ao inventário aprovado; endpoints e revisão de banco também não mudaram.
- A checagem de rollback automatizada compartilhou o mesmo erro ao tentar usar Python no frontend; por isso, seu resultado não é declarado como aprovado pelo runner. A leitura independente acima confirmou o estado operacional restaurado.
- O runbook foi corrigido para executar a health check interna do frontend com Node. O próximo deploy requer novo aceite porque os IDs dos containers, que fazem parte do fingerprint do inventário, mudaram após o rollback autorizado.

## Inventário pós-rollback para nova aprovação — 2026-10-15, 20:44 UTC

- Alvo continua `d9c8d3b118fc367af26cfa2b47772d7bff1ccd47`; checkout de produção limpo em `71be3b29659143293351968e15fb4886c2d72bf0`, ancestral do alvo em `origin/main`; Alembic `20261014_0081`.
- API saudável: container `2f417d580a249e367f358b8fb5d685a509fa6eff9b8d5f6454ac26cf17fcfd67`, imagem anterior `sha256:1efd40743c34fbf31f2b435942a4e78a8f31501928ea02ab2e238f8ba9155279`, configuração `8c68c183a87bfdc14ea473faf7612780184934bc010d93e363c21fa39a1334a1`.
- Web saudável: container `ac23005592768cde490a7c5b685dbefd89b319349253db0523c57fb112868556`, imagem anterior `sha256:6941be2068c9143f4a54331da2c9bac1511e8d1998b16986bfdbf631284ec560`, configuração `ab41c5052a1fb5d1f46f676de565ddef92ad8127c6c8d2775433f3745b94ae05`.
- Nginx Markina saudável, container `ab350661ce6db0beb4e97cc82c56f76366bab966453fe85932d31259acfe97bb`; somente `127.0.0.1:8080` publicado pelo projeto; domínio `https://markina.pickyourpic.com.br`. API 8000/web 3000 internos. Saúde e respostas HTTPS permanecem conforme verificação acima. Sem mudanças no Compose, ambiente, banco, demais containers ou recursos compartilhados.
- Recursos observados: 20,4 GiB de memória disponíveis, 72,6 GiB em disco e load de 1 minuto `0.49`.
- Novo código do inventário que vincula o aceite à identidade atual dos containers: `798ec5e08e3369df50489d0cd608ce9e86305c77c26b04080d83fe4a480390d2`.

O deploy permanece pendente de nova aprovação explícita para o SHA e inventário acima. Não repetir a troca até receber esse aceite e reconferir o fingerprint imediatamente antes da mutação.

## Segunda tentativa e rollback — 2026-10-15, 20:56 UTC

- A reconferência do inventário pós-rollback bateu no código `798ec5…`; build API/web concluiu e os artefatos continham o código aprovado. API e frontend foram trocados temporariamente para o SHA alvo; nginx validou configuração e recebeu reload.
- As verificações de health interna da web, `/healthz`, `/api/health`, `/`, `/admin/payments` em 200, endpoint administrativo anônimo em 403, revisão do banco e ID do nginx passaram. O controle final de containers divergentes falhou porque comparou linhas `nome=ID` excluindo `api/web` somente quando o sufixo da linha era o nome; assim, incluiu os IDs de API/web recriados e interpretou a troca prevista como divergência.
- O rollback autorizado restaurou checkout `71be3b29659143293351968e15fb4886c2d72bf0` e as imagens anteriores de API/web. A leitura pós-rollback confirmou API/web/nginx saudáveis, checkout limpo, HTTPS `/healthz`, `/api/health`, `/` e `/admin/payments` em 200, endpoint sem sessão em 403 e banco em `20261014_0081`. Nenhum outro serviço foi alvo do comando de recriação. O nginx permaneceu no mesmo container.
- A comparação no runbook foi corrigida para ancorar a exclusão no início da linha de serviço (`^markina-gallery-(api|web)-1=`); o rollback agora exige espera explícita por health antes de validar recuperação.

## Inventário após a segunda recuperação — nova aprovação necessária

- SHA alvo `d9c8d3b118fc367af26cfa2b47772d7bff1ccd47`; checkout limpo e atual `71be3b29659143293351968e15fb4886c2d72bf0`, `origin/main` = alvo, Alembic `20261014_0081`.
- API saudável: container `ad3f4218f2adaa49c0c503e380a8781174beb0c716d01e93086ee7aeaa2eecd7`, imagem anterior `sha256:1efd40743c34fbf31f2b435942a4e78a8f31501928ea02ab2e238f8ba9155279`, configuração `8c68c183a87bfdc14ea473faf7612780184934bc010d93e363c21fa39a1334a1`.
- Web saudável: container `82233fbb00927ec6ed320c2f5bc61556a74e0edde54e13ad90e372d6e1b5783b`, imagem anterior `sha256:6941be2068c9143f4a54331da2c9bac1511e8d1998b16986bfdbf631284ec560`, configuração `ab41c5052a1fb5d1f46f676de565ddef92ad8127c6c8d2775433f3745b94ae05`.
- Nginx Markina saudável e inalterado, container `ab350661ce6db0beb4e97cc82c56f76366bab966453fe85932d31259acfe97bb`; porta `127.0.0.1:8080`, domínio `https://markina.pickyourpic.com.br`; API 8000/web 3000 internos. Recursos lidos: 20 GiB disponíveis, 73 GiB em disco e load 1m `0.42`.
- O fingerprint é SHA-256 do JSON canônico (chaves ordenadas, separadores compactos) contendo `target`, `baseline`, `head`, `main`, `schema`, `container_ids` (API/web/nginx), `images` (API/web), `config_hashes` (API/web) e `health` (estados dos três containers e status HTTP como strings). Código atual: `314cf6232ca534fb24c5a26744b2a4b9e76017d1f37557fc57a224a5da295965`.

Este inventário foi aprovado pelo proprietário; o fingerprint foi recalculado imediatamente antes da publicação e permaneceu idêntico. A change foi implantada com sucesso conforme a evidência abaixo.

## Publicação concluída — 2026-10-15, 21:00 UTC

- Aprovação específica confirmada para SHA `d9c8d3b118fc367af26cfa2b47772d7bff1ccd47` e inventário `314cf6232ca534fb24c5a26744b2a4b9e76017d1f37557fc57a224a5da295965`, com rollback pelas imagens anteriores autorizado.
- API e frontend foram construídos sequencialmente a partir do SHA aprovado. O hash de `backend/app/main.py` da imagem API coincide com o blob Git aprovado; o artefato frontend contém `confirmed_undelivered`. Containers ativos: API `ac8b5d76d72fd914f000b9038944f285135fb0fe914ccf2e907712f4b83826b0`, imagem `sha256:d353d21d4974c8a8b08a34740c147e3594b989152bc49e72459372aa203c5cf0`, health `healthy`; web `cdc0ec2303704bc9043040f5e2ba65834aa5273ff43d5cc9cb844d09137cc3ce`, imagem `sha256:82df90ce3a383673872eb8847beb2d421a36f6983d3c50a7794f6fb28e069bec`, health `healthy`; `APP_VERSION` da API corresponde ao SHA alvo.
- Configuração efetiva da API: `965953387b335840e3e4ce8c86a0e96bfef855932894fcc290a34cbf06761535`; web: `ab41c5052a1fb5d1f46f676de565ddef92ad8127c6c8d2775433f3745b94ae05`. Nginx Markina permaneceu no container `ab350661ce6db0beb4e97cc82c56f76366bab966453fe85932d31259acfe97bb`; `nginx -t` passou e somente esse nginx recebeu reload. A comparação de IDs excluiu corretamente API/web e confirmou os demais containers Markina inalterados.
- Checks internos de API e web retornaram 200. HTTPS `/healthz`, `/api/health`, `/` e `/admin/payments` retornaram 200; endpoint `/api/admin/payment-communications` sem sessão retornou 403. API, web e nginx permanecem saudáveis.
- Revisão Alembic antes/depois permaneceu `20261014_0081`; nenhuma migration, escrita no banco, mudança de configuração/ambiente ou alteração em outros projetos ocorreu. Checkout remoto limpo em `d9c8d3b118fc367af26cfa2b47772d7bff1ccd47`.
- Os registros `last-healthy.sha` e `web-last-healthy.sha` foram atualizados para o SHA implantado após os checks. O registro operacional foi criado em `/var/lib/markina-gallery/deploy-state/payment-status-api-web-d9c8d3b118fc367af26cfa2b47772d7bff1ccd47.txt`.
- Nenhuma sessão administrativa autenticada foi disponibilizada; portanto, não houve inspeção visual autenticada. O fluxo automatizado e os checks sem sessão estão registrados acima.
