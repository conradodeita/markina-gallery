# Tasks

## 1. Baseline e preparação

- [x] 1.1 Registrar em `validation.md` o SHA/branch, arquivos preexistentes modificados, produtores das três entidades e pontos de autorização/efeitos externos; verificar o inventário com buscas de construtores e inserts, sem incluir dados pessoais ou segredos.
- [x] 1.2 Determinar o head Alembic e a fonte de código escolhida para implementação, registrar a diferença 0061/0068 e a cadeia utilizada; verificar que a nova revision tem ancestral confirmado, preservando alterações locais e sem carimbar banco remoto.

## 2. Modelo e preservação do legado

- [x] 2.1 Implementar `Tenant`, `TenantAdmin` e propriedade obrigatória/constraints das três entidades; verificar em PostgreSQL sintético que proprietário ausente, origem de outra conta e foto privada incompatível falham, e que relações válidas persistem.
- [x] 2.2 Implementar migration transacional e conferência do legado; verificar upgrade de banco vazio e base sintética válida, igualdade de UUIDs/vínculos/valores/storage keys antes/depois e rollback integral do upgrade com órfão ou relação incompatível; registrar comandos, resultados e duração em `validation.md`.
- [x] 2.3 Atualizar seed e fixtures sem sobrescrever credenciais; verificar criação transacional do vínculo no banco vazio, idempotência do seed válido e recusa de reparo silencioso de administrador sem vínculo.
- [x] 2.4 Classificar as novas tabelas como preservadas na limpeza existente de homologação; verificar por teste sintético que conta, vínculo, credenciais/sessão administrativa e configuração do canal sobrevivem à remoção do acervo, sem executar limpeza remota.

## 3. Contexto administrativo e gate da instalação

- [x] 3.1 Implementar resolvedor central da conta única e vínculo administrativo revalidado; verificar sessão anterior à migration, login senha/TOTP, vínculo revogado/ausente e tentativa de impor outro tenant pela requisição, registrando a evidência.
- [x] 3.2 Aplicar gate às operações de domínio e workers antes de publicação/efeitos externos; verificar ausência, suspensão e segunda conta sintética, inclusive mudança durante job, com zero envio real e preservação de jobs/leases sem resultados indevidos; documentar os pontos cobertos.

## 4. Produtores de galerias e fotos

- [x] 4.1 Atualizar criação/edição administrativa de origens para usar contexto autorizado; verificar fluxo existente e rejeição de proprietário incompatível sem mudança de UUIDs ou arquivos.
- [x] 4.2 Atualizar criação de galerias privadas, clonagem e vínculos derivados para herdar a propriedade da origem; verificar fluxos individuais/compartilhados com os testes existentes e novos casos de consistência.
- [x] 4.3 Atualizar upload/importação e criação assíncrona de fotos para herdar propriedade persistida; verificar produtores inventariados, retries e inserts em lote, sem fallback/default global, registrando correspondência entre cada produtor e seu teste.

## 5. Integração e pacote de liberação

- [x] 5.0 Garantir no script de deploy a interrupção e conferência dos escritores exclusivos antes do Alembic, sem parar Evolution ou vizinhos; validar com subprocessos simulados ordem, falha de parada e bloqueio de migration/rollback incompatível.
- [x] 5.1 Executar validação integrada proporcional ao risco: lint e testes backend, regressões de OTP/galerias/prévias/checkout/lifecycle e migration PostgreSQL; executar lint/testes/typecheck/build frontend aplicáveis e validação OpenSpec estrita; registrar resultados reais e investigar falhas relacionadas antes de marcar concluído.
- [x] 5.2 Revisar diff/hunks, preparar versão exata e preencher o registro de entrega local em `delivery-plan.md` com links de evidência; verificar preservação do trabalho preexistente e que nenhum segredo, ambiente ou artefato local de teste entra no pacote.

## 6. Homologação e entrega ao proprietário

- [x] 6.1 Fazer inventário somente-leitura atualizado do destino, confirmar SHA/schema e reconciliar migrations; verificar documentalmente que a cadeia de release contém a revisão real do banco e que os serviços/volumes/portas pertencem ao projeto.
- [ ] 6.2 Apresentar e registrar aprovação explícita da release, janela medida, backup, portas/subdomínio, impacto zero nos demais projetos e reversão compatível; verificar que a autorização identifica destino/escopo antes de qualquer publicação, inclusive merge/push que acione deploy automático.
- [ ] 6.3 Executar somente o deploy autorizado e seus testes de aceite; verificar propriedade/contagens, login/OTP, galeria/upload/prévias/checkout com dados permitidos e ausência de impacto em serviços vizinhos; registrar SHA, schema, horário e evidências, sem declarar sucesso se houver pendência.
- [ ] 6.4 Entregar relatório pós-deploy em linguagem simples com os quatro pontos do contrato; verificar que a entrega efetiva e a orientação de teste correspondem à versão publicada e que a restrição a um fotógrafo está explícita.
- [ ] 6.5 Após revisão humana do resultado, sincronizar a spec principal e arquivar a change; verificar aprovação registrada e validação OpenSpec, mantendo pendentes tasks sem evidência.

## Execution Notes

Estado atual: implementação e validação local/CI concluídas para a release `b4c320e75cbe0d786d8b05d62d57b77aa796a2ec`, PR #115 em rascunho. Backend 890 passed/19 skips condicionais, frontend 352 passed, lint/build/OpenSpec/segredos aprovados. Nenhuma publicação ou limpeza remota executada. Restam somente aprovação operacional, execução/aceite remoto e revisão humana para sincronização/arquivo (6.2–6.5). Ver `validation.md` e `release-runbook.md`.

Durante a aplicação, executar uma task e sua validação por vez, registrar evidência e seguir para a próxima acionável. Bloqueios são documentados por task; aprovação deste plano não aprova outras etapas P0/P1/P2 nem deploy. Não sincronizar/arquivar antecipadamente.
