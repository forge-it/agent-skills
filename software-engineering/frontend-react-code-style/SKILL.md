---
name: frontend-react-code-style
description: Patterns and conventions for writing clean, maintainable React 19 applications. Use when writing or reviewing React components, custom hooks, stores, or project structure — enforces consistent data flow, component design, and type safety across the codebase.
vibe: Keeps React codebases predictable, traceable, and free of spaghetti.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.1"
---

# React Code Style — Patterns & Conventions

A living collection of patterns that every component, hook, and store in this codebase must follow. When in doubt, check here first.

This is the React sibling of `frontend-vue-code-style`; Patterns 1–12 cover the same concerns under the same numbers, Patterns 13–14 are React-specific.

**Stack assumptions:** React 19.2+ with function components only, TypeScript in strict mode with typescript-eslint `strictTypeChecked` and `eslint-plugin-react-hooks` v7+, Vite SPA (no SSR framework), TanStack Query for server state, Zustand for global client state, TanStack Router for routing, React Compiler enabled. Where a different stack choice changes a rule, the pattern names the fallback.

---

## Pattern 1: Props Down, Callbacks Up (One-Way Data Flow)

**Why:** React's own Rules state that props and state are immutable snapshots of a single render. A child that mutates what it received desynchronizes the UI from React's model, and nobody can trace where a change came from.

**Rule:** A child component never modifies data it receives. It declares what it accepts via a typed props interface, and reports user actions via callback props. The parent owns the state and decides what to do. Callback props are named `onX`; handler functions defined in a component are named `handleX` — passing an existing hook or store action directly (`onDelete={deleteBackup}`) is fine, don't wrap it in a pointless `handleX`. Name the props type `<Component>Props` and destructure it in the signature. Never use `React.FC`.

```tsx
// ✅ CORRECT — child reports, parent decides
// BackupRow.tsx
interface BackupRowProps {
  id: string
  name: string
  status: 'active' | 'archived' | 'failed'
  onArchive: (id: string) => void
  onDelete: (id: string) => void
}

export function BackupRow({ id, name, status, onArchive, onDelete }: BackupRowProps) {
  return (
    <tr>
      <td>{name}</td>
      <td>{status}</td>
      <td>
        <button onClick={() => onArchive(id)}>Archive</button>
        <button onClick={() => onDelete(id)}>Delete</button>
      </td>
    </tr>
  )
}
```

```tsx
// ❌ WRONG — child mutates the prop object
interface BackupRowProps {
  backup: Backup
}

function BackupRow({ backup }: BackupRowProps) {
  function handleDelete() {
    backup.status = 'deleted'  // NEVER DO THIS — props are read-only snapshots
  }
}
```

The same immutability applies to your own state — update it by giving the setter a new object or array, never by mutating in place:

```tsx
// ❌ WRONG — mutates in place; React never sees the change
backups.push(newBackup)
setBackups(backups)

// ✅ CORRECT — replace with a new array
setBackups([...backups, newBackup])
```

---

## Pattern 2: Logic in Hooks, Rendering in Components

**Why:** Without it, components grow into god-files that fetch data, transform it, handle errors, and render 200 lines of JSX. Reuse and testing become impossible.

**Rule:** When a component mixes data logic with rendering, extract the logic into custom hooks. For a page or feature, split the files: the container component wires hooks together and passes their output to the presenter via props. The presenter handles display (JSX, styles, user interaction) — zero data fetching, zero business logic. The container should have almost no inline logic; if it does, extract it into a hook.

The classic container/presenter file split is no longer React dogma (its own author retracted it after hooks) — custom hooks are the primary separation mechanism. In this codebase we keep the file split for pages and data-heavy features because it keeps presenters testable without providers; skip it where a single hook extraction already leaves the component purely presentational.

```tsx
// ✅ Container — wires hooks to the presenter, almost no code
// BackupListContainer.tsx
import { BackupListPresenter } from './BackupListPresenter'
import { useBackups } from './hooks/useBackups'
import { useBackupSearch } from './hooks/useBackupSearch'

export function BackupListContainer() {
  const { backups, isLoading, error, refetchBackups, deleteBackup } = useBackups()
  const { searchQuery, setSearchQuery, showArchived, setShowArchived, filteredBackups } =
    useBackupSearch(backups)

  return (
    <BackupListPresenter
      backups={filteredBackups}
      isLoading={isLoading}
      error={error}
      searchQuery={searchQuery}
      onSearchQueryChange={setSearchQuery}
      showArchived={showArchived}
      onShowArchivedChange={setShowArchived}
      onDelete={deleteBackup}
      onRetry={refetchBackups}
    />
  )
}
```

```tsx
// ✅ Presenter — pure rendering, no data logic
// BackupListPresenter.tsx
import type { Backup } from './types'

interface BackupListPresenterProps {
  backups: Backup[]
  isLoading: boolean
  error: string | null
  searchQuery: string
  onSearchQueryChange: (searchQuery: string) => void
  showArchived: boolean
  onShowArchivedChange: (showArchived: boolean) => void
  onDelete: (id: string) => void
  onRetry: () => void
}

export function BackupListPresenter({
  backups,
  isLoading,
  error,
  searchQuery,
  onSearchQueryChange,
  showArchived,
  onShowArchivedChange,
  onDelete,
  onRetry,
}: BackupListPresenterProps) {
  if (isLoading) {
    return <p>Loading…</p>
  }

  if (error) {
    return (
      <div>
        <p>{error}</p>
        <button onClick={onRetry}>Retry</button>
      </div>
    )
  }

  return (
    <div>
      <input
        value={searchQuery}
        onChange={(event) => onSearchQueryChange(event.target.value)}
        placeholder="Search…"
      />
      <label>
        <input
          type="checkbox"
          checked={showArchived}
          onChange={(event) => onShowArchivedChange(event.target.checked)}
        />
        Show archived
      </label>
      <table>
        <tbody>
          {backups.map(backup => (
            <tr key={backup.id}>
              <td>{backup.name}</td>
              <td>
                <button onClick={() => onDelete(backup.id)}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

```tsx
// ❌ WRONG — fetching, filtering, and rendering tangled in one component
export function BackupList() {
  const [backups, setBackups] = useState<Backup[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setIsLoading(true)
    fetch('/api/backups')
      .then(response => response.json())
      .then(setBackups)
      .catch(() => setError('Failed'))
      .finally(() => setIsLoading(false))
  }, [])

  const filtered = backups.filter(/* ... */)

  return /* 150 lines of JSX */
}
```

**When to skip:** Small components with minimal logic (a badge, a button, a tooltip) don't need splitting. Apply this when a component starts mixing fetch/state logic with rendering.

---

## Pattern 3: Typed Context — Provider Component + Throwing Hook

**Why:** Without it, you either prop-drill through layers of components that don't care about the data, or use a context with a made-up default value that silently masks a missing provider.

**Rule:** Create contexts as `createContext<T | null>(null)` and never export the raw context. Export exactly two things: a provider component and a `useX()` hook that throws when called outside the provider — consumers never see `null` and never type-assert. Never invent a plausible default value; the default is only reachable when someone forgot the provider, and that must crash loudly.

```tsx
// ✅ src/features/auth/AuthContext.tsx — typed, throwing hook, raw context stays private
import { createContext, use, useState, type ReactNode } from 'react'

export type UserRole = 'admin' | 'viewer' | 'editor'

interface AuthValue {
  userRole: UserRole
  setUserRole: (userRole: UserRole) => void
}

const AuthContext = createContext<AuthValue | null>(null)

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [userRole, setUserRole] = useState<UserRole>('viewer')
  return <AuthContext value={{ userRole, setUserRole }}>{children}</AuthContext>
}

export function useAuth(): AuthValue {
  const auth = use(AuthContext)
  if (!auth) {
    throw new Error('useAuth must be used inside <AuthProvider>')
  }
  return auth
}
```

```tsx
// ✅ Consumer — anywhere deeper, no prop drilling
function DeleteServerButton() {
  const { userRole } = useAuth()
  if (userRole !== 'admin') {
    return null
  }
  return <button>Delete Server</button>
}
```

```tsx
// ❌ WRONG — fake default; a missing provider becomes a silent bug instead of a crash
const AuthContext = createContext<AuthValue>({ userRole: 'viewer', setUserRole: () => {} })

// ❌ WRONG — exporting the raw context invites unguarded use(AuthContext) everywhere
export const AuthContext = createContext<AuthValue | null>(null)

// ❌ WRONG — legacy provider form; React 19 renders the context directly
<AuthContext.Provider value={value}>{children}</AuthContext.Provider>
```

Every consumer re-renders when the context value's identity changes. Without the React Compiler, wrap the `value` object in `useMemo`; with the compiler (our default) that is handled for you. For reducer-backed contexts, split state and dispatch into two contexts so dispatch-only consumers never re-render on state changes.

**When to use:** Low-frequency, dependency-injection-shaped values needed 3+ levels deep — theme, auth/current user, locale, feature flags. For direct parent-child, use props. For high-frequency or cross-feature mutable state, use a Zustand store (Pattern 7) — context has no selector granularity.

---

## Pattern 4: Custom Hook Design Rules

**Why:** Custom hooks are the primary way to organize and reuse logic in React. Without clear conventions, they become tangled, untestable, and leak resources.

**Rule:** Every custom hook follows these five constraints:

1. **Single responsibility** — one hook, one concern.
2. **Honest naming** — name it `useX` only if it calls other hooks. A helper that calls no hooks is a plain function with a plain name (`getSortedBackups`, not `useSortedBackups`), because plain functions may be called conditionally and hooks may not.
3. **Top-level invocation only** — call hooks at the top level of a component or another hook. Never inside conditions, loops, nested callbacks, or after an early return (exception: `use`, which React permits inside conditionals and loops).
4. **Cleanup mirrors setup** — every effect that creates a timer, listener, subscription, or connection returns a cleanup that undoes it. A bug that only appears under StrictMode's double-invoke is a real missing-cleanup bug, not noise.
5. **Object return shape** — return a plain object with named properties. A tuple is acceptable only for a `useState`-like pair of exactly two values that callers are expected to rename.

```tsx
// ✅ CORRECT — focused, object return, derives during render
import { useState } from 'react'
import { BACKUP_STATUS_ARCHIVED } from '../constants'
import type { Backup } from '../types'

export function useBackupSearch(backups: Backup[]) {
  const [searchQuery, setSearchQuery] = useState('')
  const [showArchived, setShowArchived] = useState(false)

  const filteredBackups = backups.filter(backup => {
    const matchesSearch = backup.name
      .toLowerCase()
      .includes(searchQuery.toLowerCase())
    const matchesStatus = showArchived || backup.status !== BACKUP_STATUS_ARCHIVED
    return matchesSearch && matchesStatus
  })

  return { searchQuery, setSearchQuery, showArchived, setShowArchived, filteredBackups }
}
```

```tsx
// ✅ CORRECT — cleanup mirrors setup, stale responses ignored
// (illustrates cleanup discipline; for real server data prefer TanStack Query's
// refetchInterval — see Pattern 14)
import { useEffect, useState } from 'react'
import { fetchServerHealth, type ServerHealth } from '../api/serverHealthApi'

const POLLING_INTERVAL_MS = 30_000

export function useServerHealth(url: string) {
  const [health, setHealth] = useState<ServerHealth | null>(null)

  useEffect(() => {
    let ignore = false

    async function poll() {
      try {
        const nextHealth = await fetchServerHealth(url)
        if (!ignore) {
          setHealth(nextHealth)
        }
      } catch {
        // keep the last known health; the next tick retries
      }
    }

    void poll()
    const timerId = window.setInterval(() => void poll(), POLLING_INTERVAL_MS)

    return () => {
      ignore = true
      clearInterval(timerId)
    }
  }, [url])

  return { health }
}
```

```tsx
// ❌ WRONG — god hook, array return, no cleanup
export function useBackupManager() {
  // fetching + filtering + sorting + pagination + bulk selection
  // all in one hook = untestable, unreusable
  return [data, isLoading, error, filtered, sorted, page]  // positional = fragile
}
```

```tsx
// ❌ WRONG — hook called conditionally / inside a callback
if (isAdmin) {
  const { backups } = useBackups()  // breaks the Rules of Hooks
}

useEffect(() => {
  const { backups } = useBackups()  // hooks cannot run inside effects
}, [])
```

**Memoization:** with the React Compiler enabled (our default), do not wrap returned functions in `useCallback` or derivations in `useMemo` for referential identity — the compiler does it. Without the compiler, memoize a returned function only when it feeds an effect dependency or a `React.memo` child. Never build generic lifecycle wrappers (`useMount`, `useUpdateEffect`) — they discard dependency tracking; extract specific, intentional hooks instead.

---

## Pattern 5: Hooks Share Logic, Not State

**Why:** In React, every call of a custom hook gets its own independent state — always. Coming from Vue, the module-level-singleton composable habit produces silent bugs here: a module-level variable can be mutated, but no component ever re-renders to show it.

**Rule:** Never store shared mutable state in a module-level variable that components read during render. To deliberately share state, pick by scope: lift it to the closest common parent and pass it down (the default), put it in a typed context for low-frequency values (Pattern 3), or put it in a Zustand store for cross-feature client state (Pattern 7). A store is also the right home for the Vue-style "shared composable state" middle ground — notifications, a "currently editing" flag, a multi-step wizard's position.

```tsx
// ❌ WRONG — module-level variable; mutation notifies nobody, UI goes stale
const notifications: ToastNotification[] = []

export function useNotifications() {
  return {
    notifications,
    notify: (message: string) => {
      notifications.push({ id: crypto.randomUUID(), message })  // no component re-renders
    },
  }
}
```

```tsx
// ✅ CORRECT — per-component state; each caller gets an independent copy
import { useState } from 'react'

export function useDisclosure() {
  const [isOpen, setIsOpen] = useState(false)

  return {
    isOpen,
    open: () => setIsOpen(true),
    close: () => setIsOpen(false),
    toggle: () => setIsOpen(previousIsOpen => !previousIsOpen),
  }
}
```

```tsx
// ✅ CORRECT — deliberately shared state lives in a store that notifies subscribers
import { create } from 'zustand'

interface ToastNotification {
  id: string
  message: string
}

interface NotificationsState {
  notifications: ToastNotification[]
  notify: (message: string) => void
  dismiss: (id: string) => void
}

export const useNotificationsStore = create<NotificationsState>()(set => ({
  notifications: [],
  notify: message =>
    set(state => ({
      notifications: [...state.notifications, { id: crypto.randomUUID(), message }],
    })),
  dismiss: id =>
    set(state => ({
      notifications: state.notifications.filter(notification => notification.id !== id),
    })),
}))
```

Wrapping a genuinely external mutable source (a browser API, a non-React library) is the job of `useSyncExternalStore`, not an effect — and its `getSnapshot` must return a cached reference, never a fresh object, or you get an infinite render loop.

---

## Pattern 6: Descriptive Naming (CRITICAL)

**Why:** Single-letter variables and abbreviations force readers to mentally decode what a name represents. They destroy searchability, make code reviews harder, and turn simple debugging into a guessing game.

**Rule:** Never use single-letter variable names or abbreviations. Every variable, parameter, loop variable, and callback parameter must be a descriptive, intent-revealing name. The collection variable and the loop/callback variable must be consistent — the collection is the plural form, the loop variable is the singular.

```tsx
// ✅ CORRECT — descriptive, searchable, consistent
{backups.map(backup => (
  <tr key={backup.id}>
    <td>{backup.name}</td>
    <td>{backup.status}</td>
  </tr>
))}

// ❌ WRONG — single-letter callback parameter
{backups.map(b => (
  <tr key={b.id}>
    <td>{b.name}</td>
  </tr>
))}
```

```tsx
// ✅ CORRECT — callback and event parameters are descriptive
backups.filter(backup => backup.status !== 'archived')
notifications.filter(notification => notification.id !== id)
<input onChange={(event) => setSearchQuery(event.target.value)} />

// ❌ WRONG — single-letter or abbreviated parameters
backups.filter(b => b.status !== 'archived')
notifications.filter(n => n.id !== id)
<input onChange={(e) => setSearchQuery(e.target.value)} />
```

```tsx
// ✅ CORRECT — descriptive state names, boolean reads as a question
const [searchQuery, setSearchQuery] = useState('')
const [selectedBackupId, setSelectedBackupId] = useState<string | null>(null)
const [isLoading, setIsLoading] = useState(false)

// ❌ WRONG — abbreviated or vague names
const [sq, setSq] = useState('')
const [selId, setSelId] = useState<string | null>(null)
const [loading, setLoading] = useState(false)  // "loading" is ambiguous — loading what?
```

**Rationale:** This rule applies everywhere: JSX `.map()` renders, `.filter()`, `.find()`, `.reduce()`, `.forEach()`, event handlers, reducers, and any other context where a variable is introduced. No exceptions.

---

## Pattern 7: Store Scope and Boundaries

**Why:** Global stores are easy to overuse. Without strict boundaries, teams end up with god-stores that mix auth, server data, UI flags, filters, and view-specific logic in one blob. That destroys traceability, creates accidental coupling between features, and makes it unclear whether state belongs in props, a hook, or a store.

**Rule:** Zustand stores hold **client** state only — server data lives in the TanStack Query cache and is never copied into a store (Pattern 14). Use one store per feature domain, never one app-wide god-store. Reach for a store only when state must be shared across unrelated parts of the app or survive route navigation. Actions live inside the store, so components never hold update logic. Components subscribe with narrow selectors — one value per selector; selecting an object requires `useShallow`. Never subscribe to the whole store.

```tsx
// ✅ CORRECT — one store per domain, client state only, actions colocated
// src/features/backups/stores/useBackupUiStore.ts
import { create } from 'zustand'

type BackupViewMode = 'table' | 'grid'

interface BackupUiState {
  selectedBackupIds: string[]
  viewMode: BackupViewMode
  selectBackup: (id: string) => void
  clearSelection: () => void
  setViewMode: (viewMode: BackupViewMode) => void
}

export const useBackupUiStore = create<BackupUiState>()(set => ({
  selectedBackupIds: [],
  viewMode: 'table',
  selectBackup: id =>
    set(state => ({ selectedBackupIds: [...state.selectedBackupIds, id] })),
  clearSelection: () => set({ selectedBackupIds: [] }),
  setViewMode: viewMode => set({ viewMode }),
}))
```

```tsx
// ✅ CORRECT — narrow selectors; component re-renders only when its slice changes
const viewMode = useBackupUiStore(state => state.viewMode)
const setViewMode = useBackupUiStore(state => state.setViewMode)

// ✅ CORRECT — selecting multiple values as an object requires useShallow
import { useShallow } from 'zustand/react/shallow'

const { selectedBackupIds, clearSelection } = useBackupUiStore(
  useShallow(state => ({
    selectedBackupIds: state.selectedBackupIds,
    clearSelection: state.clearSelection,
  })),
)
```

```tsx
// ❌ WRONG — god-store mixing unrelated concerns
export const useAppStore = create<AppState>()(set => ({
  user: null,
  backups: [],
  servers: [],
  sidebarCollapsed: false,
  searchQuery: '',
}))

// ❌ WRONG — whole-store subscription; re-renders on every state change
const store = useBackupUiStore()

// ❌ WRONG — server data copied into a client store (see Pattern 14)
export const useBackupStore = create<BackupState>()(set => ({
  backups: [],
  fetchBackups: async () => {
    const response = await fetch('/api/backups')
    set({ backups: await response.json() })
  },
}))
```

**Decision rule:** If one component owns it, keep it local with `useState`. If a parent can pass it down, use props. If it's low-frequency and dependency-injection-shaped, use context (Pattern 3). Use a Zustand store only when the state is truly cross-feature, high-frequency shared, or must survive navigation. Note that once server state lives in the query cache, global client state is small — a handful of focused stores, not an architecture.

---

## Pattern 8: Persist Deliberately

**Why:** Persisting everything feels convenient until stale loading flags, old error messages, transient filters, or selection state survive a reload and confuse the user. Persistence is not a dumping ground for the whole store. It is an explicit durability decision.

**Rule:** Persist only state that must survive a page reload: remembered user preferences, UI settings, or similarly durable data. Never persist loading flags, error messages, transient search queries, temporary selections, server data, or anything that should reset naturally when the page is refreshed. `partialize` is an allowlist — name the persisted fields explicitly, never persist the whole store by default. Set `version` (with `migrate` when the shape changes) from day one. Auth tokens do not belong in `localStorage`: keep access tokens in memory and let the refresh token live in an `HttpOnly` cookie; persisting a token client-side is an explicit, documented exception, never a default.

```tsx
// ✅ CORRECT — durable preferences, allowlisted fields, versioned
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type ThemeName = 'light' | 'dark'

interface PreferencesState {
  theme: ThemeName
  sidebarCollapsed: boolean
  tablePageSize: number
  setTheme: (theme: ThemeName) => void
}

export const usePreferencesStore = create<PreferencesState>()(
  persist(
    set => ({
      theme: 'light',
      sidebarCollapsed: false,
      tablePageSize: 20,
      setTheme: theme => set({ theme }),
      // setSidebarCollapsed and setTablePageSize elided — actions stay in the store (Pattern 7)
    }),
    {
      name: 'preferences',
      version: 1,
      partialize: state => ({
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
        tablePageSize: state.tablePageSize,
      }),
    },
  ),
)
```

```tsx
// ❌ WRONG — persists transient state that should die on refresh
export const useBackupUiStore = create<BackupUiState>()(
  persist(
    set => ({
      selectedBackupIds: [],
      searchQuery: '',
      isDeleting: false,
      error: null,
    }),
    { name: 'backup-ui' },  // no partialize = everything persists, stuck spinners included
  ),
)
```

**Practical rule:** If you cannot clearly explain why a field should still exist after a full page reload, do not persist it.

---

## Pattern 9: No Duplicate Literals — Extract Constants (CRITICAL)

**Why:** Hardcoded string or number literals scattered across multiple files are invisible coupling. When the value changes, you have to find every copy — miss one and you have a silent bug. Constants give the value a name, a single source of truth, and make the intent searchable.

**Rule:** Any literal value (string, number, etc.) that appears in more than one place across the codebase **must** be extracted into a named constant. Define the constant once in the module that owns the concept, then import it everywhere else. Never duplicate the raw literal.

```tsx
// ✅ CORRECT — single source of truth in the feature that owns the concept
// src/features/backups/constants.ts
export const BACKUP_STATUS_ACTIVE = 'active' as const
export const BACKUP_STATUS_FAILED = 'failed' as const
export const BACKUP_STATUS_ARCHIVED = 'archived' as const

export const MAX_BACKUP_RETENTION_DAYS = 90

// src/features/backups/hooks/useBackupSearch.ts
import { BACKUP_STATUS_ARCHIVED } from '../constants'

const visibleBackups = backups.filter(backup => backup.status !== BACKUP_STATUS_ARCHIVED)
```

```tsx
// ❌ WRONG — same string hardcoded in multiple places
// hooks/useBackups.ts
backups.filter(backup => backup.status !== 'archived')

// hooks/useBackupSearch.ts
const matchesStatus = showArchived || backup.status !== 'archived'  // duplicate!

// components/BackupBadge.tsx
const badgeClass = status === 'archived' ? 'bg-gray-400' : 'bg-green-500'  // duplicate!
```

```tsx
// ❌ WRONG — same number used in multiple places without a name
setTimeout(poll, 30000)        // what does 30000 mean?
setTimeout(healthCheck, 30000) // is it intentionally the same?

// ✅ CORRECT — named constant, intent is clear
const POLLING_INTERVAL_MS = 30_000
setTimeout(poll, POLLING_INTERVAL_MS)
setTimeout(healthCheck, POLLING_INTERVAL_MS)
```

---

## Pattern 10: Route Organization — Typed Routes, Code Splitting, Validated Params

**Why:** Hand-built path strings like `navigate('/backups/' + id)` break silently when a route changes. Eagerly imported route components bloat the initial bundle. Untyped params and search params give you `unknown` (or worse, lying `string`) everywhere.

**Rule:** Routes are defined once, in the router; everything else navigates through the typed API. With TanStack Router (our default): no hardcoded path strings outside route definitions — `<Link to>` and `navigate({ to })` are type-checked against the route tree, so a renamed route fails the build. Enable the router plugin's `autoCodeSplitting` instead of hand-rolling `React.lazy` per route. Validate search params with a schema in `validateSearch` so they arrive typed. Read params through the route's own hooks (`Route.useParams()`, `Route.useSearch()`) — they stay in sync with the URL.

```tsx
// ✅ CORRECT — file-based route, typed params, search validated at the boundary
// src/routes/backups.$backupId.tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/backups/$backupId')({
  component: BackupDetailPage,
})

function BackupDetailPage() {
  const { backupId } = Route.useParams()  // typed string, updates with the URL
  return <BackupDetail backupId={backupId} />
}
```

```tsx
// ✅ CORRECT — typed navigation; a renamed or deleted route fails type-checking
import { Link, useNavigate } from '@tanstack/react-router'

<Link to="/backups/$backupId" params={{ backupId: backup.id }}>Details</Link>

const navigate = useNavigate()

async function handleOpenBackup(backup: Backup) {
  await navigate({ to: '/backups/$backupId', params: { backupId: backup.id } })
}
```

Under `strictTypeChecked`, a promise-returning handler cannot feed a void callback prop directly (`no-misused-promises`) — wrap it: `onClick={() => { void handleOpenBackup(backup) }}`. The same applies to hook actions passed as props: expose a `() => void` wrapper, not the raw promise-returning function.

```tsx
// ✅ CORRECT — search params validated once, typed everywhere
// src/routes/backups.index.tsx
export const Route = createFileRoute('/backups/')({
  validateSearch: search => backupListSearchSchema.parse(search),
  component: BackupListPage,
})
```

```tsx
// ❌ WRONG — hand-built path string; the type-checker rejects it under TanStack Router,
// and it breaks silently under untyped routers
navigate({ to: `/backups/${backup.id}` })
window.location.href = '/backups/' + backup.id

// ❌ WRONG — manual per-route React.lazy when autoCodeSplitting does it
const SettingsPage = React.lazy(() => import('./SettingsPage'))
```

**Fallback:** if a project uses React Router (data mode) instead, the same invariants hold by convention rather than by types: one central `paths.ts` module owns every path string and builder function, every route component is lazy-loaded, and no component ever concatenates a URL.

---

## Pattern 11: Component Body Organization

**Why:** Function components have no enforced internal ordering, so every file arranges its hooks, derived values, and handlers differently and readers can't predict where anything lives.

**Rule:** Order a component body top-to-bottom as: **hooks → derived values → event handlers → early returns → JSX**. The first zone is a hard rule from React itself — hooks must run before any early return. The rest is house convention: derive values during render right after the hooks, define handlers next, then one early return per visible state (loading, error, empty) instead of nested ternaries, then the happy-path JSX.

```tsx
// ✅ CORRECT
export function BackupList() {
  const { backups, isLoading, error } = useBackups()          // hooks first, always
  const [searchQuery, setSearchQuery] = useState('')

  const filteredBackups = backups.filter(backup =>            // derived during render
    backup.name.toLowerCase().includes(searchQuery.toLowerCase()),
  )

  function handleSearchChange(event: React.ChangeEvent<HTMLInputElement>) {
    setSearchQuery(event.target.value)
  }

  if (isLoading) {                                            // one early return per state
    return <Spinner />
  }
  if (error) {
    return <ErrorBanner error={error} />
  }

  return (
    <div>
      <input value={searchQuery} onChange={handleSearchChange} />
      <BackupTable backups={filteredBackups} />
    </div>
  )
}
```

**Subordinate to Patterns 2 and 4.** Ordering is layout, not cleanliness — a well-ordered god-component is still a god-component. Fix composition first, then order what remains. Skip for trivial components; apart from the hooks-first rule (which `eslint-plugin-react-hooks` enforces), this is a human convention, not a hard gate.

---

## Pattern 12: No `any` — Reach for a Real Type (CRITICAL)

**Why:** `any` switches off type-checking for everything it touches, and it spreads silently — one `any` and the compiler stops catching typos, missing fields, and renames downstream. In **tests** it is worse than in app code: a mock typed `any` makes a test pass against a shape that no longer matches reality, so the test keeps reporting green while testing nothing. A lying test is worse than no test.

**Rule:** Never write `any` — in app code or in tests. When you genuinely need to step outside the type system, use the narrowest, most explicit escape hatch instead, preferring earlier options:

1. A real type / interface (almost always possible)
2. `unknown` + a narrowing check (every network/JSON boundary is `unknown` until parsed)
3. `Partial<T>` for a partial mock
4. A typed mock factory that returns `T`
5. `as unknown as T` for a deliberate, greppable cast
6. `// @ts-expect-error` on the single line that feeds intentionally-invalid input

Testing is where `any` is most tempting; these cover the real cases without it:

| You reach for `any` because… | Use instead |
| --- | --- |
| Building a partial mock object | `Partial<User>`, or a typed factory `(overrides?: Partial<User>): User` |
| Forcing an incompatible shape | `as unknown as User` — explicit and searchable |
| Passing **invalid** input to test error handling | `// @ts-expect-error` on that one line (self-documenting; fails if the error disappears) |
| An untyped third-party test helper | `unknown` + narrow, or declare a minimal local type |

```tsx
// ✅ CORRECT — typed mock factory, no `any`
function makeUser(overrides: Partial<User> = {}): User {
  return { id: 'u-1', name: 'Ada', email: 'ada@example.com', ...overrides }
}

const user = makeUser({ name: 'Grace' })          // fully typed; a renamed field breaks the test loudly

// ✅ CORRECT — deliberate invalid input, scoped to one line
// @ts-expect-error — name is required; verifying the guard rejects it
expect(() => renderProfile({ email: 'x@y.z' })).toThrow()
```

```tsx
// ❌ WRONG — `any` mock; the test passes against a shape that no longer exists
const user: any = { nmae: 'Ada' }                 // typo + missing email, both invisible
renderProfile(user)
expect(screen.getByText('Ada')).toBeTruthy()       // green, but exercised nothing real

// ❌ WRONG — `any` to silence one incompatible field, disables checking for the whole object
const response = await fetchUser() as any

// ❌ WRONG — untyped event parameter
function handleChange(event: any) { /* ... */ }
// ✅ CORRECT
function handleChange(event: React.ChangeEvent<HTMLInputElement>) { /* ... */ }
```

**Enforcement:** `@typescript-eslint/no-explicit-any` at `error` in both app and test files, on top of the `strictTypeChecked` preset. The escape hatches above (`as unknown as T`, `@ts-expect-error`) are deliberately *not* `any`, so they pass the rule while staying explicit and local.

---

## Pattern 13: Effects Are a Last Resort

**Why:** Most `useEffect` misuse falls into two buckets: state that could have been derived during render, and logic that belongs in the event handler that caused it. Both produce extra renders, cascade chains, and stale-closure bugs that are hard to trace.

**Rule:** An effect exists to synchronize with an **external system** — a network connection, a browser API, a timer, a non-React widget. If no external system is involved, you don't need an effect:

- **Derive during render.** Anything computable from existing props/state is a `const`, not a state-plus-effect pair.
- **User actions belong in handlers.** Logic caused by a click runs in the click handler, not in an effect that watches for the click's side effects.
- **Reset subtree state with `key`,** not with an effect that watches a prop and calls setters.
- **No effect chains** — one effect adjusting state that triggers another effect is a rewrite signal; compute everything in the event that started it.
- **Dependency honesty is non-negotiable.** Never silence `react-hooks/exhaustive-deps`; fix the dependency instead — move the function inside the effect, use the updater form of a setter, or wrap a callback prop in `useEffectEvent` so the effect reads the latest version without depending on it. `useEffectEvent` is only for logic that is genuinely an event fired from the effect — never a general way to erase dependencies.
- **One effect per synchronization concern** — two independent subscriptions are two effects, not one.

```tsx
// ✅ CORRECT — derived during render, no state, no effect
const fullName = firstName + ' ' + lastName

// ❌ WRONG — redundant state synced by an effect (extra render, can go stale)
const [fullName, setFullName] = useState('')
useEffect(() => {
  setFullName(firstName + ' ' + lastName)
}, [firstName, lastName])
```

```tsx
// ✅ CORRECT — the action's consequences live in the handler that caused it
function handleDelete(backupId: string) {
  deleteBackup(backupId)
  showNotification('Backup deleted')
}

// ❌ WRONG — effect spies on state to react to a user action
useEffect(() => {
  if (deletedBackupId) {
    showNotification('Backup deleted')
  }
}, [deletedBackupId])
```

```tsx
// ✅ CORRECT — remount resets all child state when the backup changes
<BackupDetail key={backupId} backupId={backupId} />

// ❌ WRONG — manual reset effect in the child
useEffect(() => {
  setDraftComment('')
}, [backupId])
```

```tsx
// ❌ WRONG — silencing the linter hides a stale-closure bug
useEffect(() => {
  connectToRoom(roomId, onMessage)
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [])

// ✅ CORRECT — honest dependencies; the callback is an effect event, not a dependency
const handleMessage = useEffectEvent(onMessage)

useEffect(() => {
  const connection = connectToRoom(roomId, handleMessage)
  return () => connection.disconnect()
}, [roomId])
```

---

## Pattern 14: Server State Lives in the Query Cache

**Why:** Server data copied into `useState` or a Zustand store becomes a second source of truth that immediately starts drifting from the backend. Hand-rolled `useEffect` fetching re-invents (badly) what a query cache already solves: races, caching, deduplication, retries, invalidation.

**Rule:** All server data goes through TanStack Query. Each feature domain defines a query-key factory and `queryOptions` factories next to its API functions — components, loaders, and imperative code all consume the same factory. Set a non-zero `staleTime` deliberately (the default `0` refetches on every mount). Mutations invalidate through the same key factory. Polling is `refetchInterval` on the query options, not a hand-rolled interval. Never copy query results into component state or a store — use `select` to derive, and keep only IDs in client state (Pattern 7). A hand-rolled `useEffect` fetch is acceptable only where the library is genuinely unavailable, and then it must handle stale responses with an `ignore` flag or `AbortController` in cleanup (Pattern 4's polling example).

```tsx
// ✅ CORRECT — one key factory + queryOptions factory per domain
// src/features/backups/api/backupQueries.ts
import { queryOptions } from '@tanstack/react-query'
import { fetchBackup, fetchBackups } from './backupApi'

const BACKUP_STALE_TIME_MS = 30_000

export const backupKeys = {
  all: ['backups'] as const,
  detail: (id: string) => [...backupKeys.all, id] as const,
}

export const backupsQuery = () =>
  queryOptions({
    queryKey: backupKeys.all,
    queryFn: fetchBackups,
    staleTime: BACKUP_STALE_TIME_MS,
  })

export const backupQuery = (id: string) =>
  queryOptions({
    queryKey: backupKeys.detail(id),
    queryFn: () => fetchBackup(id),
    staleTime: BACKUP_STALE_TIME_MS,
  })
```

```tsx
// ✅ CORRECT — components read the cache; `select` derives without copying
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

const { data: backups = [], isPending, error } = useQuery(backupsQuery())

const { data: activeBackupCount } = useQuery({
  ...backupsQuery(),
  select: allBackups => allBackups.filter(backup => backup.status === 'active').length,
})

// ✅ CORRECT — mutations invalidate through the same key factory
const queryClient = useQueryClient()

const deleteBackupMutation = useMutation({
  mutationFn: deleteBackup,
  onSuccess: () => queryClient.invalidateQueries({ queryKey: backupKeys.all }),
})
```

```tsx
// ❌ WRONG — copies server state into local state; the copy goes stale immediately
const { data } = useQuery(backupsQuery())
const [backups, setBackups] = useState<Backup[]>([])

useEffect(() => {
  if (data) {
    setBackups(data)
  }
}, [data])

// ❌ WRONG — server data in a client store (Pattern 7's boundary, violated)
export const useBackupStore = create<BackupState>()(set => ({
  backups: [],
  fetchBackups: async () => {
    set({ backups: await fetchBackups() })
  },
}))

// ❌ WRONG — raw effect fetching as the default data layer
useEffect(() => {
  fetch('/api/backups')
    .then(response => response.json())
    .then(setBackups)
}, [])
```

**The boundary in one sentence:** server state (data you don't own — the backend's truth, snapshotted) belongs to the query cache; client state (data you own — UI mode, filters, drafts, selections) belongs to `useState`, context, or a Zustand store.
