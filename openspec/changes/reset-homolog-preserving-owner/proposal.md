## Why

O proprietário solicitou zerar os dados de teste no servidor Oracle após a migração para `markina.pickyourpic.com.br`, sem criar dump, conservando somente `conradodeita@gmail.com`, seu acesso e suas configurações. O inventário pós-deploy encontrou cinco fotógrafos/admins; a rotina atual recusa múltiplos fotógrafos e preserva todas as contas, portanto não atende ao resultado solicitado.

## What Changes

- Introduzir um procedimento exclusivo de reset de homologação que identifica a conta proprietária e seu único vínculo ativo antes de qualquer exclusão.
- Remover todos os dados operacionais de todas as contas, incluindo clientes, galerias/pastas/fotos, compras/pagamentos de teste, mídia, dados faciais e filas relacionadas.
- Remover os quatro demais fotógrafos/admins e suas configurações/vínculos, preservando integralmente conta, senha/TOTP, sessões válidas, privilégios e preferências da proprietária.
- Preservar a Evolution conectada, segredos externos, configuração InfinityPay/PIX/branding/notificações/processamento do proprietário e observabilidade administrativa global.
- Exigir inventário sanitizado, schema fechado, SHA publicado conhecido, pausa conferida de todos os writers Markina, ensaio PostgreSQL e validação de preservação antes/depois. A limpeza antiga continua recusando instalações multitenant.
- Não criar backup novo. Após o reset integral, excluir somente os 164 dumps `.dump` antigos do diretório fixo da Markina que foram inventariados e autorizados separadamente; snapshots de marca/configuração e outros arquivos permanecem. O reset não desfaz pagamentos externos na InfinityPay.

## Capabilities

### New Capabilities

- `deployment-operations/owner-reset`: reset explícito de dados de teste e contas adicionais em homologação, conservando a identidade e as configurações do proprietário.

### Modified Capabilities

Nenhuma: o novo procedimento é distinto da limpeza operacional existente e não modifica seus gates.

## Impact

- Código CLI de manutenção, script de operação e workflow protegido `homolog`; sem endpoint público nem migration de schema.
- Somente banco/Redis/volumes do projeto `markina-gallery`, checkout `/opt/markina-gallery`, entrada local `127.0.0.1:8080`, domínio `markina.pickyourpic.com.br`.
- Janela breve de indisponibilidade da API Markina enquanto seus writers estão parados. Evolution, NPM compartilhado, ClearBudget, Portainer, DNS, certificados e demais projetos permanecem fora da operação.
- Operação destrutiva sem recuperação por dump novo, autorizada pelo proprietário em 13/10/2026. Execução depende do inventário e das guardas, não de dispensar a segurança da rotina anterior.
