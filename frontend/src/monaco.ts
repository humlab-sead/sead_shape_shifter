import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import yamlWorker from 'monaco-yaml/yaml.worker?worker'

// Configure Monaco to use bundled workers instead of CDN
// This prevents browser tracking prevention warnings and ensures workers run properly
export function configureMonacoWorkers() {
  self.MonacoEnvironment = {
    getWorker(_: string, label: string) {
      try {
        if (label === 'yaml') {
          return new yamlWorker()
        }
        return new editorWorker()
      } catch (error) {
        console.error(`Failed to create ${label} worker:`, error)
        // Fallback to editor worker if YAML worker fails
        return new editorWorker()
      }
    },
  }
}
