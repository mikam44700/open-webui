"""Modules par fournisseur de passerelle (openrouter, kilocode, novita, ...).

Chaque module expose ses propres constantes/caches et ses fonctions ``_fetch_*`` /
``_*_has_credit`` / ``_*_model_pairs``. ``hermes_adapter.py`` les importe et les
ré-exporte pour que les tests existants continuent d'y accéder via
``providers_bridge.hermes_adapter._<symbole>``.

Règle anti-cycle : ces modules ne doivent JAMAIS importer ``hermes_adapter`` au
niveau module (ça recréerait le cycle que ce découpage cherche à éviter). S'ils ont
besoin d'un helper du socle (``read_env_value``, ``_http_status``...), ils
l'importent à l'intérieur de la fonction qui l'utilise (import différé).
"""
