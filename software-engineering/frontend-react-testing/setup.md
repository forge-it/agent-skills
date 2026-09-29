# React Testing — Green-Field Setup (commit 1)

Companion to `SKILL.md` in this folder. Run these steps once when bootstrapping a React 19 project; the conventions in `SKILL.md` cite them by number and assume the files they create.

### Step 1 — Install

```bash
npm install -D vitest @vitest/coverage-v8 happy-dom jsdom \
  @testing-library/react @testing-library/dom @testing-library/jest-dom \
  @testing-library/user-event @types/react-dom msw axe-core
npm install -D @playwright/test && npx playwright install
```

`@testing-library/dom` is a **required peer dependency** of `@testing-library/react` 16+ and `jest-dom` 7+ — it is no longer bundled, so install it explicitly. `@types/react-dom` is also required for TypeScript. MSW 3 is ESM-only and requires Node 22.12+ and TypeScript 5.9+.

### Step 2 — Configure Vitest in `vite.config.ts`

Use the **single** `vite.config.ts`, not a separate `vitest.config.ts`. A separate file makes Vitest ignore `vite.config.ts` entirely, which silently drops the React Compiler from the test build — and then the suite no longer tests what ships. See Convention 15.

```ts
/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import react, { reactCompilerPreset } from '@vitejs/plugin-react'
import babel from '@rolldown/plugin-babel'

export default defineConfig({
  plugins: [
    tanstackRouter({ target: 'react', autoCodeSplitting: true }),
    react(),
    babel({ presets: [reactCompilerPreset()] }),
  ],
  test: {
    // Explicit imports of describe/it/expect — see the cleanup note in Step 3.
    globals: false,
    css: false,
    // `exclude` is inherited by every project below and CONCATENATED into its
    // own, so these four apply everywhere and must not be repeated.
    exclude: ['**/node_modules/**', '**/dist/**', 'e2e/**', '**/*.spec.ts'],
    // Deliberately NO root `include`. Inherited arrays concatenate, so a root
    // include would be merged into each project's include and widen it — the
    // a11y project would end up claiming every *.test.tsx file as well. Each
    // project owns its include instead.

    // Two projects — SKILL.md's "The stack" spells out the happy-dom / jsdom
    // trade. `projects` replaced `workspace`, which Vitest 4 removed.
    projects: [
      {
        extends: true, // the default since Vitest 5; explicit so the merge is visible
        test: {
          name: 'unit',
          environment: 'happy-dom',
          include: ['src/**/*.test.{ts,tsx}'],
          // Concatenated onto the root exclude, not replacing it.
          exclude: ['src/**/*.a11y.test.{ts,tsx}'],
          setupFiles: ['./src/test/setup.ts', './src/test/setup-msw.ts'],
        },
      },
      {
        extends: true,
        test: {
          name: 'a11y',
          // jsdom on purpose: axe breaks on happy-dom's Node.prototype.isConnected.
          environment: 'jsdom',
          // Forces Node module resolution so `msw/node` does not resolve MSW's
          // browser build. Step 4's smoke test proves it took effect.
          environmentOptions: { jsdom: { customExportConditions: [''] } },
          include: ['src/**/*.a11y.test.{ts,tsx}'],
          setupFiles: [
            './src/test/setup.ts',
            './src/test/setup-msw.ts',
            // The five APIs jsdom lacks and happy-dom ships. Loaded only here,
            // so the unit project keeps happy-dom's real implementations
            // instead of no-op stubs.
            './src/test/setup-jsdom-stubs.ts',
            './src/test/accessibility.ts',
          ],
        },
      },
    ],

    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'lcov'],
      reportOnFailure: true,
      // Vitest 4 removed `coverage.all`. Without an explicit include, files no
      // test imported vanish from the report instead of showing as 0%.
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/routeTree.gen.ts',
        'src/main.tsx',
        'src/test/**',
        'src/**/*.test.{ts,tsx}',
        'src/**/types/**',
        'src/**/*.d.ts',
        'src/**/index.ts',
      ],
    },
  },
})
```

**The `include`/`exclude` arithmetic above is exact, and getting it wrong fails silently.** Projects extend the root config (the default since Vitest 5; `extends: true` spells it out), and Vitest merges it into each project through Vite's `mergeConfig`, which **concatenates** arrays rather than replacing them. So a root-level `include` does not get narrowed by a project's own `include` — the two are unioned, and the `a11y` project would claim every `*.test.tsx` file in addition to its own. The symptom is not an error: your whole component suite quietly runs a second time on jsdom, with stubs shadowing real APIs and the axe matcher loaded, roughly doubling suite time while defeating the split. Keep `include` out of the root, give each project its own, and let the root `exclude` be inherited rather than repeated. Verify with `vitest list --filesOnly`: each file must appear under exactly one project name.

**Do not use `@vitejs/plugin-react`'s `babel` option to wire the compiler** — plugin-react 6.0.0 removed it. `react({ babel: { plugins: [['babel-plugin-react-compiler', {}]] } })` is the form in nearly every tutorial and it no longer works; the current form is the `reactCompilerPreset` + `@rolldown/plugin-babel` pairing above.

### Step 3 — Global setup file (`src/test/setup.ts`)

```ts
import '@testing-library/jest-dom/vitest'

import { cleanup, configure } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

configure({
  // Render every test tree inside <StrictMode>. RTL default: false. See Convention 15.
  reactStrictMode: true,
  asyncUtilTimeout: 2_000,
  // Throws when a weaker query was used where a stronger one would work —
  // mechanical enforcement of Convention 2's priority order.
  throwSuggestions: true,
})

// REQUIRED: with `globals: false`, RTL cannot register its own afterEach, so
// auto-cleanup does not run. Skipping this produces the classic symptom where
// the first test passes and the second finds two matching elements.
afterEach(() => {
  cleanup()
})

// Route every `create` and `createStore` import from 'zustand' through the
// reset harness (Step 5). Automocking intercepts both entry points.
vi.mock('zustand')
```

**No browser-API stubs live here.** happy-dom implements `matchMedia`, `ResizeObserver`, `IntersectionObserver`, `showModal()`, and `scrollIntoView` natively, and stubbing over a real implementation would make the unit project test a no-op instead of the behavior. jsdom lacks all five, so the stubs load **only** in the accessibility project:

```ts
// src/test/setup-jsdom-stubs.ts — loaded by the `a11y` project only.
import { beforeEach, vi } from 'vitest'

class ResizeObserverStub implements ResizeObserver {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
}

class IntersectionObserverStub implements IntersectionObserver {
  readonly root: Element | null = null
  readonly rootMargin: string = '0px'
  readonly thresholds: readonly number[] = [0]
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
  takeRecords(): IntersectionObserverEntry[] {
    return []
  }
}

const createMatchMediaStub = (matches: boolean) => (query: string): MediaQueryList => ({
  matches,
  media: query,
  onchange: null,
  addEventListener: () => {},
  removeEventListener: () => {},
  addListener: () => {},
  removeListener: () => {},
  dispatchEvent: () => false,
})

beforeEach(() => {
  vi.stubGlobal('ResizeObserver', ResizeObserverStub)
  vi.stubGlobal('IntersectionObserver', IntersectionObserverStub)
  vi.stubGlobal('matchMedia', createMatchMediaStub(false))
  // jsdom has no layout engine.
  Element.prototype.scrollIntoView = () => {}
  // jsdom does not implement the dialog element's methods; without these a
  // component that opens a <dialog> throws on construction rather than failing
  // an assertion, which is a confusing way to discover the gap.
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.open = true
  }
  HTMLDialogElement.prototype.close = function close() {
    this.open = false
  }
})
```

All five APIs named above are stubbed here — leave none out. A missing stub does not produce a clear failure; it throws during render, so the accessibility test reports a crash instead of the violation it was written to catch.

If a component under test needs one of those five to do something real, that is a signal the test belongs in the unit project on happy-dom, where the API is genuinely implemented.

**`reactStrictMode` and `throwSuggestions` are house decisions, not industry defaults.** RTL ships both **off**, and neither RTL nor react.dev recommends enabling them in tests — the StrictMode docs never mention tests at all, and `throwSuggestions` is marked experimental. They are on here because both are one-line, once, at commit 1: StrictMode is the only mechanism that mechanically catches missing effect cleanup, and `throwSuggestions` turns Convention 2's query priority from a review comment into a red test. On an existing codebase both will be noisy; that is an argument for turning them on before there is anything to be noisy about, not for leaving them off.

Three traps this file avoids:

- **`import '@testing-library/jest-dom'` without `/vitest` is the Jest form** and silently fails to register the matchers under Vitest.
- **Never set `IS_REACT_ACT_ENVIRONMENT` yourself.** RTL sets it. Hand-setting it is a 2022-era snippet.
- **Never enable fake timers globally here.** They break `user-event`'s internal delays and `waitFor` polling. Enable them per test, in the smallest scope, and always restore (Convention 17).

Keep this file to test-infrastructure imports only. Vitest will not mock a module that a setup file already imported, so if `setup.ts` transitively imports app code that imports `zustand`, the Step 5 harness stops working.

### Step 4 — MSW server (`src/test/msw/` + `src/test/setup-msw.ts`)

```ts
// src/test/msw/handlers/backups.handlers.ts
import { http, HttpResponse, type HttpResponseResolver } from 'msw'
import { BACKUPS_API_PATH } from '@/features/backups/api/backupApi'
import { BackupStatus } from '@/features/backups/constants'
import type { Backup } from '@/features/backups/types/backup'
import { buildBackup } from '@/test/factories/backup.factory'

interface BackupIdParams {
  readonly backupId: string
}

interface BackupListResponse {
  readonly items: readonly Backup[]
  readonly total: number
}

export const backupHandlers = [
  // The third generic is the response body. Omit it and MSW does not type-check
  // HttpResponse.json() at all — always supply it.
  http.get<never, never, BackupListResponse>(BACKUPS_API_PATH, () => {
    const items = [buildBackup({ status: BackupStatus.Active })]
    return HttpResponse.json({ items, total: items.length })
  }),

  // Declaring your own params interface gives `string`, not
  // `string | readonly string[] | undefined` as MSW's own PathParams would.
  http.get<BackupIdParams, never, Backup>(`${BACKUPS_API_PATH}/:backupId`, ({ params }) =>
    HttpResponse.json(buildBackup({ id: params.backupId })),
  ),
]

export const serverErrorResolver: HttpResponseResolver<never, never, null> = () =>
  new HttpResponse(null, { status: 500 })
```

```ts
// src/test/msw/server.ts
import { setupServer } from 'msw/node'
import { handlers } from './handlers'

export const server = setupServer(...handlers)
```

```ts
// src/test/setup-msw.ts
import { afterAll, afterEach, aroundEach, beforeAll } from 'vitest'
import { server } from './msw/server'

beforeAll(() => {
  // An unmocked request is a test failure, not a silent real network call.
  // MSW 3 name; MSW 2 called this option `onUnhandledRequest`.
  server.listen({ onUnhandledFrame: 'error' })
})

// Scopes every server.use() to the test that made it, even under test.concurrent.
// `aroundEach` is a Vitest 4 addition; no older material mentions it.
aroundEach((runTest) => server.boundary(runTest)())

afterEach(() => {
  server.resetHandlers()
})

afterAll(() => {
  server.close()
})
```

MSW intercepts by patching `globalThis.fetch`, so there is no polyfill to install — `whatwg-fetch`, `cross-fetch`, and `undici` instructions are v1-era and now wrong. `setupServer()` remains the Node entry point in MSW 3; `defineNetwork` is still behind `msw/experimental`. Handlers importing app modules (the API-path constant, the status enum object) is fine: `setup.ts` has already registered the zustand mock by the time `setup-msw.ts` loads. `setup.ts` itself stays free of app imports (Step 3).

**Write this smoke test at commit 1, in both projects, and never delete it.** MSW resolving its browser build instead of `msw/node` is the single most common MSW-under-Vitest failure, and it fails *silently* — tests start hitting the real network or failing for unrelated-looking reasons. Two things make it worth a permanent test rather than a config comment: there are open reports of Vite 6+ ignoring `customExportConditions` entirely, and that option is **jsdom-specific**, so it does nothing for the happy-dom project. Whether happy-dom misresolves the same way is not something to assume in either direction — this test is how you find out, in both environments.

```ts
// src/test/msw/assertInterception.ts — one assertion, two callers
import { http, HttpResponse } from 'msw'
import { expect } from 'vitest'
import { server } from './server'

export async function assertMswInterceptsFetch(): Promise<void> {
  server.use(http.get('/api/interception-probe', () => HttpResponse.json({ intercepted: true })))

  const response = await fetch('/api/interception-probe')

  expect(await response.json()).toEqual({ intercepted: true })
}
```

```ts
// src/test/msw/interception.test.ts        → runs on happy-dom (`unit`)
import { it } from 'vitest'
import { assertMswInterceptsFetch } from './assertInterception'

it('intercepts fetch through msw/node under happy-dom', assertMswInterceptsFetch)
```

```ts
// src/test/msw/interception.a11y.test.ts   → runs on jsdom (`a11y`)
import { it } from 'vitest'
import { assertMswInterceptsFetch } from './assertInterception'

it('intercepts fetch through msw/node under jsdom', assertMswInterceptsFetch)
```

If the jsdom one fails, `customExportConditions` was ignored. If the happy-dom one fails, force Node resolution for the whole test build with `resolve: { conditions: ['node'] }` — that is the fix that covers both projects. A per-file `// @vitest-environment jsdom` docblock is not a substitute: it changes only that file's environment, leaving every other file in the `unit` project misresolving.

### Step 5 — Zustand reset harness (`__mocks__/zustand.ts`)

Every module-level store persists across tests in the same file. This harness registers a reset for each store as it is created and runs them all after each test, so no store can be forgotten. It is the official Zustand pattern, typed for `strictTypeChecked`.

```ts
// __mocks__/zustand.ts — at the project root (Vitest's `root`), NOT under src/.
// Vitest resolves a dependency's mock from `<root>/__mocks__/`; a copy under
// src/ is never loaded, and every store then leaks across tests in silence.
import { act } from '@testing-library/react'
import { afterEach, vi } from 'vitest'
import type * as ZustandExports from 'zustand'

export * from 'zustand'

const { create: actualCreate, createStore: actualCreateStore } =
  await vi.importActual<typeof ZustandExports>('zustand')

const storeResetFunctions = new Set<() => void>()

const registerReset = <Store extends { getInitialState: () => unknown; setState: (state: never, replace: true) => void }>(
  store: Store,
): Store => {
  const initialState = store.getInitialState() as never
  // `true` replaces rather than merges, so keys added during a test do not survive.
  storeResetFunctions.add(() => store.setState(initialState, true))
  return store
}

// Both `create` and `createStore` have a curried form (`create<T>()(creator)`), so
// each wrapper must handle "called with a creator" and "called with nothing".
export const create = (<StoreState>(
  stateCreator?: ZustandExports.StateCreator<StoreState>,
) => {
  const wrapped = (creator: ZustandExports.StateCreator<StoreState>) =>
    registerReset(actualCreate(creator))
  return typeof stateCreator === 'function' ? wrapped(stateCreator) : wrapped
}) as typeof ZustandExports.create

export const createStore = (<StoreState>(
  stateCreator?: ZustandExports.StateCreator<StoreState>,
) => {
  const wrapped = (creator: ZustandExports.StateCreator<StoreState>) =>
    registerReset(actualCreateStore(creator))
  return typeof stateCreator === 'function' ? wrapped(stateCreator) : wrapped
}) as typeof ZustandExports.createStore

afterEach(() => {
  act(() => {
    for (const resetStore of storeResetFunctions) {
      resetStore()
    }
  })
})
```

Two gaps to respect. The harness only wraps the `zustand` entry point, so **every store must be created via `create` or `createStore` imported from `'zustand'`** — a store built from `zustand/vanilla`, or from any other specifier, is never registered and will leak. (Wrapping both entry points is why Convention 6 can recommend per-instance `createStore` stores without opening a leak.) And `persist`-backed stores also need `localStorage.clear()` in the same `afterEach`.

### Step 6 — Provider harnesses (`src/test/providers.tsx`)

```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, type RenderOptions, type RenderResult } from '@testing-library/react'
import type { JSX, ReactElement, ReactNode } from 'react'

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      // The default is 3 retries with backoff, which makes every error-path test time out.
      queries: { retry: false, staleTime: 0 },
      mutations: { retry: false },
    },
  })
}

interface RenderWithProvidersOptions extends Omit<RenderOptions, 'wrapper'> {
  readonly queryClient?: QueryClient
}

export interface RenderWithProvidersResult extends RenderResult {
  readonly queryClient: QueryClient
}

export function renderWithProviders(
  element: ReactElement,
  { queryClient = createTestQueryClient(), ...renderOptions }: RenderWithProvidersOptions = {},
): RenderWithProvidersResult {
  function Providers({ children }: { readonly children: ReactNode }): JSX.Element {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }

  return { ...render(element, { wrapper: Providers, ...renderOptions }), queryClient }
}
```

**Do not** follow RTL's documented `export * from '@testing-library/react'` re-export trick. A barrel that shadows `render` hides which `render` a test is using. Export `renderWithProviders` under its own name and let tests import `screen`, `within`, and `act` from `@testing-library/react` directly.

Two `defaultOptions` cargo-cults to avoid: **`gcTime: Infinity`** is a Jest open-handle workaround and buys nothing under Vitest with a fresh client, and **`logger`** was removed in Query v5 — there is nothing to silence, because Query stopped logging query errors to the console in v4.

### Step 7 — Scripts (`package.json`)

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "test:e2e": "playwright test"
  }
}
```
