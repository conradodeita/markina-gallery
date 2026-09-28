# Tasks

## 1. Base e persistência

- [x] 1.1 Reconciliar encerramento documental de simplify-gallery-access-modes após revisão humana e preservar suas evidências locais sem misturar commits; verificar git status/diff e base develop=9c8a880.
- [x] 1.2 Criar modelo/configuração opcional por pasta e migration aditiva após 0067; validar upgrade SQLite/PostgreSQL descartáveis com pastas existentes herdadas e downgrade que recuse perda de configuração própria; registrar evidência e contrato nos artefatos.
- [x] 1.3 Implementar resolução efetiva e assinatura de revisão distinguindo fonte galeria/pasta; testar +0,3 versus +0,5 sem soma, exposição zero, off, retorno à herança, padrão desligado e alteração geral sem afetar personalizada.

## 2. Ajuste de prévias e lifecycle

- [x] 2.1 Aplicar resolvedor em enqueue/worker/publicação/entrega e cancelar somente trabalhos afetados; testar reprocessamento da entrada convencional, idempotência, revisão coincidente, mudança/off durante render e isolamento entre duas pastas; documentar lock/assinatura usados.
- [x] 2.2 Aplicar resolução efetiva na retenção temporária high-res e preservar TTL/fallback/autorização; testar pasta off/personalizada/herdada sem exclusão prematura e sem alterar retenção do índice/histórico.
- [x] 2.3 Adicionar configuração/progresso/enqueue/antes-depois administrativos por pasta com paginação e auditoria; testar auth negada, pasta inválida/capa/inativa, valores inválidos, fotos antigas somente por ação e escopo restrito ao folder_id.

## 3. Processamento facial

- [x] 3.1 Aplicar modo facial local somente a novas admissões/agendamentos/retentativas, respeitando todos os gates globais; testar off sem afetar derivados, on sem bypass e preservação de trabalhos admitidos/índice/busca autorizada; registrar a semântica de pausa na documentação.
- [x] 3.2 Oferecer status/retentativa paginada facial por pasta e respeitar modos locais nas ações gerais; testar que ação em A não retenta B e que cliente não autorizada continua sem acesso a outras pastas; nenhum dado biométrico real será processado nos testes.

## 4. Interface por pasta

- [x] 4.1 Criar FolderProcessingPanel recolhível com dois cards, estado efetivo, valores com sinal/vírgula, progressos, sucesso/erro e ações locais; testar herança/custom/off, payload, abertura sem escrita e polling abortado ao fechar/desmontar; documentar texto de compartilhamento/pausa.
- [x] 4.2 Integrar o mesmo componente na pasta aberta da etapa Imagens e do Acervo, identificando o padrão geral existente; testar ausência em pastas fechadas, IDs acessíveis únicos e configuração da pasta compartilhada consistente entre cards.
- [x] 4.3 Refinar CSS conforme tokens existentes e verificar visualmente em mobile/desktop com dados sintéticos, nomes longos, loading/erro/vazio/progresso e navegação por teclado; registrar evidências sem dados de usuário e corrigir overflow/contraste encontrados.

## 5. Integração e publicação

- [ ] 5.1 Executar regressão backend/frontend, lint/typecheck, build Docker e OpenSpec estrito; revisar diff de escopo/segredos/migration e registrar comandos/resultados sem declarar teste não executado.
- [ ] 5.2 Preparar PR focado e validar CI; parar enquanto Actions roda; publicar somente pelo fluxo autorizado com inventário/porta/subdomínio/plano, conferir SHA/migration/healthchecks, sem limpeza ou reprocessamento facial de dados reais não autorizado.
- [ ] 5.3 Após revisão humana, sincronizar spec principal e arquivar somente com evidência de implementação/validação/publicação; validar OpenSpec estrito e preservar os registros de decisões.

## Evidências e continuidade

- Investigação: pastas comuns/restritas usam o mesmo upload/derivados; ajuste atual resolve GalleryPreviewSettings no enqueue, worker e entrega, e o lifecycle high-res depende dessa configuração. Inputs usa admin_preview convencional; não usar resultado ajustado como entrada.
- Controles atuais da etapa Imagens atuam na galeria inteira. Acervo deve usar endpoints locais, nunca copiar ações globais sem escopo. FacialPolicyPanel e PreviewAdjustmentPanel existentes são referências de estilo/contrato, sem duplicar polling em cards fechados.
- Branch codex/folder-processing-settings criada de origin/develop=9c8a880 sem descarte de trabalho local. A alteração preexistente em simplify-gallery-access-modes/tasks.md foi preservada e não pertence à nova implementação.
- Artefatos preparados antes do código; revisão humana do plano técnico pendente, conforme mandato 1.1 item 4. Nenhum código funcional, servidor, configuração ou dado de usuário foi alterado nesta etapa.
- Proprietário aprovou a change. Base origin/develop=9c8a880 conferida; simplify-gallery-access-modes/tasks.md é a única alteração preexistente, preservada e excluída do escopo de futuro commit. A revisão humana anterior da change simplify ocorreu na aprovação dos checks/merge/deploy #311; documentação local adicional não será descartada nem misturada.
- Migration aditiva 0068 validada em SQLite e PostgreSQL 17 descartável (container exclusivo `markina-gallery-folder-processing-tests` em loopback 55459): 2 testes passaram, incluindo upgrade de pasta existente sem linha, recusa de downgrade com override e downgrade seguro após herança. Nenhum banco do sistema foi aberto.
- Resolver e ajuste: `test_folder_processing.py`, `test_folder_processing_api.py`, `test_preview_adjustment.py` cobrem +0,3 versus +0,5, zero, off, configuração própria com padrão desligado, assinatura, entrada convencional, mudança durante render e fallback; a suíte legada de ajuste teve 22 testes aprovados. `test_highres_pipeline.py -k 'folder_override or folder_facial_pause or adjustment_must_complete'`: 3 passaram, confirmando retenção por override e pausa de nova admissão sem apagar índice.
- API administrativa: GET/PATCH e ações por pasta com autenticação, same-origin, pasta de conteúdo/galeria ativa, limites Pydantic, auditoria, paginação e recusa no modo off. Testes de API negam cliente, capa e inatividade; mudança em A preserva B. Facial: `test_facial_status.py` e `test_facial_indexing.py` passaram em regressão direcionada; caso novo verifica contagem local, retentativa só de A e pausa de B na ação geral. Os jobs antigos sem foto vinculada preservam o comportamento global anterior.
- Interface: painel só monta na pasta aberta em Imagens/Acervo e só consulta quando expandido; Vitest cobriu payload e aviso de pasta compartilhada, retorno de erro/retry, fechamento com abort do fetch e cancelamento do timer, mesmo `folder_id` em duas vistas com IDs acessíveis distintos e abertura por Enter, sem PATCH no abrir/fechar. Inspeção visual com HTML/CSS sintético local no browser (sem dados de usuário): 390 px com documento 375 px e 1 coluna de 283 px; 1280 px com 2 colunas de 462 px. Nome longo permaneceu dentro do card; foco usa `--focus` existente. Esta inspeção não substitui homologação autenticada.
- Integração parcial: Ruff `backend/app backend/tests` passou; frontend lint sem erros, TypeScript e build Next passaram; 49 arquivos/338 testes frontend passaram com um worker após timeout por carga paralela na primeira rodada; após os últimos ajustes, o teste focal do painel teve 4 aprovados. Docker backend e frontend reconstruídos com o código final, sem erro; TypeScript final aprovado. OpenSpec estrito da change e `--all` (67 itens) passaram. A suíte completa local do backend foi interrompida sem falha na marca de 8% para evitar duplicar o mesmo job longo que o CI executará no PR; resultados focais (APIs/facial 21, high-res 3, preview legado 22, migration SQLite/PostgreSQL 2, painel 4, paginação facial 1) passaram. Os testes de política de manutenção de homologação e de preservação de branding também passaram. 5.1 permanece pendente até o CI completo e revisão final do diff.
- Higiene da validação: container PostgreSQL descartável próprio foi parado após os testes. A revisão automática bloqueou a remoção dos dois arquivos temporários da prévia visual em `C:\codex-data\tmp\folder-processing-visual`; nenhum arquivo do repositório, volume ou dado real foi removido por essa tentativa.
