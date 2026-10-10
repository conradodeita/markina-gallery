# Inventário e publicação autorizada — 09/10/2026

## Confirmação final — 10/10/2026

Workflow 38047039331 SUCCESS, SHA remoto 3bdc36200ff4a83f4e894c4cc7e4e7dc44f9201c, Git limpo, schema 0072. Treze containers próprios healthy e health interno/público 200. Seis processos enabled=true; API APP_VERSION correto e snapshot read-only configurado. Timer ativo e arquivo privado 0600 fresco. Proprietário/grants revalidados. Os seis containers de terceiros mantêm o fingerprint anterior; portas/subdomínio preservados. Jornada final autenticada e relatórios JSON/texto sanitizados aprovados, sem 429 na abertura/recarga e sem alteração A+B. Task 6.2 concluída; histórico abaixo registra falhas/interrupções anteriores, não pendências atuais. Evidências detalhadas em `validation.md`.

O proprietário autorizou migration, deploy, configuração, indicação inicial de propriedade/grants e validação remota da task 6.2. Pediu pausa enquanto o CI executa, retornando com o resultado.

## Inventário antes do merge

- Servidor autorizado `132.145.193.169`, checkout `/opt/markina-gallery`, projeto Compose `markina-gallery`.
- SHA remoto `d4d000de3b41d4b2c7c96197cfea28b7940c5aea`; Git limpo.
- Origem pública `https://markina-homolog.duckdns.org`; único binding próprio publicado `127.0.0.1:8080` (Nginx). API 8000, web 3000, PostgreSQL 5432 e Redis 6379 internos.
- 13 containers próprios; API e PostgreSQL healthy. Volumes da API: source, derivatives, history, facial-references e branding.
- Filesystem `/dev/sda1`: 194 GiB, 88 GiB usados, 106 GiB disponíveis; interface `enp0s6`, dispositivo `sda`.
- Diretórios privados de backup e estado de deploy existentes, modo 0700, proprietário ubuntu.
- Seis containers de terceiros em execução; fingerprint SHA256 dos IDs curtos ordenados e separados por newline, sem newline final: `c63b9f91cb364f1ee7a2cf26a69b602734b6d8d34eaf363174695128a1c72bc6`. A primeira consulta usou filtro não suportado e foi descartada; fingerprint acima foi obtido por classificação dos labels Docker em Python.

## Plano de impacto apresentado

Fluxo existente `scripts/deploy-homolog.sh`: backup lógico exclusivo Markina; build das imagens alvo; migration aditiva 0072 com breve parada dos escritores próprios prevista pelo fluxo; recriação dos serviços próprios e verificações de saúde. Sem alteração de recursos de terceiros, porta/subdomínio, campanha A+B, limpeza de dados ou carga. Coleta e grants ainda não ativados; proprietário, host e jornadas remotas serão configurados/validados depois da publicação. Downgrade destrutivo não autorizado.

## Merge e pausa

CI do PR `37997734427` aprovado no HEAD `c093eaeba9d058faa1d5991d9329aacb4ee64dae`: 1.289 testes backend aprovados, 20 pulados; regressão PostgreSQL adicional aprovada; frontend, OpenSpec e gitleaks aprovados.

PR #151 mesclado por merge commit `777495b012bb98174e50c07b15dd507b329b8de4`. CI de develop `38000212755` confirmado `in_progress`: https://github.com/conradodeita/markina-gallery/actions/runs/38000212755 . O job deploy-homolog depende desse novo CI e do gate do environment. Não declarar deploy concluído nem task 6.2 validada por causa do merge. Pausar conforme instrução e retomar quando o usuário trouxer o resultado.

Próxima retomada: conferir resultado/deploy remoto e SHA; se houver gate homolog pendente, tratar autorização persistente do proprietário; reconferir saúde e fingerprint de terceiros; indicar proprietário por UUID/e-mail confirmado e grants; configurar overlay e snapshot privado de host; validar coleta/SQL e jornadas remotas sintéticas. Nenhum segredo foi lido ou registrado neste inventário.

## Publicação e ativação verificadas

Workflow `38000212755` SUCCESS, incluindo deploy-homolog. Oracle confirmado no SHA `777495b012bb98174e50c07b15dd507b329b8de4`, schema `20261009_0072`, checkout limpo e 13 containers próprios healthy. Conta proprietária indicada por UUID/e-mail confirmado recebeu metrics/tree/incidents/export, com referência auditada `owner-approved-monitor-20261009`.

Snapshot de host: timer exclusivo `markina-gallery-system-monitor-host.timer`, 60 s; diretório `/var/lib/markina-gallery/system-monitor` 0700, `host.json` 0600; bind somente leitura na API. Interface enp0s6, dispositivo sda, filesystem /. Host usa Python 3.8.10; a primeira execução falhou por import de datetime.UTC, corrigido para timezone.utc. Coletor corrigido standalone em deploy-state, SHA256 `74a8163329c79a036b9d6be70d413de8fb5af1a344f973173c7ab537c28ee3c9`, conferido entre cópia local e servidor. A criação inicial do diretório exigiu sudo porque seu pai pertence a root; diretório dedicado criado com proprietário ubuntu e modo 0700.

Overlay privado 0600 habilita seis processos. Após recriar API/workers, o upstream Nginx antigo respondeu 502; recriado somente Nginx próprio com os mesmos arquivos/configuração. Health interno e público voltaram a 200. Os seis serviços ativados foram confirmados enabled=true e healthy. Fingerprint dos seis containers de terceiros continua idêntico ao inventário anterior.

SQL/relatório e negação anônima verificados; proprietário autenticou-se normalmente no navegador. Árvore, filtros/busca, card e duas exportações efetivas foram exercitados, sem extrair senha/TOTP/cookie, fabricar sessão ou alterar tabelas de campanha. Falha 429 da abertura inicial foi delimitada em três consultas concorrentes contra duas leituras permitidas; atualização manual recuperou a árvore. Correção da coordenação no frontend reproduzida/validada por teste; exige nova publicação e repetição remota. O ajuste reutilizável do wrapper de deploy preserva ambos os overlays e identifica APP_VERSION pelo checkout real; sua publicação será feita via PR/CI junto com compatibilidade Python 3.8 e correção da interface. A task 6.2 permanece aberta até publicação e validação da nova versão.
