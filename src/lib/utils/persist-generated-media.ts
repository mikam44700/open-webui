// Rapatrie les médias GÉNÉRÉS (images/vidéos) dans NOTRE stockage pour que leur lien
// ne meure jamais.
//
// Les CDN des fournisseurs de génération (ex. files-cdn.x.ai pour Grok, fal.media pour
// FAL) servent des URLs qui EXPIRENT au bout de quelques heures/jours. Une fois la
// réponse terminée, on télécharge le média pendant qu'il est encore vivant (endpoint
// backend `/utils/media/persist`, qui le range dans le volume persistant) et on réécrit
// l'URL du message vers `/api/v1/files/{id}/content`. Au rechargement de la conversation,
// l'URL est déjà locale → plus de lien mort, plus de re-rapatriement (idempotent).
//
// Repli gracieux : si un rapatriement échoue, on GARDE l'URL d'origine (aucune perte
// d'affichage). On ne touche QUE les hôtes connus pour expirer (liste blanche) afin de
// ne jamais rapatrier par erreur une image permanente collée par l'utilisateur.

import { WEBUI_API_BASE_URL } from '$lib/constants';

// Hôtes dont les liens médias expirent (fournisseurs de génération). Extensible.
const EXPIRING_MEDIA_HOSTS = /^(?:files-cdn\.x\.ai|(?:[\w-]+\.)?fal\.media)$/i;

// URLs média (nues OU déjà en markdown `![](...)`) : images ET vidéos.
const MEDIA_URL_G =
	/https?:\/\/[^\s<>()\]]+?\.(?:png|jpe?g|webp|gif|avif|mp4|webm|mov|m4v)(?:\?[^\s<>()\]]*)?/gi;

// Extrait les URLs de médias générés (hôtes expirables) présentes dans un message.
export const extractExpiringMediaUrls = (content: string): string[] => {
	if (!content || content.indexOf('http') === -1) return [];
	const found = content.match(MEDIA_URL_G) || [];
	const out: string[] = [];
	const seen = new Set<string>();
	for (const url of found) {
		if (seen.has(url)) continue;
		let host = '';
		try {
			host = new URL(url).hostname;
		} catch {
			continue;
		}
		if (EXPIRING_MEDIA_HOSTS.test(host)) {
			seen.add(url);
			out.push(url);
		}
	}
	return out;
};

// Range un média dans notre stockage ; renvoie l'URL locale, ou null si échec.
const persistOne = async (url: string): Promise<string | null> => {
	try {
		const res = await fetch(`${WEBUI_API_BASE_URL}/utils/media/persist`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${localStorage.token}`
			},
			body: JSON.stringify({ url })
		});
		if (!res.ok) return null;
		const data = await res.json();
		return typeof data?.url === 'string' ? data.url : null;
	} catch {
		return null;
	}
};

// Réécrit le contenu d'un message en remplaçant les URLs de médias générés expirables
// par leur URL locale stockée. Renvoie le contenu inchangé si rien à rapatrier ou si
// tous les rapatriements échouent (repli gracieux).
export const persistGeneratedMedia = async (content: string): Promise<string> => {
	const urls = extractExpiringMediaUrls(content);
	if (urls.length === 0) return content;
	let out = content;
	for (const url of urls) {
		const local = await persistOne(url);
		if (local) out = out.split(url).join(local);
	}
	return out;
};
