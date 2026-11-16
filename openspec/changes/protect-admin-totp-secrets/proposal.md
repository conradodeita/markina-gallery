# Proposal

## Why

`AdminUser.totp_secret` está persistido como texto (`String(128)`) e é lido diretamente pelo endpoint `/auth/admin/totp`. O mandato SaaS exige cifrar esse fator em repouso sem forçar novo cadastro TOTP, manter chaves fora do banco e impedir perda de acesso administrativo.

## What Changes

- Cifrar envelopes TOTP com AES-256-GCM, versão e identificador da chave; autenticar o ambiente e o UUID do administrador como contexto.
- Obter um keyring TOTP dedicado exclusivamente de configuração secreta externa, separado das chaves de integração e biometria; falhar fechado fora de testes quando ausente ou inválido.
- Migrar dados existentes por expansão aditiva: preencher envelopes e preservar a coluna legada enquanto houver consumidores antigos; limpar o texto claro em migration contract separada somente após atualizar/drenar todos os consumidores. Downgrade restaura primeiro o plaintext a partir dos envelopes e valida todos os registros transacionalmente.
- Durante a janela de convivência, permitir dual-read/write da coluna legada sob configuração explícita; fora dela, persistir somente envelope cifrado. Suportar rotação explícita, testes de chave anterior/ativa e observabilidade sem material secreto.
- Persistir o último intervalo TOTP aceito e recusar replay, mantendo a janela já especificada e os limites de tentativa/auditoria existentes.
- Emitir códigos administrativos de recuperação de uso único, guardar somente hashes resistentes a brute force e permitir regeneração mediante sessão autenticada e TOTP recente.
- Documentar recuperação operacional de chave e de acesso, incluindo dependência do keyring para restauração de backups.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `auth`: segredo TOTP cifrado em repouso, proteção contra replay e recuperação com códigos de uso único.
- `deployment-operations`: configuração e rotação do keyring TOTP externo e restauração compatível de backups.

## Impact

Backend de autenticação, provisionamento/seed, migrations Alembic, testes com PostgreSQL, configuração documentada e superfície `Configurações` para emitir/regenerar códigos. Esta change não inclui deploy, alteração de configuração real, cadastro/reset da conta de produção nem troca de fator por terceiro.
