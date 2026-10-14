# Plano do corpus sintético do spike facial

## Objetivo e limites

O corpus reproduz somente condições técnicas de um evento fotográfico. Todas as identidades são adultas, ficcionais e geradas por IA. Nenhuma imagem de cliente, produção, homologação, pessoa real conhecida ou criança pode ser usada.

Os arquivos do corpus SHALL permanecer em diretório efêmero fora do repositório. O Git recebe apenas scripts, testes, métricas agregadas e este inventário. O construtor grava um marcador de segurança e um manifesto com hashes; a limpeza recusa diretórios sem esse marcador.

## Inventário reproduzível

- Duas folhas sintéticas 4 × 4 com as mesmas 16 identidades adultas ficcionais: uma frontal e uma com variações leves de pose.
- Evento A: 504 JPEGs indexáveis.
  - 480 imagens individuais: 30 variações por identidade.
  - 16 imagens de grupo: quatro rostos por imagem.
  - 8 imagens sem rosto para medir rejeição e falha de detecção.
- Evento B: 4 sentinelas isoladas, usadas somente para provar que uma consulta ao Evento A nunca atravessa o escopo.
- Consultas: 32 JPEGs, duas por identidade, mantidas fora do conjunto indexado.
- Total efêmero esperado: 540 JPEGs, dentro do intervalo normativo de 500–1.000.

As variações determinísticas incluem pose sintética, escala, iluminação, contraste, desfoque, redução de resolução, ruído e oclusão parcial. O seed padrão é `20260905`.

## Métricas

### Detecção

- cobertura de rostos esperados;
- falsos rostos em imagens negativas;
- rejeições de consulta por nenhum rosto, múltiplos rostos e qualidade insuficiente;
- cobertura por cenário de qualidade.

### Recuperação

- acerto top-1 e recall@5;
- falsos positivos e falsos negativos por limiar;
- precisão e recall por cenário;
- candidatos indevidos de outro evento, cujo valor aceitável é zero;
- curva de limiar sem apresentar similaridade como porcentagem de identidade.

### Operação

- latência e throughput separados para indexação e consulta;
- pico e variação de memória do processo;
- tempo de CPU e uso de disco do índice;
- versão, formato, hash e licença de cada peso.

## Ambiente

O harness roda em ambiente Python isolado, sem conexão com banco, Redis, worker ou APIs da Markina Gallery. Modelos ficam em cache efêmero e são verificados por hash registrado na execução. A primeira rodada local mede o host AMD64; a medição ARM precisa ocorrer depois em ambiente isolado autorizado, sem deploy e sem dados da aplicação.

## Limpeza e evidência

1. construir o corpus em diretório temporário explícito;
2. executar `dataset.py verify` e registrar somente o resumo agregado;
3. executar o benchmark;
4. executar `dataset.py clean`;
5. verificar que o diretório efêmero não existe;
6. confirmar por `git status` que nenhum JPEG, embedding, índice ou modelo foi incluído.

## Evidência da preparação

Em 2026-09-05, o construtor foi validado por `python -m pytest scripts/face_spike/test_dataset.py -q` (`3 passed`) e `ruff` sem achados. Uma execução real com as duas folhas ficcionais produziu e verificou 504 imagens no Evento A, 4 sentinelas no Evento B, 32 consultas, 16 identidades e 540 JPEGs no total. Todos os hashes conferiram. O diretório temporário marcado foi removido pelo próprio utilitário e `Test-Path` retornou `False` após a limpeza.
