# Plano de migração DNS — Pick-your-Pic

## Autorização de execução — 05/11/2026

Após revisar os registros, IP, DNS-only, nameservers atribuídos, redução temporária de DNSSEC e limite de retorno de quatro horas, o proprietário respondeu: **“Autorizo a troca e a transição temporária do DNSSEC”**. Autorização abrange salvar `kara.ns.cloudflare.com` e `mustafa.ns.cloudflare.com`, acompanhar propagação e reativar DNSSEC com a chave Cloudflare após validação. Não abrange interrupção, deploy, proxy/cache, curinga ou alteração do Oracle. Revalidação imediatamente anterior à execução às 16:43 BRT: quatro consultas aos NS novos com A/TTL corretos, markina HTTPS 200.

## Estado em 05/11/2026

**Troca enviada e aceita pelo Registro.br às 16:45 BRT (19:45 UTC).** O painel persistiu `kara.ns.cloudflare.com` e `mustafa.ns.cloudflare.com` e informou transição por aproximadamente 1h59m45s antes da delegação externa. Primeira nova verificação útil a partir de aproximadamente **18:45 BRT de 05/11/2026**, sem assumir que todos os caches terão mudado nesse horário. Zona Cloudflare Free ainda pendente; os dois A estão persistidos e validados diretamente nos novos NS. Nenhum destino, proxy, certificado ou serviço Oracle foi alterado. Migração e restauração do DNSSEC ainda não concluídas.

Na primeira confirmação (aproximadamente 16:43), a sessão do Registro.br expirou, sem mensagem de sucesso. O proprietário entrou novamente; painel ainda mostrava DNS Registro.br. Só depois dessa conferência a operação foi repetida, com confirmação da transição visível. Não houve repetição cega nem nova solicitação de autorização.

## Inventário confirmado

Tabela autenticada completa do Registro.br, consultada em 05/11/2026 aproximadamente 16:30 BRT (19:30 UTC), sem editar/salvar:

| Nome | Tipo | Destino | TTL público observado | Configuração de destino |
| --- | --- | --- | --- | --- |
| pickyourpic.com.br | A | 132.145.193.169 | 3600 | DNS-only |
| markina.pickyourpic.com.br | A | 132.145.193.169 | 3600 | DNS-only |

A tabela apresentou somente esses dois registros de usuário; sem MX, TXT, CNAME, AAAA ou curinga. O próprio editor informa: não aceita `@`, `*` nem SRV. Nenhum filtro textual foi preenchido. NS/SOA e material DNSSEC são gerenciados pelo provedor e não devem ser copiados como registros de serviço.

Consultas públicas (Resolve-DnsName/1.1.1.1 e DNS over HTTPS Google), aproximadamente 16:26 BRT:

- NS: `e.sec.dns.br` e `f.sec.dns.br`, TTL observado 3600.
- A: os dois destinos acima. AAAA raiz sem resposta positiva.
- MX/TXT/CAA raiz: NOERROR sem Answer, respostas autenticadas; ausência de dados nesses nomes, não falha de consulta.
- `www` e `_dmarc`: NXDOMAIN.
- DNSSEC: DS ativo, key tag 34215, algoritmo 13, digest type 2, TTL 3600. Reconsultar antes da operação; não reutilizar DS anterior para a Cloudflare.
- HTTPS normal: `https://markina.pickyourpic.com.br` HTTP 200; `https://pickyourpic.com.br` HTTP 404. A raiz 404 é referência anterior, não falha causada por migração.

## Oracle e impacto

Leitura SSH com chave existente e validação de host preservada, sem mutações:

- Serviços Markina API/web/nginx, workers, banco/Redis e WhatsApp observados ativos e saudáveis. Outros projetos compartilham o host e permanecem fora do escopo.
- Nginx Proxy Manager publica 80/443 (admin 81 existente); gateway Markina publica somente `127.0.0.1:8080 -> 80`. Não alterar portas/firewall.
- NPM `/data/nginx/proxy_host/3.conf`: `markina.pickyourpic.com.br` encaminha HTTP para `markina-homolog-nginx:80`; certificado existente `/etc/letsencrypt/live/npm-3/fullchain.pem`.
- O nome `markina-homolog-nginx` é alias ativo de `markina-gallery-nginx-1` na `npm-network`; não prova ambiente de homologação nem deve ser corrigido nesta migração. Imagem observada `sha256:96868d9fa38f469a86d2f25787e43ee9ad330339d30be260aa9f5a338bb03751`, StartedAt `2026-10-30T18:04:10.704021473Z`.
- Nenhum host raiz explícito apareceu nos trechos de proxy conferidos. Não publicar website nem alterar essa configuração como parte do DNS.

## Plano operacional e checkpoints registrados

Os itens abaixo preservam o plano e os checkpoints conhecidos em 05/11/2026. As pendências daquela etapa são históricas e foram atualizadas pelas seções posteriores, especialmente pelos registros de validação final de 07/11/2026.

1. **Concluído:** zona Free pendente com entrada manual dos dois A, TTL 3600, DNS-only. Bot Preference Sync desativado na preparação para não alterar robots.txt. Não foi feita varredura nem importado qualquer registro extra. NS atribuídos: `kara.ns.cloudflare.com` e `mustafa.ns.cloudflare.com`. Cada um respondeu A raiz e A markina = 132.145.193.169, TTL 3600 (quatro consultas Resolve-DnsName corretas). Tabela final confirma 2 de 200 registros e estado pending.
2. **Procedimento oficial confirmado:** DNSSEC é obrigatório no DNS Registro.br e não tem desativação separada. Em Características Técnicas / Desativando o serviço, o provedor documenta informar pelo menos dois NS autoritativos e aguardar pelo menos duas horas para retirada da chave antes da publicação dos novos servidores; descreve transição de até três horas. A ajuda geral pede consistência dos servidores antigos/novos por 24 horas. Não interpretar esses prazos como garantia para todos os caches. Não foi enviado contato ao suporte.
3. **Concluído:** proprietário revisou e autorizou expressamente a troca e a transição temporária DNSSEC, conforme seção de autorização. Não há consentimento para interrupção.
4. **Checkpoint de 05/11, após o envio:** salvos os dois NS no fluxo oficial, sem acrescentar DS antigo; painel confirmou a transição às 16:45 BRT. Naquele momento, ainda era necessário aguardar o processamento externo. A delegação, a reativação de DNSSEC e a validação final estão documentadas nas seções posteriores.
5. **Plano para a transição:** manter serviços Oracle e registros equivalentes durante caches. Conferir NS/A/DS em 1.1.1.1 e 8.8.8.8, autoridade do pai e servidores atribuídos; repetir HTTPS com validação normal. Só marcar corte concluído após observação, não apenas por salvar o formulário. Não misturar proxy, cache, certificado, curinga ou deploy.
6. **Plano condicionado à estabilização:** após nova autoridade estável e expiração dos caminhos/caches que ainda apontem aos NS antigos (respeitar horizonte observado e recomendação de transição do provedor), ativar assinatura Cloudflare e cadastrar seu DS exato no Registro.br; validar correspondência DS/DNSKEY, AD e ausência de SERVFAIL. Essa etapa dependia da nova zona e autorização aplicável; não publicar DS novo cedo enquanto validadores ainda pudessem consultar zona antiga incompatível.

## Recuperação

O Registro.br documenta que voltar ao seu DNS só fica disponível quatro horas após a desativação. Sua documentação não garante retenção permanente da zona/chaves; o inventário de dois A permite reconstrução caso necessário, mas não há rollback imediato. Em falha, pausar novas alterações, identificar delegação, DS, cache ou aplicação e preservar o Oracle. Restaurar NS somente se os servidores antigos servirem a zona e forem compatíveis com o DS publicado/em cache, respeitando o bloqueio do provedor. Se DS novo estiver ativo, sua retirada/expiração pode ser necessária antes de restaurar provedor antigo. Não restaurar DS antigo sem verificar a chave correspondente. Registros/destino corretos na Cloudflare permitem corrigir divergências na nova zona sem voltar de provedor, sujeito ao diagnóstico e autorização.

## Evidências da preparação — checkpoint de 05/11/2026

Esta lista registra o estado observado durante a preparação, antes da propagação e da validação DNSSEC. As pendências abaixo foram resolvidas ou atualizadas nas seções posteriores; não representam o estado final da migração.

- Inventário completo e baseline: concluídos por leitura nesta sessão.
- Zona Cloudflare pendente, NS atribuídos e comparação: concluídos, quatro respostas diretas corretas e tabela final persistida como DNS-only / 1 hr.
- Procedimento DNSSEC Registro.br: confirmado na documentação oficial e na mensagem real de transição; retorno ao DNS anterior bloqueado por quatro horas segundo o provedor.
- Aprovação operacional do plano concreto: recebida e operação enviada. Naquele checkpoint, execução pública completa, propagação e DNSSEC novo ainda aguardavam processamento externo/caches; consulte as seções posteriores para os resultados observados.
- Conferência às 16:46 BRT: DNS Google ainda apresentou NS antigos e DS key tag 34215 válidos (Status 0 / AD true); markina continuou HTTP 200 com TLS normal. É estado inicial esperado, não prova de conclusão nem de retirada imediata do DS.
- A consulta direta sem recursão a `a.dns.br` desta estação falhou com erro DNS; não foi tomada como falha pública do domínio. As consultas recursivas independentes anteriores e HTTPS passaram. Repetir autoridade do pai por caminho disponível na validação posterior.
- Nenhum código funcional alterado; política de refatoração avaliada sem limpeza elegível. Sem necessidade de rodar suítes de aplicação para estas alterações documentais.
- Naquele checkpoint, OpenSpec strict e `git diff --check` no escopo passaram; a revisão de integração e a validação final estão registradas nas tasks 3.1 e na seção de 07/11.
- Capturas locais (fora do Git): `C:/codex-data/visualizations/2026/11/05/cloudflare-migration/cloudflare-zone-prepared.jpg` e `registro-cutover-review.jpg` no mesmo diretório.
- Confirmação enviada: `C:/codex-data/visualizations/2026/11/05/cloudflare-migration/registro-transition-started.jpg` mostra NS atribuídos e contagem da transição naquele checkpoint. A espera do provedor foi acompanhada nas seções de retomada; as tasks 2.2–3.1 foram concluídas e têm evidências posteriores.

## Retomada após a espera

**Checkpoint às 19:08 BRT de 05/11/2026:** 1.1.1.1 e 8.8.8.8 já retornam kara/mustafa como NS e A raiz 132.145.193.169; HTTPS markina continua 200. Consulta Google DS: NOERROR sem DS; NS sem AD, esperado durante transição sem cadeia. TTL dos NS novos observado 86400 em 1.1.1.1 e 21600 em Google. Isso comprova delegação nos caminhos consultados, não expiração universal de caches. DNSSEC Cloudflare ainda não foi ativado/publicado: preservar a recomendação de transição de 24 horas do provedor antes de introduzir DS novo incompatível com eventual cache antigo; nova avaliação a partir de 06/11/2026 16:45 BRT, conferindo estado/TTL atuais. Não é autorização para manter DNSSEC desligado indefinidamente. A implementação local de escolha/reserva de subdomínio foi priorizada expressamente pelo proprietário em change independente, sem antecipar wildcard, TLS ou ativação pública.

1. A autorização de 05/11/2026 continua válida: não pedir novamente a mesma troca nem repetir o salvamento sem necessidade. Ler o estado atual do painel e consultar NS/DS/A antes de qualquer mutação.
2. Comparar resolução via 1.1.1.1 e 8.8.8.8 e respostas diretas de kara/mustafa, conferir ausência de SERVFAIL e HTTPS 200 de markina. Capturar TTLs e horário; não confiar apenas em badge de painel.
3. Confirmar Cloudflare ativa e tratar caches antigos antes de publicar o DS novo; ativar DNSSEC na zona, obter somente os dados públicos do DS e cadastrar os valores exatos no Registro.br. Nenhuma chave privada/token é necessário no chat ou no Git.
4. Comprovar cadeia e serviço, registrar evidências e concluir tasks somente após a validação. Se o painel exigir novo login, proprietário faz a autenticação sem enviar senha/código. Não ativar proxy, curinga, WAF, robots.txt ou alterar Oracle nesta retomada.

## Fontes oficiais consultadas em 05/11/2026

- [Cloudflare: full setup e DNSSEC](https://developers.cloudflare.com/dns/zone-setups/full-setup/setup/)
- [Cloudflare: limitações da varredura](https://developers.cloudflare.com/dns/zone-setups/reference/dns-quick-scan/)
- [Cloudflare: curinga](https://developers.cloudflare.com/dns/manage-dns-records/reference/wildcard-dns-records/)
- [Registro.br: características do DNS](https://registro.br/tecnologia/caracteristicas-tecnicas/)
- [Registro.br: DNSSEC obrigatório em seu DNS, item 1.13](https://registro.br/tecnologia/dnssec/dns-e-dnssec/desativar-dnssec/)
- [Registro.br: tutorial DNSSEC v1.8.0, passo 5 (cadastrar KeyTag e Digest)](https://ftp.registro.br/pub/doc/tutorial-dnssec-1.8.0_1.pdf)
- [Registro.br: publicações e consistência na transição](https://registro.br/ajuda/gerenciamento-de-conta/publicacoes-dns/)

## Retomada pública — 07/11/2026, antes de reativar DNSSEC

Consulta somente leitura às 17:56 BRT, sem alterar painel, DNS, registro, serviços ou configurações:

- Cloudflare Resolver `1.1.1.1` e Google DoH/Resolver `8.8.8.8` retornaram `kara.ns.cloudflare.com` e `mustafa.ns.cloudflare.com`. TTL observado dos NS: 86400 s na Cloudflare e 21600 s no Google.
- Os dois resolvers retornaram A de `pickyourpic.com.br` e `markina.pickyourpic.com.br` como `132.145.193.169`, TTL 3600 s. Consultas diretas aos dois NS autoritativos retornaram o mesmo destino para ambos os nomes, TTL 3600 s.
- HTTPS com validação TLS normal: `markina.pickyourpic.com.br` respondeu 200; `pickyourpic.com.br` respondeu 404, igual à referência anterior. Não foi feita transação financeira nem alteração de serviço.
- Consultas DS via Google e Cloudflare DoH retornaram NOERROR sem resposta DS; a prova negativa veio da zona pai `com.br`. `AD=false`, consistente com a janela em que DNSSEC ainda não foi reativado. Não há evidência de SERVFAIL nas consultas/respostas observadas; isso não prova ausência de todos os caches globais.
- A nova autoridade e o destino de produção estão coerentes nos caminhos consultados. O DS Cloudflare continua pendente: é preciso habilitar assinatura na zona Cloudflare, copiar os valores públicos exatos mostrados pelo painel para o Registro.br e então validar DNSSEC por resolvers validadores. Não publicar DS antigo nem ativar curinga, proxy ou novos hosts nesta change.
- O painel Cloudflare está atualmente na tela de login. Nenhuma autenticação foi automatizada. A validação seguinte requer a sessão autenticada do proprietário; não é necessário enviar senha ou código no chat.

## Publicação do DS no Registro.br — 07/11/2026

Às **18:18 BRT**, o Registro.br confirmou a gravação de `DS 1` para `pickyourpic.com.br`, com Keytag `2371` e digest SHA-256 `86045413A35DFE871815A7225772066067969EC3C47198CDBD0CF1B39407FD64`. Os nameservers `kara.ns.cloudflare.com` e `mustafa.ns.cloudflare.com` continuaram configurados. O painel autenticado mostrou o DS salvo após a confirmação.

O Registro.br apresenta somente campos `Keytag` e `Digest`. O tutorial oficial orienta copiar esses dois valores do registro DS (`dsset`) para a interface; foram inseridos os valores correspondentes ao DS 2371 13 2 mostrado pela Cloudflare, sem alterar o algoritmo nem o digest type independentemente.

Às **18:19 BRT**, consultas DNS over HTTPS independentes a Cloudflare e Google ainda retornavam `NOERROR` sem `Answer` DS, uma resposta SOA de `com.br` na autoridade e `AD=false`. Isso é compatível com propagação pendente, mas ainda não comprova a cadeia DNSSEC nem ausência global de caches antigos. A consulta de A a `pickyourpic.com.br` manteve `132.145.193.169` (TTL 3600); `https://markina.pickyourpic.com.br` respondeu HTTP 200 com verificação TLS válida (`ssl_verify_result=0`). Nenhum serviço, destino, proxy ou configuração do Oracle foi alterado.

**Estado observado às 18:19 BRT:** publicação do DS confirmada no painel, mas ainda sem resposta pública DS. Reconsultar DS/AD por resolvers validadores; a Cloudflare informou que a ativação pode levar de dez minutos a uma hora. A validação posterior consta na seção seguinte.

## Validação DNSSEC final — 07/11/2026

Às **18:22 BRT**, a consulta direta ao servidor autoritativo `a.dns.br` retornou `DS 2371 13 2` para `pickyourpic.com.br`, TTL 3600. Cloudflare DoH (`cloudflare-dns.com/dns-query`) e Google DoH (`dns.google/resolve`) retornaram o mesmo DS, ambos com `AD=true` e `Status=0`. Os dois validadores retornaram A para `pickyourpic.com.br` e `markina.pickyourpic.com.br` como `132.145.193.169`, TTL 3600 e `AD=true`. A consulta de DNSKEY pelo resolver Cloudflare apresentou chaves da zona com algoritmo 13. Não houve SERVFAIL nessas consultas.

Checagem HTTPS com validação TLS padrão às 18:22 BRT: `https://markina.pickyourpic.com.br` respondeu HTTP 200 e `https://pickyourpic.com.br` HTTP 404, ambos com `ssl_verify_result=0`; a raiz conserva a resposta histórica. Nameservers, A, TTL e modo DNS-only permaneceram dentro do inventário. Nenhum container, processo, porta, configuração, arquivo, dado ou serviço Oracle foi alterado; nenhuma transação financeira foi executada.

**Resultado:** cadeia DNSSEC observada válida nos dois validadores independentes e DS confirmado pelo pai. Isso é evidência dos caminhos consultados, não garantia de propagação universal em todos os caches.
