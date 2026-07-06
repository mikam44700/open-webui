<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { safeImageUrl } from '$lib/utils/safeImageUrl';
	import fileSaver from 'file-saver';
	const { saveAs } = fileSaver;

	import { settings } from '$lib/stores';
	import ImagePreview from './ImagePreview.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Download from '$lib/components/icons/Download.svelte';
	import { getContext } from 'svelte';

	export let src = '';
	export let alt = '';

	export let className = ` w-full ${($settings?.highContrastMode ?? false) ? '' : 'outline-hidden focus:outline-hidden'}`;

	export let imageClassName = 'rounded-lg';

	export let dismissible = false;
	// Affiche une icône « télécharger » au survol (images générées dans le chat).
	export let downloadable = false;
	export let onDismiss = () => {};

	const i18n = getContext('i18n');

	let _src = '';
	$: _src = safeImageUrl(src.startsWith('/') ? `${WEBUI_BASE_URL}${src}` : src);

	let showImagePreview = false;

	const downloadImage = async (e) => {
		e.stopPropagation();
		try {
			const res = await fetch(_src);
			const blob = await res.blob();
			const ext = (blob.type.split('/')[1] || 'png').split('+')[0];
			saveAs(blob, `image-${Date.now()}.${ext}`);
		} catch {
			// CORS ou réseau : repli qui laisse l'utilisateur enregistrer manuellement.
			window.open(_src, '_blank');
		}
	};
</script>

<ImagePreview bind:show={showImagePreview} src={_src} {alt} />

<div class=" relative group w-fit flex items-center">
	<button
		class={className}
		on:click={() => {
			showImagePreview = true;
		}}
		aria-label={$i18n.t('Show image preview')}
		type="button"
	>
		<img src={_src} {alt} class={imageClassName} draggable="false" data-cy="image" />
	</button>

	{#if dismissible}
		<div class=" absolute -top-1 -right-1">
			<button
				aria-label={$i18n.t('Remove image')}
				class=" bg-white text-black border border-white rounded-full group-hover:visible invisible transition"
				type="button"
				on:click={() => {
					onDismiss();
				}}
			>
				<XMark className={'size-4'} />
			</button>
		</div>
	{/if}

	{#if downloadable}
		<div class=" absolute top-2 right-2">
			<button
				aria-label={$i18n.t('Télécharger l’image')}
				title={$i18n.t('Télécharger')}
				class=" p-1.5 rounded-lg bg-black/60 text-white backdrop-blur hover:bg-black/80 opacity-0 group-hover:opacity-100 transition"
				type="button"
				on:click={downloadImage}
			>
				<Download className={'size-4'} />
			</button>
		</div>
	{/if}
</div>
