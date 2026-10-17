# Evidências e limites — 17/10/2026

## Autorização e escopo

O proprietário forneceu as referências `DSC07382.jpg`, `untitled-06490.jpg`, `untitled-09930.jpg`, autorizou o teste na sessão cliente autenticada e identificou `LIV00862.jpg` como positivo esperado para a primeira referência. Depois solicitou investigar e corrigir e conferir a condução ao resultado. Finalidade desta execução: diagnosticar e corrigir o fluxo existente, restrito à Galeria pública autorizada `2f0aadfb-1f68-413d-9edd-962e1356aac6`. Não há autorização para ampliar rollout, trocar modelos, editar `.env`/secrets ou publicar sem o gate operacional.

## Baseline reproduzido

Servidor e API/worker de busca na revisão `0779b3e`; main de preparação `b695b2e`. Checkout original `5774ed7` não representa o runtime. As três consultas compararam 2691/2691 fotos, terminaram em `no_candidates` e confirmaram exclusão da referência. Toque no rosto em primeiro plano de `LIV00862.jpg` terminou em `ready` com dez candidatas, incluindo essa foto. Não houve seleção ou compra.

## Diagnóstico do índice persistido

Inventário SSH limitado à Markina: serviços saudáveis, Nginx em `127.0.0.1:8080`, domínio `markina.pickyourpic.com.br`. API cerca de 195 MiB; worker de busca cerca de 159/512 MiB antes da medição. A inferência das referências foi feita localmente; no servidor apenas comparação de vetores em memória em transação PostgreSQL `READ ONLY`, com timeout de statement de 15 segundos. Nenhuma tabela, índice ou configuração foi alterada. Dados temporários viajaram somente pelo canal SSH; relatórios não contêm vetores, crops, coordenadas, scores ou chaves.

OpenCV local/remoto 4.12.0; pesos YuNet/SFace conferidos com os hashes fixados no manifesto. Configuração efetiva: limiar firme 750, faixa ambígua ausente, detecção default, SFace versão `yunet-2023mar+sface-2021dec`, qualidade `opencv-technical-v1`. A foto de controle tem três regiões highres-v1 e fingerprints atuais; o rosto selecionado na UI corresponde ao ordinal 0.

O par positivo `DSC07382.jpg` → região principal de `LIV00862.jpg` falha em 750 e passa em 500. Isso confirma a rejeição pelo limiar no caso indicado; não é falha de transferência, modelo incompatível ou fingerprint obsoleto. Os embeddings da mesma imagem pelos caminhos de referência/indexação coincidem numericamente em experimento local controlado.

Comparação em memória restrita ao snapshot original da cliente, acesso canônico atual e fingerprints correntes: 2691 fotos autorizadas, 10531 rostos. Contagens de candidatas por foto, ainda sem anotação humana de todas as identidades:

| Referência | 750 | 650 | 600 | 550 | 500 | 450 | 363 |
|---|---:|---:|---:|---:|---:|---:|---:|
| DSC07382.jpg | 0 | 6 | 13 | 20 | 23 | 51 | 346 |
| untitled-06490.jpg | 0 | 0 | 0 | 9 | 18 | 50 | 532 |
| untitled-09930.jpg | 0 | 21 | 22 | 35 | 53 | 160 | 861 |

A foto de controle fica em oitavo lugar para a primeira referência e em décimo quarto para a segunda. Só o primeiro par tem ground truth explicitamente fornecido pelo proprietário. Não transformar as demais posições ou os dez resultados do controle em rótulos de verdade automaticamente. Não foi medida precisão/recall/FAR real; 500 é proposta para possibilidades revisáveis, não uma calibração formal.

## Conclusão de UI

`frontend/app/public-galleries/[galleryId]/page.tsx` condiciona a rolagem a `regionRequest.current`; `FacialSearchPanel` envia resultados de upload sem registrar esse contexto. O efeito atual usa `window.scrollTo({top: 0})`. Na sessão real, o bloco `Possibilidades encontradas` estava cerca de 1034 pixels abaixo do topo, após a capa. Assim a conclusão por upload não garante condução e o retorno ao topo por toque não garante fotos encontradas no viewport.

## Pendências

Proprietário aprovou em 17/10/2026 a faixa 500 para upload/câmera e a navegação; posteriormente pediu também faixa 600 por toque mesmo com pessoas erradas possíveis. Implementação e regressões estão em preparação, sem suítes automatizadas locais ou publicação nesta change. CI ainda pendente. A revisão visual e a qualidade das candidatas devem ser registradas separadamente da aprovação dos contratos automatizados.

## Implementação preparada para CI

- Configuração: `FACIAL_REFERENCE_AMBIGUOUS_THRESHOLD_MILLI` default 500 e `FACIAL_REGION_AMBIGUOUS_THRESHOLD_MILLI` default 600, ambos desativáveis por vazio e limitados a 0–1000. Compose preserva vazio explícito usando substituição sem `:`. Nenhum `.env` foi editado.
- Worker: origem persistida e namespace SFace escolhem a faixa; limiar firme, faixa geral mais permissiva, Gemma, autorização, fingerprints e lifecycle permanecem nos contratos existentes.
- Navegação: confirmação normal/recuperada marca consulta iniciada nesta página; `ready` com fotos renderizáveis fecha ampliação, foca e rola para o título real uma vez. Restauração não marca nova admissão. Pasta e interações posteriores são preservadas.
- Regressões preparadas: parser de ambas as faixas (default, vazio, limites e inválidos); worker real com índice sintético e cossenos conhecidos nas fronteiras, classificação, origem e limpeza; engine Gemma positiva/ortogonal; React com upload/câmera, 100% em ranking, fotos tardias, confirmação incerta, restauração/polling, terminais vazios e repetição do mesmo UUID.
- `openspec validate fix-uploaded-face-reference-matching --strict` e `git diff --check` passaram antes do envio. Isso não substitui CI nem teste visual do runtime publicado.
