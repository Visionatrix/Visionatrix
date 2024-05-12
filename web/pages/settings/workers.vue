<script setup lang="ts">
const workersStore = useWorkersStore()

const links = [
	{
		label: 'Settings',
		icon: 'i-heroicons-cog-6-tooth-20-solid',
		to: '/settings',
	},
	{
		label: 'Workers information',
		icon: 'i-heroicons-chart-bar-16-solid',
		to: '/settings/workers',
	},
]
</script>

<template>
	<AppContainer class="lg:h-dvh">
		<div class="flex flex-col md:flex-row">
			<UVerticalNavigation :links="links" />
			<div class="content px-5 w-full">
				<h2 class="my-3 text-xl">Workers</h2>
				<div class="list w-full">
					<UAlert
						v-for="worker in workersStore.$state.workers"
						:key="worker.id"
						class="worker mb-3 w-full"
						:title="worker.device_name"
						:description="worker" />
				</div>
			</div>
		</div>
	</AppContainer>
</template>