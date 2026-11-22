# Preparação operacional de pagamentos — 22/10/2026

## Autorização e alvo

O proprietário autorizou a preparação da publicação após o resultado do CI789 e decidiu guardar no próprio PC um backup cifrado da chave mestra. A senha de recuperação será definida pelo proprietário no terminal SSH, sem chat, argumentos ou logs. Esta preparação não equivale à execução da migration/publicação nem ao aceite de homologação pendente.

Candidato de aplicação: `d7944baef5191ade6ac26fa86cd631bd5ad464d1`, main após merge dos PR262/266. Árvore igual ao candidato d631 aprovado pelo CI788. CI789 terminou com todas as nove validações técnicas aprovadas e falha esperada em release-scope: `release_scope=protected`; sete jobs operacionais skipped. Não alterar gates0084, hashes, manifesto ou allowlists para admitir0086. PR242/Dependabot é independente; PR261 permanece intocado.

## Inventário somente leitura — 08:44:29 de São Paulo

Host `clearbudget-vnic`; raiz `/opt/markina-gallery`; projeto `markina-gallery`; Compose `docker/docker-compose.yml` mais os cinco overlays ativos já existentes. Domínio `https://markina.pickyourpic.com.br`; única porta publicada do projeto: nginx `127.0.0.1:8080`; API8000/web3000 apenas internos. Nenhuma porta ou domínio novo proposto.

Checkout limpo e APP_VERSION: `21b89c332c6937b7079679888d52bd6a8aefe25d`. Schema observado `20261017_0084`; tabela do cofre ainda ausente. Quinze serviços saudáveis; sem marcadores pendentes de release. HTTPS healthz/api-health200. Disco61GiB livres. Chave mestra ausente na API e demais serviços; binding legado presente. Não identificar/alterar compras reais neste procedimento.

| Serviço | Imagem ativa observada |
|---|---|
| API | sha256:92bcf8652e1932fbd3b2d6c7bcbd0c7006f0012cfe686d4eb6aa95e6eec139a5 |
| Web | sha256:c1be0a0128c87ef756abde0a4343a8a9331defa84ca00645704d17e71d71bbb2 |

Python3.13.16; aiohttp3.14.4, multidict6.9.1, urllib32.8.0, yarl1.25.1. Nenhum diff de Dockerfile/requirements/backend ou package/lock frontend entre21b89c3 e o candidato. Manter essa distribuição, sem executar a missão Python.

Evidência local sanitizada: `C:/codex-data/tmp/payments-0086-oracle-inventory-20261022.json`, SHA256 `b556ae5293135303cc883e79db1debbe826a272fb4ecfcb863183070bfb838c92`. Este inventário deve ser renovado antes da operação; não substitui os recibos das imagens alvo.

## Ensaios executados nesta preparação

1. PostgreSQL17 exclusivamente sintético: cadeia0084→0085→0086; comparação dos campos legados após cada upgrade; dump customizado/pg_restore em segundo banco descartável;97tabelas idênticas; dois tenants com envelopes recuperáveis somente pelos próprios identificadores. Keyring cifrado com AES-GCM e chave derivada por scrypt; restauração correta, senha errada recusada e ausência do keyring recusada. Sem provedor real ou dados Oracle. Bancos temporários removidos e somente o container próprio identificado foi parado/preservado.
2. API ARM64 construída localmente do Git imutável d794 sobre a base efetivamente publicada, sem instalar/atualizar pacotes. Todas as distribuições e Python idênticos à base. Smoke em emulação ARM64, rede desativada, filesystem read-only: inicialização, health200, rotas protegidas403 e cifragem/isolamento sintético aprovados. Builds nativos permanecem evidência do CI788/789; não chamar emulação de validação nativa.
3. Preparador manual do keyring: self-test com restauração correta e três recusas (senha incorreta, ciphertext adulterado e nonce adulterado). Motor criptográfico repetido na imagem ARM64, rede desativada, aprovado. Suíte final de oito testes executada na imagem ARM64, zero skips,63,672s: sucesso com arquivos0600/link, não sobrescrita, terminal obrigatório, confirmação/tamanho de senha, release pendente, diretório inseguro, ambiente errado e restauração/recusas criptográficas. Ruff sem erros; OpenSpec estrito aprovado. Nenhum segredo real gerado.

Imagem local de validação do candidato d7944bae: ID local/containerd `sha256:455abe77b6fe57f666df0da4ba5084a62a9b86a8982e772eb9560ce3358db115`. A base importada apresenta ID de manifesto local57defce4, diferente do ID/config da engine Oracle92bcf865; arquitetura, criação, todas as camadas RootFS e todos os campos não vazios da configuração de runtime foram comparados. Campos legados vazios e referência histórica Config.Image não definem runtime. Não assumir igualdade entre IDs de engines ou anunciar esse ID local como imagem publicada. A tag completa está no recibo local de imagem; evitar repetir em prosa identificador que o scanner interpreta como token após a palavra api.

Recibos locais: `payments-0086-synthetic-restore-result.json`, `payments0086-baseline-equivalence.json`, `payments0086-api-image-receipt.json` em `C:/codex-data/tmp/`. Não são backup da produção nem homologação completa API/web/PostgreSQL.

## Preparador manual e backup do proprietário

Fonte revisável: `scripts/provision_infinitepay_keyring.py`. Exige host, diretório700/owner correto, ausência de keyring/backup/link e de tentativa pendente; ambiente observado staging; entrada interativa e senha repetida com16caracteres ou mais. Gera material aleatório32bytes, cifra e verifica backup antes de persistir arquivo ativo0600. Escritas exclusivas, sem sobrescrever material existente. Falha preserva arquivos para reconciliação. Somente com `--provision`; self-test não provisiona. Nunca inicia/recria containers, consulta provedor ou altera pagamentos.

Preparador final disponibilizado na Oracle: `/var/lib/markina-gallery/deploy-state/provision-payments0086-keyring-reviewed.py`, modo700, SHA256 `2210109fdd6cc7b3c0805b4395ed597e810df0a204a1c6befb05abbd31c924bf`. As únicas escritas remotas desta preparação são código sem segredos: versão preliminar preservada e versão final distinta. Não executar a preliminar; nenhuma versão foi executada em modo provisionamento.

Após autorização específica de provisionamento e escolha da senha pelo proprietário no SSH:

```
python3 /var/lib/markina-gallery/deploy-state/provision-payments0086-keyring-reviewed.py --provision
```

Arquivos resultantes previstos: material ativo `/var/lib/markina-gallery/deploy-state/integration-secrets.env` e backup cifrado `/var/lib/markina-gallery/deploy-state/integration-secrets-backup-20261022.json`. Link ignorado pelo Git `docker/.env.integration-secrets` aponta ao arquivo ativo; somente a API candidata tem env_file para lê-lo. A API antiga não recebe o keyring sem recriação. Não executar compose config resolvido nos logs.

O proprietário deverá copiar somente o backup cifrado para o PC, comparar seu SHA256 com o recibo e guardar a senha separadamente. A cópia no mesmo host não constitui recuperação de desastre. Confirmar custódia e restauração antes de liberar cadastro gerido. Não copiar o arquivo ativo em claro para o PC nem enviar qualquer senha/APIKey/chave mestra no chat.

## Sequência restante e critérios de interrupção

1. Finalizar homologação isolada do conjunto de imagens API/web/PostgreSQL e fluxo autenticado de dois tenants, conforme release-plan.md. Fixar identidade exportável/importável das imagens API/web/migrate e imagem compatível de recuperação; conferir distribuição/arquitetura após transferência. O smoke local não preenche esse gate integral.
2. Renovar inventário e revisar o plano com o proprietário antes de ações operacionais. Realizar provisionamento manual acima, custódia externa e backup de produção com restauração isolada comprovada. Não afirmar que o ensaio sintético validou o dump real.
3. Usar lock comum de produção, preservar imagens/recibos/configuração e preparar barreira de novas escritas que mantenha retorno e webhook. **Não reutilizar sem ajuste/revisão o helper de manutenção antigo**: ele permite `/api/infinitepay/return`, mas bloqueia `/api/infinitepay/webhook`. Qualquer tratamento novo deve ser ensaiado antes de executar. Sem continuidade de callbacks comprovada, manter NO-GO operacional.
4. Em etapa explicitamente autorizada, executar somente Alembic0085→0086 com imagem migrate fixa e sem dependências automáticas; depois API compatível antes da web, usando Compose com projeto/arquivo/overlays exatos. Não atualizar workers/Redis/DB/Nginx binário ou recursos de terceiros. Admitir somente a recarga do nginx Markina necessária à barreira/upstreams, no plano aprovado. Saúde/schema/configuração divergente interrompe a abertura de escritas.
5. Validar capacidade do cofre, ownership A/B, ausência de material mestre fora API, PIX manual, retomada legada, callback e webhook. Confirmar custódia externa. Só após publicação bem-sucedida o proprietário habilita PIX na InfinitePay. Nenhum checkout/pagamento real sem autorização própria. Registrar recibos e só então considerar sincronização/arquivo das changes.

## Rollback

Preservar schema aditivo, snapshots, ciphertext, keyring e pagamentos legítimos. Não fazer downgrade/restore antigo automático nem reemitir links. Antes de uso gerido/misto, retorno às imagens antigas só após verificar ausência de estado novo relevante. Depois de qualquer adoção nova, API antiga #260 não é recuperação completa: manter imagem compatível0086 e callbacks/conciliação ou correção progressiva com escritas restritas. Falha sem recuperação compatível/segregação ensaiada mantém NO-GO.

## Estado após preparação inicial — anterior ao provisionamento humano

GO para continuar a preparação. Sem migration, restart, troca de containers, habilitação de PIX ou mutação financeira na Oracle. Chave mestra/backup reais ainda ausentes; somente preparador sem segredo instalado. Homologação completa, backup real restaurável, guarda externa, barreira preservando webhook e imagens alvo/recuperação são gates ainda pendentes. Não declarar publicação pronta enquanto faltar qualquer um.

## Continuidade após participação do proprietário — 22/10/2026, 09:49 São Paulo

O proprietário executou o preparador e confirmou que guardou a senha. Verificação somente de metadados: material ativo e backup cifrado existem, ambos0600/ownerubuntu, link ignorado pelo Git correto. Não foi lido/imprimido o material mestre. Backup cifrado copiado para `%USERPROFILE%/Documents/Pick-your-Pic Backups/integration-secrets-backup-20261022.json`; SHA256 servidor/PC idêntico: `3a95f51f4f675b4b80fdd9b8f38c7b2df537caf0aa7686f3af682295f83d4247`. O preparador verificou o backup com a senha antes de persistir o material ativo. A API ativa não foi recriada e ainda não carregou esse keyring.

### Imagens finais nativas, sem atualização de dependências

As duas imagens foram construídas em ARM64 na Oracle, a partir do Git imutável d794 e das imagens efetivamente publicadas. Build limitado a1CPU/3GiB, sem trocar tags/containers ativos. API contém app/migrations/tests do candidato, conservando todas as60distribuições e Python3.13.16. Web foi reconstruída com o mesmo runtime Node24.22.1/Next16.4.2/React19.3.1/ReactDOM19.3.1 da base publicada. Comparação nativa aprovada; não incorporou PR261. Imagens não foram publicadas nem selecionadas pelos serviços ativos.

| Papel | Identidade Oracle pronta para o plano |
|---|---|
| API e migrate0086 | sha256:166a4cbab9df9eccbb4ed877e342a8f30157fbdb5406517b7051568c52a7a04e |
| Web | sha256:68a3267b1d7cd1fdc72fca58b5a02faeb981d50ef0fb5c038ba40dd598e4d4f2 |

Arquivo-fonte de runtime transferido por Git archive:7045120bytes, SHA256 `f70656689de0b216b596e39b29cbcb945e1df8e5b4183a33b25148abdf629818`. Contexto exclusivo `/var/lib/markina-gallery/deploy-state/payments0086-candidate-d7944bae`. Sem `.env`, material mestre ou dados reais no contexto/imagens.

### Homologação completa nativa — aprovada

Ensaio finalv6: rede interna própria, nenhuma porta publicada, PostgreSQL17 em tmpfs, API/web/nginx de identidades fixas, dois tenants inteiramente sintéticos. Nenhum segredo/canal/cliente de produção foi reutilizado. Chaves sintéticas somente nas instâncias da API; web/migrate/DB/nginx sem material mestre. Produção permaneceu com os mesmos IDs/StartedAt dos15serviços. Todos os containers criados pelo ensaio foram parados; tmpfs descartou bancos sintéticos. Não houve modificação de recursos de terceiros.

Passaram: cadeia Alembic0084→0085→0086; HTTP por nginx e páginas compiladas da web; guards de cliente; cadastro A/B com senha real de fixture e OTP sandbox cifrado/decriptado pelo harness, sem bypass dos handlers de confirmação/ownership; rejeição401 de desafio de A usado por B; isolamento de status/InfiniteTag; PIX manual disponível; checkout misto com foto e link preservados no Carrinho; tentativa pendente ausente de Compras; acesso cruzado404; troca da chave A conservando referência histórica da compra; desconexão B preservando A e PIX manual; desistência visual; PIX tardio e webhook duplicado com uma confirmação/receipt e uso da chave original.

Somente a fronteira HTTP externa InfinitePay foi simulada com MockTransport. O estado do provedor sintético é compartilhado entre réplicas, sem consultar o estado interno para inventar aprovação. Nenhum request real à InfinitePay ou pagamento real. Limite de requisições da fixture final é30 para acomodar probes repetidos da troca; não se trata de validação de rate limit nem de mudança na produção. A regressão do limite continua comprovada nos testes específicos/CI anteriores.

Barreira final testada pelo renderizador `scripts/render_payments0086_ingress.py`: três testes unitários aprovados e ensaio nativo com principal realmente parada e substituída. Saúde200, escrita503, webhook inicial400 para retry; depois retorno303/webhook200 por uma API0086 temporária enquanto a principal estava parada; principal nova com outro ID; retorno ao upstream principal; parada da temporária; remoção da barreira e web200. Nenhuma alteração no helper de manutenção legado, workflow0084, allowlist ou manifesto.

Falhas intermediárias foram do harness, sem alteração de runtime da aplicação: arquivo auxiliar http.py sombreava biblioteca padrão; expectativa de403/404 corrigida para401 neutro definido pelo handler; rótulo Compose herdado da imagem confundia o inventário e foi sobrescrito somente nos containers sintéticos; stub externo inicialmente tinha estado por processo e foi corrigido para representar estado externo compartilhado entre réplicas. v4 aprovou fluxo financeiro; v6 aprovou fluxo e troca com barreira. Não apresentar tentativas anteriores como homologação concluída.

### Backup real de banco e restauração — aprovados

Dump consistente via pg_export_snapshot/pg_dump, schema0084,110493443bytes. Fonte consultada em transação read-only; restore em PostgreSQL17 próprio com networknone/tmpfs, sem conectar aplicação ou enviar mensagens. Contagens e digest de todas as96tabelas idênticos ao snapshot. Clone parado ao final; nenhum restore, restart ou migration no banco ativo.

Referência privada no servidor: `/var/lib/markina-gallery/deploy-state/payments0086-pre-migration-backup-20261022/pre-0086.dump`, SHA256 `0aded4b5f46e94db85553773410dc50eff76407adecd7764403041588788047a`. Arquivo0600 em diretório0700. **Este dump não está cifrado**: é uma cópia restrita no próprio servidor para esta operação; não foi transferida externamente. Não confundir com o backup cifrado da chave mestra no PC. Nenhum keyring incluído no dump; tabela do cofre ainda não existe no banco ativo. Restore automático de dump antigo permanece proibido por risco a transações posteriores.

### Inventário e sequência concreta para revisão operacional

Alvo de aplicação continua d7944baef5191ade6ac26fa86cd631bd5ad464d1, igual ao candidato aprovado CI788; main conferida novamente. Produção ainda21b89c3/schema0084, API/web saudáveis, sem reinício. Não publicar por meio do workflow0084. Nenhuma ativação de PIX no provedor, compra real ou troca da APIKey do fotógrafo foi executada.

1. Sob lock comum `/var/lib/markina-gallery/deploy-state/production-release.lock`, renovar SHA/schema/IDs/configuração e recusar divergência/tentativa pendente. Preservar imagens21 e recipientes de rollback; salvar configuração nginx Markina e estado de release. Registrar esta autorização específica de execução antes da primeira mutation. Projeto markina-gallery/Compose docker/docker-compose.yml; domínio e porta127.0.0.1:8080 existentes. Sem nova porta/subdomínio.
2. Manter API antiga atendendo retornos durante barreira e migration aditiva. Barreira inicial permite saúde/retorno e responde400 a webhook para retry, bloqueando novas operações503. Não afirmar continuidade se nginx-t/health/probes falharem. O nginx afetado é exclusivamente o container Markina, nunca o proxy compartilhado externo.
3. Usar overlay externo com imagens exatas desta tabela para api/web/migrate e APP_VERSION=d794, conservando os cinco overlays existentes: branding.compose.yml externo, docker-compose.raw-development.yml, docker-compose.preview-adjustment.yml, docker-compose.system-monitor.yml e system-monitor.compose.yml externo. Checkout limpo em Git imutável; nenhum .env alterado. Executar migrate explicitamente com run--rm--no-deps--pullnever, Alembic upgrade20261021_0086, lock_timeout5s/statement_timeout120s. Migrate não recebe keyring. Recusar revisão diferente da cadeia inspecionada.
4. Depois de schema0086, iniciar somente uma API temporária interna, nome `payments0086-api-canary`, da imagem166a4c, pelo mesmo serviço/configuração segura API e sem dependências. Conferir saúde/versão/capacidade do cofre sem revelar chave. Apontar a barreira à temporária e verificar retorno/webhook; só então recriar a API principal com imagem166a4c e depois web68a326, sem build/pull/dependências. Manter callbacks na temporária durante essa troca; conferir principal antes de retornar o upstream a api. A instância temporária não é worker e não tem porta pública.
5. Validar schema, IDs, saúde HTTPS, rotas autenticadas recusando acesso anônimo e material mestre somente na API. Restaurar ingresso normal, confirmar saúde e só então parar/remover exclusivamente a temporária identificada por ID/rótulo, sem volumes compartilhados. Registrar recibos/overlays ativos/imagens/versão e retirar marcador próprio ao final. Sem downgrade ou restauração automática de banco. Após qualquer estado0086/cofre em uso, falha exige API compatível/continuidade de callbacks e correção progressiva; binário #260 não é rollback completo. Somente após sucesso o proprietário habilita PIX na InfinitePay e configura/rotaciona credenciais pela UI se desejar.

Imagens de recuperação da fase anterior são as antigas92bcf865/c1be0a01 já inventariadas; candidata compatível0086 é a imagem166a4c preservada. O plano não promete rollback de defeito de código pela mesma imagem: após adoção nova, eventual defeito exige correção progressiva com emissões bloqueadas e callbacks compatíveis.

Recibos verificáveis no deploy-state: payments0086-native-images.json, payments0086-native-distributions.json, payments0086-native-homolog-v6-result.json, payments0086-real-backup-restore-result.json. Cópia sanitizada agregada em C:/codex-data/tmp/payments0086-prepublication-receipts.json. Matriz de referência/limitações preservada acima.

**Decisão:** preparação técnica e guarda externa concluídas; GO para revisão/solicitação de autorização da operação concreta0084→0086/API/web com temporária interna. Execução permanece pendente dessa autorização operacional específica, conforme release-plan.md. Não declarar deploy ou cofre ativo na aplicação publicada.

## Resultado posterior à autorização expressa

O proprietário autorizou a operação acima (“Autorizado”, reiterada por “Então continue”). Inventário renovado sem divergência; execução concluída22/10/2026,10:07:37SãoPaulo. A decisão anterior é histórica: schema0086 e API/web d7944bae agora estão publicados. Nenhuma nova autorização era necessária para repetir o mesmo escopo aprovado. Recibo atual, verificações e limites em `publication-20261022.md`; PIX InfinitePay não foi habilitado pelo executor e nenhum pagamento real foi criado.
