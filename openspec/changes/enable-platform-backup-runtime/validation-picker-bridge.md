# Validação da extensão protegida do Picker

## Escopo aprovado em 19/11/2026

O proprietário autorizou a recriação somente da API e aprovou a extensão técnica da ponte. A implementação adiciona picker-inventory, picker-prepare e picker-apply, com imagem e APP_VERSION preservados, bind fixo read-only/rprivate, origem não criada, metadados root-only, fingerprint e journal privados. A web permanece no ID/processo anterior. Recuperação por fase reutiliza o journal e atua somente na API. O workflow manual production-google-picker-config.yml exige main, CI do SHA exato, fingerprint atual, mesmo host diagnosticado e environment production antes da mutação.

## Evidência local

- Suíte Windows: 151 testes, OK, 78 skips correspondentes a POSIX/root/Engine; a suíte Linux cobre os contratos POSIX.
- Linux root isolado: 151 testes, OK, 23 skips dos ensaios Engine opt-in. Fonte copiada para diretório descartável; somente os finais CRLF dos scripts shell preexistentes foram normalizados nessa cópia. O primeiro ensaio diretamente no bind Windows falhou no instalador por CRLF, sem indicar regressão da implementação.
- Picker com Engine real local 29.9.3 e Compose 5.6.1: 9 testes, OK, 83,347 s. Sucesso com prova real do mount somente leitura e invariância de imagem/versão/web; recuperação após stop, rename e criação interrompidos; configuração inválida recusada antes de stop; configuração root-only e vocabulário fechado. A imagem sintética não contém o módulo da aplicação: exclusivamente a importação de _picker_config foi substituída por leitura/validação do JSON e modo; schema, execução Compose, journal e provas semânticas foram reais.
- O primeiro ensaio de bind em diretório sob o data-root do Docker revelou restrição de propagação desse laboratório. O ensaio final usa diretório exclusivo /tmp/pyp-picker-lab-20261119 fora do data-root e propagação explícita rprivate, sem relaxar a prova.
- Gitleaks 8.24.3 no snapshot expl�cito de arquivos da extens�o: nenhuma ocorr�ncia. A primeira varredura identificou apenas duas fixtures sint�ticas literais; foram substitu�das por constru��o sint�tica sem ampliar allowlist.
- Ruff F/E9, sintaxe Bash dos executores, YAML do novo workflow e OpenSpec estrito passaram. A política existente de workflow de produção passou.

## Operação pendente

Nenhum helper novo foi instalado no Oracle e nenhum container de produção foi recriado. A chave/configuração do Picker já foi provisionada conforme release-preflight.md, mas continua sem mount na API ativa. O candidato manual anterior é apenas evidência: o executor deriva seu próprio candidato do modelo comprovado e não aceita arquivo externo.

Sequência após revisão e merge: CI exato da main; instalação pelo workflow production-app-compose-bridge-install.yml; diagnóstico production-google-picker-config.yml em diagnose; rever fingerprint, inventário e impacto; executar apply com o fingerprint e aprovação protegida usando a autorização operacional registrada; conferir HTTPS, schema, flag facial, mount e invariância das testemunhas. Recuperação usa production-app-handoff-recovery.yml com novo diagnóstico/fingerprint e aprovação própria, sem repetição cega.

A operação pode causar breve indisponibilidade da API. Domínio markina.pickyourpic.com.br, entrada Markina em 127.0.0.1:8080; API 8000/tcp e web 3000/tcp sem nova porta publicada. Banco, workers, volumes, redes, proxy vizinho e serviços de terceiros permanecem fora do alvo. A validação da ponte existente de Nginx e seu reload confinado mantêm o comportamento de release já especificado.

Tasks 3.1, 3.2 e 3.3 continuam abertas; backup real e timer não estão autorizados nesta extensão. Não sincronizar/arquivar sem revisão humana.
