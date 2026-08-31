## Why

O gerenciamento atual exige desmontar manualmente vínculos, fotos e pastas antes de excluir uma Galeria pública, cria galerias privadas antes de existir uma seleção efetiva e ainda não oferece ao fotógrafo uma leitura clara do estado de cada cliente. Além disso, o teste real de OTP confirmou a negação correta de acesso sem convite, mas tornou necessário explicitar a diferença entre não criar um cadastro permanente de cliente e reter temporariamente dados mínimos do desafio de autenticação.

## What Changes

- Padronizar “Galeria pública” como nome visível do acervo hoje denominado galeria-mãe/acervo-fonte, sem transformar eventos coletivos em grade pública nem alterar os identificadores internos antes de uma migração segura.
- Permitir que o fotógrafo exclua uma Galeria pública em uma única operação, mesmo quando existirem pastas, fotos, galerias privadas ou clientes vinculados.
- Excluir a disponibilidade pública, os vínculos e a mídia sem referência privada da galeria, sem excluir clientes nem galerias privadas derivadas. Fotos ainda disponíveis em ao menos uma privada SHALL permanecer como o mesmo ativo físico compartilhado, sem cópia, até o encerramento da última referência privada.
- Preservar, de forma independente e imutável, pedidos, pagamentos, itens comprados, entregas e demais evidências comerciais necessárias ao histórico do fotógrafo e do cliente.
- Permitir desvincular individualmente um cliente da Galeria pública, revogando seu acesso operacional sem apagar seu cadastro nem seu histórico comercial.
- Resolver ou criar uma única identidade de cliente pelo telefone E.164 verificado, sem duplicar cadastro nem usar o nome como credencial; criar sua galeria privada por primeira seleção autorizada ou por ação explícita do administrador com ao menos uma foto disponível.
- Manter acessíveis em paralelo todas as Galerias públicas abertas para a cliente, suas galerias privadas ativas e seu histórico; uma nova foto escolhida na Galeria pública SHALL ser incorporada à única galeria privada correspondente ao mesmo par de cliente e origem.
- Separar fotos disponíveis na galeria privada de seleções para compra, registrando a origem da disponibilidade (`admin`, `client` ou origem futura autorizada). Uma galeria criada pelo administrador SHALL poder permanecer com fotos disponíveis e nenhuma seleção.
- Encerrar automaticamente uma galeria privada derivada pelo cliente somente quando ela ficar sem fotos disponíveis e sem impedimento comercial; remover uma seleção SHALL NOT remover referências disponibilizadas pelo administrador.
- Exigir login por OTP antes de entregar qualquer prévia fotográfica. O backend SHALL declarar o modo de acesso da Galeria pública (`standard`, `invite_only` ou `collective_protected`) e SHALL NOT delegar essa decisão ao frontend.
- Tratar links públicos e convites individuais como localizadores opacos, revogáveis, rotacionáveis, expirantes e auditáveis, com token armazenado por hash; a posse do link SHALL NOT substituir a validação do telefone proprietário.
- Herdar da Galeria pública, sem overrides arbitrários nesta change, configuração comercial, PIX, mensagens, interações, apresentação visual e prazo padrão das galerias privadas; o prazo efetivo SHALL ser materializado na derivação e os valores comerciais SHALL ser congelados no pedido.
- Exigir login ao abrir o link de uma Galeria pública; quando já existir sessão de cliente, vincular idempotentemente o `Client` autenticado à origem somente quando o modo de acesso permitir e continuar sem solicitar novo OTP. Garantir que esse acesso ou outra galeria privada nunca conceda acesso às galerias privadas de terceiros.
- Manter a derivação facial fora da implementação desta change até o spike obrigatório; quando habilitada por change própria, ela SHALL reutilizar o mesmo vínculo individual e criar somente resultado privado aprovado.
- Reestruturar a listagem de clientes vinculados com acesso direto à galeria privada, contadores de fotos selecionadas e compradas, estado visual da galeria e ação clara de desvinculação.
- Padronizar a terminologia visível do produto de “Responsável” para “Cliente” e de “Galeria-mãe”/“Acervo-fonte” para “Galeria pública”, preservando nomes técnicos internos apenas quando uma migração imediata trouxer risco sem benefício funcional.
- Formalizar a minimização de dados no OTP sem convite: a tentativa negada não cria `Client`, vínculo ou sessão; dados transitórios de autenticação são retidos somente pelo período operacional e de segurança definido e depois anonimizados ou removidos.
- Definir o tratamento seguro de remoção diante de carrinho e pedidos: descartar carrinho sem pedido; cancelar com auditoria pedido pendente sem comunicação de pagamento; bloquear enquanto o pagamento estiver em revisão; e permitir limpeza operacional após confirmação somente quando snapshots e evidência histórica estiverem materializados.
- Preservar no histórico comercial snapshots, uma prévia histórica mínima protegida e a referência/entrega final autorizada, sem reter todos os originais apenas para histórico e sem fixar nesta change um prazo legal não definido.
- **BREAKING**: substituir a resposta síncrona `204` da exclusão administrativa por uma operação acompanhável e idempotente, com identificador e estado, sem exigir a sequência manual atual.
- **BREAKING**: esta change supersede, para o escopo afetado, propostas ativas que exijam exclusão somente de galeria vazia, criem galeria privada ao simples cadastro/link ou tratem a galeria privada como única superfície de navegação do cliente. A reconciliação formal dessas propostas e das capabilities transversais SHALL ocorrer antes de editar código.

## Capabilities

### New Capabilities

- `gallery-sales/commercial-history-retention`: histórico comercial imutável e independente do ciclo de vida operacional das galerias, pastas e fotos.

### Modified Capabilities

- `auth`: deduplicar identidade por telefone verificado, reutilizar sessão existente em links de galeria e minimizar dados de tentativas OTP negadas.
- `client-access/cloned-private-galleries`: derivar a galeria privada por seleção do cliente ou criação administrativa, separar disponibilidade de seleção, herdar a configuração da Galeria pública, garantir propriedade exclusiva e permitir sua remoção segura quando ficar sem referências disponíveis.
- `client-access/derived-galleries`: apresentar conjuntamente Galerias públicas abertas, galerias privadas ativas e histórico, mantendo acesso comercial após remoção da galeria operacional.
- `gallery-sales/client-selection-operations`: distinguir fotos disponíveis, selecionadas e compradas na ficha individual e aplicar a política comercial segura às remoções.
- `gallery-sales/original-gallery-experience`: ampliar a jornada da cliente para Galerias públicas autenticadas, privadas derivadas e histórico, com estados decididos pelo backend.
- `gallery-sales/operational-gallery-interface`: permitir exclusão integral da Galeria pública, criação administrativa da galeria privada, modos explícitos de acesso, indicadores por cliente e terminologia visível padronizada.
- `media-storage/protected-previews`: exigir autenticação e autorização antes de qualquer prévia fotográfica e preservar somente evidência histórica mínima protegida.
- `media-storage/staged-folder-release`: aplicar o modo de acesso na liberação e, ao excluir a Galeria pública, remover pastas, fotos e derivados sem referência privada, mantendo uma única cópia dos ativos ainda exibidos por privadas e a mídia histórica mínima exigida por compras.
- `gallery-visualization-and-watermark-controls`: fazer a privada herdar a apresentação efetiva da Galeria pública, manter proteção global incorporada e aplicar o ciclo de vida comercial à exclusão em massa.

## Impact

- Backend: modelos e migrations de pedidos/itens, serviço de snapshot histórico, desvinculação, exclusão idempotente, autorização e auditoria.
- Armazenamento: separação entre mídia operacional, mídia ainda referenciada por privadas e evidência visual histórica de itens comprados; limpeza física segura somente de originais e derivados sem referência privada ou histórica.
- APIs: modos de acesso, convites seguros, herança de configuração, derivação atômica na primeira seleção, criação administrativa, separação entre disponibilidade e seleção, regras por estado do pedido, desvinculação e exclusão da Galeria pública, estado/progresso da exclusão e métricas consolidadas por cliente.
- Frontend administrativo: cartões responsivos de clientes, indicadores coloridos, confirmação destrutiva consolidada e substituição da terminologia “Responsável”.
- Frontend do cliente: biblioteca unificada de Galerias públicas abertas, galerias privadas ativas e histórico desacoplado de galerias removidas.
- Privacidade: retenção limitada de PII em desafios e entregas OTP negados, sem criação de identidade persistente fora de um convite válido.
