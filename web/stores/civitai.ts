export const useCivitAiStore = defineStore('civitAiStore', {
	actions: {
		fetchFlowLoras(flow: Flow, token: string, limit: number = 10, nextPageUrl?: string) {
			if (!flow.lora_connect_points || Object.keys(flow.lora_connect_points).length !== 1) {
				console.debug('Flow does not have lora_connect_points or has more than one, skipping fetching loras')
				return
			}
			const { $apiFetch } = useNuxtApp()
			// @ts-ignore
			const modelType = flow.lora_connect_points[Object.keys(flow.lora_connect_points)[0]].base_model_type
			let url = `https://civitai.com/api/v1/models?query=${modelType}&types=LORA&limit=${limit}`
			if (nextPageUrl) {
				url = nextPageUrl
			}
			const proxiedUrl = `/other/proxy?target=${encodeURIComponent(url)}`
			return $apiFetch(proxiedUrl, {
				method: 'GET',
				headers: {
					Authentication: 'Bearer' + token,
					Accept: 'application/json',
				}
			})
		},
		fetchFlowLorasByHash(flow: Flow, token: string, hash: string) {
			if (!flow.lora_connect_points || Object.keys(flow.lora_connect_points).length !== 1) {
				console.debug('Flow does not have lora_connect_points or has more than one, skipping fetching loras')
				return
			}
			const { $apiFetch } = useNuxtApp()
			const url = `https://civitai.com/api/v1/model-versions/by-hash/${hash}`
			const proxiedUrl = `/other/proxy?target=${encodeURIComponent(url)}`
			return $apiFetch(proxiedUrl, {
				method: 'GET',
				headers: {
					Authentication: 'Bearer' + token,
					Accept: 'application/json',
				}
			})
		},
	}
})

export interface ModelApiItem {
	id: number
	name: string
	description: string
	allowNoCredit: boolean
	allowCommercialUse: string[]
	allowDerivatives: boolean
	allowDifferentLicense: boolean
	type: string
	minor: boolean
	poi: boolean
	nsfw: boolean
	nsfwLevel: number
	cosmetic: any
	supportsGeneration: boolean
	stats: {
		downloadCount: number
		favoriteCount: number
		thumbsUpCount: number
		thumbsDownCount: number
		commentCount: number
		ratingCount: number
		rating: number
		tippedAmountCount: number
	}
	creator: {
		username: string
		image: string
	}
	tags: string[]
	modelVersions: {
		id: number
		index: number
		name: string
		baseModel: string
		baseModelType: any
		publishedAt: string
		availability: string
		nsfwLevel: number
		description: string
		trainedWords: string[]
		stats: {
			downloadCount: number
			ratingCount: number
			rating: number
			thumbsUpCount: number
			thumbsDownCount: number
		}
		supportsGeneration: boolean
		files: {
			id: number
			sizeKB: number
			name: string
			type: string
			pickleScanResult: string
			pickleScanMessage: string
			virusScanResult: string
			virusScanMessage: any
			scannedAt: string
			metadata: {
				format: string
				size: any
				fp: any
			}
			hashes: {
				AutoV1: string
				AutoV2: string
				SHA256: string
				CRC32: string
				BLAKE3: string
				AutoV3: string
			}
			downloadUrl: string
			primary: boolean
		}[]
		images: {
			id: number
			url: string
			nsfwLevel: number
			width: number
			height: number
			hash: string
			type: string
			hasMeta: boolean
			onSite: boolean
			remixOfId: any
		}[]
		downloadUrl: string
	}[]
	currentFlowLora?: boolean
}

export interface ModelApiItems {
	items: ModelApiItem[]
	metadata: {
		nextCursor: string
		nextPage: string
	}
}
