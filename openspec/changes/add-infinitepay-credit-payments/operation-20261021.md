# OperaÃ§Ã£o supervisionada â€” 21/10/2026

## AutorizaÃ§Ã£o vigente

O proprietÃ¡rio autorizou manutenÃ§Ã£o imediata, indisponibilidade, encerramento gracioso inclusive de workers ativos, merge/release dos PRs necessÃ¡rios e rollback supervisionado por identidade. Autorizou os quatro pins Python nos oito consumidores apenas com candidaturas/gates aprovados; manter Python 3.13.16 e demais distribuiÃ§Ãµes. Essa autorizaÃ§Ã£o substitui o NO-GO por escopo operacional anterior; nÃ£o autoriza apagar volumes, dados, fotografias ou histÃ³rico financeiro. NÃ£o incluir #262/migration 0085 sem seus prÃ³prios prÃ©-requisitos comprovados; nesta operaÃ§Ã£o ficam excluÃ­dos. #261 nÃ£o Ã© necessÃ¡rio Ã  prioridade API/web e nÃ£o Ã© incluÃ­do.

## InventÃ¡rio inicial e impacto

Host `clearbudget-vnic`, projeto `markina-gallery`, `/opt/markina-gallery/docker/docker-compose.yml` e overlays jÃ¡ ativos. DomÃ­nio `https://markina.pickyourpic.com.br`, entrada exclusiva Nginx `127.0.0.1:8080`; portas pÃºblicas/proxy compartilhado nÃ£o serÃ£o alterados. Disco 63 GiB livres e RAM aproximadamente 14 GiB disponÃ­veis. Todos os quinze serviÃ§os do projeto estavam saudÃ¡veis. API e web mantÃªm as identidades registradas em `release-gates-20261021.md`, schema 0084, APP_ENV staging.

Binding cadastrado pelo proprietÃ¡rio em terminal SSH com getpass e repetiÃ§Ã£o, arquivo raw ignorado dedicado Ã  API, modo 0600 e owner ubuntu. ConferÃªncia pelo executor apenas de estrutura, tenant e ambiente, sem imprimir valor. Tenant confirmado por associaÃ§Ã£o administrativa ativa. Primeiro cadastro nÃ£o foi concluÃ­do; arquivo ausente foi confirmado, sem chave exposta; repetiÃ§Ã£o concluiu. Arquivo nÃ£o foi criado em Git/CI/frontend e nÃ£o Ã© compartilhado com workers.

Agregados iniciais: facial 3937 completed/219 cancelled/2 failed; mÃ­dia 3447 completed; prÃ©vias 3439 ready; RAW/e-mail vazios; WhatsApp 18 accepted/200 expired/1 failed. Nenhum estado processing nesses agregados; essa observaÃ§Ã£o nÃ£o Ã© requisito de fila vazia nem prova de ausÃªncia de requisiÃ§Ã£o em voo. CartÃ£o: 1 confirmed, 2 awaiting_payment, 1 verification_required. Preservar essas compras, em especial e2194ce5; nÃ£o criar nova cobranÃ§a nem repetir emissÃ£o.

## Gates corrigidos sob a autorizaÃ§Ã£o nova

O manifesto passa a registrar baseline web/checkout 27e1b8ff e baseline API fe1f3bc6 separadamente, junto ao ID exato da imagem API anterior e blob aprovado de requirements-push. O verificador compara tambÃ©m todos os inputs backend contra a baseline API, impedindo que avanÃ§o web oculte alteraÃ§Ãµes. Permanece recusando modelos, migrations, Dockerfiles, outras dependÃªncias ou blobs divergentes. O classificador sÃ³ admite o caso emergencial se o verificador completo aprovar; a classificaÃ§Ã£o genÃ©rica protected/dependencies continua intacta.

O executor app existente aceita o Compose somente atravÃ©s do gate de blobs; continua recusando migrations. Confere o ID da API antiga e seus inputs reais. A API candidata deriva da imagem preservada, instala os quatro wheels com no-deps, copia app/requirements diretamente de git archive do SHA aprovado, preserva as demais camadas e compara todas as distribuiÃ§Ãµes/Python. Pip check e startup isolado ARM64/network none/tmpfs/sem segredos devem passar antes de atualizar a referÃªncia de imagem e antes de qualquer recriaÃ§Ã£o.

A conferÃªncia de drift volta ao checkout anterior para comparar o runtime com sua prÃ³pria configuraÃ§Ã£o; ao retornar ao alvo, compara novamente os hashes resolvidos capturados antes do build. Assim uma alteraÃ§Ã£o de config durante o build continua recusada e o env_file API-only revisado nÃ£o Ã© confundido com drift ilegÃ­timo. Wrapper continua root-owned e pinado por blob; sua instalaÃ§Ã£o serÃ¡ conferida por hash antes do preflight oficial. Nenhuma proteÃ§Ã£o de branch/environment serÃ¡ dispensada.

## SequÃªncia e recuperaÃ§Ã£o

1. CI final do #260, homologaÃ§Ã£o ARM64 do cÃ³digo candidato e revisÃ£o do delta. Merge oficial com match do head, sem bypass/automerge; CI pÃ³s-merge e aprovaÃ§Ã£o protegida do release.
2. PreparaÃ§Ã£o autorizada dos objetos Git e wrapper revisado; backup lÃ³gico PostgreSQL em local restrito e verificaÃ§Ã£o do arquivo, preservaÃ§Ã£o de imagens/recibos. Sem migration. NÃ£o restaurar banco para resolver incidente de cÃ³digo.
3. Preparar manutenÃ§Ã£o dos ingressos somente da plataforma. Preservar retorno financeiro e integraÃ§Ãµes internas enquanto possÃ­vel; nÃ£o responder sucesso a callback nÃ£o processado. Registrar estados/IDs tÃ©cnicos e janela; a integraÃ§Ã£o atual consulta payment_check no retorno do navegador e nÃ£o consome webhook financeiro como prova. Retornos que coincidirem com a indisponibilidade exigem repetiÃ§Ã£o da URL de retorno/reconciliaÃ§Ã£o com IDs do provedor, jamais reemissÃ£o da compra. Manter compras ambÃ­guas bloqueadas; nÃ£o declarar retry externo garantido.
4. Release oficial somente API/web, com comparaÃ§Ã£o integral de distribuiÃ§Ãµes, isolamento ARM64 e imagens anteriores preservadas. Workers sem candidato completo nÃ£o sÃ£o substituÃ­dos. Verificar identidade, saÃºde, logs sanitizados e recebedor/binding; testar cartÃ£o pelo proprietÃ¡rio com nova compra, sem cobranÃ§a criada pelo executor.
5. Conferir filas/estados antes e depois, serviÃ§os preservados, PIX e rotas de autenticaÃ§Ã£o/galerias/uploads; reabrir plataforma apÃ³s gates essenciais. SaÃºde de worker nÃ£o comprova inferÃªncia nem processamento RAW real. RecuperaÃ§Ã£o por imagens anteriores somente com recibos vÃ¡lidos, preservando banco e transaÃ§Ãµes legÃ­timas; pendÃªncias financeiras nÃ£o autorizam reemissÃ£o.

## EvidÃªncias e execuÃ§Ã£o

Testes locais de polÃ­tica: 15 de escopo (incluindo baseline por serviÃ§o e ocultaÃ§Ã£o de dependÃªncia), 13 de classificador, 3 da comparaÃ§Ã£o integral de pacotes e 2 do provisionamento sem echo; Ruff e OpenSpec estrito aprovados. Testes direcionados de estado/preflight em acompanhamento; resultados adicionais, CI, SHAs/imagens e passos efetivamente executados ficam no corpo do PR/recibos operacionais. NÃ£o transformar esta sequÃªncia em alegaÃ§Ã£o de deploy jÃ¡ realizado.

## Evidência adicional antes da integração

Backup lógico PostgreSQL 107582465 bytes, SHA-256 `bb213711ca569aa1ade763814d2a1c53a7fcf6d22f2cd505f170e9bf169e02b4`, restaurado em PostgreSQL descartável network none/tmpfs, schema 0084 confirmado, container descartável encerrado/removido. Arquivo restrito permanece somente no host, com recibo no diretório operacional. Não houve restore no banco de produção.

Código API do candidato 0c4fd633 homologado em ARM64 local: imagem `sha256:db528a98af72ba19d0f77d00a52586be23b239389df1a6b628f8146f2adaa5cb`, comparação integral de distribuições aprovada, Python 3.13.16, quatro pins corretos, pip check e startup/health/admin sem sessão aprovados. Revisões subsequentes alteram somente operações/Compose/tests; a publicação ainda construirá e homologará a identidade definitiva antes da troca.

Host Python 3.8.10 detectado; extração de git archive ajustada para arquivos regulares em caminhos permitidos, com testes de traversal/symlink/path estrangeiro. O Python dos containers não foi alterado. Configuração de manutenção validada pelo nginx -t do container ativo em arquivo temporário removido, sem reload/ativação. Guarda preserva health/retorno financeiro e retorna 503 nos demais ingressos. Reabertura exige restauração do arquivo original e smoke normal, sem tratar 503 como plataforma saudável. API recebe stop_grace_period 120s. Recibos de rollback incluem hashes Compose anterior e alvo para reconhecer somente IDs/configurações da tentativa aprovada.
