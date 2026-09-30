# Procedimento da primeira liberação

Estado: plano histórico da primeira liberação, **não usar como roteiro para repetir deploy ou limpeza**. O PR [#115](https://github.com/conradodeita/markina-gallery/pull/115) foi integrado e publicado; o workflow de merge encontrou a revisão 0069 já aplicada. A execução real e suas lacunas estão em [deploy-2026-09-29-tenant-foundation.md](deploy-2026-09-29-tenant-foundation.md). Este procedimento não autoriza novo deploy nem altera o fluxo habitual das próximas releases.

## Destino e preservação

Checkout `/opt/markina-gallery`, projeto `markina-gallery`, arquivo `docker/docker-compose.yml`, ambiente existente `docker/.env.homolog`. Entrada pública `https://markina-homolog.duckdns.org/`, nginx próprio `127.0.0.1:8080 → 80`. API8000/web3000/PostgreSQL5432/Redis6379/Evolution8080 internos. Estado inventariado: SHA `04c6bb98cdbb7607026cd54106d9e4cdf43d1e29`, schema `20260928_0068`, uma instância Evolution `open`.

Preservar admin, senha/TOTP, sessões e meios de acesso; conta/vínculo criados na 0069; branding/PIX/configurações preservadas pelo CLI; todos os volumes da Evolution e proxy/HTTPS. Firefly/Clearbudget, Proxy Manager e Portainer não são alvos. Somente os dados operacionais e as quatro raízes de mídia exclusivas listadas pelo CLI de homologação podem ser descartados. A autorização de descarte do proprietário já está registrada em `validation.md`.

## Condições de entrada

1. Aprovação humana identifica o SHA, este destino, janela e escopo. CI da implementação e validação OpenSpec aprovadas. A limpeza será executada na mesma janela, com backup, antes de retomar escritores.
2. Revalidar checkout limpo, origin esperado, SHA/schema e topologia. Conferir serviços ativos, volumes/portas e estado Evolution sem imprimir configuração resolvida ou segredos. Divergência cancela a operação até reconciliação.
3. Conferir configuração atual em leitura: origem pública correta, chaves obrigatórias presentes/válidas e flag facial compatível com os três workers. Nenhuma rotina de geração/substituição de segredos ou edição de ambiente está autorizada por esta release.
4. Confirmar ausência de outra publicação em execução. **Não fazer merge em develop para iniciar este procedimento:** o workflow habitual migra e retoma workers antes da manutenção. Esta primeira liberação usa a sequência manual abaixo, com o SHA explicitamente aprovado. Revisão/merge posteriores não integram a aprovação automaticamente.

## Sequência operacional controlada

O executor utiliza as funções versionadas de `scripts/deploy-homolog.sh`, carregadas por `source`, sem chamar `main`. O caminho manual precisa repetir as verificações de destino acima; não executar um script remoto desconhecido. `compose` mantém projeto/arquivo explícitos e inclui o override de branding e o de preview quando presentes. Definir as variáveis de controle a partir do inventário: SHA anterior/alvo, flag facial existente e preview ativo; não inferir ausência de serviço pela configuração de outro projeto.

1. Registrar imagens anteriores, SHA/schema e horário UTC. Obter o commit aprovado por fetch e conferir seu conteúdo; selecionar somente esse commit no checkout remoto limpo. Isso não reinicia os containers atuais. Construir as imagens dos serviços próprios antes da janela.
2. Aplicar `prepare_branding_transition` com preservação obrigatória e confirmar sua evidência antes de qualquer recriação. A função preserva a marca pelo procedimento existente e pode interromper a API. Não chamar as funções que escrevem chaves/ambiente; os valores foram conferidos em leitura.
3. Executar `stop_application_writers` e conferir API, worker geral, face-search, face-index, face-maintenance e preview interrompidos pelos labels exclusivos. Manter PostgreSQL, Redis, Evolution e vizinhos ativos. Criar backup lógico com `create_backup` depois dessa interrupção; conferir arquivo não vazio e listagem do arquivo com `pg_restore --list`, sem imprimir conteúdo. Registrar caminho restrito, tamanho, SHA-256 e horário. Essa conferência não substitui um ensaio de restauração.
4. Executar `apply_target_migrations` com revisão anterior observada. Exigir head `20260929_0069`, uma conta ativa, vínculo do admin e propriedade completa. A função confere novamente a parada antes do Alembic. Falha ou schema inesperado mantém a janela aberta para correção compatível; não reiniciar binários antigos.
5. Ainda com escritores interrompidos, executar `compose run --rm --no-deps -e APP_ENV=homolog api python -m app.homolog_cleanup --mode inventory` e guardar somente o JSON de contagens. Comparar também admin/credenciais/sessões/configuração do canal por verificador privado, sem imprimir valores sensíveis. O override de ambiente vale só para o processo, seguindo o wrapper existente; não modifica o arquivo de ambiente.
6. Executar o mesmo CLI com `--mode execute --confirmation DELETE_HOMOLOG_GALLERIES_AND_CLIENTS`. Ele usa lista fechada de tabelas, PostgreSQL exclusivo e raízes conferidas, preservando `tenant`/`tenant_admin`. Limpar apenas o banco Redis da aplicação com o comando já usado no wrapper `compose exec -T redis redis-cli FLUSHDB`; conferir previamente que esse serviço/banco é o exclusivo da aplicação. O Redis da Evolution não participa.
7. Repetir o inventário: todas as contagens operacionais/mídia devem ser zero, e todas as contagens preservadas iguais às do passo 5. Verificar igualdade dos dados administrativos/canal sem publicar seus valores. Falha mantém os escritores parados; não registrar conclusão parcial como sucesso.
8. Retomar somente aplicação com `start_application_services`, seguido de `wait_for_health`, `verify_facial_deploy_state` e registro de revisão saudável. Não chamar `start_whatsapp_infrastructure_if_active`: Evolution já saudável deve manter seus containers/volumes atuais. Confirmar saúde local/HTTPS, Evolution `open` e ausência de mudança nos serviços vizinhos.
9. Registrar versão/schema/UTC e resultado da limpeza. Testar galeria/upload/prévia com JPEG sintético; login real e OTP exigem participação do proprietário, sem registrar senha/código. Não processar lote facial real nem enviar mensagem real sem a autorização própria por execução. Entregar os quatro pontos definidos em `delivery-plan.md`, identificando qualquer aceite humano pendente.

## Janela e recuperação

O site pode ficar indisponível entre preservação/parada e saúde final. Dump lógico somente-leitura medido: 7,641 s/105 MB; migration, gravação/verificação do backup, remoção de aproximadamente 1,85 GB e retomada ainda não foram medidos no destino. Não há promessa de duração exata. Impacto zero é o objetivo para os projetos vizinhos, conferido antes/depois.

O dump preserva o banco; **não contém os arquivos de mídia descartados**. O proprietário autorizou esse descarte. O procedimento não promete restaurar o acervo apagado nem equivale ao futuro backup cifrado externo com ensaio de RPO/RTO. Branding e Evolution possuem preservação própria e não entram no descarte.

Antes da migration, uma falha permite avaliar retorno ao código anterior compatível, mantendo o acervo ainda não descartado. Depois de 0069, manter o schema e corrigir com binário compatível: a versão anterior não fornece `tenant_id` nas novas escritas. Não executar downgrade, restauração nem rollback automático neste procedimento. Se necessários, registrar o estado e obter a autorização específica, preservando o backup e os recursos próprios.
