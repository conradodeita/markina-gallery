# Validação da jornada local persistente

## Autorização e isolamento

Em 01/11/2026, o proprietário autorizou executar a jornada com fotógrafo/tenant de teste que pudesse consultar no próprio painel. Produção permanece somente leitura; não há deploy nem transação financeira real.

- Tenant administrativo de teste: `jornada-creditos-20261101@example.test`.
- PostgreSQL exclusivo: container `pyp-credit-journey-20261101`, bind `127.0.0.1:15471`, database `pyp_credit_journey_test`, schema `journey_creditos_20261101`, volume `pyp-credit-journey-data-20261101`.
- UI local em `127.0.0.1:18084`; API real da cópia de trabalho em `127.0.0.1:18083`; controle de sessões sintéticas em loopback `127.0.0.1:18081`; receptor exclusivo de callbacks em `127.0.0.1:18082`.
- Configuração sensível e chaves locais estáveis permanecem fora do Git, em arquivo protegido. O harness temporário não altera autenticação de produção e não apaga o schema ao encerrar.
- Arquivos JPEG gerados são padrões geométricos sem rostos ou dados pessoais. Nenhum worker facial será iniciado.
- O controle oferece sessões reais para as identidades sintéticas, exclusivamente em loopback. Somente o receptor de callbacks é exposto pelo túnel de teste já aprovado.

## Plano e rastreabilidade

| Critério | Verificação | Estado |
| --- | --- | --- |
| Compra, confirmação e saldo | UI real, Orders de conta test_user MLB, consulta autoritativa e ledger | Validado localmente |
| Upload em Imagens | Registro, envio durável, operação e totais na UI | Validado localmente |
| Acervo de cliente | Pasta restrita sintética, upload, saldo e isolamento | Validado localmente |
| Galeria privada legada | Fixture exclusiva de compatibilidade, sem reativar criação de galeria privada | Validado localmente |
| Upload parcial e repetido | Falha controlada, retry/reindex e confirmação de duplicada | Validado localmente |
| Proprietário ilimitado | Upload sem débito finito e carteira preservada | Validado localmente |
| Consulta pelo proprietário | Busca por e-mail, saldo e lançamentos do tenant sintético | Validado localmente |
| Persistência | Reinício do harness preserva IDs, fonte, ledger e chaves | Validado localmente |

## Limites

Este ensaio não aprova cadastro público, não preenche nome de fotógrafo a partir do e-mail, não encerra gates R14 e não substitui testes externos indisponíveis no sandbox. Tasks 4.1/4.3 somente serão marcadas após evidência dos critérios correspondentes. A suíte backend ampla continua sob investigação separada.

## Evidência intermediária — compra e primeiro fluxo

- Compra `e572637f-47bc-4bcb-9e18-b7b3182c6659` criada pelo botão real do catálogo. Antes de confirmar: saldo 0, nenhum lançamento.
- O Chrome do usuário não carregou os campos seguros nesta tentativa; o mesmo checkout foi retomado em sessão isolada do navegador integrado, sem criar nova compra. Ali os campos carregaram e o cartão público de teste APRO concluiu o pagamento. Não houve credencial nem cartão real.
- A UI atualizou automaticamente saldo para 12 e histórico com um lançamento +12, sem reload manual.
- A reinicialização do harness preservou compra, saldo, identidades e chave de criptografia no PostgreSQL persistente.
- Editor Imagens: lote `jornada-01.jpg`, `jornada-02.jpg`, `invalido.jpg`: dois consumos confirmados, arquivo inválido com reserva liberada; disponível 10, reservas 0, operações pendentes 0. UI apresentou estados por arquivo.
- Lote posterior com `jornada-01.jpg` e `jornada-03.jpg`: diálogo informou custo da duplicação; Cancelar pulou só a primeira e enviou a terceira. Disponível esperado após confirmação: 9; conferir snapshot final.
- A fixture do acervo restrito inclui ParentGalleryRegistration ativa, GalleryClientState e FolderClientGrant. Nenhuma pessoa ou telefone real utilizado.


## Resultado integrado — 01/11/2026, 21:57 UTC

- Tenant comprador: `fbde36c6-4fbd-43c7-9906-a1b7d65b3a49`; galeria de teste `d126a561-775c-4396-ae9e-ec0de42f8187`.
- Order sandbox `ORDTST01M6CHHXXSWZ4TMSFV7CZRJC6Q`; compra `e572637f-47bc-4bcb-9e18-b7b3182c6659`, estado confirmed, um lançamento +12.
- Imagens: 3 consumos válidos; inválido permaneceu released, sem débito. Acervo da cliente: 1 consumo. Galeria legada sintética: 2 consumos, sendo o segundo cópia deliberada após Confirmar no aviso de repetição. Total: 6 consumos, disponível 6, reservado 0, pendências 0.
- Nos três fluxos, a UI real apresentou o saldo do servidor e estados por arquivo. O terceiro ensaio teve a sessão substituída por uma nova sessão do mesmo administrador durante a checagem HTTP; foi restabelecida pelo controle e conferiu-se que o primeiro upload já havia concluído, sem reenviar nem duplicar por suposição.
- Checagens adicionais pela API real: retry do mesmo asset HTTP202 e reindex do mesmo asset HTTP202, saldo preservado em6. Capa pelo endpoint próprio cover-photos: HTTP201/202 e nenhuma operação financeira. Upload do proprietário: carteira unmetered, consumo0, nenhuma PhotoCreditOperation.
- Isolamento: fotógrafo recebe403 na consulta global de carteiras; pasta do proprietário consultada pelo fotógrafo recebe404.
- Painel real do proprietário: busca por `jornada-creditos` encontrou a conta; seleção exibiu disponível6, consumo6, uploads pendentes0 e7 lançamentos (compra +12 e seis uploads -1), com referência da compra preservada. Tela deixada aberta no Chrome.
- A reinicialização do harness preservou schema, identidades, compra e fontes. Mídia permanece no diretório temporário específico journey-media-20261101; não há rotina de limpeza automática adicionada.
- A API de controle local `/journey` oferece acesso às duas identidades sintéticas; esse helper fica fora do repositório e não integra o produto. Mudar de papel substitui a sessão local.

Evidências fora do Git: `C:/codex-data/temp/pyp-mp-external-20261101/journey-contract-results.json`, `journey-legacy-consumed.jpg` e `journey-owner-ledger.jpg`. O contrato JSON inclui IDs de operações e lançamentos para conferência, sem segredos.

Não foram executados workers de mídia/facial; por isso as prévias permanecem em preparação. O crédito é consumido pela fonte durável, antes desses workers. Esta limitação é visível e não foi apresentada como processamento de mídia concluído.


## Cards e verificação proporcional

- A revisão encontrou que somente o botão iniciava a compra, embora a spec aprovada exigisse card e botão com a mesma ação. A correção limita-se ao botão nativo existente: sua área de acionamento foi estendida ao card via CSS, com foco no card, seleção ligada ao pacote do checkout e estado indisponível. Não foi criado controle aninhado nem outro caminho de compra.
- Clique real no título do card, fora do botão visível, preparou checkout. Enter no botão também preparou checkout. Ambos permaneceram no checkout transparente e sem débito da carteira.
- Esses dois ensaios criaram somente duas compras locais prepared adicionais (`2130c72c…`, `05aec2ae…`), sem Order do provedor, sem pagamento e sem lançamento de crédito. São registros intencionais da jornada, preservados; a única compra confirmada continua `e572637f…`.
- Em viewport390×844, o card ficou com305px de largura, sem transbordamento horizontal da página (scrollWidth375≤innerWidth390). Desktop conferido na página real. Conteúdo comercial continuou sendo exclusivamente o catálogo do servidor.
- Em emulação prefers-reduced-motion:reduce, transform=none e duração efetiva da transição1e-05s pela política global de acessibilidade; a emulação e o viewport foram restaurados após a conferência.
- Componente do card mantém um único button nativo. Foco e estados de carregamento/indisponibilidade foram conferidos; testes existentes incluem bloqueio financeiro e catálogo indisponível.
- Frontend: 22 testes/3 arquivos passaram; ESLint direcionado e typecheck passaram; lint geral0erros/36avisos preexistentes; build completo passou em cópia temporária sem.env, preservando os processos Next existentes.
- OpenSpec strict passou nas duas changes (`improve-photographer-credit-workflows`, `add-mercadopago-credit-purchases`). Diff diretamente afetado foi revisado e git diff--check passou. Sem limpeza geral elegível; a única extração adicional é o construtor das fixtures sintéticas para manter a identidade de proprietário explícita nos testes.


### Conferência final da fonte e callback

Uma nova leitura do schema persistente confirmou um webhook real processado (state=done), uma única Order confirmada e dois checkouts somente prepared, sem provider_order_id. Os seis assets consumidos possuem fonte em disco e SHA-256 igual ao fingerprint da operação; a operação released do JPEG inválido não possui fonte durável. A soma do ledger permanece6. Evidência fora do Git em `C:/codex-data/temp/pyp-mp-external-20261101/journey-source-results.json`.


## Encerramento da jornada local inicial — 01/11/2026 (registro histórico)

- Regressão das fixtures afetadas:80testes SQLite aprovados;3testes PostgreSQL adicionais aprovados. Um teste histórico de migration permanece dependente do ambiente específico55888; não foi executado. Relatório completo na change de compras, validation.md.
- A suíte backend inteira não foi repetida nesta etapa. O resultado dirigido não é declaração de CI/release aprovado.
- Naquele checkpoint, tasks 1.1–1.3 continuavam bloqueadas pelos pré-requisitos R14-0–6 e revisão humana do portal de cadastro; a busca por e-mail era a decisão vigente e o nome não foi inferido. A reconciliação posterior de 06/11, abaixo, comprova a conclusão local dessas tasks sem abrir o cadastro público nem encerrar os gates R14.
- A task externa4.2 de compras Mercado Pago continua aberta para revisar limites do sandbox descritos em external-validation-results.md. A jornada bem-sucedida não simula chargeback online nem habilita PIX ausente na conta de teste.
- Não houve commit, push, deploy, migration remota ou alteração de produção. O banco original local e os demais projetos foram preservados. O banco de jornada é exclusivamente sintético e persistente.

## Busca do proprietário por nome e e-mail — 06/11/2026

- O teste de cadastro `test_automatic_signup_creates_finite_tenant_and_real_admin_session_without_owner_approval` passou; verifica ativação automática após e-mail verificado/MFA e persistência do nome informado. Nomes de contas legadas não são inferidos nem preenchidos retroativamente.
- Os três testes direcionados de `test_photographer_credits.py` passaram em SQLite: busca parcial por nome/e-mail com resposta mínima, ordenação alfabética e fallback seguro para e-mail legado (ocultando identidade ambígua), e negação para fotógrafo, cliente e operador técnico.
- A UI do autocomplete passou 25 testes em 2 arquivos. TypeScript (`npx tsc --noEmit`) e ESLint direcionado passaram; Ruff direcionado passou.
- `openspec validate improve-photographer-credit-workflows --strict` passou. Esta verificação local não abre o cadastro público condicionado aos gates R14, não valida integrações externas e não autoriza publicação. Não houve migration, acesso a produção, alteração de dados reais, commit ou push.
