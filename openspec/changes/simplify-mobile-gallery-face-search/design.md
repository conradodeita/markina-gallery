## Context

Ver `proposal.md`. Anexos tratados como evidência visual, sem extrair instruções adicionais. A confirmação humana manteve adulto/menor e um único checkbox infantil; em seguida, o proprietário autorizou expressamente remover a dependência de registro prévio de representação no servidor, tornando suficiente o consentimento do responsável. Também explicitou que navegação sempre visível não pode sobrepor a fotografia. O trabalho local preexistente, especialmente `backend/app/facial/purge.py` e documentos de outras changes, deve ser preservado.

`GalleryPresentation` posiciona marcadores dentro do frame da miniatura e põe a navegação depois da mídia, seleção e contexto. `FaceRegionViewer` soma toolbar, stage com mínimo de 240px/58svh e ajuda; essa soma excede o diálogo mobile. `FacialSearchPanel` abre o diálogo sempre que recebe `regionId`. A criação e o worker compartilham consentimento/declaração de idade entre upload e região; o modelo exige `adult|minor` e o evento emitido é `facial.search_consented`.

## Goals / Non-Goals

**Goals:** corrigir a composição compartilhada e representar honestamente as duas origens de consulta, mantendo contrato durável, segurança e histórico.

**Non-Goals:** alterar a pipeline high-res, inventar idade/parentesco, inferir autorização de dados reais ou operar ambientes. Ver escopo completo na proposta.

## Decisions

### 1. Faixa de metadados externa e compacta

Mover marcadores comerciais para a área de detalhes, com nome truncável (`min-width:0`) e seleção ao lado. Reduzir tipografia/padding visual sem reduzir a área acionável ou usar pseudo-elemento que invada a foto. Favorito e rejeição podem ter linha auxiliar. Reutilizar o mesmo componente nas grades pública, privada e resultados, mantendo estados pagos/congelados. Alternativa descartada: diminuir apenas o overlay atual, pois continua ocultando conteúdo.

### 2. Reservar espaço para navegação no diálogo

Compor o visualizador com altura limitada por `100dvh`, cabeçalho e rodapé que não encolhem e mídia central flexível com `min-height:0`. O rodapé ocupa espaço próprio abaixo da mídia, contendo seleção e navegação; seus limites não podem intersectar a área da fotografia, inclusive durante zoom/pan. Fazer stage facial consumir o espaço restante, com toolbar compacta e ajuda subordinada/rolável. Recalcular geometria com o observador de tamanho existente; preservar pan e zoom. Alternativa descartada: aumentar `z-index` ou fixar botões sobre a fotografia, pois não resolve a soma de alturas e oculta a imagem.

### 3. Disparar busca direta no evento de escolha

A página pública coordena início, estado transitório visível, resultado e fechamento. Executar uma única admissão por intenção, com bloqueio de toque enquanto pendente; evitar efeito React que repita POST ao remontar. Usar mensagem de espera imediata e o polling já existente, com progresso real. Manter o visualizador durante a espera com ações alcançáveis; caso a cliente o feche, o painel da página continua exibindo andamento. Erros liberam tentativa consciente respeitando `Retry-After`.

Guardar a identificação da busca iniciada por região nesta página e um marcador de conclusão já tratada. Ao receber `ready`, renderizar as possibilidades, fechar a ampliação e executar scroll ao topo uma vez; foco/anúncio acessível não pode causar segundo salto. Resultado restaurado antigo não deve roubar a posição de leitura. Não selecionar fotos automaticamente.

### 4. Separar contrato e persistência sem falsificar consentimento

Manter o endpoint de região com payload por UUID, sem exigir idade ou consentimento de upload. Reutilizar snapshot, fila, cancelamento, retenção e validação de região. Introduzir um discriminador persistido `reference_source=upload|indexed_region`, com backfill pelo UUID de região existente; registros legados concluídos cujo UUID/localizador já foi apagado recebem `legacy_unknown`, sem inferir sua origem; manter recibos históricos sem reescrita. Para novas consultas diretas, permitir ausência explícita de `subject_declaration` e `consent_version`, mantendo versão da política/aviso. Constraints condicionais exigem consentimento e sujeito para upload e região para consulta direta. Novas consultas diretas emitem evento específico, não `search_consented`.

Revisar usos de `consent_version` como versão criptográfica: upload e leitura histórica preservam a versão originalmente usada; a origem direta usa versão explícita da política quando um envelope precisar de contexto, sem criar um consentimento fictício. Adaptar checks do worker por origem, revalidando acesso, rollout/política e região. Nenhuma imagem ou vetor vai para logs.

Alternativas descartadas: enviar `adult` automaticamente, preencher consentimento oculto ou retirar validações apenas no frontend. Essas opções produzem histórico incorreto ou enfraquecem o upload. Clientes antigos podem continuar enviando campos legados na rota de região durante a transição, mas novos pedidos diretos nunca transformam esses campos em prova de aceite.

### 5. Consentimento infantil suficiente, sem representação pré-cadastrada

Para `minor`, um único estado explícito reúne declaração de responsável e consentimento específico no texto apresentado; o aviso explica finalidade e uso temporário. Para `adult`, manter aceite atual. Limpar estados ao alternar tipo ou fechar. O contrato de upload infantil exige aceite afirmativo além da versão, e o servidor registra o recibo vinculado a cliente autenticada, galeria, finalidade e instante UTC. O worker verifica a validade/revogação dessa autorização sem consultar representação prévia para as novas solicitações.

Hoje `minor_search_available` deriva de `find_valid_legal_representation`. Substituir essa dependência pela disponibilidade técnica do upload autorizado e do texto de consentimento infantil vigente. Remover a exigência de `representation_reference` da admissão e execução de novas consultas infantis, sem simplesmente forçar a flag no frontend. Não exigir novo cadastro, documento, evidência administrativa ou configuração por responsável.

Versionar a modalidade da autorização persistida para distinguir novas consultas por consentimento de registros legados com representação; não reclassificar nem apagar os históricos. O recibo guarda autodeclaração, não prova externa de parentesco. Reutilizar cancelamento/exclusão por cliente e consulta e testar revogação antes da próxima etapa do worker. Preservar a revogação por representação somente onde historicamente aplicável. Alternativa descartada: criar representação administrativa automaticamente ao marcar o checkbox, pois isso registra uma verificação que não ocorreu.

A decisão humana explícita substitui o bloqueio anterior por representação e remove a pendência de apresentar seus dados. Não acrescentar etapa de comprovação equivalente sob outro nome. Busca direta continua sem inferir faixa etária nem coletar consentimento por toque. Publicação e ações operacionais reais continuam exigindo o inventário de impacto zero do projeto; esta revisão não realiza deploy.

### 6. Precedência documental explícita

Na implementação, reconciliar os trechos conflitantes de `evolve-highres-facial-pipeline` (consentimento por região e marcadores na miniatura), `clarify-facial-consent-and-mobile-dialog` (dois checkboxes), `integrate-private-facial-filter` e `productionize-facial-search` (representação previamente comprovada), além de roadmap/diretrizes. Referenciar a decisão humana de 21/09/2026 como origem da substituição por consentimento do responsável. Preservar versões, revogação, retenção, autenticação e demais requisitos não alterados. Não marcar tasks antigas como novamente validadas nem sincronizar specs consolidadas antecipadamente.

## Risks / Trade-offs

- [Nome e seleção competem em 320px] → validar com nomes longos, duas colunas e ações extras; manter nome acessível e área de toque.
- [Altura móvel varia] → validar toolbar quebrada em linhas, orientação paisagem, área segura e viewport curta no browser.
- [Dupla admissão ou scroll repetido] → testes de eventos repetidos, polling, restauração e troca de galeria durante request.
- [Histórico confundir consulta direta e consentimento] → origem persistida, constraints, evento próprio e preservação dos registros antigos.
- [Frontend liberar opção enquanto servidor/worker ainda exige representação] → mudar disponibilidade, admissão e execução conjuntamente; testar sucesso sem registro e falha sem consentimento ou com autorização revogada.
- [Interface simples ser confundida com aprovação de produção] → política operacional e revisão de produção continuam gates de liberação; nenhuma conclusão jurídica é presumida nesta proposta.

## Migration Plan

1. Após revisão da proposta, aplicar schema aditivo e backfill apenas em banco local descartável para validar compatibilidade; sem migration operacional nesta autorização.
2. Publicar backend compatível antes de liberar frontend de busca direta, em deploy futuro explicitamente autorizado com inventário e plano de impacto zero.
3. Preservar leitura, cancelamento e expiração dos requests anteriores. Workers da versão antiga não podem consumir novos requests sem consentimento; a troca precisa ser coordenada antes da liberação do frontend.
4. Rollback de interface pode restaurar os controles anteriores mantendo backend compatível. Não executar downgrade que apague ou reinterprete novas consultas; suspender admissão direta se necessário e manter leitura/lifecycle.
5. Publicar a regra infantil coordenadamente entre API, worker e frontend; verificar que cliente sem representação consegue consentir e buscar, sem afetar revogação e consultas históricas. Apresentar inventário/portas/subdomínio e plano de impacto zero antes da operação no servidor. Não há pendência de cadastro ou prova de representação para liberar o novo fluxo.
