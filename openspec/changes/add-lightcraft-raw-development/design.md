# Design

## Context

Consulte `proposal.md` para a motivação e os deltas para o contrato. O JPEG atual passa pelo pipeline de mídia e de face em alta resolução; o ajuste opcional usa configurações de processamento da galeria/pasta e RawTherapee CLI. A integração atual serializa pixels para PNG e não oferece leitura direta de RAW. A fonte de integração já possui propriedade de tenant e exige que registros e consultas operacionais sejam vinculados ao tenant; configurações do motor RAW serão próprias de cada tenant.

## Goals / Non-Goals

**Goals:**

- Oferecer ingestão RAW temporária, isolada por worker, para conteúdo e capa, sem persistir RAW nem JPEG de alta resolução depois do processamento.
- Permitir selecionar motor e comparar RawTherapee e LightCraft em entradas RAW compatíveis sem mudar o fluxo JPEG atual.
- Rastrear motor/versão nos resultados e informar lançamentos estáveis disponíveis, mantendo atualização sob publicação controlada.
- Preservar autorização, ordem da indexação high-res, proteção das prévias, validação horizontal das capas e liberação de pasta existente.

**Non-Goals:**

- Substituir culling, edição final, JPEG pós-culling, SFace/Gemma ou a entrada facial da cliente.
- Reprocessar fotos antigas sem a fonte; ela será descartada e o reenvio será necessário.
- Atualização automática de binários, download de executáveis pelo painel, envio a serviços externos de processamento ou retenção/backup de RAWs.
- Ativar LightCraft como padrão, modificar ambiente remoto ou publicar o módulo nesta change de planejamento.

## Decisions

1. **Adaptador de desenvolvimento RAW separado do pipeline JPEG.** Introduzir interface por arquivo de entrada/saída para operações em RAW, sem reaproveitar diretamente `RawTherapeeEngine.render(PIL.Image)`, cuja entrada atual é a prévia PNG reduzida. O seletor por tenant vale somente para novos envios RAW. O fluxo JPEG e seus resultados permanecem no pipeline atual. Alternativa descartada: encaminhar JPEGs atuais por LightCraft, pois o proprietário considera esse fluxo pronto e a necessidade nova é a ingestão imediata de RAW.

2. **Worker opcional e versão pinada.** Empacotar a CLI selecionada em imagem/worker dedicado, sem colocá-la na API nem ampliar o worker convencional. Fixar versão e digest no artefato de implantação. `lightcraft-cli` opera sem UI e oferece desenvolvimento automático; validar a versão binária, dependências, formatos RAW e execução Linux ARM64 antes de disponibilizar o motor. Alternativa descartada: executar a CLI no processo HTTP, que tornaria uploads dependentes do tempo/CPU de decodificação.

3. **Ciclo de vida transitório e fail-closed.** Guardar o upload RAW numa raiz temporária exclusiva, com hash, quota de arquivos/bytes, limite do corpo, nome opaco, escrita atômica, TTL e retry limitado. Validar assinatura/formato e decodificar dentro de limites de pixels/tempo. Após desenvolvimento, validar dimensões/orientação e gerar JPEG high-res de trabalho numa raiz temporária do pipeline existente. Para conteúdo, aguardar indexação facial high-res e derivados obrigatórios; para capa, respeitar a regra horizontal após EXIF e o derivado limpo limitado já previsto. Remover RAW imediatamente após o JPEG de trabalho validado e remover o JPEG de trabalho no lifecycle atual após os artefatos elegíveis. Falha terminal/expiração remove temporários, registra `reupload_required` e impede publicação. Nenhum arquivo-fonte entra no Drive, backups ou endpoint de mídia.

   O primeiro contrato prioriza Sony ARW, mas aceita dinamicamente os formatos que a versão instalada do motor anuncia e consegue decodificar. A compatibilidade não será limitada a uma marca ou corpo: outros fotógrafos poderão usar ARW, CR2/CR3, DNG, NEF/NRW, RAF, RW2/RWL, PEF ou ORF quando o motor escolhido suportar aquela variante. Extensão e MIME servem apenas para selecionar o adaptador; a decodificação real confirma compatibilidade. Limites iniciais: 256 MiB por arquivo; 64 arquivos e 2 GB em processamento; saída máxima de 40 MP; 15 minutos por conversão; TTL máximo de 24 horas; duas tentativas. Esses tetos são limites de segurança iniciais, sujeitos a ajuste após benchmark local/ARM.

   O inventário de homologação classifica `raw_development_settings` como configuração preservada e `raw_development_job` como dado operacional removível. A raiz isolada de staging RAW entra no inventário de mídia e só é limpa pelo comando de limpeza já protegido por ambiente, confirmação literal e validação do path; a ausência do volume é aceita quando o módulo opcional não está instalado.

4. **Ordem de pipeline e proteção visual preservadas.** Para conteúdo: RAW → render high-res do motor selecionado → indexação facial existente no raster desenvolvido → derivados/ajuste convencional configurado → marca-d’água e proteção na saída, conforme invariantes vigentes. A conversão não cria identidades nem contorna autorização facial. O ajuste opcional de galeria permanece separado; sua execução segue a configuração atual e usa os derivados limpos. Para capas, não executar indexação facial comercial; conservar autenticação, autorização, limite, remoção de metadados e regra especial de proteção de capa.

5. **Seleção e reprocessamento explícitos.** Persistir engine, versão, versão do perfil de desenvolvimento e fingerprint da entrada como proveniência não biométrica. Trocar motor afeta só novos envios. Reprocessamento requer reenvio da fonte descartada; manter derivados atuais durante eventual nova geração. Não backfill automático nem dupla execução shadow em lotes de produção, pois aumentaria custo e exigiria retenção adicional de fontes.

6. **Comparação controlada antes de recomendar padrão.** Construir corpus de validação autorizado e separado do Git, cobrindo JPEG/RAW representativos de modelos de câmera usados, exposição, pele, interiores e eventos. Comparar os mesmos RAWs no perfil existente do RawTherapee e no `develop.auto` do LightCraft. Medir suporte por modelo, saídas válidas, dimensões/cor, tempo, pico de memória e CPU em ARM; obter avaliação estética humana. Separar a qualidade de desenvolvimento das métricas faciais: uma execução facial real só ocorre com autorização específica, origem/finalidade documentadas, ambiente autenticado e controles de retenção/exclusão já exigidos. Até todos os gates e aceite, manter o motor atual como padrão e LightCraft desativado.

7. **Versão informativa com atualização controlada.** Ler versão instalada do binário/imagem pinada e consultar a API oficial de releases estáveis do GitHub apenas quando a informação cacheada expirar (por exemplo, 24 horas) ou o proprietário solicitar atualização. Exibir versão instalada, versão estável conhecida, data/link/notas e estado da consulta. Falha externa mantém versão em execução e último resultado conhecido, marcado como possivelmente desatualizado. Não baixar nem instalar do painel; publicar nova versão pelo pipeline habitual de homologação após revisão de licença/dependências, compatibilidade, benchmark e inventário. A consulta de release nunca é dependência do upload.

8. **Migração aditiva e compatibilidade.** Adicionar configuração por tenant, registros de job/proveniência e estados necessários sem modificar fotos já existentes. Configuração inicial desligada e seleção padrão preservando o fluxo atual. Fotos legadas continuam com mesmo acesso e derivados. Desligar o módulo interrompe novas admissões; jobs já iniciados terminam ou falham com estado verificável, sem remover derivados prontos. Rollback de binário mantém suporte de leitura dos registros; downgrade destrutivo de migration não é estratégia de rollback.

9. **Teto de bytes na prévia do cliente.** Cada `client_preview` novo ou regenerado SHALL ficar em até 250.000 bytes para reduzir o tráfego da galeria em redes móveis. O encoder tenta qualidade 90, 85, 80 e 75; se ainda exceder o teto, reduz as dimensões proporcionalmente e repete até caber. O ajuste se aplica depois da marca-d'água e também ao resultado final do ajuste opcional de prévia. Miniaturas e `admin_preview` mantêm seus contratos atuais. Não há teto de bytes para o JPEG temporário usado no reconhecimento facial. A publicação desta change não reescreve automaticamente derivados históricos; qualquer recodificação em lote requer plano de execução próprio, pois substitui arquivos JPEG existentes.

10. **Propriedade e escopo de tenant.** `RawDevelopmentSettings` SHALL ser identificada por `(tenant_id, id=1)`; `RawDevelopmentJob` SHALL carregar `tenant_id` e referenciar `(photo_asset_id, tenant_id)` com a integridade composta disponível no schema integrado. Rotas administrativas resolvem o tenant pela sessão do fotógrafo, filtram todos os registros por esse contexto e recusam contexto ausente/inativo. Workers obtêm o tenant da linha persistida e aplicam o mesmo filtro antes de tocar em arquivos, publicar derivados ou alterar estado. A consulta informativa de release é cacheada no escopo do tenant junto da seleção de motor. Após integrar as migrations de pagamentos 0075–0077, a revisão RAW é `20261014_0078`, descendente de `20261012_0077`; não reutiliza a revision local divergente `20261010_0062`.

## Risks / Trade-offs

- **Formatos/câmeras ainda não suportados pelo LightCraft ou RawTherapee →** permitir motor/formato somente após teste de decodificação e manter erro por arquivo com envio JPEG como alternativa.
- **Qualidade variável do auto →** manter o JPEG atual como caminho conhecido, comparação por amostra e aceite estético do fotógrafo antes de recomendação.
- **Picos de CPU, RAM e disco no lote →** quotas, backpressure, concorrência configurável, worker limitado e medição no Oracle ARM antes de rollout.
- **RAW temporário sobreviver a interrupção →** staging isolado, TTL, limpeza idempotente, monitoramento de resíduos e teste de crash/restart; nunca assumir que `finally` é suficiente.
- **Atualização upstream quebrar formato, perfil ou licença de componentes →** pin por versão/digest, inventário SBOM/licenças e rollout/rollback controlado; não acompanhar `latest` automaticamente.
- **Atualização GitHub indisponível ou rate-limited →** cache, timeout e mensagem de estado sem bloquear upload nem alterar motor.
- **Foto escolar processada como dado facial →** seguir gates faciais existentes; a autorização de um upload RAW para conversão não substitui consentimento, autorização ou finalidade exigidos para indexação.

## Migration Plan

1. Implementar schema/configuração aditivos ligados a tenant com módulo desligado, formato de motor/versionamento e status de desenvolvimento, após o head integrado de pagamentos `20261012_0077`.
2. Construir worker e imagens com versões pinadas; validar localmente sem iniciar ou atualizar recursos remotos.
3. Rodar contratos sintéticos, corpus de RAW autorizado e medições ARM isoladas; manter LightCraft indisponível se qualquer formato/limite não for verificado.
4. Atualizar instruções e roadmap para substituir a proibição absoluta por recepção transitória para conversão, sem armazenamento/entrega de RAW.
5. O rollout de homologação inclui explicitamente o overlay e o worker pinado, sem alterar `.env`, secrets, DNS, proxy ou recursos de outros projetos. A configuração por fotógrafo permanece desligada por padrão. O rollout exige inventário atualizado de homologação, portas/subdomínio, plano de impacto zero e autorização humana explícita; produção continua fora desta change. Em 13/10/2026 o proprietário autorizou essa publicação em homologação.
6. Rollback desliga novas admissões e seleciona o motor previamente validado; novas solicitações usam JPEG como alternativa. Resultados já gerados permanecem identificados pela versão e não são apagados automaticamente. RAW descartado exige novo envio para reprocessar.

## Open Questions

- O primeiro caso informado é Sony ARW, família A7/A7R; geração/corpo exato segue necessário para avaliar amostras reais. Isso não limita o produto: compatibilidade por formato/câmera é determinada por versão e engine. Ver `docs/RAW-COMPATIBILITY.md`.
- Local, licença e autorização de um conjunto de teste representativo. Sem isso, a comparação estética/biométrica real e a recomendação final permanecem pendentes.
- Metas numéricas de vazão/memória ARM para o lote pós-evento, a serem definidas após medição de capacidade e não por benchmark do fornecedor.
