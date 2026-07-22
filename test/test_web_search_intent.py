from open_webui.utils.web_search_intent import classify_web_search_intent


def decision(message: str) -> tuple[bool, str]:
    result = classify_web_search_intent(message)
    return result.should_search, result.reason


def test_conversational_messages_stay_direct():
    assert decision('Salut, comment vas-tu ?')[0] is False
    assert decision('Présente-toi en une phrase.')[0] is False
    assert decision('Explique-moi simplement ce qu’est une facture.')[0] is False
    assert decision('Réécris ce courriel avec un ton professionnel.')[0] is False


def test_explicit_and_fresh_requests_use_web():
    assert decision("Recherche sur Internet les actualités OpenAI aujourd'hui.") == (
        True,
        'explicit',
    )
    assert decision('Quelle est la dernière version de Hermes Agent ?') == (True, 'freshness')
    assert decision('What is the latest OpenAI news?') == (True, 'freshness')


def test_source_and_live_product_requests_use_web():
    assert decision('Explique cette annonce avec les sources et les liens.') == (
        True,
        'verification',
    )
    assert decision('Kimi K3 est disponible sur quel abonnement ?') == (
        True,
        'live_product',
    )


def test_urls_use_web():
    assert decision('Analyse https://example.com/article') == (True, 'url')
    assert decision('Lis www.example.com et résume la page.') == (True, 'url')


def test_user_opt_out_has_priority_over_other_signals():
    assert decision("Sans rechercher sur Internet, explique-moi les actualités d'hier.") == (
        False,
        'user_opt_out',
    )
    assert decision('Do not search the web; answer only from memory.') == (
        False,
        'user_opt_out',
    )


def test_empty_message_stays_direct():
    assert decision('') == (False, 'empty')
