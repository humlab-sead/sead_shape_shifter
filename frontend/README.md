# SEAD Shape Shifter Project Editor - Frontend

Vue 3 + TypeScript + Vuetify frontend for editing Shape Shifter YAML projects.

## Technology Stack

- **Vue 3**: Progressive JavaScript framework with Composition API
- **TypeScript**: Type-safe development
- **Vite**: Fast build tool and dev server
- **Vuetify 3**: Material Design component library
- **Pinia**: Official Vue 3 state management
- **Vue Router 4**: Official routing solution
- **Axios**: HTTP client for API calls
- **VeeValidate + Zod**: Form validation

## Quick Start

### Installation

```bash
# From project root
cd frontend

# Install dependencies with pnpm (recommended)
pnpm install

# Or with npm
npm install
```

### Running the Development Server

```bash
# Start dev server (runs on http://localhost:5173)
pnpm dev

# Or from project root with make
make frontend-run
```

The frontend will automatically proxy API requests to the backend at `http://localhost:8012`.

### Building for Production

```bash
# Type check and build
pnpm build

# Preview production build
pnpm preview
```

## Project Structure

```
frontend/
├── src/
│   ├── api/                    # API client (Sprint 4.1)
│   │   ├── client.ts
│   │   ├── config-api.ts
│   │   ├── entity-api.ts
│   │   ├── validation-api.ts
│   │   └── dependency-api.ts
│   ├── components/             # Vue components
│   │   ├── entity/            # (Sprint 5-6)
│   │   ├── graph/             # (Sprint 7)
│   │   ├── config/            # (Sprint 8)
│   │   └── validation/        # (Sprint 8)
│   ├── composables/            # Reusable composition functions (Sprint 4.3)
│   │   ├── useProject.ts
│   │   ├── useEntityEditor.ts
│   │   ├── useValidation.ts
│   │   └── useDependencyGraph.ts
│   ├── stores/                 # Pinia stores (Sprint 4.2)
│   │   ├── project.ts          # Project state
│   │   ├── validation.ts      # Validation state
│   │   └── ui.ts              # UI state
│   ├── types/                  # TypeScript type definitions (Sprint 1.3)
│   │   ├── entity.ts
│   │   ├── project.ts
│   │   └── validation.ts
│   ├── views/                  # Page components
│   │   ├── HomeView.vue       # ✅ Landing page
│   │   ├── EntitiesView.vue   # Entity list/editor (Sprint 5)
│   │   ├── GraphView.vue      # Dependency graph (Sprint 7)
│   │   ├── ValidationView.vue # Validation report (Sprint 8)
│   │   └── SettingsView.vue   # Settings (Sprint 8)
│   ├── layouts/                # Layout components (Sprint 5.1)
│   │   └── DefaultLayout.vue
│   ├── plugins/
│   │   └── vuetify.ts         # ✅ Vuetify configuration
│   ├── router/
│   │   └── index.ts           # ✅ Vue Router configuration
│   ├── styles/
│   │   ├── main.scss          # ✅ Global styles
│   │   └── settings.scss      # ✅ Vuetify settings
│   ├── App.vue                # ✅ Root component
│   ├── main.ts                # ✅ Application entry point
│   └── vite-env.d.ts          # ✅ Vite type definitions
├── index.html                  # ✅ HTML entry point
├── vite.config.ts              # ✅ Vite configuration
├── tsconfig.json               # ✅ TypeScript configuration
├── package.json                # ✅ Dependencies
└── README.md
```

## Available Routes

- `/` - Home page with backend status
- `/entities` - Entity management (Sprint 5.2)
- `/validation` - Validation report (Sprint 8.2)
- `/settings` - Application settings (Sprint 8.3)

The dependency graph no longer has its own route; it lives inside the **Dependencies** tab of `/projects/:name`, so you must select a project from `/projects` and switch to that tab to see the graph.

## API Integration

The frontend communicates with the backend via a proxied API:

```typescript
// All requests to /api/* are proxied to http://localhost:8012
import axios from 'axios'

const response = await axios.get('/api/v1/health')
```

Project in `vite.config.ts`:
```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8012',
      changeOrigin: true,
    },
  },
}
```

## Vuetify Configuration

Material Design components are auto-imported. Customization in `src/plugins/vuetify.ts`:

- Light and dark themes
- Default component variants
- Material Design Icons (@mdi/font)

## Development Workflow

1. **Start both servers**:
   ```bash
   # Terminal 1: Backend
   cd backend
   make backend-run
   
   # Terminal 2: Frontend
   cd frontend
   pnpm dev
   ```

2. **Access the application**:
   - Frontend: http://localhost:5173
   - Backend API docs: http://localhost:8012/api/v1/docs

3. **Auto-reload**: Both servers auto-reload on file changes

## Code Quality

```bash
# Lint code
pnpm lint

# Format code
pnpm format

# Type check
vue-tsc --noEmit
```
