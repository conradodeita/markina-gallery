# Avaliação de mensagens por e-mail por tenant

## Escopo e decisão vigente — 05/11/2026

O proprietário pediu avaliar uma escolha exclusiva **WhatsApp ou e-mail por tenant**, reaproveitando a central Notificações. Push permanece independente dessa escolha. O mesmo tenant não deve emitir o mesmo aviso pelos dois transportes nem usar fallback silencioso entre eles; tenants diferentes podem escolher canais diferentes.

Depois de recordar que clientes entram por código WhatsApp, o proprietário determinou **continuar com WhatsApp obrigatório**, retirando a proposta inicial de liberar uploads sem canal. Nenhuma alteração funcional retirou esse gate. A alternativa e-mail descrita aqui é avaliação, não funcionalidade disponível nem autorização de configuração externa, SMTP, DNS ou credenciais.

## Resultado da análise do código

| Área | Evidência atual | Reaproveitamento e lacuna |
| --- | --- | --- |
| Central | `frontend/app/admin/notifications/page.tsx`: sete eventos, textos, prévias e preferências versionadas; `notification_contract.py` separa destinatário e variáveis | Reaproveitar eventos, cards e validação de variáveis. E-mail precisa assunto, texto e prévia próprios; não renomear cegamente o campo WhatsApp de 500 caracteres. |
| Isolamento | `NotificationSetting` e `NotificationEvent` escopados por tenant; versão e snapshots | Adicionar preferência exclusiva de comunicação do tenant, com versão própria. Manter push independente por evento e os dados WhatsApp existentes. |
| Entregas | `NotificationDelivery.channel` admite somente `push` e `whatsapp`; worker e outboxes revalidam identidade, origem e prazo | E-mail requer migration aditiva, lease/tentativas, vínculo tenant-remetente e idempotência por evento/versão/canal. Uma edição de UI não basta. |
| E-mail existente | `email_delivery.py`: SMTP/sandbox, remetente por configuração do servidor; `EmailDelivery.kind` limita autenticação e avisos de segurança | Aproveitar interfaces/padrões de cifra, retentativa e transporte; não reutilizar a identidade global como se fosse a caixa pessoal de cada fotógrafo. As outboxes de segurança não viram fila de marketing/comunicação comercial. |
| Destinatários | `Client` exige nome e telefone; não possui identidade de e-mail verificada equivalente à identidade de telefone | Coletar, validar e vincular e-mail por cliente/tenant, com verificação, recuperação e proteção contra associação indevida. O e-mail do fotógrafo não é o endereço dos seus clientes. |
| Entrada de clientes | Specs e auth atuais usam OTP WhatsApp | Se a intenção futura for operar totalmente sem WhatsApp, é necessário especificar OTP por e-mail, convite, vínculo, sessão, recuperação, rate limit e migração de clientes antigos; não trocar apenas o canal de avisos. |

## Remetente do fotógrafo

Verificar o e-mail no cadastro prova acesso à caixa naquele instante; não autoriza o servidor a enviar como aquele domínio. Não basta colocar o endereço do fotógrafo no cabeçalho From do SMTP da plataforma. Para cumprir o remetente próprio solicitado, é necessário um dos caminhos abaixo, sujeito a nova decisão de produto e prova de integração:

1. **Conectar caixa própria por OAuth**: Gmail com `gmail.send`, ou Microsoft com `Mail.Send` delegado. Requer consentimento individual, tokens cifrados por tenant, escopos mínimos, renovação/revogação, limites do provedor e reautorização. Identidade autorizada deve corresponder ao e-mail verificado do fotógrafo; mudar o cadastro exige revalidar o remetente. A conexão Drive existente não concede autorização de envio de e-mail. Pode ser o caminho mais direto para contas Gmail/Outlook, mas não atende automaticamente todos os provedores.
2. **Domínio próprio autenticado em serviço transacional**: verificar identidade remetente e configurar autorização DNS/SPF/DKIM/DMARC compatível. É adequado a fotógrafos com domínio sob seu controle, com quotas, reputação, bounces e credenciais isoladas. Não oferece envio automático como qualquer conta pessoal Gmail/Outlook.
3. **Remetente da plataforma com nome do fotógrafo e Reply-To dele**: implantação mais simples, porém não cumpre o requisito de From ser o e-mail do fotógrafo. É somente alternativa de produto e não será adotada sem aprovação.

Não foi escolhido fornecedor nem estimado preço/volume; nenhuma conta, domínio ou integração foi criada. Se o requisito continuar sendo o endereço pessoal cadastrado, a recomendação técnica é escolher explicitamente os provedores de caixa suportados e começar por uma integração delegada. A alternativa sob o domínio da plataforma, esclarecida pelo proprietário abaixo, simplifica a autorização e deve ser considerada antes dessa escolha.

## Subdomínio próprio do tenant sob a plataforma — esclarecimento de 05/11/2026

O proprietário reafirmou o requisito de subdomínio por tenant ao registrar: domínio raiz `pickyourpic.com.br`, proprietário em `markina.pickyourpic.com.br` e fotógrafos, por exemplo, em `marca.pickyourpic.com.br` ou `nome.pickyourpic.com.br`. Registrar e reservar esses nomes e o host canônico é parte do provisionamento previsto; esta avaliação não comprova que DNS/TLS e a atribuição automática já estejam implantados. O cadastro do fotógrafo e o `canonical_host` existente precisam ser conciliados com esse provisionamento antes do lançamento.

Como a plataforma controla o domínio pai, existe um quarto caminho viável: identidade de envio por tenant sob seu subdomínio, por exemplo **Marca <avisos@marca.pickyourpic.com.br>**, com Reply-To no e-mail verificado do fotógrafo. A autenticação de domínio e os registros DNS são administrados pela plataforma; o fotógrafo não precisa fornecer a senha ou autorização da caixa pessoal para esse remetente. Conforme o provedor escolhido, a verificação do domínio pai pode abranger seus subdomínios; no SES isso é documentado para envio simples. Configurações avançadas ou autenticação específica podem exigir identidades adicionais, e isso precisa ser validado no fornecedor selecionado.

Esse endereço não é o e-mail pessoal que o fotógrafo informou no cadastro: é um remetente atribuído pela plataforma. A sugestão depende da aceitação desse modelo, sem substituir silenciosamente o requisito original. Reply-To direciona respostas ao fotógrafo, mas não cria caixa de entrada em `avisos@marca...`. Hospedagem do site, envio autenticado e recebimento de e-mail são configurações distintas.

Esta é a opção recomendada para reduzir a configuração individual, se o remetente sob o subdomínio for aceito. Continuam necessários SPF/DKIM/DMARC coerentes com o provedor, gerenciamento de rejeições, limites/abuso por tenant e controle da reputação compartilhada. Subdomínios não garantem isolamento total de reputação. A identidade remetente deve ser derivada do tenant/host reservado pelo servidor, nunca de um From arbitrário fornecido pelo browser. Para enviar como a caixa pessoal externa, a autorização por OAuth/provedor continua necessária e é tecnicamente viável, com mais etapas de configuração.

## Exclusividade e transição futuras

### Registro.br e experiência de escolha do subdomínio — avaliação de 05/11/2026

O proprietário confirmou que usa Registro.br e que `marca` é apenas um exemplo: o prefixo deve representar a marca ou o nome de cada fotógrafo, nunca um valor literal comum a todos. O Registro.br oferece DNS autoritativo opcional separado da hospedagem de sites/e-mails. **Correção após pesquisa ampliada em 05/11/2026:** a página oficial, aberta com JavaScript no navegador, informa até **40 Resource Records** no modo avançado. É limite de registros da zona, compartilhado pelos apontamentos de site/e-mail, não uma franquia de tenants. A consulta textual anterior não apresentou esse trecho. A lista publicada de caracteres de nomes não inclui `*`; o suporte a curinga no DNS do Registro.br não foi comprovado. Não presumir zona ilimitada nem curinga disponível. A arquitetura SaaS continua viável mantendo o registro do domínio e usando DNS com suporte confirmado, sujeito ao inventário e plano de impacto zero antes de qualquer alteração.

Experiência proposta, ainda não implementada: sugerir um endereço derivado da marca, mostrar a prévia `<nome-escolhido>.pickyourpic.com.br` e permitir confirmar um nome disponível. Normalizar o prefixo, validar nomes reservados e reservar atomicamente para impedir concorrência. `markina` permanece reservado ao proprietário; demais nomes de infraestrutura e política de alteração futura precisam ser especificados antes do código. O tenant não precisa de conta no Registro.br nem editar DNS. É preciso definir em qual momento do ingresso essa escolha ocorrerá, preservando o cadastro leve.

Arquitetura de evolução proposta: DNS curinga encaminha os nomes ao SaaS; proxy/HTTPS e aplicação resolvem o host canônico registrado para o tenant. Isso evita um registro DNS manual por novo fotógrafo. Suporte do DNS escolhido, emissão/renovação automatizada do TLS e regras existentes do proxy precisam ser confirmados antes de adoção. Um nome desconhecido que resolva pelo curinga não concede acesso nem herda o tenant do proprietário. Nada foi configurado em DNS, certificados, proxy ou produção durante esta avaliação.

### Adoção por etapas — proposta histórica substituída em 05/11/2026

**Decisão vigente posterior:** o proprietário escolheu migrar agora toda a autoridade DNS para Cloudflare Free, preservando Registro.br como registrador e o destino de `markina`. A proposta Registro.br-primeiro abaixo foi substituída. Inventário e execução estão em [migrate-pickyourpic-dns-to-cloudflare](../migrate-pickyourpic-dns-to-cloudflare/migration-plan.md); a preparação não autoriza corte sem revisão do plano/DNSSEC. Migração DNS não implementa remetente e-mail nem provisionamento automático de hostname.

O proprietário propôs iniciar com o serviço DNS do Registro.br e considerar Cloudflare depois, conforme crescimento do SaaS. É viável para piloto controlado, sujeito ao inventário da zona: os 40 registros totais incluem os de site, e-mail e verificações, sem equivaler a 40 vagas de fotógrafo. Nessa fase, apontamentos individuais e HTTPS de cada novo host precisam ser preparados antes de anunciar o endereço como disponível. Não pressupor suporte a curinga nem API de automação no Registro.br.

Preservar a decisão anterior de ativação automática da conta após verificação de e-mail: não inserir aprovação manual da conta como consequência do DNS. A automação da conta e a disponibilização imediata do subdomínio são requisitos distintos; se o proprietário exigir ambos sem intervenção desde o primeiro cadastro público, a estratégia de provisionamento DNS/TLS precisa estar resolvida antes do lançamento, mesmo com poucos tenants. A aceitação de eventual preparo manual/demora do endereço no piloto continua sendo uma decisão de produto, não requisito implementado nesta avaliação.

Preparar a aplicação para independência do provedor: host canônico e isolamento pertencem ao tenant no banco. Migrar DNS futuramente não exige trocar os endereços dos fotógrafos, desde que nomes e apontamentos sejam preservados. Os gatilhos para avaliar a mudança incluem registros disponíveis, necessidade de automação e proteção por proxy, não apenas quantidade de clientes. Uma migração exige inventário integral (incluindo MX/TXT e DNSSEC), plano de preservação do `markina`, TLS e validação/rollback, com autorização operacional específica. Não foi iniciada migração.

Preferência proposta: um valor enumerado por tenant (`whatsapp` ou `email`), sem dois booleanos que permitam ambos. Habilitar e-mail dependerá de remetente autorizado e destinatários compatíveis, além de decisão sobre login cliente. Não mostrar opção funcional antes disso. Preservar a preferência WhatsApp dos tenants existentes; nenhuma migração deve enviar mensagens ou reapresentar histórico.

Eventos devem congelar a preferência/versão e criar somente uma entrega de comunicação além do push. Uma troca precisa serialização com a criação de eventos e política explícita para mensagens pendentes: cancelar as ainda não iniciadas, preservar em voo e nunca reenviar automaticamente pelo novo transporte uma tentativa de resultado ambíguo. Remetente e destinatário precisam ser revalidados na execução. Aceite do provedor não equivale a entrega ou leitura; prever quotas, backoff, expiração, rejeição, bounce e supressão, mantendo o evento de negócio confirmado.

OTP, convites, recuperação e avisos faciais não pertencem integralmente à matriz dos sete eventos. O proprietário deve definir quais desses fluxos acompanham a escolha do tenant antes de afirmar operação sem WhatsApp. A independência de Web Push não substitui o primeiro login: inscrição push exige adesão em dispositivo e destino autenticado.

## Decisões necessárias antes de implementar e-mail

- Se o modo e-mail também substitui OTP, convites e recuperação de clientes, ou apenas os sete eventos da central. A segunda opção preserva dependência WhatsApp para login.
- Provedores de caixa aceitos e autorização de remetente próprio; escolher OAuth/delegação ou domínio transacional. E-mail verificado de cadastro sozinho não basta.
- Fluxo de cadastro/verificação de e-mail dos clientes existentes e novos, sem coletar dados além do necessário.
- Política exata de troca para tentativas em voo/ambíguas, desconexão da caixa e quotas por tenant; preservar nenhum fallback automático e nenhum aviso duplicado.

## Fontes oficiais consultadas em 05/11/2026

- [Google: diretrizes para remetentes](https://support.google.com/mail/answer/81126?hl=en-en): autenticação e alinhamento de domínio para entregabilidade.
- [Gmail API: escopos](https://developers.google.com/workspace/gmail/api/auth/scopes): `gmail.send` é sensível e exige avaliação de requisitos de verificação OAuth; evitar permissão ampla de leitura da caixa.
- [Gmail API: envio](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send): envio na identidade autorizada.
- [Microsoft Graph: sendMail](https://learn.microsoft.com/en-us/graph/api/user-sendmail?view=graph-rest-1.0): autorização `Mail.Send`; resposta de aceite não confirma entrega concluída.
- [Amazon SES: identidades verificadas](https://docs.aws.amazon.com/ses/latest/dg/verify-addresses-and-domains.html): endereço/domínio remetente precisa de verificação própria do serviço. Fonte de requisitos de identidade, não escolha de fornecedor.
- [Amazon SES: herança de identidade do domínio para subdomínios](https://docs.aws.amazon.com/en_en/ses/latest/dg/creating-identities.html): envio simples a partir de subdomínios do domínio verificado, com exigências adicionais para configurações avançadas.
- [Registro.br: serviço DNS autoritativo e modo avançado](https://registro.br/tecnologia/caracteristicas-tecnicas/): página renderizada no navegador confirma limite de 40 Resource Records e publica restrições de caracteres; corrige a conclusão incompleta da extração textual inicial.
- [Documentação de DNS curinga](https://developers.cloudflare.com/dns/manage-dns-records/reference/wildcard-dns-records/): um curinga pode mapear muitos subdomínios para os mesmos recursos; Cloudflare foi escolhida posteriormente para DNS, com curinga condicionado a validação futura de TLS/proxy/isolamento.
