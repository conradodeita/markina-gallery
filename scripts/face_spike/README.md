# Harness isolado do spike facial

Este diretório contém somente ferramentas reproduzíveis do spike OpenSpec `spike-private-facial-discovery`. Ele não é importado pela API, pelo worker ou pelo frontend.

O corpus e os modelos devem ficar fora do repositório. Use apenas folhas 4 × 4 de adultos ficcionais geradas para o experimento.

```powershell
python scripts/face_spike/dataset.py build `
  --front-sheet C:\caminho\front.png `
  --angle-sheet C:\caminho\angle.png `
  --output C:\caminho\temporario\markina-face-spike-run

python scripts/face_spike/dataset.py verify `
  --output C:\caminho\temporario\markina-face-spike-run

python scripts/face_spike/models.py prepare `
  --manifest scripts/face_spike/model-manifest.json `
  --model-root C:\caminho\temporario\markina-face-spike-models

python scripts/face_spike/harness.py `
  --dataset-root C:\caminho\temporario\markina-face-spike-run `
  --yunet C:\caminho\temporario\markina-face-spike-models\face_detection_yunet_2023mar.onnx `
  --sface C:\caminho\temporario\markina-face-spike-models\face_recognition_sface_2021dec.onnx `
  --output C:\caminho\temporario\markina-face-spike-run\benchmark.json

python scripts/face_spike/models.py clean `
  --manifest scripts/face_spike/model-manifest.json `
  --model-root C:\caminho\temporario\markina-face-spike-models

python scripts/face_spike/dataset.py clean `
  --output C:\caminho\temporario\markina-face-spike-run
```

Os comandos `clean` apagam recursivamente somente diretórios que contenham o marcador gerado pelo respectivo utilitário. Nunca aponte os comandos para o repositório, diretório pessoal ou raiz de disco.

O smoke ARM pode ser executado em um container `linux/arm64` com o repositório, corpus e modelos montados somente para leitura. Com `/work` no `PYTHONPATH`, use `python -m scripts.face_spike.arm_smoke --model-root /models --query /dataset/queries/<arquivo>.jpg` dentro do container. Ele retorna apenas dimensões e contagens agregadas, nunca o vetor.
