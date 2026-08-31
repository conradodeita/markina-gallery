## Context

Consulte `proposal.md` para a motivação. Hoje `SaleOrder.derived_gallery_id` e `SaleOrderItem.photo_asset_id` são chaves obrigatórias para entidades operacionais; por isso a exclusão física dessas entidades também quebraria a consulta do histórico. A exclusão da entidade interna `ParentGallery`, que passa a ser chamada de “Galeria pública” no produto, aceita somente galerias vazias, e a remoção de arquivos ocorre em pontos síncronos sem um manifesto durável da limpeza.

O armazenamento operacional contém original e derivados protegidos referenciados pelo acervo-mãe. As galerias privadas reutilizam essas referências, enquanto pedidos já possuem snapshots parciais de cliente, preço, PIX e nome de arquivo. A mudança atravessa banco, filesystem, worker, APIs e duas interfaces, e precisa preservar privacidade, autorização e auditabilidade.

## Goals / Non-Goals

**Goals:**

- separar de forma explícita o ciclo de vida público da origem, o ciclo de vida das galerias privadas derivadas e o ciclo de vida comercial;
- materializar a galeria privada somente por primeira seleção autorizada ou criação administrativa explícita;
- separar fotos disponíveis na galeria privada de seleções para compra e registrar a procedência de cada disponibilidade;
- manter a Galeria pública autorizada acessível depois da derivação para permitir seleções adicionais na mesma privada;
- encerrar automaticamente uma galeria privada derivada pelo cliente somente quando ela ficar sem referências disponíveis e sem impedimento comercial;
- centralizar no backend o modo de acesso, a autorização por link/convite e a herança de configuração da Galeria pública;
- tornar exclusão e desvinculação idempotentes, auditáveis e retomáveis;
- preservar, sem duplicação, a mídia ainda referenciada por galerias privadas e somente a mídia histórica necessária a itens comprados;
- manter uma experiência administrativa de uma confirmação e um acompanhamento, sem exigir limpeza manual prévia;
- minimizar PII transitória de OTP depois que ela deixa de ser operacionalmente necessária.

**Non-Goals:**

- permitir exclusão do cadastro de cliente nesta change;
- apagar ou reescrever transações financeiras confirmadas;
- restaurar uma galeria operacional excluída;
- renomear em massa classes, tabelas e migrations históricas que usam `responsible`; a padronização obrigatória é do contrato novo e da interface visível;
- criar um arquivo frio de todas as fotos não compradas ou servir prévias a partir do Google Drive;
- permitir configuração específica por galeria privada que sobrescreva o modelo herdado da Galeria pública;
- habilitar busca facial antes da conclusão e aprovação do spike específico;
- expor grade de fotografias de evento coletivo sob a denominação “Galeria pública”;
- modelar nesta change a distinção futura entre `Client` e pessoa fotografada/dependente.

## Decisions

### 1. Pedidos permanecem como fonte do histórico, mas deixam de depender de FKs operacionais

`SaleOrder` continuará sendo o agregado comercial. A migration tornará `derived_gallery_id` anulável com `ON DELETE SET NULL` e adicionará snapshots de identificador/nome da galeria privada e da Galeria pública. `SaleOrderItem.photo_asset_id` também se tornará anulável com `ON DELETE SET NULL`, mantendo nome, preço, checksum e metadados históricos do item. `client_id` continuará obrigatório porque a change proíbe apagar clientes.

Os snapshots serão preenchidos retroativamente antes de liberar as constraints novas. A exclusão só poderá remover as entidades operacionais depois de confirmar que os pedidos afetados possuem os campos históricos obrigatórios.

Alternativas consideradas:

- copiar pedidos inteiros para tabelas de arquivo: duplicaria regras e consultas, aumentaria risco de divergência e dificultaria auditoria;
- manter toda a galeria e todas as fotos como soft delete: não atende à higienização física; a decisão adotada mantém apenas o registro mínimo da origem e ativos ainda referenciados por privadas, removendo fisicamente o restante.

### 2. Mídia histórica comprada terá armazenamento e metadados próprios

Será criado um registro por item comercial preservável, vinculado a `SaleOrderItem`, contendo chaves de armazenamento, checksum, tipo, tamanho e estado da preparação. Antes de remover um `PhotoAsset`, o worker preservará somente uma prévia histórica mínima e protegida e a referência ou o entregável final a que a compra dá direito, em namespace derivado do UUID do item, verificará checksum e persistirá o manifesto. A chave não conterá nome ou telefone. O original SHALL NOT ser copiado apenas para compor histórico quando uma referência segura de entrega já atender ao direito adquirido.

Itens de pedidos confirmados preservam evidência visual mínima e a entrega ou referência final autorizada. Pedidos pendentes ou cancelados preservam metadados financeiros e de auditoria, mas não justificam reter mídia. Fotos sem item comprado são apagadas com todos os derivados operacionais. A política de retenção será configurável e documentada; esta change não inventa prazo legal. Solicitações de privacidade removem ou anonimizam PII quando permitido, sem apagar os registros contábeis e de auditoria que precisem permanecer.

Alternativas consideradas:

- manter o original inteiro para qualquer pedido: amplia retenção e exposição além do necessário;
- guardar apenas o nome do arquivo: não cumpre a biblioteca visual e a entrega histórica exigidas pelas specs consolidadas.

### 3. Exclusão e desvinculação usarão uma operação durável de ciclo de vida

Uma tabela de operação registrará tipo (`delete_parent_gallery` ou `unlink_client`), alvo, ator, chave de idempotência, estado (`queued`, `preparing_history`, `removing_storage`, `removing_records`, `completed`, `failed`), manifesto de contagens, erro sanitizado e horários. O `DELETE` interno de `ParentGallery`, apresentado como exclusão da Galeria pública, passará a responder `202` com o identificador da operação; um endpoint de consulta retornará progresso. Repetir a solicitação com a mesma chave retornará a operação existente.

O início da operação coloca a galeria em `deleting`, bloqueia novos uploads, vínculos, seleções e checkout. O worker executa:

1. bloqueio transacional e inventário do alvo;
2. preenchimento dos snapshots comerciais ausentes;
3. preparação e verificação da mídia histórica comprada;
4. persistência do manifesto de chaves operacionais a remover;
5. remoção ordenada de vínculos e capacidades públicas, fotos sem referência privada e pastas esvaziadas; a origem é convertida em registro interno removido enquanto privadas, referências, arquivos e configuração herdada necessários à sua visualização permanecem;
6. limpeza idempotente somente das chaves operacionais sem referência privada e conclusão auditada.

Se a limpeza física falhar depois da remoção lógica, o manifesto independente permite nova tentativa. Se a preparação histórica falhar, nenhuma entidade comercial ou operacional é apagada e a galeria permanece bloqueada até retomada ou cancelamento seguro antes da fase destrutiva.

A desvinculação reutiliza o mesmo mecanismo para uma relação cliente–galeria. Ela remove `ParentGalleryRegistration`, a galeria derivada e interações não comerciais daquela relação; pedidos e mídia comprada são preparados e destacados antes da remoção. Outras galerias do cliente não entram no manifesto. A exclusão da Galeria pública, por outro lado, não equivale à desvinculação: ela encerra a origem compartilhável, mas conserva cada privada existente e as fotos que ela referencia.

Alternativa considerada: uma única transação HTTP com operações de filesystem. Foi rejeitada porque banco e filesystem não compartilham transação e uma interrupção poderia deixar um resultado impossível de comprovar ou retomar.

### 4. Galerias privadas separarão disponibilidade de seleção e serão materializadas sob demanda

A Galeria pública é a origem compartilhável do fluxo, mas “pública” é uma denominação de produto, não uma autorização universal. Ao abrir seu link, o backend exige sessão `client` antes de entregar fotos. Sem sessão, a interface encaminha ao login preservando um destino interno validado; depois do OTP, retorna à mesma origem. Com sessão válida, o backend cria ou reutiliza de forma idempotente o registro individual entre `Client` e Galeria pública, sem novo OTP. Esse registro não cria automaticamente uma `DerivedGallery` fora da seleção e não concede acesso a nenhuma galeria privada existente. Um cadastro feito pelo administrador só autoriza a Galeria pública explicitamente associada; existir na tabela `Client` não concede acesso global.

Uma galeria privada pode nascer por dois caminhos que usam o mesmo serviço transacional:

1. o cliente autenticado seleciona sua primeira foto em uma Galeria pública comum cuja navegação foi habilitada pelo fotógrafo; o serviço cria a `DerivedGallery`, cria a referência disponível com origem `client` e registra a `PhotoSelection` na mesma transação;
2. o administrador escolhe um cliente e ao menos uma foto da Galeria pública; o serviço cria o vínculo, a `DerivedGallery`, referências disponíveis com origem `admin` e um convite seguro na mesma operação, sem registrar seleção de compra em nome da cliente.

`DerivedGalleryPhoto` (ou entidade equivalente) representa uma foto disponível na privada; `PhotoSelection` representa a escolha comercial feita pela cliente. Cada referência disponível terá procedência (`admin`, `client` e, somente após change própria, `facial`). Uma privada criada pelo administrador pode permanecer com zero seleções enquanto possuir referências disponíveis. Desmarcar uma foto de origem `client` remove sua seleção e pode remover a referência criada exclusivamente por essa seleção; desmarcar SHALL NOT remover uma referência de origem `admin` nem transformar disponibilidade administrativa em escolha comercial.

Haverá no máximo uma galeria privada operacional por par `Galeria pública + Client`. O telefone normalizado em E.164 e comprovado por OTP é a chave de deduplicação: o backend primeiro procura telefone ativo verificado e depois o telefone canônico de `Client`, sempre sob constraints únicas e tratamento de concorrência. Se encontrar, reutiliza o mesmo `client_id`, preserva o nome cadastrado e não cria duplicata; o nome informado funciona apenas no primeiro cadastro por link válido ou em alteração administrativa própria. Se não encontrar e houver contexto válido de Galeria pública, cria um único `Client` depois do OTP; sem esse contexto, mantém a negativa já especificada. O link privado é localizador e convite, não credencial suficiente: mesmo em posse dele, outro telefone recebe negação neutra. Uma pessoa que acessa a Galeria pública não recebe IDs, metadados ou fotos das galerias privadas de outros clientes.

O vínculo automático usa somente uma sessão `client` válida, um token válido e o modo de acesso declarado no backend. Reabrir o mesmo link não duplica registro, não modifica nome/telefone e não altera a galeria privada correspondente.

A derivação não substitui nem oculta a Galeria pública. Enquanto o vínculo estiver ativo e a Galeria pública estiver aberta, a cliente poderá alternar entre a origem autorizada e sua galeria privada. Toda seleção adicional feita na origem será resolvida pelo par `parent_gallery_id + client_id`: o backend reutilizará a mesma `DerivedGallery` e adicionará somente a nova foto e sua seleção, respeitando bloqueio, expiração e elegibilidade comercial. Se a privada tiver sido encerrada por ficar sem fotos, a próxima seleção válida criará uma nova privada operacional para o mesmo par, sem reabrir ou alterar pedidos históricos.

A biblioteca retornará três coleções explicitamente tipadas: `public_galleries` abertas e autorizadas, `private_galleries` operacionais e `history` comercial. Uma cliente pode possuir simultaneamente várias origens e várias privadas, mas cada privada pertence a exatamente uma origem; contadores, preço, prazo e pedidos nunca atravessam esse limite.

Quando a cliente remove sua última seleção, o backend primeiro aplica a política comercial da decisão 10 e remove somente referências de origem `client` que não tenham outra justificativa. Se ainda houver referências disponíveis de origem `admin`, a `DerivedGallery` permanece ativa com zero seleções. Se não houver referência disponível nem impedimento financeiro, a privada derivada pela cliente é encerrada com seus estados não comerciais. O `Client` e o registro individual com a Galeria pública permanecem, permitindo futura seleção. Pedidos, pagamentos, itens e entregas materializados ficam no histórico independente. Remover seleção ou referência privada nunca remove o `PhotoAsset` da Galeria pública.

Para eventos coletivos, a Galeria pública exibe apenas capa, informações e entrada protegida; o acervo integral continua administrativo. A futura busca facial, depois do spike e de uma change própria de privacidade, reutilizará o serviço de derivação somente após consentimento, resultado privado e aprovação exigida. Esta change prepara o contrato, mas não ativa processamento facial.

Alternativas consideradas:

- criar galeria privada no cadastro ou na abertura do link: produz registros vazios e confunde vínculo com autorização de fotos;
- procurar identidade por nome + telefone: torna correções ortográficas um problema de autenticação e ainda não acrescenta prova além do OTP; o telefone verificado será a identidade antduplicação e o nome permanecerá dado mutável;
- conceder acesso pela posse do link privado sem validar a sessão: permite compartilhamento indevido e rompe a propriedade individual;
- mostrar a grade coletiva para permitir seleção manual: viola o roadmap obrigatório de privacidade.
- mover a foto selecionada para fora da Galeria pública: faria a origem variar por cliente e impediria novas escolhas coerentes; a implementação manterá o arquivo na origem e criará somente referências privadas.

Quando a Galeria pública é excluída, ela deixa de ser listável, compartilhável ou selecionável, mas suas galerias privadas não são apagadas. Cada `PhotoAsset` com ao menos uma `DerivedGalleryPhoto` permanece uma única vez e continua servindo as privadas autorizadas; não há cópia por cliente. Fotos sem qualquer referência privada seguem a limpeza física. O registro interno removido da origem e sua configuração efetiva permanecem somente enquanto necessários à integridade, autorização e herança das privadas. Ao encerrar a última referência privada, a limpeza poderá remover o ativo e, quando não houver mais dependência, o tombstone da origem.

### 5. Ordem e definição do estado do cliente serão centralizadas no backend

O resumo da Galeria pública retornará, por vínculo, `client_id`, `derived_gallery_id`, nome, telefone permitido, `selected_count`, `purchased_count` e `gallery_status`. `purchased_count` contará itens distintos de pedidos confirmados; `selected_count` contará a seleção operacional atual. A precedência será:

1. `pending_registration`, quando o cadastro/vínculo ainda não foi validado;
2. `no_selection`, quando o cliente está vinculado e não possui seleção, exista ou não galeria privada administrativa com fotos disponíveis;
3. `blocked`, quando `access_enabled` é falso;
4. `expired`, quando o prazo UTC já terminou;
5. `active`, nos demais casos.

O frontend apenas traduz esses valores para cartões, textos e cores. Verde, amarelo e preto serão acompanhados por rótulo textual e contraste, sem depender exclusivamente da cor. O nome será um link para a galeria privada quando existir. A ação de desvincular abrirá confirmação com consequências e acompanhará a operação.

### 6. “Cliente” e “Galeria pública” serão o vocabulário de produto

Strings visíveis, labels, estados vazios, confirmações, mensagens de erro, acessibilidade e documentação funcional usarão “Cliente” e “Galeria pública”. Novos DTOs usarão `client`; campos internos legados `responsible`, classes `ParentGallery` e rotas existentes poderão receber alias de compatibilidade durante a migração e serão removidos somente após consumidores e testes migrarem juntos.

### 7. Tentativas OTP negadas terão PII transitória apagada

O número em claro é necessário enquanto o desafio pode ser entregue e validado. Quando um OTP válido termina em negação por ausência de cliente e de convite, nome, `subject` em claro e destinatário da entrega serão apagados na mesma finalização lógica; permanecerão fingerprint criptográfico com salt do servidor, estado, horários, IP tratado conforme política e códigos do provedor sem conteúdo da mensagem.

Desafios abandonados ou expirados serão tratados por limpeza periódica com janela curta configurada e documentada. O rate limit passará a consultar o fingerprint quando o telefone já tiver sido anonimizado. Quando houver convite válido, nome e telefone migram para `Client`/telefone autorizado e os duplicados transitórios também são limpos após consumo.

Alternativa considerada: nunca persistir o telefone do desafio. Foi rejeitada porque o worker assíncrono precisa do destinatário até a entrega e a verificação precisa correlacionar o desafio de forma segura.

### 8. O backend declarará três modos de acesso à Galeria pública

`ParentGallery` terá um modo explícito e validado pelo backend:

- `standard`: depois do OTP, um link público válido pode criar idempotentemente o vínculo ativo e liberar a navegação pelas fotos publicadas;
- `invite_only`: o OTP deve resolver a cliente previamente associada ou o convite individual destinado a ela; uma sessão não convidada não se vincula automaticamente;
- `collective_protected`: o login pode criar um registro pendente, mas nunca libera grade fotográfica; somente um resultado privado autorizado por fluxo facial futuro poderá disponibilizar fotos.

Nenhum modo entrega prévias antes da autenticação. Capa, título e informações não fotográficas podem compor a landing page pública, mas imagem de capa que revele pessoas também seguirá a política de preview protegido. O frontend apenas representa o modo e as permissões recebidas; não infere acesso por nomenclatura, rota ou presença de dados.

### 9. Links e convites serão capacidades opacas, revogáveis e vinculadas ao escopo

O link compartilhável da Galeria pública e o convite individual usarão tokens aleatórios de alta entropia, armazenados somente por hash, com escopo, estado, expiração opcional, rotação, revogação e auditoria. Identificadores públicos ou UUIDs isolados não concedem autoridade.

O token público localiza a origem e, apenas no modo `standard`, permite vínculo depois do OTP. O convite individual identifica a relação pretendida entre `Client` e Galeria pública ou privada, mas o telefone verificado precisa resolver a mesma identidade destinatária. Uso, falha, rotação e revogação serão auditados sem persistir o token em claro. Redirecionamentos pós-login aceitarão somente destinos internos previamente validados.

### 10. Configuração privada será herdada e a remoção respeitará o estado comercial

A Galeria pública será o modelo para preços e faixas, dados PIX, mensagens, favoritos, comentários, proteção/apresentação visual e prazo padrão de seleção. Nesta change, a galeria privada não terá overrides arbitrários. O prazo efetivo (`selection_expires_at`) será materializado ao criar a privada para manter um limite estável; apresentação e interações consultarão a configuração vigente da origem; preço e pagamento usarão a configuração da origem até o checkout e serão congelados em snapshot imutável no pedido.

A migration consolida as configurações legadas por Galeria pública somente quando as privadas existentes possuem valores equivalentes. Se encontrar mensagens, interações, faixas ou PIX divergentes dentro da mesma origem, ela SHALL falhar antes de alterar o schema, para que a divergência seja inventariada e resolvida explicitamente em vez de escolher silenciosamente termos comerciais. Os campos privados legados permanecem apenas como suporte de rollback e deixam de ser lidos ou gravados pelas APIs efetivas.

A remoção de seleção, referência privada, vínculo ou galeria observará a seguinte precedência:

1. carrinho sem pedido persistido pode ser descartado com os estados não comerciais;
2. pedido pendente sem comunicação de pagamento pode ser cancelado com evento de auditoria antes da remoção;
3. pedido com pagamento comunicado ou `pending_review` bloqueia a remoção operacional afetada até decisão administrativa;
4. pedido confirmado permite remoção operacional somente depois que snapshots, prévia histórica mínima e entrega ou referência final estiverem materializados e verificados.

Essas regras preservam o histórico sem deixar a interface fingir que uma operação financeira em análise foi desfeita. A mesma política será usada por remoção da última seleção, desvinculação e exclusão em cascata.

### 11. Esta change supersede semânticas conflitantes antes da implementação

Antes de alterar código, os artefatos ativos `align-admin-gallery-wizard-and-folder-ownership`, `complete-gallery-operational-flow`, `unify-gallery-presentation` e `add-derived-client-galleries` serão confrontados com esta change. Para o escopo sobreposto, prevalecem aqui: exclusão integral acompanhável em vez de exclusão apenas de galeria vazia; derivação privada por primeira seleção ou criação administrativa em vez de criação no simples link/cadastro; navegação simultânea pela Galeria pública autorizada e privada em vez de experiência exclusivamente privada; e liberação governada pelo modo de acesso do backend.

As capabilities transversais de seleção, experiência original, previews protegidos, apresentação/marca-d'água e liberação completa SHALL receber deltas formais antes da implementação. Enquanto esses deltas não existirem e as propostas conflitantes não estiverem reconciliadas, a primeira task de código permanece bloqueada. A distinção entre `Client` e pessoa fotografada/dependente fica explicitamente adiada para uma change posterior e não destrava busca facial sem o spike obrigatório.

## Risks / Trade-offs

- [Falha entre armazenamento e banco] → usar manifesto durável, chaves determinísticas, checksum e etapas idempotentes antes de remover referências.
- [Compra histórica sem arquivo disponível em dados antigos] → backfill identifica lacunas; exclusão fica bloqueada com erro acionável somente para o alvo afetado, sem marcar sucesso.
- [Aumento de armazenamento por itens comprados] → reter apenas derivado/entregável autorizado por item confirmado e medir bytes preservados no manifesto.
- [Contagem lenta em galerias grandes] → agregar em consultas por lote e criar índices para galeria, cliente, status de pagamento e item, evitando consulta por cliente.
- [Endpoint interno deixa de retornar `204`] → atualizar frontend e testes no mesmo deploy; documentar `202`, idempotência e consulta de progresso.
- [Operação destrutiva iniciada por engano] → exigir autenticação administrativa, confirmação com nome e inventário, bloquear duplo envio e auditar ator/horário; não oferecer restauração fictícia.
- [PII removida prejudica diagnóstico] → preservar fingerprint e metadados técnicos suficientes sem nome ou telefone reversível.
- [Uso de preto para bloqueio fica ilegível em tema escuro] → componente usa tokens de contraste, borda e texto explícito, validado em viewport desktop e móvel.
- [Link vazado concede descoberta indevida] → armazenar somente hash, exigir OTP e escopo compatível, permitir revogação/rotação e responder de forma neutra.
- [Mudança na Galeria pública altera experiência privada inesperadamente] → materializar prazo na criação, congelar termos comerciais no pedido e testar explicitamente quais campos permanecem dinâmicos.
- [Remoção durante pagamento em análise perde contexto] → bloquear a mutação afetada em `pending_review` e exibir motivo e ação administrativa necessária.

## Migration Plan

1. Reconciliar as changes ativas conflitantes e criar os deltas transversais ausentes; nenhuma alteração de código começa antes dessa revisão OpenSpec.
2. Adicionar modos de acesso, convites com hash, procedência das fotos disponíveis, estados de ciclo de vida, tabela de operações, snapshots históricos, mídia histórica e índices sem remover constraints atuais.
3. Executar backfill idempotente de modo de acesso seguro, procedência conservadora das referências e snapshots de pedidos/itens; produzir relatório de lacunas sem apagar dados.
4. Tornar as FKs operacionais de histórico anuláveis e aplicar `ON DELETE SET NULL` somente após o backfill validado.
5. Implantar autorização por modo/convite, herança de configuração, regras comerciais de remoção, worker, APIs de inventário/operação/progresso e limpeza de OTP; manter a exclusão destrutiva desabilitada por flag até a validação do backfill.
6. Implantar frontend administrativo e biblioteca histórica usando o novo contrato.
7. Validar em banco descartável e homologação: upgrade, downgrade estrutural antes de qualquer exclusão real, idempotência, falhas injetadas, autorização e limpeza física em fixture sem dados reais de crianças.
8. Habilitar a ação em homologação somente após autorização humana explícita e executar um caso sintético completo antes de produção.

Rollback antes de uma operação destrutiva apenas desabilita a flag e reverte aplicação/constraints compatíveis. Depois de uma galeria ser fisicamente excluída, rollback de software não restaura sua mídia operacional; o histórico comercial preservado continua legível pelo contrato anterior apenas se os adaptadores de compatibilidade forem mantidos. Não haverá execução destrutiva automática durante a migration.
