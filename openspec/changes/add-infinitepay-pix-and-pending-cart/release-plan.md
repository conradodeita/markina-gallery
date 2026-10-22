# Plano coordenado de pagamentos — 0086 — não executado

> Preparação autorizada em22/10/2026, após merge262/266: inventário atual, ensaios sintéticos, preparador manual e gates remanescentes estão em `release-preparation-20261022.md`. CI789 comprovou validações técnicas aprovadas e bloqueio `release_scope=protected`. O proprietário escolheu backup cifrado da chave mestra no próprio PC, senha sob sua guarda. O provisionamento real exige sua entrada no SSH e ainda não ocorreu; a publicação continua não executada. Este seguimento não amplia o workflow0084.

## Escopo e precedência

Este plano atualiza o alvo do candidato combinado do PR262 para a cadeia0085→0086. O plano do cofre continua aplicável a autorização, isolamento, keyring, restore e callbacks; suas referências a0085 como alvo final ficam substituídas por0086 neste conjunto. PR266 tem CI785 aprovado e foi incorporado anteriormente; CI786 aprovou somente o checkpoint anterior à integração mista. Nenhum desses resultados aprova automaticamente o novo head.

Serviços afetados:API e web; etapa própria de schema pelo serviço migrate. API interna8000 e rotas HTTPS existentes, sem novas portas/subdomínios públicos. Webhook usa `/api/infinitepay/webhook` no proxy existente. Keyring somente na API. Sem alteração de runtime Python, workers, Redis, Nginx ou recursos de terceiros. PR261 permanece independente.

## Gates e ordem mínima autorizável

1. Revisão do candidato e CI final verde no SHA integrado; revisão humana, sem merge automático. Homologação isolada autorizada com dois tenants e chaves sintéticas:upgrade0084→0085→0086, restauração de dump+keyring, API/web, webhook, retomada legada, PIX manual e misto. Não usar clientes ou pagamentos reais nesse ensaio.
2. Solicitar autorização operacional específica após inventário atual:projeto `markina-gallery`, Compose `docker/docker-compose.yml`, domínio/portas, schema observado, imagens/digests de API/web/migrate atuais e alvo, backup restaurável, keyring seguro e responsável. Inventário Oracle não foi coletado nesta missão; referências históricas não equivalem ao estado atual.
3. Aplicar barreira de novas emissões/configuração conforme procedimento aprovado, preservando callbacks/conciliação. Backup e restore comprovados antes da cadeia Alembic inspecionada0085→0086 com imagem fixa de migrate. Não acionar workflow0084 nem ampliar suas allowlists, pins ou gate de schema para admitir o conjunto.
4. Subir API compatível com0086/cofre antes da web correspondente. Verificar saúde, capacidade do cofre, sessão/ownership A/B e endpoint de callback sem criar pagamento real. Confirmar que web/workers não receberam material mestre. Só reabrir escritas após resultados satisfatórios.
5. Proprietário habilita PIX na conta InfinitePay somente após publicação bem-sucedida, conforme sua decisão explícita. Conferir opções/recebedor de um link de teste autorizado, sem concluir pagamento. Novas emissões oferecem cartão+PIX; links legados permanecem exclusivos de cartão. Cadastro/rotação pela UI exige autenticação+confirmação e nunca pede segredo no chat.

## Rollback e continuidade financeira

Antes de qualquer uso dos campos0086 e adoção do cofre, avaliar as imagens anteriores inventariadas mantendo schema aditivo e web compatível; não fazer downgrade como rollback padrão. Depois de emissão mista, captura PIX, desistência visual ou adoção gerida, manter imagem de recuperação compatível com0086/cofre/métodos reais. API antiga que rejeita PIX ou ignora versões do cofre não constitui rollback financeiro seguro.

Na falha, interromper novas emissões afetadas pelo mecanismo previamente aprovado e manter verificação/callbacks compatíveis. Preservar snapshots, links, receipts, ciphertext, keyring, auditoria e transações legítimas. Não liberar reservas, reemitir links, restaurar seleções removidas ou reverter confirmação para corrigir aparência. PIX manual só permanece disponível para seleção independente e com aplicação financeira saudável. Sem imagem compatível ou segregação ensaiada, usar correção progressiva com escritas restritas; não alegar rollback completo.

Migration0086 recusa downgrade com campos novos em uso. Backup antigo não pode apagar pagamentos posteriores:qualquer restore exige reconciliação própria. A desistência visual não cancela link remoto, portanto confirmações tardias continuam processáveis; reabertura administrativa mantém seu tratamento excepcional já existente.

## Estado operacional

Nenhum deploy, reinício, migration remota, provisionamento de segredo ou alteração de compra real executado nesta change. Não habilitar PIX no provedor nesta fase. GO para preparar/revisar implementação; merge e publicação dependem dos gates acima e autorização específica.
