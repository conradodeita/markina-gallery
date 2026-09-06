# Avaliação de candidatos, licenças e ARM

Levantamento concluído em 2026-09-05. “Código aberto” e “peso pré-treinado liberado para uso comercial” foram avaliados separadamente. Esta análise técnica não substitui parecer jurídico para o rollout.

## Resultado

| Candidato | Código | Peso avaliado | ARM | Decisão do spike |
|---|---|---|---|---|
| OpenCV YuNet + SFace | OpenCV Apache-2.0; YuNet MIT; SFace Apache-2.0 | Licenças incluídas nos próprios diretórios dos modelos | Wheel Linux AArch64 disponível; OpenCV Zoo publica benchmarks em ARM | **Baseline aprovado para benchmark** |
| AdaFace R18 | Repositório MIT | Downloads de pesos são publicados, mas o repositório não declara de forma inequívoca a cadeia comercial de cada peso/dataset | ONNX Runtime suporta CPU ARM; conversão e desempenho ainda precisariam ser medidos | **Excluído da recomendação comercial enquanto a licença do peso não for comprovada** |
| InsightFace / Buffalo | Código MIT | Pesos públicos limitados a pesquisa acadêmica não comercial | Servidor oficial publicado para Linux x86_64 | **Excluído** |
| DeepFace | Wrapper MIT | Herda a licença de cada modelo carregado | Possível, mas adiciona camada sem resolver licença ou desempenho | **Somente referência; não candidato** |
| CompreFace | Apache-2.0 | Distribuição reúne modelos/configurações distintos | Documentação padrão exige x86 + AVX; cinco serviços e banco próprios | **Excluído do alvo ARM** |

## Baseline selecionado

### Detector YuNet

- Artefato: `face_detection_yunet_2023mar.onnx`.
- Origem oficial: <https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet>.
- Licença do diretório, incluindo o modelo: MIT.
- Tamanho observado: `232589` bytes.
- SHA-256 observado: `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`.

### Reconhecedor SFace

- Artefato: `face_recognition_sface_2021dec.onnx`.
- Origem oficial: <https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface>.
- Licença do diretório, incluindo o modelo: Apache-2.0.
- Tamanho observado: `38696353` bytes.
- SHA-256 observado: `0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79`.
- O ponto de operação de cosseno `0.363` publicado pelo exemplo oficial será apenas um dos limiares medidos, não uma configuração presumida de produção.

### Runtime ARM

O OpenCV Zoo declara benchmarks em Raspberry Pi 4B, Jetson e outras plataformas ARM: <https://github.com/opencv/opencv_zoo>. A versão isolada escolhida para o harness, `opencv-python-headless==4.12.0.88`, possui wheel oficial `manylinux2014_aarch64` no PyPI: <https://pypi.org/project/opencv-python-headless/4.12.0.88/>. Isso comprova instalabilidade AArch64, mas não substitui a medição no hardware Oracle alvo.

## Concorrentes excluídos ou condicionais

### AdaFace

O projeto oficial e seus benchmarks estão em <https://github.com/mk-minchul/AdaFace>. O repositório é MIT e publica links de pesos, mas não há declaração específica suficiente de que cada peso pré-treinado e sua cadeia de dados podem ser usados comercialmente. O candidato permanece tecnicamente promissor para baixa qualidade, porém não será baixado nem recomendado pelo spike sem comprovação adicional por escrito.

### InsightFace

A política oficial separa o código MIT dos modelos públicos e limita estes últimos a pesquisa não comercial: <https://github.com/deepinsight/insightface#license>. Precisão superior não supera esse bloqueio de licença.

### DeepFace e CompreFace

DeepFace informa expressamente que as licenças dos modelos encapsulados são herdadas: <https://github.com/serengil/deepface#licence>. CompreFace documenta cinco serviços e requisito padrão x86/AVX: <https://github.com/exadel-inc/CompreFace/blob/master/docs/Installation-options.md>. Nenhum dos dois reduz o risco operacional do baseline direto em OpenCV.

## Condições para produção

1. usar somente URLs e hashes fixados no manifesto do harness;
2. preservar textos de licença e atribuição exigidos;
3. repetir a instalação e o benchmark no ARM Oracle em ambiente isolado autorizado;
4. recalibrar limiares em corpus representativo permitido, sem converter similaridade em certeza de identidade;
5. reabrir a avaliação de licença diante de qualquer troca de peso, versão ou fonte.
