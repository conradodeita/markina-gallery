# Design

## Context

Veja `proposal.md` e os três contratos desta change. A entrega de álbum por pedido já cria o evento `order_delivery_ready`, grava o destino interno para push e valida a revisão financeira/entrega no worker. O texto WhatsApp é configurável, mas o renderizador sanitiza URLs e hoje `{{pedido}}` representa uma referência curta.

A cadeia integrada tem a fundação de tenant, a entrega do álbum e o piloto multitenant. O código já isola cadastro de cliente, pedido e sessão por `tenant_id` e conserva o gate operacional de instalação única enquanto houver lacunas. Falta hostname canônico persistido; a aplicação não deriva tenant de subdomínio ainda.

## Goals / Non-Goals

**Goals:**

- Resolver um tenant por hostname HTTPS canônico registrado e usar esse contexto no desafio OTP, sessão e Compras.
- Enviar no WhatsApp de entrega um link interno específico ao pedido e ao subdomínio, com o retorno pós-login validado.
- Restringir lista, detalhes e link do álbum aos pedidos do cliente no tenant ativo.
- Reutilizar `SaleOrder.delivery_album_url` e o evento atual disparado por “Enviar”, aceitando links de compartilhamento externos seguros e preservando-os no botão de Compras.
- Preservar semântica de `{{pedido}}`, destino do push, controles de canal, autorização do pedido e gates atuais de pagamento/revisão.

**Non-Goals:**

- Cadastrar fotógrafos, provisionar DNS/certificados, trocar domínio público ou habilitar múltiplas contas em produção nesta change.
- Completar isolamento de todo módulo do produto, fairness/cotas de filas, billing SaaS ou migração de PIX/recebedores.
- Incluir no WhatsApp o link externo do álbum, acessar/validar remotamente o destino ou conceder acesso ao pedido por possuir uma URL.

## Decisions

### 1. Hostname canônico resolve contexto; autorização vem das relações persistidas

Cada tenant poderá ter um hostname HTTPS canônico único. A aplicação compara o host normalizado da requisição com o registro persistido; não usa `X-Forwarded-Host`, slug ou tenant ID recebido do cliente. O proxy deve aceitar somente domínios provisionados e repassar o `Host` validado. Hosts desconhecidos ou inativos falham fechados para o fluxo contextual de OTP.

Compatibilidade do fotógrafo único: se houver exatamente um tenant ativo, sem hostname persistido, a origem HTTPS já configurada em `PUBLIC_APP_ORIGIN`/`MARKINA_PUBLIC_URL` pode servir como hostname canônico. Esse fallback vale somente para correspondência exata com a origem confiável e nunca aceita o Host recebido como origem para gerar links. Quando houver mais de um tenant ativo, o fallback deixa de existir e cada tenant precisa ter hostname explícito; um tenant sem hostname não pode usar a sessão em outro host. Esta change não provisiona DNS ou certificados.

Alternativa descartada: aceitar qualquer subdomínio de um wildcard e derivar tenant pelo primeiro rótulo. Isso permite host-header poisoning e roteamento para tenants inexistentes ou não verificados.

### 2. Cadastro e OTP independentes por fotógrafo

Seguir a decisão registrada no piloto multitenant: cada fotógrafo mantém cadastro próprio por tenant; o mesmo telefone pode existir em A e B com nomes/dados independentes, sem fusão automática. A rota de reautenticação via Compras aceita somente clientes já cadastrados no tenant resolvido pelo host, envia OTP ao contato verificado e dá a mesma resposta pública para cadastro ausente ou presente. Não permite cadastro novo sem convite de galeria. Challenge e sessão permanecem vinculados ao tenant; o cookie continua host-only, `Secure`, `HttpOnly` e `SameSite`. Não consultar nem enumerar cadastro de outro tenant.

Alternativa descartada: tratar subdomínio como identidade do cliente ou fundir os registros de mesmo telefone em conta global. Isso alteraria a decisão do piloto e poderia compartilhar nome, sessão e dados comerciais entre fotógrafos.

### 3. Propriedade comercial consistente por tenant

Antes de ativar o fluxo, cada pedido deve resolver sem ambiguidade para o tenant por meio de relações persistidas. Adicionar propriedade/membership comercial aos pedidos e clientes somente conforme o modelo já consolidado após reconciliar a fundação; impor constraints para que pedido, galeria de origem, cliente vinculado e entrega pertençam ao mesmo tenant. Consultas de Compras filtram tenant e cliente no backend antes da projeção. O hostname nunca substitui os predicados de autorização.

Alternativa descartada: depender somente do UUID do pedido, de um fragmento HTML ou de filtros no frontend. Fragmentos não são enviados ao servidor e UUIDs não provam propriedade.

### 4. O aviso reutiliza a entrega por pedido e leva à compra da cliente

O fluxo mantém o card de Vendas e pagamentos, o campo por pedido, o clique em “Enviar” e o evento `order_delivery_ready` já existentes. `SaleOrder.delivery_album_url` continua sendo a origem do botão externo “Fotos disponíveis” em Compras; aceita URL de compartilhamento HTTPS de serviço externo público, sem credenciais, controle ou porta não padrão, preservando query e fragmento e sem buscar o destino no servidor. O campo é validado e exibido como link externo do álbum, sem vínculo com qualquer outro pedido.

O produtor do mesmo evento cria `/library/purchases#order-{UUID}`. O renderizador WhatsApp expande `{{link_compras}}` usando HTTPS e o hostname canônico do tenant do pedido. Esse link abre a compra da cliente autenticada, não a área do fotógrafo e não o serviço externo. Sem sessão, o fluxo de OTP retorna ao pedido após validar cliente e tenant. Push continua com seu `target_path`; `{{pedido}}` permanece a referência curta; o link externo nunca é incluído no texto WhatsApp.

No ambiente atual de fotógrafo único, a origem pública configurada pode suprir temporariamente o hostname não cadastrado. Em operação multitenant, o link exige o registro explícito de hostname por tenant.

Como o template WhatsApp é snapshot imutável do evento, o link expira segundo o TTL existente para notificação. Reenvio deliberado gera snapshot novo com a configuração e hostname atuais, sujeito à mesma revisão/ propriedade do pedido.

Alternativa descartada: permitir URLs externas no renderizador WhatsApp ou alterar o significado de `{{pedido}}`. O destino de arquivo fica somente no pedido e em Compras, sem ampliar a superfície do template ou mudar notificações existentes.

### 5. Retorno do OTP é limitado a Compras e revalidado

Ao abrir Compras sem sessão válida, a superfície web redireciona para entrada no mesmo hostname, carregando apenas caminho local permitido e fragmento de UUID. Um destino `order-{UUID}` solicita OTP somente a cliente já cadastrada nesse tenant; o desafio guarda tenant e retorno interno restrito. Não aceita URL absoluta, mudança de host, rota administrativa nem caminho arbitrário. Após OTP, o backend verifica novamente tenant, identidade e propriedade do pedido; pedido não autorizado cai em `/library` sem revelar existência. Uma sessão válida no host correto abre a rota e o fragmento existentes.

Alternativa descartada: permitir OTP genérico por telefone sem contexto de host/tenant ou cadastro de novo cliente a partir do UUID. O telefone é consultado apenas no fotógrafo do hostname canônico e somente para reautenticar cadastro existente.

### 6. Dependências, rollout e alterações locais

Antes do código, reconciliar o head/ref que contém a fundação de tenant, a entrega de álbum e todas as alterações locais preexistentes. Não misturar arquivos preexistentes no escopo nem assumir que migrations presentes nesta cópia são a cadeia implantada. Implementar e validar primeiro em ambiente local/sintético; nenhuma alteração de DNS, certificado, proxy, `.env`, homologação ou produção é autorizada por esta change. Habilitar hostnames reais depende de inventário, TLS e aprovação operacional próprios.

Alternativa descartada: liberar apenas a geração de links e presumir que o tenant foundation atual cobre pedidos/sessões. Ele limita a uma conta e não entrega isolamento multitenant completo.

### 7. Imagem PostgreSQL do CI não é dependência do deploy

Os serviços PostgreSQL temporários do GitHub Actions usam `postgres:17-alpine` exclusivamente para testar o backend. Eles não são usados pelo compose de homologação nem pelo servidor. O pull da mesma imagem no Amazon ECR público foi recusado por limite de dados; antes de alterar o workflow, o manifesto `linux/amd64` de `mirror.gcr.io/library/postgres:17-alpine` foi comparado ao ECR e os dois retornaram o digest `sha256:aa90e97ee862e558111d34cfb8b2c4bec768c2b039fb791341686928560263b3`.

Para manter a imagem e versão efetivas, usar o mirror Google da imagem oficial do Docker Hub somente nos dois serviços do CI. Validar a mudança pelo workflow integral antes do merge. Nenhuma referência de imagem de runtime/deploy é alterada.

Alternativa descartada: esperar indefinidamente pela cota do ECR ou voltar ao Docker Hub sem verificar identidade da imagem e disponibilidade.

### 8. Fotos disponíveis conserva a ativação por evento

`order_delivery_ready` já é um evento comercial configurável anterior aos três eventos novos controlados por `TRANSACTIONAL_WHATSAPP_ENABLED`. O canal de fotos disponíveis SHALL depender do interruptor WhatsApp próprio do evento e da prontidão normal do provedor; aplicaremos a mesma decisão tanto na criação da entrega quanto no worker. O gate global continua protegendo `first_access`, `first_selection` e `private_photos_ready`. Push permanece independente.

Esta decisão evita ativar incidentalmente outros eventos quando o fotógrafo só habilitou “Fotos disponíveis”. Ela também corrige a divergência entre o comentário/documentação do gate (“três eventos novos”) e sua implementação anterior, que bloqueava todo evento não relacionado a pagamento.

## Risks / Trade-offs

- [Host encaminhado incorretamente pode direcionar uma cliente ao fotógrafo errado] → mapear hostname canônico registrado após validação do proxy e falhar fechado; nunca inferir pelo cabeçalho bruto.
- [Telefone repetido pode misturar cadastros entre fotógrafos] → unicidade e resolução OTP por tenant, cookies host-only, testes com nomes diferentes e nenhuma consulta cruzada.
- [Pedido sem tenant inequívoco pode expor dados] → interromper envio e projeção; resolver inconsistências por migration/inventário antes de ativar múltiplas contas.
- [URL interpolada pode ultrapassar limite de template WhatsApp] → validar renderização pelo limite existente e rejeitar config/mensagem inválida sem remover álbum disponibilizado.
- [Login comum ignora hoje destinos gerais e entrada sem convite] → criar somente reautenticação de cadastro existente ancorada no host canônico, com resposta neutra, OTP e retorno de pedido revalidado.
- [Checkout tem muitos dados/configurações globais] → escopo desta change só promete isolamento de identidade, Compras e entrega; não declarar multitenancy global nem ativar novos tenants.
- [Checkout local contém mudanças preexistentes amplas e cadeia de migration divergente] → inventariar e reconciliar base antes de aplicar; não descartar, reformatar ou incluir tais alterações.

## Migration Plan

1. Reconciliar origem/head; preservar a fundação de tenant já integrada e adicionar somente hostname canônico. Não duplicar colunas/constraints de cliente e pedido.
2. Ensaiar migration aditiva em PostgreSQL descartável; hostname é nullable para preservar tenants já existentes e único quando preenchido. Nenhum hostname real é provisionado por migration.
3. Implementar host resolver, tenant em desafio/sessão, predicados de Compras, interpolação WhatsApp e retorno OTP sem DNS real nem transporte WhatsApp real. Testar regressões da entrega atual e payloads/templates antigos.
4. Ativar hostnames reais somente em change/liberação operacional apropriada: inventário de subdomínios/portas/certificados, plano de impacto zero e autorização explícita. Não alterar infraestrutura nesta etapa de especificação.
5. Reversão preferencial por versão compatível que preserve propriedade e hostnames; não executar downgrade destrutivo nem apagar relações. Qualquer rollback de schema em ambiente remoto exige plano e autorização separados.

## Open Questions

- O padrão do domínio profissional, a política para escolha/reserva do slug e a administração de hostname serão definidos na change de provisionamento de fotógrafos; não alteram o contrato deste link canônico.
