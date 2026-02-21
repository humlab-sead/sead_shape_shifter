import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import yamlWorker from 'monaco-yaml/yaml.worker?worker'

// Create worker factories with proper error handling
function createYamlWorker(): Worker {
  if (!yamlWorker) {
    throw new Error('YAML worker module not loaded')
  }
  return new yamlWorker()
}

function createEditorWorker(): Worker {
  if (!editorWorker) {
    throw new Error('Editor worker module not loaded')
  }
  return new editorWorker()
}

// Configure Monaco to use bundled workers (prevents CDN warnings and ensures proper worker loading)
export function configureMonacoWorkers() {
  // Ensure MonacoEnvironment is properly defined on global scope
  if (typeof self !== 'undefined') {
    self.MonacoEnvironment = {
      getWorker(_workerId: string, label: string): Worker {
        console.log(`[Monaco] Creating worker for label: ${label}`)
        
        try {
          if (label === 'yaml') {
            return createYamlWorker()
          }
          return createEditorWorker()
        } catch (error) {
          console.error(`[Monaco] Failed to create ${label} worker:`, error)
          // Always try to return editor worker as fallback
          try {
            return createEditorWorker()
          } catch (fallbackError) {
            console.error('[Monaco] Failed to create fallback editor worker:', fallbackError)
            // This should never happen, but if it does, throw to make the error visible
            throw new Error(`Cannot create Monaco worker: ${fallbackError}`)
          }
        }
      },
    }
    console.log('[Monaco] Worker environment configured')
  } else {
    console.warn('[Monaco] self is undefined, cannot configure workers')
  }
}
