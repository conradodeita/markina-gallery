# Design

## Context

Veja `proposal.md` para a motivação e `specs/billing/photographer-credit-experience/spec.md` para o contrato observável.

O branch já contém localmente a carteira, o ledger, o limite ilimitado do proprietário e a administração de pacotes. A carteira expõe saldo disponível, reservas e consumo recente; os pacotes têm nome, descrição, quantidade de créditos, preço em centavos, moeda e estado ativo. A tela administrativa atual usa um seletor simples de tenant. O upload não apresenta o estado da carteira durante o envio.

O portal `add-photographer-signup-portal` já coleta o nome e e-mail informados e persiste o nome em `Tenant.photographer_name` pela migration aditiva 0097, validada em prova sintética local. Esta change reutiliza esse perfil sem backfill; contas legadas sem nome permanecem pesquisáveis pelo e-mail. Os gates R14 continuam condicionando abertura pública e publicação, não a prova local já autorizada. `add-mercadopago-credit-purchases` usa o fluxo Orders e a conta já configurada no tenant do proprietário, mantendo o tenant comprador separado. A política de chargeback após consumo foi aprovada e implementada localmente na change de compras: bloquear uploads/compras até revisão manual, sem débito automático.

## Goals / Non-Goals

**Goals:**

- Integrar o estado de crédito ao envio sem reproduzir no navegador as regras financeiras do ledger.
- Localizar contas pelo nome do fotógrafo ou pelo e-mail administrativo com autorização de proprietário.
- Apresentar os pacotes ativos em cards bem compostos, responsivos, interativos e alimentados pelo catálogo real.
- Encaminhar a seleção ao fluxo de compra de créditos que validar tenant, pacote, preço e confirmação no servidor.

**Non-Goals:**

- Alterar autenticação/login, cobrança de upload, idempotência do ledger, regra de duplicadas, retry ou reindex.
- Criar recebedor, credenciais, webhook ou ordem Mercado Pago paralelos.
- Introduzir preços promocionais, selo de recomendação ou conteúdo comercial que o proprietário não configurou.
- Fazer deploy, migration remota, provisionamento ou compra financeira real.

## Decisions

1. **O servidor continua fonte de verdade da carteira.** A interface mostra saldo/reservas existentes e estados por arquivo retornados pelo upload. Após confirmação ou liberação, atualiza pelos dados da resposta ou consulta autorizada. Timeout ambíguo mantém indicação pendente até reconciliação; o navegador não decrementa o saldo por conta própria. A carteira ilimitada do proprietário permanece ilimitada.

2. **A pesquisa usa sugestões remotas e mínimo de dados.** O proprietário digita nome informado no cadastro ou e-mail administrativo; um endpoint protegido aplica a autorização no servidor e retorna somente ID, estado, host e identidade mínima. O e-mail só é exibido quando há um administrador ativo não ambíguo. A seleção abre o painel atual da carteira. Um seletor local de todos os tenants foi considerado, mas ampliaria a exposição e escala mal conforme o cadastro crescer.

3. **O nome do cadastro integra o perfil do fotógrafo.** O portal aprovado já coleta e persiste em `Tenant.photographer_name` o nome fornecido pelo fotógrafo junto à identidade administrativa. O painel usa o valor persistido sem solicitar o nome novamente em Configurações. Não se infere nem faz backfill de nomes a partir do e-mail, do domínio ou de dados de clientes; legado continua com nome vazio.

4. **Os cards usam o DTO autoritativo do catálogo.** Exibir nome, descrição disponível, quantidade, preço e moeda retornados pelo servidor. Não derivar desconto, preço por crédito, promoção ou pacote “popular”. A composição visual deve seguir a linguagem já usada pela plataforma, com hierarquia legível, estados claros em toque/teclado/ponteiro e movimento decorativo reduzido quando solicitado pelo dispositivo.

5. **Catálogo fica imediatamente abaixo da carteira.** A área do fotógrafo autenticado, aprovado e ativo carrega somente pacotes ativos. Cards e botão de compra apresentam a mesma ação acessível para teclado e toque e abrem o checkout transparente dentro da plataforma; não há navegação para página externa hospedada pelo Mercado Pago.

6. **A compra usa a conta do proprietário, mas mantém o comprador separado.** O servidor resolve a identidade `PlatformOwner`, o tenant administrativo associado e a conta Mercado Pago ativa configurada em Payment Providers. O tenant do fotógrafo comprador vem da sessão; o tenant/conta recebedora vêm do proprietário. O browser não escolhe nenhum deles nem envia preço/quantidade como autoridade. Reutiliza-se `OrdersProvider` e o cofre/credencial já configurados; não se cria credencial global paralela.

7. **Ordens de crédito não são pedidos de fotografia.** Cada compra mantém identidade, tenant comprador, pacote/preço congelados e vínculo à conta recebedora do proprietário em registros próprios de compra de créditos. O handler de notificações consulta a Order com a conta proprietária e encaminha a referência para a compra de crédito correspondente, sem converter a compra em `MercadoPagoPayment`, `SaleOrder` ou `SaleOrderItem` de fotos.

8. **Somente Mercado Pago é provedor no checkout de créditos.** Mercado Pago é pré-selecionado quando a conta existente do proprietário estiver ativa e disponível. O PIX próprio do sistema não participa da compra de créditos nem herda `pix_enabled`; meios nativos do próprio checkout Mercado Pago, se expostos pelo Orders, continuam pertencendo ao provedor Mercado Pago. A indisponibilidade da conta não faz fallback para outro tenant ou provedor.

9. **Estados vazios e falhas permanecem explícitos.** Loading, catálogo vazio, erro de leitura, checkout pendente, conta recebedora indisponível e resultado financeiro confirmado não compartilham uma mensagem genérica. Falha de leitura não deve parecer catálogo vazio nem saldo zero.

10. **Consulta explícita e ordenação das carteiras do proprietário.** O seletor inicia sem opção, com o placeholder Selecione; não consulta nem lista fotógrafos até haver busca com dois caracteres ou seleção explícita de Todos, Ordem alfabética ou Mais recentes. A busca textual combina nome informado e e-mail ativo. Ordem alfabética usa o nome persistido e recorre ao e-mail somente quando o nome está ausente e existe um único administrador ativo; identidade ambígua sem nome fica por último, sem ordenar por e-mail oculto. Todos lista o conjunto consultável com ordem estável por tenant UUID; Mais recentes usa `Tenant.created_at DESC`; UUID desempata as ordenações. A API `/admin/platform/credit-tenants/search` aceita `query` opcional, `mode=all|alphabetical|recent` opcional, `limit` até 20 e `offset`; retorna `items` e `has_more`, sem carregar carteira/ledger de cada resultado. Sem modo e sem busca de dois caracteres, a resposta é vazia. A lista tem botão Carregar mais quando necessário. Mudança de busca/ordenação limpa seleção e paginação; Limpar restaura o estado inicial. Selecionar um resultado abre a carteira correta e fecha sugestões. Não se interpreta erro como lista vazia nem se reutiliza resposta atrasada.

Esta extensão foi solicitada e priorizada diretamente pelo proprietário enquanto a revisão dos limites externos de `add-mercadopago-credit-purchases` permanece aberta. A busca usa o perfil já persistido localmente; ela não encerra a validação externa de compras nem libera publicamente o portal de cadastro.

11. **Histórico por pasta, sem alterar o ledger.** Revisão expressa do proprietário em01/11/2026: agrupar consumo por pasta, mantendo referência, data/hora, quantidade de fotos e total. O servidor agrega todos os lançamentos upload_consumption confirmados da pasta antes de paginar os resumos; não agrupa somente os30lançamentos recentes. Cada pasta possui uma linha, ordenada pelo último consumo confirmado; novos uploads atualizam essa linha. Compras e demais movimentos mantêm identidade individual. A interface rotula a data/hora como último envio e mostra somente o resumo. Por decisão expressa posterior do proprietário em 01/11/2026, não oferece botão de expansão, lista por foto nem consulta de detalhes individuais na navegação habitual.

12. **Proveniência preservada pelo evento já existente.** Na criação de nova reserva, registrar ID/nome da pasta e ID/nome da galeria no JSON details do evento reserved, junto à origem FIFO já registrada. São metadados descritivos imutáveis, sem nova tabela, migration, alteração de saldo ou reescrita financeira. Para dados anteriores, resolver somente o vínculo real PhotoAsset→PhotoFolder do mesmo tenant quando ainda existir. Não inferir pasta pelo filename ou storage_key. Se o legado já não tiver vínculo nem snapshot, preservá-lo individual internamente e sinalizar na interface a existência de consumos anteriores sem pasta identificável, sem listar as operações; não inventar uma pasta nem combinar origens desconhecidas como se fossem a mesma. Uma pasta ainda existente exibe seu nome atual; após remoção, seu snapshot permite manter referência e histórico, sem link de mídia. Homônimas e tenants diferentes nunca se combinam. Referência do resumo identifica a pasta; referências de operações permanecem nos registros internos e nas consultas autorizadas de investigação, fora da interface habitual.

13. **Consultas limitadas e compatíveis.** Manter os campos atuais de ledger para consumidores existentes e acrescentar a projeção de histórico agregado. Resumos e detalhes usam paginação no servidor, limite validado e ordenação estável. A projeção usa endpoints próprios: o GET wallet consumido durante uploads preserva seu custo e não agrega todo o histórico a cada arquivo. Paginação usa o as_of retornado na primeira página para manter totais/detalhes coerentes enquanto novos lançamentos chegam. A API resolve tenant pela sessão para fotógrafo e exige PlatformOwner para consultas globais a um tenant; resposta private,no-store. O resumo não envia todos os lançamentos por foto ao browser. Loading, erro, vazio e carregamento incremental são distintos. Carteira, FIFO, retries, reindex, exclusão de capas e débito após fonte durável permanecem inalterados.

14. **Texto de pagamento voltado ao fotógrafo.** Por revisão expressa do proprietário, o catálogo informa somente o pagamento protegido pelo Mercado Pago dentro da plataforma. A frase sobre o PIX interno não ser usado é retirada da UI, mantendo a regra técnica de provedor sem alteração.

## Risks / Trade-offs

- **Conta legada sem nome informado** → permanece pesquisável pelo e-mail, sem inferência ou backfill; o nome aparece nas sugestões somente quando está persistido.
- **Gates R14 do portal pendentes** → não há abertura pública nem publicação até os gates documentados naquela change; a prova local de nome e busca não altera esse bloqueio.
- **Buyer e recebedor pertencem a tenants diferentes** → resolver a conta do recebedor pela identidade global do proprietário e guardar comprador e conta recebedora como vínculos distintos; testar que a credencial do fotógrafo comprador nunca é usada.
- **Chargeback após consumo de créditos** → aplicar o bloqueio tenant-wide e revisão manual aprovados na change Mercado Pago; preservar ledger sem débito automático. Simulação externa de chargeback online continua limitada pelo sandbox e registrada naquela change.
- **Saldo pode mudar em outra sessão** → sempre revalidar no servidor após operações e antes de apresentar estado final; o saldo visível é informativo e não autoriza upload.
- **Busca pode revelar dados de outros tenants** → autorização server-side, resposta mínima e testes negativos para fotógrafo, cliente e operador técnico.
- **Animações podem prejudicar acesso** → estados também devem ser comunicados por texto/semântica e respeitar `prefers-reduced-motion`.

## Migration Plan

1. Após revisão humana desta change, implementar upload, pesquisa e catálogo em etapas pequenas, preservando a implementação local já existente.
2. Se o perfil atual exigir coluna para nome do fotógrafo, usar migration aditiva vinculada ao portal de cadastro; não inventar dados para contas existentes.
3. Validar cada etapa localmente com contratos e testes direcionados, depois revisar o diff e executar as verificações amplas do projeto.
4. Sincronização de specs, arquivamento, migration remota, ativação de cadastro, compra real e publicação seguem os gates e autorizações próprios; este design não autoriza operações externas.
