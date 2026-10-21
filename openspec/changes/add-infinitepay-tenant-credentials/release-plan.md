# Plano coordenado API/web — sem execução

## Dependências e escopo

- PR pai #260: `feature/fix-infinitepay-checkout`, SHA `0959c64f00c60e6674675a9d90b43f0d7f9428b7`, aberto/draft e não mesclado na verificação de 21/10/2026. Esta branch `codex/infinitepay-tenant-credentials` parte desse SHA e terá PR draft contra a branch pai, para revisão somente do delta. Integrar #260 primeiro, retargetar este PR para `main` e repetir CI no SHA candidato após revisão humana; não mesclar automaticamente.
- PR próprio draft [#262](https://github.com/conradodeita/markina-gallery/pull/262), branch `codex/infinitepay-tenant-credentials`. O SHA exato a publicar será o head aprovado desse PR, registrado junto com o head pai e as imagens/digests no pedido operacional; qualquer alteração posterior exige rever os resultados afetados. Primeiro commit de implementação `ccf59ea101f0cdcca2bac8d00f426b457d6bdff0`; correções de testes/evidências posteriores não autorizam outro candidato automaticamente.
- Serviços afetados: `api` e `web`; schema PostgreSQL via `migrate` em etapa autorizada. Keyring somente na API. Sem alteração de dependências/runtime Python, workers, Redis, Nginx, serviços faciais, RAW ou recursos de outros projetos.
- Nenhuma ação deste plano foi executada em Oracle. Compra real `e2194ce5` permanece intocada; esta funcionalidade não a reconcilia nem migra seu binding.

## Gates antes de solicitar publicação

1. Revisão humana de ambos os PRs, CI final verde no candidato integrado, sem segredo em histórico/artefatos e sem conflito com o executor da manutenção Python. Não incorporar alterações de runtime dessa outra missão.
2. Aprovação específica do proprietário para inventário remoto, backup, provisão do material mestre, migration e publicação. Inventariar projeto `markina-gallery`, arquivo `docker/docker-compose.yml`, imagens/digests atuais, revisão Alembic, domínio/portas já existentes e capacidade de backup. API continua apenas na rede interna/porta 8000; web usa suas rotas existentes; não criar exposição, domínio ou porta nova.
3. O workflow atual de release API/web proíbe migrations. Não ampliar allowlist/manifests ou acionar seu deploy esperando que aplique 0085. Definir e aprovar separadamente uma execução coordenada e controlada da migration, com inventário/backup e barreira para novas escritas, antes de escolher qualquer automação de publicação. Esta pendência impede tratar o workflow atual como botão de publicação desta change.
4. Ensaiar o candidato em homologação isolada autorizada com dois tenants sintéticos, keyring sintético e restore. Validar cadastro, substituição, desconexão, versões de compras pendentes, ausência de chave mestra, callbacks tardios e PIX. Não usar credenciais de produção nesse ensaio.

## Ordem autorizável de publicação

1. Preservar imagens/digests anteriores e binário candidato compatível, dump PostgreSQL e backup cifrado separado do keyring. Verificar restauração e acesso restrito, sem exibir variáveis resolvidas.
2. Preparar externamente `INTEGRATION_SECRETS_ENV_FILE` com as três variáveis descritas em `operations.md`, somente na API. Não incluir a API Key do fotógrafo nesse arquivo; seu cadastro será feito pela UI. Não configurar chave mestra via Git, frontend, imagem ou argumentos.
3. Impedir novas escritas financeiras durante a troca autorizada, conforme plano operacional aprovado, preservando pendências e acesso ao verificador compatível. Aplicar a cadeia necessária até `20261020_0085` sobre revisão inspecionada; 0085 é aditiva, mas o binário novo exige o schema antes de servir requisições.
4. Publicar primeiro a API do candidato e conferir que todas as instâncias atendem ao contrato novo; depois publicar a web do mesmo candidato, sem reiniciar serviços de terceiros. Manter a barreira de escritas durante troca/rollback, sem servir requisições com segredo a uma API antiga. A UI exige capacidade explícita `credential_storage_available=true` antes de aceitar API Key. Verificar `/health`, `/api/health`, autenticação e o card existente; respostas sem segredo e `Cache-Control: no-store`. Não imprimir `docker compose config` resolvido.
5. Em tenants sintéticos, confirmar isolamento A/B por HTTP, cadastro sem cobrança, bloqueio quando cofre ausente, preservação de PIX e chave congelada em compra de teste. Conferir que web/workers não receberam material mestre. Somente depois, liberar novas escritas.
6. Proprietário cadastra a própria chave exclusivamente na interface HTTPS autenticada. UI deve mostrar cadastrada/validação remota indisponível. Conferência de recebedor/cartão no provedor e qualquer pagamento real exigem execução/autorização próprias; salvar configuração não dispara cobrança.

## Rollback e transações legítimas

- Antes de adoção gerida: pode restaurar imagens anteriores compatíveis com #260, conservando schema aditivo. Não executar downgrade de banco como rollback padrão.
- Após qualquer cadastro gerido ou compra com `credential_id`: #260 isoladamente não sabe ler o cofre. Suspender novas emissões pelo mecanismo autorizado, preservar ciphertext, keyring, snapshots e banco; manter API/verificador compatíveis para callbacks/conciliação. Usar imagem compatível aprovada ou correção progressiva. Não restaurar automaticamente imagens antigas incompatíveis, nem trocar a chave da compra por uma chave atual.
- Substituição não revoga versões antigas no provedor; só o titular pode fazê-lo após reconciliar suas compras. Desconexão recusa pendências. Não apagar ciphertext ou keyring para resolver incidente. Downgrade com estado gerido é recusado pela migration.
- Restore de banco exige keyring das versões/ambiente originais. Preservar novas transações legítimas ao escolher ponto de restauração; restaurar um dump antigo exige reconciliação antes de liberar qualquer compra. Nenhuma recuperação reemite/cancela ou libera pagamentos ambíguos automaticamente.
- Rotação mestra tem dry-run e apply por tenant em `operations.md`. Não descartar versão antiga necessária a envelope, desafio OTP ainda aberto ou backup retido.

## Decisão

Implementação local/PR revisável e CI aprovado permitem solicitar revisão e autorização de integração. Publicação continua NO-GO até revisão humana, ensaio autorizado, inventário/backup, material mestre e plano autorizado de migration coordenada. Recuperação de `e2194ce5` continua NO-GO sem evidência financeira InfinitePay e autorização específica. CI verde não autoriza nenhuma dessas operações.
