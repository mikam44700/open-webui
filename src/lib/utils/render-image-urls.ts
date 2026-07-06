// Affiche les MÉDIAS (images ET vidéos) DANS le chat au lieu d'un lien cliquable.
//
// Les outils de génération (Grok Imagine, FAL…) renvoient souvent l'URL brute du média ;
// le modèle la recopie telle quelle → le chat affiche un lien, pas le média. On convertit
// ces URLs « nues » (png/jpg/webp/gif/avif ET mp4/webm/mov/m4v) en markdown `![](url)`.
// Le rendu (MarkdownInlineTokens) décide ensuite image vs lecteur vidéo selon l'extension.
//
// On ne touche PAS aux URLs déjà en markdown (image `![alt](url)` ou lien `[texte](url)`)
// ni aux autoliens `<url>` : le garde `(^|\s)` exige un blanc/début avant l'URL.

const BARE_MEDIA_URL =
	/(^|\s)(https?:\/\/[^\s<>()\]]+?\.(?:png|jpe?g|webp|gif|avif|mp4|webm|mov|m4v)(?:\?[^\s<>()\]]*)?)(?=$|[\s.,;!?)\]])/gi;

const VIDEO_EXT = /\.(?:mp4|webm|mov|m4v)(?:\?|#|$)/i;

export const isVideoUrl = (url: string): boolean => VIDEO_EXT.test(url || '');

export const renderBareImageUrls = (text: string): string => {
	if (!text || text.indexOf('http') === -1) return text;
	return text.replace(BARE_MEDIA_URL, (_m, pre, url) => `${pre}![media](${url})`);
};
