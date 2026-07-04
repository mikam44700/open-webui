// Manifeste des avatars d'agents — source unique côté front.
// 100 portraits détourés (fond transparent), servis en statique depuis
// /assets/agents/<id>.png. Utilisé à la fois par la galerie (AvatarPicker)
// et par la suggestion automatique d'avatar à la création d'un agent.
//
// Le genre n'existe pas dans le manifest.csv source : il est renseigné ici
// (déduit du prénom) UNIQUEMENT pour filtrer la galerie et proposer un avatar
// cohérent par défaut. Il n'est jamais imposé — le dirigeant choisit librement.

export type Gender = 'male' | 'female';

export type Avatar = {
	id: string; // identifiant = nom du fichier sans extension (ex. "mike")
	label: string; // prénom affiché (ex. "Mike")
	gender: Gender;
};

// Résout un identifiant d'avatar en URL statique servie par l'app.
export const avatarImage = (id: string): string => `/assets/agents/${id}.png`;

// Retrouve l'entrée de manifeste correspondant à un chemin/identifiant d'avatar.
export const avatarFromImage = (image?: string | null): Avatar | undefined => {
	if (!image) return undefined;
	const id = image.replace(/^.*\//, '').replace(/\.png.*$/i, '');
	return AVATARS.find((a) => a.id === id);
};

export const AVATARS: Avatar[] = [
	{ id: 'adam', label: 'Adam', gender: 'male' },
	{ id: 'adrien', label: 'Adrien', gender: 'male' },
	{ id: 'aicha', label: 'Aïcha', gender: 'female' },
	{ id: 'alex', label: 'Alex', gender: 'male' },
	{ id: 'alice', label: 'Alice', gender: 'female' },
	{ id: 'alma', label: 'Alma', gender: 'female' },
	{ id: 'ambre', label: 'Ambre', gender: 'female' },
	{ id: 'amelie', label: 'Amélie', gender: 'female' },
	{ id: 'amir', label: 'Amir', gender: 'male' },
	{ id: 'anais', label: 'Anaïs', gender: 'female' },
	{ id: 'antoine', label: 'Antoine', gender: 'male' },
	{ id: 'bastien', label: 'Bastien', gender: 'male' },
	{ id: 'camille', label: 'Camille', gender: 'female' },
	{ id: 'celia', label: 'Célia', gender: 'female' },
	{ id: 'chloe', label: 'Chloé', gender: 'female' },
	{ id: 'clara', label: 'Clara', gender: 'female' },
	{ id: 'diego', label: 'Diego', gender: 'male' },
	{ id: 'dorian', label: 'Dorian', gender: 'male' },
	{ id: 'elias', label: 'Elias', gender: 'male' },
	{ id: 'elise', label: 'Élise', gender: 'female' },
	{ id: 'emma', label: 'Emma', gender: 'female' },
	{ id: 'enzo', label: 'Enzo', gender: 'male' },
	{ id: 'erik', label: 'Erik', gender: 'male' },
	{ id: 'ethan', label: 'Ethan', gender: 'male' },
	{ id: 'eva', label: 'Eva', gender: 'female' },
	{ id: 'fatou', label: 'Fatou', gender: 'female' },
	{ id: 'gabriel', label: 'Gabriel', gender: 'male' },
	{ id: 'hana', label: 'Hana', gender: 'female' },
	{ id: 'hugo', label: 'Hugo', gender: 'male' },
	{ id: 'ilyes', label: 'Ilyès', gender: 'male' },
	{ id: 'imani', label: 'Imani', gender: 'female' },
	{ id: 'ines', label: 'Inès', gender: 'female' },
	{ id: 'ingrid', label: 'Ingrid', gender: 'female' },
	{ id: 'iris', label: 'Iris', gender: 'female' },
	{ id: 'issa', label: 'Issa', gender: 'male' },
	{ id: 'jade', label: 'Jade', gender: 'female' },
	{ id: 'jeanne', label: 'Jeanne', gender: 'female' },
	{ id: 'jules', label: 'Jules', gender: 'male' },
	{ id: 'julie', label: 'Julie', gender: 'female' },
	{ id: 'kamel', label: 'Kamel', gender: 'male' },
	{ id: 'karim', label: 'Karim', gender: 'male' },
	{ id: 'kenzo', label: 'Kenzo', gender: 'male' },
	{ id: 'kiara', label: 'Kiara', gender: 'female' },
	{ id: 'leila', label: 'Leïla', gender: 'female' },
	{ id: 'lena', label: 'Léna', gender: 'female' },
	{ id: 'leo', label: 'Léo', gender: 'male' },
	{ id: 'lila', label: 'Lila', gender: 'female' },
	{ id: 'lina', label: 'Lina', gender: 'female' },
	{ id: 'linae', label: 'Linaé', gender: 'female' },
	{ id: 'liv', label: 'Liv', gender: 'female' },
	{ id: 'loan', label: 'Loan', gender: 'male' },
	{ id: 'louise', label: 'Louise', gender: 'female' },
	{ id: 'lucas', label: 'Lucas', gender: 'male' },
	{ id: 'maelle', label: 'Maëlle', gender: 'female' },
	{ id: 'maeva', label: 'Maéva', gender: 'female' },
	{ id: 'malo', label: 'Malo', gender: 'male' },
	{ id: 'manon', label: 'Manon', gender: 'female' },
	{ id: 'martin', label: 'Martin', gender: 'male' },
	{ id: 'matias', label: 'Matias', gender: 'male' },
	{ id: 'maxime', label: 'Maxime', gender: 'male' },
	{ id: 'maya', label: 'Maya', gender: 'female' },
	{ id: 'mike', label: 'Mike', gender: 'male' },
	{ id: 'milan', label: 'Milan', gender: 'male' },
	{ id: 'mina', label: 'Mina', gender: 'female' },
	{ id: 'nadia', label: 'Nadia', gender: 'female' },
	{ id: 'nathan', label: 'Nathan', gender: 'male' },
	{ id: 'nicolas', label: 'Nicolas', gender: 'male' },
	{ id: 'nils', label: 'Nils', gender: 'male' },
	{ id: 'noah', label: 'Noah', gender: 'male' },
	{ id: 'noemie', label: 'Noémie', gender: 'female' },
	{ id: 'nora', label: 'Nora', gender: 'female' },
	{ id: 'nour', label: 'Nour', gender: 'female' },
	{ id: 'oceane', label: 'Océane', gender: 'female' },
	{ id: 'omar', label: 'Omar', gender: 'male' },
	{ id: 'paul', label: 'Paul', gender: 'male' },
	{ id: 'pauline', label: 'Pauline', gender: 'female' },
	{ id: 'quentin', label: 'Quentin', gender: 'male' },
	{ id: 'rafael', label: 'Rafael', gender: 'male' },
	{ id: 'raphael', label: 'Raphaël', gender: 'male' },
	{ id: 'rayan', label: 'Rayan', gender: 'male' },
	{ id: 'remi', label: 'Rémi', gender: 'male' },
	{ id: 'robin', label: 'Robin', gender: 'male' },
	{ id: 'roxane', label: 'Roxane', gender: 'female' },
	{ id: 'sacha', label: 'Sacha', gender: 'male' },
	{ id: 'salome', label: 'Salomé', gender: 'female' },
	{ id: 'samir', label: 'Samir', gender: 'male' },
	{ id: 'samy', label: 'Samy', gender: 'male' },
	{ id: 'sanaa', label: 'Sanaa', gender: 'female' },
	{ id: 'sarah', label: 'Sarah', gender: 'female' },
	{ id: 'selma', label: 'Selma', gender: 'female' },
	{ id: 'simon', label: 'Simon', gender: 'male' },
	{ id: 'sofia', label: 'Sofia', gender: 'female' },
	{ id: 'tao', label: 'Tao', gender: 'male' },
	{ id: 'theo', label: 'Théo', gender: 'male' },
	{ id: 'tom', label: 'Tom', gender: 'male' },
	{ id: 'victor', label: 'Victor', gender: 'male' },
	{ id: 'violette', label: 'Violette', gender: 'female' },
	{ id: 'yannis', label: 'Yannis', gender: 'male' },
	{ id: 'yasmine', label: 'Yasmine', gender: 'female' },
	{ id: 'zoe', label: 'Zoé', gender: 'female' }
];

// Hash déterministe et stable d'une chaîne → entier positif.
// Même graine → même résultat (l'avatar suggéré ne « saute » pas au re-rendu).
const hashString = (s: string): number => {
	let h = 0;
	for (let i = 0; i < s.length; i++) {
		h = (h * 31 + s.charCodeAt(i)) | 0;
	}
	return Math.abs(h);
};

// Suggère un avatar cohérent et STABLE pour un agent (retourne un identifiant).
// Filtre par genre si fourni ; sinon pioche dans tout le catalogue.
export const suggestAvatar = (seed: string, gender?: Gender | null): string => {
	const pool = gender ? AVATARS.filter((a) => a.gender === gender) : AVATARS;
	const list = pool.length ? pool : AVATARS;
	return list[hashString(seed || 'agent') % list.length].id;
};
