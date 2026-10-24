# Proposal

## Why

A aposentadoria local da InfinitePay está implementada, mas o caminho de release API/web recusa migrations e mudanças no Compose, enquanto o release protegido existente fixa outro alvo de schema. É necessário um procedimento revisável para publicar a aposentadoria em produção, remover apenas a configuração exclusiva da InfinitePay e preservar o histórico financeiro e os serviços compartilhados.

## What Changes

- Criar um release de produção específico para a aposentadoria InfinitePay, condicionado a código integrado em `main`, CI aprovado, inventário remoto somente leitura e aprovação vinculada ao SHA e ao fingerprint do estado observado. As ações de inventário e release são despachos separados; a segunda exige o fingerprint aprovado e uma nova conferência remota idêntica.
- Validar o domínio `markina.pickyourpic.com.br`, a porta publicada `127.0.0.1:8080`, o projeto Compose `markina-gallery`, serviços ativos e revisão Alembic real antes de definir a execução.
- Exigir backup verificável e evidência de preservação dos registros financeiros antes da migration `20261022_0087`; bloquear em schema, containers, mounts, arquivos de credencial ou estado que divirjam do inventário aprovado.
- Aplicar somente a migration `20261022_0087_retire_infinitepay`, publicar API/web/worker com o Compose revisado e remover do host apenas o arquivo de binding InfinitePay identificado e confirmado como exclusivo após saúde do release.
- Validar healthchecks locais e HTTPS, continuidade do PIX próprio e leitura das duas compras InfinitePay históricas; limitar recuperação ao escopo aprovado e restaurar o backup antes de qualquer rollback de schema.
- Documentar o estado do servidor, evidências, impacto, tratamento do binding e resultado do release sem expor segredos ou dados pessoais.

## Capabilities

### New Capabilities

### Modified Capabilities

- `deployment-operations`: definir o contrato protegido para release de produção que aplica a migration de aposentadoria e remove binding exclusivo, preservando dados financeiros e serviços de terceiros.

## Impact

- Workflow de produção, scripts de release e gates de escopo, manifesto de runtime, Compose, migration Alembic, testes e documentação operacional.
- Produção em `/opt/markina-gallery`, projeto Compose `markina-gallery`, domínio `https://markina.pickyourpic.com.br` e entrada local do Nginx na porta `127.0.0.1:8080`. A topologia e revisão atuais do servidor ainda precisam ser confirmadas por inventário protegido.
- A migration remove configuração e credenciais exclusivas InfinitePay, referências operacionais e desafios OTP; mantém pedidos, pagamentos, tentativas, recibos, correções e PIX. Sua reversão requer restauração coordenada do backup anterior.
- Nenhum recurso, proxy, volume, rede, banco ou serviço de outro projeto poderá ser alterado.
