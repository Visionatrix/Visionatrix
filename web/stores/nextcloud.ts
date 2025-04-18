import type { RouteLocationNormalized } from 'vue-router'

export const useNextcloudStore = defineStore('nextcloudStore', {
	state: () => ({
		selectedFiles: {},
	}),

	actions: {
		registerListener() {
			window.addEventListener('message', (event) => {
				if (event.data.files) {
					this.handleFileSelect(event.data.files, event.data.inputParamName)
				}
			})
		},
		openNextcloudFilePicker(inputParamName: string) {
			// @ts-ignore
			this.selectedFiles[inputParamName] = null
			window.parent.postMessage({
				type: 'openNextcloudFilePicker',
				inputParamName,
			}, '*')
		},
		handleFileSelect(files: NextcloudFile[], inputParamName: string) {
			const selectedFiles = files.reduce((acc, file: NextcloudFile) => {
				// @ts-ignore
				acc[inputParamName] = file
				return acc
			}, this.selectedFiles)
			this.selectedFiles = selectedFiles
		},
		removeSelectedFile(inputParamName: string) {
			// @ts-ignore
			if (this.selectedFiles[inputParamName]) {
				// @ts-ignore
				this.selectedFiles[inputParamName] = null
			}
		},
		handleRouteChange(to: RouteLocationNormalized, from: RouteLocationNormalized) {
			console.debug('Route changed: ', from.path, '->', to.path)
			// Send target route path to the parent window
			if (to.path !== from.path) {
				window.parent.postMessage({
					type: 'routeChange',
					route: to.path,
				}, '*')
			}
		},
	},
})

export interface NextcloudFile {
	displayname: string
	id: string
	source: string
	mtime: string
	mime: string
	size: number
	permissions: number
	owner: string
	root: string
	attributes: {
		filename: string
		lastmod: string
		type: string
		etag: string
		getcontentlength: number
		getcontenttype: string
		getetag: string
		getlastmodified: string
		creationdate: string
		resourcetype: string
		'has-preview': boolean
		'mount-type': string
		'comments-unread': number
		favorite: number
		'owner-display-name': string
		'owner-id': string
		hasPreview: boolean
	}
}

export interface SelectedNextcloudFiles {
	[key: string]: NextcloudFile
}
