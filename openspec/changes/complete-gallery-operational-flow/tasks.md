## 1. Contratos, integridade e migration

- [ ] 1.1 Inventariar os contratos atuais de foto, prévia, pasta, resumo e cliente, e adicionar testes inicialmente falhos para capa, exclusão, busca e vínculos idempotentes; verificar que os testes cobrem escopo de galeria-mãe e compra confirmada.
- [ ] 1.2 Adicionar o metadado opcional de capa da galeria-mãe e uma migration reversível que aceite somente foto da mesma origem; verificar upgrade e downgrade em SQLite e PostgreSQL efêmero sem dados reais.
- [ ] 1.3 Implementar contratos autenticados para resumo completo da galeria, escolha/limpeza de capa e listagem ordenada de clientes; verificar ausência de originais, chaves de armazenamento e dados fora do escopo administrativo.
- [x] 1.4 Implementar exclusão contextual de foto sem compra confirmada, com limpeza idempotente de referências e mídia; verificar recusa de foto comprada, foto de outra pasta e foto de outra galeria.
- [x] 1.5 Ajustar contratos de busca e vínculo de clientes para ordem alfabética, filtro por nome/WhatsApp e reutilização de galeria derivada da mesma origem; verificar que a busca não cria dados e que o vínculo não duplica histórico.

## 2. Experiência administrativa de imagens e capa

- [x] 2.1 Completar a etapa Imagens com cartões de pasta, contagem, capa/preview padrão e estados de processamento retornados pelo backend; verificar duas pastas com fotos somente em uma delas.
- [x] 2.2 Implementar grade de prévias administrativas com marca d’água e modal acessível de ampliação; verificar teclado, fechamento, viewport móvel e ausência de URL do original.
- [x] 2.3 Implementar comandos de exclusão de foto e escolha/troca de capa com confirmação e mensagens de bloqueio do backend; verificar que foto comprada não oferece remoção efetiva e que apagar capa recompõe o fallback.
- [ ] 2.4 Manter retorno e avanço entre as cinco etapas sem efeitos colaterais de navegação; verificar recarga, foco, etapa atual e ausência de criação duplicada.

## 3. Clientes, resumo e compartilhamento

- [x] 3.1 Completar a etapa Clientes com lista alfabética, busca por nome/WhatsApp, estado vazio e cadastro contextual; verificar que o resultado e as permissões vêm exclusivamente do backend.
- [x] 3.2 Implementar vínculo de cliente existente e criação/vínculo de nova cliente para a galeria atual; verificar que clientes e galerias privadas de outras origens não são misturados.
- [x] 3.3 Implementar resumo da galeria-mãe com capa protegida, contagens, status, responsáveis vinculados e link não listado copiável; verificar atualização após criar pasta, enviar foto, escolher capa e vincular cliente.

## 4. Validação, documentação e homologação contínua

- [ ] 4.1 Criar testes backend para fluxo sintético completo: criar galeria, duas pastas, enviar JPEG, processar prévia, escolher capa, excluir foto elegível, buscar/vincular cliente e obter resumo; verificar que WhatsApp, biometria e venda não são acionados.
- [ ] 4.2 Criar testes frontend para pasta, ampliação, exclusão, capa, busca, vínculo, navegação e estados de erro; verificar que não há autorização ou persistência simulada no browser.
- [ ] 4.3 Executar ruff, testes backend, lint, testes e build frontend; registrar resultados e manter falhas abertas até correção.
- [ ] 4.4 Revisar visualmente em desktop e smartphone com dados sintéticos, seguindo as diretrizes próprias da Markina; verificar legibilidade, hierarquia, modal, confirmações e estados vazios.
- [ ] 4.5 Atualizar o roteiro de homologação e fazer push/deploy automático somente após a suíte verde, usando backup e Compose estritamente limitados ao Markina; verificar saúde, migration e URLs do ambiente.
