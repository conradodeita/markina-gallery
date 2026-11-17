# Design

## Context

Ver `proposal.md` e os três deltas de especificação. Hoje a escolha self-service grava `canonical_host_status=reserved`; o resolvedor recusa esse estado e não existe ação de promoção. O console do PlatformOwner já usa senha + TOTP, UUID de intenção, lock/idempotência e `PlatformAdminEvent` append-only para mutações sensíveis. A zona foi migrada com DNSSEC validado. A change `archive/2026-11-08-prepare-operational-wildcard-certificate-issuer` preparou e validou localmente uma arquitetura de emissor isolado; instalação/configuração no Oracle, custódia real, emissão/renovação públicas e rota SaaS continuam sem comprovação.

**Checkpoint de aplicação, 08/11/2026:** a promoção local e sua auditoria estão implementadas e validadas em PostgreSQL. O inventário em `operations-inventory.md` confirma NPM 2.15.1, rotas existentes e DNSSEC, e mostra que guardar o token DNS no SQLite do NPM não é aceitável. A change `archive/2026-11-08-prepare-operational-wildcard-certificate-issuer` fornece uma alternativa local com cofre e emissor separados, além de helper restrito para instalar apenas o bundle no NPM; seus testes sintéticos não comprovam instalação ou funcionamento no Oracle. A configuração externa continua bloqueada até inventário/instalação aprovados, custódia real e recuperação verificadas, token real autorizado, emissão/renovação ensaiadas e autorizações operacionais específicas.

## Goals / Non-Goals

**Goals:** habilitar subdomínios de um só rótulo por um wildcard DNS-only e certificado wildcard renovável, manter os hosts atuais, falhar fechado e permitir liberação individual auditada depois dos gates.

**Non-Goals:** alterar tráfego DNS/NPM/Oracle nesta etapa local; trocar `markina` ou a raiz; habilitar Cloudflare proxy/cache; publicar a aplicação; aceitar hosts com mais de um rótulo; oferecer edição, reciclagem ou reatribuição de hostname.

## Decisions

- **DNS e TLS:** adotar a escolha do proprietário: `*.pickyourpic.com.br` em DNS-only para a origem verificada e certificado Let's Encrypt wildcard via DNS-01 Cloudflare. O desafio HTTP-01 não emite wildcard. Preservar registros exatos e DNSSEC; conferir precedência de nomes existentes antes da mudança. Ver [wildcards DNS da Cloudflare](https://developers.cloudflare.com/dns/manage-dns-records/reference/wildcard-dns-records/) e [desafios Let's Encrypt](https://letsencrypt.org/docs/challenge-types/).
- **Credencial e emissão:** usar somente token Cloudflare escopado à zona e permissões DNS necessárias, custodiado no cofre operacional separado do NPM. O serviço emissor acessa a credencial por mecanismo de credenciais do systemd e não acessa Docker; um helper autenticado por identidade local e destino fixo instala somente o bundle aprovado no NPM. O pacote correspondente foi ensaiado localmente, mas ainda não instalado no Oracle. Antes de qualquer execução externa, confirmar permissões/recuperação da chave real, identidade e unidades no host, digest/configuração atuais do NPM, caminho de instalação e recuperação. Se qualquer gate falhar, bloquear emissão e instalação; não armazenar o token no SQLite do NPM nem improvisar alternativa.
- **Roteamento:** criar um único host wildcard no NPM apontado ao ingresso SaaS comprovado no inventário. Rota explícita existente tem precedência; preservar o `Host` validado até a aplicação. Não confiar em `X-Forwarded-Host` enviado pelo cliente. Hosts SaaS exigem hostname canônico exato, tenant ativo e estado `ready`; o host legado exato da conta proprietária com status nulo mantém seu contrato atual. DNS wildcard não é autorização e host desconhecido/reservado não pode cair na conta proprietária.
- **Ativação:** estender a ação sensível existente do console, sem reutilizar `Tenant.status`. A intenção identifica tenant e hostname persistidos, estado esperado `reserved`, UUID de requisição e SHA-256 do relatório operacional que o PlatformOwner revisou. O hash registra a referência exata do relatório; não prova por si só que seu conteúdo está correto, portanto a UI deixa explícita a confirmação humana. Reautenticar por senha + passo TOTP não reutilizado; atualizar somente `canonical_host_status` e gravar auditoria com hash, ator e transição. Estender aditivamente o allowlist append-only de `PlatformAdminEvent` com ações de sucesso/recusa e campo `evidence_sha256` validado como 64 caracteres hexadecimais; downgrade não pode apagar eventos novos. Replay idêntico devolve o resultado; conflito ou gate incompleto não muta. Não usar SQL manual.
- **Compatibilidade:** inventariar todos os consumidores de `tenant_hosts`/host canônico (API, web, auth, URLs de compras/galerias, notificações e jobs). Preservar o hostname legado exato da conta proprietária quando seu status é nulo; cobrir regressão explicitamente. Nenhum host pode ser promovido enquanto um serviço/worker que interpreta host estiver em runtime antigo. Cookies permanecem host-only; nenhum token ou sessão vai em query string.
- **Prova local e operação:** testar dois tenants sintéticos, hostname exato, desconhecido, reservado, suspenso, host profundo, autenticação, links e tentativas cruzadas. Depois, um runbook separado registra DNS/TLS/NPM, recuperação e validação ponta a ponta. A configuração pública só ocorre após inventário zero-impacto e autorização própria.

## Risks / Trade-offs

- **[Origem exposta por DNS-only]** clientes alcançam o IP diretamente e não passam pela borda/WAF/proxy da Cloudflare → manter proteções no Oracle/NPM e não tratar DNS-only como ocultação ou proteção de origem.
- **[A credencial DNS amplia o impacto de comprometimento]** → emissor e cofre separados do NPM, token mínimo, permissões e recuperação verificadas, rotação/revogação documentadas; bloquear se a instalação no host não reproduzir as garantias provadas localmente.
- **[Runtime SaaS ou worker divergente]** pode atribuir requisição a tenant errado ou cair no proprietário → gate exige mesma política em todos os consumidores e testes A/B antes de promover qualquer host.
- **[Wildcard DNS alcança nomes profundos, certificado cobre somente um nível]** → rejeitar hosts com rótulos adicionais no runtime; testar TLS e resposta fechada. DNS não concede acesso.
- **[Relatório operacional pode conter evidência incorreta]** → revisão e confirmação ficam explicitamente sob responsabilidade do PlatformOwner; registrar somente SHA-256, tenant, host, ator e transição, sem anexar payload livre ou segredo ao banco/auditoria.
- **[Proxy compartilhado]** host catch-all pode interferir com outros serviços → inventariar hosts/rede/upstream, preservar regras explícitas e limitar alteração à rota Pick-your-Pic.
- **[Emissor ou helper indisponível/incompatível no host]** → validar digest/identidades/configuração e recuperação sem interferir no NPM compartilhado; manter emissão/rota bloqueadas até execução externa autorizada e renovação ensaiada.

## Migration Plan

1. Implementar e validar localmente auditoria/ativação, resolução por host e telas/contratos, sem chamar Cloudflare, NPM ou Oracle.
2. Preparar pacote operacional: SHA/schema/serviços, inventário NPM/DNS, portas/rede/upstream, evidência de recuperação, checklist de isolamento e plano de reversão. Solicitar autorização específica antes de qualquer escrita externa.
3. Com autorização e runtime SaaS já compatível publicado pelo release aprovado, instalar/configurar o emissor separado e o helper após inventário de impacto zero; validar custódia/recuperação, emitir via DNS-01, ensaiar renovação e só então configurar a rota wildcard Pick-your-Pic. Validar raiz, `markina`, serviços existentes, tenant sintético, hosts reservado/desconhecido e isolamento.
4. Só após evidência validada, o PlatformOwner ativa cada hostname individualmente. Em falha, fechar a rota wildcard e restaurar somente recursos Pick-your-Pic conforme autorização; preservar DNS/serviços de terceiros e dados. Rebaixar um host pronto exige ação auditada própria; nunca liberar nem reatribuir o nome.

## Contrato local implementado

- `POST /api/admin/platform/console/tenants/{tenant_id}/hostname/activate` usa o router sensível e a validação de mesma origem já existentes.
- Corpo: `request_id`, `expected_hostname`, `expected_status="reserved"`, `evidence_sha256` em 64 hexadecimais minúsculos, `confirm_readiness=true`, `current_password` e `totp_code`. O servidor compara hostname/estado com o tenant persistido; o UUID do path não concede autoridade.
- A resposta contém tenant, hostname, `canonical_host_status="ready"` e `replayed`; não devolve credenciais. A auditoria registra `tenant.host_ready` ou `tenant.host_activation_denied`; sucesso guarda hash e transição, sem alterar `Tenant.status`.
- O console exibe a conta selecionada e o hostname. A troca de consulta limpa hash, atestação e credenciais. O hash identifica o relatório que o proprietário afirma ter revisado; não valida automaticamente seu conteúdo.
