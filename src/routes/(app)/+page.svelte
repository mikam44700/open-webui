<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';

	import Chat from '$lib/components/chat/Chat.svelte';
	import { DONE_KEY, SKIP_ONCE_KEY } from '$lib/onboarding-agentos/logic';
	import { page } from '$app/stores';

	onMount(() => {
		if ($page.url.searchParams.get('error')) {
			toast.error($page.url.searchParams.get('error') || 'An unknown error occurred.');
		}
		try {
			if (sessionStorage.getItem(SKIP_ONCE_KEY) === '1') {
				sessionStorage.removeItem(SKIP_ONCE_KEY);
				return;
			}
			if (localStorage.getItem(DONE_KEY) !== '1') {
				goto('/onboarding');
			}
		} catch {
			// Le chat reste accessible si le stockage local est indisponible.
		}
	});
</script>

<Chat />
