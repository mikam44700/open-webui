// Identité de la fiche entreprise déposée dans le coffre par l'onboarding.
//
// C'est une note GÉRÉE : le produit la réécrit à chaque rejeu de l'onboarding. Son identité tient
// à ce `lunaria-id` (frontmatter), pas à son nom de fichier ni à son dossier — le dirigeant peut
// la renommer et la ranger où il veut, le rejeu la retrouve et la met à jour sur place.
//
// Ne JAMAIS dater ce titre : un titre variable recrée un fichier par rejeu (bug des doublons
// `-2`, `-3`… corrigé le 2026-07-15). La date de mise à jour est déjà affichée par « Modifié le ».
export const COMPANY_NOTE_ID = 'fiche-entreprise';
export const COMPANY_NOTE_TITLE = 'Fiche entreprise';
