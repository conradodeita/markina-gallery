# Histórico agrupado por pasta — validação incremental

## Revisão aprovada pelo proprietário

Em 01/11/2026, ao visualizar a jornada sintética, o proprietário pediu agrupar o consumo por pasta e manter referência, data/hora e quantidade de fotos. Implementação segue tasks 5.1–5.4. A contabilidade individual permanece imutável.

## Backend — 5.1 e 5.2

- O evento reserved já existente recebe IDs/nomes da pasta e galeria, resolvidos por vínculos reais do mesmo tenant. Não há migration nem novo saldo armazenado. Teste verifica retry sem outro evento, snapshot preservado após rename/remoção, proveniência estrangeira vazia e saldo correto.
- A projeção agrupa consumos por identidade da pasta antes do LIMIT. Compras/concessões e outros lançamentos permanecem individuais. Não interpreta storage_key nem agrupa legados de origem desconhecida.
- O nome atual é mostrado enquanto a pasta existe; snapshot sustenta histórico após remoção. Fonte legada ainda vinculada usa FK real; sem vínculo e sem snapshot, mostra movimento individual com aviso de origem não identificável.
- Endpoints GET próprios: /admin/credits/history e /admin/credits/history/folders/{folder_id}; proprietário usa /admin/platform/credit-tenants/{tenant_id}/history e .../history/folders/{folder_id}. Todos limitam páginas a 30, offset até 100000 e mantêm o as_of na paginação. Visão global exige PlatformOwner; consulta estrangeira recebe404. Respostas permitidas são private,no-store.
- O endpoint wallet usado durante uploads permanece sem agregação de histórico. A resposta de detalhes do tenant do proprietário ganha history, preservando os campos anteriores.
- Cinco cenários backend passaram em SQLite (4 testes em 46,62 s + 1 de compra individual em 11,10 s), e os cinco passaram juntos em PostgreSQL 17 exclusivo (27,91 s). Cobrem36 fotos numa pasta, homônimas em galerias diferentes, atualização com novo consumo, snapshot estável entre páginas, detalhes 20+16 sem duplicação, grants separados, compras do mesmo pacote individualizadas, legado sem proveniência, rename/remoção, limites/cache e negação de visão global ao fotógrafo.
- Logs fora do Git: folder-history-sqlite.log e folder-history-postgresql.log em C:/codex-data/temp/pyp-mp-external-20261101.

## Interface e integração — 5.3 e 5.4

- Componente credit-history compartilhado entre fotógrafo e proprietário, com nome da pasta/galeria, referência da pasta, data/hora do último envio, quantidade de fotos cobradas e total. Expansão oferece período, referências e datas/horas originais por foto. Compras/concessões mantêm referência e linha individual.
- Resumos paginam 30 itens e detalhes 20. A consulta usa as_of do resumo para manter a mesma fotografia financeira entre páginas. Requisições são abortadas e respostas atrasadas ignoradas quando o tenant ou snapshot muda; os totais não são decrementados no browser.
- Seis testes novos de componente verificam carregamento sob demanda, metadados, página de detalhes 20+16, resumos paginados, resposta atrasada na troca de tenant, erro/vazio/legado e retry dos detalhes sem perder o resumo.
- Testes frontend focados: 28/28. Suíte frontend completa atual: **594 testes em 70 arquivos**, 130,21 s. Typecheck e ESLint direcionado passaram sem novos avisos; lint geral 0 erros/36 avisos preexistentes. Build completo passou em cópia temporária sem .env, mantendo os Next locais ativos.
- Regressão backend em PostgreSQL 17 exclusivo: **60 passed**, 6 avisos de depreciação,339,16 s. Incluiu test_credit_history, test_photographer_credits, test_mercadopago_credit_purchases e test_tenant_credit_browse. Ruff do módulo novo, serviço, main e testes passou.
- Página real do proprietário e fotógrafo conferida com o tenant jornada-creditos-20261101@example.test. Os sete lançamentos originais foram comparados por UUID: mesmos IDs, soma 6, saldo disponível 6, reservas 0 e pendências 0. A apresentação passou a quatro resumos: pasta Imagens 3 fotos/-3, Acervo 1 foto/-1, Legado 2 fotos/-2 e compra +12. Nenhum lançamento foi apagado ou reescrito.
- Expandir Legado mostrou período 01/11/2026, 18:55:17–18:56:48 e as referências originais das duas operações, incluindo 689c5af6-b2ea-4197-8c44-8637872c2e69. Datas/horas são exibidas no fuso local do navegador, a partir de UTC.
- Mobile 390×844: documento 375 px e região de histórico 305 px, sem overflow interno/horizontal; referência longa quebrou linha e valores/detalhes permaneceram legíveis. Viewport restaurado. Desktop conferido no Chrome e deixado para consulta.
- Evidência fora do Git: journey-grouped-results.json, journey-owner-grouped-desktop.jpg e journey-grouped-mobile-details.jpg, além dos logs folder-history-regression.log, folder-history-frontend-full.log, folder-history-build.log e folder-history-lint.log em C:/codex-data/temp/pyp-mp-external-20261101.
- Revisão proporcional removeu os dois renderizadores duplicados de movimentos e seus helpers/estilos sem consumidores restantes; manteve os seletores usados por compras, origens FIFO e revisão financeira. Não houve refatoração geral nem mudança de regra financeira.
- Compatibilidade: APIs de ledger/carteira mantiveram seus campos anteriores. O frontend novo requer os endpoints de projeção, portanto o futuro release deve disponibilizar API antes de web; não há migration desta revisão. O JSON de proveniência adicional é compatível com leitores anteriores.

## Pendências

- Tasks 5.1–5.4 concluídas e validadas localmente. Permanecem as tasks 1.1–1.3 de nome/cadastro, sujeitas aos gates R14, e a revisão dos limites externos do Mercado Pago na change de compras.
- Não houve deploy, migration remota ou mudança de produção. A jornada persistente deve continuar com 12 recebidos, 6 consumidos e 6 disponíveis após a revisão visual.


### Revisão final de autorização em páginas vazias

A consulta de detalhes também retorna 404 para pasta estrangeira quando offset > 0; uma página vazia não contorna a fronteira do tenant. Os cinco cenários foram repetidos no PostgreSQL após esse ajuste (5 passed, 27,92 s), e o caso HTTP foi repetido no SQLite. O harness persistente foi reiniciado com a fonte atual e preservou o schema e as sessões. Log adicional: folder-history-boundary.log.


## Revisão posterior — painel com resumos e rastreabilidade interna

O proprietário aprovou explicitamente retirar a lista por foto da interface habitual, mantendo pasta, referência da pasta, data/hora, quantidade de fotos e total consumido. Esta decisão substitui a expansão de detalhes descrita no checkpoint anterior, sem apagar aquela evidência histórica.

- Removidos do componente compartilhado FolderEntries, botão/estado de expansão e estilos da lista individual. Ambas as telas usam somente os resumos; compras e demais movimentos comerciais continuam individualizados.
- Consumos legados que ainda chegam sem associação comprovada de pasta não são listados por foto: há um único aviso informativo, preservando as operações internas e sem inventar vínculo de pasta. Não são tratados como histórico vazio.
- A paginação dos resumos, snapshot as_of, cancelamento de requisições e estados de erro permanecem ativos. Não houve alteração de backend, schema, regra de cobrança, ledger, permissões ou consultas internas de investigação.
- 29 testes relacionados passaram em 4 arquivos frontend (16,30 s), incluindo ambas as visões, 2.000 fotos como uma linha de pasta, nenhuma consulta de detalhes, legado sem referências individuais visíveis, troca de tenant com resposta atrasada e retry de paginação. Typecheck e ESLint direcionado passaram; build completo passou em cópia temporária sem.env.
- Conferência autenticada real: proprietário e fotógrafo exibiram quatro resumos e zero controles/referências individuais no histórico. Campos de referência da pasta, data/hora, fotos cobradas e total permaneceram visíveis.
- Consulta local somente leitura confirmou os mesmos sete UUIDs do ledger original. As três consultas internas protegidas de detalhes continuaram respondendo HTTP200 e localizaram as seis referências de operações cobradas originais. Saldo disponível6, sem alteração contábil.
- Resultado verificável fora do Git: C:/codex-data/temp/pyp-mp-external-20261101/summary-only-traceability.json. Evidência visual: journey-summary-only-owner.jpg. Build: summary-only-build.log.
- O cenário de 2.000 fotos é uma verificação funcional da apresentação, não um benchmark de 100 tenants ou 200 mil uploads.
- Produção permaneceu preservada. Não houve commit, push, migration, deploy ou exclusão de registros.

Validação final após limpeza: os 7 testes do componente passaram novamente (3,25 s), ESLint sem avisos novos; OpenSpec strict e diff--check aprovados. Tasks 6.1–6.2 concluídas.


## Revisão do texto de pagamento — task 7.1

Por solicitação do proprietário, o catálogo agora informa somente: “Pagamento protegido pelo Mercado Pago dentro da plataforma.” A explicação sobre PIX interno foi retirada da UI. Nenhuma regra, provedor ou meio de pagamento foi alterado.

Validação proporcional: 7 testes existentes da página passaram (4,02 s), ESLint direcionado passou, e a página real autenticada do fotógrafo mostrou a frase positiva com zero ocorrências da frase removida. OpenSpec strict e diff--check passaram. Não foram adicionados testes que espelhem a frase nem repetido o build para esta edição textual. Evidência visual fora do Git: C:/codex-data/temp/pyp-mp-external-20261101/payment-copy-photographer.jpg.
