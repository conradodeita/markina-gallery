## Why

A validação humana do editor e a revisão do domínio mostraram três desalinhamentos estruturais: as faixas atuais aplicam um único preço ao pedido inteiro em vez de calcular parcelas progressivas, os links seguros são descartados ou não podem ser reutilizados pela interface, e cada galeria privada ainda pertence a uma única cliente embora o produto precise compartilhar o mesmo acervo privado entre familiares com jornadas comerciais isoladas. A mudança consolida essas decisões antes de ampliar o ciclo completo em homologação.

## What Changes

- **BREAKING**: substituir a propriedade exclusiva da galeria privada por membros autorizados. Uma privada poderá conter várias clientes, mas o mesmo telefone verificado SHALL pertencer a no máximo uma privada por Galeria pública.
- Manter o acervo da privada compartilhado entre seus membros e isolar por cliente favoritos, visualizações, comentários, seleções, carrinho, pedidos, valores, pagamentos e histórico; nenhuma cliente verá membros ou atividades de outra.
- Resolver toda seleção manual adicional para a única privada do par `Galeria pública + cliente`, somando fotos de pessoas diferentes no mesmo total individual e reutilizando as mesmas referências de mídia sem cópia.
- Permitir entrada em Galeria pública ou privada por link opaco estável, revogável e rotacionável, sempre com OTP para criar um vínculo novo. O link privado poderá cadastrar novos membros e também vincular a Galeria pública de origem, sem conceder acesso a privadas irmãs ou a outras origens.
- Notificar o fotógrafo quando uma privada for criada e quando uma nova cliente ingressar; permitir bloquear, desbloquear e desvincular uma cliente somente daquela privada sem apagar cadastro, outras galerias ou histórico comercial.
- **BREAKING**: substituir o cálculo de volume no qual a faixa alcançada precifica todas as fotos por preço progressivo em parcelas. No exemplo 1–30 a R$ 7,00 e 31–60 a R$ 6,00, 60 fotos totalizam R$ 390,00.
- Criar tabelas globais de preço progressivo identificadas por código e nome, selecionáveis por dropdown na etapa Vendas. A seleção SHALL materializar um snapshot na Galeria pública; alterações ou exclusão do modelo global não mudarão galerias nem pedidos existentes.
- Oferecer alternativamente preço unitário fixo por Galeria pública, com entrada e validação em moeda brasileira e persistência em centavos inteiros.
- Exibir à cliente total progressivo, faixa, quantidade e economia em rodapé flutuante e na conferência, mantendo o backend como autoridade do cálculo e congelando os termos no pedido.
- Simplificar PIX manual para aceitar um código copia-e-cola validado ou uma chave simples de CPF, telefone ou e-mail. Para chave simples, coletar os dados públicos mínimos do recebedor, gerar localmente um BR Code válido e preservar somente a representação operacional necessária no snapshot do pedido, sem exigir um segundo campo técnico de payload.
- Fazer `Avançar` nas etapas editáveis salvar, aguardar sucesso e somente então navegar; impedir perda silenciosa ao trocar de etapa e ampliar a lista controlada de tipografias locais.
- Completar na etapa Clientes o gerenciamento do link público e dos links privados, criação administrativa da privada, membros, notificações e bloqueios com estados orientados pelo backend.
- Fazer `Salvar e avançar` na etapa Imagens publicar a rodada já processada antes de abrir Clientes, sem confundir processamento concluído com publicação nem criar automaticamente uma privada; renomear a ação administrativa da privada de acordo com seu efeito real.
- Preservar a independência entre ciclo operacional e histórico: públicas, privadas e vínculos podem ser congelados, bloqueados, desvinculados ou removidos conforme inventário, enquanto pedidos, pagamentos, entregas, snapshots e mídia histórica autorizada permanecem.
- Preparar a associação de resultados futuros com origem `facial` à privada existente, sem criar endpoint, processar biometria ou liberar busca facial nesta change. O produto facial permanece bloqueado pelo spike `spike-private-facial-discovery`, por revisão de privacidade e pelo gate do roadmap.
- **BREAKING**: superseder, no escopo afetado, requisitos ativos de uma privada por proprietária, convite privado restrito a um único telefone e preço da faixa aplicado ao pedido inteiro. Changes ainda aguardando revisão humana continuarão abertas até a nova experiência ser validada em homologação.

## Capabilities

### New Capabilities

- `gallery-sales/reusable-progressive-pricing`: modelos globais identificados, preço fixo ou progressivo por parcelas, snapshot por Galeria pública, moeda brasileira, simulador e economia.
- `messaging/gallery-membership-notifications`: notificações idempotentes ao fotógrafo para criação de privada e entrada, bloqueio ou desbloqueio de membro.

### Modified Capabilities

- `auth`: exigir OTP para criar vínculo a uma nova Galeria pública ou privada, reutilizar identidade por telefone e impedir que bloqueio seja contornado por outro link da mesma origem.
- `client-access/cloned-private-galleries`: substituir proprietária única por associação multiusuário com acervo comum, estados individuais e unicidade `Galeria pública + cliente`.
- `client-access/derived-galleries`: apresentar privadas compartilhadas autorizadas e histórico individual, inclusive após bloqueio ou remoção operacional.
- `gallery-sales/client-selection-operations`: calcular e operar seleção, carrinho, pedido e compra por membro dentro do acervo privado comum.
- `gallery-sales/operational-gallery-interface`: salvar ao avançar, completar links e membros na etapa Clientes, bloquear cliente e usar os novos modelos comerciais.
- `gallery-sales/original-gallery-experience`: apresentar rodapé de seleção, conferência PIX e estados financeiros individuais sem expor atividade de outros membros.
- `gallery-visualization-and-watermark-controls`: ampliar tipografias locais controladas e manter apresentação herdada pela privada após remoção da origem.
- `media-storage/protected-previews`: autorizar a mesma referência privada para vários membros sem expor originais, outras privadas ou interações de terceiros.

## Impact

- Banco e migrations: nova associação de membros, unicidade por origem e cliente, capacidade reutilizável de entrada privada, modelos globais/snapshots de preço e adaptação conservadora de privadas existentes.
- Backend FastAPI e worker: autorização multiusuário, bloqueio, notificações, resolução idempotente por telefone, preço progressivo, quote/economia, QR PIX e consultas agregadas sem N+1.
- Frontend Next.js: etapas 01–05, navegação com persistência, controles de links, membros e bloqueio, cadastro global de preços, checkout/rodapé e fontes locais licenciadas.
- Compatibilidade: pedidos e histórico existentes permanecem imutáveis; privadas legadas recebem seu cliente atual como primeiro membro; links e contratos antigos exigirão janela de compatibilidade e migração explícita.
- Privacidade: cada cliente vê somente seu estado comercial; links continuam opacos e auditáveis; nenhuma biometria ou dado real de criança será processado por esta change.
- Operação: nenhuma migration destrutiva, deploy ou habilitação facial é autorizada pela proposta; homologação exigirá inventário zero-impact, dados sintéticos, migrations no head e nova revisão humana desktop/mobile.
