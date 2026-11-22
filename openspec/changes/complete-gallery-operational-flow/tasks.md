## 1. Contratos, integridade e migration

- [x] 1.1 Inventariar os contratos atuais de foto, prévia, pasta, resumo e cliente, e adicionar testes inicialmente falhos para capa, exclusão, busca e vínculos idempotentes; verificar que os testes cobrem escopo de galeria-mãe e compra confirmada.
- [x] 1.2 Adicionar o metadado opcional de capa da galeria-mãe e uma migration reversível que aceite somente foto da mesma origem; verificar upgrade e downgrade em SQLite e PostgreSQL efêmero sem dados reais.
- [x] 1.3 Implementar contratos autenticados para resumo completo da galeria, escolha/limpeza de capa e listagem ordenada de clientes; verificar ausência de originais, chaves de armazenamento e dados fora do escopo administrativo.
- [x] 1.4 Implementar exclusão contextual de foto sem compra confirmada, com limpeza idempotente de referências e mídia; verificar recusa de foto comprada, foto de outra pasta e foto de outra galeria.
- [x] 1.5 Ajustar contratos de busca e vínculo de clientes para ordem alfabética, filtro por nome/WhatsApp e reutilização de galeria derivada da mesma origem; verificar que a busca não cria dados e que o vínculo não duplica histórico.

## 2. Experiência administrativa de imagens e capa

- [x] 2.1 Completar a etapa Imagens com cartões de pasta, contagem, capa/preview padrão e estados de processamento retornados pelo backend; verificar duas pastas com fotos somente em uma delas.
- [x] 2.2 Implementar grade de prévias administrativas com marca d’água e modal acessível de ampliação; verificar teclado, fechamento, viewport móvel e ausência de URL do original.
- [x] 2.3 Implementar comandos de exclusão de foto e escolha/troca de capa com confirmação e mensagens de bloqueio do backend; verificar que foto comprada não oferece remoção efetiva e que apagar capa recompõe o fallback.
- [x] 2.4 Manter retorno e avanço entre as cinco etapas sem efeitos colaterais de navegação; verificar recarga, foco, etapa atual e ausência de criação duplicada.

## 3. Clientes, resumo e compartilhamento

- [x] 3.1 Completar a etapa Clientes com lista alfabética, busca por nome/WhatsApp, estado vazio e cadastro contextual; verificar que o resultado e as permissões vêm exclusivamente do backend.
- [x] 3.2 Implementar vínculo de cliente existente e criação/vínculo de nova cliente para a galeria atual; verificar que clientes e galerias privadas de outras origens não são misturados.
- [x] 3.3 Implementar resumo da galeria-mãe com capa protegida, contagens, status, responsáveis vinculados e link não listado copiável; verificar atualização após criar pasta, enviar foto, escolher capa e vincular cliente.
- [x] 3.4 Exibir comandos textuais de edição e exclusão de galeria no resumo administrativo; permitir excluir somente galeria do evento sem pastas, fotos ou responsáveis, com confirmação e motivo retornado pelo backend.

## 4. Validação, documentação e homologação contínua

- [x] 4.1 Criar testes backend para fluxo sintético completo: criar galeria, duas pastas, enviar JPEG, processar prévia, escolher capa, excluir foto elegível, buscar/vincular cliente e obter resumo; verificar que WhatsApp, biometria e venda não são acionados.
- [x] 4.2 Criar testes frontend para pasta, ampliação, exclusão, capa, busca, vínculo, navegação e estados de erro; verificar que não há autorização ou persistência simulada no browser.
- [x] 4.3 Executar ruff, testes backend, lint, testes e build frontend; registrar resultados e manter falhas abertas até correção.
- [x] 4.4 Revisar visualmente em desktop e smartphone com dados sintéticos, seguindo as diretrizes próprias da Markina; verificar legibilidade, hierarquia, modal, confirmações e estados vazios. Evidência em 12/11/2026: sessão sintética em `3044`; configurações, vendas, comentário abaixo do preço, favorito, confirmação financeira, editor de galeria e pastas vazias revisados em 1366×900 e 390×844; prévia ampliada centralizada e Escape fecha o modal; pasta sintética vazia foi excluída após a correção e a UI confirmou sucesso. Observação não bloqueante: em 390 px, a exportação financeira quebra em três linhas e a barra fixa de filtros consome altura relevante; registrada para refinamento visual futuro.
- [x] 4.5 Atualizar o roteiro de homologação e fazer push/deploy automático somente após a suíte verde, usando backup e Compose estritamente limitados ao Markina; verificar saúde, migration e URLs do ambiente.

## Registro de bloqueio — 2026-08-28

- A revisão visual 4.4 permanece pendente. Os testes de componente e a interface local existem, mas a validação completa requer sessão administrativa autenticada com dados sintéticos em navegador. A inserção de senha e OTP, mesmo sintéticos, exige confirmação imediata no ambiente de revisão visual; não foi realizada nesta execução autônoma. Nenhuma conclusão visual foi inferida a partir dos testes automatizados.

## Registro de supersession — 2026-08-31

- A task 4.4 continua sendo revisão visual humana da entrega histórica. Regras de exclusão, vínculo e derivação desta change não devem ser reaplicadas: `improve-gallery-and-client-data-lifecycle` é a autoridade para o novo ciclo de vida e pode avançar em trabalho local independente.

## Revalidação local — 12/11/2026

- A tentativa autônoma de inspeção visual em `http://127.0.0.1:3039/`, `/admin` e `/library/cart` recebeu HTTP 500 (`Internal Server Error`). A API local respondeu HTTP 200 em `/health`. Os processos web/API já estavam ativos; não foram reiniciados ou alterados. Nenhuma sessão, credencial, OTP ou dado de cliente foi usado. Evidência e limites em `validation.md`; task 4.4 continua aberta.

## Fechamento da revisão visual — 12/11/2026

- A limitação acima foi contornada sem tocar no processo 3039: sessão administrativa sintética autenticada em `3044`, com API e dados sintéticos isolados. A sessão revisou configurações e vendas em desktop e smartphone; o detalhe do pedido mostrou comentário abaixo do preço, favorito na prévia e a situação financeira coerente.
- No editor da galeria, a prévia ampliada foi aberta e inspecionada em 390×844; Escape a fechou e removeu o modal da árvore de acessibilidade. Pastas vazias e a confirmação/resultado da exclusão da pasta sintética foram verificados após a correção de FK.
- Em 390 px, o botão “CSV financeiro detalhado” quebra em três linhas e a barra fixa de filtros ocupa espaço vertical considerável. Continua legível e não há overflow global; o refinamento visual fica registrado para trabalho futuro, sem bloquear o escopo de revisão.
- Este registro posterior substitui os estados “pendente” das tentativas anteriores: a task 4.4 foi concluída localmente; nenhuma sincronização de spec, arquivamento, deploy, migration ou acesso à produção ocorreu.
