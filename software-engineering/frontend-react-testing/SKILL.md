---
name: frontend-react-testing
description: Opinionated testing standard for React 19. Use when writing, reviewing, or setting up tests for React components, custom hooks, Zustand stores, TanStack Query data, routes, or end-to-end flows — choosing test tooling, mocking an API, deciding what to assert, or organizing test files. Covers Vitest, React Testing Library, MSW network mocking, axe accessibility checks, and Playwright, plus the behavior-first unit/component/E2E pyramid for green-field projects.
vibe: Tests that survive refactors — behavior in, implementation out.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.1"
---

# React Testing — Opinionated Standard

This skill marks **the** testing standard for a new React 19 project. It is opinionated on purpose: it names one best-in-class tool per job and one way to use it, so that every test in the codebase reads the same and survives refactors. Existing projects may not comply — that is fine; this is the bar a green-field project starts from at commit 1.

**Core principle: test what a component does, not how it does it.** A test that asserts on internal state, render counts, referential identity, CSS class names, or child-component internals breaks every time you refactor without catching a single real regression. A test that asserts on rendered output, callback props, and user-visible behavior keeps passing through refactors and fails only when behavior actually breaks. Every convention below serves that one principle.

This is the React sibling of `frontend-vue-testing`; Conventions 1–12 cover the same concerns under the same numbers, Conventions 13–17 are React-specific. It assumes the project structure and component design from `frontend-react-development` and `frontend-react-code-style` (feature folders, container/presenter split, props-down/callbacks-up, hooks for logic) — that design is what makes components testable in the first place.

## The stack

One tool per job. Do not introduce alternatives without a deliberate decision.

| Job | Tool | Why this one |
|-----|------|--------------|
| Test runner | **Vitest** | Shares the Vite transform pipeline — no separate Babel/transform config, and the React Compiler applies to tests exactly as it does to the app. Jest is legacy for new React work. |
| Component rendering + queries | **@testing-library/react** | Pushes you toward user-facing queries (role/label/text) and away from implementation details. `renderHook` ships here too. |
| DOM environment | **happy-dom** for the bulk, **jsdom** for accessibility tests | happy-dom is roughly twice as fast and natively implements the APIs a React suite actually reaches for. axe does not work reliably in it, so accessibility tests run in a second Vitest project on jsdom. Two projects, one line of config each — see the trade below. |
| User interaction | **@testing-library/user-event** | Produces the real event sequence (pointer, focus, key) instead of one synthetic event. |
| Network mocking | **MSW** (Mock Service Worker) | Mocks at the network boundary, so the same handlers serve unit, component, and E2E tests. |
| Assertion matchers | **@testing-library/jest-dom** | `toBeInTheDocument`, `toBeDisabled`, `toHaveAccessibleName` — reads like behavior. |
| Server state in tests | **@tanstack/react-query** + a fresh `QueryClient` per test | The cache is the source of truth; a fresh client is what keeps tests isolated. |
| Client state in tests | **zustand** + a global store-reset harness | Module-level stores leak across tests unless reset mechanically. |
| Accessibility | **axe-core** directly, with a small typed matcher | First-party from Deque, ships its own types, no `@types/*` and no Jest dependencies. |
| End-to-end | **Playwright** | Current best-in-class browser automation; fast, reliable, parallel. |
| Coverage | **@vitest/coverage-v8** | Native, no instrumentation step, and accurate since Vitest 3.2's AST remapping. |

> **Do not use `jest-axe` or `vitest-axe`.** `vitest-axe`'s only stable release is 0.1.0 from October 2022 and it is effectively unmaintained. `jest-axe` is maintained but ships **no TypeScript types**; the only types available are `@types/jest-axe`, which pins `axe-core@3.x` against a 4.x runtime and drags `@types/jest` into a Vitest project, where the two `expect` globals collide. Both are recommended by most 2023–2025 material. Convention 16 replaces them with ~20 lines you own.

> **Why happy-dom, and what it costs.** happy-dom benchmarks roughly **twice as fast**, and it natively implements five APIs jsdom 30 does *not* — `matchMedia`, `ResizeObserver`, `IntersectionObserver`, `showModal()`, `scrollIntoView` — so the popular "jsdom is more complete" line is true of the DOM spec broadly and false of the surface a React suite touches. Under jsdom every one of those five needs a hand-written stub, and a stub is a lie your tests believe.
>
> The cost is real and you must know it: **happy-dom's accessible-name computation is untested** — not proven worse than jsdom's, just unmeasured — and Convention 2 makes `getByRole` the primary query for the whole codebase. Two things contain that risk. First, accessibility assertions run on jsdom in their own project (Convention 16), because axe is documented to break on happy-dom's `Node.prototype.isConnected`. Second, `eslint-plugin-jsx-a11y` and the Playwright axe scan catch name/role defects that neither environment's query layer would. If a `getByRole` query ever behaves differently from the browser, that is a bug worth reporting upstream and a reason to run that one file on jsdom — not a reason to move the whole suite. Note the two mechanisms are not interchangeable: a `// @vitest-environment jsdom` docblock swaps the environment **for that file inside its own project**, so it keeps the `unit` project's setup files and does *not* pick up the jsdom stubs or the axe matcher. Renaming to `*.a11y.test.tsx` is what actually moves a file into the `a11y` project. Use the docblock for a one-off environment quirk, the rename when the file needs the a11y harness.
>
> jsdom stays installed for the accessibility project, so its patch-pinned `engines` (`^22.22.2 || ^24.15.0 || >=26.0.0`) still set the repository's Node floor — an easy `EBADENGINE` trap in CI.

> **Vitest Browser Mode is not the default here.** It is stable as of Vitest 4 and it is not slower — it measurably beats a simulated environment on larger suites, because its startup cost is fixed rather than per-file. Keep it out of the default tier anyway: it needs Playwright binaries in CI, it has a documented cluster of determinism and resource failures at real suite sizes, and it drew **four CVSS 9.4–9.8 remote-code-execution advisories during 2026**, one of them patched in 4.1.10 itself. Adopt it, if at all, as a second `projects` entry in its own CI job for the narrow set of components that genuinely need real layout — focus traps, virtualized lists, drag-and-drop, floating-element placement — and note that `vitest-browser-react` is a different API from RTL, not a faster one.

**Version floors** (verified 2026-08-03 — re-check before pinning): Vitest 4.1+, React 19.2+, `happy-dom` 20.11+, `jsdom` 30+, `@testing-library/react` 16.3+, `@testing-library/jest-dom` 7+, `@testing-library/user-event` 14.6+, `msw` 2.15+, `@tanstack/react-query` 5.101+, `zustand` 5+, `axe-core` 4.12+, `@playwright/test` 1.62+. The net Node floor is **22.22.2+** — jsdom 30 sets that specific patch floor, and `@testing-library/jest-dom@7` independently requires Node ≥ 22.

## When to use

- Writing or reviewing any `*.test.tsx` for a component, hook, store, query factory, or util
- Setting up the test toolchain for a new React project
- Deciding **what to assert** (the most common mistake lives here)
- Deciding **how to fake** an API, the router, a clock, or a third-party SDK
- Adding an end-to-end test for a critical user journey

## Setup (green-field, commit 1)

### Step 1 — Install

```bash
npm install -D vitest @vitest/coverage-v8 happy-dom jsdom \
  @testing-library/react @testing-library/dom @testing-library/jest-dom \
  @testing-library/user-event @types/react-dom msw axe-core
npm install -D @playwright/test && npx playwright install
```

`@testing-library/dom` is a **required peer dependency** of `@testing-library/react` 16+ and `jest-dom` 7+ — it is no longer bundled, so install it explicitly. `@types/react-dom` is also required for TypeScript.

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

    // Two projects, because one environment cannot serve both jobs: happy-dom is
    // ~2x faster and implements the APIs components use, but axe does not work in
    // it. `projects` replaced `workspace`, which Vitest 4 removed.
    projects: [
      {
        extends: true,
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
          // jsdom claims the `browser` export condition, so `msw/node` would
          // otherwise resolve MSW's *browser* build and silently fail to
          // intercept. This forces Node resolution — but see the smoke test in
          // Step 4: on Vite 6+ there are open reports of this option being
          // ignored, so never assume it took effect.
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

**The `include`/`exclude` arithmetic above is exact, and getting it wrong fails silently.** With `extends: true`, Vitest merges the root config into each project through Vite's `mergeConfig`, which **concatenates** arrays rather than replacing them. So a root-level `include` does not get narrowed by a project's own `include` — the two are unioned, and the `a11y` project would claim every `*.test.tsx` file in addition to its own. The symptom is not an error: your whole component suite quietly runs a second time on jsdom, with stubs shadowing real APIs and the axe matcher loaded, roughly doubling suite time while defeating the split. Keep `include` out of the root, give each project its own, and let the root `exclude` be inherited rather than repeated. Verify with `vitest list --filesOnly`: each file must appear under exactly one project name.

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
  http.get<never, never, BackupListResponse>('/api/backups', () => {
    const items = [buildBackup({ status: 'active' })]
    return HttpResponse.json({ items, total: items.length })
  }),

  // Declaring your own params interface gives `string`, not
  // `string | readonly string[] | undefined` as MSW's own PathParams would.
  http.get<BackupIdParams, never, Backup>('/api/backups/:backupId', ({ params }) =>
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
  server.listen({ onUnhandledRequest: 'error' })
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

MSW 2 intercepts by patching `globalThis.fetch`, so there is no polyfill to install — `whatwg-fetch`, `cross-fetch`, and `undici` instructions are v1-era and now wrong. Ignore the `@deprecated` tag on the `SetupServerApi` *class*: `setupServer()` itself is staying, and `defineNetwork` is still behind `msw/experimental`.

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

### Step 5 — Zustand reset harness (`src/__mocks__/zustand.ts`)

Every module-level store persists across tests in the same file. This harness registers a reset for each store as it is created and runs them all after each test, so no store can be forgotten. It is the official Zustand pattern, typed for `strictTypeChecked`.

```ts
// src/__mocks__/zustand.ts — must sit under Vitest's `root`.
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

## The testing pyramid

Many fast unit/component tests, few slow E2E tests. Never invert this into an "ice-cream cone" of mostly E2E.

| Tier | Scope | Tool | How many |
|------|-------|------|----------|
| **Unit** | Pure functions, hooks, store logic, query-key factories, utils — no rendering | Vitest | The bulk |
| **Component** | Render one component, interact, assert rendered output + callback props | Testing Library + Vitest | Many |
| **E2E** | Whole app in a real browser against a seeded backend | Playwright | A few critical journeys only |

Budget E2E as a **number, not a percentage**: 8–15 specs, ceiling around 25, with Vitest carrying ~85–90% of all assertions. Decide tier by what you are verifying: a calculation → unit; a component's contract → component; a user journey across pages → E2E. If you are reaching for E2E to test a single component, drop down to a component test.

## Convention 1: Test behavior, not implementation (CRITICAL)

This is the whole skill in one rule. Assert on what a user or a caller can observe: rendered text, roles, callback invocations, return values. Never assert on `useState` internals, effect call counts, render counts, or which child component rendered.

```tsx
// ❌ Implementation — breaks on any refactor, proves nothing about behavior
expect(result.current.internalCount).toBe(1)
expect(fetchBackups).toHaveBeenCalledTimes(1)
expect(renderSpy).toHaveBeenCalledTimes(2)

// ✅ Behavior — the user sees the row and the loading state
expect(await screen.findByRole('row', { name: /nightly-backup/i })).toBeInTheDocument()
expect(screen.getByRole('status')).toHaveTextContent(/loading/i)
```

React 19 removed the `react-dom/test-utils` helpers that made internal assertions easy, stating the reason directly: they "made it too easy to depend on low level implementation details." If you cannot test a behavior without reaching into internals, that is usually a design smell — the behavior is not observable, or the component is doing too much. Fix the design (see `frontend-react-code-style` Pattern 2), don't weaken the test.

## Convention 2: Query like a user — never by CSS class (CRITICAL)

Find elements the way a user (or a screen reader) finds them. Use this priority order:

1. `getByRole` (with `name`) — buttons, headings, inputs, links
2. `getByLabelText` — form fields
3. `getByText` — visible, non-interactive copy
4. `getByTestId` — **escape hatch only**, for elements with no accessible role or stable text

**Never** select by CSS class, tag name, or `container.querySelector`. Class names exist for styling; coupling a test to them means a purely visual change turns a green test red for no behavioral reason. `throwSuggestions: true` (Step 3) makes this mechanical rather than a review comment.

```tsx
// ❌ Coupled to markup and styling — an anti-pattern
expect(container.querySelector('.backup-title-badge')?.textContent).toBe('Backup')

// ✅ Coupled to behavior — survives restyling and re-tagging
expect(screen.getByRole('heading', { level: 3 })).toHaveTextContent('nightly-backup')

// ✅ When nothing semantic exists, add a deliberate test id in the component
expect(screen.getByTestId('backup-badge')).toHaveTextContent('Backup')
```

`data-testid` is a contract: it says "tests depend on this element." Prefer making the element accessible (a real role/label) over adding a test id — accessibility and testability improve together. Use `queryBy*` **only** to assert absence; using it for presence throws away `getBy*`'s diagnostic DOM output and leaves you with `expected null to be truthy`.

## Convention 3: Render fully — never shallow-render, never mock children

Render the component with its real children. Shallow rendering is over: enzyme has no React 18/19 adapter, `react-test-renderer/shallow` was **removed** in React 19, and `react-test-renderer` itself is deprecated with a runtime warning. A shallow test asserts that you wrote the JSX you wrote.

```tsx
// ✅ Real render, real children, real DOM
renderWithProviders(<BackupCard backup={buildBackup()} />)
```

**Do not `vi.mock()` a child component either.** You then test a tree that never ships: integration bugs between parent and child become invisible, and the mock's props drift from the real component's. Mock only at the network boundary (Convention 7). Stub a child only when it is genuinely external or expensive (a map widget, a third-party chart) — stub the exception, render the rule.

## Convention 4: Assert the component contract — rendered output and callback props

A component's contract is **props in → rendered output + callback props called**. Test exactly that boundary.

```tsx
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ConfirmDialog, type ConfirmDialogProps } from './ConfirmDialog'

it('reports the backup id when the user confirms', async () => {
  const user = userEvent.setup()
  const onConfirm = vi.fn<ConfirmDialogProps['onConfirm']>()
  render(<ConfirmDialog backupId="backup-7" onConfirm={onConfirm} onCancel={vi.fn()} />)

  await user.click(screen.getByRole('button', { name: /confirm/i }))

  expect(onConfirm).toHaveBeenCalledWith('backup-7')
})
```

Type the callback spy from the real props type (`vi.fn<ConfirmDialogProps['onConfirm']>()`) so a signature change breaks the test at compile time. Do not test that an internal handler ran; test that the callback fired with the right payload.

## Convention 5: Test hooks by concern

`renderHook` comes from **`@testing-library/react`**. `@testing-library/react-hooks` is dead — it supports React ≤ 17, is a hard error on React 19, and its own README tells you to migrate. It still gets ~3M weekly downloads, which is a direct measure of how much stale advice is in circulation. `waitForNextUpdate`, `waitForValueToChange`, and `result.error` died with it; use `await waitFor(...)` and an error boundary instead.

```tsx
import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useBackupDraft } from './useBackupDraft'

it('becomes dirty and merges partial changes into the draft', () => {
  const { result } = renderHook(() => useBackupDraft(emptyDraft, storageStub))

  act(() => {
    result.current.updateDraft({ name: 'nightly-backup' })
  })

  expect(result.current.draft.name).toBe('nightly-backup')
  expect(result.current.isDirty).toBe(true)
})

it('unsubscribes from storage when unmounted', () => {
  const unsubscribe = vi.fn<() => void>()
  const { unmount } = renderHook(() => useBackupDraft(emptyDraft, { ...storageStub, subscribe: () => unsubscribe }))

  unmount()

  expect(unsubscribe).toHaveBeenCalledOnce()
})
```

Four rules the example encodes:

- **Read through `result.current` at assertion time.** Destructuring it into a local before an `act` captures a stale snapshot — the classic `renderHook` bug.
- **Every state mutation goes inside `act`.** Calling an action bare produces the "not wrapped in act" warning and a stale `result.current`.
- **`rerender` needs `initialProps` and a props-taking callback** to mean anything; with a zero-argument callback it is just a re-render.
- **Assert cleanup through `unmount()` and an observable effect**, never by inspecting internals.

Prefer injecting a hook's collaborators as parameters, as above, so the test needs a typed stub rather than `vi.mock`. And **do not test a hook in isolation when it exists only to serve one component** — a hook with no reuse and no branching is tested for free by the component test. `renderHook` earns its keep for hooks with real state machines, cleanup, or several consumers.

## Convention 6: Zustand — reset every store, test transitions directly

**Store logic tests** — assert state transitions directly; a component adds nothing but noise. Outside a React tree, `getState()`/`setState()` need no `act`.

```ts
it('clears the status filter without touching the sort order', () => {
  useBackupFilterStore.getState().applyStatusFilter('failed')
  useBackupFilterStore.getState().changeSortOrder('name-ascending')

  useBackupFilterStore.getState().clearStatusFilter()

  const { statusFilter, sortOrder } = useBackupFilterStore.getState()
  expect(statusFilter).toBeNull()
  expect(sortOrder).toBe('name-ascending')
})
```

**Component tests that depend on a store** — drive the store, then assert the *rendered* result, not `getState()`. Asserting store state through a component is a store test with extra steps.

Prefer **per-instance stores behind a context provider** for anything feature-scoped (`createStore` from `'zustand'` plus a provider): each test constructs its own store, so there is nothing to reset and the whole class of leakage bugs disappears by construction. Reserve module-level global stores for genuinely app-wide state — theme, session, feature flags.

## Convention 7: Mock at the network boundary with MSW (CRITICAL)

Fake HTTP at the network layer — never the app's own API module, and never the query hooks. Everything between the component and the wire (query keys, `queryOptions`, `select`, serialization, status-code branching, error mapping, invalidation) is production code you are paid to test, and each layer you replace with a stub is a layer whose bugs your suite can no longer see.

```tsx
it('shows a retry affordance when the backup list fails', async () => {
  server.use(http.get('/api/backups', serverErrorResolver))

  renderWithProviders(<BackupListPage />)

  expect(await screen.findByRole('alert')).toHaveTextContent(/could not load/i)
})
```

Concretely, `vi.mock('@tanstack/react-query')` deletes the library from the test: a typo in the key factory passes, a mutation that invalidates the wrong key passes, and a hand-written `{ isLoading: true }` mock keeps passing forever after the v5 rename to `isPending` while the component renders nothing. Mocking your own `api/` module is better but still blind to a wrong URL, a wrong method, or a missing query parameter, and it couples the test to a module path so a rename breaks tests that had no behavioral change.

**Reserve `vi.mock` for non-network modules only** — clocks, `crypto`/`uuid`, third-party SDKs. Use the dynamic-import form (`vi.mock(import('./path'))`) so the path is typed and `importOriginal` inherits types.

## Convention 8: E2E with Playwright — critical journeys only

E2E is slow and flake-prone, so spend it only on journeys that must never break. A journey qualifies only if **all three** hold:

1. It crosses a boundary no simulated DOM can fake — real navigation, session across reload, a download, a cross-origin iframe.
2. It spans at least two routes or two systems.
3. Its failure has a named business cost.

Failing only the first test means it is a component test. Login, and the primary create→read flow, qualify; field validation, empty states, error banners, and sort/filter behavior do not.

```ts
// e2e/authentication.spec.ts
import { expect, test } from '@playwright/test'

test('an operator signs in and lands on the dashboard', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Email').fill('operator@example.com')
  await page.getByLabel('Password').fill('correct-horse')
  await page.getByRole('button', { name: 'Sign in' }).click()

  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
})
```

Rules: `getByRole` first, never a CSS class. Use **web-first auto-retrying assertions** (`await expect(locator).toBeVisible()`) and never `page.waitForTimeout` — an arbitrary wait is simultaneously slow and flaky. Authenticate once through a `setup` project writing `storageState`, rather than logging in per test. Configure `webServer`, `baseURL`, and `trace: 'on-first-retry'`.

**Keep your own API real in E2E.** Stub only third parties and failure states you cannot otherwise provoke (`page.route`). An E2E test with its own API stubbed is a 50×-slower component test that is blind to contract drift.

## Convention 9: File layout, naming, and structure

- **Co-locate** tests next to their source. No `__tests__/` directory: the feature folders already carry meaning (`components`, `hooks`, `api`, `stores`), and a folder level that means nothing just moves a test two path segments away from its subject. A missing test is then visible at a glance.
- **`*.test.ts` / `*.test.tsx` = Vitest. `*.spec.ts` = Playwright, in `e2e/` at the component root.** The extension names the runner, which matters because the two `expect`s have different matchers and different retry semantics. Never mix conventions within one runner.
- **Two infixes carry meaning.** `*.route.test.tsx` marks the expensive router-mounting tests so they stay greppable and cappable (Convention 14). `*.a11y.test.tsx` routes a file to the jsdom project (Convention 16) — that one is not cosmetic, it selects the environment.
- **Enforce the split on both sides**: Vitest `include`/`exclude` (Step 2), Playwright `testDir: './e2e'` + `testMatch: '**/*.spec.ts'`, plus ESLint `no-restricted-imports` forbidding `@playwright/test` under `src/` and `vitest` under `e2e/`. Playwright's `test()` running under Vitest produces an inscrutable error, so belt and braces are worth it.

```
src/features/backups/
  components/BackupTable.tsx
  components/BackupTable.test.tsx       # happy-dom (`unit` project)
  components/BackupTable.a11y.test.tsx  # jsdom (`a11y` project) — suffix picks the env
  hooks/useBackupSearch.ts
  hooks/useBackupSearch.test.ts
  api/backupQueries.ts
  api/backupQueries.test.ts          # key stability + queryFn parsing
  stores/backupUiStore.ts
  stores/backupUiStore.test.ts
src/routes/backups/
  index.tsx
  index.route.test.tsx               # the only files using renderWithRouter
e2e/authentication.spec.ts
```

- **Structure** each test as Arrange–Act–Assert, in three blank-line-separated blocks. If a test needs a second Act, it is two tests.
- **`describe` nesting depth: 1**, exceptionally 2 for genuinely distinct modes that share Arrange. Never 3 — deep nesting plus layered `beforeEach` is how tests start depending on each other. Prefer a named factory helper (`renderBackupTable(overrides)`) over `beforeEach`.
- **Name each `it` as observable behavior** in present tense, naming trigger and outcome — no "should", no component or function names, no implementation vocabulary.

| ❌ | ✅ |
|---|---|
| `it('works')` | `it('shows the total size of all backups')` |
| `it('should call onDelete')` | `it('reports the backup id when the user confirms deletion')` |
| `it('renders correctly')` | `it('shows an empty state when there are no backups')` |
| `it('sets isLoading to true')` | `it('disables the submit button while saving')` |

- **Factories over inline literals.** One `build<Type>(overrides)` factory per domain type, returning the full `T` from a `Partial<T>`, so a schema change fails the compile instead of a hundred assertions.

## Convention 10: Coverage is a signal, not a target

Coverage tells you what the suite **never executed**. That is genuinely useful and it is the only thing it tells you — `render(<Thing />)` with no assertions covers the whole component. Optimizing the number produces assertion-free tests that pin implementation details, which is worse than no test because it also blocks refactoring.

Set thresholds as a **ratchet**: a floor at or just below current, raised when comfortably exceeded. Never a target above current, which is a permanently red build people learn to override. A reasonable start is 70% lines / 65% branches globally, with 90/85 on `features/*/api/**` and `shared/domains/**`. Keep `perFile: false` so a four-line formatter at 75% does not fail, and `autoUpdate: false` so CI never rewrites the bar.

**Branch coverage is not comparable to a non-compiler project.** The React Compiler injects memo-cache branches that no test can both-take, which measurably depresses the number with no fix available. Set your branch floor from your own measured baseline, never from an industry figure.

## Convention 11: Descriptive naming in tests (CRITICAL)

Tests are read far more than they are written, and they document the behavior they assert. Apply the same naming rule as production code: **no single-letter variables and no abbreviations**, anywhere — including callback and event parameters.

```tsx
// ❌
const u = userEvent.setup()
backups.filter(b => b.status === 'failed')
<input onChange={(e) => setSearchQuery(e.target.value)} />

// ✅
const user = userEvent.setup()
const failedBackups = backups.filter(backup => backup.status === 'failed')
<input onChange={(event) => setSearchQuery(event.target.value)} />
```

Never name the render result `wrapper` — that is enzyme vocabulary for something that wraps nothing, and it invites container-querying instead of `screen`.

## Convention 12: One behavior per test (SoC/SRP)

Each test verifies exactly one behavior and has exactly one reason to fail. Do not bundle "renders, then clicks, then asserts, then clicks again" into a single `it` — when it fails you will not know which behavior broke. Separation of concerns and single responsibility apply to tests as strictly as to the code under test: a test that asserts three unrelated things is three tests wearing one name. Split it.

A second assertion after a failure never runs, so a multi-behavior test actively hides defects.

## Convention 13: Server state — fresh `QueryClient` per test, assert through the cache

A `QueryClient` is a cache. Share one across tests and test B reads test A's data without ever hitting MSW, "loading state" assertions fail because the data is already cached, and a `gcTime` timer from one test fires during another. `createTestQueryClient()` (Step 6) is cheaper than remembering those constraints.

Assert the **observable consequence** of a mutation, not that `invalidateQueries` was called — the former catches a wrong query key, which is the actual bug class.

```tsx
it('shows the new backup in the list after the mutation settles', async () => {
  const user = userEvent.setup()
  let createdBackupExists = false
  server.use(
    http.get('/api/backups', () =>
      HttpResponse.json({ items: createdBackupExists ? [buildBackup()] : [], total: createdBackupExists ? 1 : 0 }),
    ),
    http.post('/api/backups', () => {
      createdBackupExists = true
      return HttpResponse.json(buildBackup(), { status: 201 })
    }),
  )

  renderWithProviders(<BackupsPage />)
  await user.click(await screen.findByRole('button', { name: 'Create backup' }))

  // Passes only if the mutation invalidated the correct key and the list refetched.
  expect(await screen.findByRole('row', { name: /nightly-backup/i })).toBeInTheDocument()
})
```

The stateful handler is what gives this test teeth: with a static handler the list returns the same thing before and after, so a mutation invalidating `['backup']` instead of `['backups']` would pass.

**Also test the query-key factory directly** (`api/backupQueries.test.ts`) — assert key shape and stability, and that `queryFn` parses a real MSW response into the domain type. It is the cheapest test in the suite and it prevents the whole "invalidation silently missed" class.

Query v5 renames that break test code written against v4: `cacheTime`→`gcTime`, `status: 'loading'`→`'pending'`, `useErrorBoundary`→`throwOnError`, `keepPreviousData`→`placeholderData: keepPreviousData`, and query-level `onSuccess`/`onError` removed. **The dangerous one is `isLoading`**: it still exists but now means `isPending && isFetching`, so it is `false` for a cached-but-refetching query and `false` for a disabled one. Assertions written against v4 `isLoading` are subtly wrong rather than loudly broken — prefer `isPending`, and prefer asserting rendered output over either.

## Convention 14: Routing — only route files touch the router

A component may read the router (`Route.useParams`, `Route.useSearch`, `useNavigate`, `<Link>`) **only if it is a route file under `src/routes/`, or a shared navigation component whose entire job is navigating** (nav bar, breadcrumb, pagination). Every component under `src/features/*/components/` takes route data as **props** and reports navigation intent through a **callback prop**.

This keeps the expensive harness count equal to the route count rather than the component count, and it is also why such components are reusable. If you find yourself writing `renderWithRouter` for a feature component, that is the signal to refactor, not to add a router.

For route files, build the test router from the **generated** `routeTree.gen` with `createMemoryHistory` — a hand-built tree re-implements the route under test, so it tests your test. Await `router.load()` before asserting so no test observes a half-mounted route.

```tsx
it('applies the status filter from the URL', async () => {
  await renderWithRouter({ initialLocation: '/backups?status=failed' })
  expect(await screen.findByRole('combobox', { name: 'Status' })).toHaveValue('failed')
})
```

Test `validateSearch` at two levels: the exported schema in isolation for the edge cases (a pure function — fast and exhaustive), plus one integration test proving it is actually wired to the route. Assert navigation by **both** the rendered destination and `router.state.location`, since the first proves the user sees the right thing and the second proves reload, share, and back-button work. `router.state.location.search` is the parsed object — assert against an object, not a string.

## Convention 15: Never assert render counts or referential identity (CRITICAL)

This stack has **two independent reasons** to ban these assertions.

**The React Compiler** decides memoization granularity, and React's own guidance tells teams to pin it to an exact version because output can shift between releases. So `expect(firstCallback).toBe(secondCallback)` asserts compiler output granularity, not your app — a compiler patch bump turns the suite red with no product defect. `React.memo`, `useMemo`, and `useCallback` are now escape hatches the compiler makes redundant, so "memo prevented this render" asserts scaffolding that should not be there.

**StrictMode** (on by default here, Step 3) adds an extra render-body invocation and runs effects setup → cleanup → setup, so every effect-call-count assertion is off by one by design.

```tsx
// ❌ Off by one under StrictMode, unstable under the compiler, and never a good assertion
expect(fetchBackups).toHaveBeenCalledTimes(1)

// ✅ StrictMode-proof, compiler-proof, and actually about the product
expect(await screen.findByRole('row', { name: /nightly-backup/i })).toBeInTheDocument()
```

**When a test fails only under StrictMode, read what differs before touching the config.** If observable state or DOM differs — a duplicated list item, a leaked listener — StrictMode found a real defect: an impure render or a missing cleanup. Fix the component. If only a call count differs on an otherwise-idempotent effect, the **test** is wrong; rewrite it to assert the outcome. Never "fix" it by disabling StrictMode.

**Keep the compiler on in the test build (Step 2) — but know that this one is a genuine judgment call.** The compiler *does* run under Vitest whenever the single `vite.config.ts` is used, and there is no documented switch to disable it in test mode. The case for leaving it on: a suite running uncompiled code is not testing what ships, and the compiler is precisely the layer most likely to surprise you, since React's own guidance is that code relying on memoization *for correctness* can break under it. The case against, which is a defensible house standard elsewhere: compiling costs test speed and measurably corrupts branch coverage, and `eslint-plugin-react-hooks` v7 now carries the compiler's own rules, so Rules-of-React violations are caught at lint time regardless. This skill chooses **on**, and pays for it by setting the branch threshold below lines (Convention 10). If your project would rather have fast, honest coverage and lean on the lint gate, that is a legitimate inversion — make it deliberately, in one place, and write down which way you went.

For genuine "the network was hit exactly once" requirements, assert at the network boundary where request deduplication is part of the behavior under test — not at the effect-call-count level. Ban render-counting tooling (`react-performance-testing`, `<Profiler onRender>`) from the unit tier; if you need to know a component's cost, measure it with a benchmark or a Playwright trace.

## Convention 16: Accessibility — axe as a regression net, not an audit

Use **`axe-core` directly** with a small typed matcher, in files named `*.a11y.test.tsx`.

**These tests are their own Vitest project, running on jsdom (Step 2).** axe is documented to break on happy-dom's `Node.prototype.isConnected`, so it cannot run in the default `unit` project. The naming convention is what routes a file to the right environment, which means the suffix is load-bearing rather than decorative: name an accessibility test `Component.test.tsx` and it runs on happy-dom, where axe is unreliable and may report a false pass. That is the one failure mode of this split, and it is why the assertion lives behind a dedicated matcher name you can grep for.

```ts
// src/test/accessibility.ts
import axe, { type AxeResults, type ElementContext, type RunOptions } from 'axe-core'
import { expect } from 'vitest'

const rulesUnsupportedInJsdom: RunOptions = {
  rules: {
    // Needs real layout; only the Playwright scan can check contrast.
    'color-contrast': { enabled: false },
    // A component fragment legitimately has no landmark; assert this at page level.
    region: { enabled: false },
  },
}

function formatViolations(results: AxeResults): string {
  if (results.violations.length === 0) {
    return 'expected accessibility violations, but found none'
  }

  const details = results.violations
    .map((violation) => {
      const targets = violation.nodes.map((node) => node.target.join(' ')).join('\n      ')
      return [
        `  [${violation.impact ?? 'unknown'}] ${violation.id}: ${violation.help}`,
        `    ${violation.helpUrl}`,
        `    affected nodes:\n      ${targets}`,
      ].join('\n')
    })
    .join('\n\n')

  return `expected no accessibility violations, found ${String(results.violations.length)}:\n\n${details}`
}

expect.extend({
  async toHaveNoAccessibilityViolations(received: ElementContext, runOptions?: RunOptions) {
    const results = await axe.run(received, { ...rulesUnsupportedInJsdom, ...runOptions })
    return {
      pass: results.violations.length === 0,
      message: () => formatViolations(results),
    }
  },
})

declare module 'vitest' {
  // The type parameter is the *received* type, not the return type — the
  // assertion itself resolves to void. Arity must match Vitest's own
  // declaration for the augmentation to merge.
  interface Matchers<Received = unknown> {
    toHaveNoAccessibilityViolations: (runOptions?: RunOptions) => Promise<void>
  }
}
```

```tsx
// src/features/backups/components/BackupTable.a11y.test.tsx
it('has no accessibility violations', async () => {
  const { container } = renderWithProviders(<BackupTable backups={[buildBackup()]} />)
  await expect(container).toHaveNoAccessibilityViolations()
})
```

Scan page-level routes in E2E with `@axe-core/playwright`, attaching results to the report via `testInfo.attach`. The two layers are **complementary, not redundant** — contrast needs real layout, so only the browser scan checks it. Scan again after each interaction that reveals new DOM: axe only sees the current tree, so a dialog, flyout, or error state each need their own scan.

**A green axe run is not an accessible component.** It says nothing about whether an accessible name is *meaningful* (`aria-label="button"` passes every rule and helps nobody), whether Tab order is logical, whether a modal traps focus and restores it on close, or what a screen reader actually announces. Those need explicit `user.tab()` / `document.activeElement` assertions and periodic manual passes. Pair axe with `eslint-plugin-jsx-a11y`, which catches a different class of problem before runtime.

## Convention 17: Await everything — no arbitrary waits, no stray `act`

Asynchrony is the top source of flaky React tests, and almost all of it comes from four mistakes.

- **`userEvent.setup()` before render, once per test, and `await` every `user.*` call.** Missing awaits are the single biggest cause of "element not found" flakes. Direct calls (`userEvent.click(element)`) exist only to ease v13 migration — ban them; one form only.
- **`await screen.findBy*` for appearance**, `waitForElementToBeRemoved` for disappearance, and `waitFor` only when what you are awaiting is not a DOM query (a spy count, `router.state`, cache contents). `findBy*` is `getBy* + waitFor` with the retry, timeout, and — critically — the *failure message* already wired up. Never put multiple assertions or side effects inside `waitFor`: the callback runs a non-deterministic number of times, and a failure in the second assertion waits out the whole timeout instead of failing fast.
- **Never wrap `render`, `fireEvent`, or `user.*` in `act()`.** All three already do it, and the extra wrapper swallows the warning that was trying to tell you something. `act` is for driving state outside those helpers — a hook action (Convention 5) or a timer advance.
- **Never use an arbitrary `setTimeout` wait.** It is too short on a loaded CI runner and wasted seconds everywhere else.

Prefer `fireEvent` only for events `user-event` cannot produce (synthetic `scroll`, `transitionEnd`). `fireEvent.change` fires one event where a real user produces keydown/keypress/input/keyup, so tests can pass on interactions that are impossible in a browser.

**Fake timers are a last resort.** They fight `user-event`'s internal delays and `waitFor`'s polling. Most "I need fake timers" cases are really "I need to assert a debounced outcome," which `await screen.findBy*` handles without touching the clock. When you genuinely need them, scope them to the one test, use `advanceTimersByTimeAsync` so React's scheduler and promise chains flush, restore in a `finally`, and if the test also drives the UI, pass `advanceTimers` to `userEvent.setup()`.

## Quick reference

| Task | Do this |
|------|---------|
| Render a component | `renderWithProviders(<Component {...props} />)` |
| Find an element | `getByRole` → `getByLabelText` → `getByText` → `getByTestId` |
| Click / type | `const user = userEvent.setup()`, then `await user.click(...)` / `await user.type(...)` |
| Assert a callback prop | `expect(onConfirm).toHaveBeenCalledWith('backup-7')` |
| Await async UI | `await screen.findByRole(...)` — `waitFor` only for non-DOM conditions |
| Fake an API response | MSW handler (default in `handlers/`, override with `server.use(...)`) |
| Fake a clock / uuid / SDK | `vi.useFakeTimers()` per test / `vi.mock(import('./path'))` — non-network only |
| Test a hook | `renderHook` from `@testing-library/react`; mutate inside `act` |
| Test a store | `useStore.getState().action()`, assert `getState()` — reset is automatic |
| Server state | fresh `createTestQueryClient()` per test; assert rendered output |
| Route params / search | `renderWithRouter({ initialLocation })` in a `*.route.test.tsx` file |
| Type a mock | `vi.fn<typeof realFunction>()` or `vi.fn<Props['onDelete']>()` |
| Build test data | `buildBackup({ status: 'failed' })` factory |
| Accessibility | `await expect(container).toHaveNoAccessibilityViolations()` in a `*.a11y.test.tsx` file |
| Critical user journey | Playwright spec in `e2e/*.spec.ts` |

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Asserting on state internals or effect call counts | Assert rendered output and callback props (Conventions 1, 15) |
| `container.querySelector('.some-class')` | Query by role/label/text; `data-testid` only as a last resort (Convention 2) |
| `vi.mock()` on a child component or your own API module | Render real children; mock the network with MSW (Conventions 3, 7) |
| `import { renderHook } from '@testing-library/react-hooks'` | It is dead and errors on React 19 — import from `@testing-library/react` (Convention 5) |
| `jest-axe` or `vitest-axe` | Unmaintained or untypeable — `axe-core` plus the typed matcher (Convention 16) |
| An axe assertion in a plain `*.test.tsx` | It runs on happy-dom, where axe is unreliable and may false-pass. Rename to `*.a11y.test.tsx` (Convention 16) |
| Stubbing `matchMedia`/`ResizeObserver` globally | happy-dom implements them; a global stub makes the unit project test a no-op. Stubs load only in the jsdom project (Steps 2–3) |
| A root-level `include` alongside `projects` | Inherited arrays concatenate, so it widens every project's include and runs your suite twice. Give each project its own (Step 2) |
| Missing `await` on a `user.*` call | `await` every one; that is the #1 flake source (Convention 17) |
| `act()` around `render` / `fireEvent` / `user.*` | Redundant, and it hides the warning you needed (Convention 17) |
| Arbitrary `setTimeout` waits | `await screen.findBy*` / `waitForElementToBeRemoved` (Convention 17) |
| Multiple assertions inside `waitFor` | One assertion, or use `findBy*` (Convention 17) |
| `import '@testing-library/jest-dom'` under Vitest | Import `'@testing-library/jest-dom/vitest'` or matchers never register (Step 3) |
| Relying on RTL auto-cleanup with `globals: false` | Register `afterEach(cleanup)` yourself (Step 3) |
| `react({ babel: { plugins: [...] } })` for the compiler | Removed in plugin-react 6 — use `reactCompilerPreset` (Step 2) |
| A separate `vitest.config.ts` | It makes `vite.config.ts` ignored and silently drops the compiler (Step 2) |
| Sharing one `QueryClient` across tests | Fresh client per test; `retry: false`, no `gcTime: Infinity` (Convention 13) |
| `gcTime: Infinity` or `logger` in test query options | Jest-only workaround; `logger` was removed in v5 (Step 6) |
| Asserting `isLoading` from v4 habit | `isLoading` changed meaning in v5 — prefer `isPending`, or assert output (Convention 13) |
| `renderWithRouter` for a feature component | Pass route data as props; only route files touch the router (Convention 14) |
| Snapshotting whole component trees | Assert specific behavior; snapshots rot and get re-blessed unread |
| A store created via `zustand/vanilla` | Create via `'zustand'` or the reset harness never sees it (Step 5) |
| E2E for what a component test covers | Drop to a component test; reserve E2E for journeys (Convention 8) |
| One giant `it('works')` | One behavior per test (Convention 12) |
| Chasing a coverage percentage | Coverage is a signal; ratchet the floor (Convention 10) |
