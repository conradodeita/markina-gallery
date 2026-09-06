## Context

Veja `proposal.md`. Busca facial é proibida para clientes até validar privacidade, licença e desempenho ARM. A jornada comercial atual já cria ou reutiliza uma privada operacional por `Galeria pública + cliente` na primeira seleção; o spike não poderá duplicar essa entidade nem transformar uma inferência biométrica em seleção.

## Goals / Non-Goals

**Goals:** medir alternativas locais, documentar controles e produzir decisão de gate para indexação assíncrona e busca facial usada somente como filtro de uma Galeria pública já autorizada.

**Non-Goals:** liberar recurso ao cliente, usar fotos reais de crianças, criar migrations de produção, persistir uma galeria privada como resultado da busca ou integrar o spike ao produto.

## Decisions

### Ambiente isolado e dataset seguro

O spike usará ambiente separado, dataset sintético/anonimizado de 500 a 1.000 JPEGs representando um único evento e identidades ficcionais com variações controladas de pose, escala, iluminação, desfoque, oclusão e múltiplos rostos. Nenhuma imagem, embedding ou referência será reaproveitada no produto, versionada no Git ou enviada à homologação.

### Pipeline alvo avaliado, não integrado

O harness reproduzirá duas fases separadas:

1. indexação não bloqueante após o upload, detectando zero ou mais rostos por foto e registrando embedding, caixa facial, qualidade e versão do modelo em armazenamento efêmero;
2. consulta posterior com exatamente um rosto utilizável, comparação somente dentro do evento e retorno ordenado de fotos candidatas.

O resultado será uma lista temporária de referências de foto, nunca uma galeria ou uma autorização. No desenho futuro, selecionar uma candidata chamará o mesmo resolvedor transacional da seleção manual; ele cria ou reutiliza a única privada de `Galeria pública + cliente`. Pesquisas de pessoas diferentes poderão compor um único filtro e carrinho, sem duplicar fotos.

Alternativa rejeitada: criar a privada ao concluir a busca. Uma inferência pode conter falso positivo, não expressa intenção de compra e duplicaria a jornada antes de qualquer seleção.

### Candidatos e licença

YuNet + SFace será o baseline porque detector, reconhecedor e pesos publicados pelo OpenCV possuem licenças permissivas explícitas e execução documentada em ARM. AdaFace R18 ou outro candidato para baixa qualidade só entrará na comparação se a proveniência e a licença comercial do peso específico forem verificáveis. InsightFace público não será tratado como candidato comercial enquanto seus pesos permanecerem restritos a pesquisa não comercial.

DeepFace poderá ser usado apenas como referência de harness; a licença do wrapper não substitui a licença de cada modelo carregado. CompreFace não será baseline porque sua distribuição oficial padrão exige x86/AVX e acrescenta serviços e banco que não correspondem ao alvo ARM atual.

### Gate mensurável

O relatório incluirá licença comercial do código e do peso, precisão por cenário, falso positivo/negativo, cobertura de detecção, latência separada de indexação e consulta, throughput, CPU, memória e disco. As métricas serão registradas por versão de modelo e limiar. Qualquer falha obrigatória bloqueia o candidato ou o produto.

O benchmark SHALL favorecer falsos negativos a falsos positivos e apresentar resultados como possibilidades, sem converter similaridade em porcentagem de identidade. A referência do OpenCV não será adotada como limiar de produção sem calibração no dataset do spike.

### Indexação não bloqueante e isolamento

Falha biométrica não impedirá que uma prévia protegida pronta seja publicada. O estado facial será independente (`pending`, `ready`, `partial`, `failed`, `disabled`) e permitirá retentativa. A consulta não atravessará eventos, galerias, clientes ou ambientes. Troca de modelo invalidará o índice anterior e exigirá reindexação versionada.

### Fluxo humano futuro

Mesmo aprovado, o processamento futuro dependerá de habilitação explícita por galeria, base legal e transparência para as pessoas indexadas, consentimento específico da pessoa que envia a referência e controles reforçados para menores. O aceite da referência não será considerado autorização automática para indexar todas as pessoas do acervo.

A foto de consulta e seu embedding serão apagados automaticamente após o processamento ou falha, com ação manual de exclusão e auditoria idempotente. Resultados temporários terão retenção curta, opção de limpeza e não concederão acesso. Embeddings do acervo serão isolados por galeria, terão versão e expirarão conforme a finalidade; exclusão da origem removerá o índice facial mesmo quando mídia histórica comercial precisar ser preservada.

Revisão do fotógrafo continuará obrigatória quando um resultado ampliar o conjunto de fotos que a cliente pode acessar. O spike avaliará dispensá-la apenas quando a cliente já possui autorização para visualizar toda a Galeria pública e a busca somente reordena esse mesmo conjunto.

### Estados da consulta

O harness distinguirá sucesso, nenhum rosto, múltiplos rostos, qualidade insuficiente, nenhum candidato, índice incompleto e falha técnica. Antispoofing fica fora do spike porque a referência não autentica identidade nem concede acesso; sua inclusão só será reconsiderada se uma change futura alterar essa premissa.

## Risks / Trade-offs

- [Risco biométrico] → não coletar dado real e exigir decisão jurídica posterior.
- [Modelo incompatível] → rejeitar alternativa, sem degradação de privacidade.
- [Embeddings criados antes do consentimento da consulta] → exigir base legal, aviso e habilitação explícita da indexação no evento antes do futuro rollout.
- [Falso positivo apresentado como certeza] → usar limiar conservador, linguagem de candidatos e seleção humana da cliente.
- [Indexação competir com prévias] → fila independente de baixa prioridade e publicação desacoplada.
- [Resultado temporário virar autorização] → contratos separados e teste negativo de ausência de galeria, vínculo ou seleção após a busca.

## Migration Plan

Sem migration de produção. Criar e destruir recursos isolados do spike; arquivar apenas relatório e decisão sem dados biométricos.
