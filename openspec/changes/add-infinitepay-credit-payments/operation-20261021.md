# Operação supervisionada — 21/10/2026

## Autorização vigente

O proprietário autorizou manutenção imediata, indisponibilidade, encerramento gracioso inclusive de workers ativos, merge/release dos PRs necessários e rollback supervisionado por identidade. Autorizou os quatro pins Python nos oito consumidores apenas com candidaturas/gates aprovados; manter Python 3.13.16 e demais distribuições. Essa autorização substitui o NO-GO por escopo operacional anterior; não autoriza apagar volumes, dados, fotografias ou histórico financeiro. Não incluir #262/migration 0085 sem seus próprios pré-requisitos comprovados; nesta operação ficam excluídos. #261 não é necessário à prioridade API/web e não é incluído.

## Inventário inicial e impacto

Host `clearbudget-vnic`, projeto `markina-gallery`, `/opt/markina-gallery/docker/docker-compose.yml` e overlays já ativos. Domínio `https://markina.pickyourpic.com.br`, entrada exclusiva Nginx `127.0.0.1:8080`; portas públicas/proxy compartilhado não serão alterados. Disco 63 GiB livres e RAM aproximadamente 14 GiB disponíveis. Todos os quinze serviços do projeto estavam saudáveis. API e web mantêm as identidades registradas em `release-gates-20261021.md`, schema 0084, APP_ENV staging.

Binding cadastrado pelo proprietário em terminal SSH com getpass e repetição, arquivo raw ignorado dedicado à API, modo 0600 e owner ubuntu. Conferência pelo executor apenas de estrutura, tenant e ambiente, sem imprimir valor. Tenant confirmado por associação administrativa ativa. Primeiro cadastro não foi concluído; arquivo ausente foi confirmado, sem chave exposta; repetição concluiu. Arquivo não foi criado em Git/CI/frontend e não é compartilhado com workers.

Agregados iniciais: facial 3937 completed/219 cancelled/2 failed; mídia 3447 completed; prévias 3439 ready; RAW/e-mail vazios; WhatsApp 18 accepted/200 expired/1 failed. Nenhum estado processing nesses agregados; essa observação não é requisito de fila vazia nem prova de ausência de requisição em voo. Cartão: 1 confirmed, 2 awaiting_payment, 1 verification_required. Preservar essas compras, em especial e2194ce5; não criar nova cobrança nem repetir emissão.

## Gates corrigidos sob a autorização nova

O manifesto passa a registrar baseline web/checkout 27e1b8ff e baseline API fe1f3bc6 separadamente, junto ao ID exato da imagem API anterior e blob aprovado de requirements-push. O verificador compara também todos os inputs backend contra a baseline API, impedindo que avanço web oculte alterações. Permanece recusando modelos, migrations, Dockerfiles, outras dependências ou blobs divergentes. O classificador só admite o caso emergencial se o verificador completo aprovar; a classificação genérica protected/dependencies continua intacta.

O executor app existente aceita o Compose somente através do gate de blobs; continua recusando migrations. Confere o ID da API antiga e seus inputs reais. A API candidata deriva da imagem preservada, instala os quatro wheels com no-deps, copia app/requirements diretamente de git archive do SHA aprovado, preserva as demais camadas e compara todas as distribuições/Python. Pip check e startup isolado ARM64/network none/tmpfs/sem segredos devem passar antes de atualizar a referência de imagem e antes de qualquer recriação.

A conferência de drift volta ao checkout anterior para comparar o runtime com sua própria configuração; ao retornar ao alvo, compara novamente os hashes resolvidos capturados antes do build. Assim uma alteração de config durante o build continua recusada e o env_file API-only revisado não é confundido com drift ilegítimo. Wrapper continua root-owned e pinado por blob; sua instalação será conferida por hash antes do preflight oficial. Nenhuma proteção de branch/environment será dispensada.

## Sequência e recuperação

1. CI final do #260, homologação ARM64 do código candidato e revisão do delta. Merge oficial com match do head, sem bypass/automerge; CI pós-merge e aprovação protegida do release.
2. Preparação autorizada dos objetos Git e wrapper revisado; backup lógico PostgreSQL em local restrito e verificação do arquivo, preservação de imagens/recibos. Sem migration. Não restaurar banco para resolver incidente de código.
3. Preparar manutenção dos ingressos somente da plataforma. Preservar retorno financeiro e integrações internas enquanto possível; não responder sucesso a callback não processado. Registrar estados/IDs técnicos e janela; a integração atual consulta payment_check no retorno do navegador e não consome webhook financeiro como prova. Retornos que coincidirem com a indisponibilidade exigem repetição da URL de retorno/reconciliação com IDs do provedor, jamais reemissão da compra. Manter compras ambíguas bloqueadas; não declarar retry externo garantido.
4. Release oficial somente API/web, com comparação integral de distribuições, isolamento ARM64 e imagens anteriores preservadas. Workers sem candidato completo não são substituídos. Verificar identidade, saúde, logs sanitizados e recebedor/binding; testar cartão pelo proprietário com nova compra, sem cobrança criada pelo executor.
5. Conferir filas/estados antes e depois, serviços preservados, PIX e rotas de autenticação/galerias/uploads; reabrir plataforma após gates essenciais. Saúde de worker não comprova inferência nem processamento RAW real. Recuperação por imagens anteriores somente com recibos válidos, preservando banco e transações legítimas; pendências financeiras não autorizam reemissão.

## Evidências e execução

Testes locais de política: 15 de escopo (incluindo baseline por serviço e ocultação de dependência), 13 de classificador, 3 da comparação integral de pacotes e 2 do provisionamento sem echo; Ruff e OpenSpec estrito aprovados. Testes direcionados de estado/preflight em acompanhamento; resultados adicionais, CI, SHAs/imagens e passos efetivamente executados ficam no corpo do PR/recibos operacionais. Não transformar esta sequência em alegação de deploy já realizado.
