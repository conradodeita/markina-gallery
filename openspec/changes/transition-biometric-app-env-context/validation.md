# Validação operacional — 30/10/2026

## Resultado publicado

A transição autorizada e a liberação técnica de pagamentos reais foram concluídas pelo coordenador revisado `scripts/environment_cutover_release.py`, via SSH do operador autorizado. O SHA de suporte foi `180de9e8fc498052c709a1133b7f368989347424`, merge do PR #348; [CI push/main 41010400151](https://github.com/conradodeita/markina-gallery/actions/runs/41010400151) concluído com `success`. Esta é uma publicação de configuração e envelopes cifrados, preservando as imagens de aplicação existentes; não é uma atualização dessas imagens para o SHA do suporte.

A execução usou `env-mp-20261030-04`. O inventário anterior confirmou 13 serviços saudáveis, schema `20261026_0090`, 15.055 embeddings, zero jobs ativos, arquivos de referência, localizadores, entradas desconhecidas e notificações com conteúdo. O fingerprint foi `82bdff3adec2c57e416d528e5f93bffd9428fcd2ec53f45e436520f676f28157`; o plano, `63371517bf520d14ca7304292b0a3dd37412dc79cb01c6eba02719cb99bfd824`. Serviços, ingresso `https://markina.pickyourpic.com.br`, porta `127.0.0.1:8080`, impacto e recuperação foram apresentados antes da execução dentro da autorização existente.

## Preparação, aplicação e retomada

- O candidato veio de blobs Git exatos, com `core.autocrlf=false`, verificados contra a árvore oficial da main e seu CI. A preparação confirmou uma conta, continuidade SMTP/WhatsApp e configuração cifrada persistida/reaberta.
- O processo colocou Nginx em barreira 503, pausou API e worker graciosamente, comprovou ociosidade em transação READ ONLY e encerrou os três faciais com SIGINT e espera ilimitada, sem SIGKILL. Nenhuma fila ou registro foi apagado.
- O pacote completo de aproximadamente 305 MB foi persistido e autenticado antes do SQL, com chave separada e permissões POSIX restritas. O teto permaneceu explícito em 512.000.000 bytes; o processo teve limite de 4 GiB, condicionado a memória/disco disponíveis.
- Embeddings, dois envelopes da conta Mercado Pago e bindings ambientais de WhatsApp foram tratados pelo conjunto transacional aprovado. Metadados, versões históricas, identidades e valores permaneceram preservados. Somente envelopes e contexto ambiental aprovados mudaram.
- API/worker retomaram com `APP_ENV=production`, facial false e inicialmente live false. Cofre, canais, matriz e fingerprint foram conferidos antes de restaurar Nginx. O retorno foi `published`, `financial_preserved=true`, `channels_verified=true`; fingerprint de destino `daeee6349d0c3887732faec9fefba7876d88e735b273d4297e1228bbb489c029`.
- A fase separada `enable-live` confirmou esse destino e habilitou `MERCADOPAGO_ALLOW_LIVE_PAYMENTS=true`, preservando PIX, credenciais e allowlist. Retornou `live_enabled`; fingerprint final `8085fb6bc60175ac659a544e39731a8678ead8d805c116fd4503e989e7689492`.

## Verificações posteriores observadas

- Fingerprint final revalidado; 10 serviços ativos saudáveis e os três workers faciais originais parados. Imagens, comandos, mounts, redes e restart policy de API/worker foram preservados; IDs dos demais serviços e imagens/IDs dos especializados foram conferidos. Gemma/RAW aposentados não foram iniciados ou removidos.
- Prova autenticada contra as linhas atuais: `destination_verified=true`, `source_verified=false`, 15.055 embeddings. Não se inferiu migração pela mera contagem; a comparação foi com o pacote autenticado, sem abrir payloads biométricos na verificação posterior.
- Comparação READ ONLY dos 14 conjuntos financeiros com o baseline privado: contagens preservadas, snapshots integralmente iguais e nenhuma tabela divergente. Há 25 tentativas Mercado Pago preservadas. A compra de prefixo `70980398` está em `rejected`, estado já presente no baseline; não afirmar que continua em processamento nem forçar seu retorno a esse estado. O prefixo de Compra corresponde ao pagamento, não ao ID de `sale_order`.
- Matriz sanitizada: 1 tenant com preferências, PIX habilitado, Mercado Pago habilitado; 1 conta sandbox, 0 contas de produção configuradas, 0 indisponíveis; cofre verificado, gate live true e exatamente 1 par sandbox autorizado. Contas reais continuam exigindo opt-in e credenciais próprias válidas por fotógrafo.
- HTTPS: `/`, `/healthz` e `/api/health` retornaram 200. A sondagem preliminar `/api/healthz` retornou 404 porque essa rota não existe; o endpoint efetivo da API é `/api/health`.
- Não restaram `app-in-flight.sha` nem sidecar da transição. Nginx foi restaurado, sem mudança de porta, DNS, firewall, certificado ou recurso de terceiro. Schema permanece 0090; não houve Alembic/migration nesta operação.

## Recuperação e correções observadas

- PR #345 / CI main `41001303712`: primeira implementação integrada. O inventário recusou ordenação instável de mounts antes de manutenção/escrita; PR #346 / CI `41004477565` corrigiu a representação sem ignorar campos ou drift real.
- PR #347 / CI `41007045024`: `python -P` garantiu precedência do candidato sobre o pacote antigo da imagem, preservando cwd e caminhos relativos de mídia. Preparação 03 passou.
- Aplicação 03 recuperou o contexto original antes de SQL quando o pacote excedeu 256 MB. Foram observados 13 serviços saudáveis e ausência de marcador após a recuperação. Artefatos antigos permaneceram privados, sem exclusão/sobrescrita.
- PR #348 dimensionou recursos, manteve teto e guardas, incorporou prova de ociosidade e SIGINT e preservou a fase original em falhas sanitizadas. A execução 04 passou integralmente. Recuperação após commit foi ensaiada com dados sintéticos PostgreSQL; não foi provocada reversão de uma publicação real bem-sucedida.

## Validação proporcional e limites

A base já tinha 184 testes focados Linux/PostgreSQL registrados em `inventory.md`. Na correção final passaram 16 testes do operador, 5 de storage POSIX e 5 do runtime, Ruff, OpenSpec estrito e diff check; o CI integral da main também passou. Não houve bateria opcional nem alteração de modelos, bibliotecas ou imagens especializadas. A revisão focalizada consolidou apenas a parada dos consumidores diretamente afetados; nenhuma limpeza ampla foi feita.

Não houve emissão de pagamento, cobrança real, envio de mensagem, troca dos valores de credenciais ou configuração da conta Mercado Pago pelo executor. O proprietário foi avisado de que pode cadastrar as credenciais de produção pela UI do seu fotógrafo. Até isso ocorrer, a conta existente continua sandbox e restrita ao par de teste. A compra real com essas novas credenciais e a autenticação do proprietário não foram executadas nesta publicação.

A busca facial está temporariamente indisponível por decisão humana expressa; fotos e índices foram preservados. Sua reativação exige os gates próprios. O caminho de arquivos/localizadores multistore continua sem implementação/aprovação e explicitamente recusado; a tarefa 3.2 permanece pendente e não é requisito deste lote SQL exclusivo com contadores zero. A change continua ativa, sem sync/arquivo automático antes de revisão humana. Pacotes, chaves e recibos ficam no armazenamento restrito do operador, fora do Git.
