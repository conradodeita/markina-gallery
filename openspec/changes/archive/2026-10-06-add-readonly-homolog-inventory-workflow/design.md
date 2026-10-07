## Contexto

O workflow de manutenção atual oferece `inventory` e `execute` no mesmo caminho SSH. A consulta precisa estar disponível no branch padrão do GitHub para ser disparada antes da aprovação de deploy, sem tornar um modo destrutivo selecionável nessa interface.

## Decisões

1. Criar workflow `workflow_dispatch` dedicado, com execução aceita apenas quando `github.ref` for `refs/heads/main`, `permissions: contents: read` e environment `homolog`.
2. Exigir SHA hexadecimal de 40 caracteres e passá-lo como argumento validado, nunca interpolado como comando. No servidor, verificar primeiro `git rev-parse HEAD` em `/opt/markina-gallery`; divergência encerra o processo antes de qualquer consulta.
3. Usar somente `docker compose --env-file docker/.env.homolog -p markina-gallery -f docker/docker-compose.yml` e executar todas as consultas de aplicação em um único container transitório `run --rm --no-deps`. O projeto, paths e arquivo Compose são constantes do script, não inputs. Antes de ler dados, validar que apenas nginx publica porta e que volumes de banco, Redis, mídia e marca têm nomes exclusivos `markina-gallery_*` e não são externos.
4. Fazer consultas agregadas de banco e filas. Não imprimir resultados de linhas, logs de aplicação, conteúdo de configuração, valores do `.env`, payloads Redis nem identificadores de cliente/foto.
5. Ler estado de containers, portas publicadas e health checks com Compose/Docker; ler capacidade do filesystem do projeto com `df`; depois que o SHA remoto for validado, consultar os endpoints públicos de saúde no runner do Actions sem autenticação, registrando somente códigos HTTP.
6. Manter este workflow e seu script separados de `maintenance-homolog.yml`, cujo modo `execute` tem finalidade destrutiva.

## Segurança e privacidade

- O workflow valida os cinco secrets SSH, escreve chave e known_hosts em arquivos temporários com permissão restrita e os remove ao terminar.
- SSH SHALL usar `BatchMode=yes`, `StrictHostKeyChecking=yes` e `UserKnownHostsFile` apontando para os hosts aprovados.
- A entrada de SHA não poderá conter argumentos shell; o script remoto também validará sua forma.
- Consultas à aplicação devem usar a imagem/serviço já definido pelo projeto, sem iniciar dependências (`--no-deps`) e sem publicar portas.
- Qualquer informação inesperada ou falha de comando interrompe o inventário (`set -Eeuo pipefail`); não haverá fallback que altere o ambiente.

## Validação

- Validar sintaxe Bash do script e do trecho de execução do workflow.
- Testar SHA inválido e divergente, confirmando que a execução para antes de invocar consultas Docker.
- Inspecionar o workflow/script para garantir ausência de comandos de mutação e escopo fixo do Compose.
- Executar validação estrita OpenSpec e os testes de política adicionados.
- O dispatch real será executado após a PR chegar a `main`; esse resultado operacional não autoriza merge/deploy da PR #139.
