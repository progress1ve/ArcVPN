from subscription_pages import render_user_agreement


def test_user_agreement_contains_both_documents_and_product_terms():
    page = render_user_agreement(
        profile_title="ArcVPN",
        updated_date="10 сентября 2026",
        support_url="https://support.example/path?x=1&y=2",
        operator_name="ИП Тестов",
        operator_inn="123",
        operator_registration="456",
        operator_address="Москва",
        contact_email="legal@example.test",
    )

    assert "Пользовательское соглашение" in page
    assert "Политика конфиденциальности" in page
    assert "Автопродление подключается только по отдельному выбору" in page
    assert "права потребителя" in page
    assert "не ведёт список посещённых сайтов" in page
    assert "https://support.example/path?x=1&amp;y=2" in page


def test_user_agreement_escapes_dynamic_legal_values():
    page = render_user_agreement(
        profile_title='<script>alert("title")</script>',
        updated_date="<b>date</b>",
        support_url='https://example.test/\" onclick=\"alert(1)',
        operator_name="<img src=x onerror=alert(1)>",
        operator_inn="<123>",
        operator_registration="<456>",
        operator_address="<address>",
        contact_email="<mail@example.test>",
    )

    assert "<script>" not in page
    assert "<img" not in page
    assert 'onclick="alert(1)' not in page
    assert "&lt;mail@example.test&gt;" in page
