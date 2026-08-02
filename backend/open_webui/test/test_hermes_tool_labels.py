from open_webui.utils.hermes_tool_labels import humanize_tool_progress


def test_url_is_reduced_to_its_domain() -> None:
    assert humanize_tool_progress('browser_navigate', 'https://www.example.com/private/path') == (
        'Navigation en cours',
        'Je consulte example.com',
    )


def test_unknown_tool_never_leaks_its_technical_name() -> None:
    title, description = humanize_tool_progress('dangerous_internal_tool', '/secret/path')
    assert (title, description) == ('Travail en cours', 'Je travaille sur votre demande')
    assert 'dangerous_internal_tool' not in description
    assert '/secret/path' not in description


def test_long_context_is_single_line_and_bounded() -> None:
    _, description = humanize_tool_progress('web_search', 'une\nrequête ' + ('très longue ' * 20))
    assert '\n' not in description
    assert len(description) < 90

