# Validação — `develop` b4f15ab, 17/10/2026

## Escopo

A change adiciona uma seção administrativa para identificar responsáveis, membros ativos e pastas de galerias privadas na etapa 04. Não altera destino de upload, processamento, política facial, notificações ou worker OTP.

## Backend

- `GET /admin/parent-galleries/{id}/private-folders` exige administrador, valida o tenant da sessão e limita galerias, clientes, membros, pastas e contagens à galeria-fonte autorizada.
- O endpoint retorna somente metadados: nenhum telefone, token, arquivo ou URL de prévia.
- `pytest tests/test_private_folder_overview.py tests/test_private_upload_batches.py -q`: **8 testes aprovados** em SQLite temporário fora do repositório.
- Ruff direcionado aos arquivos backend alterados: aprovado.

## Frontend

- Seção privada independente na etapa 04, com responsável principal, membros ativos, pastas, estado, contagem e link para a ficha privada existente.
- Falha ou retentativa da consulta não bloqueia a lista nem o upload público.
- `npx vitest run app/admin/galleries/private-folder-client-overview.test.tsx app/admin/galleries/gallery-editor.test.tsx --maxWorkers=1`: **65 testes aprovados**.
- ESLint nos arquivos frontend afetados: **0 erros, 11 avisos** em parâmetros não utilizados e elementos `<img>` dos arquivos existentes do editor/testes; os arquivos novos não adicionam avisos.
- `npx tsc --noEmit`: aprovado.
- `npm run build`: aprovado com Next.js 16.3.2; compilação, verificação TypeScript e geração das 23 rotas concluídas.

## OpenSpec e diff

- `openspec validate identify-private-folder-clients-in-gallery-step-four --strict`: aprovado.
- `git diff --check`: aprovado.
- A revisão confirmou escopo por tenant e origem e preservação dos controles existentes. A seção privada não pode ser usada para enviar fotos às pastas públicas.

## Publicação

- Não houve deploy, migration, alteração de configuração do servidor nem envio de notificação durante esta validação.
- O inventário somente leitura do servidor confirmou versão `b4f15abd6a71585082758062feba7fcfcc225587`, revisão Alembic `20261017_0084`, API/web/worker/Nginx/Redis saudáveis e respostas HTTP 200 em `/healthz` e `/api/health`. O worker OTP está ativo. A publicação permanece pendente de aprovação operacional final após apresentação do impacto do fluxo de deploy.
