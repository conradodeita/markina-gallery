# Markina Gallery — Especificação de Execução para Claude Code

## 1. Mandato e resultado esperado

Implemente a **Markina Gallery**, plataforma self-hosted de gestão, prova, venda e acompanhamento de fotografias escolares e de eventos. O produto deve priorizar:

- poucos passos e navegação mobile-first para responsáveis;
- administração operacional rápida para um fotógrafo;
- galerias privadas importadas do DigiKam;
- eventos coletivos cujo acervo é privado ao fotógrafo e cujos resultados faciais são liberados individualmente;
- segurança, privacidade e operação resiliente.

Não substituir o culling, a edição nem a entrega final do fotógrafo. O sistema recebe apenas JPEGs exportados após o culling. RAWs e edição de imagem final estão fora de escopo.

Leia também [ROADMAP_ARQUITETURA.md](ROADMAP_ARQUITETURA.md) e [DIRETRIZES_FRONTEND_MARKINA_GALLERY.md](DIRETRIZES_FRONTEND_MARKINA_GALLERY.md). Em caso de conflito, esta especificação é a fonte operacional; decisões de segurança, privacidade e UX dos documentos complementares permanecem obrigatórias.

## 1.1 OpenSpec é obrigatório

Use **OpenSpec** como processo de desenvolvimento orientado a especificações durante todo o projeto. Esta especificação é o documento de partida; após a inicialização, as specs consolidadas em `openspec/specs/` serão a fonte de verdade do comportamento implementado.

1. Inicialize o OpenSpec no repositório para **Claude Code**, usando o perfil spec-driven/core recomendado pela ferramenta e mantendo o `AGENTS.md` gerado/gerenciado pelo OpenSpec.
2. Criar as specs base por domínio antes da primeira implementação: `auth`, `client-access`, `gallery-sales`, `media-storage`, `messaging`, `privacy-biometric` e `deployment-operations`.
3. Cada unidade de trabalho deve ter um `change-id` legível sob `openspec/changes/` e conter proposta, delta specs, design quando houver decisão técnica e `tasks.md` verificável.
4. Não escrever código de uma funcionalidade antes de a proposta/spec correspondente ser revisada e aceita pelo proprietário.
5. Implementar pelo `tasks.md`, marcar itens concluídos somente após teste adequado e executar validação do OpenSpec.
6. Depois de validado e implantado, sincronizar a mudança às specs principais e arquivá-la. `openspec/specs/` deve sempre descrever o que está efetivamente em produção.

Fluxo padrão para cada mudança:

```text
/opsx:explore (quando houver dúvida)
  → /opsx:propose <change-id>
  → revisão humana das artifacts
  → /opsx:apply
  → testes + validação
  → /opsx:sync
  → /opsx:archive
```

Começar pela mudança `bootstrap-photocrm-foundation`, que cria infraestrutura, padrões, specs iniciais e a base mínima do projeto. Não criar um único change gigante que tente implementar o produto inteiro.

## 1.2 Continuidade obrigatória entre executores

O projeto poderá ser continuado por Claude Code, Codex, DeepSeek ou qualquer outro executor. **Nenhum executor pode depender do histórico da conversa para entender o projeto.** O repositório deve ser a fonte completa de contexto.

- Antes de qualquer ação, ler este mandato, `ROADMAP_ARQUITETURA.md`, `DIRETRIZES_FRONTEND_MARKINA_GALLERY.md`, `openspec/config.yaml`, specs principais e mudanças ativas.
- Toda funcionalidade ou alteração de comportamento deve possuir `change-id` próprio com proposal, delta spec, design quando houver decisão técnica e tasks antes da implementação.
- Toda decisão nova, desvio do plano, limitação, risco ou bloqueio deve ser registrado nos artefatos OpenSpec ou na documentação técnica correspondente.
- Durante a execução, atualizar `tasks.md`, testes e documentação junto com o código. Não marcar tarefa como concluída sem evidência verificável.
- Ao finalizar, executar testes e validação OpenSpec, sincronizar somente o comportamento realmente implementado para `openspec/specs/` e arquivar a mudança após revisão humana.
- Nunca declarar como implementado, validado, testado ou implantado algo que não tenha evidência no repositório ou no ambiente informado.
- Se uma etapa não puder ser executada, registrar o bloqueio e o próximo passo necessário para o executor seguinte.

O próximo executor deve conseguir retomar o trabalho lendo apenas o repositório, sem depender de memória externa, mensagens anteriores ou conhecimento implícito.

## 2. Limites de escopo

### MVP obrigatório

1. Fundação Docker, Next.js, FastAPI, PostgreSQL, Redis, worker e Nginx.
2. Área administrativa de um único fotógrafo com autenticação segura.
3. Clientes/responsáveis, pessoas fotografadas, eventos, bibliotecas, pastas, galerias, fotos, tags e histórico.
4. Importação confiável de JPEGs e XMP do DigiKam para galerias privadas.
5. Galeria mobile-first, favoritos/carrinho, preços por faixas, checkout e PIX manual.
6. Controle de produção/edição por foto, pedidos e entrega por link de Google Photos.
7. WhatsApp via adaptador, com OTP e fila de mensagens; implementação concreta pode começar em modo sandbox.
8. Armazenamento local, espelhamento/arquivamento em Google Drive, painel de capacidade e backups.
9. Auditoria, central de pendências e testes fundamentais.

### Pós-MVP, porém preparar interfaces e dados

- Infinity Pay por cartão, por meio de um `PaymentProvider` e webhooks assinados.
- Busca facial: implementar apenas depois de um spike de compatibilidade ARM, licença comercial, desempenho e precisão.
- Múltiplos administradores, impressos, laboratórios, produtos físicos e edição dentro da plataforma.

### Limite de personalização visual

Markina Gallery não é um CMS completo de páginas. O fotógrafo pode configurar identidade simples e opções controladas por galeria — cor, tipografia do nome, capa e layouts suportados — mas não terá construtor de páginas, editor livre de HTML/CSS ou coleção de templates de website. Consulte `DIRETRIZES_FRONTEND_MARKINA_GALLERY.md` para a direção completa do frontend e `docs/frontend-reference/README.md` para o uso do protótipo visual.

O export do Google Stitch em `docs/frontend-reference/stitch-export/` é somente referência visual e funcional. **Não copiar diretamente seu código, componentes, mocks, dados, dependências ou estrutura para a aplicação oficial.** Reconstruir o frontend no stack oficial e conectá-lo às APIs, autenticação, permissões, regras de negócio e specs OpenSpec vigentes.

### Não fazer

- Não expor uma grade pública de fotografias escolares de evento coletivo.
- Não servir prévias diretamente do Google Drive.
- Não automatizar criação/compartilhamento de álbuns no Google Photos; o fotógrafo cria o link manualmente.
- Não armazenar RAWs, nem tentar editar fotos no sistema.
- Não copiar código, design ou componentes de serviços concorrentes.

## 3. Infraestrutura e arquitetura

```text
Internet → Nginx (HTTPS) → Next.js
                       └→ FastAPI → PostgreSQL
                                   → Redis → worker de filas
                                   → volume local de prévias/miniaturas
                                   → Google Drive (arquivo, cópias e backups)
                                   → adaptadores WhatsApp / pagamentos
```

- Frontend: Next.js App Router, TypeScript, Tailwind CSS, responsivo e acessível.
- Backend: FastAPI, SQLAlchemy 2, Alembic, Pydantic, Python.
- Banco: PostgreSQL. Usar UUIDs públicos, UTC no banco e valores monetários em centavos inteiros.
- Fila: Redis + Celery ou RQ. Importação, miniaturas, Drive, mensagens e processamento de imagem nunca podem depender do ciclo HTTP.
- Arquivos: volume local para ativos quentes; objetos do Drive são backup e arquivo frio.
- Imagens: Pillow/libvips/ImageMagick de modo seguro, com validação real de MIME, dimensão e limites de tamanho.
- Observabilidade: logs estruturados, health checks e correlação de job/request.

Use Docker Compose com serviços isolados. Não expor PostgreSQL ou Redis à internet. Todos os segredos ficam em `.env` não versionado ou secret store do servidor.

## 4. Autenticação e segurança

### Administrador

Há um administrador no MVP, sem registro público.

- E-mail verificado, senha hash Argon2id e política de senha forte.
- Recuperação por e-mail: token único, com hash no banco, expiração curta e invalidação após uso.
- 2FA TOTP compatível com Google Authenticator; gerar códigos de recuperação de uso único, armazenados como hash.
- WhatsApp validado para troca de número, recuperação controlada e confirmação de ações sensíveis: PIX, exclusões, desativação de 2FA e troca de senha.
- Sessões seguras em cookie `HttpOnly`, `Secure`, `SameSite`, revogáveis; listar sessões/dispositivos e encerrar todas.
- Rate limit e respostas neutras em login, reset e OTP para não enumerar contas.

### Cliente/responsável

- Sem senha permanente: nome + telefone + OTP WhatsApp.
- Sessão configurável, padrão de 7 dias; renovação por OTP.
- Convite: token opaco aleatório, hash no banco, uso único, expira em 72 horas, revogável e reenviável.
- O vínculo de acesso pertence ao cliente/responsável, não ao token; após ativação, acessos posteriores usam OTP.

### Entrada unificada e roteamento

- Usar uma única tela/rota de entrada para `Cliente` e `Fotógrafo`, com escolha explícita do contexto na mesma experiência visual.
- Cliente informa nome completo e telefone, recebe OTP pelo WhatsApp e, após validação, é encaminhado à galeria autorizada ou à biblioteca quando possuir várias galerias.
- Fotógrafo informa e-mail e senha, valida TOTP do Google Authenticator/compatível e, somente após os dois fatores, é encaminhado à área administrativa.
- O papel e o destino final são decididos e revalidados pelo backend; frontend, URL ou estado local nunca concedem autorização.

### Auditoria, incidente e configurações externas

Registrar login, falha, reset, 2FA, convite, ativação, exclusão, pagamento, mudanças de PIX, entrega e operações biométricas. Implementar função administrativa de revogar sessões, tokens e convites. Configurar SMTP transacional com SPF/DKIM/DMARC no deploy.

## 5. Modelo de domínio

Criar migrations, índices e constraints. Todos os dados operacionais importantes têm `created_at`, `updated_at` e, quando fizer sentido, `created_by`.

### Núcleo

- `admin_user`: e-mail único, senha, e-mail verificado, TOTP, telefone verificado, último acesso.
- `client`: nome, telefone E.164 único, e-mail opcional, origem e preferências de comunicação.
- `person`: pessoa fotografada; nome, referência opcional e dados mínimos necessários.
- `client_person`: N:N entre responsáveis e pessoas. Mãe e pai podem acessar a mesma criança; um responsável pode acessar várias pessoas.
- `event`: título, data, descrição, status, capacidade/arquivamento.
- `library`: biblioteca privada de uma família/responsável, com relação ao evento quando aplicável.
- `gallery`: tipo `private_digikam | collective_face_result`; título, capa, layout, visibilidade, datas de seleção/pagamento, regras de venda, status e configurações de proteção.
- `folder`: estrutura de pastas dentro de galeria/evento.
- `photo`: arquivo JPEG, hash, dimensões, caminho local, caminho Drive, metadata sanitizada, status de venda e status global de produção.
- `gallery_photo`: foto dentro da galeria/pasta, com ordenação e visibilidade.
- `gallery_access`: cliente autorizado, galeria, status `pending | active | rejected | expired`, método, token/convite e auditoria.

### Seleção e vendas

- `selection`: rascunho persistente por cliente + galeria; acessos, última atividade e expiração.
- `selection_item`: uma foto selecionada; não duplicar foto na mesma seleção.
- `price_rule`: faixa mínima/máxima e preço unitário em centavos. Aplicar a faixa inteira ao pedido.
- `order`: cliente, galeria, status, subtotal, desconto, total, snapshot de regras/comunicação.
- `order_photo`: foto, preço unitário e total congelados no pedido.
- `payment`: provedor, status, valor, payload seguro, QR/copia-cola, confirmado por quem e quando.
- `delivery`: por pedido, link Google Photos, estado, mensagem enviada, disponibilizado/em que data e confirmação opcional do cliente.

### Operação e comunicação

- `tag`, `tag_assignment`: tags por pedido, cliente+galeria e foto quando necessário.
- `photo_production`: estado global por foto (`not_sold`, `sold`, `editing`, `edited`), notas e timestamps. Não impedir nova venda por outro responsável.
- `message_template`, `message_delivery`: templates versionáveis, renderização, fila, tentativa, erro e opt-out comercial.
- `activity_log`: eventos de acesso, seleção, checkout, pedido, importação e administração.
- `storage_snapshot`, `import_job`, `import_file_result`, `background_job_error`.
- `system_config`: branding, PIX, limites, mensagens e integrações.

### Biometria (schema preparado, feature desativada inicialmente)

- `biometric_consent`, `face_reference`, `face_embedding`, `face_search`, `privacy_request`.
- Criptografar ou isolar segredos/embeddings, registrar prazo de retenção e exclusão/revogação.
- Nenhuma busca fora do evento solicitado.

## 6. Regras de negócio

### Galerias privadas DigiKam

- O fotógrafo faz a separação no DigiKam antes do upload.
- Ler JPEG + XMP, extraindo apenas metadados necessários: nome/região/keywords quando disponíveis.
- Importar para biblioteca/galeria privada e autorizar um ou mais responsáveis.
- O cliente vê pastas por evento/ano e apenas as fotos autorizadas.

### Eventos coletivos

- Acervo completo é somente administrativo.
- Não criar URL pública de grade de fotos.
- Futuramente, busca facial gera resultado privado; responsável valida telefone, aceita termo, fica pendente, fotógrafo revisa e só então ativa convite individual.

### Seleção, preços e pagamento

- Exigir login por telefone e OTP antes de entregar qualquer prévia fotográfica. Capa e informação sem fotografia identificável podem permanecer públicas quando a Galeria pública permitir; `standard`, `invite_only` e `collective_protected` são decididos e impostos pelo backend.
- Mostrar marcador visual de favorito, contador sticky e valor estimado somente após autenticação.
- Implementar preço por faixa aplicado a todas as fotos do pedido. Exemplo: 1–30 = R$7, 31–59 = R$6, 60+ = R$5.
- Painel deve simular os totais e alertar ao fotógrafo se subir uma faixa diminuir o total comparado à faixa anterior.
- No checkout, congelar fotos, quantidade, regra, valor e texto de venda. Pedido posterior não altera pedido já criado.
- PIX: criar pedido `awaiting_payment`; botão “já paguei” muda a `payment_reported`; só confirmação manual torna as fotos `paid` para aquele cliente.
- Cliente pode voltar à galeria ativa e fazer novo pedido de fotos ainda não pagas. Fotos confirmadas em pedidos desse cliente não entram novamente no carrinho; permanecem vendáveis para outros responsáveis.
- Tratar cancelado, reembolsado, não localizado e pagamentos duplicados.

### Edição e entrega

- Pagamento confirmado gera mensagem configurável “em edição”.
- Painel permite marcar fotos como edição/concluída. Se uma foto já estiver `edited`, nova venda deve informar isso ao fotógrafo.
- Fotógrafo cola manualmente o link do Google Photos no pedido e aciona “Disponibilizar entrega”.
- Portal do cliente exibe entregas mesmo após expiração de seleção: vermelho “Fotos disponíveis em breve”, amarelo “Em edição” ou botão verde “Acessar minhas fotos”.
- Ação disponibiliza o botão e dispara mensagem WhatsApp; registrar tudo.

## 7. Experiência do usuário

### Portal do cliente

- Mobile-first: 2 colunas no celular, 4 ou mais em desktop; carregamento progressivo e placeholders.
- Após autenticação e autorização, permitir alternar entre Galerias públicas abertas, galerias privadas derivadas e histórico comercial; a privada herda configuração e apresentação da Galeria pública sem conceder acesso às privadas de terceiros.
- Foto abre em ampliação; seleção é ação explícita por coração/check. Não selecionar involuntariamente ao ampliar.
- Rodapé fixo com número de fotos, estimativa e CTA de carrinho/finalização.
- Carrinho com miniaturas, remoção, preços, texto de venda e progresso até próxima faixa de desconto.
- Páginas mínimas: entrada/OTP, convite, biblioteca, galeria, carrinho/checkout, pedido e minhas entregas.
- Todo texto, cor, logo, capa e parte das mensagens deve ser configurável pelo fotógrafo.

### Proteção das prévias

- Gerar prévias de baixa/média resolução sem EXIF/GPS.
- Aplicar marca d’água textual configurável e, quando habilitado, grade diagonal/linhas com espessura, cor, espaçamento, opacidade e rotação configuráveis.
- Oferecer marca dinâmica com nome/telefone parcial/código do cliente, quando autenticado.
- Aplicar proteção à imagem que é servida, não apenas camada CSS.
- Informar que não é tecnicamente possível impedir captura de tela de forma absoluta; mostrar aviso configurável de direitos autorais.

### Administração

- Dashboard: clientes, galerias ativas, pedidos, pagamentos informados, edição, entregas e alertas.
- Central de pendências: falhas de importação, mensagens, pagamentos, convites, prazo, disco e futuras buscas faciais.
- Gestão de eventos, bibliotecas, galerias, fotos, tags, clientes, pedidos, mensagens, branding, PIX e armazenamento.
- Filtros e ações em massa: evento, pasta, tags, visibilidade, venda, edição, entrega, prazo e futura indexação facial.

## 8. Imagens, Drive e capacidade

- Prévia e miniatura de galerias ativas ficam no volume local Oracle; não usar Google Drive como CDN.
- Após importação local validada, enviar cópia verificada ao Drive em job retomável.
- Arquivar eventos antigos no Drive e liberar armazenamento local apenas após verificar arquivo íntegro. Reativação restaura conteúdo por job.
- Reservar 25% do disco local para banco, sistema, fila e processamento. Alertar e bloquear novas importações ao atingir 75% de ocupação configurável.
- Tela de armazenamento: total/usado/livre, uso por evento, média por JPEG e estimativa de fotos restantes baseada em média real.
- Importações idempotentes por hash e retomáveis após queda. Exibir arquivos importados, duplicados, pendentes e falhos com tentativa individual.
- Fazer backup diário cifrado do PostgreSQL no Drive e validar restauração em homologação.

## 9. Integrações por adaptadores

- `WhatsAppProvider`: OTP, mensagens transacionais, lembretes, status e erro. Inicialmente Evolution API; não acoplar regras de negócio ao fornecedor.
- `PaymentProvider`: PIX manual no MVP; Infinity Pay posterior com criação de cobrança, webhook assinado e reconciliação.
- `DriveStorageProvider`: upload resumível, checksum, retentativa exponencial, restauração e deleção controlada.
- `EmailProvider`: SMTP transacional para verificação e recuperação de senha.
- `FaceRecognitionProvider`: interface vazia/feature flag até concluir piloto; não ativar automaticamente.

## 10. Privacidade e biometria

- Fotos escolares e dados biométricos exigem minimização, transparência, consentimento específico de responsável e fluxo de exclusão. Não tratar isso como texto decorativo.
- Termo versionado, aceite auditável, finalidade explícita, expiração de referência facial e exclusão de embedding devem existir antes da feature ir a produção.
- Feedback facial cria revisão humana; nunca retreinar/aplicar associação automaticamente a partir de um único feedback.
- Dados reais de crianças nunca entram em homologação.

## 11. Ordem de implementação

1. Inicializar OpenSpec e propor `bootstrap-photocrm-foundation`; criar/revisar specs base, repo, Compose, CI, variáveis, ambientes e README de desenvolvimento/deploy.
2. Implementar banco, migrations, seed do administrador, login, e-mail, TOTP, sessões e auditoria.
3. Implementar CRUD administrativo de cliente/pessoa/evento/biblioteca/galeria/pasta/foto/tag.
4. Implementar importador JPEG/XMP, filas, miniaturas, watermark básico, hash e painel de jobs.
5. Implementar portal privado, OTP cliente, acessos, favoritos e carrinho.
6. Implementar regras de preço, checkout, pedidos, PIX manual e painel operacional de produção.
7. Implementar entrega por link Google Photos, WhatsApp e portal “Minhas entregas”.
8. Implementar Drive, arquivamento, métricas de armazenamento, backups e central de pendências.
9. Fortalecer testes, limites, proteção visual, observabilidade e deploy de homologação.
10. Executar spike facial isolado; só então decidir tecnologia, licença e rollout.

Não iniciar a fase facial antes de o restante estar funcional e validado em homologação.

## 12. Critérios mínimos de aceite

- Administrador consegue entrar com senha + TOTP, recuperar acesso e encerrar sessões.
- Importação interrompida pode ser retomada sem duplicar fotos.
- Mãe e pai autorizados veem a mesma pessoa, fazem pedidos independentes e uma foto editada não é reeditada indevidamente.
- Cliente consegue selecionar no celular, entende a faixa de preço, finalizar PIX e consultar o pedido.
- Após confirmação manual, a mesma foto não pode ser recomprada pelo mesmo cliente, mas pode ser comprada pelo outro responsável.
- Fotógrafo cola link de Google Photos uma vez, o cliente vê botão verde e recebe mensagem registrada.
- Galeria expirada bloqueia nova seleção, mas mantém pedidos e entregas acessíveis.
- Prévia não contém EXIF/GPS, respeita resolução/proteção configurada e não expõe originais.
- Disco, importações, mensagens e pagamentos com falha aparecem na Central de Pendências.
- Testes automatizados cobrem autenticação, autorização, cálculo de faixas, bloqueio de recompra, transições de pedido, importação idempotente e entrega.
- Homologação e produção usam bancos, segredos e integrações diferentes.

## 13. Entregáveis do executor

- Código versionado no repositório GitHub privado fornecido pelo proprietário.
- Diretório `openspec/` consistente, com specs base consolidadas e mudanças arquivadas após cada entrega aceita.
- `README.md` de desenvolvimento, `DEPLOY.md` de homologação/produção e `.env.example` sem segredos.
- Docker Compose, migrations, testes e scripts seguros de backup/restauração.
- Documento de decisões técnicas e limitações conhecidas.
- Checklist de deploy e rollback.
- Relatório do spike facial antes de qualquer ativação da feature.
