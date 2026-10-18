# Tasks

## 1. Contrato administrativo

- [x] 1.1 Implementar leitura administrativa somente de metadados das galerias privadas, cliente principal, membros ativos e pastas, limitada à galeria-fonte e ao tenant da sessão; validar autenticação e isolamento entre origens e tenants com testes de API. Evidência: `tests/test_private_folder_overview.py`, 2 testes aprovados em SQLite temporário externo ao repositório; Ruff aprovado em 17/10/2026.
- [x] 1.2 Cobrir galeria privada sem membro ativo, galeria compartilhada, origem sem privadas e tentativa de consultar dados de outra origem. Evidência: testes cobrem também acesso anônimo/cliente recusado, origem inexistente, origem de outro tenant, membros bloqueados/desvinculados omitidos e lista pública preservada.

## 2. Etapa 04

- [x] 2.1 Exibir seção privada separada das pastas públicas, com responsável principal, membros ativos e suas pastas; manter o upload público associado somente às pastas públicas. Evidência: teste de integração de `gallery-editor.test.tsx` verifica responsável, pasta privada e independência dos controles de upload público.
- [x] 2.2 Cobrir estados carregando, vazio e erro, além da identificação em galeria compartilhada, com testes do componente e integração do editor. Evidência: 4 testes do novo componente e 61 testes do editor aprovados; 65 testes no total em 17/10/2026.

## 3. Validação

- [x] 3.1 Executar testes backend e frontend direcionados, lint, typecheck e validação OpenSpec estrita; registrar comandos e evidências nesta change. Evidência atualizada em `validation.md` para a base `develop` de destino.
- [x] 3.2 Revisar o diff para confirmar que a consulta não expõe dados a clientes e não altera upload, permissões, notificações ou registros existentes. Evidência: endpoint exige `require_admin`; helper contém apenas SELECTs e retorno de metadados; a integração do editor adiciona somente import e renderização da seção. Alterações locais preexistentes foram preservadas.

## Workflow follow-up

- Revisar a change antes de iniciar a implementação.
- Sincronizar a spec principal e arquivar somente após implementação validada e revisão humana.
