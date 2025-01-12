<script lang="ts" setup>
defineProps({
	flow: {
		type: Object as () => Flow,
		required: true,
	}
})
const flowsStore = useFlowsStore()
</script>

<template>
	<div class="p-4 w-full md:w-6/12 lg:w-4/12 z-[10]">
		<UCard as="div" class="hover:shadow-md">
			<template #header>
				<div class="flex flex-grow justify-between">
					<h2 class="text-xl font-bold truncate flex items-center"
						:title="flow?.display_name">
						<UTooltip
							v-if="flow?.private || false"
							text="This flow is local, manually added">
							<UIcon
								name="i-heroicons-lock-closed"
								class="mr-2"
								:class="{
									'text-stone-500': !flow.is_supported_by_workers
								}" />
						</UTooltip>
						<UTooltip :text="flow.is_supported_by_workers ? '' : 'No workers capable of running this flow'"
							:popper="{ placement: 'top' }">
							<span :class="{
								'text-stone-500': !flow.is_supported_by_workers
							}">{{ flow?.display_name }}</span>
						</UTooltip>
					</h2>
					<UTooltip
						v-if="flowsStore.isFlowInstalled(flow?.name)"
						text="Mark flow as favorite"
						class="ml-3"
						:popper="{ placement: 'top' }"
						:open-delay="500">
						<UButton
							:icon="!flowsStore.isFlowFavorite(flow.name) ? 'i-heroicons-star' : 'i-heroicons-star-16-solid'"
							variant="outline"
							color="yellow"
							@click="flowsStore.markFlowFavorite(flow)" />
					</UTooltip>
				</div>
			</template>

			<div class="flex flex-col items-between text-sm">
				<p class="text-md text-slate-400 truncate text-ellipsis mb-2" :title="flow?.description">
					{{ flow?.description }}
				</p>
				<p class="flex flex-row flex-wrap items-center mb-2">
					<span class="flex flex-row items-center">
						<UIcon name="i-heroicons-user-16-solid" class="mr-1" />
						<b>Author:</b>&nbsp;
					</span>
					<a class="hover:underline flex flex-row items-center" :href="flow?.homepage" rel="noopener" target="_blank">
						{{ flow?.author }}
					</a>
				</p>
				<p class="flex flex-row items-center mb-2">
					<UIcon name="i-heroicons-document-text" class="mr-1" />
					<a v-if="flow?.documentation" class="hover:underline" :href="flow?.documentation" rel="noopener" target="_blank">Documentation</a>
					<span v-else>No documentation</span>
				</p>
				<p class="flex flex-row items-center mb-2">
					<UIcon name="i-heroicons-tag" class="mr-1" />
					<b>Tags:</b>&nbsp;
					<template v-if="flow?.tags.length > 0">
						<UBadge
							v-for="tag in flow?.tags"
							:key="tag"
							:label="tag"
							color="white"
							variant="solid"
							class="m-1" />
					</template>
					<template v-else>
						<UBadge label="No tags" color="white" variant="solid" class="m-1" />
					</template>
				</p>
				<p class="flex flex-row items-center">
					<UIcon name="i-mdi-help-network-outline" class="mr-1" />
					<b>Platforms:</b>&nbsp;
					<UTooltip text="Linux">
						<UIcon name="i-mdi-linux" class="mr-1" />
					</UTooltip>
					<UTooltip text="Microsoft Windows">
						<UIcon name="i-mdi-microsoft-windows" class="mr-1" />
					</UTooltip>
					<UTooltip v-if="flow.is_macos_supported" text="macOS">
						<UIcon name="i-mdi-apple" class="mr-1" />
					</UTooltip>
					<UTooltip v-if="flow?.required_memory_gb"
						class="flex flex-row items-center"
						text="Required VRAM memory (GB)">
						(<UIcon name="i-mdi-memory" class="mr-1" />
						<span>{{ flow?.required_memory_gb }} GB</span>)
					</UTooltip>
				</p>
			</div>

			<template #footer>
				<UButton
					:to="`/workflows/${flow?.name}`"
					:icon="'i-heroicons-arrow-up-right-16-solid'"
					class="flex justify-center dark:bg-slate-500 bg-slate-500 dark:hover:bg-slate-700 hover:bg-slate-700 dark:text-white">
					Open
				</UButton>
			</template>
		</UCard>
	</div>
</template>
