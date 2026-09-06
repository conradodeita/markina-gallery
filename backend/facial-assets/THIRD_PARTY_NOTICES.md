# Modelos faciais de terceiros

Os pesos não são armazenados no Git. O build facial baixa somente os artefatos
fixados em `model-manifest.json` e valida tamanho e SHA-256 antes de utilizá-los.

## YuNet

- Projeto: OpenCV Zoo — Face Detection YuNet
- Arquivo: `face_detection_yunet_2023mar.onnx`
- Licença declarada pelo diretório do modelo: MIT
- Código-fonte/licença: <https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/face_detection_yunet>

## SFace

- Projeto: OpenCV Zoo — Face Recognition SFace
- Arquivo: `face_recognition_sface_2021dec.onnx`
- Licença declarada pelo diretório do modelo: Apache-2.0
- Código-fonte/licença: <https://github.com/opencv/opencv_zoo/tree/47534e27c9851bb1128ccc0102f1145e27f23f98/models/face_recognition_sface>

O OpenCV utilizado pelo runtime é distribuído sob Apache-2.0. A inclusão de
qualquer novo código, peso ou exportação ONNX exige revisão individual de sua
origem e licença antes de alterar o manifesto.
