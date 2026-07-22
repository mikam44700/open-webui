"""Inventaire exécutable du catalogue réel des modèles LunarIA.

Usage dans le conteneur de production :
    python -m open_webui.hermes_bridge.catalog_audit

La liste n'est jamais recopiée ici : elle provient du même adapter que l'interface.
Le processus quitte avec une erreur dès qu'un provider n'a pas de politique cohérente.
"""

from __future__ import annotations

from collections import Counter

from .hermes_adapter import list_providers
from .model_catalog import SMALL_CATALOG_MAX


def audit_catalog() -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    errors: list[str] = []

    for provider in list_providers():
        expected_sort = (
            "alphabetical_search"
            if len(provider.models) > SMALL_CATALOG_MAX
            else "recent_first"
        )
        confidence = Counter(model.metadata_confidence for model in provider.models)
        if not provider.catalog_source or not provider.catalog_refresh:
            errors.append(f"{provider.id}: politique de source/mise à jour absente")
        if provider.catalog_sort != expected_sort:
            errors.append(
                f"{provider.id}: tri {provider.catalog_sort!r}, attendu {expected_sort!r}"
            )
        if any(model.provider_id != provider.id for model in provider.models):
            errors.append(f"{provider.id}: rattachement provider/modèle incohérent")

        rows.append(
            {
                "id": provider.id,
                "category": provider.category.value,
                "state": provider.state.value,
                "models": len(provider.models),
                "source": provider.catalog_source,
                "refresh": provider.catalog_refresh,
                "sort": provider.catalog_sort,
                "confidence": ", ".join(
                    f"{name}:{count}" for name, count in sorted(confidence.items())
                )
                or "aucun modèle",
            }
        )

    if errors:
        raise RuntimeError("Audit catalogue en échec:\n- " + "\n- ".join(errors))
    return rows


def markdown_report(rows: list[dict[str, str | int]]) -> str:
    lines = [
        f"# Audit catalogue — {len(rows)} providers",
        "",
        "| Provider | Catégorie | État | Modèles | Source | Mise à jour | Tri | Confiance intelligence |",
        "|---|---|---|---:|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {id} | {category} | {state} | {models} | {source} | {refresh} | {sort} | {confidence} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "> Inventaire généré depuis `hermes_adapter.list_providers()` ; aucune liste de providers n'est dupliquée dans ce rapport.",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    print(markdown_report(audit_catalog()))
