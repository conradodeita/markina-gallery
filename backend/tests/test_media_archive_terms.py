from app.photographer_terms import DEFAULT_TEMPLATE, _draft_payload, validate_template


def test_editable_default_terms_describe_folder_archive_and_credit_recovery():
    template = DEFAULT_TEMPLATE.read_text(encoding="utf-8-sig")

    assert validate_template(template) == template.strip()
    normalized = " ".join(template.split()).casefold()
    for clause in (
        "cada pasta de conteúdo",
        "30 dias corridos completos",
        "carrinhos sem pedido enviado não impedem o arquivamento",
        "por 30 dias de acesso, contados da conclusão da recuperação",
        "taxa vigente, configurada pelo provedor para cada pasta e ciclo",
        "só é debitada depois que todos os arquivos são recuperados, verificados e disponibilizados",
        "preserva a taxa e o prazo do pedido original",
        "não há expurgo automático da mídia arquivada nesta versão",
    ):
        assert clause in normalized


def test_default_terms_do_not_store_owner_identity_in_the_repository():
    draft = _draft_payload(None)

    assert draft["provider_legal_name"] == ""
    assert draft["provider_contact_email"] == ""
    assert "{{provider_legal_name}}" in draft["template_text"]
