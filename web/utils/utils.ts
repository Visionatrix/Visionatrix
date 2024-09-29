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

export function findLatestChildTask(task: any, outputIndex: number = 0, parentNodeId: number|null = null): TaskHistoryItem|FlowResult {
	if (task.child_tasks.length === 0) {
		return task
	}
	if (task.child_tasks.length === 1) {
		return findLatestChildTask(task.child_tasks[0], outputIndex, parentNodeId)
	}

	const childBranchIndex = task.child_tasks.findIndex((t: FlowResult|TaskHistoryItem|any) => t.parent_task_node_id === parentNodeId)
	if (childBranchIndex !== -1) {
		return findLatestChildTask(task.child_tasks[childBranchIndex], outputIndex, parentNodeId)
	}
	// If still not found, current task is the latest
	return task
}

export function hasChildTaskByParentTaskNodeId(task: FlowResult|TaskHistoryItem, outputIndex: number, parentNodeId: number): boolean {
	if (Number(task.parent_task_node_id) === Number(parentNodeId)) {
		return true
	}
	if (task.child_tasks.length === 0) {
		return false
	}
	return task.child_tasks.some((t: FlowResult|TaskHistoryItem|any) => hasChildTaskByParentTaskNodeId(t, outputIndex, parentNodeId))
}

export function isEnglish(inputString: string): boolean {
	const englishLetters = new Set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')

	// Split the input string into words
	const words = inputString.trim().split(/\s+/)
	if (words.length === 0) {
		return true // Return true if the string is empty or only contains whitespace
	}

	let englishWordCount = 0

	for (const word of words) {
		// Remove non-alphabetic characters from the word
		const cleanedWord = word.split('').filter(char => /^[a-zA-Z]$/.test(char)).join('')

		// Check if all characters in the cleaned word are English letters and if the word is non-empty
		if (cleanedWord && [...cleanedWord].every(char => englishLetters.has(char))) {
			englishWordCount++
		}
	}

	// Return true if more than 90% of the words are English
	return englishWordCount / words.length > 0.9
}
