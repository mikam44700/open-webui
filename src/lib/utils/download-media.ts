import fileSaver from 'file-saver';
import { WEBUI_API_BASE_URL } from '$lib/constants';

const { saveAs } = fileSaver;

// Télécharge un média (image/vidéo) généré, même quand le CDN du fournisseur bloque le
// téléchargement direct (CORS). On passe par notre proxy backend (/utils/media/download)
// qui récupère le fichier côté serveur et le renvoie en pièce jointe (même origine).
// Repli : ouverture dans un onglet si le proxy échoue.
export const downloadMedia = async (url: string): Promise<void> => {
	try {
		// Média déjà rapatrié chez nous (même origine) → téléchargement direct, sans proxy.
		const isLocal = url.startsWith('/api/') || url.startsWith(`${WEBUI_API_BASE_URL}`);
		const target = isLocal
			? url
			: `${WEBUI_API_BASE_URL}/utils/media/download?url=${encodeURIComponent(url)}`;
		const res = await fetch(target, {
			headers: { Authorization: `Bearer ${localStorage.token}` }
		});
		if (!res.ok) throw new Error('proxy download failed');
		const blob = await res.blob();
		const name = (url.split('?')[0].split('/').pop() || 'media').trim() || 'media';
		saveAs(blob, name);
	} catch {
		window.open(url, '_blank');
	}
};
