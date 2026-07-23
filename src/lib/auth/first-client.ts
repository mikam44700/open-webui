type PublicAuthConfig = {
	onboarding?: boolean;
};

export const isFirstClientSetup = (authConfig: PublicAuthConfig | null | undefined): boolean =>
	authConfig?.onboarding === true;

export const destinationAfterSignup = (
	firstClientSetup: boolean,
	requestedRedirect: string | null
): string | null => (firstClientSetup ? '/onboarding' : requestedRedirect);
