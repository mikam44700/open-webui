<script lang="ts">
	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';
	import { onMount } from 'svelte';

	onMount(() => {
		const perms = $user?.permissions?.workspace ?? {};

		if ($user?.role === 'admin' || perms.models) {
			goto('/workspace/agents');
		} else if (perms.knowledge || perms.prompts || perms.skills || perms.tools) {
			goto('/workspace/library');
		} else {
			goto('/');
		}
	});
</script>
