# Tasks

## 1. Cards de Notificações

- [x] 1.1 Implementar cards recolhíveis preservando campos e API; validar testes focados de carga, alternância independente, rascunho, salvamento e erro. Evidência: 5 testes focados passaram; suíte frontend 345/345.
- [x] 1.2 Atualizar QA sintético para sete eventos e recolhimento; verificar teclado, responsividade e temas em navegador local quando disponível, registrando evidência ou bloqueio. Seis combinações de viewport/tema passaram; ver validation.md.

## 2. Auditoria conservadora

- [x] 2.1 Revisar frontend/backend, imports, referências, logs/debug e resíduos; registrar achados e corrigir/remover somente itens comprovados com validação focada. Achado de push corrigido e testado; nenhum código morto de produção comprovado, ver validation.md.
- [ ] 2.2 Inventariar caches descartáveis e limpar apenas caches conhecidos e verificados dentro do workspace; documentar caminhos e preservar dados/temporários incertos.

Bloqueio 2.2: inventário concluído; limpeza recusada pela revisão automática (“blocked by policy”). Caches preservados.

## 3. Integração

- [x] 3.1 Executar suítes frontend/backend isoladas, lint, typecheck, build e validação OpenSpec; investigar falhas e registrar resultados. Backend 821 passaram/13 ignorados; frontend 348 passaram; Ruff, ESLint (28 avisos anteriores), typecheck, build Next.js e OpenSpec 61/61 aprovados. Ver validation.md.
- [ ] 3.2 Validar Docker config/build sem iniciar serviços nem tocar volumes; registrar bloqueio se daemon indisponível.

Bloqueio 3.2: config passou; build não executou por daemon Docker indisponível. Nenhum serviço global iniciado.
- [x] 3.3 Revisar diff e status final, documentar arquivos desta execução e proteções. A etapa local foi concluída sem commit/push/sync/archive, conforme o pedido inicial; commit/push e PR foram autorizados posteriormente, conforme validation.md. Diff restrito aos nove arquivos listados em validation.md e aos artefatos desta change; whitespace e gitleaks aprovados. Trabalho preexistente preservado.

## 4. Relato adicional de falha no aviso de entrega

- [ ] 4.1 Investigar o relato de ausência de push/WhatsApp em order_delivery_ready; rastrear agendamento, gates, worker e validação sintética, registrar causa comprovada ou informação operacional faltante. Qualquer correção comportamental exige delta/design antes do código; não enviar mensagens reais nem alterar dados/configuração de servidor.
- [x] 4.2 Corrigir rejeição do destino de entrega no transporte push e service worker; verificar regressão falhando antes e passando depois, cifragem com HTTP falso e destinos malformados rejeitados. Backend 22 testes e frontend 11 testes focados passaram.

Bloqueio 4.1: investigação local e regressões concluídas, mas causa do WhatsApp e ausência de retorno no ambiente real ainda não comprovadas. Usuário informou ausência de mensagem após Enviar; teste integrado mantém retorno visível. Solicitados endereço do ambiente e funcionamento dos demais avisos. Diagnóstico operacional adicional depende dessa identificação e de evidência sanitizada do evento/entrega (status e last_error), sem acessar dados reais ou disparar mensagens nesta manutenção. Não marcar resolução do incidente real. Correção de push incluída na publicação autorizada posteriormente; ainda sem deploy.

## 5. Higienização conservadora do servidor solicitada posteriormente

- [x] 5.1 Inventariar disco, checkout, serviços, mounts e caches sem ler dados reais; classificar candidatos e preservar recursos compartilhados. SSH somente leitura: disco 38%, 122 GB livres, 13 serviços próprios saudáveis; ver validation.md.
- [x] 5.2 Aplicar decisão de higienização proporcional à evidência, registrar exclusões e verificar saúde/IDs finais. Nenhum resíduo exclusivo com benefício de remoção comprovado: zero arquivos apagados; cache global e camadas de imagem preservados. API ok e IDs/portas de todos os serviços inalterados após inventário.
