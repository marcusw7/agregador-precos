"""Testes da proteção dos endpoints administrativos."""

import pytest
from fastapi import HTTPException

from app.main import app, exigir_admin, token_configurado


def _rotas(caminho: str):
    return [r for r in app.routes if getattr(r, "path", None) == caminho]


def test_endpoints_de_coleta_estao_protegidos():
    post = _rotas("/atualizacoes")
    status = _rotas("/atualizacoes/ultima")
    assert post, "rota POST /atualizacoes não encontrada"
    assert status, "rota GET /atualizacoes/ultima não encontrada"
    assert post[0].dependencies, "POST /atualizacoes precisa exigir autorização"
    assert status[0].dependencies, "GET /atualizacoes/ultima precisa exigir autorização"


def test_sem_token_configurado_responde_503(monkeypatch):
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    assert token_configurado() == ""
    with pytest.raises(HTTPException) as erro:
        exigir_admin()
    assert erro.value.status_code == 503


def test_token_errado_responde_401(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "segredo-de-teste")
    with pytest.raises(HTTPException) as erro:
        exigir_admin(authorization="Bearer errado")
    assert erro.value.status_code == 401

    with pytest.raises(HTTPException) as erro2:
        exigir_admin(x_admin_token="errado")
    assert erro2.value.status_code == 401

    with pytest.raises(HTTPException):
        exigir_admin()  # sem cabeçalho nenhum


def test_token_correto_autoriza(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "segredo-de-teste")
    assert exigir_admin(authorization="Bearer segredo-de-teste") is None
    assert exigir_admin(x_admin_token="segredo-de-teste") is None
    assert exigir_admin(authorization="bearer segredo-de-teste") is None  # caixa indiferente


def test_token_nao_aparece_na_raiz(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "segredo-de-teste")
    from app.main import raiz

    corpo = raiz()
    assert "segredo-de-teste" not in str(corpo)
    assert corpo["coleta_administrativa"] is True
