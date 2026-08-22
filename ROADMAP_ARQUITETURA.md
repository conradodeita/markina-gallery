# PhotoCRM — Roadmap Arquitetural

Documento vivo das decisões tomadas durante a arquitetura. Ainda não é a especificação de implementação para o executor.

## Princípios do produto

- Experiência mobile-first, com poucos passos para o responsável selecionar e comprar fotos.
- Painel administrativo robusto, porém direto para um único fotógrafo no MVP.
- Galerias privadas organizadas previamente no DigiKam e eventos coletivos protegidos por busca facial privada.
- Fotos exibidas são JPEGs exportados após o culling; RAW e edição final ficam fora do sistema.
- Google Photos é o canal de entrega final criado manualmente pelo fotógrafo; o sistema controla o link e a comunicação.

## Fase 0 — Fundamentos de engenharia

- Adotar OpenSpec como processo obrigatório: `openspec/specs/` representa o comportamento já consolidado; cada mudança nasce em `openspec/changes/<change-id>/` com proposta, delta specs, design e tarefas.
- Inicializar o OpenSpec para Claude Code e manter o `AGENTS.md` gerenciado pela ferramenta como instrução de fluxo para o executor.
- Antes de implementar qualquer fase ou alteração, criar e revisar uma proposta OpenSpec; após testes e deploy, sincronizar/arquivar a mudança para manter as specs como fonte da verdade.
- Criar specs iniciais por domínio: autenticação, acesso do cliente, galeria e seleção, preços e pedidos, mídia/armazenamento, mensagens, privacidade/biometria e deploy/operação.
- Criar repositório privado no GitHub, com `main` protegida, `develop`, branches de funcionalidade e pull requests.
- Configurar convenção de commits, `.gitignore`, documentação local e CI para lint, testes e build.
- Separar homologação de produção: domínio, banco, chaves, WhatsApp e dados totalmente distintos.
- Implantar via Docker Compose: proxy HTTPS, frontend, API, PostgreSQL, Redis e workers.
- Guardar chaves e segredos somente em variáveis seguras do servidor; nunca no Git, frontend ou tabelas comuns.
- Criar backups diários cifrados do PostgreSQL no Google Drive e testar restauração periodicamente.

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

- Galeria privada: importação DigiKam de fotos já separadas pelo fotógrafo, com vários responsáveis autorizados quando necessário.
- Evento coletivo: acervo inteiro visível somente ao fotógrafo; clientes recebem somente resultado privado aprovado.
- Cliente pode navegar, ampliar, favoritar e montar carrinho; identificação obrigatória na primeira intenção de compra.
- Carrinho persistente por cliente e galeria; histórico de acessos, favoritos, remoções e abandono.
- Preço por faixas dinâmicas: a faixa da quantidade será aplicada ao pedido inteiro, com simulador no painel e aviso de saltos de preço.
- Congelar fotos, preço, desconto e regras comerciais em cada pedido.
- Após pagamento confirmado, fotos daquele pedido ficam indisponíveis para recompra para o mesmo cliente, mas continuam disponíveis a outros responsáveis autorizados.
- Permitir compras adicionais durante o prazo da galeria; pedido e entrega permanecem acessíveis após o prazo.

## Fase 4 — Pagamentos, edição e entrega

- MVP: PIX com QR Code, copia-e-cola e confirmação manual do fotógrafo.
- Arquitetura de provedor de pagamento preparada para integração posterior com Infinity Pay e webhooks assinados.
- Estados: seleção, checkout, aguardando pagamento, pagamento informado, confirmado, em edição, pronto, link enviado, entregue, cancelado, reembolsado e não localizado.
- Ao disponibilizar entrega, fotógrafo cola link do Google Photos, aciona mensagem WhatsApp e libera cartão verde “Acessar minhas fotos” no portal.
- Antes disso, o portal mostra cartão vermelho/amarelo: “Fotos disponíveis em breve” ou “Suas fotos estão em edição”.
- Registrar link, data/hora, pedido, mensagem enviada e confirmação de entrega opcional pelo cliente.

## Fase 5 — Imagens, armazenamento e proteção visual

- Oracle: servir JPEGs de prévia e miniaturas de galerias ativas; manter banco, filas e processamento.
- Google Drive: cópia verificada dos JPEGs, arquivo frio de eventos e backups cifrados do banco.
- Google Photos: entrega manual final; não automatizar compartilhamento pela API.
- Limite operacional de 75% do disco local, com alerta e bloqueio preventivo de nova importação.
- Painel de armazenamento: uso atual, uso por evento, média por foto, estimativa de capacidade e candidatos a arquivamento.
- Arquivamento restaura fotos do Google Drive somente quando o fotógrafo reativar o evento.
- Importação retomável e idempotente: hash por arquivo, fila, progresso, relatório de duplicados/falhas e retentativas.
- Proteção de prévias: limite de resolução, remoção de EXIF/GPS, marca d’água configurável, grade diagonal, linhas configuráveis, marca individual dinâmica e aviso de direitos autorais.
- Declarar na interface que a proteção desencoraja cópia, mas não impede capturas de tela de forma absoluta.

## Fase 6 — WhatsApp e comunicação

- Mensagens configuráveis para OTP, convite, pagamento, edição, entrega, carrinho abandonado e expiração.
- Separar mensagens transacionais de lembretes comerciais e registrar opt-out destes últimos.
- Fila com retentativas, status de envio e reenvio manual pelo fotógrafo.
- Nunca enviar lembrete após expiração, cancelamento de comunicação ou exclusão válida do contato.

## Fase 7 — Busca facial protegida (piloto antes de produção)

- Importar apenas fotos aprovadas no culling.
- Indexar rostos em fila após importação; limitar toda busca a um único evento.
- Fluxo: responsável valida telefone, aceita termo específico, envia referência, fica pendente, fotógrafo revisa e ativa acesso por convite individual.
- Nenhuma grade pública de fotos escolares; o responsável só vê resultado privado aprovado.
- Feedback “não é esta pessoa” remove resultado e cria tarefa silenciosa para o fotógrafo; não treinar o modelo automaticamente sem revisão humana.
- Incluir foto/excluir foto da indexação em massa antes da liberação do evento.
- Registrar consentimento versionado, busca, revogação, exclusão e operação administrativa.
- Apagar foto de referência e embedding temporário conforme retenção configurada; oferecer exclusão de dados biométricos.
- Validar desempenho, licença comercial, compatibilidade ARM e precisão com um piloto anonimizado de 500–1.000 JPEGs antes de ativar em clientes reais.

## Fase 8 — Privacidade, observabilidade e métricas

- Termos, política de privacidade, base/finalidade do tratamento, canal de solicitação de exclusão e exportação.
- Tratamento facial limitado, com melhor interesse de crianças e consentimento específico de responsável legal.
- Auditoria de exclusões, ativação de acesso, confirmação de pagamento, links de entrega e ações biométricas.
- Métricas: conversão por evento, acessos, seleções, carrinhos abandonados, pedidos, ticket médio, mensagens e vendas por foto.
- Métricas de infraestrutura: fila, falhas, uso de disco, backup e disponibilidade das integrações.
