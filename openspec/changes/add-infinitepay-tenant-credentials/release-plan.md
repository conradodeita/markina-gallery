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

## Etapa separada de autorização da migration — preparada, não executada

O mecanismo existente é autorização humana explícita por operação e inventário, seguida de Alembic na imagem aprovada do serviço `migrate`, no projeto e Compose nomeados. O release API/web atual não executa nem autoriza essa etapa. Não alterar seus manifests, allowlists, revisão esperada ou hashes para liberar 0085.

Antes de solicitar execução, o operador deverá preencher um registro auditável com: referência da autorização do proprietário; ambiente e janela; SHA integrado/revisão humana/URL do CI verde; revisão Alembic observada; imagem/digest exato da API e de `migrate`; imagens/digests anteriores de API/web; subdomínio, portas e recursos exclusivos; responsáveis; referência/hash do dump e resultado de restore isolado; referência do backup seguro do keyring (nunca seu conteúdo); barreira de escritas e procedimento de callbacks/conciliação; critérios de interrupção e identidade da imagem compatível de recuperação. Inventário/imagens atuais da Oracle permanecem **não coletados nesta missão**, por proibição explícita; nenhuma identidade histórica é assumida como atual.

Com todos os campos revisados, solicitar separadamente autorização para: (A) inventário/backup/provisão mestre; (B) aplicação da cadeia inspecionada até `20261020_0085` com serviço/imagem fixados, sem iniciar API/web por dependência automática; (C) troca API e web e verificação controlada. Registrar início/fim, revisão antes/depois, identidade da imagem e status sem parâmetros/segredos. Qualquer revisão inesperada, backup não restaurável, chave mestra indisponível ou falha de saúde interrompe a sequência antes de abrir novas escritas. Esta documentação não é uma autorização e não fornece comando de execução remota automática.

## Matriz de compatibilidade e recuperação por identidade

| Schema/binário | Uso permitido no plano autorizado |
|---|---|
| 0084 + API antiga | Estado anterior; não servir web que coleta credenciais |
| 0084 + API nova | Incompatível: não iniciar atendimento antes de 0085 |
| 0085 + API antiga #260, sem adoção gerida | Retorno possível por imagens/digests inventariados; manter schema aditivo e retirar web nova antes da API |
| 0085 + API antiga #260, após adoção gerida | Não usar como restauração completa: binário não lê cofre e pode interpretar configuração gerida incorretamente |
| 0085 + API/web novas + keyring correto | Candidato operacional; entrada gerida exige capacidade explícita e segregação por tenant |
| 0085 + API compatível sem keyring | Novos cartões geridos indisponíveis; conservar pendências e restaurar material mestre autorizado; não substituir por chave de outro tenant |

Após adoção gerida, a identidade de recuperação deverá ser um digest aprovado compatível com 0085 e com o cofre, preservado antes de abrir o cadastro. Se o defeito impedir manter essa API, a barreira operacional aprovada deverá bloquear preparação de novos cartões e escrita de configuração, enquanto callbacks/conciliação ficam em instância compatível segregada. Não apontar essas rotas ao #260 isolado, nem desligar master key para tentar bloquear emissão: isso também impede verificar pendências. Se a separação de rotas/identidades não estiver ensaiada e documentada no pedido operacional, interromper novas operações afetadas e optar por correção progressiva; não alegar rollback completo. PIX manual só permanece liberado se a aplicação financeira e o acesso ao schema estiverem saudáveis e as proteções contra duplicidade continuarem ativas.

## Rollback e transações legítimas

- Antes de adoção gerida: pode restaurar imagens anteriores compatíveis com #260, conservando schema aditivo. Não executar downgrade de banco como rollback padrão.
- Após qualquer cadastro gerido ou compra com `credential_id`: #260 isoladamente não sabe ler o cofre. Suspender novas emissões pelo mecanismo autorizado, preservar ciphertext, keyring, snapshots e banco; manter API/verificador compatíveis para callbacks/conciliação. Usar imagem compatível aprovada ou correção progressiva. Não restaurar automaticamente imagens antigas incompatíveis, nem trocar a chave da compra por uma chave atual.
- Substituição não revoga versões antigas no provedor; só o titular pode fazê-lo após reconciliar suas compras. Desconexão recusa pendências. Não apagar ciphertext ou keyring para resolver incidente. Downgrade com estado gerido é recusado pela migration.
- Restore de banco exige keyring das versões/ambiente originais. Preservar novas transações legítimas ao escolher ponto de restauração; restaurar um dump antigo exige reconciliação antes de liberar qualquer compra. Nenhuma recuperação reemite/cancela ou libera pagamentos ambíguos automaticamente.
- Rotação mestra tem dry-run e apply por tenant em `operations.md`. Não descartar versão antiga necessária a envelope, desafio OTP ainda aberto ou backup retido.

## Decisão

Implementação local/PR revisável e CI aprovado permitem solicitar revisão e autorização de integração. Publicação continua NO-GO até revisão humana, ensaio autorizado, inventário/backup, material mestre e plano autorizado de migration coordenada. Recuperação de `e2194ce5` continua NO-GO sem evidência financeira InfinitePay e autorização específica. CI verde não autoriza nenhuma dessas operações.

Evidência técnica: commit `8465c57d265ed8add463ebf9841b20285fcff4fc`, CI integral [39545805272](https://github.com/conradodeita/markina-gallery/actions/runs/39545805272) aprovado em 21/10/2026. GO para solicitar revisão/autorização de integração, mantendo #260 → main primeiro, depois retarget #262 e CI do candidato integrado. Não é autorização de merge nem declaração de CI contra uma main futura. O encerramento documental subsequente mantém a mesma implementação; o SHA/CI exatos do head final ficam no corpo do PR #262 após conferência, sem presumir aprovação. Nenhuma imagem/digest atual da Oracle foi inferida desses resultados.
