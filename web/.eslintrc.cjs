module.exports = {
	root: true,
	extends: [
		'@nuxt/eslint-config',
	],
	rules: {
		semi: ['error', 'never'],
		quotes: ['error', 'single'],
		indent: ['error', 'tab'],
		'quote-props': ['error', 'as-needed'],
		'vue/multi-word-component-names': 0,
		'vue/max-attributes-per-line': 'off',
		'vue/no-v-html': 0,
		'vue/html-indent': ['error', 'tab'],
		'vue/first-attribute-linebreak': 0,
		'vue/html-closing-bracket-newline': 0,
		'vue/singleline-html-element-content-newline': 0,
		'vue/no-mutating-props': 0,
		'vue/no-deprecated-v-bind-sync': 0,
	}
}
