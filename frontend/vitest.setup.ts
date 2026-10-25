// jsdom omits visualViewport, which Vuetify reads when it mounts overlays.
if (!('visualViewport' in window)) {
  Object.defineProperty(window, 'visualViewport', { configurable: true, value: null })
}
