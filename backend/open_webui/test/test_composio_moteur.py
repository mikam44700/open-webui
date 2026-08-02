"""Fusion de la carte des serveurs MCP.

Hermes ne sait que remplacer la carte entiere. Une fusion ratee efface les
serveurs MCP du client sans qu'aucune erreur ne s'affiche — d'ou ces tests,
qui portent sur la seule chose capable de detruire quelque chose ici.
"""

from open_webui.routers.composio import (
    ENTETE_MCP,
    NOM_SERVEUR_MCP,
    _carte_depuis_hermes,
    fusionner_serveurs,
)

ENTREE = {"url": "https://mcp.composio.dev/abc", "headers": dict(ENTETE_MCP)}


def test_ajoute_sans_toucher_aux_autres():
    existants = {
        "figma": {"url": "https://figma.example/mcp"},
        "n8n": {"command": "npx", "args": ["n8n-mcp"]},
    }
    fusionnee = fusionner_serveurs(existants, NOM_SERVEUR_MCP, ENTREE)
    assert set(fusionnee) == {"figma", "n8n", NOM_SERVEUR_MCP}
    assert fusionnee["figma"] == {"url": "https://figma.example/mcp"}
    assert fusionnee["n8n"] == {"command": "npx", "args": ["n8n-mcp"]}
    assert fusionnee[NOM_SERVEUR_MCP] == ENTREE


def test_ne_modifie_pas_la_carte_recue():
    existants = {"figma": {"url": "https://figma.example/mcp"}}
    fusionner_serveurs(existants, NOM_SERVEUR_MCP, ENTREE)
    assert existants == {"figma": {"url": "https://figma.example/mcp"}}


def test_carte_vide_donne_une_seule_entree():
    assert fusionner_serveurs({}, NOM_SERVEUR_MCP, ENTREE) == {NOM_SERVEUR_MCP: ENTREE}


def test_reconfigure_sans_rallumer_un_serveur_eteint():
    """Le client avait eteint Composio : reconfigurer ne doit pas le rallumer."""
    existants = {NOM_SERVEUR_MCP: {"url": "https://ancienne", "enabled": False}}
    fusionnee = fusionner_serveurs(existants, NOM_SERVEUR_MCP, ENTREE)
    assert fusionnee[NOM_SERVEUR_MCP]["enabled"] is False
    assert fusionnee[NOM_SERVEUR_MCP]["url"] == ENTREE["url"]


def test_remplace_l_ancienne_adresse():
    existants = {NOM_SERVEUR_MCP: {"url": "https://ancienne", "headers": {"X": "1"}}}
    fusionnee = fusionner_serveurs(existants, NOM_SERVEUR_MCP, ENTREE)
    assert fusionnee[NOM_SERVEUR_MCP]["url"] == ENTREE["url"]
    assert fusionnee[NOM_SERVEUR_MCP]["headers"] == ENTETE_MCP


def test_carte_depuis_liste_de_resumes():
    charge = {
        "servers": [
            {"name": "figma", "url": "https://figma.example/mcp", "enabled": True},
            {"name": "n8n", "command": "npx", "args": ["n8n-mcp"]},
        ]
    }
    carte = _carte_depuis_hermes(charge)
    assert carte["figma"]["url"] == "https://figma.example/mcp"
    assert carte["n8n"]["command"] == "npx"


def test_carte_depuis_resume_avec_config_imbriquee():
    charge = {"servers": [{"name": "figma", "config": {"url": "https://f/mcp"}}]}
    assert _carte_depuis_hermes(charge) == {"figma": {"url": "https://f/mcp"}}


def test_carte_deja_sous_forme_de_dictionnaire():
    charge = {"servers": {"figma": {"url": "https://f/mcp"}}}
    assert _carte_depuis_hermes(charge) == {"figma": {"url": "https://f/mcp"}}


def test_resume_sans_nom_est_ignore_sans_casser_les_autres():
    charge = {"servers": [{"url": "https://sans-nom"}, {"name": "figma", "url": "https://f"}]}
    assert _carte_depuis_hermes(charge) == {"figma": {"url": "https://f"}}


def test_carte_vide_quand_hermes_ne_dit_rien():
    assert _carte_depuis_hermes({}) == {}
    assert _carte_depuis_hermes({"servers": []}) == {}
