# Design

## Context

Consulte também `supersession.md` para identificar as cláusulas de changes ainda ativas que esta decisão substitui, preservando seus requisitos independentes.

Consulte `proposal.md` e os delta specs. Hoje `ParentGallery` reúne configuração e pastas comuns, `DerivedGallery` reúne pastas próprias e prazo, `DerivedGalleryMembership` controla o acesso privado, e seleção/carrinho/pedidos referenciam o ID derivado mesmo tendo `client_id`. A primeira seleção na pública pode criar uma derivada. O frontend possui a rota administrativa “Galeria privada · acervo da cliente” e a rota de cliente `/gallery/{id}`. A prévia pública verifica galeria e liberação da pasta, mas não confirma explicitamente que a foto é comum; isso precisa ser corrigido antes de adicionar públicos de pasta.

O inventário somente leitura e as exclusões de escopo estão em `homolog-inventory.md`. A limpeza existente em `backend/app/homolog_cleanup.py` usa `TRUNCATE parent_gallery, client CASCADE` e remove três raízes de mídia, mas não inventaria toda configuração global nem todo registro histórico sem chave estrangeira. O ambiente corrente usa `APP_ENV=staging`; o procedimento de limpeza injeta `APP_ENV=homolog` em contêiner efêmero. O controle de ambiente deve conferir também projeto, checkout, banco, volume e domínio, sem confiar apenas nessa variável.

## Goals / Non-Goals

**Goals:**

- Uma identidade de galeria para navegação e operação, com público por pasta e estado comercial por cliente.
- “Coleção” permanece a área de pastas da cliente, reunindo as pastas comuns e as restritas atribuídas sem criar outra jornada visual.
- Uma pasta restrita única para uma ou várias clientes, criada no card de uma cliente e atribuída inicialmente a ela; pastas comuns continuam na etapa Imagens.
- Nenhum acesso por URL direta a foto fora da pasta autorizada; nenhuma derivada nova.
- Limpeza pontual, auditável e sem novo backup dos dados de teste em homologação, preservando todos os itens especificados.
- Compatibilidade não destrutiva para dados fora de homologação e rollback de código possível.

**Non-Goals:**

- Apagar dados de produção ou migrar automaticamente histórico de produção sem inventário próprio.
- Tornar a Galeria pública anônima, remover OTP ou ampliar a busca facial para acervo não autorizado.
- Alterar processamento de JPEG, marca-d'água, preço confirmado ou instância Evolution.
- Apagar backups preexistentes, segredos, logs de segurança administrativa ou recursos de terceiros.

## Decisions

### 1. Galeria canônica com estado individual, não uma derivada invisível

`ParentGallery.id` passa a ser o identificador operacional usado por frontend e novas APIs. Uma relação individual `galeria + cliente` armazena estado de vínculo, prazo e permissões que hoje dependem da derivada; a autenticação por telefone/OTP e os modos de acesso existentes continuam sendo pré-condições. O banco impõe unicidade desse par. A biblioteca mostra uma entrada por galeria, e o primeiro clique em Selecionar grava a seleção nessa relação, sem criar `DerivedGallery`.

Alternativa rejeitada: apenas renomear a tela privada e manter toda a derivação como mecanismo permanente. Isso simplificaria a navegação, mas conservaria os dois caminhos de autorização, os IDs duplicados e a complexidade que o proprietário quer eliminar.

### 2. Público da pasta separado do estado de liberação

Uma pasta de conteúdo tem escopo `all` ou `selected`; uma relação `folder + client` guarda cada atribuição restrita com unicidade e integridade de mesma galeria. O escopo é definido antes da liberação. Pasta nova permanece `preparing`, invisível às clientes. Criar pelo card estabelece escopo `selected` e atribui a cliente daquele card; adicionar outra cliente altera a mesma relação e não copia fotos. Pasta comum é criada na etapa Imagens com escopo `all` explícito.

Vínculo ativo e OTP continuam necessários mesmo para pastas comuns. Atribuir cliente ainda pendente pode ser preparado administrativamente, mas não concede leitura antes da ativação do vínculo. Alterar público após liberação recalcula acesso imediatamente; pedidos confirmados preservam seus manifestos históricos. A UI explicita o efeito em todas as clientes atribuídas antes de mudar uma pasta compartilhada.

Alternativa rejeitada: criar uma pasta por cliente ou guardar IDs em JSON. A primeira duplica fotos e a segunda perde integridade, índices e revogação auditável.

### 3. Predicado único de autorização para foto

O backend centraliza a verificação de sessão, vínculo ativo, modo de acesso da galeria, foto disponível, pasta liberada e público da pasta. Listagem e URL de prévia usam o mesmo predicado. A correção imediata da rota pública exige foto do acervo comum antes de aceitar seu ID; na arquitetura final a rota aplica o público da pasta. Seleção, favoritos, comentários, carrinho, exportação e busca facial consultam somente IDs dessa visão autorizada. Um resultado facial continua apenas reordenando fotos já visíveis. Respostas de cliente nunca trazem lista de outras clientes, IDs de atribuição alheia ou metadados de pasta negada.

Alternativa rejeitada: filtrar somente na lista ou no React. A URL de prévia e endpoints de interação continuariam capazes de contornar a restrição.

### 4. Estado comercial novo por `galeria + cliente`, histórico legado preservado

Adicionar chaves canônicas a seleção, favorito, visualização, comentário, carrinho e pedido; novas escritas usam a galeria canônica e a cliente autenticada. Ajustar índices de unicidade, idempotência e rascunho para esse par, pois `derived_gallery_id` nulo não sustenta os índices atuais. `SaleOrder` continua congelando itens, valores, identificação e mídia histórica; preço efetivo permanece na galeria. Prazos/reabertura passam ao estado individual, não a um prazo global que afetaria outras clientes.

Migrations serão aditivas e compatíveis com linhas antigas: IDs derivados permanecem legíveis durante a transição e nenhuma tabela/coluna de histórico é removida no deploy. Para bases não vazias fora da limpeza homologada, um inventário e migração verificada deverão mapear derivadas, pastas próprias, membros e pedidos para o modelo novo antes de descontinuar a leitura legada. Conflitos, duplicidades ou histórico sem dono interrompem a migração; não se fundem pedidos automaticamente. Em homologação, a limpeza autorizada elimina os dados de teste, mas a aplicação não depende dessa limpeza para iniciar sem corromper uma base preexistente.

Alternativa rejeitada: reutilizar `derived_gallery_id` como se fosse o ID da galeria canônica ou renumerar pedidos existentes. Isso quebra links, snapshots e isolamento.

### 5. “Acervo da cliente” é porta de operação, não proprietário da pasta

O card de cada cliente na etapa Clientes recebe uma seção recolhível inicialmente fechada. Ali o fotógrafo cria a pasta restrita, envia JPEGs pelo pipeline atual, acompanha processamento, define/libera o público, atribui outras clientes e revisa seleção, compras, prazo e entrega daquela cliente. A pasta compartilhada aparece nos cards de todas as atribuídas como a mesma entidade. Abrir ou fechar a seção altera apenas estado de UI; carregar detalhes autorizados ao abrir pode ser uma consulta de leitura, sem escrita ou job.

Conteúdo comum, capa e ajustes globais ficam nas etapas gerais da galeria. A antiga tela privada sai da navegação e não cria novas derivadas; sua URL administrativa permanece disponível apenas para manter acervos legados preexistentes fora da homologação até uma migração própria, pois fechá-la agora impediria gerir fotos e pedidos ainda não convertidos. A homologação autorizada elimina esses registros de teste após o deploy. Links privados existentes exigem redirecionamento autenticado para a galeria canônica ou leitura histórica compatível; não devem revelar destino a outra cliente. Não emitir novos links privados. A prévia administrativa reutiliza o componente de apresentação, mas não simula sessão de cliente.

Na área de cliente, “Coleção” mantém a navegação de pastas já usada hoje. A resposta de pasta da galeria canônica combina somente pastas comuns liberadas com pastas restritas liberadas atribuídas à cliente autenticada; seleção, compras e histórico continuam individuais na mesma galeria. O frontend não separa uma “galeria privada” nem cria uma segunda Coleção para as pastas restritas.

A rota de “Minha galeria” deixa de ser uma tela operacional. Seus controles de seleção, favoritos, comentários e pedido de novo prazo migram para a Coleção; a revisão de fotos, cotação e PIX usam o Carrinho atual; acompanhamento de pedido, pagamento e entrega usa Compras. Um link legado só redireciona após autenticação e conferência de vínculo; contexto de compra aponta a Compras e contexto de fotos à Coleção. A migração elimina os componentes duplicados após preservar os testes e a leitura histórica necessária.

Alternativa rejeitada: duplicar toda a gestão de pasta e JPEGs em cada card. Isso permitiria edições divergentes de uma pasta compartilhada.

### 6. Notificações de nova pasta direcionadas pelo público efetivo

A liberação ou nova atribuição de pasta pronta produz evento idempotente por `galeria + pasta + cliente + versão de atribuição`, somente para clientes com acesso efetivo. A configuração global existente de WhatsApp/push continua fonte de verdade; falha de transporte não reverte liberação. Desatribuição cancela trabalhos futuros ainda não enviados. Não reenviar histórico ao ativar um canal. Links e destino apontam à galeria canônica e não carregam dados de outras clientes.

Alternativa rejeitada: reaproveitar o envio para todos os membros da derivada. A audiência agora é da pasta, e o envio coletivo poderia divulgar uma pasta restrita.

### 7. Limpeza de homologação por classificação explícita

Estender a rotina existente, sem SQL ad hoc no servidor, para inventariar todas as tabelas de dados de cliente/galeria, inclusive dependências sem FK: pedidos/itens/snapshots, seleções, carrinhos, comentários, visualizações, notificações e outboxes, inscrições push de cliente, recibos, busca facial, auditoria de atividade de cliente e entregas. Separar auditoria de segurança administrativa e configurações globais. O banco usa uma classificação fechada de tabelas operacionais, preservadas e mistas; `TRUNCATE ... RESTRICT` contém somente as operacionais, enquanto sessões, push e auditoria mistas recebem exclusão filtrada. Schema novo ou dependência de tabela preservada aborta antes do commit. Incluir todo worker Markina capaz de escrever mídia ou banco na pausa controlada, inclusive ajuste de prévia. Não tocar nos contêineres, banco, Redis ou volume da Evolution.

O procedimento exige checkout `/opt/markina-gallery`, projeto Compose `markina-gallery`, arquivo/env de homologação, porta `127.0.0.1:8080`, origem HTTPS `PUBLIC_APP_ORIGIN` sincronizada pelo deploy e banco/volumes exclusivos. `MARKINA_PUBLIC_URL` pode permanecer no default local e não identifica a origem pública de homologação. No JSON de `docker compose config`, cada mount usa o nome lógico (`media-source`), enquanto a seção `volumes` contém o nome físico com prefixo `markina-gallery_`; a guarda confere ambos. A leitura da topologia inclui o perfil `whatsapp-real` para validar os serviços Evolution sem iniciá-los, mesmo quando `COMPOSE_PROFILES` não está definido no processo de manutenção. A guarda informa apenas o nome do campo divergente, sem expor valores ou segredos. Registra inventário anterior e posterior sem PII, compara as contagens de todas as categorias preservadas sem expor segredos, limpa apenas quatro raízes de mídia da Markina (originais, derivados, histórico e referências faciais) e seu Redis exclusivo. O volume de marca permanece intacto. Usa o modo já existente **sem novo backup**, solicitado para esta execução, preservando backups antigos. Se qualquer guarda falhar, aborta antes da mutação. Depois confirma contagens operacionais zero, serviços e healthchecks. Se mídia falhar após commit do banco, registra falha parcial e permite retomada idempotente limitada às mesmas raízes; rollback de código não recupera dados apagados.

Alternativas rejeitadas: `docker compose down`, prune, `DROP DATABASE`, exclusão de volumes, `FLUSHALL` fora do Redis da Markina e limpeza manual sem inventário. Todas ampliam o impacto ou removem proteções.

### 8. Documentação e fases de publicação

Atualizar `INSTRUCOES_EXECUTOR_CLAUDE_CODE.md` e `ROADMAP_ARQUITETURA.md` para substituir as cláusulas que exigem derivada, sem relaxar OTP, privacidade, snapshots e limites faciais. Reconciliar changes ativas que ainda presumem `DerivedGallery`; marcar explicitamente requisitos substituídos e manter trabalho independente. Implementar e testar o backend compatível antes do frontend, validar com clientes sintéticos distintos e uma pasta atribuída a ambos. CI, OpenSpec, lint, tipos e build precedem PR. O deploy de código e migration aditiva deve ser saudável antes da operação de limpeza; a limpeza só ocorre após novo inventário e gate operacional do servidor. Não publicar em produção sem plano separado para dados legados.

## Risks / Trade-offs

- [URL direta revela foto restrita] → mesmo predicado de autorização na listagem, prévia e mutações; testes cruzados com duas clientes e IDs conhecidos.
- [Pasta compartilhada editada a partir de um card afeta outra cliente] → entidade única, público explícito e confirmação contextual da alteração.
- [Pedido ou prazo de uma cliente aparece a outra] → todas as consultas comerciais filtram `galeria + client_id`; contratos de cliente não serializam outras pessoas.
- [Derivadas antigas e links quebram] → leitura histórica e manutenção administrativa restrita aos registros legados existentes, migração inventariada e nenhuma remoção destrutiva de schema no deploy. O fluxo novo não cria derivadas nem emite links privados.
- [Limpeza atinge 2FA, configuração ou Evolution] → lista permitida, testes PostgreSQL descartáveis e comparação anterior/posterior de estado preservado; projeto/volumes externos fora do comando.
- [Resto técnico sobrevive à limpeza das raízes] → classificação fechada, inventário de tabelas sem FK, arquivos e filas; pós-condições explícitas para históricos de cliente.
- [Limpeza sem novo backup é irrecuperável] → consequência solicitada pelo proprietário, documentada antes da execução; backups preexistentes intactos, sem promessa de restauração.

## Migration Plan

1. Implementar e testar em ambiente descartável a autorização por pasta, estado individual, comércio, compatibilidade legada e a proteção imediata da prévia pública.
2. Integrar interface administrativa e da cliente, notificações e busca facial com o predicado central; executar testes de isolamento, regressão, CI e revisão OpenSpec.
3. Publicar código e migration aditiva somente em homologação pelo fluxo aprovado; confirmar SHA e healthchecks.
4. Repetir inventário de homologação, apresentar lista de exclusão/preservação, diferenças de contagens e plano de impacto zero; executar a limpeza pontual sem novo backup somente com o gate operacional aplicável.
5. Com dados sintéticos novos e autorizados, validar galeria única, pasta comum, pasta restrita a uma e a duas clientes, URL direta negada, compra/histórico individual, notificações e fluxo administrativo. Remover esses dados pelo mesmo procedimento controlado, novamente sem novo backup, e confirmar homologação vazia de galerias, clientes, fotos, seleções e pedidos.
6. Sincronizar specs e arquivar somente após revisão humana. Produção exige plano separado de migração de registros legados; rollback de código permanece possível, mas não restaura dados de teste apagados.
