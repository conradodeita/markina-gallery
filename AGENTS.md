# Instruções para executores — Pick-your-Pic

## Fonte de verdade e leitura inicial

- Leia antes de qualquer alteração: `INSTRUCOES_EXECUTOR_CLAUDE_CODE.md`, `ROADMAP_ARQUITETURA.md`, `openspec/config.yaml`, as specs relevantes em `openspec/specs/` e as mudanças ativas em `openspec/changes/`.
- `openspec/specs/` descreve o comportamento consolidado. O roadmap define decisões arquiteturais, de segurança e privacidade obrigatórias; não o trate como mera sugestão.
- Preserve mudanças locais existentes e não reverta, descarte ou reformate trabalho não relacionado.
- Nunca execute `git reset --hard`, `git checkout -- .`, `git clean`, nem comando equivalente que descarte trabalho existente.
- Nunca faça force push. Commits devem conter somente alterações relacionadas à task/change atual; nunca inclua arquivos preexistentes ou não relacionados.

## Fluxo OpenSpec obrigatório

- Todo novo comportamento ou alteração de comportamento deve começar em `openspec/changes/<change-id>/`, com `proposal.md`, delta specs, `design.md` quando houver decisão técnica e `tasks.md` verificável, antes do código.
- Escreva todos os artefatos OpenSpec em português, mantendo os títulos estruturais do OpenSpec e as palavras normativas `SHALL`/`MUST` em inglês.
- Durante a implementação, mantenha tarefas, testes, documentação, decisões e desvios sincronizados com a mudança. Não deixe comportamento implementado sem spec correspondente.
- Marque uma task como concluída somente após implementação completa e validação com evidência verificável. Avance automaticamente apenas para a próxima task depois disso; avance para outra change somente quando a atual estiver reconciliada, implementada e validada por completo.
- Ao concluir, valide em proporção ao risco. Sincronize a spec principal e arquive a mudança somente após revisão humana. Se algo não puder ser executado, registre o bloqueio no artefato; nunca marque como concluído sem evidência.
- Não implemente proposals supersedidas ou conflitantes. Diante de decisão arquitetural não especificada, operação irreversível ou risco significativo de perda de dados, registre o bloqueio e não improvise. Se houver, avance somente para trabalho independente e claramente especificado.

## Convenções técnicas

- Stack: Next.js App Router + TypeScript + Tailwind; FastAPI + SQLAlchemy 2 + Alembic + Pydantic; PostgreSQL; Redis e workers; Nginx; Docker Compose.
- Use UUIDs públicos, UTC no banco e valores monetários em centavos inteiros.
- Use Conventional Commits. Fluxo de branches: `main` protegida por convenção via PR, `develop` e `feature/*`.
- Nunca exponha segredos: não os inclua no Git, frontend ou tabelas comuns. Use configuração segura do servidor.
- Nunca modifique `.env`, secrets, tokens, credenciais ou configurações equivalentes sem autorização humana explícita.
- Nunca invente requisito, feature ou comportamento fora do roadmap e do OpenSpec aplicável.

## Restrições de produto, segurança e operação

- Produto mobile-first; painel administrativo objetivo para um fotógrafo no MVP.
- Não implemente grade pública de evento coletivo, processamento/armazenamento de RAWs, prévias servidas do Google Drive ou criação automatizada de álbuns no Google Photos.
- Busca facial pode ser validada em homologação privada com dados reais de adultos e menores quando o lote for enviado pelo administrador/fotógrafo e houver autorização humana explícita por execução, origem e finalidade documentadas, acesso autenticado, proteção criptográfica, retenção mínima e exclusão controlada. Essa autorização não habilita produção nem dispensa os gates próprios do fluxo infantil fora da homologação controlada.
- Preserve privacidade: acesso de cliente por OTP, links de convite seguros e auditabilidade para ações críticas e dados biométricos.
- A máquina local e o Oracle compartilham infraestrutura com outros projetos. Não altere recursos de terceiros (containers, imagens, redes, volumes, proxy, firewall, DNS ou certificados).
- Nunca execute `docker system prune`, prunes equivalentes, nem `docker compose down` sem explicitar projeto e arquivo: `-p markina-gallery -f docker/docker-compose.yml`.
- Nunca execute migration destrutiva, operação destrutiva de banco ou deploy sem autorização humana explícita. Antes de ações autorizadas em homologação ou produção, apresente inventário, portas/subdomínio e plano de impacto zero.

## Qualidade e continuidade

### Gestão contínua de componentes externos

- Manter o inventário de dependências, serviços, imagens, runtimes, modelos e integrações com versão/constraint declarada, origem, funcionalidades consumidoras, criticidade, licença/ativação, risco de compatibilidade e evidência datada do runtime quando disponível. Tag ou nome de container não prova digest, processo carregado, inferência ou uso funcional.
- Usar Dependabot nativo para versões npm, pip, Docker/Compose e GitHub Actions em grupos e cadência revisável. Não combinar com outro bot de PRs sem decisão registrada. Atualizações normais SHALL permanecer em PR e SHALL NOT ter automerge; revisar changelog, avisos, licença, necessidade de ativação, compatibilidade, custo/arquitetura e critérios de rollback antes de merge.
- Consultar avisos de segurança na cadência nativa mais rápida disponível, separada do ciclo semanal de versões. Configuração ou permissão indisponível SHALL ser registrada como bloqueio/não confirmada, nunca como “sem vulnerabilidades”.
- Identificar faixas Python abertas, transitivos relevantes, imagens/tags/digests móveis, versões de apt, ações com tag móvel e registries/fontes externos. Relatórios SHALL incluir timestamp, fontes consultadas e distinguir lista vazia, fonte não habilitada/sem permissão e falha de consulta.
- Tratar serviços de autenticação, banco, fila, proxy, OTP, pagamento e entrega como críticos: testar contratos ponta a ponta e segurança, migração/compatibilidade e rollback antes de uma alteração que possa chegar a clientes.
- Tratar modelos/pesos de IA, busca facial, OpenCV/NumPy, LightCraft, RawTherapee e processamento de mídia como motores especializados. Atualização exige avaliação humana de licença, pesos/revisão, formatos, qualidade, precisão/calibração, recurso e reindexação; monitoramento SHALL NOT baixar pesos, ativar engines ou criar PR automático de versões especializadas.
- Separar dependências e ferramentas de desenvolvimento das imagens/runtime de produção. Priorizar updates por severidade de segurança, uso ativo, impacto de cliente, benefício, compatibilidade e manutenção upstream; a versão mais nova não é automaticamente a mais adequada.
- Workflows de monitoramento SHALL usar permissões mínimas de leitura, não acessar Oracle, segredos operacionais ou dados de cliente, e não invocar deploy, migrations, Docker ou merge. Relatório sem novidade SHALL não criar issue/PR/comentário nem enviar notificação. PRs SHALL exigir os gates/validações por categoria e revisão exigida pelo repositório.
- Uma atualização aprovada só pode ser publicada por fluxo de release autorizado. Antes de deploy, inventariar imagem/SHA/serviços/schema/porta e plano de impacto zero; manter referência da versão saudável anterior, fazer smoke/testes de contrato e rollback somente para artefatos/schemas compatíveis. Esta política não concede autorização de deploy, migration ou alteração de dados.

- Em toda implementação, inclusive fora de comandos OpenSpec, leia e aplique a [política permanente de refatoração contínua](docs/CONTINUOUS-REFACTORING.md). A avaliação é proporcional ao escopo e pode concluir que não há oportunidade segura de limpeza; as autorizações e prioridades existentes permanecem obrigatórias.
- Faça mudanças pequenas, focadas e cobertas por testes relevantes; execute testes, lint, typecheck e build aplicáveis antes de declarar conclusão.
- Documente o suficiente no OpenSpec para que outro executor consiga continuar apenas pelo repositório, sem depender de contexto de conversa.
- Não adicione ao Git bancos locais, journals, caches, artefatos de teste ou referências locais, salvo requisito explícito da task/change.

## Execução autônoma de changes OpenSpec

- Ao implementar uma change, leia `proposal.md`, `design.md` quando existir, deltas/specs relevantes e `tasks.md`. Identifique tasks concluídas, pendentes e bloqueadas antes de escolher a primeira task acionável.
- O fluxo padrão SHALL ser: implementar uma task, executar a menor validação relevante, investigar e corrigir falhas causadas pela alteração, registrar evidência, marcar a task somente quando estiver completa e validada, e seguir imediatamente para a próxima task acionável.
- Continue enquanto houver trabalho acionável. **The stopping condition is the state of the work, not the amount of work already performed.** “Progress made” is not equivalent to “work complete”. Nunca encerre apenas porque há progresso suficiente para resumir, porque uma task foi concluída, porque existe validação pendente ou porque um relatório intermediário seria útil.
- Atualizações intermediárias não encerram a execução: se disser que verificará ou implementará algo, prossiga efetivamente para essa ação enquanto houver trabalho seguro.
- **A blocker blocks the task, not the entire change.** Para cada bloqueio real: registre-o no artefato apropriado, não marque a task, procure tasks independentes e continue todas as que forem seguras e claramente especificadas. Validação visual autenticada, homologação manual, serviço externo indisponível ou credencial ausente não bloqueia trabalho local independente.
- Falha de comando, teste ou build não é condição automática de parada. Investigue logs e código, determine se a falha decorre do trabalho atual, aplique correção razoável, repita a validação focada e só escale quando a causa exigir informação, acesso ou decisão humana.
- Não interrompa para decisões técnicas triviais ou reversíveis. Decida nesta ordem: specs OpenSpec, design, proposal, padrões e arquitetura existentes, testes e convenções. Escale somente conflito material de requisitos, decisão de produto/arquitetura não especificada, credencial/OTP, autorização exigida ou ação irreversível.
- Não deixe várias tasks parcialmente implementadas. Antes de passar para outra task, conclua e valide a atual ou registre explicitamente seu bloqueio. Tasks bloqueadas podem ficar pendentes enquanto as independentes avançam.
- Prefira testes direcionados durante a implementação; execute suítes e validações amplas em checkpoints de integração e antes de concluir. Processo longo preexistente não justifica parar: não o mate arbitrariamente, evite duplicatas caras, acompanhe-o quando apropriado e continue trabalho independente.
- Só produza resposta final quando: (A) todas as tasks relevantes estiverem concluídas e validadas; (B) só restarem bloqueios reais, sem tasks independentes; (C) todo trabalho restante exigir participação humana; ou (D) continuar exigir ação proibida, destrutiva, irreversível ou deploy não autorizado.
- Sob pressão de contexto, preserve o estado em OpenSpec, testes e diff; não crie “rodadas” artificiais nem use duração da sessão como critério normal de conclusão.
- Antes de declarar pronto para commit, push ou conclusão, revise o diff relevante e preserve estritamente as proteções Git, segurança, segredos, deploy e dados definidas neste arquivo. Autonomia de implementação não remove esses controles.
