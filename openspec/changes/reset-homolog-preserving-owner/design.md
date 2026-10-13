## Context

Ver `proposal.md`. O SHA publicado no servidor é `0ef80fdf912e8f9cbde730d061b69b73d46ff5aa`; o deploy/CI do run `38449029514` concluiu. A API usa a origem nova e permite explicitamente DuckDNS. O inventário sanitizado identificou 5 tenants/admins, 13 clientes, 10 galerias, 8 pastas, 673 fotos, 11 pedidos, 4 pagamentos de provider e 546 MB de mídia operacional. A conta solicitada existe, coincide com `platform_owner` e possui exatamente um vínculo ativo. As configurações InfinityPay, PIX, WhatsApp, marca e processamento do proprietário são identificáveis por esse tenant.

## Goals / Non-Goals

**Goals:** reset exclusivo do servidor homologado para um proprietário, com exclusão fechada de dados e comparação de preservação, sem dump novo.

**Non-Goals:** produção, rotas públicas de reset, alteração de schema, reset genérico multitenant, troca de credenciais, cobrança/estorno externo, intervenção no NPM ou projetos vizinhos. O procedimento antigo conserva sua recusa multitenant.

## Decisions

### Registro do workflow na branch padrão

O GitHub recusou `workflow_dispatch` de `maintenance-homolog.yml` em `develop` com HTTP 404 porque o arquivo não existe na branch padrão `main`. Registrar na `main` somente um workflow inerte de mesmo caminho, nome e contrato de inputs: ele recusa operações e orienta selecionar `develop`, sem checkout, Environment, secrets ou SSH. Ao disparar com ref `develop`, o GitHub usa a versão completa revisada no PR #170, com gate `homolog` e guardas de SHA/proprietário. Os scripts e a aplicação não são promovidos para `main`; este registro não executa deploy nem reset. Os artefatos desta change acompanham o registro para documentar a operação implementada em `develop`.

O PR #170 foi aprovado pelo proprietário e integrado em `develop` como `97eacae36eed3a3ab491e46823761ca0b031c7f0`; o CI do PR (`38464341510`) passou integralmente após retry do download Gemma limitado por HTTP 429. O CI automático do push (`38469477183`) foi cancelado antes do gate remoto para evitar redeploy e dump adicional: a manutenção usa a imagem já publicada `0ef80fdf912e8f9cbde730d061b69b73d46ff5aa`.

### Identidade e preservação explícitas

Resolver e-mail exato para admin, conferir `platform_owner`, operador ativo e único vínculo de tenant ativo. Preservar IDs, credenciais, TOTP, sessões/push administrativos da conta, privilégios, configuração global do experimento e configurações vinculadas ao tenant proprietário. Atribuição global que referencie admin a remover ou FK de linha preservada para linha elegível impede execução; não reatribuir nem inventar proprietário.

Preservar observabilidade global (buckets, amostras, incidentes, transições e workers) conforme a spec do monitor; remover somente concessões/atividade de sessões das contas excluídas. Auditoria de segurança global e do proprietário permanece, auditoria operacional e de tenants removidos é excluída. Filas de e-mail e tentativas são dados de teste/transporte, não preferências: apagá-las evita entregas pendentes a contas removidas.

### Política fechada de cada tabela

Manter listas independentes de tabelas operacionais, configurações do tenant, identidade/admin e monitor global. Mudança de schema sem classificação bloqueia antes da mutação. Calcular para cada tabela as linhas preservadas e excluídas, verificar referências das preservadas e ordenar exclusões de filhos antes dos pais. O único ciclo conhecido é a capa nullable da galeria: limpar sua referência antes de excluir o grafo. Não usar TRUNCATE CASCADE, desabilitação de constraints ou recriação de banco.

### Mídia e ativos de marca

Zerar somente source, derivatives, history, facial-references e raw-staging da Markina. Na raiz branding, preservar bytes de todos os ativos referenciados pelo proprietário e seu namespace; os três ativos atuais pertencem ao proprietário. Validar caminhos absolutos/mounts sem symlinks de raiz, percorrer sem seguir links e jamais excluir alvos de links externos. Não apagar volumes ou imagens Docker.

### Manutenção com o código publicado estável

O run de execute `38472862716` abortou em 13/10/2026 antes de pausar writers ou excluir dados: `/var/lib/markina-gallery` pertence a root e o operador ubuntu não pôde criar `owner-reset`. O inventário havia validado dumps, mas não a prontidão do diretório de retomada. Provisionar somente esse diretório vazio, canônico, com modo 0700 e dono do operador; inventory e execute SHALL conferir existência, dono, modo e escrita/acesso antes da pausa. Não ampliar permissões do diretório pai nem mover o estado para o checkout.

No mesmo run, Docker recusou `.State.Health` para o contêiner one-shot `migrate` sem healthcheck. A leitura do snapshot SHALL tratar ausência do campo como `none` e propagar explicitamente falhas de inspect, inclusive quando invocada sob uma condição shell. O snapshot continua exigindo exatamente os três serviços Evolution ativos e compara IDs/imagens/início/estado antes e depois.

A mesma regra de propagação vale para listagem de writers: evitar process substitution que oculta falha de `docker ps`. A regressão simulada reproduziu aceitação indevida de lista indisponível na conferência posterior à pausa; capturar e verificar o resultado do comando antes de iterar, tanto no inventário quanto na conferência da pausa. Sem lista confirmada, nenhuma exclusão pode começar.

Executar um script Python revisado em contêiner efêmero da imagem API já publicada, fornecido pelo workflow protegido em arquivo temporário de código montado somente leitura. O script usa os modelos publicados, mas possui sua própria classificação fechada. Conferir SHA esperado, schema, origem canônica e topologia antes de executar; não refazer deploy nem migration para limpar.

O wrapper inventaria containers Markina e recusa serviço desconhecido. Parar e conferir todos os writers ativos: API, worker, faciais/SFace/Gemma, preview-adjustment e raw-development. Evolution, bancos e proxy compartilhado ficam ativos. Salvar somente metadados de retomada (IDs dos containers originalmente ativos, SHA e fase) em diretório privado da Markina; isso não contém dump nem dados de negócio. Reiniciar somente esses containers após pós-condições completas.

### Transação e retomada

Conferir owner/schema/raízes e capturar em memória digests das linhas/ativos preservados antes de excluir. Usar PostgreSQL real e locks para serializar provisão/alterações durante a transação; comparar preservação antes do commit. Após commit, limpar mídia e Redis exclusivos e conferir novamente as invariantes. Falha de mídia após commit é estado parcial, sem alegação de rollback: manter writers pausados, registrar fase sanitizada e permitir retomada idempotente para o mesmo owner/SHA. A rotina não restaura dados porque a operação foi autorizada sem dump novo.

### Dumps antigos autorizados

O proprietário autorizou excluir os 164 arquivos `.dump` anteriores (~2.077.111.921 bytes) inventariados em `/var/lib/markina-gallery/backups`. Antes de pausar writers, o inventário confirma que a pasta fixa permite excluir. A exclusão ocorre somente depois do reset de banco, mídia e Redis concluir, enquanto os writers ainda estão pausados. O wrapper valida caminho fixo, diretório sem symlink, arquivos regulares diretamente na raiz e igualdade do manifesto de contagem/bytes; divergência bloqueia sem começar a excluir. Se a remoção já terminou antes de uma falha posterior, uma repetição aceita o estado zero e prossegue. Depois confere zero `.dump`. Não lê conteúdo, nomes ou credenciais. Snapshots de branding, configuração e todos os tipos de arquivo diferentes de `.dump` permanecem preservados.

## Risks / Trade-offs

- Exclusão irreversível sem dump novo → autorização já registrada, inventário recente e ensaio descartável antes do servidor.
- FK/configuração própria apontando para outra conta → recusar antes de qualquer exclusão.
- Novo writer/schema não previsto → guarda fechada bloqueia, sem ampliar a lista automaticamente.
- Falha entre commit e exclusão de arquivos → estado parcial explícito e retomada idempotente com writers pausados.
- Defaults recriados por requisições após retomada → pós-condições operacionais são verificadas enquanto writers estão pausados; depois validar acesso e somente configurações do owner.

## Migration Plan

1. Concluir/reconciliar a migração do domínio e registrar a validação da conta proprietária.
2. Implementar CLI/wrapper/workflow separado e ensaiar cinco tenants em PostgreSQL/volumes descartáveis, inclusive falhas e preservação.
3. Revisar diff e executar checks, abrir PR e manter o gate humano `homolog`.
4. Executar inventário do procedimento novo com SHA/owner explícitos; apresentar contagens e janela restrita de API.
5. Executar o reset sem criar dump; após sucesso, remover os 164 `.dump` antigos autorizados e confirmar zero `.dump`, mantendo snapshots/configuração e outros tipos de arquivo.
6. Validar acesso do proprietário pelo domínio novo e registrar evidência. Não há rollback dos dados apagados; recuperação de serviços é restrita aos containers pausados.
