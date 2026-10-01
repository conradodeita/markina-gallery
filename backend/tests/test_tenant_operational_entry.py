"""Fronteira HTTP com duas contas; sem ensaio, monitor ou efeitos externos."""

from fastapi.testclient import TestClient

from app import auth, main
from tests.test_tenant_client_auth import client_db as _client_db
from tests.test_tenant_client_auth import graph as _graph
from tests.test_tenant_client_auth import links as _links
from tests.test_tenant_client_navigation import cookie

client_db, graph, links = _client_db, _graph, _links


def test_HTTP_A_B_catalogos_e_mutacao_cruzada_recusada(client_db, graph, links):
    cookies = [cookie(client_db, row, auth.Role.ADMIN) for row in graph]
    for index, row in enumerate(graph):
        other = graph[1-index]
        with TestClient(main.app) as browser:
            browser.cookies.set("markina_session", cookies[index])
            response = browser.get("/admin/parent-galleries")
            assert response.status_code == 200, response.text
            assert [item["id"] for item in response.json()["parent_galleries"]] == [str(row["parent"].id)]
            directory = browser.get("/admin/clients")
            assert directory.status_code == 200, directory.text
            assert str(row["client"].id) in str(directory.json())
            assert str(other["client"].id) not in str(directory.json())
            assert browser.patch(f"/admin/parent-galleries/{other['parent'].id}/settings",
                json={"name": "Não publicar"}).status_code == 404
            assert browser.get("/admin/capacity-observability").status_code == 403
    client_db.expire_all()
    assert all(row["parent"].name != "Não publicar" for row in graph)


def test_HTTP_suspensao_A_preserva_acesso_independente_de_B(client_db, graph, links):
    cookies = [cookie(client_db, row, auth.Role.ADMIN) for row in graph]
    graph[0]["tenant"].status = "suspended"
    client_db.commit()
    with TestClient(main.app) as browser:
        browser.cookies.set("markina_session", cookies[0])
        assert browser.get("/admin/parent-galleries").status_code == 403
        browser.cookies.set("markina_session", cookies[1])
        response = browser.get("/admin/parent-galleries")
        assert response.status_code == 200, response.text
        assert [item["id"] for item in response.json()["parent_galleries"]] == [str(graph[1]["parent"].id)]
