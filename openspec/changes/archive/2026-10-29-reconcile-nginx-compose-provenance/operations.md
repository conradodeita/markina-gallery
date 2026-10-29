# Procedimento operacional — Nginx e fontes Compose

Este procedimento não aprova uma publicação. A implementação local é autorizada; armazenamento remoto e troca do container exigem os planos específicos abaixo. Nenhuma etapa troca credenciais Mercado Pago ou libera cobranças.

## Escopo observado e impacto

- Projeto `markina-gallery`, serviço alvo único `nginx`, domínio `https://markina.pickyourpic.com.br`, entrada `127.0.0.1:8080 → 80/tcp`. A imagem anterior é preservada por ID; não existe build/pull no executor.
- Redes atuais: interna da Markina e ligação já existente à `npm-network`, incluindo seus aliases. A operação não cria/altera/remove redes nem configura o proxy externo, DNS ou certificados. Somente o vínculo do Nginx recriado usa as mesmas redes/aliases.
- A montagem atual do servidor é preservada. O candidato acrescenta duas montagens somente-leitura para preservar os bytes de `nginx.conf` e `mime.types` em armazenamento durável. A recuperação usa três cópias verificadas dos arquivos carregados, inclusive a configuração do servidor.
- O snapshot abrange todos os containers próprios, inclusive históricos parados, por identidade, imagem, configuração, mounts, redes e estado. A ordenação de mounts retornada pelo daemon é canonicalizada; alterar um mount ou qualquer outro campo protegido continua bloqueando.
- Parada usa o `SIGQUIT` já definido pela imagem e `docker stop --timeout -1`, sem SIGKILL. Pode haver interrupção breve de acesso. Se o encerramento não for confirmado, o executor para sem remover/recriar o container; o journal permite recuperação posterior aprovada.

## Caminho protegido

Workflow `Nginx Compose provenance`, somente despacho manual em `main` para operações remotas, ambiente `production` e credencial operacional já usada nos releases. Antes da consulta SSH, o workflow exige CI de push da mesma main e prova Docker desta change. O wrapper confirma main no remoto e executa em memória somente o blob Python pinado. Os fingerprints completos são argumentos de aprovação e nenhuma exceção bruta é exibida.

Se uma guarda anterior ao módulo recusar a execução, o wrapper emite somente um código constante da allowlist (por exemplo, falha ao ler a origem, origem não reconhecida, divergência de checkout ou revisão remota); stderr bruto dos comandos e valores de entrada são omitidos. Para a origem Git, somente formas HTTPS/SSH exatas do `github.com/conradodeita/markina-gallery` são aceitas, sem credenciais na URL. Isso identifica a pré-condição a revisar sem enfraquecer guardas ou imprimir configuração.

O job `isolated-proof` de PR/push não acessa Oracle, segredos ou clientes. Ele usa Compose 2.35.1 com checksum fixado e Nginx de teste para publicação e recuperação em namespaces descartáveis.

## 1. Inventário e plano de preparação

Despachar `operation=inventory`. Ele consulta metadados do projeto, imagem e os três arquivos reportados por `nginx -T`; não escreve nem pausa serviços. A resolução do candidato passa a consistência normal do Compose por stdin. O recibo contém hashes, versão Compose, contagem de peers, imagem e porta; não contém dumps, conteúdo de configuração ou variáveis.

Apresentar `approval_fingerprint`, `bundle_id`, ID da imagem, número de peers, porta/domínio, duas montagens adicionais e escopo de armazenamento. O plano de **preparação** cria somente a pasta durável da operação e chave HMAC própria, separada do backup, sob deploy-state; não altera segredos de integrações. Requer aprovação desse plano antes de `operation=prepare`.

## 2. Preparação do backup

Despachar `operation=prepare` com `approval` integral do inventário aprovado. A trava existente `production-release.lock` é adquirida sem bloqueio concorrente. Inventário é refeito e comparado antes da primeira escrita. O backup contém somente inspect do Nginx, configuração e cópias dos três arquivos; dados dos demais containers permanecem somente como hashes. Diretórios são 0700 e arquivos 0600, exclusivos, sem symlinks/hardlinks.

O manifesto assinado por HMAC-SHA256 é relido e autenticado com chave própria guardada separadamente. São conferidos conteúdo, plano, modelo Compose resolvido, permissões e ausência de mudança de runtime durante o preparo. O resultado necessário é `backup_verificado`. Falha deixa evidência para revisão e nunca sobrescreve preparo parcial ou backup anterior.

## 3. Plano final e publicação

Com CI verde e backup remoto verificado, apresentar novamente snapshot/fingerprint, imagens, porta/domínio, janela, impacto e recuperação. Aguardar a aprovação humana específica prevista na task 3.1; aprovação de ambiente GitHub, proposta ou implementação isoladamente não substitui esse plano.

Despachar `operation=release`, `bundle` e `approval` exatos. O executor autentica o backup, valida novamente o Compose e reconsulta o runtime. Qualquer divergência aborta antes de parada. O journal `execution.json` é persistido antes da parada, que precisa ser reconhecida. Em seguida executa somente `compose ... up -d --no-deps --no-build --pull never nginx`, usando a origem persistente. Não usa `--remove-orphans`, `down`, stop forçado ou alteração de outro container. Se a publicação falhar depois da parada e a recuperação tiver sucesso, o recibo restrito grava apenas um código constante sanitizado da falha, nunca saída de subprocesso, valor de configuração ou mensagem bruta.

Após a troca: comparar imagem, propriedades operacionais, aliases, políticas, origem/destino/read-only das três montagens e bytes dos três arquivos; validar `nginx -t`, saúde, HTTP 200 em `/healthz`, `/api/health` e `/`; comprovar igualdade dos demais containers. Identificador do Nginx e labels Compose de proveniência são alterações esperadas. A projeção compara variáveis ordenadas por nome e valores vazios equivalentes documentados da API Docker, sem ocultar mudanças de política. As montagens são comparadas separadamente porque as duas origens persistentes adicionadas fazem `HostConfig.Mounts` diferir de forma intencional.

## Recuperação

Falha posterior à parada confirmada aciona recuperação automática delimitada ao Nginx. O executor confirma projeto, nome, imagem e origem esperada do alvo, encerra graciosamente eventual candidato e remove somente o container já parado, sem `--force`. Recria pela API local Docker com a imagem imutável e configuração anterior autenticada, usando os três arquivos do backup. Rede/aliases/políticas anteriores são preservados e a mesma verificação de saúde/HTTPS/peers é repetida.

O caminho de recuperação não depende do arquivo RAW ausente. O corpo de criação omite `HostConfig.Mounts` retornado por `inspect`, para que não concorra com as três origens autenticadas de `Binds`. A validação pós-recuperação compara as montagens com essas três origens seladas, enquanto a validação da publicação compara com as origens do candidato; ambas também conferem os bytes esperados. As labels antigas são preservadas na recuperação; portanto recuperar acesso não declara a proveniência reconciliada. Resultado `publicacao_falhou_recuperada` exige revisão antes de nova tentativa.

Interrupção ou parada não confirmada pode exigir recuperação humana: despachar `operation=recovery-inventory` com bundle/approval originais. Conferir o estado e aprovar o novo `recovery_fingerprint` antes de `operation=recover` com `recovery_approval`. Mudança dos demais containers ou alvo inesperado impede a ação. Falha de recuperação gera `recuperacao_requer_operador`; não repetir com fingerprints presumidos, não forçar stop e não restaurar banco.

## Retomada APP_ENV e retenção

Somente após publicação comprovada repetir o inventário APP_ENV oficial. Seus bloqueios e aprovações continuam próprios; não alterar o coletor para aceitar fonte ausente e não antecipar liberação real do Mercado Pago. Preservar backup, chave HMAC, fontes persistentes e journals após o release; remoção futura exige inventário/revisão próprios, pois os containers passarão a depender dessas fontes.
