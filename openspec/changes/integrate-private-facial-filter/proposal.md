## Why

O spike `spike-private-facial-discovery` aprovou YuNet + SFace como baseline no Oracle ARM, e a jornada de cliente já converge para uma única Galeria pública com estado privado incorporado. A busca facial pode agora ser integrada como filtro opcional dessa superfície autorizada, sem criar outra galeria, seleção ou permissão a partir de uma inferência biométrica.

## What Changes

- Adicionar indexação facial assíncrona, versionada e isolada por Galeria pública depois que cada prévia interna limpa estiver pronta, sem marca d'água e sem bloquear a publicação da foto.
- Executar a indexação somente por eventos duráveis de foto nova, derivado alterado, versão trocada, backfill ou retentativa, sem varredura contínua da galeria; o worker deve permanecer ocioso sem consumir CPU quando a fila estiver vazia.
- Calcular, junto de cada face indexada, indicadores técnicos objetivos de nitidez local, corte nas bordas, tamanho/proeminência e pose para ranquear o rosto correspondente à consulta sem ocultar ou excluir fotos.
- Manter a indexação desligada por padrão no ambiente e, quando o operador habilitar o subsistema com configuração válida, criar/reconciliar automaticamente a política técnica interna de cada Galeria pública e indexar novas fotos sem declaração, preparação ou ativação manual do fotógrafo.
- Permitir que uma cliente autenticada e já autorizada envie uma referência temporária com exatamente um rosto após consentimento específico e destacado.
- Registrar e notificar o fotógrafo na interface administrativa quando uma cliente concluir o OTP e acessar uma galeria, sem transportar o OTP e sem duplicar o cadastro identificado pelo telefone normalizado.
- Exibir possíveis fotos encontradas no topo da mesma Galeria pública em dois blocos — melhores resultados e outros resultados — acima do acervo completo, sem chamar o resultado de identidade confirmada, sem ocultar foto autorizada e sem criar uma galeria privada.
- Reutilizar a seleção manual existente; a única privada operacional de `Galeria pública + cliente` nasce ou é reutilizada somente na primeira seleção consciente.
- Apagar automaticamente JPEG e embedding da referência em sucesso, falha, cancelamento ou timeout, além de oferecer cancelamento/exclusão manual idempotente e revogação.
- Isolar resultados, índices, jobs e auditoria por ambiente e galeria; nunca enviar embeddings ao navegador, WhatsApp, analytics ou logs.
- Expor progresso real de indexação para o fotógrafo e etapas/contagens reais da consulta para a cliente; sair, atualizar ou fechar a tela não cancela o job, que pode ser retomado pelo mesmo identificador opaco.
- Notificar pela interface os estados de qualidade, falha, índice incompleto e ausência de candidatos; enfileirar mensagem transacional idempotente e neutra quando a busca terminar, inclusive se a cliente não estiver mais na tela, sem expor biometria.
- Reconciliar o mandato, as diretrizes de frontend e a Fase 7 do roadmap: não existe grade anônima ou descoberta entre eventos; uma cliente com link, OTP e vínculo já pode ver a Galeria pública autorizada, e o filtro apenas reordena esse mesmo conjunto. Revisão do fotógrafo continua obrigatória se qualquer desenho futuro ampliar acesso.
- Preparar operação e observabilidade no ARM com fila de baixa prioridade, feature flag desligada por padrão, limites de concorrência e rollback sem apagar histórico comercial.
- Preservar a marca d'água exclusivamente nas prévias entregues ao cliente e apresentar aviso acessível de direitos autorais quando a cliente tentar copiar, arrastar, abrir o menu de contexto ou acionar captura suportada pelo navegador.

## Capabilities

### New Capabilities

- `privacy-biometric/facial-gallery-filter`: indexação biométrica por galeria, consentimento da consulta, filtro temporário, ciclo de vida, tratamento de menores, isolamento, auditoria e gates de ativação.
- `messaging/facial-search-notifications`: avisos transacionais idempotentes de busca sem candidatos, sem dado biométrico ou nova capacidade de acesso no payload.

### Modified Capabilities

- `gallery-sales/original-gallery-experience`: incorporar os resultados faciais como bloco temporário na Galeria pública, preservando a única jornada visual da cliente e a seleção comercial existente.
- `client-access/derived-galleries`: garantir que busca não crie privada e que a primeira seleção resolva a única privada operacional da cliente para aquela origem.
- `media-storage/protected-previews`: autorizar somente referências e prévias já visíveis na Galeria pública vinculada, sem expor original, embedding ou foto de outro escopo.
- `deployment-operations`: documentar configuração, dependências, limites e healthchecks do processamento facial opcional, sempre desligado por padrão e sem nova porta pública.

## Impact

- Backend FastAPI: contratos administrativos e de cliente, autorização, consentimento, auditoria, retenção e serviço de consulta.
- Worker/Redis: fila facial independente e de baixa prioridade, indexação idempotente, retentativa, cancelamento e limpeza.
- PostgreSQL/Alembic: estruturas aditivas para configuração da galeria, índice versionado, jobs/resultados temporários, consentimentos e auditoria sem armazenar a referência.
- Armazenamento local: modelos fixados por hash, índice criptografado por galeria e temporários de curta duração; nenhuma prévia servida do Google Drive.
- Frontend Next.js: painel administrativo informativo de progresso/falhas/retentativa automática, consentimento da cliente, upload/cancelamento, barras de progresso reais, retomada e blocos responsivos de melhores/outros resultados na galeria existente.
- Runtime: OpenCV headless, YuNet e SFace em worker ARM, com avaliador técnico objetivo versionado, espera bloqueante da fila e descarregamento ocioso configurável; nenhum serviço ou porta pública adicional.
- Dependência funcional: baseia-se nos contratos de jornada e unicidade de `consolidate-shared-private-galleries-and-progressive-sales` e não deve reintroduzir cards privados concorrentes.
- Operação: nenhum dado real de criança em homologação; ativação real permanece bloqueada até RIPD, textos jurídicos, mecanismo de representação legal, calibração permitida, revisão de segurança e autorização humana de deploy.
