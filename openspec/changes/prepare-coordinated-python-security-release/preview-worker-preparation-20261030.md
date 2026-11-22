# Preparação isolada do worker de prévias — 30/10/2026

## Escopo e origem

Preparação solicitada pelo proprietário após inventário somente leitura. Fonte dos pins e do preparador: `74f61300e7a818d1605afda3db1d07574c443110`. Branch local `codex/prepare-preview-security-release`. Nenhuma alteração de dependências no repositório, de executor ou de produção foi realizada.

O inventário final foi recolhido em `2026-10-31T00:08:42.603865+00:00` (30/10, 21:08 em São Paulo). Checkout Oracle: `0dd015a62447e0c8d4c6af16b381140c8118f2ec`. Dez serviços ativos saudáveis; API e worker já usam os quatro pins corrigidos. Opcionais faciais, Gemma e RAW parados foram excluídos da preparação. A comparação dos metadados dos containers, imagens, estados, reinícios e pacotes antes/depois foi idêntica; isso não afirma imutabilidade de dados de clientes, que não foram consultados.

## Imagens e versões

- Imagem anterior Oracle, preservada e ainda ativa: `sha256:48fa9dc8a2c94d5398a502ad02fcbcab89a660039c66d08470c0ae82e81ce44e`.
- Importação local containerd: `sha256:3c33ed35f2c13cf7282bc480930c94f2cf8dc7c45d87cc555c3f284fe7944d38`. O preparador confirmou a identidade do config original por SHA256 e todas as camadas; esses dois IDs não foram tratados como intercambiáveis.
- Candidato local: `sha256:ef5105e0bcd734b929d2b46945f7538dceccade45a60d806bd58a2b3b4bff45d`.
- Tag local: `markina-gallery-python-validation:preview-adjustment-worker-48fa9dc8a2c9`.
- Config do candidato registrado no build: `sha256:e88e70fd78698a9fc6a327cf990296b01e72fd408b0ed9e048760dee125e31bf`.

Build ARM64 isolado sobre a imagem anterior, com `--no-deps --only-binary=:all:`. Somente aiohttp 3.14.3 → 3.14.4, multidict 6.8.0 → 6.9.1, urllib3 2.7.0 → 2.8.0 e yarl 1.24.5 → 1.25.1 foram substituídos; o manifesto embutido foi atualizado. Python 3.13.16, RawTherapee 5.13, código, camadas anteriores e demais distribuições foram preservados. O candidato não foi enviado a registry nem carregado na Oracle.

## Validação

- Comparação completa das 60 distribuições: exatamente as quatro alterações autorizadas.
- `pip check`: exit code zero; imports e contrato de URL do preparador aprovados.
- 29 testes de `scripts.test_python_security_release`: aprovados.
- OpenSpec strict: aprovado.
- Imagem anterior e candidata executadas localmente em ARM64 emulado, sem rede externa, com filesystem read-only, tmpfs, limites de recursos e sem volumes/dados de produção.
- Dois contratos HTTP sintéticos em loopback por imagem: aiohttp e urllib3 com query multivalorada multidict/yarl.
- Dois formatos sintéticos por imagem: JPEG e PNG renderizados pelo RawTherapee real, preservando entrada, dimensões e modo RGB.
- Hash JPEG renderizado idêntico: `7f5715b56eac4585dcaf13cb99ed657e3596598b31eaba0e0311e8ae0eb58cab`.
- Hash PNG renderizado idêntico: `50d25e029fc9f0baebbc421624cf63c957625a78494ef907223138ce678de661`.
- Binário RawTherapee idêntico: `16db95e09c170f41f4ca798acbebad1a9276a247bc975ff833fa4bbf9426de63`; versão CLI 5.13 confirmada.

Não foi executado ciclo operacional com banco/fila, nem homologação com fotografias reais. Os testes não comprovam drenagem, parada segura ou recuperação operacional do worker.

## Plano oficial e bloqueios

`scripts/python_security_release.py --mode plan` com inventário real atualizado e candidato validado selecionou exclusivamente `preview-adjustment-worker`. Fingerprint de planejamento: `e0b5ae901a71395ae1cdb4f93b99f395c97bd1ea6fddcafef5eefc258d4b5ad3`. Não é aprovação operacional; `operational_approval_code=null`, `production_ready=false`.

Bloqueios retornados:

1. `legacy_worker_has_no_cooperative_drain`.
2. `specialized_startup_homologation_required`.
3. `operational_executor_and_recovery_not_implemented`.

O módulo Python recusa explicitamente release/rollback/recover. A implementação de prévias inspecionada não fornece ack de drenagem. O fluxo específico da migration 0090 contempla SIGINT no legado somente após isolamento dos produtores e fila ociosa; publica API/web e executa DDL, portanto não pode ser usado para esta correção isolada. Não remover os gates nem executar compose up diretamente para contorná-los.

A imagem anterior está disponível para servir como artefato de rollback, mas não há procedimento operacional de rollback deste escopo validado. O próximo trabalho necessário é especificar e revisar a transição segura do worker legado e completar o executor/recuperação oficial para este serviço, seguido de homologação sintética. Se isso exigir pausa de produtores/API, o impacto deve ser apresentado e autorizado antes da operação. Nenhum comando de publicação é fornecido enquanto esses bloqueios persistirem.

## Evidências e continuidade

Evidências locais fora do Git: `C:\codex-data\release-evidence\preview-python-20261030` — `baselines.json`, `inventory-before.json`, `inventory-final.json`, `candidates.json`, `source-provenance.json`, `image-smoke.py`, `baseline-smoke.json`, `candidate-smoke.json`, `official-plan.json`.

A ferramenta de worktree criou arquivos preenchidos por zeros; os bytes foram preservados em `worktree-zero-backup` e somente esses arquivos do checkout recém-criado foram reconstruídos dos blobs de HEAD. Nenhum trabalho de outro checkout foi sobrescrito. O registro do worktree no aplicativo falhou; o checkout Git existe e pode ser usado pelo caminho explícito.

Refatoração proporcional: nenhuma alteração de código elegível ou necessária. As tasks históricas coordenadas não foram marcadas completas por esta preparação de um único candidato. Nenhum merge, deploy, migration, restart, limpeza Docker ou alteração na Oracle ocorreu.
