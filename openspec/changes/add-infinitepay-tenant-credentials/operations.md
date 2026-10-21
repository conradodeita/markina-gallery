# Operação do cofre InfinitePay

## Configuração preparada, sem provisão real

Somente API precisa de `INTEGRATION_SECRET_ENV` exatamente igual a `APP_ENV`, `INTEGRATION_SECRET_ACTIVE_KEY_ID` e `INTEGRATION_SECRET_KEYS`. O último é JSON de identificadores para chaves aleatórias de 32 bytes codificadas em base64. Não gerar valores nesta documentação nem colocar exemplos de chave em `.env.example`, CI ou logs. Key-id é metadado, não segredo. A chave de API do fotógrafo será enviada uma única vez pelo formulário HTTPS autenticado após publicação autorizada.

Compose carrega essas três variáveis somente no serviço `api`, pelo arquivo externo indicado em `INTEGRATION_SECRETS_ENV_FILE` (padrão `.env.integration-secrets`, ignorado pelo Git). O operador deverá criá-lo fora do checkout com permissão restrita após autorização de publicação, sem imprimir `docker compose config` resolvido. Esta missão não cria o arquivo nem provisiona chaves reais; web, workers e migrate não recebem o keyring.

O keyring é separado das chaves OTP, facial e do banco. Configuração ausente ou inválida faz operações geridas falharem fechadas; não usar chaves de outra conta, chaves padrão ou fallback legado. O servidor não valida remotamente a API Key ao salvá-la, pois o contrato público consultado em #260 não documenta validação isolada não financeira. Cadastro não significa validação pelo provedor.

## Backup e restauração

O backup PostgreSQL contém somente ciphertext e metadados. Guardar o keyring em backup cifrado independente, com acesso operacional restrito; não anexá-lo ao dump, imagem Docker ou artefato de CI. Um restore exige todas as versões de chave ainda referidas, o ambiente original e o schema compatível. Restaurar banco sem keyring deixa cartão gerido indisponível e preserva pagamentos para conciliação. Não mudar `APP_ENV` para contornar o AAD; restaurar produção em homologação não autoriza usar suas credenciais reais.

## Substituição e desconexão

Substituir API Key cria nova versão; a compra conserva sua referência original. Não revogar a chave anterior no provedor até reconciliar todas as suas compras. Desabilitar cartão interrompe novas emissões sem apagar segredos. Desconectar exige senha/código, nenhuma compra em estado não terminal e apaga ciphertext das versões geridas. PIX permanece separado. Reconciliação de compras legadas sem credencial continua no procedimento do #260, sem reemissão nem alteração financeira automática.

## Rotação mestra

Adicionar uma chave nova ao keyring seguro e torná-la ativa, conservando as antigas para leitura. Ensaio/dry-run precede recifragem explícita; não transmitir chaves pela linha de comando. Após conferir que nenhum envelope usa o key-id antigo e testar restore com o novo backup de material criptográfico, retirar a chave antiga conforme a política de retenção dos backups. A recifragem não muda tenant, UUID da credencial, configuração ou referências de pagamento. Nunca apagar uma chave ainda necessária por envelopes ou backups válidos.

No ambiente autorizado da API, executar `python -m app.rotate_infinitepay_secrets --tenant-id <UUID>` para dry-run. Somente após revisar o relatório e o backup, executar novamente com `--apply --confirmation <mesmo-UUID>`. O utilitário usa a mesma configuração segura do processo, serializa com checkout/configuração pelo lock da conta e faz commit atômico por tenant; erro impede o commit e retorna mensagem neutra. Repetir por tenant autorizado. Saída contém apenas UUID e contagens. Não incluir segredo no comando, ticket ou relatório. Desafios OTP ainda abertos podem usar o key-id anterior: aguardar sua expiração/limpeza antes de remover essa versão, além de verificar envelopes persistidos e backups.
