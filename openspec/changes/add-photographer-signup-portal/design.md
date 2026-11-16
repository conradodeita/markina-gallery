# Design

## Context

Decisão substitutiva de 03/11/2026, refinada pela change `add-progressive-photographer-onboarding`: cadastro pelo website pickyourpic.com.br; após verificar e-mail e definir senha, a conta é ativada automaticamente, sem aprovação manual. TOTP é opcional durante o ingresso e pode ser ativado depois em Configurações; quando ativado, passa a ser exigido nos logins seguintes. O console não cria convites ou credenciais. Nome e e-mail são fornecidos pelo fotógrafo e não inferidos de clientes/checkout.

## Goals / Non-Goals

Provar localmente o backend e uma interface simples de cadastro com dados sintéticos. Não publicar, configurar DNS/TLS, chamar serviços externos, enviar e-mail real ou publicar Termos de lançamento. A prova local não declara prontidão R14 nem autoriza abertura pública.

## Decisions

1. Persistir candidatura com UUIDs gerados pelo servidor, nome/e-mail normalizado, OTP protegido e estados `email_pending → credentials_pending → active`; cancelamento/expiração são terminais.
2. Verificar e-mail por OTP com digest protegido, uso único, expiração, rate limit e respostas neutras. Não reutilizar OTP de clientes ou permitir enumeração de conta existente.
3. OTP válido concede somente sessão restrita de configuração, nunca sessão administrativa. O fotógrafo define senha; isso conclui o provisionamento atômico e idempotente de administrador verificado, tenant finito vazio e vínculo. TOTP não é exigido para ativar a conta e sua configuração voluntária fica na superfície de segurança de Configurações; nenhum papel global é concedido.
4. Preservar tenant legado e separar nome de fotógrafo de clientes. Nome persistido habilita a busca owner-only futura já especificada em improve-photographer-credit-workflows.
5. Interface local mínima com nome/e-mail, OTP e senha. TOTP não faz parte do signup; a configuração posterior é opcional e, quando ativada, protege os logins seguintes. E-mail simulado é uma fronteira exclusiva de teste: nenhuma resposta HTTP pública retorna OTP. Dados sensíveis não vão para localStorage, logs ou protocolo de aceite.
6. Feature flag permanece fechada por padrão. Ativação pública exige gates R14, domínio/DNS/TLS, SMTP, anti-bot e retenção revisados. Testes locais injetam transporte/proteção sintéticos sem alterar .env ou segredos.
7. Autorização local de suspensão pertence ao console; não restaura aprovação manual de cadastro. Reautenticação de ações sensíveis segue senha + TOTP one-time, reutilizando os contratos existentes.
8. Os Termos abaixo são conteúdo inicial do produto e poderão ser editados pelo proprietário. Pela decisão substitutiva de 11/11/2026, o aceite bloqueia somente novos uploads; compra de créditos depende de perfil completo e e-mail verificado, além dos controles financeiros existentes, sem depender da disponibilidade ou do aceite dos Termos. A criação da conta, configuração e exploração permanecem disponíveis. A prova local pode usar a versão explicitamente sintética já aprovada para teste.

O cálculo de prontidão separa a compra do upload: perfil completo e e-mail verificado habilitam a compra, sujeita aos controles financeiros próprios; o upload acrescenta aceite vigente, PIX, WhatsApp e saldo. Reutilizar os guards existentes, preservando replay/reconciliação de uploads duráveis. Atualizar apenas o template inicial dos Termos; não alterar versões publicadas nem protocolos aceitos. O checkbox começa desmarcado e exige confirmação explícita. Esta decisão substitui a dependência de aceite para compra descrita no checkpoint histórico da task 6.5 e nas specs principais de onboarding e billing; ambas permanecem sem sync até a revisão humana de fechamento.
9. Decisão do proprietário em 04/11/2026 para recuperação de conta criada pelo site: entregar link de uso único ao e-mail verificado. Com TOTP ativado, a redefinição exige TOTP vigente e não reutilizado ou código de recuperação de uso único; sem TOTP ativado, o link do e-mail verificado é o fator disponível. Endpoint separado, com resposta neutra e rate limit, elegível somente para identidade cuja origem seja candidatura ativada, tenant próprio ativo e e-mail verificado. O fluxo WhatsApp legado permanece próprio para contas com canal configurado. A solicitação por e-mail não cria sessão, não expõe existência da conta e falha fechada sem transporte de e-mail; token expirado/consumido ou fator inválido não altera senha. Códigos de recuperação são consumidos atomicamente com o token de reset e mudança de senha; o usuário os emite pela superfície de segurança existente após entrar. A prova desta variante é local/sintética, sem envio real nem ativação pública.
10. Decisão do proprietário em 07/11/2026: Cloudflare Turnstile é o provedor anti-bot do cadastro. A interface obtém a chave pública por configuração não sensível da API e carrega o script oficial sem proxy/cache. As flags `PHOTOGRAPHER_SIGNUP_TURNSTILE_ENABLED` e `PHOTOGRAPHER_SIGNUP_EMAIL_DELIVERY_ENABLED` são false por padrão; a chave secreta só existe na configuração segura do backend. O servidor chama apenas `https://challenges.cloudflare.com/turnstile/v0/siteverify`, com timeout limitado, sem redirect, sem retry e sem encaminhar IP. Exige `success=true`, hostname exato configurado e ação `photographer_signup`; token vazio, acima de 2048 caracteres, expirado/repetido, resposta malformada e falha de rede são recusados sem persistência ou fila de OTP. A chave esperada de hostname é `PHOTOGRAPHER_SIGNUP_TURNSTILE_HOSTNAME`, cujo valor deve ser um hostname DNS simples sem wildcard; o padrão do produto é `pickyourpic.com.br`. O hostname raiz autorizado pela Cloudflare cobre os subdomínios abaixo dele, então não será necessário cadastrar um hostname por tenant; a validação da aplicação continua vinculada ao hostname canônico do cadastro. A prova usa transporte HTTP falso e não chama a Cloudflare. Se ambos os gates de runtime e o canal SMTP estiverem prontos no futuro, o OTP é enfileirado na outbox cifrada já existente na mesma transação da candidatura; a validação de origem no worker recusa e-mails antigos após rotação, verificação ou expiração. Configuração SMTP e ativação pública continuam bloqueadas pelos gates 5.1–5.3, sem alteração remota ou envio real neste trabalho.

Referências oficiais consultadas em 07/11/2026: [validação server-side obrigatória e contrato Siteverify](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/) e [integração do widget](https://developers.cloudflare.com/turnstile/get-started/client-side-rendering/).

## Conteúdo inicial dos Termos

O texto editável desta proposta está em [`photographer-terms-draft.md`](photographer-terms-draft.md). O template usa campos configuráveis do provedor/fotógrafo, sem persistir nome ou e-mail real do proprietário neste repositório. A minuta contempla escopo e aceite, responsabilidades, direitos de conteúdo, crianças/biometria, créditos e contestação, funcionamento, suspensão, encerramento e mudança versionada.

## Fontes oficiais consultadas em 2026-11-01

- [LGPD — Lei nº 13.709/2018](https://www2.camara.leg.br/legin/fed/lei/2018/lei-13709-14-agosto-2018-787077-normaatualizada-pl.html)
- [ANPD — Guia de agentes de tratamento](https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/guia_agentes_de_tratamento_e_encarregado___defeso_eleitoral.pdf/@@display-file/file)
- [ANPD — Enunciado sobre crianças e adolescentes](https://www.gov.br/anpd/pt-br/assuntos/noticias/anpd-divulga-enunciado-sobre-o-tratamento-de-dados-pessoais-de-criancas-e-adolescentes)
- [ANPD — Guia ECA Digital publicado em 28/10/2026](https://www.gov.br/anpd/pt-br/assuntos/noticias/anpd-publica-guia-que-esclarece-quem-deve-cumprir-e-quais-sao-as-responsabilidades-das-plataformas-na-protecao-de-criancas-e-adolescentes)
- [ANPD — Comunicação de incidente de segurança](https://www.gov.br/anpd/pt-br/canais_atendimento/agente-de-tratamento/comunicado-de-incidente-de-seguranca-cis)
- [MP nº 2.200-2/2001, art. 10, § 2º](https://www2.camara.leg.br/legin/fed/medpro/2001/medidaprovisoria-2200-2-24-agosto-2001-391394-normaatualizada-pe.html)
- [Código Civil, art. 107](https://legis.senado.leg.br/norma/552282/publicacao/34620807)
- [STJ — validade de assinatura eletrônica sem ICP-Brasil, caso concreto de 18/03/2026](https://www.stj.jus.br/sites/portalp/paginas/comunicacao/noticias/2026/18032026-terceira-turma-valida-emprestimo-digital-com-assinatura-em-plataforma-nao-certificada-pela-icp-brasil.aspx)
- [Mercado Pago — Contestações na Orders API](https://www.mercadopago.com.br/developers/pt/docs/checkout-api-orders/payment-management/chargebacks)
- [CDC — Lei nº 8.078/1990](https://www.planalto.gov.br/ccivil_03/leis/l8078compilado.htm)

## Pendências para o lançamento

Decisões do proprietário em 07/11/2026: o provedor será identificado como pessoa física no primeiro release, com possibilidade de migrar para pessoa jurídica no futuro. Essa migração exigirá revisão e atualização da identidade e dos Termos antes de passar a usar a nova entidade. O proprietário forneceu o nome legal e autorizou usar o e-mail da conta como contato público inicial de suporte/privacidade; não duplicar esses dados pessoais em artefatos de planejamento. A troca futura por e-mail institucional exigirá atualização dos Termos. A análise de quais dados do fotógrafo são necessários segue pendente.

O proprietário informou em 07/11/2026 que ainda não dispõe de advogado/escritório para revisar a minuta. Revisão jurídica e matriz final de responsabilidades seguem como melhoria futura; não bloqueiam a preparação ou publicação inicial autorizada pelo proprietário.

Direção aprovada pelo proprietário em 07/11/2026: disponibilizar edição owner-only em rascunho com prévia e publicação explícita, mantendo versões publicadas e protocolos de aceite imutáveis. A revisão jurídica pode ocorrer futuramente e não bloqueia preparar/publicar a primeira versão. Não inserir aviso explícito de ausência de revisão no texto dos Termos. Uma alteração material preserva os protocolos antigos e segue a política de reaceite aprovada; editar não publica automaticamente.

- Revisão jurídica da minuta e validação da alocação de responsabilidades com o fluxo real de dados e suboperadores.
- Definição da identidade jurídica do provedor, CNPJ/identificador aplicável, endereço e contatos de suporte/privacidade para preencher o texto.
- Decidir quais dados identificam contratualmente o fotógrafo ou a empresa que ele represente; o cadastro atual prevê nome e e-mail, sem coleta adicional aprovada.
- Aplicar a decisão provisória do proprietário de não expurgar automaticamente `AuditEvent`/`PlatformAdminEvent`, com acesso restrito e duração/exceções finais ainda pendentes. Manter essa categoria separada das métricas do Monitor do Sistema (7 dias por padrão, ajustáveis entre 1 e 30; sinal de atividade por um dia) e dos logs técnicos (produção usa `json-file` sem rotação explícita observada). O enquadramento de seis meses do Marco Civil para registros de acesso e sua aplicação ao provedor atual pessoa física permanecem sem conclusão; não transformar isso em prazo global por inferência.
- Avaliar a aplicação do ECA Digital às galerias e aos recursos realmente acessíveis.
- Decidir a política financeira de créditos consumidos após contestação ou reembolso.
- Implementar o gate e o protocolo somente após os gates R14-0–6 e autorização da etapa de lançamento.

## Risks / Trade-offs

- OTP/replay/concorrência: transições transacionais e identificadores únicos; nenhuma criação parcial de acesso.
- Automação aumenta a importância de rate limit e proteção anti-bot; ausência de provedor não abre rota pública.
- Retenção e custódia de credenciais não podem ser presumidas; ambiente remoto permanece desabilitado.

## Migration Plan

Schema aditivo, testes em PostgreSQL descartável vazio/atual, rollback que preserva contas já ativadas. Implementação local sintética autorizada como prova de backend; publicação somente após gates R14 e inventário/plano/autorização específicos. Nenhum reset de dados ou fatores do tenant legado.


## Decisão comercial — contestação após consumo de créditos

O proprietário aprovou em 07/11/2026 congelar o saldo ainda disponível e bloquear novas compras e uploads até revisão manual quando um pagamento de créditos for contestado depois do consumo. O histórico deve ser preservado e o saldo não deve ficar negativo. A regra não decide sozinha o resultado do recurso financeiro nem altera pedidos/fotos já entregues.

## Retenção do protocolo de aceite

O proprietário aprovou em 07/11/2026 manter o protocolo completo enquanto a conta estiver ativa e por até dez anos após o encerramento, com acesso restrito; ao fim, eliminar ou anonimizar salvo obrigação legal ou disputa que justifique retenção adicional. O protocolo contém versão/texto/hash, instante e identidade das partes. Esta política é distinta dos 30 dias para nome/e-mail de cadastro não verificado e dos registros financeiros/auditoria com finalidades próprias.

## Dados do fotógrafo para checkout

Decisão do proprietário: nome completo e e-mail vêm do cadastro e não são pedidos novamente em Configurações; CPF e endereço são obrigatórios antes da compra de créditos para pré-preencher o checkout; telefone permanece opcional. O endereço usa os campos do modelo PayerAddress já compartilhado com o checkout. CPF é cifrado e não devolvido em forma bruta fora do endpoint de checkout autorizado. Não adicionar coleta de documento de identidade, data de nascimento ou dados além dos campos aprovados.

## Expurgo de candidaturas não verificadas

Após 30 dias desde a criação, a rotina remove candidaturas sem evento de verificação, independentemente de o desafio OTP já ter expirado. Também apaga corpo cifrado e destinatário HMAC da outbox associada, marca entrega ainda enfileirada/em processamento como expirada e mantém tentativas técnicas e auditoria sanitizada. Verificação é identificada pelo evento imutável `photographer_signup.email_verified`; portanto, uma candidatura verificada que depois expira durante a configuração não é confundida com cadastro não verificado. A execução fora da prova local requer `PHOTOGRAPHER_SIGNUP_RETENTION_ENABLED=true`, desligado por padrão; a flag do exemplo não ativa qualquer configuração real.

## Acesso de menores no produto

O proprietário decidiu em 07/11/2026 que clientes menores podem usar o fluxo de cliente já existente para login OTP, entrada na galeria, seleção e compra, sem vínculo obrigatório de responsável. A entrada e compra continuam sem gate novo de idade ou titularidade bancária; essa decisão de produto não conclui análises legais ou regras próprias dos meios de pagamento. Fotógrafos/tenants devem ser adultos e confirmar essa condição no cadastro por declaração afirmativa. Registrar somente a confirmação e seu instante, sem data de nascimento, documento ou alegação de verificação independente. O modelo atual não armazena idade do cliente e a representação legal biométrica é escopo separado; não será criado vínculo geral de responsável por esta decisão. A avaliação do escopo ECA Digital continua separada e pendente.

## Avaliação preliminar do ECA Digital

Consulta às orientações da ANPD em 07/11/2026: a plataforma é oferecida à distância, funciona eletronicamente e atende solicitações individuais. O produto é contratado por fotógrafos adultos, porém o proprietário espera que os clientes finais menores acessem galerias, o que torna o uso previsível e fácil (link/OTP); há riscos relevantes de privacidade por fotos e dados pessoais, com busca biométrica sujeita a gates próprios. Para planejamento, tratar a superfície de cliente como potencialmente sujeita às obrigações gerais do ECA Digital e aplicar proteção proporcional. Isso não decide a classificação jurídica final nem transforma o fluxo em rede social: a regra de vinculação do art. 24 está no capítulo de redes sociais e não será aplicada automaticamente sem essa classificação. Nenhuma exigência de vínculo geral ou gate de compra foi acrescentada por esta análise. Permanecem por mapear controles gerais proporcionais, especialmente informação e eventual supervisão parental, preservando o fluxo sem bloqueio por idade que o proprietário aprovou.

### Decisão de escopo do proprietário — 08/11/2026

Para concluir a task 6.9 nesta etapa, o proprietário aprovou: manter a jornada existente de clientes sem barreira de idade, vínculo obrigatório de responsável ou etapa extra para entrar, selecionar e comprar; acrescentar apenas transparência adequada à idade, contato para dúvidas/denúncias e avisos contextuais de privacidade. Ferramentas de supervisão parental ficam fora deste escopo até avaliação específica. A implementação não deve declarar conformidade ou conclusão jurídica. Reutilizar somente o e-mail de suporte/privacidade de uma versão publicada dos Termos; rascunhos não são contato público. Se não existir versão publicada, orientar o cliente a contatar o fotógrafo pelo canal pelo qual recebeu o convite, mantendo acesso normal.

### Mapeamento dos controles proporcionais

- A orientação atual da ANPD (Guia de 28/10/2026) organiza deveres gerais em prevenção, proteção, informação e segurança; avalia acesso provável por atratividade/probabilidade, facilidade de uso e risco significativo em conjunto, considera o funcionamento real e orienta medidas proporcionais que devem ser acompanhadas e aperfeiçoadas. Este mapeamento preliminar não declara que o produto cumpre a lei nem demonstra eficácia dos controles.
- Entrada/login: manter OTP e orientação de que o código é enviado somente a telefone com acesso à galeria; não coletar idade ou dados adicionais do cliente.
- Galeria autenticada: informar em linguagem simples que fotos e seleções podem ser dados pessoais, orientar uso responsável e exibir caminho de contato para dúvidas ou denúncias sem interferir na navegação.
- Busca facial: manter os avisos e consentimentos específicos já existentes; o aviso geral não substitui nem flexibiliza esses controles.
- Supervisão parental: não adicionar ferramenta, conta vinculada ou mecanismo de monitoramento nesta mudança.
- Compra/seleção: manter fluxo, autenticação, gates de compra e estados existentes; nenhum gate etário novo.
- Pendência registrada: avaliar separadamente quais medidas de supervisão parental ou outros controles específicos se aplicam às funcionalidades reais e ao risco do produto, bem como revisar os atos/orientações da ANPD antes de abertura pública ampla. A decisão de escopo atual adia ferramentas de supervisão; ela não afirma dispensa legal.
- Refatoração: revisão limitada às superfícies de login cliente, galeria autenticada e contato público de suporte; nenhum código funcional antigo deve ser removido sem evidência de substituição.

## Retenção do perfil operacional de cliente — decisão de 11/11/2026

O proprietário aprovou não expurgar automaticamente o nome e o telefone do cadastro operacional do cliente somente por inatividade, ausência de galeria acessível ou conclusão das obrigações correntes. A remoção continua explícita e auditada, seguindo o fluxo existente, que bloqueia a exclusão quando há histórico comercial protegido. Esta regra não define prazo para compras/pagamentos, biometria, logs ou mídia, nem fecha o processo completo de atendimento aos direitos do titular. Encerrar uma conta de fotógrafo não concede acesso ao cliente nem elimina automaticamente seu histórico.

## Histórico comercial/financeiro de clientes — decisão de 11/11/2026

Na primeira versão, pedidos, pagamentos e compras de clientes não terão expurgo automático. Manter somente os dados necessários, sob os controles de acesso tenant/console existentes. O prazo final e as exceções não foram definidos e deverão ser reavaliados futuramente; esta decisão temporária não significa retenção permanente. Encerrar a conta do fotógrafo não expurga esse histórico. A edição ou remoção de rascunhos ainda não convertidos em registros históricos segue o fluxo normal do checkout e não é política de retenção.

Inspeção estática de 11/11/2026: `client_lifecycle.py` exige contexto do tenant, bloqueia a exclusão explícita quando encontra ordens, itens, grupos/comunicações de pagamento, entregas, mídia comercial, tentativas do Mercado Pago ou movimentos retidos; após a remoção permitida, persiste recibo idempotente e evento de auditoria. As exclusões localizadas em `checkout.py` e `unified_checkout.py` substituem ou removem rascunhos pendentes, editáveis e não congelados durante ações de atualização ou remoção da seleção. Busca focada em `backend/app` e `backend/migrations` não encontrou rotina automática de expurgo financeiro. A revisão é estática, não substitui testes e não altera comportamento.

## Eventos de auditoria — decisão de 11/11/2026

O proprietário aprovou manter `AuditEvent` e `PlatformAdminEvent` sem expurgo automático por enquanto, com acesso restrito. A duração final e as exceções serão decididas depois; a decisão temporária não equivale a retenção permanente. Essa política não se estende a logs técnicos de aplicação, Nginx ou containers, nem à telemetria agregada do Monitor do Sistema.

Verificação estática: `PlatformAdminEvent` é consultado pela rota do console global protegida por autorização owner-only e tem proteção append-only no banco. Não foi identificado endpoint que retorne registros `AuditEvent` diretamente a fotógrafo ou cliente; o cleanup de auditoria em `homolog_cleanup.py` pertence à limpeza explícita de dados sintéticos de homologação. Não foi executado teste nesta revisão nem alterado código.
