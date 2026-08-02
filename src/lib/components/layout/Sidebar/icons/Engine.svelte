<script lang="ts">
	export let className = 'size-4';
	export let strokeWidth = '1.5';
</script>

<svg
	class={className}
	aria-hidden="true"
	xmlns="http://www.w3.org/2000/svg"
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width={strokeWidth}
	stroke-linecap="round"
	stroke-linejoin="round"
>
	<rect x="7" y="7" width="10" height="10" rx="2" />
	<path
		d="M9.5 1.75V5M14.5 1.75V5M9.5 19v3.25M14.5 19v3.25M1.75 9.5H5M1.75 14.5H5M19 9.5h3.25M19 14.5h3.25"
	/>
	<circle cx="12" cy="12" r="2.25" />
</svg>
