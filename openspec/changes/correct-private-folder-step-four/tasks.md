# Tasks

## 1. Contrato e consulta de pastas

- [x] 1.1 Atualizar a spec administrativa para identificar a pasta restrita no título existente e remover o comportamento da seção separada. Evidência: delta OpenSpec válido em `specs/gallery-sales/operational-gallery-interface/spec.md`.
- [x] 1.2 Incluir nomes das clientes atribuídas na consulta paginada de pastas, isolados por origem e tenant; cobrir pastas compartilhadas e sem atribuições. Evidência: teste de `test_folder_processing_api.py` aprovado para duas clientes e lista vazia sem atribuição.

## 2. Upload e notificação

- [x] 2.1 Criar lote para upload restrito da etapa Imagens, incluir o ID ao registrar fotos e fechar o lote mesmo com falha parcial; manter pastas comuns sem lote. Evidência: teste frontend de envio parcial aprovado e testes `test_private_upload_batches.py` existentes aprovados.
- [x] 2.2 Substituir a seção extra pelo nome no título do card e ajustar testes de apresentação e upload. Evidência: testes de `gallery-editor.test.tsx` aprovados, incluindo cliente única, múltiplas clientes e pasta sem atribuição.
- [x] 2.3 Remover a importação e renderização da seção extra na etapa 04, preservando os módulos administrativos existentes fora do fluxo; verificar que não há chamada de produção à seção.

## 3. Validação

- [x] 3.1 Executar testes frontend e backend direcionados, lint, typecheck, build, escopo do release API/web e validação OpenSpec estrita; registrar comandos e evidências em `validation.md`.
- [x] 3.2 Revisar diff e atualizar esta change com resultados e limitações antes da revisão humana. Evidência: `git diff --check` sem erros e revisão do escopo concluída; sem migração ou publicação remota.

## Workflow follow-up

- Revisão humana desta change ainda pendente; após aceite, sincronizar as specs principais e arquivar.
