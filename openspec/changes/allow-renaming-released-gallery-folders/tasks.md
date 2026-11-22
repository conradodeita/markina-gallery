# Tasks

## 1. Renomeação autenticada de pastas

- [x] 1.1 Permitir renomear pastas comuns/restritas liberadas e pastas exclusivas de Galeria privada legada pela rota existente, normalizar o nome e preservar estado/fotos/audiência; validar renomeação comum, restrita e legada, nome inválido, galeria em exclusão e tenant incorreto, incluindo IDs, seleções, pedidos, totais e snapshots comerciais inalterados. Evidência: `test_admin_manages_preparing_folders_without_storage_urls`, `test_rename_released_common_restricted_and_legacy_folders_preserves_audience_and_commerce` e `test_blocked_parent_gallery_rejects_new_folder_and_photo` passaram (3); `test_UUID_estrangeiro_equivale_ausente` passou para os 4 tipos de recurso. O teste de preservação compara IDs de fotos/grant/seleção/pedido, total confirmado e snapshot original de nome da pasta.

## 2. Ações na interface administrativa

- [x] 2.1 Exibir a ação `Renomear` no editor de Imagens, no `Acervo da cliente` e na gestão já existente da Galeria privada legada; validar PATCH, atualização, cancelamento e erro por componente, sem alterar atribuições ou carregamento de fotos. Evidência: três testes de componente passaram para galeria pública, pasta restrita e cancelamento/erro; `page.test.tsx` confirmou o PATCH, o nome atualizado e o fluxo de pasta exclusiva legada. Execução focada: 4 testes passaram, sem alterar atribuições ou recarregar fotos abertas no Acervo.

## 3. Integração local

- [x] 3.1 Executar regressões direcionadas de API e das três telas, Ruff, ESLint, TypeScript e OpenSpec strict; revisar apenas a área afetada, registrar resultados e confirmar que não houve migration, operação remota ou alteração de dados existentes. Evidência: `test_derived_galleries.py` + `test_tenant_acervo.py`: **123 passaram** em 19m16s; warnings apenas de deprecações preexistentes FastAPI/SQLAlchemy. UI de galerias: **144 passaram** em 6 arquivos; TypeScript passou; ESLint passou com 16 avisos preexistentes (imagens/variáveis de testes); Ruff passou; `openspec validate allow-renaming-released-gallery-folders --strict` passou; `git diff --check` passou. Revisão focal confirma mudança somente do nome, sem migration, operação remota ou gravação em dados existentes.

## Workflow follow-up

- Sincronizar as specs principais e arquivar a change somente após revisão humana.
