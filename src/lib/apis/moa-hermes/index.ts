import { changerDeModele, getModelesCombines } from '$lib/apis/hermes';

export type MoaSlot = { provider: string; model: string };
export type MoaConfig = {
	reference_models: MoaSlot[];
	aggregator: MoaSlot | Record<string, never>;
	enabled: boolean;
	active: boolean;
};

export const getMoaConfig = (token: string): Promise<MoaConfig> => getModelesCombines(token);
export const setMoaConfig = async (
	token: string,
	reference_models: MoaSlot[],
	aggregator: MoaSlot
): Promise<MoaConfig> => {
	const current = await getModelesCombines(token);
	return { ...current, reference_models, aggregator };
};
export const activateMoa = async (token: string): Promise<MoaConfig> => {
	await changerDeModele(token, 'default', 'moa');
	return getModelesCombines(token);
};
export const deactivateMoa = async (token: string): Promise<MoaConfig> => getModelesCombines(token);
