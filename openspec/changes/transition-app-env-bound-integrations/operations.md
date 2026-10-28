# Procedimento operacional — transição de ambiente

Este roteiro descreve uma operação futura; **não significa que a transição de produção esteja pronta ou autorizada para execução**. O preflight read-only `40715456515` falhou fechado após identificar `outro_ambiente_conhecido` e não produziu fingerprint completo, contagens do banco, classificação das integrações nem prova sobre dados biométricos. Não derive valores atuais de produção deste documento ou do Compose versionado.

O run read-only `40762760966` repetiu o bloqueio ao executar `orders-pilot-inventory`: depois de validar os serviços/portas, o preflight Orders parou em `ambiente_divergente:outro_ambiente_conhecido`. Esse fluxo exige `APP_ENV=production` e não é o coletor de transição; não o repita como substituto. O wrapper Orders foi instalado com sucesso no run `40760247201`, mas nenhum inventário de `APP_ENV`, fingerprint, contagem de banco ou classificação de integrações foi produzido. O coletor dedicado, seu validador de relatório e o comando restrito foram implementados localmente nesta change; ainda precisam passar CI, ser integrados em `main` e executar o primeiro inventário remoto read-only.

Esta mudança preserva o conteúdo do `access_token` e do segredo de webhook ao re-cifrá-los, e não altera `public_key`, vendedor ou classificação de conta sandbox. Ela não troca credenciais de teste por credenciais de produção nem habilita cobrança real. A configuração de credenciais reais é uma ação separada, e o proprietário será avisado antes dessa etapa.

## Pré-condições obrigatórias

1. Obter novo inventário read-only do host e banco reais, com fingerprint aprovável, SHA/schema, serviços/portas, contagens das duas classes de envelope, contagens biométricas por categoria, estado do gate live e classificação de WhatsApp, SMTP e facial. Qualquer campo ausente, consumidor desconhecido, ciphertext biométrico ou integração incompatível bloqueia a operação.
2. Produzir plano específico com origem/destino em categorias, fingerprint completo do inventário, fingerprint das contas Mercado Pago, quantidade de contas, serviços próprios afetados, janela, impacto, plano de recuperação e evidência de backup. Submeter esse plano à aprovação humana explícita antes de alterar dados ou serviços.
3. Manter `MERCADOPAGO_ALLOW_LIVE_PAYMENTS` fechado. Não criar cobranças, pedidos de teste, mensagens ou tráfego externo.
4. Preservar uma cópia cifrada e recuperável da configuração anterior no armazenamento seguro já aprovado, incluindo o keyring original e as configurações dos consumidores. A keyring não é embutida no backup de envelopes; mantê-la separada e disponível até a verificação final ou recuperação.
5. Usar exclusivamente um PostgreSQL de teste descartável, chamado `app_env_transition_test` em loopback, para o teste opcional do código. Não apontar esse teste para homologação, produção ou banco compartilhado.

## Coleta remota somente-leitura

Após CI e integração em `main`, executar o workflow manual `CI` com `operation=app-env-transition-inventory`, pelo ambiente protegido de preflight. O wrapper SSH aceitará apenas esse identificador com SHA atual de `main` e o blob revisado do script. O relatório pode conter bloqueios e fingerprint nulo; isso é evidência de inventário, não aprovação para mutação. Uma fonte ausente gera envelope sanitizado `coleta_incompleta`, sem inventário parcial nem fingerprint, e inclui apenas um código de falha de lista fechada; exceções não classificadas usam categoria genérica, sem mensagem, valor, argumento ou caminho bruto. A coleta não pausa os serviços, não lê payloads biométricos, não chama Mercado Pago/WhatsApp/SMTP e não escreve no host ou banco. Se não houver relatório válido ou houver qualquer bloqueio, interromper a preparação e registrar o resultado; não reutilizar o inventário Orders.

## Execução controlada

1. Conferir novamente o inventário completo e compará-lo byte a byte pelo fingerprint aprovado. Divergência encerra a janela sem escrita.
2. Validar que `IntegrationCipher()` lê o contexto atual e que `source.for_environment("production")` usa o mesmo keyring/chave ativa. A operação não troca `os.environ` nem introduz ou rotaciona chaves.
3. Em sessão somente-leitura, gerar `MercadoPagoTransitionPlan` e backup cifrado com `create_mercadopago_transition_plan()` e `create_encrypted_transition_backup()`. Persistir o payload cifrado fora do repositório, em armazenamento aprovado; reler, validar com `EncryptedTransitionBackup.from_payload()` e autenticar antes de prosseguir. Guardar apenas fingerprints, contagens e recibo sanitizado no log de operação.
4. Pausar graciosamente os consumidores próprios identificados pelo inventário. A matriz estática atual cita `api`, `worker`, `face-search-worker`, `face-index-worker` e `face-maintenance-worker`, mas a lista real deve vir do inventário revisado. Não parar serviços por força, não alterar recursos de outros projetos e não usar `compose down`.
5. Com uma sessão PostgreSQL nova, chamar `execute_approved_mercadopago_transition()` passando o inventário e fingerprint aprovados, o backup persistido e verificado, a confirmação `APLICAR_TRANSICAO_APP_ENV:<fingerprint-inventario>:<fingerprint-contas>`, e a lista exata de consumidores pausados. A guarda aborta antes do primeiro write se qualquer condição divergir.
6. A transação bloqueia a tabela e as linhas das contas no PostgreSQL; revalida a contagem/fingerprint, descriptografa com tenant/ID originais, recifra no destino, verifica o destino e altera somente os dois campos de envelope. Registrar fingerprints pré/pós e contagem; nunca registrar plaintext, envelopes, IDs ou tokens.
7. Atualizar a configuração dos processos somente conforme o plano aprovado e sem editar outros serviços. Integrações externas classificadas como desativadas permanecem desativadas; as não classificadas impedem o reinício com a nova configuração.
8. Verificar configuração/contextos, descriptografia, isolamento, schema, saúde e HTTPS por mecanismos read-only. Comparar contagens e registros financeiros com o inventário anterior; gate live permanece fechado. Só então retomar graciosamente os serviços do projeto.

## Recuperação

1. Manter gate live fechado e consumidores pausados. Restaurar os valores anteriores da configuração a partir da cópia cifrada e revisada; o código de recovery não altera `os.environ` ou arquivos de serviço.
2. Abrir os contextos explícitos anterior e destino com a keyring preservada; chamar `restore_mercadopago_transition_backup()` com o backup autenticado. A função valida as contas e envelopes, verifica metadados/fingerprint e restaura, em transação única, somente os dois envelopes Mercado Pago.
3. Se a recuperação falhar, manter os consumidores pausados e gate fechado, preservar a evidência e escalar. Não repetir com fingerprint alterado, não remover linhas e não editar estados financeiros.
4. Reabrir serviços somente depois de confirmar que a configuração e os envelopes pertencem ao mesmo contexto anterior, os checksums batem, dados financeiros permanecem idênticos e a saúde está normal.

## Estado nesta change

O código de cifra, backup, recovery e guardas locais foi testado com fixtures sintéticas SQLite. O PostgreSQL local específico não está configurado e nenhuma etapa de pause, persistência externa de backup, inventário de produção, alteração de configuração ou re-cifragem real foi executada. A transição operacional continua bloqueada até a evidência e a aprovação específica do plano.
