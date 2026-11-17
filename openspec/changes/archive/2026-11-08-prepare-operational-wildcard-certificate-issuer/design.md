# Design

## Context

Ver `proposal.md`, os deltas e runbook de `secure-wildcard-dns-credential-custody` e o inventário de `enable-tenant-subdomain-ingress`. O novo DNS não fornece TLS/rota. O NPM compartilhado continua fora da instalação local. A prova anterior não possui loader, cliente ACME ou helper operacional.

Consulta SSH sem elevação em 08/11/2026: Linux 6.8.0-1062-oracle aarch64, systemd `249.11-0ubuntu3.23`, `systemd-run` em `/usr/bin/systemd-run`; `systemd-creds` não encontrado. `command -v certbot` não retornou caminho no PATH do usuário, o que não contradiz o Certbot interno do NPM. `/` com 132 GiB disponíveis e `/run` tmpfs de 2,4 GiB. `getent passwd pyp-acme` não retornou entrada; não prova ausência de outras identidades. O comando composto terminou em 1 por essa ausência. Não houve `sudo`, criação de usuário, unit transitória, leitura de segredo ou modificação no servidor.

## Goals / Non-Goals

**Goals:** pacote operacional local auditável para ARM64/systemd 249, reaproveitando a cifra existente sem compartilhar a chave da aplicação; identidades emissor/instalador separadas e recuperação demonstrável.

**Non-Goals:** upgrade de SO/systemd, configuração real de token/segredos, instalação no Oracle, emissão pública, DNS TXT real, timer ativo, rota NPM ou ativação de tenant. Não afrouxar marcadores, restrições sintéticas ou validação dos scripts anteriores.

## Decisions

1. **Loader compatível:** candidato `LoadCredential=` nativo do systemd 249 para entregar ao emissor uma chave de envelope exclusiva. Token em cofre AES-GCM separado, reutilizando `IntegrationCipher.from_explicit_context` com novo contexto operacional. Chave mestra root-only, separada do cofre e das cópias do token; nunca no banco NPM, env, argumentos ou logs. Caminhos candidatos fixos: chave em `/etc/pyp-acme-issuer/`, cofre em `/var/lib/pyp-acme-issuer/`, material efêmero em diretório privado de `/run/pyp-acme-issuer/`. Não criar esses caminhos no Oracle nesta change. `LoadCredential=` não cifra a fonte: a proteção da chave é uma custódia própria, não consequência do nome da diretiva. Acesso root comprometido ou obtenção conjunta da chave e do cofre permite decifrar; não prometer proteção contra esse cenário. Exigir backup offline da chave sob custódia do proprietário separado do backup do cofre, restauração e rotação antes de uso real. Rejeitar automaticamente o candidato se as permissões, segregação ou recuperação não forem comprovadas. `systemd-creds`/`LoadCredentialEncrypted=` são rejeitados como premissa do host atual; atualização global e serviço externo de segredos ficam fora do escopo.
2. **Emissor separado:** candidato Certbot e plugin Cloudflare 5.6.0, inventariados anteriormente, isolados do runtime NPM/app. Fixar versões, transitivos, hashes/licenças e runtime ARM64 antes de implementar o adaptador. Sem instalação dinâmica no NPM. Um renovador exclusivo; autorização operacional futura limita SAN a `*.pickyourpic.com.br` e token a DNS Edit na zona necessária. CLI recebe somente caminhos; INI temporário 0600 removido em sucesso/falha, dumps desabilitados e saída sanitizada. Não assumir que `/run` tmpfs exclui swap; comprovar política de memória/swap no laboratório e exigir inventário equivalente antes da aplicação.
3. **Instalador privilegiado estreito:** emissor sem grupo/socket Docker e sem API administrativa NPM. Helper distinto recebe apenas bundle limitado e pedido de instalação para destino fixo; autentica identidade do peer e recusa nomes, caminhos, comandos, container ou destino fornecidos pelo cliente. Caminhos operacionais, ownership e checks de symlink/TOCTOU serão fixados no pacote revisado. Somente o helper administra o destino; transporte não cria scripts/hooks executáveis. A integração candidata permite apenas validação Nginx, reload gracioso e probe TLS com comandos literais para o NPM inventariado; mudança de identidade/digest/rotas bloqueia antes da ação. A preparação do novo host wildcard pertence à task 3.4 do ingresso, após runtime autorizado; o helper não cria rota por conta própria.
4. **Validação e recuperação:** validar cadeia completa com trust store fixado, hostname, SAN exclusivo, EKU/KeyUsage, validade e chave correspondente; não reutilizar a suposição sintética de cadeia de dois certificados. Troca atômica com lock e referência anterior; persistência com fsync e estados reconciliáveis após crash. Falha ou renovação concorrente preserva referência saudável; rollback exige novo probe e não presume sucesso de reload. Não expurgar releases automaticamente. Recusa de emissão mantém certificado vigente e gera estado sanitizado de falha/expiração para o operador.
5. **Laboratório:** somente credenciais e CA/DNS sintéticos, sem egress público. Provar separação real de UIDs, reinício, restauração da chave/cofre e comportamento de units no systemd 249 em ambiente descartável; mocks não comprovam esses pontos. Inventariar infraestrutura local antes de escolher container/VM próprio. Se não houver executor compatível, registrar bloqueio; não usar o Oracle como laboratório nem iniciar helpers remotos. O cliente ACME pode ter contratos exercitados com transporte simulado, mas isso não será chamado de emissão pública/renovação real.
6. **Manutenção proporcional:** avaliar reutilização de `IntegrationCipher`, validação de bundle e primitivas de instalação do protótipo; qualquer extração preserva os consumidores sintéticos e seus testes. Não duplicar cifra nem alterar scripts existentes apenas para remover restrições. Código operacional novo não será chamado pela aplicação enquanto não houver release próprio.

### Detalhamento da interface operacional local — 08/11/2026

O adaptador privilegiado candidato valida ID imutável do container `nginx-proxy-manager`, image ID inventariado e SHA-256 de uma lista fixa de arquivos do helper antes de chamar `docker exec` por ID, nunca por um destino escolhido pelo peer. A operação interna usa somente `/data/pyp-wildcard-helper/` para código/trust público e `/data/pyp-wildcard-certificates/` para releases; certificados e token não entram no SQLite. O payload stdin contém apenas bundle, com limite; comandos e paths vêm do código protegido. Não há shell. O emissor chama socket Unix autenticado por SO_PEERCRED e não recebe Docker/API NPM. O provisionamento futuro desses arquivos é uma escrita externa específica que continua sem autorização. O renovador deverá ler o material do Certbot sob sua raiz privada e enviá-lo ao helper, sem tratar o resultado da emissão como instalação concluída. Antes/depois da troca, o helper verifica TLS e resposta dos hosts exatos, além do fingerprint wildcard. O pacote será entregue inativo e não inicia timer/serviço ao ser renderizado.

## Risks / Trade-offs

- [Chave disponível no host para renovação automática] → acesso root é fronteira de confiança explícita; caminhos e backups segregados, permissões comprovadas, recovery offline e rotação; revisão humana do mecanismo antes de uso real.
- [Helper com acesso privilegiado ao proxy compartilhado] → interface fixa, autenticação do peer, validação de identidade/configuração, testes negativos e continuidade dos hosts de referência. Sem comandos arbitrários nem credencial Docker no emissor.
- [Crash/reboot e expiração silenciosa] → estados recuperáveis, testes de interrupção e falha fechada com aviso operacional; não apagar o último certificado válido.
- [Laboratório não equivale à produção] → pacote distingue cada prova local, simulação, lacuna e operação externa pendente. Root/markina existentes não são substituídos nem reiniciados para testar.

## Migration Plan

Esta change entrega somente pacote local. Sequência futura, sujeita a autorização por operação: rever inventário e recovery; apresentar arquivos/hashes/identidades/permissões; preparar store e token seguro; emitir certificado antes de qualquer rota; ensaiar renovação; depois tratar rota/runtime na change de ingresso. Sem consentimento para interrupção, um mecanismo que precise dela é recusado. Rollback futuro limita-se aos recursos novos aprovados; não inclui downgrade do SO, troca do NPM ou restauração ampla de banco.

## Sources

Consultadas em 08/11/2026:

- [systemd v249, Credentials](https://raw.githubusercontent.com/systemd/systemd/v249/man/systemd.exec.xml): `LoadCredential=` entrega fonte arquivo/socket à unidade; não declara cifragem da origem.
- [systemd v250, systemd-creds](https://raw.githubusercontent.com/systemd/systemd/v250/man/systemd-creds.xml): referência ao mecanismo de credenciais cifradas; não é prova de suporte no Oracle 249.
- [Plugin Cloudflare do Certbot](https://certbot-dns-cloudflare.readthedocs.io/en/stable/): token limitado à zona, arquivo INI e proteção de permissões; não seguir o fallback de Global API Key.
- As páginas HTML do freedesktop falharam por timeout; fontes XML oficiais versionadas foram consultadas em substituição. Não houve download/instalação de binário ou pacote.
