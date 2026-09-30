# Tasks

## 1. Reconciliação e matriz de isolamento

- [ ] 1.1 Reconciliar `add-tenant-ownership-foundation` com PR #115, SHA/schema e evidências de liberação/aceite, preservando pendências sem prova; verificar fontes e registrar dependências em `validation.md` antes de alterar código desta change.
- [ ] 1.2 Registrar aceite humano desta proposta e da substituição do limite de fotógrafo único no mandato/roadmap/configuração OpenSpec; verificar que documentos operacionais descrevem a transição condicionada e não declaram implantação antecipada.
- [ ] 1.3 Criar `ownership-matrix.md` com tabelas, rotas, produtores, jobs, outboxes, caches, arquivos e efeitos externos, classificados e associados a testes; verificar buscas dos gates e queries sem escopo, incluindo caminhos legados, lifecycle, exports e biometria, sem omissões ou dados reais.

## 2. Persistência e preservação do legado

- [ ] 2.1 Adicionar propriedade de cliente/telefone, índices por conta e integridade composta; testar em PostgreSQL telefone igual em A/B, duplicidade na mesma conta e relacionamento cliente/telefone incompatível.
- [ ] 2.2 Aplicar propriedade e constraints aos demais recursos identificados na matriz, incluindo configurações comerciais e registros duráveis sem origem viva; testar inserts incompatíveis e documentar cada classificação concluída na matriz.
- [ ] 2.3 Implementar migration expansiva com inventário/aborto em ambiguidade; ensaiar base vazia, legado válido e inconsistente em PostgreSQL descartável, comparando UUIDs, relações, valores, snapshots, configurações e storage keys e demonstrando rollback transacional da falha.
- [ ] 2.4 Atualizar seed e ferramenta offline de provisionamento com dry-run, idempotência, recusa de alvo ambíguo e proteção de credenciais existentes; testar somente recursos sintéticos e documentar invocação sem segredo em logs ou Git.

## 3. Identidade autenticação e sessão

- [ ] 3.1 Tornar identidade, diretório, busca e troca de telefone explícitos por conta; testar nomes distintos com mesmo telefone, edição independente, duplicidade local e respostas sem enumeração entre contas; atualizar documentação do cadastro.
- [ ] 3.2 Resolver contexto de cliente pelo link autorizado e vincular desafio/reenvio/OTP/sessão à conta, preservando rate limit e respostas neutras; testar OTP trocado entre A/B, telefone repetido, link inválido e sessão legada ambígua sem envio externo real.
- [ ] 3.3 Substituir contexto administrativo único por vínculo inequívoco revalidado; testar senha/TOTP, vínculo ausente/revogado/ambíguo, conta suspensa e tentativa de impor conta por parâmetro, sem autorização por frontend.
- [ ] 3.4 Atualizar entrada e navegação cliente para contexto do link, biblioteca restrita e orientação sem contexto; testar acesso por links de A/B em contextos independentes, teclado e viewport móvel, documentando a autenticação separada.

## 4. Domínio comércio e configurações

- [ ] 4.1 Restringir galerias/pastas/fotos/uploads/importações e acesso direto à mídia ao proprietário, preservando públicos por pasta; testar listagem, edição, upload, variantes, URLs e inserts cruzados em API e PostgreSQL.
- [ ] 4.2 Restringir seleções/interações/carrinhos/pedidos/pagamentos/entregas/histórico; testar carrinho misto recusado, checkout com PIX de A/B e estados independentes da mesma pessoa nas duas contas, sem transação financeira real.
- [ ] 4.3 Tornar PIX/branding/templates/preferências/presets editáveis/processamento próprios da conta; testar segunda conta vazia, manutenção das configurações legadas, mudanças sem afetar B e desafio PIX com proprietário incompatível; documentar configuração por fotógrafo.
- [ ] 4.4 Restringir estatísticas, exports, recibos e operações de lifecycle; testar exclusão sintética autorizada de A preservando B e histórico protegido, além de recusa de cleanup integral em instalação multitenant; atualizar contratos de manutenção.

## 5. Execução assíncrona e efeitos externos

- [ ] 5.1 Contextualizar mídia e ajuste de prévias em jobs/retries/caches/arquivos; testar mesma sequência nas duas contas, suspensão antes da publicação e progresso de B preservado; fechar respectivas linhas da matriz.
- [ ] 5.2 Contextualizar notificações/outboxes/transportes/deduplicação e associação segura de canais; testar destinatários e templates isolados, canal ausente recusado, retries e suspensão antes do envio com adaptadores sintéticos; documentar vínculo externo sem provisioná-lo remotamente.
- [ ] 5.3 Contextualizar lifecycle/retenção/cleanup e rotas/jobs/artefatos faciais inventariados; testar fixtures sintéticas negativas sem biometria real, preservar criptografia e registrar bloqueio específico se depender de change própria; não habilitar fluxo não validado.

## 6. Dono da instalação e monitor

- [ ] 6.1 Implementar permissão explícita e revogável do operador, provisionamento offline sem concessão automática e revalidação antes de coleta/cache; testar dono autorizado, fotógrafo comum, cliente e revogação com cache, comprovando ausência de privilégio comercial cruzado.
- [ ] 6.2 Mostrar painel/cópia somente com capacidade autorizada e manter snapshot sanitizado agregado; testar omissão para fotógrafo comum, remoção após 403, cópia fiel após atualização e compatibilidade `capacity-report/v1`; atualizar guia do dono.

## 7. Piloto local e integração

- [ ] 7.1 Criar fixtures e executor reproduzível de 2 fotógrafos × 3 clientes, até 12 JPEGs sintéticos sem pessoas, telefone repetido e adaptadores sem envio; verificar provisionamento idempotente e isolamento dos recursos locais e preencher `pilot-plan.md` com comandos validados.
- [ ] 7.2 Executar jornadas e negativas do roteiro local, concorrência máxima de seis clientes e leituras antes/durante/depois pelo monitor; registrar UTC/cache/valores/lacunas e conclusão de jobs em `pilot-results.md`, recusando liberação em qualquer acesso cruzado.
- [ ] 7.3 Executar lint/testes backend, regressões PostgreSQL/migrations, testes/lint/typecheck/build frontend e OpenSpec estrito; investigar falhas relacionadas e registrar evidências, matriz completa e revisão do diff/segredos em `validation.md`.

## 8. Homologação e fechamento

- [ ] 8.1 Preparar pacote com SHA/schema, inventário do destino, backup verificável, janela, portas/subdomínio, escritores próprios e reversão compatível; obter autorização operacional explícita antes de qualquer merge/push que acione deploy e registrar o aceite do pacote.
- [ ] 8.2 Executar somente a publicação autorizada e validar healthchecks/legado/serviços vizinhos; registrar SHA/schema/UTC e autorização explícita para contas, dados, operador e canais do piloto antes do provisionamento remoto.
- [ ] 8.3 Executar ensaio pequeno em homologação e analisar os relatórios reais do monitor; verificar o caso do mesmo telefone, negativas cruzadas, jornada OTP e resultados assíncronos; registrar limitações/bloqueios reais sem concluir etapa com bypass ou evidência local substitutiva.
- [ ] 8.4 Entregar resultado ao dono e obter revisão humana; sincronizar somente requisitos implementados/validados e arquivar depois do aceite, verificando validação OpenSpec final e preservando tarefas bloqueadas.

## Execution Notes

Estado: planejamento local, sem implementação, provisionamento ou deploy. Todas as tarefas permanecem pendentes. Decisão confirmada: cadastro independente por fotógrafo para o mesmo telefone. O tamanho e as demais decisões do piloto estão propostos para revisão.

Dependências: reconciliação documental da fundação; aceite desta proposta; gates de operação/canais e eventual biometria. Bloqueios remotos não impedem as tarefas locais independentes após aprovação da implementação. Nenhum fotógrafo adicional será ativado antes de completar a matriz e os testes de isolamento.
