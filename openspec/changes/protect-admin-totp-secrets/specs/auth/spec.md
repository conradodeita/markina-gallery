## ADDED Requirements

### Requirement: Segredo TOTP cifrado em repouso

O sistema SHALL cifrar TOTP administrativo em envelope autenticado/versionado, com chave externa e AAD vinculada ao ambiente e ao administrador. Novas escritas SHALL usar envelope. Texto claro legado SHALL permanecer somente até o contract; ao concluir, o legado SHALL ser NULL e o dual-write MUST estar desligado. Falhas criptográficas SHALL ser fechadas e sanitizadas.

#### Scenario: Cadastro ou leitura após a etapa contract

- **WHEN** uma credencial administrativa é criada ou carregada depois da etapa contract
- **THEN** o valor bruto só existe em memória para cálculo TOTP e o banco contém envelope válido, sem valor claro legado

#### Scenario: Leitura durante compatibilidade com binário antigo

- **WHEN** a configuração dual-write está explicitamente ligada e o schema está na janela de expansão
- **THEN** a aplicação nova mantém o plaintext legado sincronizado para leitores antigos, lê a fonte compatível definida pelo modo e mantém o envelope validável; nenhuma etapa contract executa nesse modo

#### Scenario: Binário legado grava durante a janela de expansão

- **WHEN** um consumidor antigo atualiza o plaintext legado enquanto dual-write está ligado
- **THEN** a aplicação nova trata esse valor como fonte da janela, valida o envelope existente e sincroniza o envelope no próximo flush, mantendo os dois leitores funcionais

#### Scenario: Keyring indisponível

- **WHEN** o keyring ativo está ausente, inválido, pertence a outro ambiente ou não contém a chave identificada pelo envelope
- **THEN** a operação protegida é recusada de modo sanitizado, sem fallback inseguro nem alteração do dado

#### Scenario: Envelope adulterado ou copiado

- **WHEN** o ciphertext, identificador de chave, versão, ambiente ou UUID do administrador não corresponde ao AAD
- **THEN** a decifragem falha sem revelar material ou detalhe criptográfico ao cliente

### Requirement: Migração recuperável de segredo TOTP

Migrações SHALL usar etapas expand/contract, preservar o fator e ser idempotentes. A expansão SHALL adicionar o envelope e backfill sem alterar a coluna legada. A etapa contract SHALL limpar plaintext somente após confirmação de todos os consumidores novos e dual-write desligado. Uma falha de validação MUST NOT apagar ou alterar parcialmente a fonte. Downgrade SHALL restaurar o plaintext a partir de todos os envelopes válidos na mesma transação antes de qualquer rollback para binário antigo.

#### Scenario: Expansão com dados legados válidos

- **WHEN** `0091` encontra segredos legados válidos e keyring compatível
- **THEN** preserva `totp_secret` legível pelo binário antigo e grava envelope autenticado equivalente em `totp_secret_envelope`

#### Scenario: Contract após atualização dos consumidores

- **WHEN** todos os leitores/escritores estão atualizados, dual-write está desligado e cada envelope/contexto foi validado
- **THEN** `0093` reconcilia qualquer escrita legada válida ainda divergente, limpa o valor claro legado atomicamente e mantém os envelopes e o mesmo fator

#### Scenario: Última escrita legada antes do contract

- **WHEN** a coluna legada contém uma atualização válida feita durante a convivência e o envelope anterior é válido
- **THEN** `0093` cifra a versão legada mais recente e só a limpa depois de validar todo o conjunto, sem descartar a alteração

#### Scenario: Downgrade para binário legado

- **WHEN** o rollback exige binário que lê plaintext
- **THEN** a reversão de `0093` autentica/decifra os envelopes cujas colunas legadas foram limpas e restaura `totp_secret` antes de voltar o binário, preservando plaintext legado que ainda seja mais recente e sem escrita parcial

#### Scenario: Upgrade repetido ou segredo já protegido

- **WHEN** a migration é reexecutada ou encontra envelope válido já protegido
- **THEN** não gera nova cifra desnecessária nem altera o valor lógico do segredo

#### Scenario: Falha de chave ou dado inválido

- **WHEN** o keyring está indisponível, o envelope existente é inválido ou o contexto não corresponde ao administrador/ambiente
- **THEN** a transação aborta sem perda, limpeza parcial, fallback para ciphertext inválido ou mensagem contendo segredo

#### Scenario: Configuração dual-write inválida

- **WHEN** `ADMIN_TOTP_LEGACY_DUAL_WRITE` não é `true` nem `false`
- **THEN** a leitura/escrita protegida e a migration contract falham fechadas

### Requirement: Rotação explícita da chave TOTP

O sistema SHALL identificar a chave de cada envelope, suportar rotação controlada sem invalidar TOTP e manter a chave antiga disponível até todos os envelopes serem recifrados e conferidos.

#### Scenario: Rotação concluída

- **WHEN** todos os envelopes foram recifrados com a chave ativa e decifrados/verificados
- **THEN** autenticação continua aceitando os mesmos fatores e a chave anterior pode ser removida em operação separada autorizada

#### Scenario: Rotação incompleta

- **WHEN** algum envelope não pode ser lido ou validado
- **THEN** a operação preserva o registro e mantém necessária a chave anterior

### Requirement: TOTP de uso único com proteção contra replay

O sistema SHALL manter os limites atuais de janela, desafio, rate limit e respostas neutras e MUST aceitar cada passo temporal TOTP no máximo uma vez por administrador.

#### Scenario: Código TOTP válido novo

- **WHEN** o código corresponde a passo ainda não consumido e o desafio está válido
- **THEN** o passo é consumido atomicamente e a sessão é criada segundo a autorização vigente

#### Scenario: Código TOTP reutilizado ou submetido simultaneamente

- **WHEN** o passo já foi usado ou duas requisições tentam consumi-lo simultaneamente
- **THEN** no máximo uma autenticação é aceita e a outra é recusada/auditada sem sessão

### Requirement: Código de recuperação TOTP de uso único

O sistema SHALL permitir códigos aleatórios de recuperação para administradores privilegiados, mostrar cada lote somente uma vez após reautenticação recente, guardar somente hashes e consumir cada código atomicamente uma única vez com limites de tentativa.

#### Scenario: Emissão de códigos

- **WHEN** administrador autenticado conclui reautenticação recente com TOTP válido e solicita códigos
- **THEN** sistema invalida lote anterior, guarda hashes do novo lote e revela os códigos apenas naquela resposta

#### Scenario: Recuperação com código válido

- **WHEN** o código de recuperação válido é enviado ao desafio administrativo ainda válido
- **THEN** exatamente um código é consumido atomicamente e o login segue criando sessão administrativa com MFA satisfeita

#### Scenario: Código inválido, repetido ou concorrente

- **WHEN** o código é inválido, já consumido, revogado ou concorre com outro uso
- **THEN** acesso é recusado com resposta neutra, tentativa limitada e auditoria sanitizada

#### Scenario: Regeneração requer fator atual

- **WHEN** o administrador tenta gerar novo lote sem sessão ativa e TOTP recente válido
- **THEN** o sistema não revela códigos nem invalida os códigos existentes
