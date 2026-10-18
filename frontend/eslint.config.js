import js from '@eslint/js'
import globals from 'globals'
import pluginVue from 'eslint-plugin-vue'
import vueTsEslintConfig from '@vue/eslint-config-typescript'
import prettierConfig from '@vue/eslint-config-prettier'

export default [
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue,js,jsx}'],
  },
  {
    name: 'app/files-to-ignore',
    ignores: ['**/dist/**', '**/dist-ssr/**', '**/coverage/**', 'node_modules/**'],
  },

  js.configs.recommended,
  ...pluginVue.configs['flat/essential'],
  ...vueTsEslintConfig(),

  {
    name: 'app/browser-globals',
    files: ['src/**/*.{ts,mts,tsx,vue,js,jsx}', 'public/**/*.{js,jsx}'],
    languageOptions: {
      globals: globals.browser,
    },
  },
  {
    name: 'app/node-globals',
    files: ['*.config.{js,mjs,ts,mts}', 'tests/e2e/**/*.{ts,mts,js,jsx}'],
    languageOptions: {
      globals: globals.node,
    },
  },
  {
    name: 'app/custom-rules',
    rules: {
      'vue/multi-word-component-names': 'off',
      'vue/valid-v-slot': ['error', { allowModifiers: true }],
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          ignoreRestSiblings: true,
        },
      ],
      'no-undef': 'error',
    },
  },
  {
    name: 'app/typescript-rules',
    files: ['**/*.{ts,mts,cts,tsx,vue}'],
    rules: {
      'no-undef': 'off',
    },
  },

  prettierConfig,
]
