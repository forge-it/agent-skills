---
name: frontend-vue-testing
description: Opinionated testing standard for Vue 3. Use when writing, reviewing, or setting up tests for Vue components, composables, Pinia stores, or end-to-end flows — choosing test tooling, mocking an API, deciding what to assert, or organizing test files. Covers Vitest, Vue Test Utils / Testing Library, MSW network mocking, and Playwright, plus the behavior-first unit/component/E2E pyramid for green-field projects.
vibe: Tests that survive refactors — behavior in, implementation out.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.1"
---

# Vue Testing — Opinionated Standard

This skill marks **the** testing standard for a new Vue 3 project. It is opinionated on purpose: it names one best-in-class tool per job and one way to use it, so that every test in the codebase reads the same and survives refactors. Existing projects may not comply — that is fine; this is the bar a green-field project starts from at commit 1.

**Core principle: test what a component does, not how it does it.** A test that asserts on internal state, private methods, CSS class names, or child-component internals breaks every time you refactor without catching a single real regression. A test that asserts on rendered output, emitted events, and user-visible behavior keeps passing through refactors and fails only when behavior actually breaks. Every convention below serves that one principle.

## The stack

One tool per job. Do not introduce alternatives without a deliberate decision.

| Job | Tool | Why this one |
|-----|------|--------------|
| Test runner | **Vitest** | Shares the Vite transform pipeline — no separate Babel/transform config. Jest is legacy for new Vue work. |
| Component rendering + queries | **@testing-library/vue** | Pushes you toward user-facing queries (role/text) and away from implementation details. Wraps Vue Test Utils. |
| Low-level mounting (rare fallback) | **@vue/test-utils** | Only when you genuinely need component-instance access Testing Library cannot give. |
| DOM environment | **happy-dom** | Fast. Use `jsdom` instead only if you hit a compatibility gap. |
| Network mocking | **MSW** (Mock Service Worker) | Mocks at the network boundary, so the same handlers serve unit, component, and E2E tests. |
| Assertion matchers | **@testing-library/jest-dom** | `toBeInTheDocument`, `toHaveTextContent`, `toBeDisabled` — reads like behavior. |
| Pinia in tests | **@pinia/testing** | `createTestingPinia` for component tests; `setActivePinia` for isolated store tests. |
| End-to-end | **Playwright** | Current best-in-class browser automation; fast, reliable, parallel. |
| Coverage | **@vitest/coverage-v8** | Native, no instrumentation step. |

## When to use

- Writing or reviewing any `*.test.ts` for a component, composable, store, or util
- Setting up the test toolchain for a new Vue project
- Deciding **what to assert** (the most common mistake lives here)
- Deciding **how to fake** an API, the router, a clock, or a third-party SDK
- Adding an end-to-end test for a critical user journey

This skill is Vue 3 + Vite specific. It assumes the project structure and component design from `frontend-vue-development` and `frontend-vue-code-style` (feature folders, container/presenter split, props-down/emits-up) — that design is what makes components testable in the first place.

## Setup (green-field, commit 1)

### Step 1 — Install

```bash
npm install -D vitest @testing-library/vue @testing-library/jest-dom \
  @vue/test-utils happy-dom msw @pinia/testing @vitest/coverage-v8
npm install -D @playwright/test && npx playwright install
```

### Step 2 — Configure Vitest (`vite.config.ts`)

```ts
/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: "happy-dom",          // DOM for every test; opt down per-file if a pure-logic file is hot
    globals: true,                     // describe/it/expect without imports
    setupFiles: ["./src/test/setup.ts"],
    coverage: { provider: "v8", reporter: ["text", "html"] },
  },
});
```

### Step 3 — Global setup file (`src/test/setup.ts`)

```ts
import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { cleanup } from "@testing-library/vue";
import { mswServer } from "./msw/server";

// MSW: any unmocked request is a test failure, not a silent fallthrough.
beforeAll(() => mswServer.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  cleanup();              // unmount components between tests
  mswServer.resetHandlers();
});
afterAll(() => mswServer.close());
```

### Step 4 — MSW server (`src/test/msw/`)

```ts
// src/test/msw/handlers.ts
import { http, HttpResponse } from "msw";
import { makeJob } from "../factories/job";

export const defaultHandlers = [
  http.get("/api/jobs/:jobId", () => HttpResponse.json(makeJob())),
];

// src/test/msw/server.ts
import { setupServer } from "msw/node";
import { defaultHandlers } from "./handlers";

export const mswServer = setupServer(...defaultHandlers);
```

### Step 5 — Scripts (`package.json`)

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
| **Unit** | Pure functions, composables, store logic, utils — no rendering | Vitest | The bulk |
| **Component** | Mount one component, interact, assert rendered output + emitted events | Testing Library + Vitest | Many |
| **E2E** | Whole app in a real browser against a mocked/seeded backend | Playwright | A few critical journeys only |

Decide tier by what you are verifying: a calculation → unit; a component's contract → component; a user journey across pages → E2E. If you are reaching for E2E to test a single component, drop down to a component test.

## Convention 1: Test behavior, not implementation (CRITICAL)

This is the whole skill in one rule. Assert on what a user or a caller can observe: rendered text, roles, emitted events, return values. Never assert on internal `ref` values, private methods, or which child component rendered.

```ts
// ❌ Implementation — breaks on any refactor, proves nothing about behavior
expect(wrapper.vm.internalCount).toBe(1);
expect(wrapper.vm.handleClick).toHaveBeenCalled();
expect(wrapper.findComponent(InternalSpinner).exists()).toBe(true);

// ✅ Behavior — the user sees a count of 1 and a loading state
expect(screen.getByText("1 item")).toBeInTheDocument();
expect(screen.getByRole("status")).toHaveTextContent(/loading/i);
```

If you cannot test a behavior without reaching into internals, that is usually a design smell: the behavior is not actually observable, or the component is doing too much. Fix the design (see `frontend-vue-development` container/presenter split), don't weaken the test.

## Convention 2: Query like a user — never by CSS class (CRITICAL)

Find elements the way a user (or a screen reader) finds them. This is also what makes Convention 1 enforceable. Use this priority order:

1. `getByRole` (with `name`) — buttons, headings, inputs, links
2. `getByLabelText` — form fields
3. `getByText` — visible, non-interactive copy
4. `getByTestId` — **escape hatch only**, for elements with no accessible role or stable text

**Never** select by CSS class or tag name. Class names exist for styling; coupling a test to them means a purely visual change turns a green test red for no behavioral reason.

```ts
// ❌ Coupled to markup and styling — an anti-pattern
expect(wrapper.find(".record-title-badge").text()).toBe("Backup");
expect(wrapper.find("h3.record-title-id").text()).toBe("019e7d1a");

// ✅ Coupled to behavior — survives restyling and re-tagging
expect(screen.getByText("Backup")).toBeInTheDocument();
expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent("019e7d1a");

// ✅ When nothing semantic exists, add a deliberate test id in the component
//    <span data-testid="record-badge">{{ type }}</span>
expect(screen.getByTestId("record-badge")).toHaveTextContent("Backup");
```

`data-testid` is a contract: it says "tests depend on this element." Prefer making the element accessible (a real role/label) over adding a test id — accessibility and testability improve together.

## Convention 3: Render fully — never `shallowMount`

Render the component with its real children. `shallowMount` (stubbing all children) tests the wiring you wrote instead of the behavior the user gets, and it makes Convention 2 impossible because the real DOM is never produced.

```ts
import { render, screen } from "@testing-library/vue";

// ✅ Real render, real children, real DOM
render(BackupCard, { props: { backup: makeBackup() } });
```

Stub a child only when it is genuinely external or expensive (a map widget, a third-party chart). Stub the exception, render the rule.

## Convention 4: Assert the component contract — output and emitted events

A component's contract is: **props in → rendered output + emitted events out.** Test exactly that boundary. Interactions are `async` because Vue updates the DOM on the next tick — always `await` them.

```ts
import { render, screen, fireEvent } from "@testing-library/vue";
import ConfirmDialog from "../ConfirmDialog.vue";

it("emits confirm with the id when the user confirms", async () => {
  const { emitted } = render(ConfirmDialog, { props: { recordId: "backup-7" } });

  await fireEvent.click(screen.getByRole("button", { name: /confirm/i }));

  expect(emitted()).toHaveProperty("confirm");
  expect(emitted().confirm[0]).toEqual(["backup-7"]);
});
```

`render` (Testing Library) returns `emitted()` just like Vue Test Utils — use it to assert the event half of the contract. Do not test that an internal handler ran; test that the event fired with the right payload.

## Convention 5: Test composables by concern

Split by how the composable relates to the component lifecycle.

**Pure composables** (no lifecycle hooks) — call them as plain functions:

```ts
import { usePagination } from "../usePagination";

it("clamps the page to the last available page", () => {
  const { currentPage, goToPage } = usePagination({ totalItems: 30, pageSize: 10 });
  goToPage(99);
  expect(currentPage.value).toBe(3);
});
```

**Lifecycle-bound composables** (`onMounted`, `provide`, `watch` needing a scope) — run them inside a host so the lifecycle actually fires:

```ts
import { render } from "@testing-library/vue";
import { defineComponent, h } from "vue";

function renderComposable<ReturnValue>(composable: () => ReturnValue) {
  let result!: ReturnValue;
  const HostComponent = defineComponent({
    setup() {
      result = composable();
      return () => h("div");
    },
  });
  render(HostComponent);
  return result;
}
```

One composable, one concern, one test file — never a combined test for a `useUserFormTable`-style grab-bag, because the composable itself should not exist (see `frontend-vue-code-style`).

## Convention 6: Pinia — isolate stores, fake them in component tests

**Store logic tests** — fresh Pinia per test so state never leaks between cases:

```ts
import { setActivePinia, createPinia } from "pinia";
import { beforeEach, it, expect } from "vitest";
import { useBackupStore } from "../backupStore";

beforeEach(() => setActivePinia(createPinia()));

it("marks the backup as failed and records the error", () => {
  const backupStore = useBackupStore();
  backupStore.recordFailure("backup-7", "disk full");
  expect(backupStore.statusOf("backup-7")).toBe("failed");
});
```

**Component tests that depend on a store** — mount with a controllable testing Pinia rather than driving real store logic:

```ts
import { render } from "@testing-library/vue";
import { createTestingPinia } from "@pinia/testing";

render(BackupList, {
  global: {
    plugins: [createTestingPinia({ initialState: { backup: { items: [makeBackup()] } } })],
  },
});
```

## Convention 7: Mock at the network boundary with MSW (CRITICAL)

Fake HTTP at the network layer, not at your API module. Define request handlers once; reuse them across unit, component, and E2E tiers. Override per-test for error and edge cases.

```ts
import { http, HttpResponse } from "msw";
import { mswServer } from "@/test/msw/server";

it("shows an error banner when the jobs request fails", async () => {
  mswServer.use(
    http.get("/api/jobs/:jobId", () => new HttpResponse(null, { status: 500 })),
  );

  render(JobDetailPage, { props: { jobId: "job-1" } });

  expect(await screen.findByRole("alert")).toHaveTextContent(/could not load/i);
});
```

**Reserve `vi.mock` for non-network modules only** — clocks (`vi.useFakeTimers`), `crypto`/`uuid`, and third-party SDKs. Do **not** `vi.mock` your own API layer: that couples every test to the module's shape, so an internal refactor of the API client breaks tests that never changed behavior. Mocking the network instead of the module is what keeps the same fixtures usable from unit tests up to Playwright.

## Convention 8: E2E with Playwright — critical journeys only

E2E is slow and flake-prone, so spend it only on journeys that must never break (login, the primary create/read flow). Select by role or `data-testid`, never by CSS class or visible copy that marketing might change. Run against a seeded or MSW-mocked backend for determinism.

```ts
// e2e/login.spec.ts
import { test, expect } from "@playwright/test";

test("a user logs in and lands on the dashboard", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("operator@example.com");
  await page.getByLabel("Password").fill("correct-horse");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
});
```

E2E lives in a top-level `e2e/` directory, separate from co-located unit/component tests, with its own `playwright.config.ts`.

## Convention 9: File layout, naming, and structure

- **Co-locate** unit and component tests next to the source in a `__tests__/` folder (`features/jobs/components/__tests__/JobCard.test.ts`). E2E lives in top-level `e2e/`.
- **Name** test files `*.test.ts`. Pick one extension and never mix `*.spec.ts` in.
- **Structure** each test as Arrange–Act–Assert. One `describe` per unit; phrase each `it` as an observable behavior:

```ts
describe("JobCard", () => {
  it("shows a progress bar while the job is running", () => { /* ... */ });
  it("emits retry when the user clicks Retry on a failed job", () => { /* ... */ });
});
```

- **Factories over inline literals.** Build test data with a `makeJob(overrides)`-style factory in `src/test/factories/` so a schema change touches one place, and each test overrides only the field it cares about.

## Convention 10: Coverage is a signal, not a target

Track coverage (`test:coverage`) and run the suite in CI as a merge gate. Read coverage to find untested critical paths — not to chase a percentage. Do not write assertion-free tests, snapshot-everything tests, or tests of trivial getters just to move the number. A meaningful test of a critical path is worth more than 5% of line coverage on glue code.

## Convention 11: Descriptive naming in tests (CRITICAL)

Tests are read far more than they are written, and they document the behavior they assert. Apply the same naming rule as production code: **no single-letter variables and no abbreviations**, anywhere — including callback and loop parameters.

```ts
// ❌
const w = render(JobCard, { props: { j } });
jobs.filter(j => j.status === "failed");

// ✅
const failedJobs = jobs.filter(job => job.status === "failed");
render(JobCard, { props: { job: failedJob } });
```

## Convention 12: One behavior per test (SoC/SRP)

Each test verifies exactly one behavior and has exactly one reason to fail. Do not bundle "renders, then clicks, then emits, then re-renders" into a single `it` — when it fails you will not know which behavior broke. Separation of concerns and single responsibility apply to tests as strictly as to the code under test: a test that asserts three unrelated things is three tests wearing one name. Split it.

```ts
// ❌ One test, three reasons to fail
it("works", async () => {
  render(ConfirmDialog, { props: { recordId: "backup-7" } });
  expect(screen.getByRole("heading")).toBeInTheDocument();
  await fireEvent.click(screen.getByRole("button", { name: /confirm/i }));
  expect(emitted()).toHaveProperty("confirm");
  await fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
  expect(emitted()).toHaveProperty("cancel");
});

// ✅ Three tests, each naming one behavior (see Convention 9)
```

## Quick reference

| Task | Do this |
|------|---------|
| Render a component | `render(Component, { props })` from `@testing-library/vue` |
| Find an element | `getByRole` → `getByLabelText` → `getByText` → `getByTestId` |
| Click / type | `await fireEvent.click(...)` / `await fireEvent.update(input, "text")` |
| Assert an emit | `expect(emitted().eventName[0]).toEqual([payload])` |
| Fake an API response | MSW handler (default in `handlers.ts`, override with `mswServer.use(...)`) |
| Fake a clock / uuid / SDK | `vi.useFakeTimers()` / `vi.mock(...)` — non-network only |
| Pure composable | Call it directly, assert returned refs |
| Lifecycle composable | Run it inside a host component |
| Store logic | `setActivePinia(createPinia())` per test |
| Store in a component | `createTestingPinia({ initialState })` |
| Critical user journey | Playwright spec in `e2e/` |

## Common mistakes

| Mistake | Fix |
|---------|-----|
| Asserting on `wrapper.vm.*` internals | Assert on rendered output and emitted events (Convention 1) |
| `find(".some-class")` / `find("div")` | Query by role/text; `data-testid` only as a last resort (Convention 2) |
| `shallowMount` everywhere | `render` with real children; stub only the genuinely external (Convention 3) |
| `vi.mock("../api/...")` for your own API | Mock the network with MSW; share handlers across tiers (Convention 7) |
| Forgetting `await` on an interaction | `await fireEvent.*` — Vue updates the DOM on the next tick (Convention 4) |
| Snapshotting whole components | Assert specific behavior; snapshots rot and get rubber-stamped |
| E2E for what a component test covers | Drop to a component test; reserve E2E for journeys (Convention 8) |
| One giant `it("works")` | One behavior per test (Convention 12) |
| State leaking between tests | Fresh Pinia per test; `cleanup()` and `resetHandlers()` in setup |
| Chasing a coverage percentage | Coverage is a signal; test critical paths, not getters (Convention 10) |
