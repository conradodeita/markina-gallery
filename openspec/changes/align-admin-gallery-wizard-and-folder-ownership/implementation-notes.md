# Inventário de implementação

## Produtores de fotos sem pasta antes da mudança

- `POST /admin/parent-galleries/{parent_gallery_id}/photos`: contrato legado que criava `PhotoAsset` sem `folder_id`; será mantido apenas como resposta de descontinuação `410 Gone`.
- Fixtures históricas em `backend/tests/test_derived_galleries.py` e `backend/tests/test_media.py`: criavam `PhotoAsset` diretamente para testar comportamentos anteriores; serão convertidas para criar pasta coerente, exceto fixtures explícitas da migration legada.
- Migration `20260827_0005_staged_photo_folders.py`: adicionou `photo_asset.folder_id` como opcional para compatibilidade; a nova migration fará o saneamento antes de torná-lo obrigatório.

## Consumidores que aceitavam fotos sem pasta

- `assigned_photo_for_gallery` e `GET /gallery/{gallery_id}/photos`: tratavam `folder_id IS NULL` como conteúdo liberado; após a migration aceitarão somente pasta `released`.
- Criação de galeria derivada: permitia foto sem pasta e validava estado apenas quando `folder_id` existia; passará a exigir pasta liberada e da mesma origem.
- Upload da origem JPEG: validava o estado da pasta apenas quando havia pasta; passará a rejeitar qualquer registro incoerente.
- Consultas administrativas por galeria continuam permitidas porque são leitura contextual, não criação avulsa.

## Verificação de fechamento

Ao concluir a implementação, `rg` deverá encontrar `folder_id IS NULL` ou construção sem pasta somente na migration/fixtures de compatibilidade e na documentação deste inventário. Nenhum frontend oficial deverá chamar o contrato legado de criação direta.

## Arquitetura aplicada

O caminho de escrita é obrigatório e único: **galeria-mãe → pasta em preparação → foto**. A publicação da pasta cria apenas referências para galerias privadas derivadas da mesma galeria-mãe; não copia o original nem publica um catálogo geral. A interface administrativa consome os contratos autenticados do editor e não infere permissões, disponibilidade comercial ou estado de uma pasta no navegador.

O passo comercial e o de aparência permanecem visíveis no editor de cinco etapas, mas retornam indisponibilidade explícita do backend até que seus contratos tenham sido aprovados. Isso evita mostrar preços, formas de pagamento ou controles visuais simulados.

## Validação da migration e rollback

A migration foi exercitada integralmente com dados sintéticos nos dois bancos suportados:

- SQLite: upgrade, reexecução idempotente, preservação de histórico, nulidade, índices, chave candidata composta, chave estrangeira composta e downgrade.
- PostgreSQL 17 efêmero: duas galerias, pasta preexistente, duas fotos legadas, posição das pastas de compatibilidade, rejeição de vínculo pasta/galeria divergente, índices e constraints refletidos pelo SQLAlchemy, além do downgrade não destrutivo. Nenhum dado real ou banco persistente foi usado.

O teste PostgreSQL fica disponível em `backend/tests/test_cloned_gallery_migration.py` e é habilitado explicitamente com `TEST_POSTGRES_DATABASE_URL`; sem essa variável, a parte PostgreSQL é ignorada para que a suíte comum não dependa de infraestrutura externa.

O rollback operacional SHALL partir de backup exclusivo do banco Markina e revisão conhecida. Se a aplicação nova falhar depois da migration, interromper novas escritas, executar `alembic downgrade 20260827_0005` no container/API do projeto e somente então restaurar a revisão anterior compatível. O downgrade torna `photo_asset.folder_id` novamente opcional, troca a chave estrangeira composta pela chave simples anterior e remove a chave candidata composta. Ele preserva as pastas de compatibilidade e os vínculos saneados; não apaga nem desassocia fotos. Antes de reabrir escritas, conferir a revisão Alembic, contagens e referências de fotos, seleções e pedidos. Qualquer restauração de backup ou reorganização destrutiva permanece uma operação separada e exige autorização humana.
