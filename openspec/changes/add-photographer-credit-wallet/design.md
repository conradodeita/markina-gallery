# Design: Carteira de créditos do fotógrafo

## Estado

Design técnico aprovado pelo proprietário em 31/10/2026, com a decisão R03-101 e o aviso de duplicidade definidos em 01/11/2026. Schema/migration `20261031_0094`, serviço de ledger, rotas owner-only, reserva/captura, reconciliação, proteção da exclusão de ativos pendentes, tela `/admin/credits`, resumo no dashboard e confirmação de JPEGs repetidos estão implementados e validados localmente. A reserva ocorre antes da transferência do corpo JPEG. Os checkpoints locais foram concluídos; a change aguarda revisão humana antes de sincronizar a spec principal ou arquivar. Nenhuma migration foi aplicada em produção ou homologação; não houve concessão real, ativação comercial nem publicação.

Validação acumulada até 01/11/2026: a suíte `test_tenant_photographer_migration.py` passou 18 testes no PostgreSQL descartável e o teste adicional dos gatilhos append-only passou. Os testes focados anteriores incluíram 22 casos da carteira, 3 fluxos de upload em `test_derived_galleries.py`, 17 de `test_gallery_workflow_remediation.py`, 6 de lotes, 1 cenário high-res e 19 casos de acervo/produtor em SQLite temporário. O checkpoint PostgreSQL de tenant/TOTP/carteira passou 28 testes, com 1 ignorado esperado e 6 avisos em 335,75 s. O checkpoint SQLite amplo de carteira/acervo/galerias registrou 141 passados e 1 ignorado; a única falha foi a expectativa de resposta que não incluía `content_fingerprint: null`, corrigida e coberta novamente junto a três casos relacionados (4/4). O frontend passou 571 testes em 67 arquivos; lint teve 0 erros e 36 avisos; typecheck e build passaram. Ruff, `py_compile`, OpenSpec strict, `git diff --check` e revisão final do diff passaram. O primeiro tmpfs descartável de 512 MB atingiu `DiskFull`; não foi reiniciado nem limpo. A bateria final usou container dedicado de 1,5 GiB, removido após os testes.

O reconciliador do worker considera operações `reserved` após 15 minutos e tenta novamente operações `reconciliation_required` após 1 minuto. Usa `SELECT ... FOR UPDATE SKIP LOCKED`, verifica a chave de storage confinada ao tenant e só libera quando o arquivo está comprovadamente ausente. Um arquivo existente com fingerprint divergente ou filesystem ilegível mantém a reserva pendente. A exclusão de fotos é recusada enquanto houver operação pendente, evitando que a limpeza física apague a evidência necessária à reconciliação.

Em 31/10/2026 o proprietário confirmou que a interface do proprietário deve incluir pacotes e operações por fotógrafo. A tela lista/seleciona tenants, apresenta estado, saldo e histórico, e permite concessão/revogação auditáveis por origem; a própria carteira ilimitada do proprietário é somente leitura. Não há preço ou quantidade comercial pré-preenchidos. O login permanece sem alteração e a compra de créditos por Mercado Pago continua fora desta change.

## Decisões do proprietário registradas em 31/10/2026

- Somente o proprietário global poderá criar pacotes, conceder créditos e revogar concessões. `InstallationOperator` e a capacidade `capacity_diagnostics` permanecem exclusivamente técnicos.
- O proprietário informou que hoje não há fotógrafo tenant além da sua conta. O tenant explicitamente associado ao proprietário será ilimitado; fotógrafos futuros terão carteira finita, sem saldo ou pacote inicial automático presumido.
- Cobrança: um crédito por novo JPEG de pasta `content` armazenado com sucesso. `cover_assets` não consome; retry, replay e `x-facial-reindex` do mesmo `PhotoAsset` não criam segundo débito.
- Se o arquivo já foi publicado duravelmente e a confirmação falhou, a operação precisa ser reconciliada e consumida exatamente uma vez; não se apaga o arquivo nem se cobra novamente. Falha comprovada antes da durabilidade libera a reserva.

Estas regras foram escolhidas pelo proprietário em resposta às perguntas da task 1.1. Os detalhes de identidade, autorização, saldo e recuperação abaixo são decisões técnicas locais derivadas dessas regras e do código atual.

## Limites derivados do código atual

1. O tenant deve vir da sessão administrativa resolvida no servidor. IDs e referências financeiras carregam `tenant_id` e constraints compostas, seguindo `tenant-foundation` e a change de piloto.
2. Créditos, pagamentos de compras e pontos de fidelidade permanecem livros/entidades separados, com referências explícitas entre si quando a compra Mercado Pago for especificada.
3. O ledger é imutável para operações normais. Saldo é derivado ou reconstruível; correções e reversões são novos eventos auditáveis, nunca edição/exclusão de movimentos confirmados.
4. Cada upload mantém a distinção entre metadado registrado, fonte JPEG durável e processamento assíncrono. A cobrança não pode depender de o worker de prévias terminar quando a fonte já foi armazenada com sucesso, salvo decisão explícita em contrário.
5. Reserva, confirmação e liberação precisam compartilhar uma chave estável de operação lógica por item do lote. Retentativas técnicas reutilizam a operação; uma operação deliberada nova recebe identidade distinta.
6. O limite transacional é híbrido: PostgreSQL controla reserva/ledger e storage local publica o JPEG por rename atômico. Recuperação deve reconciliar `receiving`, fingerprint, arquivo durável e reserva após queda entre esses efeitos.
7. A compra de pacotes deve ser acrescentada em change separada sobre a infraestrutura Mercado Pago existente, sem misturar `SaleOrder`/checkout de cliente com compra do fotógrafo.

## Resumo financeiro no dashboard

- O endpoint privado `/admin/credits/wallet` retorna, por tenant autenticado no servidor, saldo disponível, operações pendentes, até 30 movimentos recentes e consumo confirmado dos últimos 30 dias. O período rolante de 30 dias é explícito na resposta para não induzir o frontend a inferi-lo.
- `can_upload_content` é uma leitura autoritativa da carteira no instante do snapshot; a reserva do endpoint de upload volta a validar saldo sob lock e é a decisão final. Uma resposta de insuficiência da API de upload é exibida no fluxo de lote; o frontend não calcula saldo nem substitui a decisão do servidor.
- A consulta financeira do dashboard é independente da consulta operacional existente de galerias, clientes, imports e armazenamento. Sua falha apresenta indisponibilidade sem saldo zero e não oculta os dados operacionais já carregados.
- O resumo identifica uma insuficiência somente com base na resposta da API para a operação ou lote. Uma falha ao carregar a carteira aparece como indisponibilidade e não como saldo zero; os dados operacionais que já carregaram continuam visíveis.
- O painel do fotógrafo e o checkout do cliente permanecem superfícies distintas. Compra de créditos e pontos de fidelidade continuam sob suas changes próprias.

## Modelo de dados proposto

O ledger, a reserva e as alocações serão entidades distintas. A reserva é estado de workflow por upload; movimentos confirmados e eventos de alocação permanecem append-only.

| Entidade proposta | Responsabilidade e integridade |
| --- | --- |
| `tenant_credit_wallet` | Uma linha por tenant com modo `finite` ou `unmetered`; não armazena saldo autoritativo. `tenant_id` é FK e chave primária. Um índice parcial garante no máximo um tenant `unmetered`. Novos tenants recebem modo `finite`, sem créditos iniciais; ausência inesperada da linha falha fechada. Provisionamento de tenant cria a carteira finita na mesma transação. |
| `photographer_credit_entry` | Ledger imutável com `tenant_id`, delta inteiro de créditos, tipo/origem, referência, ator, chave idempotente e data UTC. Grants, compras futuras, consumo, reversão e correção são movimentos novos; `source_entry_id` liga revogação/estorno ao crédito positivo de origem. Nenhum movimento confirmado é editado ou removido. |
| `photo_credit_operation` | Reserva/estado idempotente por `tenant_id + photo_asset_id`, fingerprint fixado na primeira intenção, quantidade 1 e estado `reserved`, `consumed`, `released` ou `reconciliation_required`. Cada intenção deliberada tem `PhotoAsset` próprio; a restrição composta impede associar foto de outro tenant. |
| `photo_credit_operation_event` | Trilha append-only de reserva, tentativa, captura, liberação e reconciliação ligada à operação e ao tenant. É a evidência recuperável das transições de workflow. |
| `photographer_credit_allocation_event` | Eventos append-only que ligam reserva, consumo, liberação ou revogação a um movimento positivo específico; suas somas provam saldo livre por origem e autorizam revogar somente o restante de uma concessão. |

### Detalhes de schema para a implementação

- `photographer_credit_package` é uma tabela global explicitamente classificada como pertencente ao `PlatformOwner`, separada das tabelas técnicas compartilhadas e das tabelas tenant-owned. Ela mantém nome, descrição opcional, quantidade positiva, preço/moeda opcionais para rascunho, estado inativo por padrão, timestamps e FKs de criação/edição para `platform_owner.admin_user_id`. Um pacote só pode ficar ativo com preço e moeda informados; não há valor ou moeda padrão. Credenciais, tokens, URLs assinadas e payloads secretos de checkout não serão armazenados no pacote; a integração de compra pertence à change Mercado Pago separada.
- Os tipos de ledger previstos no schema são grant/revogação do proprietário, compra, consumo por upload, reversão de compra e correção. A tabela usa `delta` inteiro não zero, chave idempotente única por tenant e referências opcionais ao pacote, operação e movimento positivo de origem. Consumo de upload exige operação, origem e delta `-1`; um índice único parcial permite no máximo um consumo por operação.
- Cada movimento positivo forma um lote de origem. A reserva escolhe a origem mais antiga com saldo livre pela ordem FIFO `(created_at, id)` e cria evento imutável. Captura cria o movimento negativo ligado à origem e um evento de consumo; falha comprovada libera a mesma reserva com novo evento. O saldo livre por origem é o valor positivo original menos consumos, revogações e reservas ainda ativas.
- Revogar exige identificar o `owner_grant` original e limita a quantidade ao saldo livre desse lote; não pode retirar créditos reservados, consumidos ou de outra origem. A entrada negativa aponta para o grant original e a alocação registra a revogação. Grant, reserva, captura e revogação serializam pela linha da carteira do tenant.
- Para manter ownership verificável no banco sem exigir que o proprietário global seja membro do tenant beneficiário, o ledger separa `actor_admin_id` (FK composta para membership do tenant) de `global_owner_admin_id` (FK para o PlatformOwner persistido). Uma concessão/revogação usa a segunda identidade; um ator técnico ou de tenant nunca herda autoridade global. A tabela de pacote e seus atores usam a mesma identidade persistente de proprietário.
- Operações guardam `photo_asset_id` anulável para permitir desassociação explícita antes de exclusão física, mais `photo_asset_id_snapshot`, `storage_key_snapshot`, fingerprint imutável, quantidade fixa em um, estado, timestamps e FKs compostas. Eventos guardam tenant, operação, tipo, instante UTC e detalhes sanitizados opcionais. Ledger, eventos de operação e alocações são append-only também no PostgreSQL.
- A criação do wallet finito de um novo tenant ocorre na mesma transação do provisionamento. O setup explícito do proprietário materializa o modo `unmetered` somente para o tenant validado; nenhuma linha de wallet contém saldo editável.

O `photo_credit_operation.photo_asset_id` será nullable com FK composta para `photo_asset(id, tenant_id)`, acompanhado de `photo_asset_id_snapshot` não nulo. Antes da exclusão física da foto, a aplicação desassocia a operação mantendo o snapshot; ledger, operação e histórico sobrevivem à limpeza e não geram reembolso automático.

O saldo é reconstruído da soma de entradas confirmadas. Saldo disponível é essa soma menos reservas `reserved` e `reconciliation_required`. A linha da carteira funciona como lock por tenant, não como saldo editável. Uma projeção cacheável poderá ser adicionada somente como derivada e reconstruível, caso benchmark justifique.

Todos os caminhos que alteram uma operação de upload adquirem locks nesta ordem: carteira do tenant e depois operação da foto. O reconciliador seleciona um candidato sem lock, bloqueia a carteira e então reivindica a operação ainda pendente. Isso mantém a ordem consistente com reserva, consumo, liberação e revogação.

## Identidade e fluxo de upload propostos

1. A identidade financeira continua sendo `tenant_id + photo_asset_id`. Para cada seleção deliberada de arquivo, o frontend cria um UUID de intenção e forma a chave com o escopo da galeria/pasta, SHA-256 e UUID. Antes de registrar, compara fingerprints com as fotos da pasta e pede confirmação única para o lote repetido: confirmar permite novos `PhotoAsset`s/operações; cancelar filtra só as repetições e prossegue com fotos novas. Retries técnicos reutilizam exatamente a mesma chave/asset, e reindex usa o asset já existente. O UUID de intenção não é segredo nem substitui validação do fingerprint.
2. Para `cover_assets`, a rota mantém o comportamento atual de mídia e derivados sem abrir operação de crédito. O tenant do proprietário em modo `unmetered` também não abre reserva nem movimento de consumo.
3. Para tenant finito e pasta `content`, `register_folder_photo_asset` extrai o SHA-256 da `storage_key`, cria/reutiliza somente o asset identificado pela mesma intenção e reserva um crédito na mesma transação, antes de a UI chamar o `PUT` de bytes. Um UUID diferente representa uma seleção nova mesmo com o mesmo hash. A UI envia `allow_duplicate_content` somente após o aceite; a rota bloqueia uma chave nova que corresponda a fingerprint já registrado na pasta sem esse aceite, serializando a decisão pelo lock da pasta. Saldo insuficiente recusa o cadastro e impede o início do envio. Chaves legadas `hash.jpg` continuam legíveis; novas chaves carregam o UUID da intenção. O proprietário ilimitado e capas permanecem isentos.
4. Como proteção para clientes que chamem o `PUT` diretamente, a rota de fonte deriva o fingerprint da `storage_key` e garante/reutiliza a reserva antes de ler o corpo da requisição. Depois da leitura, valida que o SHA-256 real corresponde à identidade reservada. Conteúdo diferente falha fechado e não consome o crédito reservado.
5. Retry/replay encontra a operação pela chave única do asset. Se já consumida com o mesmo fingerprint, responde idempotentemente; `x-facial-reindex` reusa a mesma operação. Uma nova seleção deliberada cria chave/asset/operação próprios, mesmo com bytes iguais. O mesmo asset não pode ser reutilizado para conteúdo incompatível.
6. Cancelamento ou erro antes do rename comprova ausência do arquivo e libera a reserva; se a ausência não puder ser provada, mantém-se a reserva para reconciliação. Após rename, uma transação cria um único movimento `upload_consumption` e marca a operação `consumed`. Falha no commit preserva o arquivo e a reserva.
7. O reconciliador reivindica operações antigas pendentes com lock/lease e valida o caminho confinado ao tenant e o fingerprint. Fonte durável correspondente captura uma vez; fonte ausente libera a reserva; divergência ou indisponibilidade mantém `reconciliation_required`, conserva o arquivo e não devolve disponibilidade até resolução segura. O worker de derivados não decide a cobrança.
8. Em lote, cada `PhotoAsset` tem sua própria operação e reserva. Falhas parciais liberam apenas os itens comprovadamente não duráveis; nenhuma operação do lote substitui as identidades individuais.

## Owner global e tenant ilimitado

`PlatformOwner` persiste o proprietário como singleton por `admin_user_id`, enquanto `TenantAdmin` associa esse sujeito ao tenant. O schema atual não guarda diretamente `owner_tenant_id`. Se a base estiver realmente vazia, sem tenants e sem PlatformOwner, a migration cria apenas o schema, sem seed de carteira; não existe associação a resolver ainda. Se houver tenants, a criação inicial do modo `unmetered` SHALL resolver a associação persistida e exigir exatamente um membership ativo; ausência ou ambiguidade SHALL abortar sem escolher e-mail, primeiro tenant ou fallback. Os demais tenants existentes recebem modo `finite` sem crédito. O resultado fica materializado na linha de `tenant_credit_wallet`, para que memberships futuros não transfiram automaticamente a isenção. Provisionamento posterior cria carteira finita; estabelecimento explícito do PlatformOwner altera somente seu tenant validado para `unmetered`. Grants/revogação de pacote e créditos exigem sessão do `PlatformOwner` persistente; `InstallationOperator` continua sem capacidade comercial.

Revogar concessão será movimento negativo auditável limitado à parcela ainda disponível daquela concessão. Não poderá retirar créditos já consumidos, tornar o saldo negativo ou modificar compras/pagamentos; reembolso/chargeback de compra continua na change Mercado Pago própria.

## Revisão e gate da migration

- O proprietário aprovou este desenho técnico em 31/10/2026. O gate da task 2.1 está satisfeito.
- A migration deve falhar antes de DDL/dados se houver tenants e a associação do proprietário estiver ausente/ambígua; a única exceção é instalação realmente vazia sem tenant/PlatformOwner.
- Não consultar nem alterar produção como parte desta change. Nenhuma quantia de crédito será semeada.

## Compatibilidade

- Não alterar o checkout e os pedidos de clientes no escopo desta change.
- Não remover nem reformatar `uploadJpeg`, `register_folder_photo_asset`, `import_photo_source`, `PhotoAnalysis` ou `MediaJob` até validar os consumidores e os testes de retry/reprocessamento.
- Não semear créditos, habilitar uma flag comercial ou atualizar saldo de tenants por migration.
- Qualquer migration nova deve ser aditiva, ensaiada em PostgreSQL descartável a partir da revisão real da base, com upgrade, downgrade seguro, rollback de falha e preservação de dados sintéticos.
- O frontend só exibirá valores retornados por API autorizada; não calcula saldo ou disponibilidade como autoridade.
- A falha isolada na consulta da carteira não deve esconder galerias, clientes, imports ou storage do dashboard existente, nem induzir leitura de saldo zero.

## Gestão de carteiras pelo proprietário global

- A UI global inclui catálogo de pacotes e uma área separada para procurar/selecionar tenants de fotógrafos, consultar estado, identificadores de contato, carteira, histórico recente e concessões ainda com quantidade livre.
- O modelo `Tenant` não tem nome comercial. A identificação legível vem dos e-mails das memberships ativas (`TenantAdmin`/`AdminUser`) e do `canonical_host`, acompanhados do UUID do tenant para desambiguar. Se não houver membership ativa, a UI mostra o identificador do tenant e o estado sem inventar nome.
- `GET /admin/platform/credit-tenants` será owner-only e `private, no-store`; retorna uma lista compacta de tenant UUID/estado/host/e-mails ativos e snapshot agregado da carteira. Após selecionar uma conta, `GET /admin/platform/credit-tenants/{tenant_id}` retorna o wallet snapshot, até 30 movimentos recentes e concessões do tipo `owner_grant` com saldo ainda revogável reconstruído pelos eventos FIFO. O tenant unmetered do proprietário poderá ser consultado, mas não receberá ações comerciais.
- Conceder exige quantidade inteira positiva e referência informada pelo proprietário. Revogar exige selecionar a concessão de origem, quantidade não superior ao saldo livre daquela concessão e referência explícita. O servidor continua autoridade final e as chamadas usam idempotency key estável para repetir com segurança a mesma tentativa.
- Ledger/auditoria já gravam o sujeito PlatformOwner, tenant, origem, quantidade, referência e instante UTC. A UI confirma sucesso somente após resposta da API e atualiza o saldo/histórico do tenant selecionado. Falha de atualização preserva a mensagem do servidor e não representa como concluída a operação sem confirmação.
- Pacote é catálogo, não uma autorização para checkout. Compra via Mercado Pago, valores automáticos, cadastro público e ativação comercial permanecem fora desta change.
