# Tasks

## 1. Resolver os pins de segurança

- [x] 1.1 Atualizar somente `aiohttp`, `multidict`, `urllib3` e o pin incompatível `yarl` conforme o design. Evidência: `backend/requirements-push.txt` agora fixa `aiohttp==3.14.4`, `multidict==6.9.1`, `urllib3==2.8.0` e `yarl==1.25.1`; os demais pins não mudaram.
- [x] 1.2 Confirmar instalação resolvida e `pip check` no conjunto compartilhado, preservando os demais pins. Evidência: `py -3.13 -m pip install --dry-run --ignore-installed -r backend/requirements.txt -r backend/face-requirements.txt -r backend/benchmark-requirements.txt` resolveu o conjunto; instalação isolada equivalente concluiu e `pip check` retornou “No broken requirements found”.

## 2. Validar runtimes consumidores

- [ ] 2.1 Executar testes backend e validar builds/checks da API, Gemma, face e workers que instalam `requirements.txt`.
- [ ] 2.2 Registrar falhas externas de runner separadas de incompatibilidade e confirmar que nenhum job de deploy/publicação foi executado.

## 3. Preparar PR sem integrar

- [ ] 3.1 Revisar diff e validar OpenSpec; criar commit e PR direcionados à `main`.
- [ ] 3.2 Confirmar checks do PR, os 14 alertas associados e os limites de produção/Oracle antes do relatório final.
