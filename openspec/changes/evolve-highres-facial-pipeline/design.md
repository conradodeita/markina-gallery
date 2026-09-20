## Context

Ver proposal.md e audit.md. Reutilizar filas, envelopes AEAD, FK composta foto/galeria, MediaJob e PreviewAdjustment. O harness antigo possui provider próprio sem limite e não representa o runtime atual. Não existe corpus anotado disponível nesta execução.

## Goals / Non-Goals

**Goals:** eliminar a dependência de pixels reduzidos para fotos novas opt-in; preservar fluxos comerciais e legado; tornar estados, geometria e evidência reproduzíveis.

**Non-Goals:** escolher parâmetros de produção sem medição, implantar, trocar modelo sem licença/calibração, criar identidade ou infraestrutura vetorial.

## Decisions

1. Flag de admissão `FACIAL_HIGHRES_ENABLED=false` por padrão, subordinada aos gates faciais existentes. A adesão é persistida por foto e não desaparece ao desligar a flag. Fotos legadas conservam o caminho original; fotos aderentes nunca fazem fallback para detector de prévia. Rollback seguro desliga novas admissões e preserva suporte de leitura/lifecycle. Voltar a binário anterior à migration após remover fontes exige reupload: não prometer reversibilidade dos pixels apagados.
2. Registro único de processamento por foto, com fingerprint da fonte, dimensões orientadas, bytes, prazo, estado facial, descarte e métricas JSON sem vetores/caixas/landmarks. Índice high-res enfileirado no recebimento; MediaJob aguarda etapa facial. Conclusão facial libera derivados e ajuste existente. Falha terminal permite apresentação convencional, preservando fonte para retry até TTL. Remoção normal exige derivados verificados e ajuste vigente concluído ou desligado. Expiração gera estado explícito que exige reupload quando necessário. Locks por foto e exclusão idempotente protegem contra leitura/remoção concorrentes.
3. Admission quota global sob lock no banco antes de gravar arquivo, limite de bytes/fotos temporárias, reserva de disco e corpo limitado. Upload em arquivo temporário + rename atômico. Frontend continua envio progressivo; resposta 503/Retry-After impede acumulação ilimitada. Fragmentos próprios `.pyp-uploading` abandonados são varridos após TTL; MediaJob aderente recupera crash após 10 minutos e falhas após 30 segundos, até três tentativas por geração. Nenhuma cópia high-res permanente. Fonte removida só permite regeneração fotométrica/proteção da prévia limpa; não gera novos embeddings.
4. Detector global preserva orçamento atual. Plano high-res configurável: escala adicional e tiles sobre imagem orientada quando resolução, contagem, tamanho/confiança ou bordas indicam dificuldade. Hipóteses iniciais explícitas, sem alegação de calibração. Orçamento máximo de passes/tiles, candidatos (2048) e embeddings (256) limita custo; saturação é observável. Coordenadas/landmarks retornam ao espaço original antes de NMS e alinhamento no high-res. Embeddings calculados após dedup, sem crops persistentes.
5. Evoluir PhotoFaceEmbedding: modelo/dimensão, pipeline/pass, confiança e bbox normalizada nullable para legado. Não fabricar regiões para registros antigos. A versão do espaço vetorial acompanha consulta e índice; rejeitar combinações incompatíveis. Protocolo FaceEmbeddingProvider permite benchmark futuro usando mesmas detecções/alinhamento; somente SFace no runtime inicial.
6. GET de regiões e POST de consulta por UUID repetem autorização de navegação, pertencimento, disponibilidade, versão, consentimento, capacidade e rate limit. Consulta por região usa o job/snapshot existente, persiste apenas UUID de referência, sem recortar preview. Worker revalida região e escopo. Referência inválida/obsoleta falha fechada. Nenhuma concessão comercial.
7. Similaridade e qualidade técnica são eixos separados. `match_class=matched|ambiguous` nas candidatas; demais fotos continuam no acervo como outras fotos. Faixa ambígua opt-in por configuração calibrada; default conserva threshold legado sem fingir calibração. Não aplicar margem top1/top2 entre rostos de uma mesma pessoa sem evidência.
8. Regiões carregadas somente na ampliação autenticada; poucas aparecem discretamente, muitas requerem ação. Zoom/pan compartilham transformação com a imagem; regiões fora do viewport não capturam interação. Teclado, labels e alvos de toque ampliados. A seleção comercial fica em barra externa à imagem, miniaturas bottom-center.
9. Auto Adjustment mantém fila/engine/configuração/cleanup. Perfil atual é fotométrico. Exigir saída com mesma geometria e rejeitar transformação sem mapeamento; alterar exposição não cria job facial. Prévia nova com maior lado 1980 e JPEG adaptativo visando 250 KB, com piso de qualidade e sem corte.
10. Benchmark mede matching geométrico um-a-um contra caixas anotadas para recall; retrieval usa identidades pseudônimas e pares/top-k separadamente. Relatórios agregados incluem CPU, pico RSS, latência/throughput, configuração e hashes. Corpus/embeddings ficam fora do Git. ARM e carga de serviços são gates próprios, sem alterar limites por intuição.
11. Diagnóstico administrativo mantém somente a última tentativa por fonte. Falhas de provider transportam contagens sanitizadas até a transação de retry, mesmo após rollback; instâncias reutilizadas limpam métricas entre fotos. O endpoint existente de status da galeria pública agrega contagens/duração das fontes high-res e fila de indexação do mesmo escopo. Não é um histórico cumulativo de falhas nem recall; não usar cobertura como precisão. Métricas globais conservam as dimensões restritas existentes.

## Risks / Trade-offs

- [Retenção termina sem sucesso] → TTL explícito, erro/reupload e nenhum falso estado concluído.
- [CPU maior e memória high-res] → tiles sequenciais, máximo de pixels/passagens e pressão de fila/disco; medir ARM antes de habilitar.
- [Consentimento infantil por clique] → mesmos controles da selfie; não interpretar clique como representação legal.
- [Pesos EdgeFace] → código BSD-3-Clause não implica licença comercial dos pesos oficiais CC-BY-NC-SA-4.0; produção bloqueada para esses artefatos.
- [Legado sem original após migração] → não reindexar automaticamente e exigir reupload quando fonte faltar.

## Migration Plan

Migration aditiva após 0056; campos legados recebem modelo/dimensão atuais e pipeline legacy-preview-v1, sem inventar coordenadas. Criar tabela de lifecycle com FK cascade e validações. Upgrade/downgrade somente em banco descartável local nesta execução; downgrade estrutural não é rollback operacional. Testar flag desligada/ligada/desligada e coexistência. Nenhuma fonte existente será apagada retroativamente. Deploy requer inventário, backup, portas/subdomínio e autorização específica.

## Open Questions

Corpus real, anotação, limiares finais e configuração ARM dependem da medição; defaults são hipóteses de homologação. Autorização privada recebida; origem e caminho ainda pendentes.
