> **Decisão substitutiva — `simplify-gallery-access-modes`:** oferecer somente Padrão (link válido + OTP permite vínculo) e Somente convite individual (vínculo prévio ou convite autorizado). Ambos mostram pastas comuns e exclusivas atribuídas; `collective_protected` permanece somente como legado bloqueado, sem conversão automática nem promoção de vínculos pendentes. Na etapa 2, Pagamento obrigatório exige preços positivos. Desmarcado, a cliente finaliza seleção sem cobrança/PIX, sem preços ou totais, com snapshot individual, exportação e entrega posterior em Compras; isso não confirma pagamento nem registra receita. A mensagem comercial aparece por galeria na revisão. Gates faciais e de privacidade permanecem independentes e obrigatórios.

> **Decisão do proprietário em 24/09/2026 — `client-gallery-covers-and-payment-review`:** retirar o botão de feedback “Não é esta pessoa” da interface cliente. Esta decisão substitui a exigência visual anterior; endpoints, evidências históricas e proibição de treinamento automático permanecem. Cards de galerias/pastas passam a ter prévias clicáveis e recusa financeira pode voltar à revisão pela correção auditada e silenciosa existente.

> **Decisão substitutiva aprovada em 21/09/2026 — `simplify-mobile-gallery-face-search`:** para novas buscas, toque em região indexada inicia diretamente sem diálogo/aceite ou declaração de idade; upload continua exigindo consentimento específico. Upload infantil exige somente o checkbox único com autodeclaração de responsável e consentimento versionado, sem registro prévio ou prova administrativa de representação. Regras anteriores de representação obrigatória e dois checkboxes ficam substituídas exclusivamente nesse escopo; evidências/controles históricos permanecem. Nome/seleção ficam abaixo das miniaturas; navegação ampliada sempre visível em barra externa abaixo da fotografia, nunca sobreposta. Demais controles de acesso, retenção, revogação e operação permanecem. Contrato completo: `openspec/changes/simplify-mobile-gallery-face-search/`.

> **Entrega por pedido aprovada — `add-order-google-photos-delivery`:** o campo Google Photos substitui o histórico visual de mensagens. Enviar exige pagamento confirmado, disponibiliza botão verde “Fotos disponíveis” em Compras e agenda o sétimo evento configurável na central de Notificações. Sem entrega elegível, botão cinza “Fotos indisponíveis”. Reenviar aviso é explícito e deduplicado. Correção financeira preserva o link, suspende exposição e invalida avisos antigos; reconfirmação restaura disponibilidade sem aviso automático de entrega. Esta decisão substitui os cartões vermelho/amarelo e o disparo de entrega não configurável previstos abaixo. Filas técnicas e auditoria permanecem, sem backup paralelo do histórico visual.

# Pick-your-Pic — Roadmap Arquitetural

> **Decisão de galeria única — `unify-gallery-client-collections`:** a Galeria pública autenticada é a única galeria operacional. Cada pasta é comum ou atribuída a uma ou mais clientes; “Coleção” reúne somente as pastas comuns e atribuídas à pessoa autenticada. Seleções, compras, prazo e histórico permanecem por galeria + cliente. “Minha galeria” deixa de ser uma tela e links antigos redirecionam após autorização. A limpeza e os workflows remotos de homologação foram encerrados pela decisão do proprietário em 18/11/2026; essas cláusulas históricas não são executáveis.

> Direção detalhada de interface e UX: [DIRETRIZES_FRONTEND_MARKINA_GALLERY.md](DIRETRIZES_FRONTEND_MARKINA_GALLERY.md).

Documento vivo das decisões tomadas durante a arquitetura. Ainda não é a especificação de implementação para o executor.

## Princípios do produto

- Experiência mobile-first, com poucos passos para o responsável selecionar e comprar fotos.
- Painel administrativo robusto, porém direto para um único fotógrafo no MVP. Transição aprovada em 30/09/2026 na change `add-small-multi-photographer-pilot`: preparar e implementar localmente fotógrafos independentes, com clientes/telefones próprios da conta e permissão técnica separada para o dono da instalação. Substituição condicionada à fundação anterior validada, isolamento completo, preservação do legado e testes de engenharia; a instalação publicada continua de conta única até liberação autorizada. O ensaio pequeno ocorrerá assim que houver prontidão, sem ativação antecipada nem autorização implícita de deploy/canais/biometria.
- O produto tem duas áreas — administração do fotógrafo e portal do cliente — com comportamento de CMS apenas para conteúdo estruturado de galerias, não para construção livre de websites.
- Personalização visual controlada: cor da galeria, tipografia do nome, capa e templates suportados de organização; sem construtor de páginas ou múltiplos templates de website.
- Pastas restritas organizadas pelo fotógrafo dentro da galeria autenticada; busca facial limitada às fotos já autorizadas à cliente.
- Fotos exibidas são JPEGs exportados após o culling; RAW e edição final ficam fora do sistema.
- Google Photos é o canal de entrega final criado manualmente pelo fotógrafo; o sistema controla o link e a comunicação.

## Fase 0 — Fundamentos de engenharia

- Adotar OpenSpec como processo obrigatório: `openspec/specs/` representa o comportamento já consolidado; cada mudança nasce em `openspec/changes/<change-id>/` com proposta, delta specs, design e tarefas.
- Inicializar o OpenSpec para Claude Code e manter o `AGENTS.md` gerenciado pela ferramenta como instrução de fluxo para o executor.
- Antes de implementar qualquer fase ou alteração, criar e revisar uma proposta OpenSpec; após testes e deploy, sincronizar/arquivar a mudança para manter as specs como fonte da verdade.
- Criar specs iniciais por domínio: autenticação, acesso do cliente, galeria e seleção, preços e pedidos, mídia/armazenamento, mensagens, privacidade/biometria e deploy/operação.
- Criar repositório privado no GitHub, com `main` protegida, `develop`, branches de funcionalidade e pull requests.
- Configurar convenção de commits, `.gitignore`, documentação local e CI para lint, testes e build.
- Manter desenvolvimento local, CI efêmera e produção isolados; não criar ambiente operacional intermediário.
- Implantar via Docker Compose: proxy HTTPS, frontend, API, PostgreSQL, Redis e workers.
- Guardar chaves e segredos somente em variáveis seguras do servidor; nunca no Git, frontend ou tabelas comuns.
- Avaliar uma solução open source comum para backup global do PostgreSQL e arquivo/recuperação de pastas frias por fotógrafo. A prova SHALL incluir dados sintéticos, isolamento por tenant e recuperação verificada; raízes, chaves, namespaces e retenção permanecem separados. Candidatos atuais: Restic e Rclone, com Backrest opcional para operação. Preservar o contrato de prazo/créditos do arquivo frio descrito na change `add-gallery-media-archive` e no OpenSpec `prove-open-source-backup-and-recovery`.

## Fase 1 — Segurança e autenticação

### Administrador (um usuário no MVP)

- E-mail verificado, senha com hash Argon2id, recuperação por e-mail e sessão revogável.
- 2FA TOTP compatível com Google Authenticator, Authy e equivalentes.
- Códigos de recuperação de uso único, armazenados como hash, exibidos apenas na configuração inicial.
- WhatsApp validado para confirmação de ações sensíveis e recuperação controlada.
- Sem cadastro administrativo público; primeira conta criada por configuração segura de deploy.
- Listar sessões/dispositivos e permitir encerrar todas as sessões.
- Registrar log de login, falhas, recuperação, alteração de senha/2FA/telefone e operações críticas.

### Cliente/responsável

- Sem senha permanente: nome + telefone + OTP WhatsApp.
- Respostas neutras para impedir descoberta de contas por e-mail/telefone.
- Rate limit, expiração curta, limite de tentativas e auditoria de OTP.
- Token de convite com entropia alta, armazenado como hash, uso único e expiração de 72 horas.
- Acesso posterior por OTP; tokens podem ser revogados e reenviados pelo fotógrafo.

### Pendência não urgente — recuperação por OTP para proprietário e Tenants

- Em 25/11/2026, o proprietário não recebeu OTP pelo fluxo de recuperação por WhatsApp e conseguiu entrar com a senha existente após o bloqueio temporário expirar. Os registros sanitizados mostraram um desafio de recuperação sem vínculo a administrador/tenant e um reenvio `resend_simulated`; não comprovam envio de OTP. A causa exata permanece desconhecida.
- Antes da ampliação para novos Tenants, validar a recuperação por OTP de ponta a ponta para o proprietário e fotógrafos/Tenants: destino WhatsApp corretamente vinculado, envio real distinguido de sandbox/simulação, respostas neutras sem afirmar envio não realizado, rate limit, isolamento por Tenant e testes sintéticos para conta elegível/inelegível e canal indisponível.
- Prioridade: não urgente para o acesso atual, já restabelecido; manter no roadmap e concluir antes de depender desse fluxo em futuras contas Tenant.

### Dependências externas de segurança

- Escolher provedor SMTP transacional e configurar SPF, DKIM e DMARC no domínio.
- Criar procedimento de incidente: revogar sessões, tokens, convites e credenciais de integrações.

## Fase 2 — Base de dados e operação do fotógrafo

- Modelar `pessoa`, `cliente/responsável`, `cliente_pessoa`, eventos, bibliotecas, pastas, fotos, seleções, pedidos, pagamentos, entregas, tags, histórico e configurações.
- Permitir vários responsáveis para uma pessoa e várias pessoas para um responsável.
- Manter venda e entrega por cliente/pedido, mas status de produção por foto: não vendida, vendida, em edição, editada e entregue.
- Identificar foto já editada quando for comprada por outro responsável, sem bloquear a nova venda.
- Implementar Central de Pendências: importações, buscas faciais, clientes pendentes, mensagens falhas, pagamentos, expirações e disco.
- Aplicar filtros e ações em massa por evento, pasta, tags, venda, edição, entrega, prazo e indexação facial.

## Fase 3 — Galerias e vendas

- Pasta restrita: JPEGs já separados pelo fotógrafo, criada no card de uma cliente e atribuível a outras responsáveis autorizadas sem cópia.
- Galeria pública é uma denominação de produto, não acesso anônimo: nenhuma prévia fotográfica é entregue antes do OTP, e o backend oferece `standard` e `invite_only`; `collective_protected` permanece apenas como legado bloqueado, sem conversão automática.
- A galeria única fornece configuração efetiva a pastas comuns e restritas; fotos disponíveis e seleções comerciais continuam sendo estados distintos por cliente.
- Evento coletivo: nenhuma grade é anônima; clientes autenticados e vinculados podem visualizar somente a Galeria pública autorizada, enquanto qualquer ampliação de acesso por reconhecimento exige resultado privado aprovado.
- Cliente pode navegar, ampliar, favoritar e montar carrinho; identificação obrigatória na primeira intenção de compra.
- Carrinho persistente por cliente e galeria; histórico de acessos, favoritos, remoções e abandono.
- Preço por faixas dinâmicas: a faixa da quantidade será aplicada ao pedido inteiro, com simulador no painel e aviso de saltos de preço.
- Congelar fotos, preço, desconto e regras comerciais em cada pedido.
- Após pagamento confirmado, fotos daquele pedido ficam indisponíveis para recompra para o mesmo cliente, mas continuam disponíveis a outros responsáveis autorizados.
- Permitir compras adicionais durante o prazo da galeria; pedido e entrega permanecem acessíveis após o prazo.

## Fase 4 — Pagamentos, edição e entrega

- MVP: PIX com QR Code, copia-e-cola e confirmação manual do fotógrafo.
- Checkout de cartão indisponível durante a transição da InfinitePay para a integração posterior do Mercado Pago Orders API.
- Estados: seleção, checkout, aguardando pagamento, pagamento informado, confirmado, em edição, pronto, link enviado, entregue, cancelado, reembolsado e não localizado.
- Ao disponibilizar entrega, fotógrafo cola link do Google Photos, aciona mensagem WhatsApp e libera cartão verde “Acessar minhas fotos” no portal.
- Antes disso, o portal mostra cartão vermelho/amarelo: “Fotos disponíveis em breve” ou “Suas fotos estão em edição”.
- Registrar link, data/hora, pedido, mensagem enviada e confirmação de entrega opcional pelo cliente.

## Fase 5 — Imagens, armazenamento e proteção visual

- Oracle: servir JPEGs de prévia e miniaturas de galerias ativas; manter banco, filas e processamento.
- Armazenamento: cópia verificada dos JPEGs e arquivo frio por pasta; a nova solução open source cobrirá também o backup global cifrado do banco sem misturar os domínios de acesso.
- Google Photos: entrega manual final; não automatizar compartilhamento pela API.
- Limite operacional de 75% do disco local, com alerta e bloqueio preventivo de nova importação.
- Painel de armazenamento: uso atual, uso por evento, média por foto, estimativa de capacidade e candidatos a arquivamento.
- A pasta torna-se elegível ao arquivo frio após o prazo individual e 30 dias completos. O fotógrafo solicita a recuperação e escolhe 7, 14 ou 30 dias; a taxa configurável por pasta/ciclo é reservada e só debitada após restauração integral verificada. Falha libera a reserva; estado incerto exige reconciliação. O proprietário é isento e não há expurgo automático na primeira versão.
- Importação retomável e idempotente: hash por arquivo, fila, progresso, relatório de duplicados/falhas e retentativas.
- Proteção de prévias: limite de resolução, remoção de EXIF/GPS, marca d’água configurável, grade diagonal, linhas configuráveis, marca individual dinâmica e aviso de direitos autorais.
- Exceção de capa aprovada: capa vigente sem marca-d’água/grade, mantendo título, autenticação, autorização, prévia limitada e remoção de metadados; fotos de conteúdo permanecem protegidas. Novas capas devem ser horizontais após EXIF, sem recorte automático; capas antigas são preservadas até substituição.
- Declarar na interface que a proteção desencoraja cópia, mas não impede capturas de tela de forma absoluta.
- Ajuste automático opcional das prévias: módulo independente, desligado por padrão, motor substituível e resultados separados. Aplicar proteção depois do ajuste; preservar originais, prévias convencionais e análise facial. Desligamento retorna à prévia convencional na próxima requisição; prever higienização exclusiva conforme `add-optional-preview-auto-adjustment`. Edição final continua externa.

## Fase 6 — WhatsApp e comunicação

- Evolução aprovada em `configurable-push-and-whatsapp-notifications`: central `/admin/notifications` com seis eventos e dois canais independentes (WhatsApp/push); substitui inbox read/unread e editor de pagamentos em Configurações. Histórico e auditoria permanecem.
- Avisos ao fotógrafo: primeiro acesso e primeira seleção por cliente/galeria canônica; pagamento informado. Avisos ao cliente: novas prévias de pasta restrita prontas somente para destinatárias efetivas; pagamento confirmado ou recusado. Correções financeiras são silenciosas; falha de transporte não desfaz o negócio.
- Web Push exige adesão explícita por dispositivo, inscrição cifrada, VAPID externo, destino interno autenticado e worker sem cache privado. Lotes, marcos e entregas são duráveis/idempotentes; ligar canais não reproduz histórico. Operação real depende dos gates da release protegida e aprovação humana; CI usa dados sintéticos.

- Mensagens configuráveis para OTP, convite, pagamento, edição, entrega, carrinho abandonado e expiração.
- Separar mensagens transacionais de lembretes comerciais e registrar opt-out destes últimos.
- Fila com retentativas, status de envio e reenvio manual pelo fotógrafo.
- Nunca enviar lembrete após expiração, cancelamento de comunicação ou exclusão válida do contato.

## Fase 7 — Busca facial protegida (piloto antes de produção)

- Importar apenas fotos aprovadas no culling.
- Quando o subsistema estiver operacionalmente habilitado, garantir automaticamente a política técnica interna e indexar rostos e qualidade explicável em fila depois que as prévias limpa e protegida estiverem prontas; o fotógrafo não prepara nem ativa política por galeria, e a disponibilidade da foto e a seleção manual não aguardam o processamento facial.
- Executar indexação somente por evento persistido de foto/derivado novo, mudança versionada, backfill ou retentativa. Não manter varredura recorrente da galeria; worker ocioso aguarda a fila sem consumo ativo de CPU e pode descarregar modelos da memória.
- Limitar toda busca a uma única Galeria pública já autorizada por link opaco, telefone/OTP e vínculo persistido. `Pública` é denominação de produto para acervo de interesse de várias pessoas, não acesso anônimo nem autorização por posse do URL.
- Fluxo: responsável já autorizado aceita em checkbox o consentimento específico para uso temporário da referência, envia uma foto com um rosto e acompanha um job durável. Fechar ou atualizar a tela não cancela a busca; progresso real e conclusão ficam disponíveis para retomada e notificação transacional neutra.
- Comparar somente com embeddings do snapshot daquela galeria. Resultados apenas reordenam fotos que a cliente já pode visualizar e aparecem na mesma Galeria pública, sem criar permissão, seleção ou galeria privada.
- Ranqueamento técnico avalia o rosto que correspondeu à referência, não o maior rosto ou a foto inteira. Nitidez local, corte, tamanho/proeminência e pose separam `Melhores resultados encontrados` de `Outros resultados encontrados`; nenhuma foto é excluída ou ocultada automaticamente e nenhum atributo pessoal ou estético é inferido.
- A primeira seleção consciente, manual ou a partir do resultado, cria ou reutiliza somente o estado comercial individual de `Galeria pública + cliente`; a busca isolada não cria entidade comercial.
- Nenhuma grade anônima de fotos escolares e nenhuma busca entre eventos. Revisão do fotógrafo permanece obrigatória se um desenho futuro pretender liberar conteúdo antes invisível ou ampliar o escopo autorizado.
- Feedback “não é esta pessoa” remove resultado e cria tarefa silenciosa para o fotógrafo; não treinar o modelo automaticamente sem revisão humana.
- Incluir foto/excluir foto da indexação em massa antes da liberação do evento.
- Registrar consentimento versionado da cliente, busca, revogação, exclusão e operação administrativa; cada login OTP continua auditado. Na change `configurable-push-and-whatsapp-notifications`, somente o primeiro acesso autorizado por cliente/galeria canônica produz aviso externo, sem transportar OTP e sem replay de vínculos históricos.
- Apagar foto de referência e embedding temporário conforme retenção configurada; oferecer exclusão de dados biométricos.
- Validar desempenho, licença comercial, compatibilidade ARM, precisão facial e qualidade técnica com conjunto sintético em CI/local isolado. Não usar homologação ou dados de produção como ambiente de teste; um requisito posterior de dados reais exige decisão e autorização operacional específicas. OFIQ ou qualquer modelo adicional continua exigindo validação separada de código, pesos e dependências.

## Fase 8 — Privacidade, observabilidade e métricas

- Termos, política de privacidade, base/finalidade do tratamento, canal de solicitação de exclusão e exportação.
- Tratamento facial limitado, com melhor interesse de crianças e consentimento específico de responsável legal.
- Auditoria de exclusões, ativação de acesso, confirmação de pagamento, links de entrega e ações biométricas.
- Métricas: conversão por evento, acessos, seleções, carrinhos abandonados, pedidos, ticket médio, mensagens e vendas por foto.
- Métricas de infraestrutura: fila, falhas, uso de disco, backup e disponibilidade das integrações.
