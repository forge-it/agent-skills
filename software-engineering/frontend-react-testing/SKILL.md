---
name: frontend-react-testing
description: Use when writing, reviewing, or setting up tests for a React 19 SPA — components, custom hooks, Zustand stores, TanStack Query data, TanStack Router routes, accessibility checks, or end-to-end journeys — and when deciding what to assert, how to fake the network, or where a test file lives.
vibe: Tests that survive refactors — behavior in, implementation out.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.2"
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
| DOM environment | **happy-dom** for the bulk, **jsdom** for accessibility tests | Roughly twice as fast, and it implements the browser APIs a React suite reaches for; axe does not run reliably on it, so accessibility tests are a second Vitest project on jsdom. The trade is spelled out once, below. |
| User interaction | **@testing-library/user-event** | Produces the real event sequence (pointer, focus, key) instead of one synthetic event. |
| Network mocking | **MSW** (Mock Service Worker) | Mocks at the network boundary, so the same handlers serve unit, component, and E2E tests. |
| Assertion matchers | **@testing-library/jest-dom** | `toBeInTheDocument`, `toBeDisabled`, `toHaveAccessibleName` — reads like behavior. |
| Server state in tests | **@tanstack/react-query** + a fresh `QueryClient` per test | The cache is the source of truth; a fresh client is what keeps tests isolated. |
| Client state in tests | **zustand** + a global store-reset harness | Module-level stores leak across tests unless reset mechanically. |
| Accessibility | **axe-core** directly, with a small typed matcher | First-party from Deque, ships its own types, no `@types/*` and no Jest dependencies. |
| End-to-end | **Playwright** | Current best-in-class browser automation; fast, reliable, parallel. |
| Coverage | **@vitest/coverage-v8** | Native, no instrumentation step, AST-accurate. |

> **Do not use `jest-axe` or `vitest-axe`.** `vitest-axe`'s only stable release is 0.1.0 from October 2022 and it is effectively unmaintained. `jest-axe` is maintained but ships **no TypeScript types**; the only types available are `@types/jest-axe`, which pins `axe-core@3.x` against a 4.x runtime and drags `@types/jest` into a Vitest project, where the two `expect` globals collide. Both are recommended by most 2023–2025 material. Convention 16 replaces them with ~20 lines you own.

> **Why happy-dom, and what it costs.** happy-dom benchmarks roughly **twice as fast**, and it natively implements five APIs jsdom 30 does *not* — `matchMedia`, `ResizeObserver`, `IntersectionObserver`, `showModal()`, `scrollIntoView` — so the popular "jsdom is more complete" line is true of the DOM spec broadly and false of the surface a React suite touches. Under jsdom every one of those five needs a hand-written stub, and a stub is a lie your tests believe.
>
> The cost is real and you must know it: **happy-dom's accessible-name computation is untested** — not proven worse than jsdom's, just unmeasured — and Convention 2 makes `getByRole` the primary query for the whole codebase. Two things contain that risk. First, accessibility assertions run on jsdom in their own project (Convention 16), because axe is documented to break on happy-dom's `Node.prototype.isConnected`. Second, `eslint-plugin-jsx-a11y` and the Playwright axe scan catch name/role defects that neither environment's query layer would. If a `getByRole` query ever behaves differently from the browser, that is a bug worth reporting upstream and a reason to run that one file on jsdom — not a reason to move the whole suite. Note the two mechanisms are not interchangeable: a `// @vitest-environment jsdom` docblock swaps the environment **for that file inside its own project**, so it keeps the `unit` project's setup files and does *not* pick up the jsdom stubs or the axe matcher. Renaming to `*.a11y.test.tsx` is what actually moves a file into the `a11y` project. Use the docblock for a one-off environment quirk, the rename when the file needs the a11y harness.
>
> jsdom stays installed for the accessibility project, so its patch-pinned `engines` (`^22.22.2 || ^24.15.0 || >=26.0.0`) still set the repository's Node floor — an easy `EBADENGINE` trap in CI.

> **Vitest Browser Mode is not the default here.** It is stable as of Vitest 4 and it is not slower — it measurably beats a simulated environment on larger suites, because its startup cost is fixed rather than per-file. Keep it out of the default tier anyway: it needs Playwright binaries in CI, it has a documented cluster of determinism and resource failures at real suite sizes, and it drew **four CVSS 9.4–9.8 remote-code-execution advisories during 2026**, one of them patched in 4.1.10 itself. Adopt it, if at all, as a second `projects` entry in its own CI job for the narrow set of components that genuinely need real layout — focus traps, virtualized lists, drag-and-drop, floating-element placement — and note that `vitest-browser-react` is a different API from RTL, not a faster one.

**Version floors** (verified 2026-09-29 — re-check before pinning): Vitest 5+, React 19.2+, `happy-dom` 20.14+, `jsdom` 30.1+, `@testing-library/react` 16.3+, `@testing-library/jest-dom` 7+, `@testing-library/user-event` 14.6+, `msw` 3+ (ESM-only; `server.listen`'s `onUnhandledRequest` became `onUnhandledFrame`), `@tanstack/react-query` 5.104+, `zustand` 5+, `axe-core` 4.13+, `@playwright/test` 1.63+, TypeScript 5.9+ (MSW 3's floor). The net Node floor is **22.22.2+** — jsdom 30 sets that specific patch floor; Vitest 5, MSW 3, and `@testing-library/jest-dom@7` each independently require Node 22.

Two Vitest 5 defaults the conventions lean on: an asynchronous assertion that is not awaited now fails the test, and mocks are cleared before every test.

## When to use

- Writing or reviewing any `*.test.tsx` for a component, hook, store, query factory, or util
- Setting up the test toolchain for a new React project
- Deciding **what to assert** (the most common mistake lives here)
- Deciding **how to fake** an API, the router, a clock, or a third-party SDK
- Adding an end-to-end test for a critical user journey

## Setup (green-field, commit 1)

The one-time toolchain setup lives in [`setup.md`](setup.md) next to this file: install, the two-project `vite.config.ts`, the global setup file and the jsdom stubs, the MSW server with its interception smoke test, the Zustand reset harness, the provider harness, and the scripts. Read it when bootstrapping a project or when a convention below cites one of its steps. The conventions assume the files it creates:

| File | What the conventions rely on |
|------|------------------------------|
| `vite.config.ts` (setup.md Step 2) | `unit` project on happy-dom for `*.test.tsx`, `a11y` project on jsdom for `*.a11y.test.tsx`; the React Compiler runs in the test build |
| `src/test/setup.ts` (setup.md Step 3) | jest-dom matchers, `reactStrictMode: true`, `throwSuggestions: true`, explicit `afterEach(cleanup)`, `vi.mock('zustand')` |
| `src/test/setup-msw.ts` + `src/test/msw/` (setup.md Step 4) | `server` listening with `onUnhandledFrame: 'error'`, a `server.boundary` per test, typed handlers, `serverErrorResolver` |
| `__mocks__/zustand.ts` at the project root (setup.md Step 5) | every store created through `'zustand'` resets after each test |
| `src/test/providers.tsx` (setup.md Step 6) | `renderWithProviders`, `createTestQueryClient` |

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

**Never** select by CSS class, tag name, or `container.querySelector`. Class names exist for styling; coupling a test to them means a purely visual change turns a green test red for no behavioral reason. `throwSuggestions: true` (setup.md Step 3) makes this mechanical rather than a review comment.

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
  useBackupFilterStore.getState().applyStatusFilter(BackupStatus.Failed)
  useBackupFilterStore.getState().changeSortOrder(SortOrder.NameAscending)

  useBackupFilterStore.getState().clearStatusFilter()

  const { statusFilter, sortOrder } = useBackupFilterStore.getState()
  expect(statusFilter).toBeNull()
  expect(sortOrder).toBe(SortOrder.NameAscending)
})
```

**Component tests that depend on a store** — drive the store, then assert the *rendered* result, not `getState()`. Asserting store state through a component is a store test with extra steps.

Prefer **per-instance stores behind a context provider** for anything feature-scoped (`createStore` from `'zustand'` plus a provider): each test constructs its own store, so there is nothing to reset and the whole class of leakage bugs disappears by construction. Reserve module-level global stores for genuinely app-wide state — theme, session, feature flags.

## Convention 7: Mock at the network boundary with MSW (CRITICAL)

Fake HTTP at the network layer — never the app's own API module, and never the query hooks. Everything between the component and the wire (query keys, `queryOptions`, `select`, serialization, status-code branching, error mapping, invalidation) is production code you are paid to test, and each layer you replace with a stub is a layer whose bugs your suite can no longer see.

```tsx
it('shows a retry affordance when the backup list fails', async () => {
  server.use(http.get(BACKUPS_API_PATH, serverErrorResolver))

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
- **Enforce the split on both sides**: Vitest `include`/`exclude` (setup.md Step 2), Playwright `testDir: './e2e'` + `testMatch: '**/*.spec.ts'`, plus ESLint `no-restricted-imports` forbidding `@playwright/test` under `src/` and `vitest` under `e2e/`. Playwright's `test()` running under Vitest produces an inscrutable error, so belt and braces are worth it.

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
backups.filter(b => b.status === BackupStatus.Failed)
<input onChange={(e) => setSearchQuery(e.target.value)} />

// ✅
const user = userEvent.setup()
const failedBackups = backups.filter(backup => backup.status === BackupStatus.Failed)
<input onChange={(event) => setSearchQuery(event.target.value)} />
```

Never name the render result `wrapper` — that is enzyme vocabulary for something that wraps nothing, and it invites container-querying instead of `screen`.

## Convention 12: One behavior per test (SoC/SRP)

Each test verifies exactly one behavior and has exactly one reason to fail. Do not bundle "renders, then clicks, then asserts, then clicks again" into a single `it` — when it fails you will not know which behavior broke. Separation of concerns and single responsibility apply to tests as strictly as to the code under test: a test that asserts three unrelated things is three tests wearing one name. Split it.

A second assertion after a failure never runs, so a multi-behavior test actively hides defects.

## Convention 13: Server state — fresh `QueryClient` per test, assert through the cache

A `QueryClient` is a cache. Share one across tests and test B reads test A's data without ever hitting MSW, "loading state" assertions fail because the data is already cached, and a `gcTime` timer from one test fires during another. `createTestQueryClient()` (setup.md Step 6) is cheaper than remembering those constraints.

Assert the **observable consequence** of a mutation, not that `invalidateQueries` was called — the former catches a wrong query key, which is the actual bug class.

```tsx
it('shows the new backup in the list after the mutation settles', async () => {
  const user = userEvent.setup()
  let createdBackupExists = false
  server.use(
    http.get(BACKUPS_API_PATH, () =>
      HttpResponse.json({ items: createdBackupExists ? [buildBackup()] : [], total: createdBackupExists ? 1 : 0 }),
    ),
    http.post(BACKUPS_API_PATH, () => {
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
  expect(await screen.findByRole('combobox', { name: 'Status' })).toHaveValue(BackupStatus.Failed)
})
```

Test `validateSearch` at two levels: the exported schema in isolation for the edge cases (a pure function — fast and exhaustive), plus one integration test proving it is actually wired to the route. Assert navigation by **both** the rendered destination and `router.state.location`, since the first proves the user sees the right thing and the second proves reload, share, and back-button work. `router.state.location.search` is the parsed object — assert against an object, not a string.

## Convention 15: Never assert render counts or referential identity (CRITICAL)

This stack has **two independent reasons** to ban these assertions.

**The React Compiler** decides memoization granularity, and React's own guidance tells teams to pin it to an exact version because output can shift between releases. So `expect(firstCallback).toBe(secondCallback)` asserts compiler output granularity, not your app — a compiler patch bump turns the suite red with no product defect. `React.memo`, `useMemo`, and `useCallback` are now escape hatches the compiler makes redundant, so "memo prevented this render" asserts scaffolding that should not be there.

**StrictMode** (on by default here, setup.md Step 3) adds an extra render-body invocation and runs effects setup → cleanup → setup, so every effect-call-count assertion is off by one by design.

```tsx
// ❌ Off by one under StrictMode, unstable under the compiler, and never a good assertion
expect(fetchBackups).toHaveBeenCalledTimes(1)

// ✅ StrictMode-proof, compiler-proof, and actually about the product
expect(await screen.findByRole('row', { name: /nightly-backup/i })).toBeInTheDocument()
```

**When a test fails only under StrictMode, read what differs before touching the config.** If observable state or DOM differs — a duplicated list item, a leaked listener — StrictMode found a real defect: an impure render or a missing cleanup. Fix the component. If only a call count differs on an otherwise-idempotent effect, the **test** is wrong; rewrite it to assert the outcome. Never "fix" it by disabling StrictMode.

**Keep the compiler on in the test build (setup.md Step 2) — but know that this one is a genuine judgment call.** The compiler *does* run under Vitest whenever the single `vite.config.ts` is used, and there is no documented switch to disable it in test mode. The case for leaving it on: a suite running uncompiled code is not testing what ships, and the compiler is precisely the layer most likely to surprise you, since React's own guidance is that code relying on memoization *for correctness* can break under it. The case against, which is a defensible house standard elsewhere: compiling costs test speed and measurably corrupts branch coverage, and `eslint-plugin-react-hooks` v7 now carries the compiler's own rules, so Rules-of-React violations are caught at lint time regardless. This skill chooses **on**, and pays for it by setting the branch threshold below lines (Convention 10). If your project would rather have fast, honest coverage and lean on the lint gate, that is a legitimate inversion — make it deliberately, in one place, and write down which way you went.

For genuine "the network was hit exactly once" requirements, assert at the network boundary where request deduplication is part of the behavior under test — not at the effect-call-count level. Ban render-counting tooling (`react-performance-testing`, `<Profiler onRender>`) from the unit tier; if you need to know a component's cost, measure it with a benchmark or a Playwright trace.

## Convention 16: Accessibility — axe as a regression net, not an audit

Use **`axe-core` directly** with a small typed matcher, in files named `*.a11y.test.tsx`.

**These tests are their own Vitest project on jsdom (setup.md Step 2), because axe does not run reliably on happy-dom — the trade is in The stack.** The `*.a11y.test.tsx` suffix is what routes a file there, so it is load-bearing: name an accessibility test `Component.test.tsx` and axe may false-pass on happy-dom. That is the one failure mode of the split, and why the assertion lives behind a dedicated matcher name you can grep for.

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

- **`userEvent.setup()` before render, once per test, and `await` every `user.*` call.** Missing awaits are the single biggest cause of "element not found" flakes. Vitest 5 fails a test whose asynchronous *assertion* (`resolves`, `rejects`, an async custom matcher) is not awaited; a missing `await` on a `user.*` call is still on you. Direct calls (`userEvent.click(element)`) exist only to ease v13 migration — ban them; one form only.
- **`await screen.findBy*` for appearance**, `waitForElementToBeRemoved` for disappearance, and `waitFor` only when what you are awaiting is not a DOM query (a spy count, `router.state`, cache contents). `findBy*` is `getBy* + waitFor` with the retry, timeout, and — critically — the *failure message* already wired up. Never put multiple assertions or side effects inside `waitFor`: the callback runs a non-deterministic number of times, and a failure in the second assertion waits out the whole timeout instead of failing fast.
- **Never wrap `render`, `fireEvent`, or `user.*` in `act()`.** All three already do it, and the extra wrapper swallows the warning that was trying to tell you something. `act` is for driving state outside those helpers — a hook action (Convention 5) or a timer advance.
- **Never use an arbitrary `setTimeout` wait.** It is too short on a loaded CI runner and wasted seconds everywhere else.

Prefer `fireEvent` only for events `user-event` cannot produce (synthetic `scroll`, `transitionEnd`). `fireEvent.change` fires one event where a real user produces keydown/keypress/input/keyup, so tests can pass on interactions that are impossible in a browser.

**Fake timers are a last resort.** They fight `user-event`'s internal delays and `waitFor`'s polling. Most "I need fake timers" cases are really "I need to assert a debounced outcome," which `await screen.findBy*` handles without touching the clock. When you genuinely need them, scope them to the one test, use `advanceTimersByTimeAsync` so React's scheduler and promise chains flush, restore in a `finally`, and if the test also drives the UI, pass `advanceTimers` to `userEvent.setup()`. MSW 3 no longer patches `setTimeout` to dodge fake timers, so a handler that uses `delay()` resolves only when you advance the clock.

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
| Build test data | `buildBackup({ status: BackupStatus.Failed })` factory |
| Accessibility | `await expect(container).toHaveNoAccessibilityViolations()` in a `*.a11y.test.tsx` file |
| Critical user journey | Playwright spec in `e2e/*.spec.ts` |
