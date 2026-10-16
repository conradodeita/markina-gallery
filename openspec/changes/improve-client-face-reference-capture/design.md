# Design

## Context

Consulte `proposal.md` e as specs desta change. `OpenCvSFaceProvider.observe_bytes` decodifica a referência, limita a imagem de trabalho antes da detecção, então alinha o rosto detectado com `alignCrop` e gera o embedding SFace de 128 dimensões. O clique em região reutiliza embedding já indexado; fotos do acervo podem ter sido processadas pelo pipeline high-res. O workflow de push em `develop` publica homologação; a automação de produção existente é limitada ao serviço `web` e a execução documentada exige inventário e aprovação protegida.

## Goals / Non-Goals

**Goals:** preservar detalhes da referência até detecção/alinhamento; reduzir falhas por rosto pequeno, orientação, pose ou enquadramento; manter upload e tornar obrigatória a captura guiada quando a cliente escolher a câmera; testar a versão em produção pelo fluxo GitHub autorizado sem alterar terceiros.

**Non-Goals:** substituir SFace, reindexar o catálogo, fazer busca entre galerias, exigir presença da criança, adicionar liveness, adicionar API paga, persistir recortes faciais ou remover o envio de fotos antigas.

## Decisions

1. **Manter o contrato de embedding.** Consultas continuam usando o mesmo detector/reconhecedor, modelo, versão, dimensão e normalização do índice. A mudança fica no caminho de preparação da referência; não mistura espaços vetoriais nem exige migration/backfill.

2. **Detectar antes de recortar.** Corrigir orientação da referência e executar detecção multiescala seletiva em pixels da imagem original, sob limites de bytes, pixels, passes e tempo. Deduplicar caixas/landmarks no espaço original e então alinhar diretamente dessa resolução para gerar o embedding. Limitar extração de candidatos da referência a dois rostos, suficiente para distinguir rosto único de múltiplos rostos. Reutilizar técnicas e orçamento do pipeline high-res quando compatíveis, sem invocar a análise de todas as fotos do acervo durante uma consulta.

3. **Qualidade com resultado explicável.** Manter a validação de rosto único e os limites de tamanho, nitidez e confiança; quando falhar, não comparar o embedding com a galeria e retornar estado específico e orientação sanitizada. Não aumentar o limiar de similaridade nem aceitar correspondência fraca como substituto de qualidade. A opção de câmera exige uma captura explícita após instrução visual de enquadramento, pose, iluminação e estabilidade; os limites técnicos medidos pelo servidor continuam determinando se haverá comparação. A opção de upload continua disponível para fotos antigas.

4. **Sem restauração generativa.** Não aplicar super-resolução que sintetize traços faciais. Correções fotométricas ou redução de ruído só poderão ser avaliadas futuramente como variantes separadas, sem substituir a imagem original, e exigirão comparação anotada de falsos positivos/negativos.

5. **Sem liveness nesta change.** Liveness verifica presença e resistência a spoofing, não demonstra melhor correspondência com fotos antigas. Captura guiada e feedback de qualidade podem atingir o objetivo sem exigir que a pessoa buscada esteja fisicamente presente nem transmitir vídeo facial a terceiro.

6. **Publicação GitHub com gate protegido.** O workflow de produção será iniciado automaticamente após merge do SHA aprovado em `main` e sucesso dos jobs obrigatórios. O job dependerá do environment protegido `production`, repetirá inventário imediatamente anterior e executará somente os serviços Pick-your-Pic definidos no plano. O job não pode limitar-se ao serviço `web` quando o SHA contém alterações em API/worker. Nenhuma etapa remota mutável será executada sem aprovação operacional exigida pelo ambiente.

7. **Validação conforme preferência do proprietário.** Não executar testes locais. PR e workflow GitHub continuam executando as verificações já configuradas; o proprietário realiza primeiro o smoke funcional com cliente autenticado no servidor de produção após publicação aprovada. Registrar SHA, resultado e métricas sanitizadas no OpenSpec, sem alegar acurácia melhorada sem conjunto rotulado.

## Limites operacionais e rollback

- A referência mantém o limite configurado de 30 MiB e, por padrão, 25 milhões de pixels (`FACIAL_MAX_REFERENCE_BYTES` e `FACIAL_MAX_REFERENCE_PIXELS`). A imagem é decodificada em memória, orientada por EXIF e não é persistida em claro.
- A consulta reutiliza `FACIAL_DETECTION_CONFIG_JSON`: uma passagem global, uma multiescala quando a heurística indica dificuldade e até `max_tiles` recortes (padrão 64). Cada entrada é limitada pelos lados configurados e a resolução da passagem global não excede 2 megapixels. Apenas os dois rostos de maior confiança são alinhados/embeddados, suficientes para decidir rosto único versus múltiplos rostos.
- O lease padrão do job é 120 segundos. O número e tamanho das inferências são limitados por configuração; não há garantia de latência fixa em hardware compartilhado. Métricas existentes de passes e tempo podem orientar ajuste, sem incluir pixels, recortes, embeddings, landmarks ou scores.
- Não há migration nem reindexação. Rollback é a reversão do código web/API/workers pelo fluxo de publicação aprovado, sem rollback de dados. Nenhuma melhoria quantitativa de acurácia pode ser alegada sem corpus rotulado e revisão de falsos positivos/negativos.

## Risks / Trade-offs

- [Foto de referência realmente sem detalhe] → orientação antes da busca e estado de qualidade específico; nenhuma técnica recupera informação que não foi capturada.
- [Mais passes aumentam CPU e latência] → orçamento estrito, passes extras apenas quando a detecção inicial indica dificuldade e telemetria agregada.
- [Mudanças de idade entre evento e captura atual] → preservar upload de foto antiga; a captura guiada só é exigida quando a cliente escolhe usar a câmera.
- [Falso positivo por limiar permissivo] → não reduzir threshold sem calibração; manter apresentação como possibilidade e escopo da galeria autorizada.
- [Deploy multissserviço afeta produção compartilhada] → inventário atualizado, conjunto de serviços limitado, ambiente protegido, plano de impacto zero, healthchecks e rollback específico; falhar fechado em divergência.
- [CI atual executa testes automaticamente] → nenhuma suíte será rodada localmente, mas os gates remotos obrigatórios não serão removidos para acelerar a publicação.

## Migration Plan

Sem migration de banco e sem reindexação. Após revisão do OpenSpec e implementação, abrir PR isolada com somente arquivos desta change. O GitHub executa CI e OpenSpec; após merge aprovado, inicia automaticamente o job de produção, que aguarda o gate do environment `production`. Antes da execução, registrar inventário atualizado do host, SHA, serviços/portas/subdomínio e plano de impacto zero. Após aprovação, publicar o conjunto necessário com rollback restrito ao projeto. O proprietário valida imediatamente o fluxo autenticado em produção e registra evidência no OpenSpec. Não executar rollback de dados nem alterar `.env`/secrets.

## Decisão aprovada pelo proprietário — fluxo de entrega sem aprovações repetidas

Esta decisão detalha e substitui qualquer interpretação anterior que exija aprovação humana para cada push ou para o preflight somente-leitura:

- O executor SHALL conduzir os ciclos CI → leitura dos logs → correção verificável dentro do escopo → commit/push → novo CI, sem pedir aprovação por commit. Deve continuar até os checks obrigatórios ficarem verdes, exceto quando houver decisão de produto/arquitetura, credencial, acesso ou ação proibida que exija o proprietário.
- O PR SHALL habilitar auto-merge após todos os checks obrigatórios e as revisões exigidas pela política do repositório. Não se deve enviar push extra apenas para iniciar o deploy.
- Após CI e merge, o mesmo fluxo SHALL executar preflight SSH somente-leitura sem aprovação do ambiente. Para isso, exige uma chave separada, restrita no `authorized_keys` a um comando de inventário, sem shell interativo, forwarding ou escrita. A chave de deploy atual não pode ser reutilizada nesse job.
- O preflight SHALL publicar inventário, SHA, serviços, portas, subdomínio, fingerprint, impacto e rollback como evidência revisável. Somente depois disso o job mutável SHALL referenciar `production` e aguardar a única aprovação humana do release.
- O job mutável SHALL revalidar fingerprint e SHA após aprovação e executar apenas serviços Pick-your-Pic previstos. Os gates faciais, infantis, legais, de capacidade e de operação existentes continuam obrigatórios; esta decisão não os aprova.
- A configuração GitHub ainda não tem evidência de auto-merge nem de credencial SSH read-only separada. Não enfraquecer o environment `production` nem alterar secrets; registrar como tarefa/bloqueio de configuração e continuar o trabalho independente.
