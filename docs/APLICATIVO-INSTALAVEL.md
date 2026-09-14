# Aplicativo instalável — Pick-your-Pic

O mesmo PWA atende fotógrafo e cliente. A instalação não cria outra conta, não muda permissões e não substitui login/OTP. Ao abrir pelo ícone, a entrada é a página inicial neutra `/`.

- Chrome/Edge compatíveis: “Instalar aplicativo” aparece no topo quando o navegador libera a instalação; o clique abre o prompt nativo. Recusar não causa repetição automática.
- iPhone/iPad: o botão apresenta instruções para adicionar pelo menu de compartilhamento. Se a opção não estiver disponível naquele navegador, abrir no Safari.
- Safari desktop: instrução de Arquivo → Adicionar ao Dock, quando suportado.
- Em modo standalone ou após a instalação na sessão, a ação fica oculta. A detecção universal de instalação fora do aplicativo não existe em todos os navegadores; o botão manual pode continuar aparecendo ao voltar ao navegador.

## Privacidade e offline

O service worker `/markina-sw.js` não usa CacheStorage nem persiste fotos, respostas de API, páginas autenticadas ou tokens. Requisições existentes continuam usando autorização/cache privado do backend. Uma navegação documental sem rede recebe somente uma página neutra de reconexão; não há acervo offline. Push e notificações não foram incluídos nesta change.

HTTPS é necessário em homologação/produção. Manifesto em `/manifest.webmanifest`. Os ícones são os arquivos oficiais enviados em Configurações → Identidade visual: `/api/branding/favicon` para o navegador e `/api/branding/app-icon?size=180`, `?size=192` e `?size=512` para Apple/PWA. Os tamanhos PNG preservam proporção com margem transparente quando necessário; a arte original não é alterada. Não existe ícone substituto desenhado pelo sistema. Sem upload, a rota retorna 404 e a instalação pode não ser oferecida. Recomenda-se arte quadrada de pelo menos 512 px para boa definição.

Configurações mostra prévias, estado de envio e erro recuperável. Os arquivos de marca revalidam cache HTTP; trocar o favicon atualiza a referência na página aberta. Aplicativos já instalados podem depender do ciclo de atualização do navegador/SO para refletir nova arte. Identidade preto/amarelo, fundo cinza claro e bege em botões secundários. A versão do worker é verificada sem cache HTTP; atualizações não precisam apagar cache privado porque ele não é criado.

## Verificação

Testes focados: `app/install-app.test.tsx`, `app/pwa-contract.test.ts`. Conferir também em navegador real o manifesto, PNGs, registro do worker, botão, instalação no dispositivo e reentrada autenticada. A simulação do evento em teste automatizado comprova a ação da UI, não a instalação no sistema operacional do usuário.

Referências: [guia Next.js](https://nextjs.org/docs/app/guides/progressive-web-apps) e [prompt de instalação MDN](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/How_to/Trigger_install_prompt).
