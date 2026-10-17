# Decisões de design

## Gate de homologação

Manter `environment: homolog` para segredos, trilha do GitHub Actions e política de branch protegida, removendo apenas a regra `required_reviewers`. O workflow segue condicionado ao push em `develop` e às dependências de CI que já possui. Os checks exigidos pela proteção de `develop` permanecem inalterados.

## Operação

O deploy continua usando o fluxo atual, com inventário, backup, validação do Compose, escopo do projeto `markina-gallery` e verificações de saúde. Esta mudança não encurta nem contorna esses passos. Uma falha de preflight ou de healthcheck continua impedindo ou reprovando o deploy.

## Efeito observável

Após todos os checks que antecedem o job de homologação concluírem com sucesso, o deploy deixa de aguardar aprovação manual do ambiente e começa automaticamente. O release continua limitado à branch protegida `develop`; produção permanece sujeita aos seus gates próprios.

## Recuperação do worker encerrado

O incidente real deixou o container geral `worker` existente em `exited (1)`, embora sua configuração facial persistida permaneça habilitada. O preflight SHALL permitir somente este caso quando os logs confirmam o erro `value too long for type character varying(192)`, o SHA alvo contém a correção versionada da chave e a variável do container coincide com `.env.homolog`. Os logs são filtrados sem serem exibidos. O container antigo não será iniciado para o diagnóstico. Todos os outros workers faciais continuam sujeitos à verificação de saúde prévia; depois da troca, `worker` precisa passar healthcheck e probes públicos antes de declarar sucesso. Container ausente, outro estado/código, configuração divergente, causa divergente ou ausência da correção no alvo continuam sendo bloqueios.
