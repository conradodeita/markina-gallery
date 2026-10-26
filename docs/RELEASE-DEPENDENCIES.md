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

Os requisitos comuns são instalados nas imagens API/worker, face e ajuste opcional de prévias. Gemma e ingestão RAW foram aposentados no código em 26/10/2026; registros e dados históricos permanecem. O plano deriva consumidores dos contextos e includes reais, cruza apenas serviços running com o inventário e exclui opcionais ausentes/parados. `migrate`/`seed-admin` não são alvos operacionais. Não ativar profiles por esse plano.

O executor atual `deploy-prod-app-services.sh` atende somente api/web, está pinado no wrapper restrito e não fornece rollout/rollback dos workers. O plano Python SHALL permanecer bloqueado quando os consumidores necessários não forem cobertos. A allowlist app funcional não foi ampliada para simular cobertura. Nenhuma atualização deve entrar pelo deploy-homolog, que possui um escopo operacional mais amplo.

Antes de autorizar esse grupo: executor restrito aos consumidores ativos, inventário/fingerprint integral, imagens ARM64 e versões instaladas verificadas, resolução total e `pip check` da imagem candidata, CI/homologação exigidos, plano de filas/leases sem perda de jobs e rollback por ID para cada worker. Face e ajuste de prévias exigem homologação específica quando seu runtime é reconstruído; modelos, pesos, índices e versões dos motores permanecem fora dessa atualização.

Preservar imagem anterior de cada serviço, configuração, source SHA e evidência dos backups existentes de banco/mídia conforme o runbook. Este grupo não tem migration: mudança de schema/Docker/Compose é bloqueio para plano separado. Os quatro pins não tornam o restante do requirements sem lock reproduzível: guardar a resolução efetiva do candidato e impedir atualizações não relacionadas antes da aprovação.

Rollback Python ainda não coberto pelo executor atual é bloqueio, não comando operacional disponível. Não publicar API deixando workers vulneráveis como se o grupo estivesse concluído.

### Preparação Python com recusa operacional

O mesmo `deploy-prod-app-services.sh` possui entrada explícita `--scope python-security` antes dos argumentos legados. Ela nunca entra no fluxo que constrói/recria API/web. O módulo de política é lido do objeto da main aprovada, sem fetch ou alteração do checkout. `--mode plan`/`inventory` requer JSON real recente do coletor, `--sha` e opcionalmente `--candidates`; produz **planning_fingerprint**, sem approval_code operacional. Execução local equivalente:

```text
python scripts/python_security_release.py --mode plan --sha <main-aprovada> --inventory <inventario-real.json> --candidates <candidatos.json>
```

`--mode simulate --simulation <fixture-sintetica.json>` testa o contrato sequencial e rollback inverso por serviço. Não opera Docker/filas/banco e não concede autorização. Modos reais release/rollback/recover, inclusive seus inventários de recuperação, são recusados antes de qualquer escrita: o executor operacional dos workers ainda não existe. Não substituir essa recusa pelo modo app legado nem executar homolog-deploy.

`scripts/build_python_security_candidates.py` constrói **somente no contexto Docker local desktop-linux**, exigindo socket local e reserva mínima de disco. Parte de imagens anteriores importadas por ID com exportação Docker somente leitura, sem volumes/configurações de containers. Docker clássico e containerd podem expor IDs diferentes: o hash do config original e a lista completa de camadas devem coincidir. O preparo acrescenta quatro wheels fixados com `--no-deps --only-binary=:all:` e o manifesto aprovado, sem reinstalar os demais requisitos ou atualizar base/apt/modelos. Compara toda a distribuição instalada, Python, ARM64, camadas anteriores, pins embutidos e `pip check`. Um candidato local nunca é apresentado como imagem publicada ou disponível na Oracle.

Fila vazia e Redis saudável **não** substituem a barreira cooperativa: um novo claim pode ocorrer entre a consulta e o stop. Antes da futura implementação operacional é necessário impedir novos claims/entradas, confirmar fim de ciclo/efeitos externos, preservar jobs aguardando e obter encerramento reconhecido sem SIGKILL. O worker geral exige cobrir providers, outboxes e lifecycle; facial usa SQL durável com lease/token e Redis como wakeup; ajuste tem recuperação por tempo que pode consumir tentativas. O inventário remoto pré-publicação deverá localizar e interromper com segurança qualquer serviço legado RAW/Gemma antes de remover os guardas residuais dos scripts. Não alterar estados de jobs, suspender tenants, pausar containers ou restaurar banco para simular drenagem.

Ordem conceitual, depois desses gates: API isolada, worker geral, manutenção facial, busca, indexação e ajuste de prévias. Componentes aposentados não são incluídos em builds novos; serviços remotos legados requerem inventário e interrupção aprovada antes da publicação. Atualização sequencial exige recibo anterior, saúde/versões e snapshot externo por troca; contingência restaura IDs em ordem inversa sem reverter dados legítimos. Essa ordem é planejamento; homologação especializada e executor/drenagem comprovados continuam obrigatórios. O frontend publicado não é reconstruído nem substituído.
