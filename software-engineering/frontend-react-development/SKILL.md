---
name: frontend-react-development
description: Use when deciding where code lives in a React 19 SPA (a feature, a shared domain module, or the shared foundation), scaffolding a new React project's Vite, compiler, and lint setup, or building UI that must look polished, be accessible, and be responsive. Code-level patterns for components, hooks, stores, and types are frontend-react-code-style.
vibe: Builds responsive, accessible web apps with pixel-perfect precision.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.2"
---

# React Frontend Development

This is the React sibling of `frontend-vue-development`; it follows the same rules and structure with React vocabulary and the React stack from `frontend-react-code-style` (React 19.2+, React Compiler, TanStack Router, TanStack Query, Zustand).

## 🚨 Critical Rules

### Design-First, Then Functionality, Then Performance
- **First priority — Visual appeal**: The UI must be attractive and pleasant to look at. Invest in polished layouts, typography, spacing, color, and micro-interactions before optimizing anything
- **Second priority — Correctness**: The application must work reliably — correct data flow, proper error states, and solid functionality
- **Third priority — Performance**: Once it looks great and works correctly, optimize the experience with code splitting, lazy loading, caching, and Core Web Vitals tuning

### Descriptive Naming
- Never use single-letter variable names or abbreviations — every variable, parameter, and loop variable must be descriptive and intent-revealing
- Good names are searchable and self-documenting: `selectedBackup` not `sel`, `notification` not `n`, `backup` not `b`, `event` not `e`
- Loop/callback variables must match their collection: `backups.filter(backup => ...)` not `backups.filter(b => ...)`
- This applies everywhere: `.map()` renders in JSX, `.filter()`, `.find()`, `.reduce()`, event handlers, reducers, and all other contexts

### Separation of Concerns and Single Responsibility
- Every component, hook, and module must have exactly one reason to exist and one reason to change
- Prefer code duplication over premature abstraction — duplicate code with distinct responsibilities is clearer than a shared abstraction serving multiple concerns
- Split components by responsibility: a component that fetches data should not also render UI — extract data logic into custom hooks and keep components presentational; for pages, use a container/presenter split
- Keep hooks focused: one hook per concern (e.g., `useUserAuth`, `useFormValidation`, `useTableSort` — never a combined `useUserFormTable`)
- Separate API calls, state management, business logic, and presentation into distinct layers — do not mix them within a single file or function
- When in doubt, split further rather than merging — the cost of an extra file is lower than the cost of tangled responsibilities

### Accessibility and Inclusive Design
- Follow WCAG 2.2 AA guidelines for accessibility compliance
- Implement proper ARIA labels and semantic HTML structure — reach for the semantic element before adding roles to a `div`
- Ensure keyboard navigation and screen reader compatibility
- Lint it from day one: `eslint-plugin-jsx-a11y` catches missing labels, bad roles, and unkeyboardable handlers at build time

## 📋 Reference Component

### Modern React Component Example
```tsx
// Modern React 19 component — generic, virtualized, keyboard- and screen-reader-accessible.
// The utility classes are Tailwind CSS; nothing in the pattern depends on it.
import { useRef, type ReactNode } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'

interface Column<TRow> {
  key: string
  label: string
  renderCell: (row: TRow) => ReactNode
}

interface VirtualizedTableProps<TRow extends { id: string }> {
  rows: TRow[]
  columns: Column<TRow>[]
  onRowClick: (row: TRow) => void
}

export function VirtualizedTable<TRow extends { id: string }>({
  rows,
  columns,
  onRowClick,
}: VirtualizedTableProps<TRow>) {
  const scrollContainerRef = useRef<HTMLDivElement | null>(null)

  const rowVirtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollContainerRef.current,
    estimateSize: () => 50,
    overscan: 5,
    getItemKey: index => rows[index].id,
  })

  return (
    <div
      ref={scrollContainerRef}
      className="h-96 overflow-auto"
      role="table"
      aria-label="Data table"
      aria-rowcount={rows.length + 1}
    >
      <div
        role="row"
        aria-rowindex={1}
        className="flex items-center sticky top-0 z-10 bg-white border-b font-medium"
      >
        {columns.map(column => (
          <div key={column.key} role="columnheader" className="px-4 py-2 flex-1">
            {column.label}
          </div>
        ))}
      </div>
      <div role="rowgroup" style={{ height: `${rowVirtualizer.getTotalSize()}px`, position: 'relative' }}>
        {rowVirtualizer.getVirtualItems().map(virtualRow => {
          const row = rows[virtualRow.index]
          return (
            <div
              key={virtualRow.key}
              role="row"
              aria-rowindex={virtualRow.index + 2}
              tabIndex={0}
              className="flex items-center border-b hover:bg-gray-50 cursor-pointer"
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${virtualRow.size}px`,
                transform: `translateY(${virtualRow.start}px)`,
              }}
              onClick={() => onRowClick(row)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  onRowClick(row)
                }
              }}
            >
              {columns.map(column => (
                <div key={column.key} role="cell" className="px-4 py-2 flex-1">
                  {column.renderCell(row)}
                </div>
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

Note the choices a less careful version gets wrong: the component is generic (`TRow`, no `any`), rows are keyed by stable `id` via `getItemKey` (never by array index), rows are keyboard-actionable (`tabIndex`, Enter handling), the sticky header carries a z-index so scrolling rows can't paint over it, and the markup carries full table semantics for screen readers — including `aria-rowcount`/`aria-rowindex`, which virtualized tables specifically require because most rows are absent from the DOM. Divs with ARIA roles are used because virtualization's absolute positioning breaks native `<table>` layout. Whole-row activation is the edge of what `role="table"` can carry; the moment interaction goes beyond it (cell focus, arrow-key navigation), escalate to the ARIA grid pattern (`role="grid"`, `role="gridcell"`) with managed focus.

## 🗂️ Project Structure

Organize by **feature** (domain), not by file type. Each feature is a self-contained module with its own components, hooks, API layer, and types. Shared code lives in `shared/`, which holds two distinct kinds of code that must not be mixed: a **generic foundation** (domain-agnostic primitives — `BaseButton`, `useDebounce`, the HTTP client) and **shared domain modules** under `shared/domains/` (business concepts reused by 2+ features — e.g. `connectivity-health`, `jobs`). If code is specific to one feature, it belongs in that feature's folder, not in `shared/`.

```
src/
├── app/                        # App shell — bootstrap and wiring only
│   ├── App.tsx
│   ├── main.tsx
│   └── providers/              # QueryClientProvider, theme, error boundary wiring
│
├── routes/                     # TanStack Router file-based route tree (routesDirectory)
│   ├── __root.tsx              #   thin files only: mount a feature's page component,
│   ├── index.tsx               #   wire loader/validateSearch — no business logic here
│   └── backups.$backupId.tsx
│
├── features/                   # Feature modules (one folder per domain)
│   ├── auth/
│   │   ├── components/         # Auth-specific components (LoginForm, LoginPage, etc.)
│   │   ├── hooks/              # Auth-specific logic (useAuth, useSession)
│   │   ├── api/                # Auth API calls + query-key/queryOptions factories
│   │   ├── stores/             # Auth Zustand store
│   │   ├── types/              # Auth-specific TypeScript types
│   │   └── index.ts            # Public API — only export what other features may use
│   ├── dashboard/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── api/
│   │   ├── stores/
│   │   └── types/
│   └── settings/
│       └── ...
│
├── shared/                     # Reusable across features — two distinct tiers
│   ├── domains/                # Shared domain modules — business concepts used by 2+ features
│   │   ├── connectivity-health/#   owns no routes; shaped like a feature (components, hooks, types)
│   │   └── jobs/               #   imported by features, never imports from them
│   ├── components/             # Generic foundation: design system primitives (BaseButton, BaseModal)
│   ├── hooks/                  # Generic hooks (useDebounce, useMediaQuery, usePagination)
│   ├── api/                    # HTTP client setup, interceptors, QueryClient configuration
│   ├── utils/                  # Pure functions (formatDate, slugify)
│   └── types/                  # Shared TypeScript types and interfaces
│
├── assets/                     # Static assets (images, fonts, icons)
└── styles/                     # Global styles, CSS variables, theme tokens
```

**Rules:**
- Features never import from other features directly — if the shared code is generic, lift it to the `shared/` foundation; if it's a business concept reused by 2+ features, lift it to a module under `shared/domains/`
- Dependency direction is one-way: `features/` → `shared/domains/` → `shared/` foundation. A `shared/domains/` module may be imported by any feature but must never import from `features/` (that would re-couple features through the back door)
- A shared domain module is *not* a feature: it owns no routes or pages. If it needs a route, it is a feature and belongs in `features/`
- Each feature's (and shared domain module's) `index.ts` is its public API — internal files are private by convention
- A component in `shared/components/` must be domain-agnostic (e.g., `BaseButton` yes, `UserAvatar` no); anything domain-specific goes in a feature or a `shared/domains/` module
- Route files in `routes/` stay thin: mount a page component exported from a feature — or define only a trivial local wrapper that reads params/search and mounts it — and wire the loader and `validateSearch`, nothing else; real page components live in their feature, not in `routes/`
- API calls live in `api/` folders, never inline in components or stores
- One store file per concern, matching the feature or domain-module boundary
- Enforce the dependency direction with the linter so violations fail the build instead of surviving review: an inline flat-config plugin as `frontend-vue-eslint-setup` builds it (the layer rules are framework-agnostic — port them), with `eslint-plugin-boundaries` only at a scale where the inline rules stop being enough

## 🔄 Workflow

### Step 1: Project Setup and Architecture
- Scaffold with Vite (`npm create vite@latest my-app -- --template react-ts`) — leverage HMR for instant feedback during development
- Configure Vite plugins: `tanstackRouter({ target: 'react', autoCodeSplitting: true })` **before** `@vitejs/plugin-react`, then enable the React Compiler. Since `@vitejs/plugin-react` v6 dropped its Babel pipeline, the compiler wires through `@rolldown/plugin-babel` — install `@rolldown/plugin-babel`, `@babel/core`, and `babel-plugin-react-compiler` (plus `@types/babel__core`), then:

```ts
// vite.config.ts
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
})
```

`@vitejs/plugin-react` also ships a native `compiler: true` option backed by `oxc-transform-react`, a Rust port of the compiler; it is marked experimental, so stay on the Babel wiring above until that label is gone.

- Set up the lint gate as flat config: typescript-eslint `strictTypeChecked`, `eslint-plugin-react-hooks` (v7 `recommended` — includes the compiler-powered Rules of React), and `eslint-plugin-jsx-a11y` (`flatConfigs.recommended`)
- Set up Vitest for unit tests and Playwright for e2e, integrated into CI; add `@tanstack/react-query-devtools` and `@tanstack/react-router-devtools` as dev dependencies
- Establish component architecture and design system foundation

### Step 2: Component Development
- Design components with single responsibility — each component does one thing well, with data fetching and presentation separated as the SoC rule above says
- Implement responsive design with a mobile-first approach
- Build accessibility into components from the start; respect `prefers-reduced-motion`, `prefers-contrast`, and `prefers-color-scheme`
- Reach for React 19's concurrent primitives where they fit: Suspense through TanStack Query's `useSuspenseQuery`, `useTransition` / `useDeferredValue` for non-urgent updates, and Actions (`useActionState`, `useOptimistic`) for form submission and optimistic UI

### Step 3: Performance Optimization
- Code splitting and memoization are already decided: routes split through `autoCodeSplitting` and the React Compiler memoizes (`frontend-react-code-style` Patterns 10 and 4). Add `React.lazy` only for heavy below-the-fold widgets (charts, editors)
- Virtualize long lists (`@tanstack/react-virtual`) instead of rendering thousands of rows
- Optimize images and assets for web delivery
- Monitor Core Web Vitals; set performance budgets and keep them monitored

### Step 4: Testing and Quality Assurance
- Tooling, the pyramid, network mocking, and the accessibility assertions (`axe-core` under Vitest, `@axe-core/playwright` in e2e) are defined in `frontend-react-testing` — follow it rather than restating it here
- Test cross-browser compatibility and responsive behavior
- Cover the critical user flows end to end
