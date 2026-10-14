# Publicação conjunta em homologação — 2026-09-20

## Autorização e escopo

Após a solicitação de pastas e persistência de push, o proprietário declarou: “Após o job, autorizo a paridade de sistemas, push, merge, deploy.” Informou também CI facial #265 verde. Esta autorização sucede a preferência anterior de parar após push: autoriza concluir os gates e publicar a versão conjunta. Não autoriza apagar dados reais, enviar mensagens a clientes nem alterar terceiros.

O plano de paridade já apresentado na change `evolve-highres-facial-pipeline` permanece: código completo em homologação, migration aditiva 0057, habilitação de novas admissões high-res pelo único ajuste `FACIAL_HIGHRES_ENABLED=true`, limites e demais configurações preservados. A permissão não implica benchmark arbitrário de fotos existentes.

## Diagnóstico do deploy ausente

Actions #265 (`35521564392`) é evento pull_request da PR #88, SHA dbf5d07e66a87712a6dde1dec7d93428930623dd. Backend/frontend/OpenSpec/gitleaks passaram. `deploy-homolog` foi SKIPPED porque seu `if` exige push em develop. PR #88 ainda estava aberta na inspeção. Não se trata de falha de implantação.

## Inventário revalidado

- Checkout limpo `/opt/markina-gallery`, SHA 9b83f062e21ea613537c1b931bd885cf5241972f.
- 13 containers Markina saudáveis, entrada exclusiva `127.0.0.1:8080`, mesmo `https://markina-homolog.duckdns.org`. Nenhum novo domínio/porta/proxy.
- Host ARM64, 4 CPUs, 23.988 MiB RAM, 19.774 MiB disponíveis, disco 125 GB livre/194 GB. Health API `ok`.
- Terceiros inalterados: firefly_bot 9335f5e9077e, firefly_api f06f36a5ed33, firefly_frontend 6ea8a742b093, firefly_db 768223c11835, nginx-proxy-manager 66c25ca56d8c, portainer e49166611a66.
- GitHub environment homolog conserva required_reviewers e política de branches. Não remover proteções, alterar secrets nem usar implantação paralela para contornar o workflow. Uma aprovação requerida pela plataforma deve registrar a autorização humana acima pelo mecanismo normal; se a plataforma exigir interação exclusiva do proprietário, deixar o gate pendente e informar o link.

## Sequência e verificação

Concluir validação local e commits focados; integrar a PR facial verde; atualizar a branch deste job com develop; resolver conflitos preservando limpeza high-res; validar integração; publicar PR e aguardar CI. Merge somente do SHA aprovado. Evitar duas implantações simultâneas e publicar o candidato final conjunto. Workflow existente faz backup, preserva branding, constrói imagens, aplica migration e valida saúde. Não executar prune, down, restore, downgrade ou limpeza de dados.

Após deploy, comparar SHA local/remoto, revisão Alembic, serviços, flags autorizadas, mount de origem facial somente leitura e terceiros. Testes reais de consentimento nativo/mobile, OTP e corpus facial anotado exigem a interação/dados do proprietário; não declarar essas evidências sem executá-las.
