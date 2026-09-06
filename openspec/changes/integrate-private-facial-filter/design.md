## Context

Consulte `proposal.md` e os resultados de `spike-private-facial-discovery`. O baseline YuNet + SFace obteve 14,36 fotos/s no Oracle ARM com 2 CPUs, 100% de cobertura no corpus sintético, zero falsos positivos e recall de 98,62% no limiar preliminar `0,750`. Esses números aprovam a base técnica, mas não autorizam dados reais nem tornam o limiar definitivo.

A aplicação já possui prévias protegidas, `MediaJob`, worker, Redis, auditoria, outboxes e seleção persistente. A change `consolidate-shared-private-galleries-and-progressive-sales` define Galeria pública como superfície principal da cliente e garante uma privada operacional por `Galeria pública + cliente`; esta change depende desses contratos e não pode reintroduzir propriedade exclusiva ou dois cards concorrentes.

O roadmap ainda descreve revisão do fotógrafo antes de liberar qualquer resultado. Ele será atualizado para distinguir grade anônima proibida de filtro dentro de uma galeria já autorizada: revisão permanece obrigatória somente quando o resultado ampliar acesso.

## Goals / Non-Goals

**Goals:**

- integrar indexação e busca sem acoplar disponibilidade de mídia à biometria;
- garantir isolamento por ambiente, galeria e cliente no banco, fila, armazenamento e API;
- tornar referência e embedding temporários efêmeros por construção;
- reutilizar autorização, prévias e seleção existentes;
- manter rollout reversível, observável e desligado por padrão;
- permitir implementação e testes locais completos sem exigir ativação jurídica.

**Non-Goals:**

- autenticar cliente por rosto, estimar idade, inferir atributos ou identificar uma pessoa como verdade;
- treinar ou ajustar modelo automaticamente com fotos, seleções ou feedbacks;
- criar grade anônima, pesquisar entre eventos ou ampliar acesso por resultado;
- usar dados reais de crianças em homologação;
- introduzir vector database, serviço externo de reconhecimento ou pesos sem licença comercial;
- habilitar produção, definir parecer jurídico ou substituir seleção manual.

## Decisions

### 1. Dependência explícita da jornada consolidada

A implementação usará o resolvedor transacional e o contrato `journeys` da change `consolidate-shared-private-galleries-and-progressive-sales`. A busca não conhecerá `DerivedGallery` e retornará apenas `PhotoAsset.id`; selecionar candidata chamará a mesma mutation manual que resolve a privada e grava `PhotoSelection`.

Alternativa rejeitada: gravar fotos encontradas como origem `facial` na privada. Isso compartilharia inferências entre membros, criaria a privada antes da intenção de compra e confundiria filtro com acervo autorizado.

### 2. Gate operacional global e política interna automática

`FACIAL_PROCESSING_ENABLED=false` será o kill switch de ambiente. Quando o operador habilitar o subsistema com todas as versões, chaves e modelos válidos, o backend criará ou reconciliará automaticamente uma `GalleryFacialPolicy` interna para cada Galeria pública ativa, com versão do aviso, referência da hipótese legal, política infantil, limiar e modelo. Somente uma política interna `active` e coerente permite novos jobs.

O fotógrafo não declara autorização, não prepara política e não ativa o filtro por galeria na interface. O painel é informativo: progresso, falhas sanitizadas e retentativa. A autorização operacional para dados reais continua externa ao fluxo da galeria e bloqueada se a configuração de ambiente não declarar versões jurídicas aprovadas; testes e homologação usam somente configuração sintética adulta explícita.

Alternativa rejeitada: um checkbox ou declaração do fotógrafo por galeria. Isso transfere ao usuário uma decisão operacional que deve ser validada pelo ambiente e cria uma etapa sem valor na rotina de upload.

### 3. Face worker separado, orientado a eventos e sem porta

Um serviço `face-worker`, opcional e sem porta, consumirá de forma bloqueante uma fila Redis própria com prioridade inferior à geração de prévias. Ele terá imagem/dependências específicas, limites configuráveis e somente os mounts necessários. API e worker de mídia não carregarão OpenCV ou pesos. Não existirá laço que revisite continuamente uma galeria: jobs nascem somente de eventos persistidos ou de uma reconciliação idempotente executada uma vez no startup para políticas ausentes ou versões divergentes.

O processo poderá manter os modelos carregados durante um lote, mas deverá descarregá-los depois de um período ocioso configurável e limitar jobs por processo. Quando a fila estiver vazia, permanecerá sem consumo ativo de CPU. Reinício do container não perde trabalho porque fila, lease e progresso pertencem ao banco/Redis, não à memória do navegador ou do worker.

Os pesos YuNet/SFace não entram no Git: o build isolado baixa URLs fixadas, valida tamanho/SHA-256 e preserva licenças. O startup compara manifest, configuração e arquitetura; divergência deixa o subsistema indisponível sem derrubar API ou seleção manual.

Alternativas rejeitadas: executar inferência na request, no worker geral ou varrer cada galeria continuamente. Essas opções aumentam latência, mantêm recursos ocupados sem trabalho e permitem que o lote facial prejudique prévias, mensagens e lifecycle.

### 4. Modelo aditivo sem pgvector

A escala MVP de 500–1.000 JPEGs por evento permite comparação linear vetorizada em memória. Evitaremos extensão PostgreSQL ou serviço vetorial nesta change. A migration aditiva criará:

- `gallery_facial_policies`: gate e versão por Galeria pública;
- `photo_face_embeddings`: galeria, foto, ordinal do rosto, modelo, versão de embedding, versão de qualidade, banda técnica, indicadores técnicos cifrados, ciphertext, nonce, key id, timestamps, fingerprint da prévia e unicidade versionada;
- `facial_jobs`: tipo `index|purge|search|cleanup`, escopo, estado, lease, tentativas e erro sanitizado;
- `facial_search_requests`: galeria, cliente, estado, aviso/consentimento, declaração de representação, referência opaca temporária, expiração e limpeza;
- `facial_search_snapshot_items`: IDs e fingerprints das fotos congeladas por request, com estado `pending|ready|excluded`, sem vetor ou score;
- `facial_search_candidates`: request, foto, rank e banda técnica pública (`best|other`), sem identidade, similaridade ou pontuação técnica persistida em claro;
- outbox específica para notificação de ausência de candidatos.

Índices cobrirão jobs pendentes, embeddings por `(gallery_id, model_version)`, requests por `(client_id, gallery_id, expires_at)` e candidatos por request/rank. Chaves estrangeiras e checks impedirão cruzamento de galeria. Similaridade existe somente em memória durante a ordenação.

Alternativa rejeitada: pgvector agora. Para o volume medido, ele acrescentaria extensão, migration e operação sem benefício proporcional; a troca futura fica atrás de um repositório de embeddings.

### 5. Criptografia vinculada ao contexto

Embeddings persistentes e referências temporárias usarão AEAD com chave de servidor versionada fora do Git. Nonce aleatório e AAD incluirão ambiente, galeria, foto/request, modelo e versão para impedir transplante de ciphertext entre escopos. A API grava o upload já cifrado em volume temporário exclusivo; somente o face worker decifra em memória.

O embedding da consulta nunca será persistido. Embeddings do acervo ficam cifrados em `BYTEA`; o worker carrega e decifra apenas o evento solicitado. Rotação de chave agenda recriptografia/reindexação controlada e não aceita fallback silencioso.

Alternativa rejeitada: vetor em claro no PostgreSQL ou Redis. Isolamento lógico não reduz o impacto de cópia indevida do banco/cache.

### 6. Pipeline de indexação incremental e idempotente

Quando `admin_preview` e `client_preview` concluem, um hook pequeno garante a política técnica interna automática e grava job facial na mesma transação, com chave `(photo_id, preview_fingerprint, model_version, quality_version)`. Essa variante interna é redimensionada diretamente do original, não recebe marca d'água e não é servida à cliente. O face worker valida novamente política e foto antes de processar, detecta zero ou mais rostos, cria embeddings e métricas técnicas de cada rosto e substitui atomicamente apenas a versão daquela foto. A `client_preview` protegida continua sendo a única variante usada para apresentação e autorização visual da cliente. Falha grava estado retomável e não altera `processing_status` da mídia.

No startup, o face worker reconcilia uma única vez galerias ativas sem política ou com versão divergente e agenda backfill paginado apenas para as prévias internas limpas ainda não compatíveis, exigindo também que a prévia protegida esteja pronta antes de expor qualquer candidata. Foto nova ou derivado limpo alterado agenda somente seu próprio job; troca de versão agenda reindexação explícita. Desligar globalmente interrompe novos jobs; excluir ou retirar foto agenda purge prioritário. Uma limpeza reconciliadora procura temporários vencidos e índices sem origem válida, sem recalcular fotos saudáveis.

Alternativa rejeitada: varrer pasta em background sem jobs duráveis ou manter scan recorrente por galeria. Isso perde auditoria, idempotência e capacidade de retomar depois de falha, além de consumir recursos sem alteração de conteúdo.

### 7. Consulta efêmera com autorização repetida

Endpoints propostos:

- `GET /api/admin/galleries/{gallery_id}/facial-index` para contagens e progresso real;
- `POST /api/admin/galleries/{gallery_id}/facial-index/retry`;
- `GET /api/client/galleries/{gallery_id}/facial-search` para disponibilidade/aviso;
- `POST /api/client/galleries/{gallery_id}/facial-searches` para consentimento e upload;
- `GET /api/client/facial-searches/{request_id}` para estado/candidatas;
- `DELETE /api/client/facial-searches/{request_id}` para cancelamento/exclusão idempotente;
- `POST /api/client/facial-searches/{request_id}/candidates/{photo_id}/reject` para feedback.

Cada rota resolve sessão e vínculo novamente; `request_id` nunca concede acesso sozinho. Upload aceita JPEG/PNG decodificável com limites de bytes, pixels e dimensões, remove metadados, exige um rosto e não segue conteúdo/URL remota. A referência cifrada é removida antes de confirmar o estado terminal. A consulta é durável: polling, refresh, fechamento da aba ou troca de dispositivo não cancelam o job.

Ao criar a consulta, o backend congela um `index_snapshot` com a quantidade e os fingerprints elegíveis. Se esse snapshot ainda estiver sendo preparado, o job aguarda os itens pendentes e publica progresso real `ready/total`; fotos carregadas depois pertencem a uma nova geração e não alteram silenciosamente a busca em andamento. Resultados guardam somente fotos que ainda passam pela mesma autorização de listagem e prévia. Uma mudança de vínculo, política ou galeria cancela/oculta o resultado imediatamente.

### 8. Limiar conservador e estados

`0,750` será apenas default sintético versionado para testes. A configuração real não poderá ser ativada sem versão de calibração aprovada. Estados externos serão `unavailable`, `consent_required`, `queued`, `waiting_index`, `validating_reference`, `searching`, `ranking`, `ready`, `no_face`, `multiple_faces`, `low_quality`, `index_incomplete`, `no_candidates`, `cancelled`, `expired` e `failed`.

A resposta inclui rank e IDs, não score. O texto sempre fala em possibilidades. Feedback negativo remove candidata daquele request e cria métrica agregada; nunca altera modelo, limiar ou outro resultado automaticamente.

### 9. UX na mesma Galeria pública e progresso retomável

O frontend mostrará `Procurar por reconhecimento facial` como ação opcional, modal de consentimento destacado, upload mobile-first, progresso cancelável e mensagens orientativas. O fotógrafo verá indexação automática com `prontas/total`, fila, processamento, falhas e retentativa, sem botões de preparar, ativar, suspender ou revogar política. A cliente verá etapas e contagens reais do snapshot; não haverá percentual inventado quando uma etapa não expuser unidade mensurável.

Resultados aparecem acima das pastas em `Melhores resultados encontrados` e `Outros resultados encontrados`, seguidos pelo acervo integral. Os três blocos reutilizam o mesmo card/favorito/seleção; uma foto repetida visualmente referencia o mesmo estado, e selecionar ou desmarcar atualiza o resumo e a cotação existentes.

A UI não mantém referência em local storage, não renderiza score e não cria rota/card de “galeria facial”. Ela mantém apenas o `request_id` opaco necessário para retomar a consulta autorizada; perder esse identificador não concede nem revoga acesso. Depois da limpeza, mostra evidência de que a referência foi apagada. A alternativa manual permanece visível em todos os estados.

A apresentação da cliente mantém a marca d'água como mecanismo de desestímulo à cópia e intercepta menu de contexto, cópia e arraste, além do evento de captura quando disponibilizado pelo navegador. Nessas tentativas, abre um diálogo acessível com referência informativa à Lei nº 9.610/98, artigo 79, pedido de não copiar/compartilhar e confirmação explícita. O texto não afirma que JavaScript impede screenshots, ferramentas externas ou acesso técnico à resposta: a proteção material continua sendo a prévia degradada e marcada. A prévia administrativa limpa usada pela análise facial não é incorporada ao HTML da cliente nem autorizada por rotas públicas.

A configuração global de proteção visual preserva texto repetido e adiciona transparência, sombra, alinhamento principal em nove posições e linhas diagonais cruzadas opcionais. Esses campos pertencem a `BrandingSettings`, recebem defaults compatíveis e são aplicados somente durante a geração de `client_preview`. Salvar a proteção reenfileira a geração de derivados, porém a idempotência facial usa o fingerprint de `admin_preview`; portanto uma mudança puramente visual não cria reindexação biométrica desnecessária.

### 10. Consentimento da referência e tratamento de menores

A indexação técnica do acervo é governada pela configuração operacional do ambiente e não pede declaração do fotógrafo dentro da galeria. O checkbox da cliente cobre somente o uso temporário da foto de referência para procurar possíveis correspondências naquela Galeria pública autenticada; o recibo é versionado, isolado por cliente e eliminado junto dos dados temporários conforme a retenção. Para referência declarada de criança, `minor_processing_mode` exige representação legal comprovada por mecanismo não biométrico definido e habilitado; até lá o backend recusa. O sistema não estima idade pela face.

Homologação usa somente adultos sintéticos. Testes de fluxo infantil usam flags e fixtures sem imagem humana. RIPD e textos aprovados são artefatos operacionais obrigatórios antes de qualquer piloto com dado real.

### 11. Retenção, revogação e auditoria

O arquivo de consulta expira no primeiro estado terminal ou em 15 minutos. Candidatas expiram em 24 horas. Índices do acervo sobrevivem apenas enquanto política, finalidade, foto, galeria e versão forem válidas. Exclusão da origem apaga o índice mesmo se uma referência de mídia sobreviver em privada/histórico.

`AuditEvent` registrará UUIDs internos, versões, estados, contagens e motivos; nunca imagem, vetor, score, caixa ou nome inferido. Exclusão manual e automática usam a mesma operação idempotente. Jobs de purge têm prioridade sobre indexação/search e alerta se ultrapassarem o SLA.

### 12. Notificação de conclusão

Ao terminar em `ready`, `no_candidates` ou falha terminal recuperável pela cliente, a transação cria uma outbox com chave `facial-search:{result_kind}:{request_id}`. O payload cifrado usa somente destinatário já verificado, texto neutro e link que continua sujeito à sessão/autorização normal; não inclui imagem, nome procurado, score, quantidade de correspondências ou IDs de foto. A mensagem pode ser entregue mesmo depois de a cliente fechar a tela. Falha do canal não reabre a busca nem impede o resultado na interface.

### 13. Ranqueamento técnico não destrutivo por rosto correspondente

O runtime inicial não incorporará digiKam, Facet ou outro aplicativo completo. YuNet + SFace permanecem responsáveis por detecção e correspondência; um avaliador OpenCV versionado calcula nitidez local na região facial, folga das bordas, proporção/proeminência e pose aproximada a partir da caixa e landmarks. O OFIQ será comparado em spike isolado no ARM e só poderá substituir ou complementar o avaliador se desempenho, precisão e licenças de código, pesos e dependências forem aprovados.

A similaridade primeiro aplica o gate conservador de candidata. Entre candidatas, somente o ordinal facial que correspondeu à referência participa da qualidade. `best` exige correspondência forte e todos os gates técnicos mínimos; `other` preserva correspondências possíveis com qualidade inferior. Qualidade nunca remove, oculta, vende ou cria seleção. O sistema não calcula beleza, emoção, gênero, raça, idade, atratividade ou valor estético da pessoa.

Alternativa rejeitada: avaliar a foto inteira, o maior rosto ou o centro como sujeito. Em eventos e grupos, isso pode favorecer outra pessoa e reduzir a utilidade para quem realizou a busca.

### 14. Reconciliação normativa

`INSTRUCOES_EXECUTOR_CLAUDE_CODE.md`, `DIRETRIZES_FRONTEND_MARKINA_GALLERY.md` e `ROADMAP_ARQUITETURA.md` serão reconciliados junto da implementação: “pública” significa compartilhável por link opaco, OTP e vínculo, não anônima. A proibição de grade aberta e pesquisa entre eventos permanece. Quando o filtro apenas reordena fotos já autorizadas, a escolha da cliente é a revisão humana; se uma mudança futura usar o resultado para liberar conteúdo antes oculto, revisão do fotógrafo e nova change voltam a ser obrigatórias.

### 15. Notificação de acesso autenticado

Cada verificação OTP concluída em contexto de galeria reutiliza o cadastro único pelo telefone normalizado, registra o acesso e cria uma notificação administrativa idempotente por desafio consumido, com cliente, Galeria pública e horário. O payload nunca contém OTP. A notificação não exige aprovação do fotógrafo nem altera a autorização já concedida pelo link e pelo login.

## Risks / Trade-offs

- [Base legal inadequada para pessoas incidentais] → flag global e política interna automática fail-closed; RIPD e revisão jurídica antes de dado real.
- [Falso positivo apresentado como identidade] → limiar conservador, linguagem de possibilidade, sem score, seleção consciente e feedback sem treinamento.
- [Vazamento entre eventos ou membros] → FKs compostas, AAD por escopo, autorização repetida e testes negativos com IDs trocados.
- [Referência permanece após crash] → armazenamento cifrado, deadline no banco e cleaner independente com retentativa/auditoria.
- [Fila facial degrada prévias] → serviço separado, prioridade baixa, limites de recursos e backpressure.
- [Modelo ou wheel muda silenciosamente] → versões e hashes fixados, startup fail-closed e reindexação explícita.
- [Banco copiado expõe vetores] → AEAD por registro e chave externa versionada; ainda exige controle de acesso e backup cifrado.
- [Comparação linear não escala] → limite por galeria, métricas e interface de repositório; pgvector somente em change futura baseada em volume real.
- [Métrica de qualidade favorece outro rosto ou uma estética arbitrária] → avaliar somente o rosto correspondente, usar fatores técnicos explicáveis e manter todos os resultados/autoria da escolha.
- [Worker ocioso retém memória ou reprocessa a galeria] → espera bloqueante, fingerprint/versionamento, descarregamento ocioso e ausência de scan recorrente.
- [Cliente fecha a tela e perde o resultado] → job e snapshot duráveis, consulta retomável e outbox idempotente de conclusão.
- [Índices antigos sobrevivem à nova configuração] → versões jurídicas e técnicas fazem parte da assinatura interna; mudança invalida e agenda reindexação controlada.
- [Dois clientes compartilham inferência] → request/candidate sempre possui `client_id`; somente `PhotoSelection` consciente segue para o modelo comercial individual.

## Migration Plan

1. Reconciliar roadmap e confirmar que a change de jornada consolidada está aplicada no código alvo.
2. Adicionar migration somente aditiva e testes de upgrade/head, sem ligar o kill switch do ambiente.
3. Introduzir criptografia, repositórios, jobs e face worker com modelos verificados; manter `FACIAL_PROCESSING_ENABLED=false`.
4. Implementar APIs e frontend com indisponibilidade explícita quando a flag estiver desligada.
5. Executar testes unitários, integração, contratos, concorrência, retenção, segurança e corpus sintético local; validar que busca não cria entidade comercial.
6. Preparar inventário e runbook de homologação, incluindo CPU/memória/disco, modelos, secrets e rollback; nenhuma imagem real infantil.
7. Em deploy futuramente autorizado, aplicar backup/migration, publicar com flag desligada e validar healthchecks/smoke sintético.
8. Habilitar somente o piloto sintético adulto por operação autorizada; deixar o reconciliador automático criar políticas internas e observar fila e limpeza antes de ampliar.

Rollback: desligar o kill switch, cancelar novas operações, executar purge idempotente e retornar aplicação/face worker à versão saudável. As tabelas aditivas permanecem para auditoria e limpeza; nenhuma down migration destrutiva será executada.
