# Design

## Context

`GalleryPreviewSettings` controla ativação, intensidade, exposição e geração por galeria. `preview_adjustment.service` usa essa configuração no enqueue, lease, publicação e entrega. `inputs` parte de admin_preview convencional e inclui a proteção no fingerprint. `facial.lifecycle.cleanup_source` também consulta a configuração de ajuste para decidir a retenção temporária de fontes high-res.

Pastas do Acervo são PhotoFolder de conteúdo com audience_scope=selected e pertencem à mesma ParentGallery; upload passa por /admin/photo-assets/{id}/source. Não existe processamento separado por cliente. FacialPolicyPanel/PreviewAdjustmentPanel atuais exibem e acionam a galeria inteira; copiá-los para o Acervo sem limitar escopo seria incorreto. O facial tem gates de ambiente, rollout e política que não podem ser contornados por um controle de pasta.

## Goals / Non-Goals

**Goals:** herança compatível, substituição completa por pasta e processamento local observável; interface móvel clara; preservar permissões e evitar exposição acumulada ou resultado obsoleto.

**Non-Goals:** edição final, transformação de originais, novo motor, ajuste por cliente individual dentro de pasta compartilhada, limpeza de índices, alteração de consentimento/retencão, novo acesso facial ou execução biométrica real no servidor durante desenvolvimento.

## Decisions

### 1. Configuração opcional isolada pela pasta

Criar registro FolderProcessingSettings com FK de pasta, modos inherit/custom/off para prévias e inherit/on/off para novos trabalhos faciais. Sem registro equivale à herança, mantendo pastas existentes intactas. Campos próprios de intensidade/exposição seguem limites atuais. Não aceitar configurações próprias incompletas; zeros são valores válidos e nunca significam herança.

Classificar a nova tabela como operacional no inventário/limpeza restrita de homologação, pois sua FK aponta à pasta e seus valores não são configuração global. A classificação só atualiza a lista fechada e o inventário; não executa limpeza. A lista de preferências globais preservadas permanece intacta.

O padrão facial herdado continua sendo a disponibilidade atual da galeria/ambiente; on permite agendamento local somente se os gates globais permitirem. off pausa novas admissões/agendamentos e retentativas, preservando índices já existentes e seus resultados autorizados. Trabalhos faciais admitidos antes da pausa podem terminar para evitar interromper o lifecycle/retencão de fontes; o painel explica essa regra. Exclusão de índice e desativação retroativa de busca ficam fora desta change.

### 2. Resolução efetiva única sem soma

Introduzir resolvedor da configuração efetiva por PhotoFolder/PhotoAsset. inherit usa todos os valores da galeria; custom usa todos os valores da pasta; off usa prévia convencional. Nenhuma soma/multiplicação entre configurações. Exemplo aceito pelo proprietário: galeria +0,3 e pasta +0,5 resulta em +0,5.

Usar esse resolvedor no enqueue, worker, seleção de resultado, revalidação pós-render e retenção temporária high-res. A configuração própria funciona mesmo quando o padrão da galeria está desligado. Não remover o padrão atual nem mudar seus endpoints existentes.

### 3. Versão efetiva e concorrência

Persistir revisão local e assinatura efetiva nos trabalhos/resultados para distinguir galeria geração 2 de pasta revisão 2. Resultados herdados legados conservam sua compatibilidade; mudanças entre modos exigem assinatura nova. Alterar o padrão cancela/invalida somente trabalhos/resultados herdados; não invalida pastas personalizadas. Alterar a pasta cancela somente seus trabalhos de ajuste ativos; resultado pronto anterior fica inelegível até processamento explícito. O worker verifica fonte, proteção, modo e assinatura após render antes de publicar. Mutações de configuração serializam pelo registro da galeria e pela configuração da pasta; a publicação trava galeria, foto e configuração antes de validar o trabalho, sem manter locks durante o render.

Sempre ler admin_preview convencional preservado; nunca usar resultado anterior como entrada. Mudança de valores não processa automaticamente todo acervo antigo; novas fotos seguem a configuração efetiva e fotos existentes usam ação explícita. Desligar restaura imediatamente a versão convencional nas próximas requisições.

### 4. APIs e ações por pasta

Endpoints administrativos autenticados validam existência, propósito de conteúdo, galeria ativa e pertencimento correto. Configuração em PATCH com modos e valores completos explícitos e auditoria; status/progresso, enqueue paginado de prévias e retentativa facial são limitados por folder_id. UUID conhecido não autoriza cliente; APIs de cliente e filtros de audiência permanecem inalterados. Ações globais existentes continuam disponíveis, respeitando overrides/off de cada pasta. Status facial local pode reutilizar agregador existente com filtro opcional de pasta, preservando payload antigo da galeria.

### 5. Interface única com hierarquia visual

Componente FolderProcessingPanel reutilizado na pasta aberta da etapa Imagens e na pasta aberta do Acervo; não montar em todas as pastas/clientes recolhidas. Cabeçalho recolhível “Processamento da pasta” com resumo “Herdado da galeria”, “Personalizado” ou “Desligado”. Conteúdo em dois cards: Reconhecimento facial e Ajuste das prévias, com contagens/barra reais, escolhas explícitas e botões “Processar esta pasta”/“Retentar nesta pasta”.

Layout em duas colunas em desktop e uma em mobile; tokens de cor/bordas existentes, destaque amarelo somente nas ações principais, badges legíveis e estados vazios/erro/sucesso. Exibir valor efetivo de exposição com sinal e vírgula, orientação de que não acumula, comparação antes/depois protegida quando disponível e limites de largura para nomes longos. Teclado, foco, labels únicos por pasta e aria-expanded no cabeçalho. Nota de pasta compartilhada: configuração vale para a pasta e todas as clientes atribuídas, não só para o card em que foi aberta. Polling somente aberto e com trabalhos pendentes, cancelado ao fechar/desmontar.

Etapa Imagens mantém padrão/resumo da galeria com título inequívoco; mostra que configurações próprias prevalecem. Sem alterações na UI do cliente.

## Risks / Trade-offs

- [Gerações numéricas coincidentes] → assinatura efetiva persistida e revalidada, incluindo origem da configuração.
- [Fonte high-res retida desnecessariamente ou apagada cedo] → resolvedor também no lifecycle, com política de TTL existente preservada.
- [Pausa interpretada como apagar índice] → descrição explícita, sem purge e sem alteração de busca já indexada.
- [Tratamento de pasta compartilhada afeta várias clientes] → nota de escopo e mesma configuração para o folder_id.
- [Muitos painéis consultam filas] → carregamento sob abertura, paginação e polling restrito a trabalhos pendentes.

## Migration Plan

1. Revisar estes artefatos e reconciliar documentação pendente da change anterior sem misturar commits.
2. Migration aditiva após 0067; pastas sem configuração continuam herdando. Validar SQLite/PostgreSQL descartáveis; não converter registros em massa.
3. Implementar resolvedor/assinatura, workers, gates locais, endpoints e UI com testes direcionados a cada task.
4. Regressão completa aplicável, lint/typecheck/build Docker, OpenSpec e diff. Testes locais sintéticos somente; nenhum reprocessamento biométrico de dados reais.
5. PR/CI; parar enquanto Actions executa. Deploy separado autorizado, com inventário e plano delimitado. Não limpar dados novos de homologação.
6. Rollback não remove configurações próprias sem revisão; downgrade deve recusar configurações não herdadas para evitar perda silenciosa. Arquivar/sincronizar somente após revisão humana e evidência de publicação.
