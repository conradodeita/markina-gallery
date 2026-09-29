# Proposal

## Why

Na retomada controlada de 2026-09-29, `docker compose start` tentou iniciar a dependência one-shot `migrate` usando uma imagem antiga que não continha a revisão ativa `20260929_0069`. O banco permaneceu na revisão correta e a aplicação foi recuperada por início direto dos contêineres; falta um caminho documentado e testado para reiniciar somente os serviços da aplicação sem disparar migration implicitamente.

## What Changes

- Definir o contrato de retomada dos serviços da aplicação sem executar migration, limpeza de dados, recriação de recursos persistentes ou reinício da Evolution e dos projetos vizinhos.
- Ajustar o procedimento versionado de recuperação para iniciar os serviços existentes sem seguir dependências one-shot antigas, verificar saúde de todos os serviços ativados e confirmar as rotas locais e públicas.
- Cobrir por testes a recusa de revisão/configuração incompatível e a garantia de que o caminho de retomada não chama Alembic nem inicia o serviço `migrate`.
- Registrar evidência de validação controlada e deixar explícito que migration é operação separada do reinício.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `deployment-operations`: retomada controlada da aplicação sem execução implícita de migration one-shot.

## Impact

- `scripts/deploy-homolog.sh` e seus testes de política/execução.
- `docker/docker-compose.yml` e override de workers somente se a análise confirmar que a definição atual impede um caminho seguro de retomada; não alterar dependências sem preservar o fluxo de primeira inicialização.
- Procedimentos operacionais de deploy e recuperação, OpenSpec e validação local/sintética. A mudança não autoriza operação remota, migration, alteração de segredos ou interrupção de homologação.
