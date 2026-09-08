# Calibração e equidade da busca facial

## Gate de produção

Produção MUST permanecer bloqueada enquanto não existir aprovação humana ativa que corresponda exatamente a ambiente, modelo, versão de qualidade, versão de calibração e limiar. A aprovação registra apenas referências opacas, contagens agregadas de grupos relevantes e o administrador aprovador; não registra atributos inferidos, imagens, embeddings ou resultados individuais.

O baseline sintético anterior mediu o limiar `0,750` com precisão agregada de 100%, recall de 98,62%, top-1 de 100%, zero falso positivo e 15 falsos negativos. Ele demonstra a orientação conservadora, mas não aprova produção nem substitui corpus representativo permitido.

## Critérios do próximo ensaio permitido

- corpus com origem, finalidade, retenção e autorização documentadas fora do relatório técnico;
- separação de treino/calibração e validação, sem treinamento automático a partir da interação da cliente;
- grupos de cenário definidos antes da execução: captura frontal, pose, iluminação, oclusão, desfoque, distância/resolução, dispositivo e foto coletiva;
- métricas agregadas por cenário: consultas válidas, precisão, recall, falso positivo, falso negativo, top-1 e intervalo de confiança quando aplicável;
- zero falso positivo como objetivo conservador inicial; qualquer falso positivo bloqueia o limiar até revisão humana;
- diferenças relevantes de falso negativo entre cenários devem ser explicadas ou mitigadas; ausência de amostra suficiente deixa o grupo reprovado;
- nenhum atributo como idade, gênero, raça, etnia, emoção ou identidade é inferido pelo runtime. Se uma avaliação jurídica aprovar categorias autodeclaradas para equidade, elas permanecem somente no corpus controlado e fora do produto;
- relatório final contém somente métricas agregadas e referência opaca do corpus, com aprovação explícita de todos os grupos relevantes.

## Estado atual

O gate técnico está implementado e falha fechado: até a aprovação correspondente existir, `activate_rollout` recusa produção e um rollout previamente ativo deixa de ser efetivo se a aprovação for revogada ou se o limiar mudar. A execução empírica representativa e sua aprovação humana ainda não ocorreram; portanto, produção continua bloqueada.
