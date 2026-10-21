/** Navegação na mesma aba, sem depender de popup após uma resposta assíncrona. */
export function navigateToCardCheckout(url: string): void {
  window.location.assign(url);
}
