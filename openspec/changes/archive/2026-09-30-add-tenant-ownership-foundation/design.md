# Design

## Context

Ver [proposal.md](proposal.md). Os modelos atuais concentram-se em `backend/app/auth.py`; `AdminUser` e `AuthSession` são persistidos. `ParentGallery`, `DerivedGallery` e `PhotoAsset` não possuem proprietário fotógrafo. FKs compostas já protegem algumas relações de pasta/galeria; os clientes, PIX, branding e notificações continuam globais.

O checkout original tinha head 0061 e alterações locais de outras changes preservadas. A implementação usa worktree isolado baseado em `origin/develop`, SHA `04c6bb98cdbb7607026cd54106d9e4cdf43d1e29`; leitura SSH confirmou esse mesmo SHA no destino e schema `20260928_0068`. A revision `20260929_0069` deriva de 0068. Inventário e evidências em [validation.md](validation.md); revalidar antes de publicar.

## Goals / Non-Goals

**Goals:** introduzir um proprietário estável para as três entidades, impedir combinações incompatíveis na persistência, resolver o vínculo administrativo no servidor e ensaiar preservação do legado em PostgreSQL.

**Non-Goals:** este recorte é uma subetapa de P0.1, não o aceite completo de P0.1 nem B01. Clientes/configurações/jobs globais tornam insegura a operação com uma segunda conta; o gate de conta única é parte obrigatória desta entrega. Não alterar storage keys, arquivos, ciphertext, AAD, retenção ou formato das sessões.

## Decisions

### 1. Conta persistida, vínculo explícito e gate de conta única

Criar `Tenant` com UUID, status `active`/`suspended` e criação UTC; `TenantAdmin` com FKs para tenant/admin, vínculo único por par e flag de atividade. A migration cria a conta legada com UUID gerado uma vez e vincula todos os administradores existentes, pois o acervo atual é único. Não duplicar acervos por administrador nem usar e-mail como chave de propriedade.

O resolvedor central verifica exatamente uma conta total na instalação e seu status ativo. Operações protegidas e workers de domínio usam esse gate; a ausência ou multiplicidade bloqueia o domínio, não seleciona a primeira linha. Workers revalidam antes de efeitos externos e publicação. Nenhuma rota de provisionamento de tenant ou papel de suporte é criada. Esse controle é uma proteção transitória verificável, não autorização multitenant.

Alternativas: usar somente `admin_user_id` nas fotos confundiria identidade de login com conta comercial; liberar múltiplas contas agora deixaria dados/configurações globais sem isolamento.

### 2. Propriedade explícita nas raízes e integridade no banco

Adicionar `tenant_id` obrigatório com FK a `Tenant` nas três entidades. Garantir unicidade de `(id, tenant_id)` na origem e de `(id, parent_gallery_id, tenant_id)` na galeria privada. FKs compostas fazem a galeria privada e a foto apontarem para uma origem com o mesmo tenant; a foto privada também referencia a tupla correspondente da galeria privada. Manter as FKs e invariantes existentes de pasta, origem e membership.

Toda criação de origem recebe tenant do contexto administrativo. Toda criação de galeria privada/foto, inclusive importação, clonagem e processamento posterior, deriva tenant da origem carregada do banco. Inventariar todos os construtores e inserts em lote; nenhum default implícito de banco ou fallback global atribui tenant a novas linhas. Pastas e demais filhos continuam com propriedade alcançável pela origem; não adicionar colunas indiscriminadamente nesta etapa.

Alternativa: apenas filtros no ORM não impediriam inserção incoerente por worker ou rotina administrativa. Testes sintéticos com duas contas exercitam constraints em banco isolado, sem habilitar essas contas na aplicação.

### 3. Autorização compatível com a sessão atual

Preservar cookie opaco, hash, papel, expiração e revogação. Para operações administrativas, resolver `subject_id` para `AdminUser`, exigir `TenantAdmin` ativo e conta única ativa. A revalidação é por operação, inclusive para sessões anteriores à migration. Identificador de tenant externo nunca substitui esse contexto. Recuperação de conta, TOTP e OTP não são redesenhados.

O seed em banco vazio adiciona o vínculo junto com o administrador na mesma transação. Se o seed encontrar administrador existente sem vínculo, não o reparar silenciosamente: a migration/inventário deve resolver essa inconsistência. Não sobrescrever credenciais nem alterar arquivos de ambiente.

### 4. Migration expansiva com ensaio e barreira a binários antigos

Criar tabelas e colunas inicialmente nullable; conferir órfãos e relações; preencher tudo com o UUID único; conferir contagens e relações; tornar obrigatório e adicionar constraints/índices. O upgrade transacional falha integralmente diante de inconsistência. Não alterar valores comerciais, UUIDs existentes ou storage keys. A revisão nova deriva do head reconciliado, sem fixar antecipadamente número 0062 ou 0069.

As colunas obrigatórias sem default tornam os binários antigos incompatíveis com novas escritas. Portanto, o plano de liberação deve interromper apenas os escritores do Pick-your-Pic durante a janela controlada (API/worker/classes identificadas), drenar ou preservar jobs duráveis e aplicar banco+binários compatíveis antes de reabrir. Zero impacto refere-se aos projetos vizinhos; não prometer indisponibilidade zero deste produto. Medir a duração do ensaio antes de estimar a janela.

Reversão preferencial: versão corretiva compatível com o novo schema, mantendo dados. Retorno ao binário anterior somente depois de demonstrar compatibilidade em cópia descartável; restauração/downgrade não é automática e requer autorização própria. Registrar isso em vez de prometer rollback que falhará por `NOT NULL`.

### 5. Registro da entrega sem segredo ou dado pessoal

Usar [delivery-plan.md](delivery-plan.md) como contrato e modelo. Um registro por liberação vincula change, ambiente, UTC, SHA/revisões, evidências e resultado. A explicação para o proprietário começa com a entrega funcional e distingue preparação, implementação local, publicação e validação. Logs de OTP, fotos, biometria, credenciais e dados pessoais não entram no registro versionado.

### 6. Compatibilidade com limpeza de homologação

O proprietário autorizou o descarte dos dados atuais de negócio do servidor, preservando admin, acesso e Evolution conectada. A lista fechada de `homolog_cleanup` precisa classificar `tenant` e `tenant_admin` como preservadas; sem essa classificação, o procedimento deve continuar recusando schema desconhecido. Usar a limpeza existente, sem ampliar sua lista de recursos apagados. O ensaio usa dados sintéticos; a operação remota exige apresentação prévia do inventário e preserva credenciais, sessões administrativas, configurações e volumes Evolution e proxy/HTTPS. Esta tarefa de compatibilidade foi acrescentada por necessidade das novas tabelas e pela orientação explícita do proprietário.

## Risks / Trade-offs

- [Schema remoto possivelmente mais recente] → Reconciliação obrigatória; nunca usar `stamp`, downgrade ou renumerar histórico para forçar deploy.
- [Ponto de criação não atualizado] → Inventário de inserts, teste dos produtores síncronos/assíncronos e ausência de default de tenant nas colunas.
- [Migration/locks em acervo existente] → Ensaio PostgreSQL representativo, backup e janela medida dos serviços próprios; se a janela for impraticável, revisar a change antes do remoto.
- [Confundir fundação com isolamento completo] → Gate único testado e relatório de entrega explícito; B01/B02 continuam futuros.
- [Alterações preexistentes em arquivos compartilhados] → Revisão de hunks e baseline; commits apenas desta change, sem reset ou inclusão indiscriminada.
- [Gate invalidado durante job] → Revalidar antes de publicar/efeitos externos, preservando lease e trabalho durável sem enviar mensagens.

## Migration Plan

1. Revisar e aplicar a change localmente; registrar inventário de produtores e do estado Git.
2. Ensaiar upgrade em PostgreSQL isolado com base vazia, legado sintético válido e legado inconsistente; comparar UUIDs, counts, vínculos, valores e referências antes/depois.
3. Testar gate, sessão antiga, revogação e integridade negativa; verificar regressões de galerias, prévias, checkout, lifecycle e produtores sem serviços externos reais.
4. Executar verificações locais/CI aplicáveis; preparar relatório de implementação com evidências e limitações.
5. Identificar a versão real do destino e reconciliar histórico somente com fonte confirmada, preservando outras changes. Inventariar host/serviços/volumes/rede/portas/subdomínio apenas em leitura.
6. Apresentar release exata, janela própria, backup/restauração, serviços afetados e reversão compatível; solicitar autorização operacional.
7. Somente depois da autorização, liberar os recursos exclusivos do projeto e validar contagens, contexto e fluxos; registrar a entrega efetiva ou falha.
8. Após revisão humana do resultado, sincronizar specs e arquivar; pendências reais permanecem abertas até haver evidência.

## Validation Notes

Os ensaios históricos de downgrade usam head explícito 0068, pois 0069 recusa remoção de propriedade já atribuída. A cadeia completa e a preservação de todas as colunas legadas continuam testadas separadamente em PostgreSQL/SQLite; não relaxar a barreira para fazer testes antigos passarem. Fixtures de schemas históricos refletem somente as colunas existentes naquela revisão. A CI recebe PostgreSQL sintético exclusivo para que os testes de integridade/migration/contexto novos não sejam pulados.
