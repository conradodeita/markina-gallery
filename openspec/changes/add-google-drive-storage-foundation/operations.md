# Operação — preparação para conexão real do Drive

## Status — 03/11/2026

Inventário remoto de leitura autorizado pelo proprietário ao fornecer acesso SSH. DNS do domínio raiz salvo sob a orientação de usar o mesmo servidor Oracle, com confirmação de sucesso no Registro.br e resposta pública A. Após pedido de continuidade e entrada do proprietário no painel NPM, foi emitido certificado exclusivo do domínio raiz e criado host reservado 404 com HTTPS obrigatório. Detalhes no checkpoint abaixo. Não houve deploy de aplicação, migration, alteração de segredos ou chamada real Drive.

Condição posterior do proprietário para o release: produção atende clientes e deve permanecer ativa. Não desligar ou suspender serviços, tenants, uploads, jobs, mensagens ou fluxos de pagamento no plano padrão. Qualquer indisponibilidade temporária necessária exige descrição prévia de alcance, duração, janela e retorno, seguida de consentimento específico; sem ele, não executar a etapa. O contrato TOTP `0093` pode bloquear escritas de autenticação e não entra em `upgrade head` automático. Ver `release-readiness.md`.

## Checkpoint HTTPS concluído — 03/11/2026, aproximadamente 22:14 GMT-3

- Emissão pelo formulário Certificates → Let's Encrypt via HTTP do NPM autenticado. Domínio único `pickyourpic.com.br`, ECDSA 256; teste do painel confirmou alcance HTTP antes de emitir. O formulário não pediu novo aceite de termos nem novo e-mail.
- Certificado `npm-4`, SAN `pickyourpic.com.br`, validade UTC `2026-11-04 00:13:55` a `2027-02-02 00:13:54`. Não foram lidas chaves privadas.
- Criado **404 Host** próprio, configuração `/data/nginx/dead_host/1.conf`, `server_name pickyourpic.com.br`, portas existentes 80/443, certificado `npm-4` e Force SSL; HSTS não foi habilitado. Não é proxy para a aplicação e não publica cadastro ou OAuth. Essa reserva permite concluir TLS sem expor o conjunto SaaS incompleto.
- Verificação externa ao servidor, com resolução direta para o IP: HTTPS 404 com validação normal de certificado; HTTP 301 para a mesma URL HTTPS. `markina.pickyourpic.com.br` continuou HTTP 200. `nginx -t` no NPM passou. Nenhum restart de container, alteração de redes/firewall, schema ou secrets ocorreu. NPM aplicou a configuração pelo fluxo normal da interface.
- O inventário abaixo descreve o estado anterior à preparação HTTPS; a falha TLS foi resolvida. Para publicar posteriormente a aplicação, será necessário substituir deliberadamente a reserva 404 pela rota aprovada, preservando o certificado e evitando conflito de server_name. Não criar simultaneamente proxy host ativo e 404 host ativo para o mesmo domínio.
- Retorno da preparação HTTPS, se necessário: desabilitar somente o 404 Host 1 pelo NPM; preservar certificado e hosts legados. Não apagar recursos ou revogar certificado sem autorização. Retorno de código/schema SaaS continua separado e ainda não foi executado.

## Inventário observado

| Recurso | Evidência | Limite |
| --- | --- | --- |
| Domínio raiz | `pickyourpic.com.br` A `132.145.193.169`, retornado pelo Google Public DNS após salvar no Registro.br | Não comprova atualização de todos os resolvedores nem HTTPS |
| Domínio existente | `markina.pickyourpic.com.br` A para o mesmo IP; HEAD HTTPS respondeu HTTP 200 | Preservar rota e certificado vigentes |
| Proxy público | `nginx-proxy-manager`, imagem `sha256:bd94715ff0d6f11047446b2c149d4adb45deaa8e18152b34befb13945b3dbd7b`, portas 80/81/443 publicadas | Recurso compartilhado, incluindo redes de outro projeto; não reiniciar/recriar ou alterar configurações globais |
| Host existente do produto | `/data/nginx/proxy_host/3.conf`: `server_name markina.pickyourpic.com.br`, upstream HTTP `markina-homolog-nginx:80` | O nome do alias não prova ambiente de homologação |
| Alias do upstream | O nginx `markina-gallery-nginx-1` tem alias `markina-homolog-nginx` em `npm-network`; NPM também pertence à rede | Confirma destino observado, não autoriza alterar redes |
| Nginx do produto | `sha256:96868d9fa38f469a86d2f25787e43ee9ad330339d30be260aa9f5a338bb03751`; porta publicada `127.0.0.1:8080 → 80` | Não abrir nova porta pública |
| API | `sha256:6e732610932d5e7eb01c1fbed5ddbc7a1f4b05a39da9de8179c0ed0ab8375aea`, porta interna 8000; `find_spec('app.google_drive_oauth')` retornou ausente | Código OAuth local ainda não está nessa imagem; label de revisão OCI estava vazia |
| Web | `sha256:4e8177c0658b5378845af7816444d6529baff46adaefd5fdb9b119be1ac25027`, porta interna 3000 | Label de revisão OCI estava vazia; cadastro novo não foi validado nesse runtime |
| Certificado público atual | SAN somente `markina.pickyourpic.com.br`, validade de 13/10/2026 a 11/01/2027 | Foi lido apenas o certificado público; chave privada não foi lida |
| HTTPS raiz | HEAD com resolução direta para o IP falhou na negociação TLS (`SEC_E_ILLEGAL_MESSAGE`) | Não contornar validação de certificado; causa interna ainda não comprovada |

Os containers do produto retornados por `docker ps` estavam saudáveis. Há outros projetos no host, que não foram alterados. Banco, schema, configurações de integração e segredos não foram lidos. Os IDs de imagem não substituem commit, CI e manifesto de release.

## Plano de impacto para revisão

1. Preparar release reproduzível a partir do código revisado, com SHA, CI e imagem candidata, inventário de schema e compatibilidade da migration 0098. A imagem atual não pode atender o callback OAuth só com DNS/certificado. O diff SaaS local inclui outras mudanças; não publicar esse conjunto por inferência ou selecionar arquivos avulsos sem provar dependências.
2. Para o domínio raiz, propor host próprio no NPM usando somente portas públicas já existentes 80/443 e o upstream do produto confirmado; preparar certificado próprio para `pickyourpic.com.br`, sem modificar o host 3 ou o certificado de `markina`. Rever quais rotas do site raiz serão efetivamente publicadas antes de salvar o proxy. Não ativar cadastro público enquanto os gates de `add-photographer-signup-portal` estiverem pendentes.
3. Antes da execução, apresentar ao proprietário a configuração exata, imagens/SHA/schema, escopo de cada migration, sequência que preserve atendimento e plano de retorno. Obter autorização específica de produção para release, migrations e secrets conforme as ações necessárias. Qualquer interrupção temporária exige consentimento próprio após informar alcance, duração e janela; o acesso SSH fornecido autorizou o inventário, não essas escritas.
4. Em execução autorizada e com continuidade demonstrada, preservar a imagem/configuração saudável como referência e limitar alterações ao produto. Validar configuração antes de aplicar; comparar disponibilidade e jornadas de cliente de `markina` antes, durante e depois. Se a capacidade simultânea ou uma migration bloquear essas jornadas, parar antes da etapa e pedir o consentimento específico. Não reiniciar NPM, usar `compose down`, mexer em certificados de terceiros ou alterar DNS adicional.
5. Guardar client ID/secret e configuração de cifra apenas no mecanismo seguro aprovado, sem copiar material ao repositório/chat. Confirmar callback HTTPS exato, sessão owner e rotas publicadas antes do consentimento Google.
6. Voltar configuração do novo host e imagem apenas por procedimento compatível com o schema quando houver falha; não fazer downgrade destrutivo de banco, apagar volumes ou alterar o host existente. A política de recuperação de segredo/consentimento deve ser aprovada antes do ensaio.

## Critério de parada atual

Revisão posterior em `release-readiness.md`: schema real `0090`; cadeia até `0098` inclui contract TOTP `0093`; a base SaaS local está atrás do `main` remoto e contém dependências além de Drive. O callback raiz requer sessão owner criada no mesmo host. Esses fatos impedem tratar o OAuth como patch isolado ou executar upgrade head por inferência. Preparação TLS foi concluída pelo NPM autenticado pelo proprietário. O túnel administrativo temporário foi encerrado após a configuração; será necessária nova sessão de túnel para outro acesso ao painel.

DNS e TLS raiz concluídos; host raiz responde 404 de propósito. Backend OAuth publicado, candidato revisado de release, plano de migração TOTP, secrets e consentimento continuam ausentes. Não publicar o diff SaaS, executar upgrade head ou iniciar consentimento por inferência. Tasks 1.1 e 3.1 permanecem abertas.

## Atualização de metadados do runtime — 06/11/2026

Consulta SSH read-only posterior ao inventário HTTPS, limitada a timers systemd, containers/imagens/status/portas publicadas, nomes de volumes e nomes de arquivos cron. A evidência detalhada e os limites estão em `../add-platform-backup-recovery/inventory.md`. Markina estava em execução e sem alteração; NPM publicou 80–81/443, enquanto o Nginx do produto permanecia em `127.0.0.1:8080→80`. O `oracle-project-backups.service` terminou com status 1 em 06/11. Filtros processaram 14 entradas do journal e encontraram duas ocorrências de `RuntimeError`/`interrupted candidate needs reconciliation`. A leitura autorizada e filtrada de `backup()` localizou a comparação do conjunto remoto `entries` com o esperado `old`, sem atribuir o candidato ou explicar a divergência. Isso não prova backup SaaS restaurável.

Essa consulta não revalidou schema, imagem por digest/SHA, configuração de callback, secret store, firewall ou runtime OAuth. Apenas o recorte do journal descrito acima foi processado pelo filtro local; mensagens brutas não foram exibidas/salvas. Não foram lidos variáveis de ambiente, arquivos de configuração, mounts, conteúdo de backup ou dados. Nenhuma operação de produção foi alterada; não houve deploy, migration, parada/restart de serviço, mudança de volume ou chamada Drive.
