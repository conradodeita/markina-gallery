# Design

## Context

O code atual já modela credenciais Mercado Pago por fotógrafo, verifica a conta recebedora no servidor, cifra segredos associados a tenant/credencial e controla disponibilidade por `mercadopago_enabled`. `can_create` permite conta ativa de produção somente quando `MERCADOPAGO_ALLOW_LIVE_PAYMENTS=true`; Compose usa `false` como padrão. Contas classificadas como teste passam por `MERCADOPAGO_TEST_CUSTOMERS` fora de desenvolvimento/teste. A bateria funcional sandbox está registrada na change Orders e é aceita pelo proprietário como validação do fluxo.

## Goals / Non-Goals

**Goals:**

- Abrir o gate global de produção sem habilitar automaticamente a integração para fotógrafos que ainda não configuraram/ativaram sua conta.
- Preservar o par allowlist de credenciais de teste, PIX, reconciliação e histórico já enviados.
- Reusar os cenários sandbox existentes, acrescentando somente verificação proporcional do gate, identificação da conta por tenant e saúde da publicação.

**Non-Goals:**

- Criar marketplace, split/comissão, OAuth, novas tabelas ou credenciais compartilhadas.
- Criar cobranças reais de teste, alterar credenciais dos fotógrafos ou habilitar automaticamente todas as configurações individuais dos tenants; a abertura do gate global permanece uma operação separada, após inventário e aprovação do plano concreto.
- Repetir a bateria sandbox já concluída sem mudança técnica que a justifique.

## Decisions

1. **Reusar o gate global já implementado.** A ativação operacional usará `MERCADOPAGO_ALLOW_LIVE_PAYMENTS=true`. Alternativa de introduzir um segundo toggle ou migrar a configuração por tenant foi rejeitada porque já há gate global e opt-in Mercado Pago independente em `PaymentPreferences`; duplicar flags criaria estados ambíguos.

2. **Manter opt-in individual por fotógrafo.** Abrir o gate global apenas torna contas reais elegíveis. Cada fotógrafo ainda precisa configurar credenciais de produção próprias, passar pela verificação server-to-server do recebedor e habilitar Mercado Pago no próprio tenant. A API continua derivando tenant da sessão autenticada; o cliente não escolhe recebedor.

3. **Preservar o isolamento das contas de teste.** `MERCADOPAGO_TEST_CUSTOMERS` continua sendo o único caminho para contas classificadas como teste em ambiente operacional. O gate de produção não amplia essa allowlist. Alternativa de remover a allowlist por o sandbox ter passado foi rejeitada para evitar pagamentos de teste fora do par autorizado.

4. **Reaproveitar a evidência sandbox como teste funcional da integração.** Não repetir pagamentos APRO/FUND/CONT, reembolsos, webhooks ou compras simultâneas. A validação adicional fica restrita aos contratos de elegibilidade live/teste já existentes, configuração/identidade isolada por tenant, smoke HTTPS e reconciliação sem novas emissões.

5. **Separar implementação de ativação operacional.** Esta change pode atualizar código/spec/docs e preparar um plano. Alterar o ambiente de produção exige inventário atual de serviços/portas, confirmação do SHA/configuração alvo e aprovação explícita do plano de impacto zero conforme AGENTS.md; não fazer toggle durante implementação.

6. **Inventariar sem exigir que o checkout operacional acompanhe commits de suporte.** O workflow aceita apenas o SHA atual de `main` e baixa `orders_pilot_release.py` desse SHA por HTTPS, validando o blob Git contra o pin no wrapper restrito. A produção pode continuar no SHA de produto publicado, que deve ser limpo e ancestral do candidato atual; o helper verifica essa relação, além da ancestralidade do runtime ativo. A rota de inventário não deve importar módulos Python do checkout local, pois ele pode ser anterior ao helper e não é a fonte confiável para esse procedimento. Isso permite leitura remota do runtime existente sem atualizar a aplicação, repositório operacional, serviços ou gate.

7. **Diagnosticar falhas de comandos sem revelar dados operacionais.** Se um subprocesso do inventário falhar, a mensagem de erro poderá incluir apenas um rótulo estático correspondente à etapa (por exemplo, leitura do schema ou verificação HTTPS). Para uma divergência de ancestralidade Git, podem ser reportados somente os SHAs completos que já foram validados como 40 caracteres hexadecimais, pois são necessários para verificar a procedência do checkout. Argumentos de outros comandos, saída do processo, variáveis de ambiente, queries e identificadores nunca serão incluídos; os guards e o comportamento fail-closed permanecem inalterados.

## Risks / Trade-offs

- [Recebedor ou credenciais configurados no tenant errado] → verificar identidade pela API do Mercado Pago no servidor e manter busca por `account_id` e `tenant_id`.
- [Abertura do gate habilita mais contas reais do que o esperado] → manter o opt-in por tenant como condição de disponibilidade, mostrar estado/ambiente no painel e conferir uma matriz de tenants habilitados antes do toggle.
- [Contas de teste escapam do par autorizado] → manter teste da allowlist operacional com gate live aberto e validar falha fechada para par ausente/inválido.
- [Falha após habilitar novas cobranças] → fechar novas emissões pelo gate global, preservando webhook, consulta e conciliação das tentativas já enviadas.
- [Escopo atual conflita com a liberação decidida] → esta change estabelece a exceção posterior à regra de piloto; manter a change Orders como histórico do piloto e apontar a supersessão aqui, sem editar evidências históricas.

## Migration Plan

Não há migration de banco prevista. Primeiro confirmar na CI e no alvo publicado que os contratos existentes suportam conta live e continuam restringindo conta de teste. Depois apresentar o inventário operacional, o valor alvo do gate e os serviços/portas afetados ao proprietário. Somente após aprovação executar a mudança de configuração pelo procedimento de release aprovado, verificar saúde local/HTTPS e elegibilidade de tenants sem emitir cobrança. Para reversão, fechar o gate de novas cobranças reais e manter leitores e reconciliação ativos.
