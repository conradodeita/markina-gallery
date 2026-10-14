> **Decisão substitutiva aprovada em 21/09/2026 — `simplify-mobile-gallery-face-search`:** para novas buscas, toque em região indexada inicia diretamente sem diálogo/aceite ou declaração de idade; upload continua exigindo consentimento específico. Upload infantil exige somente o checkbox único com autodeclaração de responsável e consentimento versionado, sem registro prévio ou prova administrativa de representação. Regras anteriores de representação obrigatória e dois checkboxes ficam substituídas exclusivamente nesse escopo; evidências/controles históricos permanecem. Nome/seleção ficam abaixo das miniaturas; navegação ampliada sempre visível em barra externa abaixo da fotografia, nunca sobreposta. Demais controles de acesso, retenção, revogação e operação permanecem. Contrato completo: `openspec/changes/simplify-mobile-gallery-face-search/`.

## Why

O índice atual usa uma prévia e reduz novamente os pixels antes do detector. Isso pode perder rostos pequenos, mas a cobertura por foto não mede recall. A evolução deve medir detecção separadamente da recuperação e permitir reutilizar regiões persistidas sem reprocessar prévias.

## What Changes

- Introduzir ingestão high-res temporária versionada e opt-in, com análise antes dos derivados/ajuste, retenção para retry, quotas, cleanup e remoção após artefatos duráveis.
- Implementar passes globais, multiescala e tiles seletivos, coordenadas na geometria orientada, deduplicação e métricas sem biometria nos logs.
- Evoluir PhotoFaceEmbedding com regiões normalizadas, proveniência e identificação explícita do espaço vetorial; reutilizar criptografia e isolamento existentes.
- Adicionar busca por região persistida, preservando consentimento, autorização, fila, snapshot e retenção existentes; distinguir correspondências, possibilidades e outras fotos.
- Adaptar ampliação com zoom/pan, seleção facial discreta e controles comerciais externos; reduzir visualmente seleção nas miniaturas.
- Criar benchmark reproduzível, calibração por modelo e avaliação documental do EdgeFace, sem ativação comercial presumida.
- Preservar legado sob flag; fotos high-res concluídas nunca retornam ao detector de prévias, inclusive em rollback.

## Capabilities

### New Capabilities
- `privacy-biometric/highres-facial-pipeline`: análise, regiões, consulta, benchmark e coexistência versionada. Complementa as changes faciais ativas, sem duplicar identidades.

### Modified Capabilities
- `media-storage/protected-previews`: fonte temporária e derivados duráveis para fotos que aderem ao pipeline novo.

## Impact

Backend de mídia/facial/ajuste, modelos e migration aditiva, APIs autenticadas, apresentação da galeria e testes. Nenhuma alteração de secrets, deploy, recursos Oracle ou limites de containers sem autorização operacional específica. O pedido de 19/09/2026 autoriza explicitamente planejar e depois implementar incrementalmente na mesma execução; prevalece sobre a pausa padrão da skill propose.

## Non-goals

Clustering, cadastro de pessoas, banco vetorial, RAW, dependência digiKam, retenção escondida de originais, troca automática para EdgeFace e habilitação em produção.
