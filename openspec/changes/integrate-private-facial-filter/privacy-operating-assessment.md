# RIPD operacional preliminar — filtro facial privado

## Escopo e finalidade

Este documento é um artefato técnico preliminar, não uma aprovação jurídica. A finalidade estrita é permitir que uma cliente já autenticada e vinculada reorganize temporariamente fotos que ela já pode visualizar em uma única Galeria pública. O resultado representa possibilidades, não identidade, não amplia acesso e não cria seleção, galeria privada ou compra sem ação consciente.

Tratamentos separados:

1. indexação do acervo autorizado, após a prévia ficar pronta;
2. referência enviada voluntariamente para uma consulta específica;
3. seleção comercial comum, que só começa quando a cliente escolhe uma foto.

## Papéis

| Papel | Responsabilidade mínima |
|---|---|
| Fotógrafo/empresa operadora da Markina | Controlador: define finalidade, base legal, galerias elegíveis, prazo, atendimento de direitos e eventual comunicação de incidente. |
| Infraestrutura/Markina Gallery | Operador técnico: executa somente instruções documentadas, segurança, retenção, auditoria, purge e comunicação de incidentes. |
| Provedor de hospedagem | Suboperador de infraestrutura conforme contrato e região aprovados, sem uso próprio de biometria. |
| Cliente autenticada | Titular ou representante que recebe transparência, decide enviar referência, pode cancelar/rejeitar e mantém seleção manual. |

A identificação nominal do controlador, canal de privacidade, contratos e região dos suboperadores MUST ser preenchida e revisada antes de qualquer piloto real.

## Minimização e retenção

- A referência é validada, cifrada em storage exclusivo e eliminada ao concluir, falhar ou cancelar, ou em no máximo 15 minutos.
- O embedding da consulta existe apenas em memória.
- Candidatas guardam somente foto, ordem e banda `best|other` por até 24 horas; não guardam score.
- Embeddings do acervo são cifrados e existem somente enquanto galeria, foto, finalidade, versão e política estiverem válidas.
- A outbox contém payload neutro cifrado e é limpa após entrega/cancelamento.
- Seleção, pedido e histórico comercial têm finalidade própria e não são eliminados junto com inferência facial.

## Transparência e textos versionados

Antes do upload, a UI MUST informar de modo destacado: finalidade limitada à galeria atual; natureza probabilística; ausência de confirmação de identidade; retenções; seleção manual disponível; exclusão automática; como cancelar/rejeitar; e, quando aplicável, o tratamento de dados de menores. O recibo registra versões de aviso e consentimento, declaração de faixa etária e UUIDs internos, nunca a imagem.

Mensagens externas serão neutras: “busca concluída”, “nenhuma possibilidade encontrada” ou “não foi possível concluir”; não revelarão pessoa, rosto, score, quantidade, foto ou nova capacidade de acesso.

## Direitos e revogação

O canal do controlador deverá permitir confirmação de tratamento, acesso às informações, correção cadastral, oposição/revogação quando aplicável, explicação do filtro, eliminação da referência/candidatas e contestação. A cliente pode cancelar a consulta e rejeitar candidata na UI. O operador autorizado pode desligar/revogar a finalidade e obter prova técnica de limpeza; o painel do fotógrafo mostra progresso e retentativa, sem declaração ou ativação jurídica por galeria. Nenhuma decisão exclusivamente automatizada produz compra ou bloqueio.

## Crianças e representação legal

O sistema não estima idade pela imagem. Em homologação privada, `minor_search_enabled` MAY ser habilitado somente para uma execução expressamente autorizada e vinculada a lote enviado pelo administrador/fotógrafo, com origem documentada, finalidade limitada, acesso autenticado, proteção criptográfica, retenção mínima e exclusão controlada. Fora desse modo de homologação, a busca infantil continua exigindo mecanismo não biométrico de comprovação de representação legal, texto específico, minimização adicional, análise do melhor interesse, procedimento de revogação e aprovação jurídica/humana. Homologação e benchmark podem usar dados reais de adultos e menores quando todos os gates operacionais forem registrados.

## Riscos e controles

| Risco | Controle atual | Gate residual |
|---|---|---|
| Falso positivo interpretado como identidade | linguagem de possibilidade, threshold conservador, sem score, seleção humana | calibração representativa permitida e revisão de texto |
| Vazamento entre eventos/clientes | FKs compostas, AAD por ambiente/galeria/objeto, autorização repetida | teste de intrusão/revisão independente |
| Persistência após falha | storage cifrado, deadline, cleaner durável e purge prioritário | observabilidade e alerta de SLA em homologação |
| Uso de dados de menores fora do lote autorizado | gate por ambiente/execução, origem documentada, acesso autenticado e ausência de inferência de idade | auditoria do lote, retenção e prova de exclusão |
| Degradação da mídia | worker/profile/fila separados e recursos limitados | ensaio concorrente no ARM alvo |
| Viés/calibração inadequada | autorização de homologação não transforma o default sintético em limiar de produção | corpus autorizado, representativo e avaliação de equidade |

## Critérios de calibração e equidade

Uma calibração real só poderá ser aprovada com origem/consentimento documentados, separação de treino/validação, câmeras/iluminação/pose/oclusão/tons de pele suficientemente representativos, métricas de detecção, precisão, recall, falso positivo, falso negativo e top-1 por cenário e grupos permitidos. O limiar deve priorizar redução de falso positivo, publicar intervalos de confiança e limites conhecidos, e nunca inferir atributos sensíveis. Diferença material entre grupos ou cenário sem amostra bloqueia ativação; não se corrige ocultando resultados de grupos afetados.

## Gate de aprovação

Permanecem obrigatórios: identificação formal de controlador/suboperadores; registro de origem, finalidade, autorização e retenção de cada lote real; revisão jurídica deste RIPD e dos textos antes de produção; mecanismo infantil fora do modo controlado de homologação; calibração permitida; ensaio de segurança; medição concorrente ARM; autorização humana de deploy e ativação; e prova de exclusão ao final. A flag permanece desligada fora da janela autorizada, e a autorização de homologação não habilita produção.
