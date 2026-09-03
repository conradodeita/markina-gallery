## Context

Consulte `proposal.md` para a motivação e os deltas desta change para o comportamento normativo. Hoje `DerivedGallery.client_id` e o índice `(parent_gallery_id, client_id)` tornam a privada propriedade exclusiva; `GalleryAccessCapability.private_invite` exige uma cliente previamente definida e persiste apenas o hash de um token aleatório, portanto a interface não consegue reconstruir o link depois da resposta que o criou. As interações e pedidos já carregam `client_id`, o que permite separar o estado comercial sem duplicar o acervo.

O preço atual vive em `PriceRule` por Galeria pública e `pricing.quote` aplica o valor unitário da faixa alcançada a todas as unidades. Pedidos já guardam snapshots comerciais e não podem ser recalculados. A implantação exige migration aditiva, compatibilidade progressiva entre backend e frontend e nenhuma perda de vínculos, mídia ou histórico. Busca facial continua subordinada ao spike, ao roadmap e à revisão de privacidade.

## Goals / Non-Goals

**Goals:**

- Introduzir associação multiusuário à privada sem reescrever as tabelas individuais de seleção, favorito, visualização, comentário e pedido.
- Tornar links públicos e privados permanentes durante o ciclo normal da galeria, reconstruíveis e auditáveis sem armazenar o segredo em texto puro, reservando revogação/rotação para incidente operacional.
- Garantir unicidade concorrente de uma privada por `Galeria pública + cliente`, inclusive por caminhos de link, seleção e ação administrativa.
- Introduzir modelos globais e snapshots comerciais progressivos por parcelas, mantendo histórico e sem reinterpretar faixas legadas.
- Executar uma transição aditiva que permita validar dados antes de retirar dependências do proprietário legado.

**Non-Goals:**

- Habilitar reconhecimento facial, criar endpoint biométrico, processar imagem de consulta ou usar dados reais de crianças.
- Alterar o mecanismo de entrega de originais, automatizar conciliação PIX ou integrar Infinity Pay.
- Compartilhar atividades comerciais entre membros ou transferir automaticamente histórico entre privadas.
- Apagar registros comerciais na remoção operacional de galerias ou membros.

## Decisions

### 1. Associação explícita e proprietário legado temporário

Será criada `DerivedGalleryMembership` com UUID público, `derived_gallery_id`, `parent_gallery_id`, `client_id`, estado `active|blocked|unlinked`, datas de criação/atualização/bloqueio/desvinculação e ator administrativo quando aplicável. Uma restrição única em `(parent_gallery_id, client_id)` será a autoridade de concorrência; `parent_gallery_id` será materializado para que a regra não dependa de join e possa ser garantida pelo banco. Uma chave/validação composta garantirá que a origem da associação coincida com a origem da privada.

`DerivedGallery.client_id` permanecerá preenchido e somente leitura durante a janela de compatibilidade como `legacy_owner_client_id`. A migration criará um membro ativo para cada proprietária atual. Autorização, agregações e novas escritas passarão para a associação; a coluna antiga só será removida em change posterior, após observabilidade e validação humana.

Alternativa rejeitada: reutilizar `GalleryAccess` ou guardar uma lista JSON na privada. Nenhuma das duas representa bloqueio/desvinculação, integridade relacional, auditoria e unicidade concorrente de maneira adequada.

### 2. Resolução transacional de privada por origem e cliente

Um serviço único resolverá a associação dentro de transação:

1. normaliza a identidade já verificada;
2. procura a associação `(parent_gallery_id, client_id)`, incluindo bloqueada ou desvinculada;
3. se veio por link privado e não existe associação, ingressa naquela privada;
4. se veio pela pública e existe associação ativa, reutiliza-a;
5. se não existe, seleção manual ou ação administrativa cria a privada e o primeiro membro;
6. conflito de unicidade recarrega o vínculo vencedor em vez de duplicar.

Associação bloqueada não será substituída por outro link. Associação desvinculada exige ação administrativa explícita para reativar ou mover; o sistema não transfere estado automaticamente. Entrar por outro link da mesma origem encaminha para a privada já vinculada, sem revelar o destino pedido pelo token conflitante.

Alternativa rejeitada: escolher a privada mais recente no frontend. Isso permite corrida, ignora bloqueio e expõe decisão de autorização ao cliente.

### 3. Acervo comum e atividades individuais

`DerivedGalleryPhoto` continuará sendo a relação do acervo comum com a mídia original da Galeria pública. `PhotoSelection`, `PhotoFavorite`, `PhotoView`, `PhotoComment` e `SaleOrder` já possuem `client_id` e serão consultados sempre pelo membro autenticado. A autorização exigirá associação ativa antes da leitura operacional; histórico confirmado usará os snapshots e manifestos comerciais já existentes.

A origem da referência (`admin`, `client`, `facial`) continuará registrando justificativas distintas. A remoção de uma origem só apagará a relação correspondente quando nenhuma outra justificativa sustentar a foto. A porta `facial` permanece não exposta e lançando indisponibilidade até o spike aprovado.

### 4. Links estáveis como capacidades HMAC versionadas

O link reutilizável usará um identificador público aleatório da capacidade e uma assinatura HMAC versionada sobre escopo, alvo e versão de rotação. O banco armazenará metadados, versão e hash/fingerprint para auditoria, nunca a assinatura em texto puro. Assim, o backend consegue reconstruir o mesmo endereço enquanto a versão estiver ativa; rotação incrementa a versão e invalida assinaturas antigas. Uma chave dedicada de servidor será fornecida por secret de ambiente, separada do segredo de OTP.

O `public_gallery` continuará reutilizável. `private_invite` será dividido semanticamente em `private_gallery_link` reutilizável sem `client_id` e `private_client_invite` individual compatível quando necessário. A interface operacional mostrará somente o endereço permanente e a ação de copiar; não oferecerá regeneração ou revogação rotineira. Tokens legados continuarão válidos até consumo, expiração ou incidente. Quando o segredo legado não puder ser reconstruído, a reparação excepcional deverá ser executada de forma administrativa e auditada, com aviso explícito de que o endereço anterior deixará de funcionar.

Alternativa rejeitada: guardar o token completo criptografado ou em texto puro. A assinatura determinística versionada reduz material secreto persistido e permite reconstrução; criptografia acrescentaria rotação de ciphertext e risco operacional sem benefício para este caso.

Todo novo vínculo de origem sem sessão comprovada exigirá OTP contextual. Uma sessão válida poderá retomar vínculo já existente sem novo OTP; entrar em outra origem seguirá exigindo prova contextual conforme a política de segurança vigente. O desafio carregará a capacidade e a origem; a confirmação resolverá primeiro `ClientPhone` e depois o telefone canônico E.164, reutilizará o mesmo `Client.id` criado pelo fotógrafo e nunca criará uma segunda identidade para o mesmo número. O nome informado no login não substituirá silenciosamente o cadastro administrativo.

### 5. Notificação transacional por outbox

Criação de privada e mudança de membro gravarão evento idempotente na outbox na mesma transação da alteração. O painel será o canal obrigatório e poderá consultar notificações agregadas. WhatsApp ou outro canal configurado será consumidor opcional do mesmo evento, com chave lógica estável, retentativa e erro sanitizado. Reabrir link ou repetir callback não produzirá novo evento.

Alternativa rejeitada: enviar WhatsApp dentro da request. Isso poderia confirmar vínculo sem notificação ou reverter cadastro por indisponibilidade externa.

### 6. Modelos de preço versionados e snapshot da galeria

Serão criadas `ProgressivePricingPreset` e `ProgressivePricingTier`, com código único, nome, versão, estado e faixas. A Galeria pública terá modo `fixed|progressive|legacy_volume`, preço fixo opcional e snapshot JSON normalizado da tabela escolhida. O vínculo ao preset serve para rastreabilidade, mas a cotação lê somente o snapshot da galeria.

O algoritmo progressivo percorrerá as faixas e cobrará apenas a interseção da quantidade com cada intervalo. Retornará parcelas, total, preço-base e economia. O mesmo serviço será usado por simulador, rodapé, checkout e criação do pedido; o frontend apenas formata a resposta. `SaleOrder.price_rule_snapshot` armazenará modo, código/nome, versão, faixas, parcelas, economia e total cotado.

Faixa unitária legada será convertida para `fixed`. Duas ou mais faixas serão marcadas `legacy_volume`, preservadas em leitura e impedidas de gerar novo checkout até o fotógrafo escolher explicitamente fixo ou progressivo. Nenhum pedido existente será recalculado.

Alternativa rejeitada: converter automaticamente faixas antigas em parcelas. Isso mudaria totais comerciais sem consentimento e poderia divergir de valores já apresentados.

### 7. PIX com uma fonte operacional de verdade

`PixCheckoutSettings.copy_paste` continuará sendo a fonte autoritativa consumida pelo checkout e pelo QR. O editor aceitará diretamente um BR Code válido ou uma chave simples dos tipos explicitamente suportados: CPF, telefone brasileiro ou e-mail. Uma chave simples será normalizada e, junto do nome e da cidade públicos do recebedor, convertida localmente em BR Code estático conforme o formato EMV; esses dados estruturados serão persistidos para permitir edição e regeneração determinística. O sistema SHALL NOT gerar QR contendo apenas texto cru nem inventar nome/cidade do recebedor.

`qr_code_payload` legado será aceito na janela de compatibilidade: se somente ele existir, será copiado para `copy_paste`; se ambos existirem e divergirem, a galeria será marcada para revisão, sem sobrescrever qualquer valor. O pedido preservará o BR Code, instruções e representação necessária no snapshot, mas não exporá campos administrativos adicionais. Chave aleatória permanece fora deste incremento porque não foi solicitada na revisão humana.

### 8. Editor transacional por etapa e fontes locais

Cada etapa terá uma função explícita de validação e persistência. `Salvar e avançar` aguardará a mutation e somente navegará após sucesso. Stepper, retorno e troca direta verificarão estado sujo; salvarão pelo mesmo caminho ou pedirão confirmação de descarte. Não haverá salvamentos concorrentes implícitos.

O upload continuará enfileirando a geração de miniatura e prévias protegidas; a mídia original nunca será servida. Assim que o worker concluir o derivado `client_preview`, ele marcará a foto como disponível e liberará sua pasta de conteúdo de forma idempotente. `Processamento` será apenas um estado técnico transitório exibido como preparação da prévia. A etapa Imagens não exigirá botão de publicação: `Salvar e avançar` apenas persistirá a organização e avisará sobre itens ainda em preparo ou com falha, sem impedir que as fotos já prontas apareçam para administrador e clientes autorizadas.

A lista de tipografias será um registro estático tipado de fontes locais licenciadas, com categoria e fallback. A API aceitará apenas IDs desse registro. Arquivos de fonte serão carregados via mecanismo local do Next.js, sem dependência de CDN.

### 8.1. Seleção pública persistente e cotação autoritativa

A listagem pública autorizada retornará, para a identidade autenticada, o estado de seleção de cada foto, a privada derivada resolvida para aquela origem e a cotação atual calculada pelo mesmo serviço do carrinho privado. Selecionar ou desmarcar gravará/removerá `PhotoSelection` no backend; a interface recarregará o estado autoritativo após cada mutation e em toda nova visita. O botão alternará explicitamente entre `Selecionar` e `Desmarcar`, e o resumo flutuante mostrará quantidade, total, economia e `Prosseguir` para a privada correspondente.

A administração continuará lendo as mesmas `PhotoSelection` persistidas em suas agregações, portanto não dependerá de checkout para conhecer a seleção em andamento. A resposta de cliente não serializará seleções de outros membros. Se a última seleção encerrar uma privada criada somente por aquela jornada, a resposta orientará a cliente de volta à Galeria pública sem apagar histórico comercial.

### 9. Lifecycle e histórico

Bloqueio é atributo da associação e afeta apenas acesso/interações futuras daquele membro. Desvinculação encerra o acesso operacional, mas mantém a associação tombstone para unicidade, auditoria e histórico. Exclusão da privada revoga sua capacidade reutilizável e remove referências operacionais elegíveis; pedidos, itens, snapshots, manifestos de mídia e entregas permanecem consultáveis pela identidade correta.

As prévias operacionais exigirão membro ativo. As prévias históricas continuarão protegidas pelo pedido/entrega e não pela existência da privada. Inventários de exclusão serão ampliados para contar membros e capacidades, sem transformar vínculo em impedimento comercial.

### 10. Contratos e consultas sem N+1

Respostas administrativas da privada incluirão acervo agregado, lista paginada de membros e, para cada membro, contagens e estado comercial calculados em subconsultas agrupadas. Respostas de cliente não incluirão a lista de membros. DTOs antigos com `client_id` serão mantidos temporariamente como `legacy_owner_client_id`, enquanto novos contratos usarão `membership` e `members` somente nas rotas administrativas.

Índices cobrirão `(derived_gallery_id, status)`, `(client_id, status)`, `(parent_gallery_id, client_id)` e consultas comerciais já filtradas por `(derived_gallery_id, client_id)`. Testes de contrato verificarão que serialização de cliente não contém PII ou atividade de terceiros.

### 11. Reconciliação com changes ativas

Esta change supersede somente os requisitos conflitantes de propriedade exclusiva, clonagem por segundo responsável, convite privado preso a um telefone e preço por volume aplicado ao total. Implementações úteis das changes `improve-gallery-and-client-data-lifecycle` e `remediate-gallery-workflow-and-payment-experience` serão reaproveitadas; seus checkboxes de revisão humana permanecem pendentes até a experiência substituta ser validada. O spike `spike-private-facial-discovery` continua independente e bloqueia qualquer habilitação facial.

### 12. Cadastro de cliente independente e exclusão restrita

A busca administrativa de clientes representa o diretório global, não uma lista de candidatas ainda não vinculadas. Portanto, a API continuará retornando todas as identidades correspondentes e o frontend mostrará o estado `Já vinculada`, desabilitando apenas a mutação redundante. Nome e telefone serão editados sobre o mesmo `Client.id`; a troca de telefone reutilizará a prova OTP já existente, a unicidade E.164 e a aposentadoria de `ClientPhone`, preservando snapshots comerciais.

Excluir e recriar não será o fluxo para troca de telefone porque quebraria continuidade de identidade e poderia separar histórico. A exclusão direta será limitada a cadastros sem dependências protegidas, após inventário autoritativo. Qualquer vínculo, sessão/desafio, interação, mensagem, notificação, pedido, pagamento, entrega ou registro histórico bloqueará a operação. A limpeza integral de dados sintéticos de homologação será uma operação de manutenção separada, guardada por `APP_ENV=homolog`, com modo de inventário, confirmação explícita e escopo restrito aos recursos da Markina Gallery.

### 13. Projeção operacional após desvinculação e diálogos compactos

A associação `DerivedGalleryMembership` preservada como `unlinked` é um tombstone histórico e de unicidade, não um vínculo operacional. A listagem atual da Galeria pública incluirá cadastros públicos ainda existentes, associações `active|blocked` e, durante a compatibilidade, proprietárias legadas somente quando não houver associação explícita para o mesmo par origem/cliente. Assim, uma associação explícita `unlinked` impede que `DerivedGallery.client_id` ressuscite o vínculo encerrado; `blocked` continua visível e reversível. Pedidos e seleções históricas podem permanecer em consultas comerciais sem tornar a cliente vinculada novamente.

Os diálogos compartilhados limitarão sua altura à viewport e oferecerão rolagem vertical própria ou no backdrop. Essa regra preserva confirmação e consequências completas, mantendo as ações alcançáveis em janelas desktop baixas e dispositivos móveis sem alterar a semântica das operações.

## Risks / Trade-offs

- [Privadas legadas inconsistentes para o mesmo par origem/cliente] → a migration executa diagnóstico prévio, aborta diante de conflito e gera relatório sem mesclar histórico automaticamente.
- [Rollback do backend após ingresso de múltiplos membros] → manter coluna proprietária e leitura compatível; em rollback, desabilitar novas escritas multiusuário e preservar associações, sem down migration destrutiva.
- [Vazamento entre membros por filtro ausente] → centralizar autorização, exigir `client_id` em toda consulta individual e cobrir respostas/rotas com testes negativos de dois membros.
- [Link reutilizável encaminhado fora do público pretendido] → capacidade opaca de alta entropia, HMAC, rotação/revogação, rate limit, OTP contextual e auditoria; não prometer proteção contra compartilhamento voluntário.
- [Segredo HMAC ausente em deploy] → validar configuração no startup e adicionar ao inventário de secrets; nunca reutilizar segredo de OTP nem persistir a chave no Git.
- [Mudança de preço causa divergência no checkout] → backend como única autoridade, chave idempotente, snapshot no pedido e bloqueio explícito de `legacy_volume`.
- [Migrations longas ou lock em homologação] → criar estruturas e índices de forma aditiva, medir cardinalidade antes, backfill em passos idempotentes e validar constraints somente após reconciliação.
- [Notificação externa indisponível] → outbox e painel confirmam o evento; falha de WhatsApp não reverte associação e pode ser retomada.
- [Fonte adicional degrada performance] → subconjunto local, preload apenas das famílias usadas e medição de build/Lighthouse em mobile.
- [Escopo facial avançar por acidente] → manter porta não exposta, teste de indisponibilidade e dependência explícita do spike e de change futura.

## Migration Plan

1. Executar inventário somente leitura: migrations no head, contagem de privadas, duplicidades potenciais por origem/cliente, capacidades ativas, configurações PIX divergentes e galerias com múltiplas faixas legadas.
2. Publicar migration aditiva para associações, presets/snapshots comerciais, versão de capacidade e campos de compatibilidade, sem remover coluna ou tabela existente.
3. Backfill idempotente: transformar cada `DerivedGallery.client_id` em membro ativo, preencher origem materializada, converter faixa única para preço fixo, marcar múltiplas faixas como `legacy_volume` e copiar PIX somente quando não houver conflito.
4. Validar contagens, chaves compostas e ausência de conflito; somente então ativar as constraints únicas. Qualquer conflito aborta antes da alteração de comportamento.
5. Publicar backend de leitura dupla e escrita nova, mantendo contratos antigos necessários e links legados válidos. A chave HMAC dedicada precisa existir antes de ativar links reconstruíveis.
6. Publicar frontend administrativo e de cliente usando os novos contratos, mantendo mensagem explícita para galerias `legacy_volume` e capacidades antigas não reconstruíveis.
7. Executar testes de integração com duas ou mais clientes, concorrência de links, isolamento, cálculo progressivo, lifecycle, histórico e navegação; usar somente dados sintéticos em homologação.
8. Após validação humana, retirar fallback de escrita por proprietária em change posterior. Não remover associações nem rebaixar schema em rollback; retornar temporariamente ao backend compatível e bloquear novas mutações multiusuário.
