# Publicação de dependências por grupo

Preparação não autoriza release. O merge de infraestrutura/dependências continua sem publicação automática. O classificador emite `dependencies`; os jobs de produção existentes aceitam somente os escopos próprios `app` ou `facial`. Docker/Compose, migrations e workers especializados permanecem protegidos.

## Inventário somente leitura

Usar somente o SSH já autorizado pelo proprietário. Não abrir a chave nem imprimir ambiente, logs ou dados de aplicação. Exemplo PowerShell (substituir a referência da chave já autorizada, sem copiá-la para o repositório):

```powershell
Get-Content scripts/inventory-dependency-runtimes.py -Raw |
  ssh -i <chave-ja-autorizada> -o BatchMode=yes -o StrictHostKeyChecking=yes ubuntu@132.145.193.169 'python3 -'
```

O coletor lê apenas metadados do projeto `markina-gallery`, metadados de quatro pacotes Python/Next/React e o campo não secreto APP_VERSION. Inclui migrate parado; não o executa. As consultas de pacotes usam processos isolados `docker exec`, sem importar a aplicação, sem rede externa, sem volumes de teste e com bytecode Python desabilitado. Um erro de coleta exige diagnóstico, nunca preenchimento por suposição.

Salvar o JSON sanitizado fora do Git e manter hash/horário da coleta. Inventário deve ser refeito imediatamente antes da aprovação; o planejamento rejeita inventário com mais de uma hora, identidade/saúde/arquitetura inválidas ou versões ausentes. IDs locais de imagem são identidades imutáveis de conteúdo; `repo_digests=[]` não é digest de registry nem prova de publicação de imagem.

```text
python scripts/dependency_release.py impact --base <checkout-oracle> --target <main-aprovada>
python scripts/dependency_release.py plan --base <checkout-oracle> --target <main-aprovada> --inventory <json-real> --group web
python scripts/dependency_release.py plan --base <checkout-oracle> --target <main-aprovada> --inventory <json-real> --group python
```

Esses comandos não alteram servidor/containers. Plano não é fingerprint operacional nem autorização. Nunca usar fixtures dos testes como inventário.

## Grupo A — frontend

1. Confirmar CI/revisão do SHA integral da main, frontend ARM64 construído e versões conferidas contra o lockfile. Confirmar que o frontend mantém os contratos de autenticação, vendas e entrega; os testes de integração existentes continuam obrigatórios.
2. Usar `deploy-prod-web.sh` do SHA aprovado. O helper também é carregado dos objetos desse SHA, e não do checkout antigo. O alvo deve estar disponível no Git do host: se estiver ausente, o inventário falha sem fetch. Preparação Git no host exige autorização própria posterior.
3. O inventário web comprova contexto resolvido exclusivamente `/opt/markina-gallery/frontend`, sem contextos/args/volumes extras, Dockerfile/.dockerignore revisados e árvore sem symlinks/submódulos ou arquivos não versionados incluídos no build. O hash da árvore é proveniência dos inputs, não digest da imagem. O hash Compose deve coincidir com o container.
4. Requisitos Python conhecidos podem estar pendentes no mesmo SHA. Mudanças de código API, schema, Compose ou build web continuam recusadas. A API mantém sua revisão e ID observados; o checkout compartilhado no SHA novo não significa que Python foi publicado.
5. Apresentar inventário, fingerprint, SHA e impacto ao proprietário; somente depois executar o modo release em outra missão. O script preserva a imagem anterior por ID, constrói somente web, registra o ID construído e recria somente web com `--no-deps`. Nenhuma migration. Interrupção breve é possível.

Saúde: healthcheck web e HTTPS `/healthz`, `/api/health`, `/`, `/admin/payments`; `/admin/statistics` permanece 404. Nenhum OTP, pagamento, envio ou acesso a fotos de clientes como smoke. Parar diante de falha, mudança de main, snapshot não-web/configuração divergente ou imagem de recuperação ausente. O snapshot não-web deve permanecer igual.

Rollback: inventário/approval-code próprios, imagem anterior e recibo exatos (`web-previous.identity`), configuração e snapshot correspondentes; usar modos rollback/recover previstos no runbook `DEPLOY-PROD-WEB.md`. Não reconstruir uma tag móvel para substituir a imagem anterior. Não restaurar banco nem reiniciar dependências.

## Grupo B — Python

Os requisitos comuns são instalados nas imagens API/worker, face, Gemma, ajuste e RAW. O plano deriva consumidores dos contextos e includes reais, cruza apenas serviços running com o inventário e exclui opcionais ausentes/parados. `migrate`/`seed-admin` não são alvos operacionais. Não ativar profiles por esse plano.

O executor atual `deploy-prod-app-services.sh` atende somente api/web, está pinado no wrapper restrito e não fornece rollout/rollback dos workers. O plano Python SHALL permanecer bloqueado quando os consumidores necessários não forem cobertos. A allowlist app funcional não foi ampliada para simular cobertura. Nenhuma atualização deve entrar pelo deploy-homolog, que possui um escopo operacional mais amplo.

Antes de autorizar esse grupo: executor restrito aos consumidores ativos, inventário/fingerprint integral, imagens ARM64 e versões instaladas verificadas, resolução total e `pip check` da imagem candidata, CI/homologação exigidos, plano de filas/leases sem perda de jobs e rollback por ID para cada worker. Face/Gemma/RAW/prévias exigem homologação específica quando seu runtime é reconstruído; modelos, pesos, índices e versões dos motores permanecem fora dessa atualização.

Preservar imagem anterior de cada serviço, configuração, source SHA e evidência dos backups existentes de banco/mídia conforme o runbook. Este grupo não tem migration: mudança de schema/Docker/Compose é bloqueio para plano separado. Os quatro pins não tornam o restante do requirements sem lock reproduzível: guardar a resolução efetiva do candidato e impedir atualizações não relacionadas antes da aprovação.

Rollback Python ainda não coberto pelo executor atual é bloqueio, não comando operacional disponível. Não publicar API deixando workers vulneráveis como se o grupo estivesse concluído.
