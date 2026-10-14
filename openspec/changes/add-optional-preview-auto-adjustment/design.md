## Context

`media.generate_derivatives` gera `thumbnail`, `admin_preview` limpa e `client_preview` protegida e dispara a indexação facial. A API entrega arquivos privados com cache desativado. Jobs convencionais e biométricos possuem fluxos próprios. A proposta foi aceita pelo proprietário na conversa, incluindo implementação e reversibilidade; sua instrução prevalece sobre a pausa padrão do fluxo propose.

## Goals / Non-Goals

**Goals:** módulo removível, trabalho fora do HTTP, preservação byte a byte do material convencional, desligamento consultado em cada entrega e execução, comparação administrativa e dependência pesada exclusiva do worker.

**Non-Goals:** edição final, IA generativa, processamento da referência facial enviada pela cliente, entrega histórica ajustada, troca imediata de imagens já carregadas no navegador ou benchmarking de carga amplo nesta rodada.

## Decisions

1. Primeira implementação: adaptador RawTherapee CLI com perfil versionado de níveis automáticos, contraste/tonalidade moderados e mistura com a prévia limpa. A interface de motor permite substituir a implementação depois de comparar qualidade. Image-Adaptive-3DLUT não é integrado nesta versão: compatibilidade de runtime/pesos e aceitação estética ainda não verificadas. Alternativa de filtro artesanal com Pillow não representa o motor fotográfico avaliado.
2. Duas tabelas exclusivas: configuração singleton (`enabled`, geração, intensidade) e trabalho/resultado por foto com FK `ON DELETE CASCADE`, estado, tentativa, token de reserva, impressão da prévia/proteção, duração e caminho relativo. Não ampliar enums das tabelas convencionais. Modelos registrados na metadata central para migrations e testes.
3. Depois do commit de prévias convencionais, agendamento em transação própria e isolada. Falha do módulo não reverte importação. Ativação não varre acervo: UI oferece paginação explícita por galeria para avaliação/retentativa. Worker exclusivo consulta somente a fila e dorme ocioso; uma foto por vez, timeout por subprocesso, reserva com expiração e número limitado de tentativas.
4. CPU: imagem de entrada é a prévia limpa reduzida ao limite do cliente. Converter entrada com perfil ICC quando presente na geração convencional não pertence a esta change; o ajuste trabalha sobre RGB da prévia existente. Saída é sanitizada e protegida pelo compositor atual. O original nunca é entrada escrita pelo motor.
5. Entrega seleciona a cópia ajustada somente com flag ativa, geração, assinatura de proteção e versão da prévia iguais. API de comparação serve antes/depois protegidos somente ao admin. Capas e histórico retido usam convencional. Cache `no-store` já existente evita persistência após desligamento; não é possível apagar pixels já exibidos pelo navegador.
6. Saída sob `derivatives/<photo-uuid>/preview-adjustment/<claim-uuid>.jpg`; só esse namespace é removível pelo módulo. Comparação e entrega validam caminho, existência e estado. Revalidar reserva, foto, geração, fonte e proteção antes de publicar evita corrida com desligamento/regeneração/exclusão. Files temporários ficam dentro de diretório temporário do worker e não são acessíveis por HTTP.
7. Worker Docker opcional em override próprio, sem porta publicada, com CPU/memória limitadas. Não alterar defaults do Compose nem instalar RawTherapee na API. Chave geral fica no banco e pode ser desligada sem deploy/restart; parar o worker elimina o custo ocioso.
8. UI isolada em Configurações: ligar/desligar, intensidade moderada, galeria, progresso e seleção de foto para comparar. Novas fotos recebem ajuste quando habilitado; existentes exigem comando explícito. Nenhum controle extra na área cliente.

## Risks / Trade-offs

- Qualidade estética variável → desligado por padrão, comparação antes/depois e intensidade; aceitação pelo fotógrafo permanece pendente até amostra real.
- Custo CPU/disco → resolução de prévia, worker limitado, armazenamento extra exclusivo e limpeza inventariada. Não extrapolar benchmark facial.
- Resultado obsoleto → assinatura de configuração/fonte e geração, fallback em toda leitura, teste de corrida.
- CLI indisponível local → teste de contrato com executável simulado e tentativa de validação real se disponível; registrar falta de prova real sem declarar equivalência com Lightroom.
- Licença RawTherapee GPL-3.0 e distribuição de imagem → manter atribuição, referência ao código-fonte e obrigações do pacote; não copiar código do motor para aplicação.

## Migration Plan

Migration aditiva cria somente tabelas do módulo. Código convencional mantém arquivos e estados. Deploy fica separado de ativação. Desligar via painel muda a resolução na próxima requisição; parar worker antes da limpeza; executar inventário dry-run e limpeza explícita. Remoção futura de código usa os pontos de integração documentados, sem revert geral de Git nem downgrade destrutivo dos outros domínios.

## Open Questions

- Aceitação estética do perfil nas fotos do fotógrafo e desempenho no host ARM compartilhado serão medidos antes de recomendar ativação ampla.
