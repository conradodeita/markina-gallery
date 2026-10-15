# Provisionamento offline por conta

## Estado e autorização

Ferramenta da task 2.4. Não é cadastro público nem habilita uso imediato de segunda conta. Isolamento/prontidão e piloto local concluídos; operadores só podem executar provisionamento real após obter aceite e validar publicação conforme o pacote operacional das tasks 8.1–8.2. As invocações abaixo são contrato de operação futura; os testes executados usam schemas PostgreSQL exclusivos e valores sintéticos, sem dados/configuração de homologação.

## Entrada e dry-run

Executar a partir de `backend/`, com `DATABASE_URL` e `ADMIN_SEED_EMAIL` fornecidos pela configuração segura do processo. O UUID de destino precisa vir do inventário aprovado. Não colocar senha/TOTP em argumentos, histórico de shell, comandos versionados ou logs. O comando abaixo usa marcador a substituir pelo UUID autorizado; não escolher a primeira conta do banco.

```text
python -m app.provision_photographer --tenant-id UUID_DO_PACOTE --create-tenant --dry-run
```

`--create-tenant` é intenção explícita quando o destino ainda não existe; não é necessário para uma conta existente sem vínculo. Dry-run é o padrão e funciona sem senha/TOTP. Não cria conta, administrador, vínculo nem configuração. A saída JSON contém somente UUID de destino e flags `create_tenant`, `create_admin`, `create_membership`, `applied`; não imprime e-mail, credenciais ou hash.

## Aplicação futura controlada

Somente para novo administrador, fornecer `ADMIN_SEED_PASSWORD` e `ADMIN_SEED_TOTP_SECRET` pela configuração segura já autorizada, sem editar `.env` ou inventar credenciais. Repetir o mesmo alvo e confirmar seu UUID:

```text
python -m app.provision_photographer --tenant-id UUID_DO_PACOTE --create-tenant --apply --confirm-tenant UUID_DO_PACOTE
```

CLI recusa confirmação ausente/divergente antes de criar recursos. Em PostgreSQL, execução serializa as tabelas de conta/admin/vínculo, incluindo tradução explícita do schema de teste quando configurada. O plano é recalculado dentro da transação, com validação de senha/TOTP anterior à criação. Erros de configuração/banco são sanitizados, sem traceback/payload de credenciais.

Repetição com administrador já associado inequivocamente retorna flags de criação falsas, sem exigir/revalidar/regravar senha ou TOTP. Vínculo ausente, revogado, para outra conta, múltiplos vínculos ativos, conta suspensa, identidade por e-mail ambígua ou destino já ocupado por outro administrador impedem escrita; a ferramenta não repara nem reativa esses estados. A conta nova recebe somente `Tenant`, `AdminUser` e `TenantAdmin`; PIX, marca, templates, canal externo e permissão de operador não são copiados ou concedidos.

## Seed inicial e evidência

`python -m app.seed_admin` conserva finalidade de primeiro administrador, com variáveis externas. Na criação exige instalação de conta única e ausência de outro administrador. Em repetição identifica e verifica somente o vínculo existente do e-mail escolhido, sem regravar credenciais ou depender da quantidade total de contas; não serve para adicionar outro fotógrafo.

Ajuda da CLI (`python -m app.provision_photographer --help`) validada. Dry-run, aplicação confirmada, idempotência, preservação de credenciais/configuração, recusas e saída sanitizada exercitados em `backend/tests/test_tenant_provisioning.py`, sem mensagens/canais reais. Evidências de cada execução e falhas corrigidas ficam em `validation.md`. Nenhuma aplicação remota foi executada.

## Permissão técnica do dono da instalação — task 6.1

A migration 0071 cria `installation_operator` vazia. Seed, criação de fotógrafo e login não concedem o privilégio. A permissão pertence ao UUID administrativo existente e não muda conta comercial, senha, TOTP, PIX, templates ou canais. Não há endpoint de concessão. Antes de operar remotamente, o pacote 8.1–8.2 precisa autorizar o UUID e a referência; os comandos abaixo são modelos futuros e não foram executados no destino.

A partir de `backend/`, com conexão segura do processo e UUID canônico do inventário:

```text
python -m app.provision_installation_operator --admin-id UUID_ADMIN_AUTORIZADO --action grant --authorization-reference REFERENCIA_DO_ACEITE --dry-run
python -m app.provision_installation_operator --admin-id UUID_ADMIN_AUTORIZADO --action grant --authorization-reference REFERENCIA_DO_ACEITE --apply --confirm-admin UUID_ADMIN_AUTORIZADO
python -m app.provision_installation_operator --admin-id UUID_ADMIN_AUTORIZADO --action revoke --authorization-reference REFERENCIA_DA_REVOGACAO --apply --confirm-admin UUID_ADMIN_AUTORIZADO
```

Dry-run é padrão; escrita exige confirmação do mesmo UUID. Referência sanitizada admite somente letras ASCII, números, ponto, underscore, dois-pontos e hífen, até 120 caracteres; não incluir dados pessoais ou segredos. Grant exige identidade verificada e exatamente um vínculo ativo a conta ativa. Revogação pode retirar a permissão mesmo com conta suspensa. Repetições sem mudança preservam timestamps e auditoria. Execução PostgreSQL serializa a tabela própria. Saída JSON informa apenas `action`, `changed`, `applied`; erros não imprimem identidade, driver ou credencial.

`GET /admin/installation-capabilities` retorna somente `capacity_diagnostics` e usa private/no-store. Capacidade e diagnóstico facial agregado exigem operador mais sessão administrativa válida; ambos revalidam antes de devolver dados, e capacidade também antes de consultar/publicar cache. O coletor não publica resultado após revogação durante coleta. Permissão técnica não amplia acesso a fotos, clientes ou pedidos de B. Limpeza homolog conserva registro e auditoria de grant/revoke, continua recusando instalação multitenant e não foi executada remotamente.
