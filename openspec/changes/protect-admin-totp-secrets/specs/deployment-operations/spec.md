## ADDED Requirements

### Requirement: Keyring TOTP externo e recuperação de backups

A operação SHALL manter keyring TOTP dedicado fora do banco e separado de outras chaves. Procedimentos de backup/restore SHALL preservar, sob acesso restrito, as versões de chave necessárias para decifrar o snapshot e SHALL validar recuperação em ambiente isolado antes de descartar a chave antiga.

#### Scenario: Inicialização sem chave válida

- **WHEN** ambiente protegido não possui keyring válido ou o ambiente do keyring diverge de `APP_ENV`
- **THEN** operações TOTP falham fechadas e o serviço informa somente estado operacional sanitizado

#### Scenario: Restauração de backup

- **WHEN** um banco é restaurado em ambiente isolado
- **THEN** equipe confirma presença autorizada das versões de chave correspondentes e valida decifragem de fixture sintética antes de considerar restore íntegro

#### Scenario: Remoção de chave antiga

- **WHEN** operador solicita remover uma versão antiga
- **THEN** a operação recusa até que inventário prove zero envelopes referenciados e restore compatível com a chave ativa

### Requirement: Migração TOTP compatível com versões antigas

O rollout SHALL usar migração expand/contract. A etapa expand mantém a coluna legada legível pelos processos antigos e acrescenta envelope cifrado. A etapa contract só SHALL limpar plaintext depois que todas as instâncias/API/workers que leem o formato antigo tiverem sido atualizados e drenados, e dual-write estiver desligado. Rollback SHALL restaurar plaintext antes da volta a um binário antigo.

#### Scenario: Instância antiga durante expansão

- **WHEN** um processo antigo lê `admin_user.totp_secret` após `0091`
- **THEN** a coluna permanece com o valor legado compatível; a coluna envelope adicional é ignorada sem alterar a autenticação antiga

#### Scenario: Contract com consumidor antigo ativo

- **WHEN** o inventário operacional ainda identifica consumidor antigo, o backup/restore não foi comprovado ou dual-write permanece habilitado
- **THEN** o operador não executa `0093` e mantém o rollout bloqueado até os gates operacionais passarem; se dual-write estiver habilitado, a própria migration também recusa limpar plaintext

#### Scenario: Rollback de aplicação após contract

- **WHEN** uma reversão usa binário antigo que exige plaintext
- **THEN** operador para o binário novo e executa downgrade transacional que restaura plaintext antes de voltar o binário antigo; nenhuma reversão automática é inferida
