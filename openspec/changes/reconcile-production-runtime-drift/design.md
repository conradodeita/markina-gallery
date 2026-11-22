# Design

## Context

O HEAD consultado no checkout do servidor é `0dd015a62447e0c8d4c6af16b381140c8118f2ec`. O container saudável da API reporta `APP_VERSION=74f61300e7a818d1605afda3db1d07574c443110`; o worker saudável reporta `APP_VERSION=c1944189761799be96eeeb921cad9906484d8b09`. O `git ls-remote` confirmou o `main` remoto em `6af538ecd5c46da7691fa973c33869f263945a25`. Hashes dos 144 módulos `app/**/*.py` de cada container foram comparados com blobs Git de `main`: API 141/144 coincidem; worker 135/144 coincidem. Os três módulos diferentes na API coincidem com os blobs de `0dd015a`; o worker coincide integralmente com seu próprio `APP_VERSION`, mas difere de `main` em nove módulos. `backend/app/auth.py`, incluindo o modelo `AdminUser.totp_secret`, coincide com `main`.

Os diffs são materialmente relevantes. Na API, `integration_secrets.py` em runtime exige que `INTEGRATION_SECRET_ENV` corresponda a `APP_ENV`; `main` também preserva essa restrição via `_configure` e adiciona contextos explícitos e keyring imutável. `facial/crypto.py` em runtime valida menos tipos e não contém `FacialCryptoContext`; `main` adiciona validação e contextos vinculados a ambiente. `facial/reference_store.py` em runtime cria o diretório antes da gravação e persiste a referência antes de cifrar o locator; `main` valida escopos/cifra antes de criar diretório. No worker, os nove módulos divergentes são `integration_secrets.py`, `main.py`, `auth.py`, `storage_metrics.py`, `folder_processing.py`, `folder_processing_api.py`, `facial/reference_store.py`, `facial/crypto.py` e `preview_adjustment/api.py`. A revisão local indica mudanças de consultas agregadas, validação/caching delimitados por tenant e limite de força de prévia de 75 no worker versus 100 em `main`; qualquer implantação precisa validar compatibilidade entre API e worker. Não há evidência aqui de falha observada em produção.

## Decisions

1. Usar o `main` remoto confirmado em `6af538` como base de trabalho. Os seis commits posteriores a `74f613` são documentação e ferramentas controladas de release; não há motivo para retroceder a base.
2. A proteção `INTEGRATION_SECRET_ENV == APP_ENV` permanece no `main` por validação em `_configure`; a versão de `main` também conserva o keyring imutável e os contextos explícitos usados pelo fluxo de transição.
3. A versão de `main` conserva validação mais estrita do keyring facial. A referência armazenada valida escopos/cifra antes de criar o diretório, preservando o fluxo normal e falhando sem escrita quando o escopo é inválido; isso é confirmado por testes sintéticos existentes. Não enfraquecer essa proteção para reproduzir uma ordem interna menos restritiva do runtime.
4. Não modificar runtime para forçar igualdade de hashes; registrar as 3 diferenças da API e as 9 do worker e resolver compatibilidade somente numa release futura revisada e autorizada. Não adicionar fallback que aceite chave de outro ambiente nem reduzir a capacidade do `main` para o limite legado de 75.
5. Tratar o limite de prévia 75/100 como gate de compatibilidade a verificar em testes locais antes de uma release, não como incidente confirmado.
6. Não executar migration, deploy, alteração de segredo, backup remoto, teste de integração com provedor real ou operação de escrita em produção.

## Validation

- Registrar os hashes comparados para API, worker e `main`, e revisar os diffs dos nove módulos do worker.
- Executar os testes existentes/novos focados de criptografia, referência facial e secrets com dados sintéticos.
- Executar lint e validação OpenSpec pertinente.
- Registrar bloqueios de versões/dependências sem inferir defeito do runtime.
