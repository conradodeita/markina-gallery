# Design

## Context

Ver `proposal.md` para motivação. A base de planejamento é `ce628f01d4aa9f7f9d7eb24bf347e30ae42579d3`, em branch isolada `feature/plan-small-multi-photographer-pilot`.

Correção de intenção confirmada pelo proprietário em 30/09/2026: a validação pequena com fotógrafos/clientes ocorrerá assim que houver prontidão técnica. Neste momento o foco é preparar o isolamento; o roteiro não é ordem para executar um piloto agora ou ativar outra conta antes de completar as dependências.

`backend/app/tenancy.py` exige exatamente uma conta e repete o gate no commit; galerias e fotos já têm propriedade e FKs compostas. `Client.phone_e164` e telefones ativos possuem unicidade global; `client_identity.py` consulta sem conta. Branding, PIX, templates, preferências, conectores e várias rotinas ainda são globais. O diagnóstico atual exige a conta única antes de coleta/cache. Portanto, remover somente `require_single_tenant` seria insuficiente.

O PR #115 da fundação foi integrado em 29/09/2026, mas seus artefatos ainda descrevem release em rascunho e tarefas remotas abertas. Essa divergência é dependência real: reconciliar com evidências de deploy/aceite antes de implementar a presente change, sem marcar tarefas históricas por inferência.

## Goals / Non-Goals

**Goals:** fronteira de autorização verificável em requisições, persistência, workers e mídia; preservação do legado; preparação para fotógrafos independentes; dono com monitor técnico agregado; roteiro futuro de validação pequena condicionado à prontidão.

**Non-Goals:** garantir escala ou concluir P0.2/P0.3; projetar SaaS público; identidade global de cliente; impersonação por suporte; tornar biometria automaticamente disponível; provisionar infraestrutura ou compartilhar canais comerciais por fallback.

## Decisions

### 1. Identidade por conta, confirmada pelo proprietário

Adicionar propriedade explícita a cliente e telefone, com FK composta entre eles. Substituir unicidade global do telefone por unicidade `(tenant_id, phone_e164)`, incluindo índice parcial de telefone ativo/reservado. Toda função de identidade exige contexto autorizado; nenhum resolvedor pesquisa telefone globalmente. UUIDs continuam únicos e legado conserva seus UUIDs.

A alternativa de uma pessoa global com memberships foi rejeitada pelo proprietário em 30/09/2026: dois fotógrafos podem atender a mesma pessoa e precisam de cadastros independentes. Troca/exclusão de telefone em A não afeta B.

### 2. Contexto autenticado sem seletor arbitrário

No piloto, cada administrador tem um vínculo operacional inequívoco com uma conta. Múltiplos vínculos ativos recusam a operação até futura especificação de troca de conta. Senha, TOTP e revogação preservam seus controles.

Para cliente, o backend deriva a conta da capacidade opaca válida do link da galeria/convite, sem aceitar `tenant_id` como autoridade. Desafio e sessão persistem a conta e o cadastro da cliente; verificação, reenvio, retorno interno e rate limit revalidam o contexto. A entrada genérica sem contexto orienta usar o link do fotógrafo. Sessão de A não autentica B, mesmo com telefone igual. O piloto usa perfis/contextos de navegador independentes; não promete várias sessões cliente no mesmo perfil simultaneamente.

Sessões legadas sem conta podem ser reconciliadas somente quando o sujeito tem propriedade única demonstrável; caso contrário, exigir nova autenticação. Nenhuma escolha por primeira conta.

### 3. Matriz completa de propriedade antes de habilitar a segunda conta

Inventariar cada tabela, rota, query, construtor, worker, outbox, cache, arquivo e efeito externo. Classificar em raiz com `tenant_id`, filho com proprietário derivável e constraint verificável, ou infraestrutura compartilhada sem dados comerciais. Cada item recebe teste e decisão explícita. Usar FKs compostas onde entidades próprias de contas se relacionam; filtros autorizados continuam obrigatórios em leituras. Filtros ORM implícitos isoladamente não garantem proteção de SQL, bulk inserts e workers.

As raízes incluem clientes, configurações comerciais e trabalhos que sobrevivem à exclusão da origem. Filho durável cuja origem pode desaparecer precisa conservar proprietário para retenção/cleanup. Estatísticas, exports, recibos de exclusão e mídia histórica entram na matriz. Qualquer item não classificado bloqueia ativação, não é excluído do inventário para liberar o piloto.

### 4. Configurações comerciais e integrações

Transformar os singletons comerciais em configuração por conta: branding, PIX, templates, preferências, presets editáveis e ajuste de prévias. Catálogos imutáveis sem proprietário comercial podem ser compartilhados com decisão documentada. Não clonar PIX, telefone administrativo, branding ou canal do fotógrafo existente para uma conta nova.

Conectores Evolution/Drive e transportes têm vínculo explícito por conta e referência segura de credencial; no piloto, ausência de vínculo impede envio, sem fallback para o canal legado. A conta atual conserva sua associação existente; contas sintéticas usam adaptadores de teste. Canal real da segunda conta depende de inventário/autorização operacional posteriores. Não criar instâncias, credenciais ou novos volumes automaticamente. SMTP técnico de autenticação pode ser compartilhado quando envia exclusivamente ao sujeito verificado e suas entregas/desafios preservam contexto; não é canal comercial compartilhado.

Manter PIX e carrinho dentro da mesma conta. Testar duas configurações PIX sintéticas distintas e snapshots sem movimentação financeira. Segredos continuam em configuração segura de servidor; a referência de configuração não contém o segredo.

### 5. Jobs, caches e mídia

Job/outbox recebe propriedade persistida e idempotência contextual; worker resolve o dono pelo registro e revalida antes de publicar arquivo, confirmar estado ou enviar aviso. Remover o gate de instalação única somente depois de substituir cada uso por controle de proprietário. Jobs de uma conta suspensa não impedem execução de outra. Estado de suspensão não autoriza apagar trabalho durável.

Chaves de cache incluem conta e autorização aplicável. Storage keys legadas são preservadas; novas chaves têm namespace por conta e UUID, sem telefone/nome. Cada endpoint de arquivo revalida ownership; namespace sozinho não concede proteção. Limpezas e retenção conferem manifestos/propriedade persistida antes de atuar. Deduplicação por conteúdo não concede referências entre contas. Preservar formato criptográfico/AAD vigente; se o inventário demonstrar que algum fluxo biométrico exige mudança não especificada, mantê-lo bloqueado e registrar dependência em change própria.

### 6. Dono da instalação e diagnóstico agregado

Criar permissão persistida e revogável de operação vinculada ao administrador, distinta de `TenantAdmin`. Provisionamento é controlado por ferramenta administrativa offline, com dry-run e confirmação do alvo; nenhuma API pública concede esse privilégio. Atribuição inicial ao dono exige identificação inequívoca e aceite explícito no pacote operacional. Não conceder a todos os administradores na migration.

Expor à interface uma capacidade booleana sanitizada calculada pelo backend para mostrar o painel existente somente a operador. O endpoint revalida a permissão antes de coleta/cache. O payload métrico e `capacity-report/v1` permanecem agregados e sem identificadores de contas. Permissão não inclui leitura de acervos de terceiros. Alternativa de manter o monitor global visível aos demais fotógrafos foi descartada por expor a operação da instalação.

### 7. Ensaio pequeno e monitor

Separar preparação/isolamento, verificação de engenharia e validação futura das jornadas. Antes do ensaio, registrar evidências de matriz completa, migration ensaiada, testes de isolamento/autenticação/comércio aprovados e ausência de bloqueios que invalidem as jornadas. Não reduzir esses critérios para antecipar a demonstração. A intenção é executar assim que os critérios e, no remoto, as autorizações operacionais forem atendidos; não há data ou execução imediata solicitada.

O tamanho 2 × 3 limita somente o ensaio, sem prometer limite comercial ou capacidade. Roteiro em `pilot-plan.md`: 12 JPEGs sintéticos sem rostos e metadados pessoais; concorrência máxima de seis jornadas cliente; amostras antes/durante/depois. Respeitar até 30 segundos de cache e comparar timestamps. Jobs podem terminar entre snapshots; não retardar workers artificialmente nem prometer fila positiva. Logs/evidências de conclusão suplementam o snapshot sem inventar tempos.

Não enviar WhatsApp/push/e-mail real em testes automatizados. Em homologação, o fluxo real OTP depende de canal e destinatários explicitamente autorizados; sem isso, registrar bloqueio do aceite real, não substituir por bypass silencioso. Busca facial não executada é uma lacuna declarada do ensaio, embora acesso cruzado às suas rotas e referências seja testado com fixtures sintéticas.

## Risks / Trade-offs

- [Alteração transversal extensa] → matriz de ownership obrigatória e tarefas sequenciais verificáveis; nenhuma segunda conta ativa até todos os caminhos terem cobertura.
- [Contato repetido seleciona pessoa errada] → constraints por conta, OTP contextual e caso obrigatório de telefone igual.
- [Canal legado atende outra conta] → vínculo explícito, testes negativos e envio indisponível sem associação.
- [Migration preserva dados mas quebra binário antigo] → ensaio do schema/binário e barreira de escritores do projeto; reversão corretiva compatível como primeira opção.
- [Monitor confundido com garantia de escala] → comparação descritiva, lacunas explícitas e nenhuma margem orçada/SLO inferidos.
- [Limpeza multitenant apaga vizinhos] → inventário fechado; rotina antiga de limpeza integral fica recusada em instalação com várias contas até plano próprio explicitamente autorizado.

## Migration Plan

1. Reconciliar a fundação e a baseline vigente, obter aceite humano desta proposta e documentar exceção ao MVP de fotógrafo único nos artefatos operacionais quando iniciar implementação.
2. Construir matriz de propriedade e ensaiar migration em PostgreSQL descartável: legado válido, vazio, relações inválidas e duplicidade de telefone em contas distintas. Preservar hashes/referências/contagens sem exportar dados sensíveis.
3. Completar contexto, constraints, configurações, rotas, workers, frontend e negativas antes de habilitar múltiplas contas. Inventariar revisões Alembic reais; não fixar revision a partir de memória.
4. Executar testes locais/CI e registrar prontidão. Somente após esses pré-requisitos, realizar o ensaio sintético isolado futuro. Preparar pacote remoto com SHA/schema, backup verificado, janela, serviços próprios, porta/subdomínio e reversão compatível.
5. Após autorização operacional específica, publicar apenas no projeto `markina-gallery`, em `markina-homolog.duckdns.org`, entrada atual `127.0.0.1:8080`, sujeito a novo inventário. Não criar ou alterar recursos de outros projetos.
6. Autorizar provisionamento/dados/canais do piloto por inventário separado ou explicitamente abrangido no pacote; executar e registrar aceite. Eventual remoção de dados recebe autorização específica, sem `git clean`, prune ou limpeza integral implícita.
7. Após revisão humana do resultado, sincronizar specs e arquivar. Não retornar a binário de conta única sobre schema ou dados multitenant sem compatibilidade demonstrada; downgrade destrutivo/restauração exigem decisão própria.
