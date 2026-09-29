# Contrato de entrega por etapa

Estado em 2026-09-29: **implementação local concluída; validação integrada em andamento; deploy pendente**.

Este documento permite ao proprietário acompanhar entregas sem ler código. As etapas abaixo são uma sequência proposta; somente a primeira está especificada nesta change. Cada etapa futura precisa de change e aceite próprios. Uma etapa pode exigir mais de uma liberação e nenhum deploy será anunciado como concluído apenas porque seu código foi escrito.

## Sequência proposta

| Etapa | O que será entregue | Como reconhecer o resultado | Condição para avançar |
|---|---|---|---|
| 1 — Propriedade do acervo | Galerias e fotos vinculadas à conta do fotógrafo atual; vínculo administrativo explícito; legado preservado | Você continua entrando, criando galerias e enviando fotos. O relatório técnico comprova a propriedade e a preservação dos dados | Migration ensaiada, regressões aprovadas, versão/schema reconciliados e homologação autorizada/validada |
| 2 — Isolamento completo | Separação dos dados, configurações, pagamentos, clientes e trabalhos de fotógrafos independentes | Contas de teste não conseguem acessar ou alterar dados umas das outras | Modelo comercial/privacidade aprovado, B01 sem vazamentos; admissão comercial de outro fotógrafo também depende da etapa 3 |
| 3 — Limites e distribuição das filas | Limites de uso e processamento que preservam o atendimento de cada fotógrafo | Um lote grande não impede o progresso de outro fotógrafo ou o envio de OTP | Limites/prazos aprovados e B02/B03 com concorrência e retries validados |
| 4 — Medição e recuperação | Evidências de espera, velocidade, uso, conexões e custo; backup com restauração ensaiada | Relatório mostra o limite medido da instalação e a recuperação comprovada | SLO e RPO/RTO aprovados, inventário financeiro real e benchmarks aplicáveis |
| 5 — Expansão medida | Mais capacidade de processamento, somente quando os dados justificarem | Ganho medido de velocidade sem degradar o acesso nem ultrapassar orçamento | Etapas anteriores, comparação controlada de workers e autorização da configuração/custo |

As etapas 2 e 3 completam fundamentos necessários antes de admitir fotógrafos independentes. A ordem não impede antecipar trabalho independente de medição/backup em outra change; essas entregas não autorizam liberar multitenancy. Não há contratação de infraestrutura ou promessa de número de clientes nesta sequência.

## O que você receberá após cada deploy

1. **Entregue:** mudança concreta e benefício, indicando se a entrega aparece na interface ou é uma proteção interna.
2. **Você pode testar:** passos simples, ambiente e resultado esperado.
3. **Verificado:** testes executados e evidências, com falhas ou testes não realizados identificados.
4. **Pendente:** limitações desta versão e requisito da próxima etapa.

Antes de publicar, também serão apresentados versão exata, ambiente, serviços próprios afetados, portas/subdomínio, eventual janela de indisponibilidade do Pick-your-Pic e reversão possível. A autorização operacional é específica para essa liberação.

## Primeiro deploy: resultado esperado

Exemplo de comunicação **a preencher após execução; não é declaração de entrega atual**:

> Entregue: novas galerias e fotos têm sua conta de fotógrafo como proprietária explícita. O acervo anterior foi descartado conforme sua autorização, preservando admin, acesso e Evolution conectada, conforme as conferências registradas.
>
> Você pode testar: entre como fotógrafo e crie uma galeria de teste com um JPEG sintético. Confira envio, galeria privada autorizada e prévia protegida. O teste de cliente/OTP depende de acesso humano autorizado e será registrado separadamente.
>
> Verificado: [preencher testes e links reais, contagens antes/depois e versão/schema].
>
> Pendente: a operação continua com um fotógrafo. Clientes, PIX, branding, notificações e filas ainda precisam de isolamento antes de habilitar outras contas; nenhuma capacidade comercial nova foi comprovada.

## Registro de cada liberação

Copiar este modelo para `deploy-<data>-<identificador>.md` dentro da change correspondente e preencher fatos observados. Não usar resultados previstos como evidência.

| Campo | Valor a registrar |
|---|---|
| Change e etapa | Identificador e recorte liberado |
| Ambiente e endereço | Local, homologação ou produção; endereço confirmado |
| Data/hora UTC | Início e término reais |
| Estado | Preparado / autorizado / publicado aguardando validação / validado / falhou / revertido |
| Versão | SHA e identificação dos artefatos efetivamente executados |
| Schema | Revisões observadas antes/depois e cadeia validada |
| Autorização | Referência da aprovação humana específica |
| Inventário e impacto | Serviços/volumes/rede próprios, portas/subdomínio; verificação dos projetos vizinhos |
| Backup e reversão | Evidência do backup, ensaio, versão compatível e procedimento aprovado; sem credenciais |
| Entregue | Funcionalidade ou proteção interna realmente disponível |
| Você pode testar | Passos, resultado esperado e participação humana necessária |
| Verificado | Comandos/resumos e links; distinguir aprovado, falhou e não executado |
| Pendente | Bloqueios, limitações e requisito de avanço |

## Gates desta primeira liberação

- Reconciliação concluída: servidor e base de implementação em `04c6bb98cdbb7607026cd54106d9e4cdf43d1e29`, schema remoto `20260928_0068`; alvo `20260929_0069`, ancestral 0068. Ver [validation.md](validation.md).
- Destino confirmado por leitura: `https://markina-homolog.duckdns.org/`, nginx próprio em `127.0.0.1:8080`. API, web, bancos, Redis e Evolution usam portas internas. Endereço/proxy/DNS/certificados permanecem como estão.
- PostgreSQL, Redis e serviços vizinhos permanecem protegidos. Somente inventário remoto de leitura foi executado; nenhuma publicação ou limpeza.
- A obrigatoriedade de propriedade pode impedir escritas de versões antigas. A janela e a reversão compatível precisam de ensaio; não prometer rollback automático nem indisponibilidade zero do produto.
- Busca facial com dados reais e envio de mensagens continuam sujeitos às autorizações existentes; os testes locais usam dados sintéticos e serviços substitutos.

## Preparação operacional desta liberação

Branch isolada: `feature/add-tenant-ownership-foundation`, baseada no SHA remoto confirmado. Implementação versionada em `b4c320e75cbe0d786d8b05d62d57b77aa796a2ec`, [PR #115 em rascunho](https://github.com/conradodeita/markina-gallery/pull/115). Nenhum arquivo de ambiente ou segredo foi alterado. O [procedimento da primeira liberação](release-runbook.md) detalha a sequência manual necessária para inserir a limpeza antes da retomada dos escritores; não usar o merge automático como início dessa janela.

Escopo de preservação solicitado: conta administrativa, hash da senha, TOTP, sessões e meios de acesso; nova conta/vínculo do fotógrafo; configurações do canal e volumes `evolution-instances`, `evolution-pgdata`, `evolution-redisdata`. A Evolution foi consultada sem envio: uma instância `open`. Admin e OTP reais continuam sujeitos ao teste humano, sem compartilhar senha/código no relatório.

O descarte do acervo atual foi autorizado pelo proprietário. A execução será incluída na janela operacional da liberação, com backup antes da operação e sem reabrir workers entre a migration e a limpeza. Não será usado modo sem backup. O inventário atual tem 12 origens, 18 pastas, 3.214 fotos, uma cliente e cerca de 1,85 GB de mídia operacional; contagens e relação de tabelas serão revalidadas imediatamente antes da execução. A leitura identificou 71 sessões administrativas e uma configuração de canal a preservar, além dos demais itens listados em [validation.md](validation.md).

O serviço atual usa `APP_ENV=staging`; o wrapper de manutenção existente executa seu CLI exclusivo com `APP_ENV=homolog` apenas no processo. O inventário confirmou essa compatibilidade sem modificar arquivos de configuração. A mesma distinção deverá ser respeitada na execução autorizada.

Ordem operacional prevista:

1. Revalidar destino, SHA/schema, estado da Evolution e recursos vizinhos. Conferir por igualdade, sem imprimir ou substituir segredos, que as configurações existentes são válidas. Divergência de ambiente exige decisão humana específica.
2. Construir as imagens compatíveis antes da janela; registrar imagem anterior e preservar branding pelo procedimento existente. Criar backup lógico próprio com acesso restrito antes da migration/limpeza.
3. Parar apenas API, worker geral, três workers faciais e ajuste opcional; conferir pelos labels do projeto. Evolution, PostgreSQL/Redis e serviços vizinhos permanecem ativos. Jobs permanecem duráveis até a limpeza autorizada dos dados de negócio.
4. Aplicar `0068 → 0069`, conferir conta/vínculo e propriedade. Executar a rotina existente de limpeza com os binários novos e os escritores ainda parados; conta/vínculo/admin/sessões/canal ficam preservados. Remover somente mídia operacional própria e limpar apenas o Redis da aplicação, preservando o Redis da Evolution.
5. Conferir contagens operacionais zeradas e preservação por comparação; iniciar binários compatíveis e validar saúde local/HTTPS, Evolution `open`, admin, galeria e JPEG sintético. OTP/checkout real e biometria seguem suas autorizações próprias; nenhum envio ou lote real é criado por esta preparação.
6. Registrar SHA/schema/UTC e os quatro pontos de entrega abaixo. A janela só termina com os serviços saudáveis; qualquer falha é registrada sem declarar sucesso.

O site pode ficar indisponível durante a parada dos escritores. A duração de build não compõe a janela planejada, mas backup, migration, limpeza e health checks compõem. Ensaio somente-leitura de dump lógico no servidor: 7,641 s para aproximadamente 105 MB, sem arquivo salvo. Os testes locais fornecem ensaio funcional; gravação/verificação do backup, migration e limpeza remotas ainda não foram cronometradas, portanto não há promessa de duração exata ou indisponibilidade zero. Impacto zero refere-se a Firefly/Clearbudget, Proxy Manager, Portainer e seus recursos.

Reversão: antes de qualquer mudança de schema, o script permite restaurar código compatível com o schema observado. Após 0069, o binário anterior não pode criar entidades sem proprietário; manter schema e usar correção compatível. Restauração de backup/downgrade é decisão separada e não automática. O backup deste deploy não comprova a etapa futura de backup cifrado externo e restauração/RPO/RTO.

## Entrega local — ainda não publicada

- **Entregue localmente:** modelo e migration de propriedade do acervo, vínculo administrativo revalidado, herança em galerias/fotos, gate da conta única e proteção da limpeza. A interface comercial atual permanece igual.
- **Você poderá testar após publicar:** entrar com o admin atual, criar uma galeria e enviar um JPEG sintético, abrir a prévia e o fluxo privado autorizado. Após a limpeza, o acervo de teste anterior estará vazio. A conectividade da Evolution deve permanecer `open`.
- **Verificado:** [CI da implementação b4c320e](https://github.com/conradodeita/markina-gallery/actions/runs/36586629460) aprovada: backend **890 passed / 19 skipped**, frontend **50 arquivos / 352 testes**, lint/build/OpenSpec/varredura de segredos e políticas de deploy. Integridade/migration/contexto novos foram executados com PostgreSQL sintético; quatro testes adicionais de high-res PostgreSQL passaram localmente. TypeScript local aprovado. Evidências e limites dos skips em [validation.md](validation.md).
- **Pendente:** autorização operacional da release **b4c320e75cbe0d786d8b05d62d57b77aa796a2ec**, deploy/limpeza e testes reais de acesso, seguidos de revisão humana. Múltiplos fotógrafos, quotas, isolamento completo e expansão não estão habilitados. O PR segue em rascunho; nenhuma publicação automática foi iniciada.
