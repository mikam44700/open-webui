export const isBridgeDown = (err: any) =>
	err?.error?.code === 'bridge_unreachable' ||
	err?.error?.code === 'hermes_unavailable' ||
	`${err ?? ''}`.toLowerCase().includes('hermes');
