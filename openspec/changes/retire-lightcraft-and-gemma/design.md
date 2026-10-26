# Design

## Context

A base de trabalho é `origin/main` no commit `4cc02068`, consultado novamente em 26/10/2026. A cadeia Alembic termina em `20261025_0089`; o proprietário informou que esse é o schema do último deploy. O checkout tem implementação integrada de RAW/LightCraft, avaliação/worker Gemma e ajuste opcional de prévias com RawTherapee. O branch atual declara JPEG como formato de entrada e proíbe RAW. A evidência remota disponível para serviços Gemma/RAW é histórica (11–19/10); não prova quais containers estão ativos hoje.

## Goals / Non-Goals

**Goals:**

- Remover do código executável a admissão/processamento RAW, LightCraft e Gemma, mantendo compatibilidade com a linha publicada em schema 0089.
- Servir buscas faciais exclusivamente com YuNet + SFace, preservando limiares, contratos de autorização e estado facial vigente.
- Manter o ajuste opcional de prévias no worker dedicado e fixar RawTherapee 5.13 para Linux x86_64 e ARM64.
- Preservar o fluxo JPEG, dados e registros existentes; documentar limites da verificação remota.

**Non-Goals:**

- Excluir tabelas, embeddings, jobs, consultas históricas, arquivos, imagens ou volumes Docker.
- Executar migrations, iniciar/parar/recriar containers, limpar imagens, publicar ou alterar homologação/produção.
- Recalibrar SFace, mudar o pipeline de busca facial ou alterar o perfil/estética do ajuste de prévias.

## Decisions

1. **Retirar todo o intake RAW, não converter o módulo para outro motor.** O branch atualizado declara entrada JPEG e não autoriza processamento RAW. Remover validação/roteamento RAW, endpoints, UI, worker, override Compose, Dockerfile, limites Nginx exclusivos e testes específicos. Preservar o envio JPEG e o processamento em pastas. Não fazer limpeza de arquivos existentes em disco.

2. **Manter migrations históricas e não criar migration de remoção.** A 0073/0074 registra a implantação Gemma e 0078 o estado RAW; a 0089 é o head informado do ambiente. Esses arquivos são parte da linhagem auditável. A aplicação deixa de admitir/executar configurações e jobs aposentados. Os mapeamentos estruturais históricos permanecem no metadata exclusivamente para compatibilidade com schema 0089, inventário e políticas fechadas de manutenção; não reintroduzem rotas, serviços, seleção de engine ou processamento. Tabelas e linhas existentes são preservadas. O campo histórico de engine da busca e os campos de modelo/dimensão dos embeddings continuam compatíveis; consultas novas filtram SFace. Nenhum purge ou reescrita de histórico é implícito.

3. **Remover Gemma do caminho executável e operacional versionado.** Retirar provider/assets, roteamento/seleção, configuração administrativa e endpoints, kinds de novos jobs Gemma, métricas exclusivas, imagem e dependências PyTorch/Transformers, serviço/profile Compose, scripts e gates de CI exclusivos. Preservar abstrações e dados genéricos necessários a SFace, retenção biométrica e consulta histórica. Migrations e relatórios passados permanecem identificados como histórico, sem executar o worker.

4. **Fixar RawTherapee 5.13 apenas no worker de ajuste de prévias.** Usar AppImage oficial x86_64 e ARM64 com os SHA-256 publicados pelo projeto, invocando `rawtherapee-cli` com as opções existentes. O build deverá verificar arquitetura, checksum e versão da CLI e rodar um smoke com imagem sintética. Se o AppImage não funcionar no container sem dependência global de FUSE ou sem preservar o contrato CLI, interromper essa task e registrar o bloqueio; não voltar silenciosamente ao pacote 5.9.

5. **Separar código local da aposentadoria operacional.** A remoção do serviço da configuração Compose não prova que containers/imagens antigos foram removidos. Antes de release, um inventário atual deverá identificar serviços próprios ativos, ambiente, imagens, schema, filas/jobs RAW ou Gemma, linhas experimentais e volumes de staging. Drenagem/stop dos serviços Markina e qualquer purge permanecem fora desta execução sem plano de impacto zero e autorização operacional específica.

6. **Atualizar gates de CI sem relaxar validações restantes.** Remover o job/check `gemma-runtime` e referências a ele em agregadores/políticas de teste; manter backend, frontend, OpenSpec, Gitleaks, migração e validações das imagens afetadas. O CI deverá construir/testar o worker RawTherapee 5.13 nas duas arquiteturas disponíveis.

## Risks / Trade-offs

- A migração de deployments deixa metadados de Gemma/RAW sem consumidores na aplicação; isso é intencional para preservar histórico e evitar DDL destrutivo.
- Um serviço opcional já ativo pode permanecer como órfão após publicar um Compose sem sua definição. O runtime atual não foi consultado; a change não poderá ser considerada operacionalmente concluída sem inventário e procedimento de parada autorizada.
- AppImage contém runtime e dependências próprias; compatibilidade real com Debian Bookworm, CLI headless, bibliotecas e limite de recursos do worker precisa ser provada nos builds/smokes locais.
- RawTherapee 5.13 alterou perfil de trabalho padrão em relação a 5.12. O código usa perfil `.pp3` versionado e não muda sua especificação; validação sintética verifica contrato técnico, não equivalência estética nem resultado em fotos reais.
- A branch base contém critérios/políticas de CI que podem depender de check names externos. Confirmar o resultado do CI da PR; não alterar branch protection externa por esta change.

## Operational authorization

A autorização humana de 26/10/2026 substitui exclusivamente a restrição anterior de merge/deploy desta change. Preservar todos os gates de segurança, privacidade, compatibilidade e isolamento. Publicar a mesma revisão verde aprovada, sem migration destrutiva, sem apagar históricos e com inventário/plano documentados em `deployment.md`. O fluxo genérico API/web não atende esta mudança especializada e seu manifesto antigo não será flexibilizado.
