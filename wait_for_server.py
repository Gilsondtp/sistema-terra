"""Wait until the local Sistema Terra Flask server answers its health endpoint."""

import http.client
import json
import os
import sys
import time


def wait_for_server():
    try:
        port = int(os.environ.get("PORT", "5000"))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        print("A porta configurada para o Sistema Terra e invalida.", file=sys.stderr, flush=True)
        return 1

    try:
        timeout_seconds = max(5, int(os.environ.get("TERRA_STARTUP_TIMEOUT_SECONDS", "120")))
    except ValueError:
        timeout_seconds = 120

    deadline = time.monotonic() + timeout_seconds
    last_message_at = 0.0
    print(
        f"Aguardando o Sistema Terra em http://127.0.0.1:{port}/healthz "
        f"(limite: {timeout_seconds}s)...",
        flush=True,
    )

    while time.monotonic() < deadline:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        try:
            connection.request("GET", "/healthz", headers={"Connection": "close"})
            response = connection.getresponse()
            payload = json.loads(response.read(4096).decode("utf-8"))
            if (
                response.status == 200
                and isinstance(payload, dict)
                and payload.get("service") == "sistema-terra"
                and payload.get("status") == "ok"
            ):
                print("Sistema Terra pronto; abrindo o navegador.", flush=True)
                return 0
        except (http.client.HTTPException, OSError, ValueError, json.JSONDecodeError):
            pass
        finally:
            connection.close()

        now = time.monotonic()
        if now - last_message_at >= 15:
            remaining = max(0, int(deadline - now))
            print(f"Ainda inicializando; tempo restante: {remaining}s.", flush=True)
            last_message_at = now
        time.sleep(1)

    print(
        "O servidor não respondeu dentro do prazo. Consulte sistema_terra.log "
        "na pasta do projeto; se o arquivo não existir, execute iniciar_sistema.bat "
        "e envie a mensagem exibida.",
        file=sys.stderr,
        flush=True,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(wait_for_server())
