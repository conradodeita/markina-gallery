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

## Estado fiel

GO para continuar a preparação. Sem migration, restart, troca de containers, habilitação de PIX ou mutação financeira na Oracle. Chave mestra/backup reais ainda ausentes; somente preparador sem segredo instalado. Homologação completa, backup real restaurável, guarda externa, barreira preservando webhook e imagens alvo/recuperação são gates ainda pendentes. Não declarar publicação pronta enquanto faltar qualquer um.
