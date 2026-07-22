import types
import unittest
from unittest import mock

from open_webui.hermes_bridge.model_catalog import (
    SMALL_CATALOG_MAX,
    clean_model_label,
    provider_catalog_policy,
    verified_model_metadata,
)
from open_webui.hermes_bridge.providers._shared import _display_pairs
from open_webui.hermes_bridge.providers import kimi as kimi_provider
from open_webui.hermes_bridge.providers.kimi import _kimi_code_callable_ids


class ModelCatalogTests(unittest.TestCase):
    def test_threshold_selects_the_expected_navigation(self):
        self.assertEqual(
            provider_catalog_policy("future-provider", SMALL_CATALOG_MAX)["sort"],
            "recent_first",
        )
        self.assertEqual(
            provider_catalog_policy("future-provider", SMALL_CATALOG_MAX + 1)["sort"],
            "alphabetical_search",
        )

    def test_unknown_provider_still_receives_a_total_policy(self):
        self.assertEqual(
            provider_catalog_policy("future-provider", 2),
            {
                "source": "hermes_catalog",
                "refresh": "engine_update",
                "sort": "recent_first",
            },
        )

    def test_visible_label_casing_keeps_the_api_id_untouched(self):
        model_id = "deepseek.v3.2"
        self.assertEqual(clean_model_label(model_id, model_id), "DeepSeek.v3.2")
        self.assertEqual(model_id, "deepseek.v3.2")
        self.assertEqual(clean_model_label("gpt-oss-120b"), "GPT-OSS-120B")
        self.assertEqual(clean_model_label("mimo-v2.5-pro"), "MiMo-V2.5-Pro")

    def test_kimi_live_models_receive_clean_labels_and_stable_order(self):
        served = [
            "kimi-k2.5",
            "kimi-k2-thinking",
            "kimi-k3",
            "kimi-for-coding",
            "kimi-k2.7-code",
            "kimi-for-coding-highspeed",
            "kimi-k2.6",
        ]
        pairs = _display_pairs("kimi-coding", served)
        self.assertEqual(
            pairs,
            [
                ("kimi-k3", "Kimi K3"),
                ("kimi-for-coding-highspeed", "Kimi K2.7 Code HighSpeed"),
                ("kimi-for-coding", "Kimi K2.7 Code"),
                ("kimi-k2.7-code", "Kimi K2.7 Code"),
                ("kimi-k2.6", "Kimi K2.6"),
                ("kimi-k2.5", "Kimi K2.5"),
                ("kimi-k2-thinking", "Kimi K2 Thinking"),
            ],
        )
        self.assertEqual(_display_pairs("kimi-coding-cn", served), pairs)

    def test_kimi_coding_plan_hides_version_names_that_fail_at_chat_time(self):
        served = [
            "kimi-k2.5",
            "kimi-k3",
            "kimi-k2.7-code",
            "kimi-for-coding",
            "kimi-for-coding-highspeed",
            "kimi-k2.6",
        ]
        self.assertEqual(
            _kimi_code_callable_ids(served),
            ["kimi-k3", "kimi-for-coding-highspeed", "kimi-for-coding"],
        )

    def test_kimi_verified_metadata_fixes_dates_and_effort_levels(self):
        self.assertEqual(
            verified_model_metadata("kimi-coding", "kimi-k3")["supported_efforts"],
            ["low", "high", "xhigh"],
        )
        self.assertEqual(
            verified_model_metadata("kimi-coding", "kimi-k2.5")["release_date"],
            "2026-01-27",
        )
        self.assertIsNone(
            verified_model_metadata("kimi-coding", "kimi-k2.7-code")["supported_efforts"]
        )
        self.assertEqual(verified_model_metadata("openai-api", "kimi-k3"), {})


class KimiPlanLockTests(unittest.TestCase):
    """Verrou forfait HighSpeed : sonde réelle simulée (cf. contrôle du 2026-07-22)."""

    def setUp(self):
        # Cache neuf à chaque test : le verrou est mémorisé par clé pendant 6 h.
        kimi_provider._KIMI_LOCK_CACHE = kimi_provider.TTLCache(kimi_provider._KIMI_MODELS_TTL)

    @staticmethod
    def _reponse(status_code: int, text: str = "") -> types.SimpleNamespace:
        return types.SimpleNamespace(status_code=status_code, text=text)

    def test_subscription_refusal_locks_highspeed_and_is_cached(self):
        refus = self._reponse(
            401, '{"error": {"message": "Your current subscription does not have access"}}'
        )
        with mock.patch.object(kimi_provider.httpx, "post", return_value=refus) as sonde:
            self.assertTrue(kimi_provider._kimi_highspeed_locked("sk-kimi-test"))
            self.assertTrue(kimi_provider._kimi_highspeed_locked("sk-kimi-test"))
            sonde.assert_called_once()  # 2e lecture servie par le cache, zéro appel réseau

    def test_successful_call_means_plan_includes_highspeed(self):
        with mock.patch.object(kimi_provider.httpx, "post", return_value=self._reponse(200)):
            self.assertFalse(kimi_provider._kimi_highspeed_locked("sk-kimi-test"))

    def test_network_failure_never_locks_and_is_not_cached(self):
        import httpx

        with mock.patch.object(kimi_provider.httpx, "post", side_effect=httpx.ConnectError("down")):
            self.assertFalse(kimi_provider._kimi_highspeed_locked("sk-kimi-test"))
        refus = self._reponse(401, "subscription")
        with mock.patch.object(kimi_provider.httpx, "post", return_value=refus):
            # La panne n'a pas été mémorisée : la sonde suivante rend son vrai verdict.
            self.assertTrue(kimi_provider._kimi_highspeed_locked("sk-kimi-test"))

    def test_plain_401_without_subscription_wording_does_not_lock(self):
        invalide = self._reponse(401, '{"error": {"message": "Invalid Authentication"}}')
        with mock.patch.object(kimi_provider.httpx, "post", return_value=invalide):
            self.assertFalse(kimi_provider._kimi_highspeed_locked("sk-kimi-test"))

    def test_unavailable_reasons_only_apply_to_coding_plan_keys(self):
        with mock.patch.object(kimi_provider, "_kimi_read_key", return_value="sk-moonshot-legacy"):
            self.assertEqual(kimi_provider._kimi_unavailable_reasons("kimi-coding"), {})
        refus = self._reponse(401, "subscription")
        with (
            mock.patch.object(kimi_provider, "_kimi_read_key", return_value="sk-kimi-test"),
            mock.patch.object(kimi_provider.httpx, "post", return_value=refus),
        ):
            self.assertEqual(
                kimi_provider._kimi_unavailable_reasons("kimi-coding"),
                {"kimi-for-coding-highspeed": "Forfait Allegretto et plus"},
            )


if __name__ == "__main__":
    unittest.main()
