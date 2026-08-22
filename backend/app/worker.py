"""Worker placeholder — scaffolding da fundação.

A fila real (Redis + processamento de importação, miniaturas, Drive e mensagens)
será introduzida pela mudança que implementar o domínio correspondente.
"""

import time


def main() -> None:
    print("markina-gallery-worker: scaffolding ativo, aguardando fila de trabalhos", flush=True)
    while True:
        time.sleep(30)


if __name__ == "__main__":
    main()
