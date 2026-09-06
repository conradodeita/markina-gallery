# Avaliação de privacidade e ciclo de vida biométrico

## Escopo da avaliação

Esta é uma avaliação técnica preliminar, não um parecer jurídico. O rollout SHALL permanecer bloqueado até o controlador definir e documentar, com assessoria adequada, a hipótese legal aplicável a cada operação. A fotografia comum passa a envolver dado pessoal sensível quando dela é extraído atributo biométrico vinculável a uma pessoa.

Fontes normativas consultadas em 2026-09-05:

- LGPD, especialmente arts. 5º, 6º, 8º, 9º, 11, 14–18, 20, 37–38 e 46–50: <https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm>;
- Enunciado CD/ANPD nº 1/2023 sobre hipóteses legais e prevalência do melhor interesse de crianças e adolescentes: <https://www.in.gov.br/web/dou/-/enunciado-cd/anpd-n-1-de-22-de-maio-de-2023-485306934>;
- agenda e consulta regulatória da ANPD sobre biometria, ainda em evolução: <https://www.gov.br/anpd/pt-br/assuntos/noticias/anpd-abre-tomada-de-subsidios-sobre-tratamento-de-dados-biometricos>;
- ECA Digital, Lei nº 15.211/2025, vigente desde março de 2026: <https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2025/lei/l15211.htm>;
- página oficial da ANPD sobre implementação do ECA Digital: <https://www.gov.br/anpd/pt-br/assuntos/eca-digital>.

## Operações e bases legais distintas

### Indexação do acervo

Extrair embeddings de todos os rostos de uma Galeria pública é uma operação separada do envio voluntário de uma referência. O aceite de quem consulta não autoriza indexar as demais pessoas fotografadas. Antes de habilitar uma galeria, o fotógrafo/controlador MUST:

1. declarar finalidade específica, hipótese do art. 11 da LGPD e como informou os titulares;
2. manter prova dessa base e da transparência anterior à indexação;
3. oferecer seleção manual equivalente sem biometria;
4. impedir indexação quando a declaração estiver ausente, revogada ou vencida;
5. produzir RIPD antes do piloto real, dado o tratamento sensível, automatizado e potencial envolvimento de menores.

O produto não deve presumir que contrato fotográfico, presença no evento, publicação da galeria ou consentimento do cliente que pesquisa bastam. Se a base escolhida for consentimento, ele precisa ser específico, destacado, demonstrável, revogável e associado às finalidades de indexação e descoberta.

### Consulta por referência

A pessoa autenticada que envia a referência MUST receber aviso destacado, separado dos termos gerais, contendo finalidade, controlador, duração, exclusão, ausência de garantia de identidade, possíveis falsos resultados, direitos e alternativa manual. O consentimento específico da consulta SHALL ser versionado e comprovável.

O envio em nome de terceiro exige declaração de legitimidade. Para rosto de criança, exige consentimento verificável de pelo menos um dos pais ou responsável legal e análise concreta do melhor interesse. A recusa ou revogação não pode retirar o acesso ou a seleção manual já permitidos.

## Crianças e adolescentes

O fluxo futuro SHALL adotar proteção reforçada:

- nenhum dado real de criança entra em desenvolvimento ou homologação;
- aviso em linguagem simples e adequada tanto ao responsável quanto ao menor;
- verificação razoável de que o consentimento de criança veio do responsável;
- finalidade limitada a localizar fotos dentro da galeria já autorizada, sem autenticação, classificação, publicidade ou criação de perfil;
- ausência de reconhecimento de emoção, raça, saúde ou outros atributos;
- teste documentado de necessidade e proporcionalidade frente à seleção manual;
- bloqueio da indexação quando o melhor interesse não puder ser demonstrado;
- revisão do RIPD, do ECA Digital e das orientações vigentes da ANPD antes do piloto.

O sistema não deve usar estimativa facial de idade para liberar a busca: isso acrescentaria novo tratamento biométrico. O fluxo deve coletar a declaração etária mínima necessária e, nos casos infantis, comprovar a representação legal por mecanismo não biométrico definido em change própria.

## Ciclo de vida mínimo

| Dado | Coleta/uso | Retenção máxima proposta | Exclusão |
|---|---|---|---|
| JPEG de referência | Um rosto, busca em uma galeria | Até terminar ou falhar a consulta; teto operacional de 15 minutos | Automática em sucesso, falha, cancelamento ou timeout; ação manual idempotente enquanto pendente |
| Embedding da referência | Memória de processo para uma consulta | Somente durante a consulta | Descarte imediato junto da referência; nunca persistir em log, auditoria ou cache |
| Resultado temporário | IDs de fotos candidatas e ordem | 24 horas por padrão; nunca além do prazo da galeria | Cancelamento, revogação, nova busca, expiração ou exclusão manual |
| Embedding do acervo | Índice isolado por galeria e versão | Enquanto base legal, finalidade, galeria e versão permanecerem válidas | Exclusão/opt-out da foto ou galeria, revogação aplicável, expiração ou troca de modelo |
| Registro de auditoria | Evidência de operação e direitos | Conforme política formal de auditoria, sem biometria | Expiração da política; preservar somente obrigação legal demonstrada |

Os prazos propostos são limites de desenho a confirmar na change de produto. Excluir uma foto de origem MUST remover suas entradas do índice mesmo se uma cópia comercial precisar permanecer no histórico de compra. Excluir uma Galeria pública MUST invalidar o índice inteiro, ainda que mídia já selecionada sobreviva em uma privada histórica.

## Segurança e isolamento

- criptografia em trânsito e em repouso para temporários e índice;
- filas, chaves e namespace separados por ambiente e galeria;
- comparação obrigatoriamente filtrada pelo identificador interno da Galeria pública antes do cálculo de candidatos;
- URLs assinadas de curta duração; nenhum embedding no navegador, WhatsApp, analytics ou logs;
- acesso mínimo do worker; rotação e reindexação versionada na troca de modelo;
- limites de tamanho, formato, pixels, tempo, concorrência e tentativas;
- limpeza transacional com retentativa e fila de quarentena apenas por identificadores opacos;
- métricas agregadas sem imagem, vetor, caixa facial, telefone ou nome;
- resposta ao titular capaz de confirmar, bloquear e eliminar o tratamento sem revelar dados de terceiros.

## Resultado, revisão e auditoria

O resultado é uma hipótese visual, não uma afirmação de identidade. A interface deve dizer “possíveis fotos encontradas”, nunca apresentar similaridade como porcentagem de certeza. Nenhuma candidata cria seleção, privada, vínculo, pedido ou autorização; somente a ação consciente de selecionar usa o fluxo comercial já existente.

A revisão prévia do fotógrafo pode ser dispensada apenas se a pessoa já estiver autorizada a ver todas as fotos consideradas e o filtro somente reordenar esse mesmo conjunto. Ela continua obrigatória antes de qualquer ampliação de acesso. Decisão automatizada contestável, revogação ou resultado indevido deve oferecer canal humano.

A auditoria SHALL registrar: galeria e versão por UUID interno, operação, estado, quantidade agregada de rostos/candidatos, versão do modelo e limiar, recibo/versionamento do aviso e consentimento, motivo de exclusão, timestamps UTC e ator. SHALL NOT registrar imagem, embedding, landmarks, caixa facial, similaridade por pessoa ou identidade inferida.

## Riscos residuais e gate

Permanecem riscos de falso positivo, desempenho desigual por grupo e qualidade, exposição de embeddings, base legal inadequada de pessoas incidentais, representação indevida de menores e uso secundário. Portanto, aprovação técnica do modelo não autoriza o produto.

Antes de qualquer piloto real são obrigatórios: RIPD revisado, responsável/controlador definido, textos de transparência e consentimento aprovados, fluxo infantil validado, política de retenção configurada, teste de exclusão ponta a ponta, avaliação de segurança, calibração representativa permitida, medição ARM e revisão humana da change de integração.
