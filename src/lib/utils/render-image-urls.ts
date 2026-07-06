// Affiche les images DANS le chat au lieu d'un lien cliquable.
//
// Les outils de génération d'image (Grok Imagine, FAL…) renvoient souvent l'URL brute
// de l'image ; le modèle la recopie telle quelle → le chat affiche un lien, pas l'image.
// On convertit ces URLs « nues » (png/jpg/webp/gif/avif) en markdown image `![](url)`
// pour qu'elles s'affichent directement. Robuste : ne dépend pas du bon vouloir du modèle.
//
// On ne touche PAS aux URLs déjà en markdown (image `![alt](url)` ou lien `[texte](url)`)
// ni aux autoliens `<url>` : le garde `(^|\s)` exige un blanc/début avant l'URL, donc une
// URL précédée de `(` ou `<` n'est jamais réécrite.

const BARE_IMAGE_URL =
	/(^|\s)(https?:\/\/[^\s<>()\]]+?\.(?:png|jpe?g|webp|gif|avif)(?:\?[^\s<>()\]]*)?)(?=$|[\s.,;!?)\]])/gi;

export const renderBareImageUrls = (text: string): string => {
	if (!text || text.indexOf('http') === -1) return text;
	return text.replace(BARE_IMAGE_URL, (_m, pre, url) => `${pre}![image](${url})`);
};
