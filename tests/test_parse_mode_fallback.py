from bot.middlewares.parse_mode_fallback import _plain_text


def test_invalid_html_fallback_does_not_show_raw_tags():
    assert _plain_text('💙 <b>Спасибо!</b> <code>A&amp;B</code>') == '💙 Спасибо! A&B'
