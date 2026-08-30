## 1. Persistência e contratos de entrega

- [x] 1.1 Criar migration aditiva e modelos para configuração não secreta do canal, outbox WhatsApp genérica, tentativas e recibos de webhook, preservando a outbox/histórico de pagamento; verificar upgrade do zero, upgrade sobre o head atual, downgrade reversível de homologação e constraints de idempotência/estado.
- [x] 1.2 Implementar payload efêmero de OTP com cifra autenticada e chave exclusiva do ambiente, limpeza após aceitação/expiração e ausência de texto puro em banco/logs; verificar round-trip, adulteração, chave ausente/incorreta e descarte por TTL com testes.
- [x] 1.3 Definir estados e transições monotônicas de `queued` até `read`, `failed`, `unknown` ou `expired`; verificar concorrência, evento atrasado, duplicata e impossibilidade de regredir um estado terminal com testes de banco.

## 2. Provider Evolution e confiabilidade

- [x] 2.1 Evoluir a porta `WhatsAppProvider` para resultados tipados de envio, identidade, conexão, pareamento e reconciliação, mantendo sandbox/fakes sem efeitos externos; verificar compatibilidade dos fluxos existentes e testes unitários sem rede.
- [x] 2.2 Adaptar envio de texto à resposta real da Evolution API 2.3.7, validando corpo, identificador, destinatário e erro sanitizado; verificar 2xx válido, 2xx incompleto, destinatário divergente, 4xx, 429, 5xx, EOF e timeout ambíguo com servidor HTTP falso.
- [x] 2.3 Implementar criação/consulta/conexão da instância Baileys dedicada, identidade remetente e material efêmero de QR/pairing sem expor API key; verificar estados aberto/conectando/fechado, número coincidente/divergente e expiração do pareamento com fake Evolution.
- [x] 2.4 Implementar reconciliação de tentativas `unknown` sem retry cego e limites de reenvio manual/automático; verificar mensagem possivelmente aceita, falha inequivocamente anterior à aceitação e prevenção de duplicata.
- [x] 2.5 Implementar webhook interno mínimo para conexão e entrega, com header secreto, comparação constante, limite de corpo, deduplicação e transição monotônica; verificar evento válido, repetido, fora de ordem, não autenticado, excessivo e conteúdo recebido fora de escopo.

## 3. Integração dos fluxos existentes

- [x] 3.1 Migrar solicitação e reenvio de OTP para a outbox prioritária, preservando resposta neutra, rate limit, desafio de uso único e expiração; verificar que o endpoint não depende da rede, que códigos expirados não saem e que nenhuma resposta/log revela OTP ou existência de cliente.
- [x] 3.2 Migrar notificações de pagamento já especificadas para a outbox genérica, preservando destinatários verificados, templates, decisão financeira, idempotência, reenfileiramento e histórico; verificar os cenários atuais e uma migration com registros preexistentes.
- [x] 3.3 Atualizar o worker para prioridade de OTP, validade, backoff, estados de entrega e retomada segura após reinício; verificar concorrência entre workers, crash durante processamento e ausência de mensagem duplicada.
- [x] 3.4 Expor diagnóstico sanitizado de falhas e desconexão na operação administrativa existente sem retornar telefone completo, corpo, chave ou sessão; verificar autorização e payloads de erro com testes de API.

## 4. Configuração administrativa do WhatsApp

- [x] 4.1 Implementar endpoints administrativos para consultar estado mascarado, salvar número esperado, iniciar pareamento e atualizar prontidão, exigindo sessão de fotógrafo e auditoria; verificar acesso negado para cliente/anônimo, E.164 inválido, divergência e ausência de segredos nas respostas.
- [x] 4.2 Adicionar em `Configurações → WhatsApp` um painel responsivo com provedor/ambiente, número esperado e conectado mascarados, estado, última verificação, pendências e fluxo de QR/pairing; verificar acessibilidade, estados de carga/erro/expiração e testes de componente após consultar a documentação local do Next.js exigida por `frontend/AGENTS.md`.
- [x] 4.3 Bloquear visualmente a promessa de canal pronto enquanto conexão e identidade não coincidirem e explicar que o número precisa ser pareado; verificar os estados sandbox, pendente, conectando, pronto, divergente e desconectado em desktop e smartphone.

## 5. Infraestrutura e operação isoladas

- [x] 5.1 Verificar no registry a imagem oficial Evolution API 2.3.7, registrar tag e digest, e adicionar `evolution-api`, `evolution-db` e `evolution-redis` ao Compose com imagens fixadas, volumes exclusivos, limites, healthchecks, rede interna e nenhuma porta pública; verificar `docker compose config`, inventário de portas/redes/volumes e testes da automação sem iniciar efeitos externos.
- [x] 5.2 Configurar somente por variáveis seguras e separadas por ambiente a API key, bancos, cache, instância, webhook e chave de payload OTP; atualizar `.env.example` apenas com nomes/fallbacks inertes e verificar que gitleaks não encontra credenciais.
- [x] 5.3 Criar runbook de bootstrap, pareamento, reconexão, backup, restauração, rotação, atualização fixada, rollback para sandbox e resposta a comprometimento; verificar que não exige exposição pública nem comandos destrutivos e que distingue tarefas do executor e ações humanas.
- [x] 5.4 Cobrir persistência e recuperação local da instância com dados sintéticos, incluindo reinício de Evolution/API/worker, preservação da outbox e bloqueio quando a sessão não volta; registrar evidência sem telefone, QR, chave ou conteúdo de mensagem.

## 6. Qualidade, deploy autorizado e homologação real

- [x] 6.1 Executar lint, testes backend/frontend, typecheck, build, migrations, Compose, gitleaks e validação OpenSpec estrita; corrigir regressões e registrar comandos/resultados verificáveis.
  - Evidência em 2026-08-30: `python -m pytest tests -q` — 106 aprovados, 1 ignorado; `python -m ruff check .` — aprovado.
  - Evidência em 2026-08-30: `npm test -- --maxWorkers=1` — 57 aprovados; `npx tsc --noEmit` e `npm run build` — aprovados; `npm run lint` — 0 erros e 16 avisos preexistentes fora desta change.
  - Evidência em 2026-08-30: migration testada em upgrade/downgrade e banco sintético levado ao head `20260830_0016`; Compose base e perfil `whatsapp-real` validados com `config --quiet`; testes shell/policy do deploy aprovados.
  - Evidência em 2026-08-30: gitleaks sem achados no histórico de 106 commits, no diff e nos arquivos novos; `openspec validate --all --strict` — 22 itens aprovados.
- [x] 6.2 Apresentar antes do deploy o inventário Markina, consumo estimado, serviços/volumes novos, confirmação de nenhuma porta pública e plano de impacto zero/rollback; aguardar autorização humana explícita sem bloquear correções locais independentes.
  - Evidência em 2026-08-30: inventário apresentado e deploy explicitamente autorizado pelo proprietário; a autorização não inclui pareamento, exclusão de volumes ou alteração de recursos externos ao projeto Markina.
- [ ] 6.3 Após autorização, publicar pelo fluxo protegido, confirmar SHA, migrations, healthchecks e que o canal permanece sem efeitos externos até o pareamento; não marcar concluída sem evidência do deployment.
- [ ] 6.4 Solicitar ao proprietário o número próprio de homologação e a leitura de QR ou uso do pairing code somente depois da infraestrutura pronta; confirmar conexão, identidade coincidente e recuperação após reinício sem registrar material sensível.
- [ ] 6.5 Validar em homologação com dados sintéticos o recebimento real de OTP, login do cliente e todas as mensagens transacionais já implementadas nas direções sistema→cliente e sistema→fotógrafo; verificar IDs/estados, ausência de duplicata em falha simulada e limites de autorização.
- [ ] 6.6 Concluir a revisão visual autenticada pendente das changes de galeria em desktop e smartphone depois do OTP real, sem marcar as tasks correlatas antes do aceite humano.
