# EdgeFace: avaliação de licenciamento e benchmark

Verificação documental em 19/09/2026, fontes primárias. Não constitui aprovação jurídica.

| Item | Evidência | Decisão |
|---|---|---|
| Código de inferência oficial | [otroshi/edgeface LICENSE](https://github.com/otroshi/edgeface/blob/main/LICENSE): BSD-3-Clause, com preservação de avisos/condições na redistribuição e restrição de endosso | Não assumir MIT; separar código dos pesos |
| Pesos oficiais EdgeFace-Base | [Model card Idiap](https://huggingface.co/Idiap/EdgeFace-Base/blob/main/README.md), revisão exibida 2944a63, declara CC-BY-NC-SA-4.0 | Esse artefato não está liberado para uso comercial; não incluído nas imagens Docker |
| Proveniência | Model card publicado pelo Idiap, com links ao projeto/paper e código oficial | Não substituir por reexport ONNX de terceiros sem hash e cadeia de origem |
| Dados de treinamento | Model card informa WebFace260M, subsets 12M/4M | Treinamento/dataset requer avaliação separada; licença de código não resolve direitos do dataset |
| Redistribuição | Licenças de código e pesos diferem; conversão/quantização não elimina condições do artefato original | Não redistribuir pesos junto ao produto nesta change |

A fonte do código aponta para o projeto de pesquisa e modelos, mas não concede por si só direito comercial sobre cada checkpoint. Para qualquer variante XS/S/XXS distinta, repetir a avaliação do arquivo exato, origem, licença própria, dataset e dependências; não generalizar a licença do Base para todas, nem a BSD do código para seus pesos. Contatar titulares por autorização comercial se essa for a opção escolhida.

## Resultado técnico

Nenhum vencedor declarado. O A/B decisivo está bloqueado pela ausência de corpus real anotado e por aprovação de uso da variante/pesos escolhidos. O protocolo `FaceEmbeddingProvider` mantém modelo, versão, dimensão e entrada alinhada explícitos. Runtime continua SFace 128; filtros recusam vetores de outro modelo ou dimensão. Não há torch.hub remoto em produção, pesos EdgeFace incorporados ou mistura vetorial.

Depois do baseline de detecção validado, comparar modelos sobre as MESMAS regiões, com alinhamento/preprocessamento próprios documentados, thresholds separados e métricas top-k/FP/FN/latência/CPU/RSS/ARM. Uma melhora pública de LFW não substitui a avaliação no domínio Markina.
