/**
 * Marked inline extension: renders Hermes label badges.
 *
 * Patterns recognised (case-sensitive, at any inline position):
 *   [À décider]   → badge rouge / orange
 *   [À surveiller] → badge ambre
 *   [Pour info]   → badge bleu/gris
 *
 * The extension uses an inline tokenizer so it fires during paragraph
 * parsing, not at block level. This means it works inside prose text
 * produced by the model and doesn't interfere with fenced code blocks
 * or other block-level constructs.
 */

type BadgeVariant = 'a-decider' | 'a-surveiller' | 'pour-info';

const BADGE_PATTERNS: { pattern: RegExp; variant: BadgeVariant; label: string }[] = [
	{ pattern: /^\[À décider\]/u, variant: 'a-decider', label: 'À décider' },
	{ pattern: /^\[À surveiller\]/u, variant: 'a-surveiller', label: 'À surveiller' },
	{ pattern: /^\[Pour info\]/u, variant: 'pour-info', label: 'Pour info' }
];

// Tailwind utility classes for each variant (safe for DOMPurify — only class attrs)
const VARIANT_CLASSES: Record<BadgeVariant, string> = {
	'a-decider':
		'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 border border-red-200/60 dark:border-red-700/40',
	'a-surveiller':
		'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 border border-amber-200/60 dark:border-amber-700/40',
	'pour-info':
		'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 border border-blue-200/60 dark:border-blue-700/40'
};

function hermesBadgeTokenizer(this: any, src: string) {
	for (const { pattern, variant, label } of BADGE_PATTERNS) {
		const match = pattern.exec(src);
		if (match) {
			return {
				type: 'hermesBadge',
				raw: match[0],
				variant,
				label
			};
		}
	}
}

function hermesBadgeRenderer(token: any) {
	const classes = VARIANT_CLASSES[token.variant as BadgeVariant] ?? '';
	// The label is a static string from our own list — no user input here.
	return `<span class="${classes}">${token.label}</span>`;
}

function hermesBadgeStart(src: string): number {
	// Find the earliest occurrence of any of the three bracket labels.
	const idx = src.search(/\[À décider\]|\[À surveiller\]|\[Pour info\]/u);
	return idx >= 0 ? idx : -1;
}

export default function hermesBadgeExtension() {
	return {
		extensions: [
			{
				name: 'hermesBadge',
				level: 'inline' as const,
				start: hermesBadgeStart,
				tokenizer: hermesBadgeTokenizer,
				renderer: hermesBadgeRenderer
			}
		]
	};
}
