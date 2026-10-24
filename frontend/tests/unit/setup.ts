// Shared Vitest setup for unit tests.
// jsdom does not provide window.visualViewport, which Vuetify's overlay
// location strategies read directly. Without a stub, mounting components that
// use overlays (menus, tooltips, selects) throws "visualViewport is not
// defined" as an unhandled rejection during tests.
if (typeof globalThis.visualViewport === 'undefined') {
  const visualViewportStub = {
    angle: 0,
    height: 768,
    offsetLeft: 0,
    offsetTop: 0,
    onPageResize: null,
    onresize: null,
    onscroll: null,
    pageLeft: 0,
    pageTop: 0,
    scale: 1,
    width: 1024,
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => true,
  }
  Object.defineProperty(globalThis, 'visualViewport', {
    value: visualViewportStub,
    writable: true,
    configurable: true,
  })
}
