export function paginate(items: any[], page: number, items_per_page: number): any[] {
	const paginated = []
	const pages = Math.ceil(items.length / items_per_page)
	for (let i = 0; i < pages; i++) {
		paginated.push(items.slice(i * items_per_page, (i + 1) * items_per_page))
	}
	return paginated[page - 1]
}

export function formatBytes(bytes: number, decimals: number = 2) {
	if (bytes === 0) return '0 Bytes'

	const k = 1024
	const dm = decimals < 0 ? 0 : decimals
	const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']

	const i = Math.floor(Math.log(bytes) / Math.log(k))

	return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
}

export function findLatestChildTask(task: any, outputIndex: number = 0): TaskHistoryItem|FlowResult {
	if (task.child_tasks.length === 0) {
		return task
	}
	if (task.child_tasks.length > 1
		&& task.outputs.length > 1
		&& task.outputs[outputIndex].comfy_node_id === task.child_tasks
			.find((t: FlowResult|TaskHistoryItem|any) => t.comfy_node_id === task.outputs[outputIndex].comfy_node_id).comfy_node_id) {
		return task
	}
	return findLatestChildTask(task.child_tasks[task.child_tasks.length - 1], outputIndex)
}
