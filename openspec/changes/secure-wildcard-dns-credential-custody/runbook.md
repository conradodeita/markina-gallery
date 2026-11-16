# Runbook — protótipo sintético de custódia DNS-01

## Alcance e responsáveis

Esta change implementa um protótipo local, não uma instalação operacional. Não há cliente ACME real, token real, timer ou helper privilegiado de produção. O operador do laboratório prepara os diretórios fixos e liga os callbacks; o transporte sintético recebe somente o caminho temporário da credencial. O instalador recebe somente o bundle e o destino fixado na construção. Não fornecer API administrativa NPM, socket Docker ou shell ao emissor.

Antes de aplicação externa: revisão humana do mecanismo, inventário atualizado, autorização específica e prova de continuidade. A conclusão desta change não libera as tasks 3.3/3.4 do ingresso. Raiz e markina conservam seus certificados/hosts próprios. Não fazer fallback para upload nativo da chave ou token no SQLite.

## Contratos e caminhos fixos do laboratório

- `scripts/wildcard_certificate_custody.py`: biblioteca sem CLI e sem rede. Recusa Windows, raiz relativa, symlinks de raiz e diretório sem marcador `.pyp-wildcard-lab` com conteúdo `pyp-wildcard-synthetic-only-v1`, proprietário atual e modo 0700.
- `SyntheticVault`: referência UUID, token obrigatoriamente `synthetic-*`, chave AES-GCM injetada em memória e contexto exclusivo `wildcard-dns-lab-v1`. Arquivo cifrado `<UUID>.json` 0600, com validade protegida pelo envelope e referência autenticada. Não grava a chave de cifragem.
- Credencial temporária: subdiretório `credential-*` 0700 e `cloudflare.ini` 0600; o transporte recebe apenas seu caminho. O contexto remove o arquivo/diretório em sucesso e falha, antes de instalar o certificado. Falha é reportada por código sanitizado, sem exceção original.
- `SyntheticInstaller`: diretório fixo `/data/pyp-wildcard-certificates` no NPM descartável. Releases `release-<SHA256>` 0700, `fullchain.pem` e `privkey.pem` 0600. Lock exclusivo `.install.lock` e links relativos `current`/`previous`; não aceita destino em uma requisição.
- Validação deliberadamente sintética: cadeia de dois certificados (folha e CA de teste confiável), assinaturas, CA válida, folha não-CA, SAN único exatamente `*.pickyourpic.com.br`, chave correspondente, início válido e mais de sete dias restantes. Isso não implementa a política de cadeia intermediária de uma CA pública.
- Runner `scripts/wildcard_npm_lab.py`: exige versão 2.15.1, ambiente explícito `PYP_WILDCARD_LAB=synthetic-network-none`, ausência de rota padrão e banco sem usuários/hosts. Inicializa somente dados sintéticos via API nativa. Não repetir contra banco preenchido.

O runner configura somente seus três hosts descartáveis via `advanced_config`. O wildcard aponta para `current`; raiz e markina têm bundles de referência separados. O host usa `certificate_id=0`, sem certificado/renovador nativo. A interface NPM não exibirá um certificado nativo para esse host: a confirmação real é o probe TLS, não o indicador de SSL da UI.

Os únicos comandos dos callbacks são `nginx -t` e `nginx -s reload`, com argumentos literais, dentro do container descartável. Eles não são uma interface privilegiada exportada pelo protótipo. Não há comandos de parada ou desativação de hosts no fluxo de renovação.

## Repetição dos testes locais

1. Inventariar contexto Docker, containers, portas, mounts e espaço livre. Usar `desktop-linux` somente se confirmado local; preservar os recursos preexistentes. Não usar Compose, prune ou portas publicadas para este ensaio.
2. Usar o índice NPM fixo e a plataforma ARM64 de `feasibility.md`; conferir manifest e config digest. Rodar os oito testes unittest com `/opt/certbot/bin/python3 -B -m unittest discover -s /repo/scripts -p test_wildcard_certificate_custody.py -v` em container descartável `--network none --read-only`, tmpfs `/tmp` e binds somente dos dois scripts e `backend/app/integration_secrets.py`, todos readonly. Não montar o repositório inteiro ou `.env`.
3. Para integração, criar container **próprio** rotulado `pyp.lab=wildcard-custody`, sem rede/portas/socket, com `/data`, `/etc/letsencrypt` e `/tmp` em tmpfs. Copiar apenas os três scripts e `integration_secrets.py` para `/lab`. O consumidor NPM não monta o cofre do teste unitário e não recebe credencial DNS.
4. Nesta execução, uma chave JWT administrativa exclusivamente sintética foi gerada localmente em arquivo temporário e montada readonly em `/data/keys.json`, no formato nativo `{key,pub}`. Isso evita a geração RSA lenta sob emulação ARM64; não altera a imagem nem constitui configuração operacional. Nenhuma chave sai no relatório.
5. Executar o runner com o ambiente explícito e Python do Certbot. Ele espera a API local, cria hosts, verifica TLS/SNI/cadeia/hostname, renova, repete o bundle e força falha no probe para testar retorno. O recibo sanitizado fica em `/tmp/pyp-wildcard-lab-result.json`; não usar um resultado de tentativa anterior como prova de outra execução.
6. Inspecionar o recibo e somente metadata necessária. Conferir tabela `certificate` vazia e ausência de token/chave privada nos arquivos SQLite/logs. O runner não imprime respostas autenticadas da API nem PEM.
7. Antes de remover o laboratório, conferir nome, label e `NetworkMode=none`. Parar/remover somente o container próprio; os tmpfs são descartados. Resolver e conferir o arquivo JWT sintético dentro do diretório temporário `pyp-wildcard-*`, apagar somente esse arquivo e o diretório vazio. Não remover imagem/cache compartilhados.

## Falhas e recuperação

Falha de transporte encerra a materialização e não altera o certificado. Bundle inválido é recusado antes da troca. Configuração, reload ou probe que falhe restaura o link anterior, repete check/reload e verifica seu fingerprint. Repetir o mesmo bundle saudável não recarrega o Nginx. A exclusão mútua impede duas instalações concorrentes. A biblioteca não expurga releases.

`recovery_failed` significa que a referência anterior foi restaurada no filesystem, mas sua saúde não foi comprovada. Não reportar sucesso nem tentar operações amplas. O laboratório é descartável; interromper sua promoção e investigar. Não improvisar retorno em produção a partir desses comandos.

O ensaio cobre falhas síncronas e concorrência, não crash/power-loss do host ou perda do volume. A chave do cofre só existe em memória no teste; recriar o laboratório exige gerar nova chave/credencial sintética, não recuperar segredo real. Custódia offline, rotação/revogação, restauração do store e segregação por identidades reais continuam gates operacionais, não fatos validados por este protótipo.

## Gates para qualquer operação real

- Revisar cliente ACME/plugin, versões/transitivos/licenças e validar cadeia pública real. Certbot 5.6.0 é candidato inventariado, não executor desta change.
- Escolher/provar loader cifrado e recuperação no servidor. Não concluir suporte systemd pela documentação ou por AES-GCM em laboratório. Store, chave e backups devem ter custódias separadas e acesso restrito, sem cofre/token montados no NPM.
- Revisar e testar interface operacional entre identidades distintas do emissor/instalador, com destino/comandos fixos, permissões mínimas e sem acesso Docker do emissor. Callbacks Python do laboratório não substituem essa fronteira.
- Só então solicitar token Cloudflare mínimo para a zona autorizada; não enviar token no chat ou persistir em tabela comum. Criar/configurar credencial real exige autorização específica.
- Inventariar DNS/DNSSEC, NPM, certificados, upstream, redes/portas e estado saudável anterior; apresentar impacto/retorno e obter autorização para cada aplicação externa. Provar renovação e continuidade sob o runtime real antes de ativar ingressos.
- Manter um único renovador do wildcard. Não criar LE nativo concorrente. Sem consentimento específico para interrupção, qualquer mecanismo que a exija permanece bloqueado.

Não houve publicação, emissão ACME, desafio DNS, timer real, alteração do Oracle ou mudança nos serviços existentes por esta change.

## Continuidade operacional — 08/11/2026

Uma nova consulta read-only confirmou systemd 249 no Oracle e `systemd-creds` ausente no PATH. A referência a systemd 255 deste estudo não equivale à compatibilidade do destino. A proposta `../prepare-operational-wildcard-certificate-issuer/` prepara loader, emissor e instalador compatíveis, com provas locais e revisão humana antes da implementação. Ela não modifica este laboratório nem libera instalação externa. O DNS A wildcard foi concluído separadamente na task 3.2 do ingresso; certificado e rota permanecem pendentes.
