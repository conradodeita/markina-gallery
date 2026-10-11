# Desenho da avaliação de embeddings faciais e multimodais

## Escopo isolado

O harness SHALL executar fora do fluxo da aplicação, sem API, PostgreSQL, Redis, worker facial de produto ou escrita nos índices biométricos existentes. O motor atual continua sendo a referência operacional. O cenário principal reproduz a operação pretendida: embeddings faciais gerados antecipadamente após upload; consultas de referência por foto enviada e por região facial tocada; múltiplos fotógrafos com múltiplos clientes concorrentes. Resultados são descartáveis; o relatório versionado contém somente números agregados, versões, hashes de pesos e limitações, sem imagens, embeddings, nomes, UUIDs de pessoas ou caminhos sensíveis.

## Candidatos

1. **Atual:** detector YuNet e reconhecedor SFace do OpenCV, atualmente usado pelo produto, saída facial de 128 dimensões.
2. **EmbeddingGemma 2:** `google/embeddinggemma-2`, processado localmente. Testar entrada de imagem inteira, crop facial alinhado e crop com contexto. Testar 768, 512, 256 e 128 dimensões; normalizar novamente após truncamento.
3. **Especializado adicional:** candidato ArcFace/InsightFace ou equivalente somente após identificar artefato, revisão, dependências e licença comercial inequívoca de código e pesos. Pesos públicos InsightFace/Buffalo e pesos EdgeFace previamente avaliados não podem ser presumidos licenciados para uso comercial. SFace já é um baseline facial especializado e não deve ser contado como modelo distinto do atual.

O detector, alinhamento e bounding boxes serão iguais entre comparadores sempre que o formato de entrada permitir. Diferenças inevitáveis do pré-processamento devem ser registradas. Nenhum embedding de candidatos distintos será misturado ou consultado no índice do produto.

## Configuração global com roteamento por galeria

A interface administrativa SHALL ser restrita ao `PlatformOwner` validado por `InstallationOperator` ativo, usando os gates existentes; ser administrador ou owner de um tenant não concede esta permissão. Um único controle global alterna entre “Usar SFace” e “Usar Gemma”. SFace permanece o padrão. A escolha Gemma inicia a indexação somente para galerias criadas a partir do primeiro instante de ativação; galerias anteriores continuam usando SFace. Uma galeria nova só usa Gemma após todos os ativos elegíveis estarem indexados e atuais em Gemma. Enquanto houver cobertura pendente, falha ou divergente, essa galeria usa SFace integralmente. A decisão de engine é fixada em cada busca. Nenhuma configuração global substitui consentimento, política, autorização ou retenção já exigidos por galeria.

A implementação acrescenta uma tabela global de configuração sem `tenant_id`, acessível somente no endpoint sob o gate do proprietário; a inclusão é classificada como infraestrutura compartilhada no catálogo de ownership. O worker Gemma usa o profile opcional `facial-gemma`, que não é ativado pelo profile facial existente. É outro serviço e imagem, com PyTorch/Transformers fora do runtime SFace, revisão do modelo fixada e pesos provisionados localmente na construção dessa imagem. Ele confere um marcador de revisão antes de iniciar e reporta heartbeat próprio. A ativação grava `enabled_since`; a fila Gemma exige também `ParentGallery.created_at > enabled_since`, impedindo indexação de galerias antigas mesmo por reconciliação. O detector/alinhador existente é reutilizado, mas não executa o embedding SFace durante os jobs Gemma. O registro passa pelo mesmo envelope de criptografia e ciclo de exclusão, com `model_id`, versão e dimensão 768 separados. Busca por imagem enviada e por rosto clicado usa o mesmo engine selecionado para a galeria, sem misturar namespaces ou dimensões; consultas persistem o engine escolhido para sobreviver a mudanças globais enquanto aguardam worker/fila.

Ativar Gemma não significa inferir retroativamente galerias já criadas. A indexação inicia apenas em galerias novas após a ativação, segundo as políticas existentes; backfill do acervo já existente fica fora desta change. Trocar para SFace pausa novos jobs Gemma sem apagar embeddings nem comprometer SFace; galerias já cobertas podem voltar a Gemma quando o proprietário reativar a opção. Destruição do índice exige procedimento de exclusão separado.

O seletor SHALL poder ser exercitado em homologação privada, sob autorização explícita por execução, e não habilita produção. A troca SHALL ser reversível, preservar ambos os namespaces e escolher um engine por galeria segundo cobertura completa; nenhum vetor será convertido entre modelos. Se a cobertura Gemma não alcançar todas as fotos elegíveis de uma galeria nova, preservar a busca SFace completa em vez de degradar silenciosamente a experiência.

A escolha verifica cobertura de todos os ativos elegíveis da galeria, incluindo pastas restritas; isso não revela ativos a clientes nem amplia o snapshot autorizado. Jobs devem corresponder à chave da geração atual, à fonte/fingerprint atual high-res ou à prévia limpa vigente. Heartbeat futuro ou antigo e ambiente de produção mantêm SFace. Regiões de ambos os modelos respeitam autorização por pasta, e notificações continuam pelo worker de busca existente com configuração de transporte vigente.

O runtime ainda reutiliza o limiar operacional configurado para a busca atual; esse valor não constitui calibração Gemma. Resultados do seletor servem à avaliação privada e SHALL NOT fundamentar recomendação de substituição nem liberação de produção até a calibração separada da seção de benchmark.

## Corpus e protocolo

### Publicação autorizada em homologação

A compatibilidade efetiva SHALL ser validada nativamente: ARM64 no container sintético exclusivo do servidor e AMD64 no runner GitHub hospedado, em job CI dedicado que também condiciona o deploy. Ambos SHALL limitar build a 2 GiB/1 CPU e inferência a 6 GiB/1 CPU, sem rede, banco ou fotos operacionais na inferência. O teste SHALL gerar uma imagem sintética em memória e verificar vetor finito 768d, normalização e repetibilidade; não representa um benchmark de eficácia facial.

Após a autorização de 11/10/2026 para push, merge e deploy, o runtime SHALL ser validado com entrada sintética e orçamento explícito de memória/CPU antes da primeira ativação operacional. O host Oracle ARM64 inventariado possui memória suficiente; a máquina Windows permanece com pouca RAM disponível e não SHALL carregar o modelo sem orçamento compatível. Builds de validação SHALL usar diretório e recursos exclusivos, sem montar banco ou mídia operacional.

O deploy SHALL seguir CI e merge em develop, manter SFace como configuração inicial e aplicar somente as migrations aditivas 0073/0074 após backup verificável e pausa dos escritores próprios. A primeira inicialização do worker SHALL ocorrer explicitamente pelo profile facial-gemma depois do schema compatível; não altera a escolha global nem reindexa galerias antigas. Deploys posteriores SHALL descobrir o worker Gemma já ativo, incluí-lo em build, pausa antes de Alembic, recriação e healthchecks. Retomada de containers existentes SHALL incluir Gemma somente quando seu container existir; manutenção destrutiva autorizada em outra execução SHALL reconhecer e pausar esse leitor antes de excluir dados, restaurando-o depois. Nenhuma rotina SHALL iniciar Gemma apenas porque o profile facial está ativo. Rollback de código para revisão sem definição Gemma SHALL parar exclusivamente esse worker antes de trocar o checkout; não haverá downgrade nem restauração automática de banco.

Inventário e plano SHALL registrar SHA/schema, porta 127.0.0.1:8080, origem HTTPS vigente, recursos de outros projetos preservados e limites de reversão. Segredos e arquivos de ambiente SHALL permanecer intactos nesta entrega. A falha preexistente do worker geral SHALL ser delimitada antes da publicação, sem alegar ambiente saudável enquanto ele estiver parado.

### Integração high-res e monitor

Na primeira provisão operacional, o estado persistido do overlay de monitor SHALL receber somente a entrada do novo serviço Gemma, com os parâmetros de monitor já configurados para face-index-worker. A operação SHALL validar o Compose candidato, preservar semanticamente as entradas existentes, criar backup restrito e não editar .env/segredos. Configuração Gemma existente divergente SHALL exigir reconciliação, sem sobrescrita silenciosa. Somente Gemma SHALL ser recriado para aplicar essa inclusão, com a escolha global SFace preservada.

A inferência Gemma SHALL proteger a leitura da fonte pelo lease do seu próprio job, sem manter lock de PhotoAnalysis durante o cálculo; SFace e geração de prévias não podem aguardar a inferência experimental. Antes da persistência, o engine SHALL reler a identidade da fonte (fingerprint, expiração e versão de pipeline), recusando resultado de fonte alterada/excluída. A proteção de cleanup por lease ativo existente permanece obrigatória. O orçamento exclusivo do lease Gemma SHALL ser 900 segundos por padrão, limitado pelo contrato existente, sem alterar os 120 segundos SFace. A medição ARM64 sintética de 34,4 segundos por crop com 1 CPU motivou esta separação e não autoriza alegação de eficácia ou de throughput.

Fotos aderentes ao lifecycle high-res SHALL enfileirar Gemma na finalização da mesma fonte temporária, com chave própria por revisão/generation/retention. Gemma SHALL NOT alterar estado, métricas ou fila de ajuste pertencentes à análise SFace. Apresentação continua liberada exclusivamente por SFace; jobs Gemma pendentes preservam a fonte somente até o TTL vigente, sem renovar retenção. Um lease ativo de qualquer leitor protege contra exclusão concorrente; após TTL, jobs Gemma sem fonte falham e a busca permanece SFace. Desligar Gemma libera a retenção adicional de jobs ainda não iniciados. Fontes descartadas SHALL NOT ser reanalisadas a partir de prévias.

O Monitor do Sistema SHALL incluir filas Gemma nos totais faciais de busca/indexação e reconhecer heartbeat, duração e erros do worker `gemma` como dimensão fixa, sob os mesmos gates e sanitização. A configuração do overlay SHALL alcançar o worker dedicado. CPU/RAM do host continuam medidas agregadas da fonte existente; não alegar atribuição por modelo. Ausência de runtime/host SHALL permanecer uma lacuna explícita.

Usar lote real fornecido especificamente para esta execução, acompanhado por rótulos de identidade pseudonimizados e separação por evento/câmera/tempo para evitar vazamento entre referência e consulta. Documentar categorias de tamanho, pose, iluminação, flash, oclusão, crianças e semelhança visual apenas quando houver cobertura e permissão adequadas. Ausência de amostras em uma categoria será declarada, não inferida.

Comparar candidatos nos mesmos exemplos e partições. Calibrar threshold somente no conjunto de validação, priorizando falsa aceitação/identificação errada; manter teste final separado. Variar Top-K e margem entre primeiro e segundo candidato. Reportar top-1/top-5, precision, recall, FAR/FPR, FRR/FNR, identificação correta, rejeição correta de desconhecidos e curvas de threshold; não converter similaridade em probabilidade de identidade.

Medir tempo por rosto, throughput, RAM de pico, VRAM se houver GPU disponível, CPU, tamanho do modelo, dimensão e custo de armazenamento dos vetores. Registrar hardware e runtime reais. BFloat16 será considerado somente em GPU compatível; no alvo ARM/CPU existente comparar float32 e não assumir disponibilidade de GPU.

## Trilhas multimodais

O objetivo desta avaliação é identidade facial. Busca de cenas por texto, como “casal se beijando”, não é requisito nem métrica de seleção do motor. EmbeddingGemma poderá ser recomendado para identidade somente se superar ou complementar SFace nos mesmos exemplos anotados e cumprir as metas operacionais. A semântica multimodal poderá ser reavaliada em change separada.

## Carga e concorrência multi-fotógrafo

Além do custo por foto, o benchmark deverá caracterizar tempo de indexação e duração para drenar lotes por fotógrafo, latência p50/p95/p99 das consultas por referência/click, throughput sustentado, fila, pico e recuperação após rajadas em níveis de concorrência representativos. Reportar consumo e custo total do modelo residente e distinguir custo compartilhado de custo por consulta. Isolamento e fairness por tenant são requisitos distintos de throughput agregado: não alegar capacidade multi-tenant equivalente se o cenário medido não usar tenants/sessões independentes e se o produto não oferecer quotas/fairness verificáveis.

## Privacidade e bloqueios

Não procurar nem selecionar fotografias arbitrárias nos discos, galerias ou homologação. A execução real começa somente depois de receber o lote e de registrar origem, finalidade e autorização humana explícita da execução. Exigir acesso autenticado, armazenamento cifrado, diretório efêmero restrito, retenção mínima, rotina de exclusão verificada e nenhuma transferência externa. Menores só podem integrar lote se os requisitos específicos de autorização e proteção aplicáveis à homologação estiverem documentados; benchmark não habilita produção.

## Decisão

Nenhum limiar, engine ou índice de produção é alterado. O relatório final recomendará manter SFace, substituir por um candidato elegível ou adotar arquitetura híbrida somente com evidência comparativa do teste real. Sem corpus autorizado/anotado, a decisão permanece inconclusiva e tarefas do benchmark real não serão marcadas como concluídas.
