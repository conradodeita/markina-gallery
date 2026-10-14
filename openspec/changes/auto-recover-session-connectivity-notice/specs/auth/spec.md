# Spec Delta

## ADDED Requirements

A recuperação automática abaixo substitui a dependência de tentativa explícita descrita em `add-small-multi-photographer-pilot`, preservando a revalidação periódica de segurança e os tratamentos de revogação/expiração existentes.

### Requirement: Recuperação automática de conectividade em áreas autenticadas

O frontend SHALL acompanhar falhas transitórias de API nas áreas autenticadas de fotógrafo e cliente e iniciar automaticamente a reconexão/revalidação da sessão, sem exigir que o usuário clique em “Reconectar” ou “Verificar conexão novamente”. O aviso global de indisponibilidade SHALL aparecer somente enquanto a própria verificação de sessão não puder confirmar conectividade; falha isolada de uma operação SHALL permanecer no fluxo dessa operação. As verificações automáticas SHALL ser limitadas, sem sobreposição e pausadas enquanto a página estiver oculta. Quando a sessão voltar a ser confirmada para o mesmo contexto, o aviso temporário SHALL ser removido automaticamente. A checagem de conectividade MUST NOT repetir requisições comerciais, OTP, uploads ou outras operações que possam produzir efeitos duplicados.

#### Scenario: Sessão recuperada sem intervenção

- **WHEN** uma chamada protegida falha temporariamente e uma verificação automática posterior confirma o mesmo contexto de sessão
- **THEN** o aviso de indisponibilidade desaparece sem clique do fotógrafo ou cliente e o sistema não reenvia a chamada que falhou

#### Scenario: Serviço ainda indisponível

- **WHEN** a sessão não pode ser confirmada por falha de rede, timeout ou erro temporário do servidor
- **THEN** o aviso permanece visível e as verificações automáticas continuam com frequência limitada, sem criar requisições concorrentes ilimitadas

#### Scenario: Erros concorrentes durante recuperação

- **WHEN** existe uma tentativa automática agendada e outras operações falham
- **THEN** essas falhas e a verificação periódica SHALL respeitar o backoff agendado sem antecipar novas consultas da sessão

#### Scenario: Falha isolada em uma operação

- **WHEN** uma chamada de operação retorna erro transitório, mas a verificação automática confirma a sessão no mesmo contexto
- **THEN** o aviso global de indisponibilidade não permanece na tela e o erro próprio da operação continua visível no fluxo correspondente

#### Scenario: Página volta a ficar visível

- **WHEN** a página autenticada estava oculta durante a indisponibilidade e volta a ficar visível
- **THEN** o sistema retoma automaticamente a verificação de sessão, respeitando a deduplicação de chamadas em andamento

#### Scenario: Sessão expirada durante a recuperação

- **WHEN** a verificação automática confirma que a sessão expirou
- **THEN** o sistema preserva o fluxo existente de limpeza e redirecionamento de autenticação, sem manter o aviso temporário nem expor conteúdo privado

#### Scenario: Falha ambígua em operação com efeito

- **WHEN** uma requisição de envio, compra ou upload falha e seu resultado pode ser desconhecido
- **THEN** a verificação automática confirma apenas conectividade/sessão, não repete a operação e mantém a semântica existente de reconciliação ou consulta do resultado
