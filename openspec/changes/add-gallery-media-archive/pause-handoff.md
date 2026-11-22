# Retomada do trabalho — arquivo frio

Atualizado em 22/11/2026: `add-gallery-media-archive` está em 56/57 tasks; somente a task operacional 1.4 permanece aberta. O resumo e a regra de acesso abaixo foram reconciliados com as specs e tasks atuais. O gate global do primeiro push continua separado deste change. Task 1.4 é pós-release/pré-tenants: configurar e ensaiar a identidade e raiz reais do Drive após release autorizado, primeiro somente com mídia sintética do proprietário, antes de liberar qualquer outro tenant. Não há autorização implícita de deploy/migration/push. Evidências e limites em `validation.md`.

## Decisões recentes

- A recuperação oferece prazos de 7, 14 ou 30 dias, iniciados somente após pull completo e verificado; a taxa fixa por pasta/ciclo é igual para as três opções.
- Se uma foto de `content` for a capa e sua pasta arquivar antes das demais, somente a miniatura reduzida usada como capa fica no servidor até a última pasta ativa arquivar. O original e os outros derivados acompanham a pasta de origem.
- A identidade Workspace e a raiz para mídia são dedicadas e separadas do backup do banco; a conta do proprietário será usada somente no ensaio inicial.
- Após a retomada em 08/11, o proprietário confirmou subpasta própria por UUID para cada tenant. A hierarquia remota não substitui autorização tenant-scoped no backend.
- Após a retomada, o proprietário também aprovou a remoção auditada da cópia fria em pedido explícito validado; a operação só termina após confirmação do provedor e impede restauração posterior. Não haverá expurgo automático nesta versão.
- Task 2.1 documentou o manifesto V1, readback completo para tamanho/SHA-256 e a separação entre catálogo PostgreSQL e bytes frios. Implementação sintética concluída; ainda não houve chamada Google real.
- O staging do restore foi esclarecido: raiz física compartilhada, subdiretório privado por tenant UUID/operação UUID, não servido pela aplicação; capacidade reservada contabilizada por volume e pulls concorrentes. O proprietário aprovou margem pós-staging de max(10 GiB, 15% da capacidade do volume).
- O proprietário aprovou uma transferência global ativa por vez; recuperações têm prioridade sobre novos arquivamentos e cada fila ordena por criação.
- O proprietário aprovou que cada nova pasta exija número inteiro positivo de dias escolhido antes da liberação, sem padrão/herança da galeria, com contagem desde `released_at`. A implementação local por pasta não depende da identidade/quota do Drive.
- Para pastas legadas, o proprietário confirmou que o prazo começa ao salvar a configuração; não há expiração retroativa.
- Durante os 30 dias após a expiração, o cliente autenticado pode ver somente as prévias protegidas de fotos que já estavam selecionadas no instante da expiração e concluir o checkout desses itens. Cada acesso revalida cliente, tenant, pasta, instante da seleção e disponibilidade local. Não há navegação geral nem novas seleções. Após essa janela, só continuam acessíveis as prévias dos próprios itens de pedidos criados durante a janela, se o estado comercial permitir, a mídia ainda estiver local e o pedido impedir o arquivo. Rascunho editável pode impedir o arquivo, mas não estende as prévias; carrinho sem pedido não bloqueia o arquivo nem estende a janela. Depois do arquivamento frio, as fotos ficam invisíveis e as referências são preservadas.
- Decisão recebida: pasta pública aprovada reabre para todos os clientes autorizados; pasta privada somente para a solicitante, ainda que existam outras autorizadas. O fotógrafo escolhe número inteiro positivo de dias a partir da aprovação, sem taxa de recuperação fria.
- O proprietário confirmou que a elegibilidade física da pasta privada aguarda 30 dias completos após o prazo mais recente concedido, mantendo o acesso apenas para a cliente contemplada.

## Retomada

1. Conferir `tasks.md`, `validation.md`, `design.md` e delta spec da change. As tasks locais 2.2a–g, 2.3a–c, 2.4, 2.5a–d, 2.6–2.8, 3.1 e 3.2 possuem evidências; não repetir o antigo planejamento de 21/32 tasks deste arquivo.
2. Task 1.4 é pós-release/pré-tenants. Não chamar Drive real nem ativar worker externo agora. A produção atual permanece preservada. Revisão humana é exigida para sincronizar/arquivar a spec; change não foi arquivada.
3. Matriz R06/R08 e resumo de fases atualizados: 120 unidades reconciliadas. Conector Google/custódia/quota reais, retenção jurídica e backup independente não foram indevidamente declarados concluídos.
4. Laboratório externo ao Git: `C:/codex-data/test-runs/archive-ui-20261109`. PostgreSQL tmpfs exclusivo `pyp-archive-ui-20261109`, loopback 15473; API 8000 e frontend 3039. Proprietário sintético reativado após fase cliente. Storage/capacidade são sintéticos; não confundir sucesso com Drive real. Sessões locais de revisão não testam login/OTP.
5. Último checkpoint frontend: nove arquivos com 109 aprovados/uma expectativa antiga; módulo corrigido repetido com quatro aprovados. Build passou, lint zero erros/13 avisos. OpenSpec estrito e diff check passaram. Logs/capturas fora do Git; não os adicionar ao commit.
6. A próxima etapa global deve partir do checklist de release vigente e das demais changes, respeitando que esta só tem gate pós-release. Não existe autorização de primeiro push antes de 100% do checklist aplicável; não inventar percentual do SaaS a partir de 39/40 desta change.

Arquivos principais: `design.md`, `specs/media-storage/gallery-media-archive/spec.md`, `tasks.md`, `validation.md` e `docs/saas-evolution/requirements.json`.
