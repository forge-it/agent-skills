---
name: frontend-vue-code-style
description: Use when writing or reviewing Vue components, composables, provide/inject pairs, Pinia stores, routes, watchers, or TypeScript types in a Vue 3 SPA — the house patterns for data flow, state ownership, and type safety.
vibe: Keeps Vue codebases predictable, traceable, and free of spaghetti.
license: MIT
metadata:
  author: cristian.ciortea@syneto.eu
  version: "0.0.10"
---

# Vue Code Style — Patterns & Conventions

A living collection of patterns that every component, composable, and store in this codebase must follow. When in doubt, check here first.

This is the Vue sibling of `frontend-react-code-style`; Patterns 1–12 cover the same concerns under the same numbers, Pattern 13 is React's Pattern 15 (closed sets are enum objects), and Pattern 14 is the Vue analog of React's Pattern 13 (derive, don't watch) — numbers are stable identifiers and are never renumbered.

**Stack assumptions:** Vue 3.5+ with `<script setup>` and TypeScript in strict mode checked by `vue-tsc`, Pinia 4 setup stores (ESM-only; `@vue/devtools-api` is installed alongside it) with `pinia-plugin-persistedstate` 4, Vue Router 5 with typed file-based routes, Vite SPA (no SSR framework), server data fetched by store actions through the feature's `api/` module. Vue 3.6 (Vapor) is still a release candidate and is not assumed. Where a different stack choice changes a rule, the pattern names the fallback.

---

## Pattern 1: Props Down, Emits Up (One-Way Data Flow)

**Why:** Without it, child components mutate parent state directly, nobody can trace where a change came from, and debugging becomes a nightmare.

**Rule:** A child component never modifies data it receives. It declares what it accepts via `defineProps<T>()`, and reports user actions via `defineEmits<T>()`. The parent owns the state and decides what to do.
```vue
<!-- ✅ CORRECT — child reports, parent decides -->
<!-- BackupRow.vue -->
<script setup lang="ts">
import type { BackupStatus } from '@/features/backups/constants'

const props = defineProps<{
  id: string
  name: string
  status: BackupStatus
}>()

const emit = defineEmits<{
  delete: [id: string]
  archive: [id: string]
}>()
</script>

<template>
  <tr>
    <td>{{ props.name }}</td>
    <td>{{ props.status }}</td>
    <td>
      <button @click="emit('archive', props.id)">Archive</button>
      <button @click="emit('delete', props.id)">Delete</button>
    </td>
  </tr>
</template>
```
```vue
<!-- ❌ WRONG — child mutates parent state directly -->
<script setup lang="ts">
const props = defineProps<{ backup: Backup }>()

function handleDelete() {
  props.backup.status = 'deleted'  // NEVER DO THIS
}
</script>
```

---

## Pattern 2: Container / Presenter Split

**Why:** Without it, components grow into god-files that fetch data, transform it, handle errors, and render 200 lines of template. Reuse and testing become impossible.

**Rule:** When a component mixes data logic with rendering, split it. The container wires composables together and passes their output to the presenter via props. The presenter handles display (template, styles, user interaction) — zero data fetching, zero business logic. The container should have almost no inline logic; if it does, extract it into a composable.

```vue
<!-- ✅ Container — wires composables to presenter, almost no code -->
<!-- BackupListContainer.vue -->
<script setup lang="ts">
import { useBackups } from './composables/useBackups'
import { useBackupSearch } from './composables/useBackupSearch'
import BackupListPresenter from './BackupListPresenter.vue'

const { backups, isLoading, error, fetchBackups, deleteBackup } = useBackups()
const { searchQuery, showArchived, filteredBackups } = useBackupSearch(backups)
</script>

<template>
  <BackupListPresenter
    :backups="filteredBackups"
    :is-loading="isLoading"
    :error="error"
    v-model:search="searchQuery"
    v-model:show-archived="showArchived"
    @delete="deleteBackup"
    @retry="fetchBackups"
  />
</template>
```

```vue
<!-- ✅ Presenter — pure rendering, no data logic -->
<!-- BackupListPresenter.vue -->
<script setup lang="ts">
import type { Backup } from './types'

defineProps<{
  backups: Backup[]
  isLoading: boolean
  error: string | null
}>()

const search = defineModel<string>('search', { required: true })
const showArchived = defineModel<boolean>('showArchived', { required: true })

defineEmits<{
  delete: [id: string]
  retry: []
}>()
</script>

<template>
  <div>
    <input v-model="search" placeholder="Search…" />
    <label>
      <input v-model="showArchived" type="checkbox" />
      Show archived
    </label>
    <div v-if="isLoading">Loading…</div>
    <div v-else-if="error">
      <p>{{ error }}</p>
      <button @click="$emit('retry')">Retry</button>
    </div>
    <table v-else>
      <tr v-for="backup in backups" :key="backup.id">
        <td>{{ backup.name }}</td>
        <td><button @click="$emit('delete', backup.id)">Delete</button></td>
      </tr>
    </table>
  </div>
</template>
```

```vue
<!-- ❌ WRONG — container has inline logic instead of composables -->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

const backups = ref([])
const isLoading = ref(false)
const error = ref(null)

async function fetchBackups() {
  isLoading.value = true
  try {
    const response = await fetch('/api/backups')
    backups.value = await response.json()
  } catch {
    error.value = 'Failed'
  } finally {
    isLoading.value = false
  }
}

const filtered = computed(() => backups.value.filter(/* ... */))

onMounted(fetchBackups)
</script>
```

**When to skip:** Small components with minimal logic (a badge, a button, a tooltip) don't need splitting. Apply this when a component starts mixing fetch/state logic with rendering.

---

## Pattern 3: Typed provide/inject — Provider Function + Throwing Composable

**Why:** Without it, you either prop-drill through layers of components that don't care about the data, or use string-based injection that silently breaks on typos with no type safety. A typed key alone is not enough: `inject()` returns `undefined` when nobody provided the value and carries on, so a missing provider is the same silent failure.

**Rule:** Model each injection as a module that owns a private `InjectionKey<T>` and exports exactly two functions: `provideX()` for the ancestor and `useX()` for consumers, where `useX()` throws when the value is missing — consumers never see `undefined` and never type-assert. Provide reactive values (`Ref`, not raw primitives) so consumers stay reactive. Never use bare string keys, never export the raw key, and never pass `inject()` a default: the default is only reachable when someone forgot the provider, and that must crash loudly.

```typescript
// ✅ src/features/auth/userRole.ts — the key stays private; two functions are the whole API
import { inject, provide, ref, type InjectionKey, type Ref } from 'vue'

export const UserRole = {
  Admin: 'admin',
  Viewer: 'viewer',
  Editor: 'editor',
} as const

export type UserRole = (typeof UserRole)[keyof typeof UserRole]

const userRoleKey: InjectionKey<Ref<UserRole>> = Symbol('userRole')

export function provideUserRole(initialRole: UserRole): Ref<UserRole> {
  const userRole = ref<UserRole>(initialRole)
  provide(userRoleKey, userRole)
  return userRole
}

export function useUserRole(): Ref<UserRole> {
  const userRole = inject(userRoleKey)
  if (!userRole) {
    throw new Error('useUserRole must be called in a component below provideUserRole')
  }
  return userRole
}
```
```vue
<!-- ✅ Provider — high in the tree -->
<!-- App.vue -->
<script setup lang="ts">
import { provideUserRole, UserRole } from '@/features/auth/userRole'

provideUserRole(UserRole.Viewer)
</script>
```
```vue
<!-- ✅ Consumer — anywhere deeper, no prop drilling, no undefined check -->
<!-- ServerRow.vue -->
<script setup lang="ts">
import { useUserRole, UserRole } from '@/features/auth/userRole'

const userRole = useUserRole()
</script>

<template>
  <button v-if="userRole === UserRole.Admin">Delete Server</button>
</template>
```
```typescript
// ❌ WRONG — string key, no types, typo = silent undefined
provide('userole', userRole)         // typo, nobody catches it
const role = inject('userRole')      // type is unknown

// ❌ WRONG — exported key plus a fallback default; a missing provider becomes a silent bug
export const userRoleKey: InjectionKey<Ref<UserRole>> = Symbol('userRole')
const userRole = inject(userRoleKey, ref(UserRole.Viewer))
```

**When to use:** Low-frequency, dependency-injection-shaped values needed 3+ levels deep — theme, current user, locale, feature flags. Anything else is placed by Pattern 7's decision rule.

---

## Pattern 4: Composable Design Rules

**Why:** Composables are the primary way to organize and reuse logic in Vue 3. Without clear conventions, they become tangled, untestable, and leak resources.

**Rule:** Every composable follows these five constraints:

1. **Single responsibility** — one composable, one concern.
2. **Reactive in, refs out** — accept `MaybeRefOrGetter<T>` and read it through `toValue()`, so a caller can pass a ref, a getter over props (`() => props.backups`), or a plain value; return an object of refs so consumers can destructure.
3. **Cleanup mirrors setup** — if it creates timers, listeners, or connections, it undoes them in `onUnmounted` (`onScopeDispose` when it may run outside a component).
4. **Object return shape** — always return a plain object with named properties, never an array.
5. **Synchronous invocation** — call composables at the top level of `<script setup>`, never inside callbacks, conditions, or async functions.

```typescript
// ✅ CORRECT — focused, reactive in / refs out, object return
import { computed, ref, toValue, type MaybeRefOrGetter } from 'vue'
import { BackupStatus } from '@/features/backups/constants'

export function useBackupSearch(backups: MaybeRefOrGetter<Backup[]>) {
  const searchQuery = ref('')
  const showArchived = ref(false)

  const filteredBackups = computed(() =>
    toValue(backups).filter(backup => {
      const matchesSearch = backup.name
        .toLowerCase()
        .includes(searchQuery.value.toLowerCase())
      const matchesStatus = showArchived.value || backup.status !== BackupStatus.Archived
      return matchesSearch && matchesStatus
    })
  )

  return {
    searchQuery,
    showArchived,
    filteredBackups,
  }
}
```

```typescript
// ✅ CORRECT — cleanup mirrors setup; the composable subscribes to an external system
import { onMounted, onUnmounted } from 'vue'

export function useEscapeKey(onEscape: () => void): void {
  function handleKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      onEscape()
    }
  }

  onMounted(() => document.addEventListener('keydown', handleKeyDown))
  onUnmounted(() => document.removeEventListener('keydown', handleKeyDown))
}
```

```typescript
// ❌ WRONG — god composable, array return, no cleanup
export function useBackupManager() {
  // fetching + filtering + sorting + pagination + bulk selection
  // all in one function = untestable, unreusable
  return [data, isLoading, error, filtered, sorted, page]  // array = fragile
}
```

```typescript
// ❌ WRONG — called inside a callback
onMounted(() => {
  const { data } = useBackups()  // lifecycle hooks inside won't bind
})
```

---

## Pattern 5: Module-Level vs Function-Level State in Composables

**Why:** Without understanding this distinction, you either get unexpected shared state between components (bugs) or fail to share state when you need to (duplicate fetches, out-of-sync UI).

**Rule:** Reactive state declared **inside** the composable function gives each caller its own independent copy. State declared **outside** the function at module level is a shared singleton — all callers see the same data. Choose deliberately. Protect shared state with `readonly()` and expose mutation only through the composable's functions.

```typescript
// ✅ Per-component state — each caller gets their own copy
export function useCounter() {
  const count = ref(0)  // inside the function
  const increment = () => count.value++
  return { count, increment }
}
```

```typescript
// ✅ Shared state — all callers see the same value
import { ref, readonly } from 'vue'

const notifications = ref<Notification[]>([])  // outside the function

export function useNotifications() {
  function notify(message: string): void {
    notifications.value.push({ id: crypto.randomUUID(), message })
  }

  function dismiss(id: string): void {
    notifications.value = notifications.value.filter(notification => notification.id !== id)
  }

  return {
    notifications: readonly(notifications),  // read-only to consumers
    notify,
    dismiss,
  }
}
```

```typescript
// ❌ WRONG — shared state without readonly, anyone can mutate directly
const items = ref<string[]>([])

export function useItems() {
  return { items }  // consumer can do items.value.push('anything')
}
```

**Which one:** Pattern 7's decision rule places it — function-level for anything each instance owns (form state, a local search query, a component-scoped timer), module-level for a few components in one feature sharing a notification list or a "currently editing" flag, Pinia beyond that.

---

## Pattern 6: Descriptive Naming (CRITICAL)

**Why:** Single-letter variables and abbreviations force readers to mentally decode what a name represents. They destroy searchability, make code reviews harder, and turn simple debugging into a guessing game.

**Rule:** Never use single-letter variable names or abbreviations. Every variable, parameter, loop variable, and callback parameter must be a descriptive, intent-revealing name. The collection variable and the loop/callback variable must be consistent — the collection is the plural form, the loop variable is the singular.

```vue
<!-- ✅ CORRECT — descriptive, searchable, consistent -->
<tr v-for="backup in backups" :key="backup.id"><td>{{ backup.name }}</td></tr>

<!-- ❌ WRONG — single-letter loop variable -->
<tr v-for="b in backups" :key="b.id"><td>{{ b.name }}</td></tr>
```

```typescript
// ✅ CORRECT — callback parameters and state names are descriptive; booleans read as a question
backups.value.filter(backup => backup.status !== BackupStatus.Archived)
const selectedBackupId = ref<string | null>(null)
const isLoading = ref(false)

// ❌ WRONG — single-letter, abbreviated, or vague names
backups.value.filter(b => b.status !== BackupStatus.Archived)
const selId = ref<string | null>(null)
const loading = ref(false)  // loading what?
```

**Rationale:** This rule applies everywhere: `v-for` loops, `.map()`, `.filter()`, `.find()`, `.reduce()`, `.forEach()`, computed properties, and any other context where a variable is introduced. No exceptions.

---

## Pattern 7: Store Scope and Boundaries

**Why:** Pinia stores are easy to overuse. Without strict boundaries, teams end up with god-stores that mix auth, entities, UI flags, filters, and view-specific logic in one reactive blob. That destroys traceability, creates accidental coupling between features, and makes it unclear whether state belongs in props, a composable, or a store.

**Rule:** Use one store per feature domain. Reach for a store only when state must be shared across unrelated parts of the app, survive route navigation, or benefit from Pinia devtools inspection. Stores own durable state, getters, and simple mutations or API actions. Composables own view-specific derived logic layered on top of store state. When destructuring a store, always use `storeToRefs()` for state and getters, and destructure actions directly from the store instance. Never build a god-store.

```typescript
// ✅ CORRECT — one store per domain, setup-store syntax, simple state + actions
// src/features/backups/stores/useBackupStore.ts
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { getBackups } from '../api/backupApi'
import { BackupStatus } from '../constants'
import type { Backup } from '../types'

export const useBackupStore = defineStore('backups', () => {
  const backups = ref<Backup[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const activeBackups = computed(() =>
    backups.value.filter(backup => backup.status === BackupStatus.Active)
  )

  async function fetchBackups(): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      backups.value = await getBackups()  // getBackups(): Promise<Backup[]> — typed at the wire boundary, throws on failure
    } catch (caughtError) {
      error.value = caughtError instanceof Error ? caughtError.message : 'Unknown error'
    } finally {
      isLoading.value = false
    }
  }

  function removeBackup(id: string): void {
    backups.value = backups.value.filter(backup => backup.id !== id)
  }

  return {
    backups,
    isLoading,
    error,
    activeBackups,
    fetchBackups,
    removeBackup,
  }
})
```

```typescript
// ✅ CORRECT — composable layers view logic on top of store state
// src/features/backups/composables/useBackupSearch.ts
import { computed, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { BackupStatus } from '../constants'
import { useBackupStore } from '../stores/useBackupStore'

export function useBackupSearch() {
  const backupStore = useBackupStore()
  const { backups } = storeToRefs(backupStore)

  const searchQuery = ref('')
  const showArchived = ref(false)

  const filteredBackups = computed(() =>
    backups.value.filter(backup => {
      const matchesSearch = backup.name
        .toLowerCase()
        .includes(searchQuery.value.toLowerCase())
      const matchesStatus = showArchived.value || backup.status !== BackupStatus.Archived
      return matchesSearch && matchesStatus
    })
  )

  return {
    searchQuery,
    showArchived,
    filteredBackups,
  }
}
```

```typescript
// ✅ CORRECT — state/getters via storeToRefs, actions directly
import { storeToRefs } from 'pinia'
import { useAuthStore } from '@/features/auth/stores/useAuthStore'

const authStore = useAuthStore()
const { isAuthenticated, userName } = storeToRefs(authStore)
const { login, logout } = authStore
```

```typescript
// ❌ WRONG — god-store mixing unrelated concerns
export const useAppStore = defineStore('app', () => {
  const user = ref<User | null>(null)
  const backups = ref<Backup[]>([])
  const servers = ref<Server[]>([])
  const sidebarCollapsed = ref(false)
  const searchQuery = ref('')

  return { user, backups, servers, sidebarCollapsed, searchQuery }
})
```

```typescript
// ❌ WRONG — raw destructuring loses reactivity for state/getters
const { backups, isLoading, activeBackups } = useBackupStore()
```

**Decision rule:** If one component owns it, keep it local. If a parent can pass it down, use props. If each caller needs its own reusable state, use a composable with function-level state. If a few components in one feature share it, a composable with module-level state may be enough. Use Pinia only when the state is truly cross-feature or must survive navigation.

---

## Pattern 8: Persist Deliberately

**Why:** Persisting everything feels convenient until stale loading flags, old error messages, transient filters, or selection state survive a reload and confuse the user. Persistence is not a dumping ground for the whole store. It is an explicit durability decision.

**Rule:** Persist only state that must survive a page reload: remembered user preferences, UI settings, or similarly durable data. Never persist loading flags, error messages, transient search queries, temporary selections, or anything that should reset naturally when the page is refreshed. Auth tokens do not belong in `localStorage`: keep access tokens in memory and let the refresh token live in an `HttpOnly` cookie; persisting a token client-side is an explicit, documented exception, never a default. Prefer `pick` to whitelist persisted fields explicitly instead of persisting the whole store by default.

```typescript
// ✅ CORRECT — persist the preference, not the token
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)  // in memory only; the refresh token lives in an HttpOnly cookie
  const rememberMe = ref(false)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => token.value !== null)

  function logout(): void {
    user.value = null
    token.value = null
    error.value = null
  }

  return {
    user,
    token,
    rememberMe,
    isLoading,
    error,
    isAuthenticated,
    logout,
  }
}, {
  persist: {
    key: 'auth',
    pick: ['rememberMe'],
  },
})
```

```typescript
// ✅ CORRECT — preferences are durable, so persisting the whole store is reasonable
const ThemeName = { Light: 'light', Dark: 'dark' } as const
type ThemeName = (typeof ThemeName)[keyof typeof ThemeName]

export const usePreferencesStore = defineStore('preferences', () => {
  const sidebarCollapsed = ref(false)
  const theme = ref<ThemeName>(ThemeName.Light)
  const tablePageSize = ref(20)

  function setTheme(nextTheme: ThemeName): void {
    theme.value = nextTheme
    document.documentElement.setAttribute('data-theme', nextTheme)
  }

  return {
    sidebarCollapsed,
    theme,
    tablePageSize,
    setTheme,
  }
}, {
  persist: {
    pick: ['sidebarCollapsed', 'theme', 'tablePageSize'],
  },
})
```

```typescript
// ❌ WRONG — persists transient state that should die on refresh
export const useBackupStore = defineStore('backups', () => {
  const backups = ref<Backup[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const selectedIds = ref<string[]>([])
  const searchQuery = ref('')

  return { backups, isLoading, error, selectedIds, searchQuery }
}, {
  persist: true,
})
```

**Practical rule:** If you cannot clearly explain why a field should still exist after a full page reload, do not persist it.

---

## Pattern 9: No Duplicate Literals — Extract Constants (CRITICAL)

**Why:** Hardcoded string or number literals scattered across multiple files are invisible coupling. When the value changes, you have to find every copy — miss one and you have a silent bug. Constants give the value a name, a single source of truth, and make the intent searchable.

**Rule:** Any literal value (string, number, etc.) that appears in more than one place across the codebase **must** be extracted into a named constant. Define the constant once in the module that owns the concept, then import it everywhere else. Never duplicate the raw literal.

```typescript
// ✅ CORRECT — single source of truth in the module that owns the concept
// src/features/backups/api/backupApi.ts
export const BACKUPS_API_PATH = '/api/backups'

export async function fetchBackups(): Promise<Backup[]> {
  const response = await fetch(BACKUPS_API_PATH)
  return backupListSchema.parse(await response.json())
}

// src/features/backups/api/backupApi.test.ts
import { BACKUPS_API_PATH } from './backupApi'

server.use(http.get(BACKUPS_API_PATH, () => HttpResponse.json(backupFixtures)))
```

```typescript
// ❌ WRONG — same string hardcoded in multiple places
// api/backupApi.ts
fetch('/api/backups')

// api/backupApi.test.ts
http.get('/api/backups', () => HttpResponse.json(backupFixtures))  // duplicate!

// features/dashboard/api/dashboardApi.ts
fetch('/api/backup')                                                // duplicate — and a silent typo!
```

```typescript
// ❌ WRONG — same number in two modules without a name
staleTime: 30000,   // backupQueries.ts — what does 30000 mean?
staleTime: 30000,   // serverQueries.ts — is it intentionally the same?

// ✅ CORRECT — named once, imported where the value is shared on purpose
export const LIST_STALE_TIME_MS = 30_000
```

**Scope:** this pattern covers *standalone* literals. When the literal is one alternative in a closed set — a status, kind, or mode — a family of constants is the wrong fix; the set becomes an enum object (Pattern 13).

---

## Pattern 10: Route Organization — Typed File-Based Routes, Typed Meta, Reactive Params

**Why:** Hand-built paths like `router.push('/backups/' + id)` break silently when a route changes. Eagerly imported route components bloat the initial bundle. Untyped `route.meta` and `route.params` give you `unknown` (or a lying `string`) everywhere. Destructured `route.params` loses reactivity and goes stale on navigation.

**Rule:** Routes are generated, not hand-listed. With Vue Router 5 (our default) the Vite plugin from `vue-router/vite` scans `src/pages/`, emits `typed-router.d.ts` (add it to the tsconfig `include`), and lazy-loads every page by default, so code splitting is not a per-route chore. Navigate by typed route name — `router.push({ name: '/backups/[id]', params: { id } })` and `<RouterLink :to>` fail `vue-tsc` when a page is renamed or a param is missing. Read params through `useRoute('/backups/[id]')`, which types them and stays reactive; never destructure `route.params`. Put per-page meta in `definePage()` and type `RouteMeta` once, globally. Page files under `src/pages/` stay thin: they mount the feature's page component and nothing else.

```typescript
// ✅ CORRECT — vite.config.ts: the router plugin runs before the Vue plugin
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import VueRouter from 'vue-router/vite'

export default defineConfig({
  plugins: [
    VueRouter({ routesFolder: 'src/pages', dts: 'src/typed-router.d.ts' }),
    vue(),
  ],
})
```

```typescript
// ✅ CORRECT — src/app/router.ts: generated routes, nothing hand-listed
import { createRouter, createWebHistory } from 'vue-router'
import { routes, handleHotUpdate } from 'vue-router/auto-routes'

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

if (import.meta.hot) {
  handleHotUpdate(router)
}
```

```vue
<!-- ✅ CORRECT — src/pages/backups/[id].vue: thin page file; meta via definePage; typed, reactive params -->
<script setup lang="ts">
import { useRoute } from 'vue-router'
import BackupDetailPage from '@/features/backups/BackupDetailPage.vue'

definePage({ meta: { requiresAuth: true, title: 'Backup Details' } })

const route = useRoute('/backups/[id]')  // route.params.id is `string`, no cast
</script>

<template>
  <BackupDetailPage :backup-id="route.params.id" />
</template>
```

```typescript
// ✅ CORRECT — type RouteMeta globally
// src/app/router.d.ts
import 'vue-router'
import type { UserRole } from '@/features/auth/userRole'

export {}

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    title?: string
    requiredRole?: UserRole
  }
}
```

```typescript
// ✅ CORRECT — typed navigation; a renamed page or a missing param fails vue-tsc
router.push({ name: '/backups/[id]', params: { id: backup.id } })
```

```typescript
// ❌ WRONG — hand-built path string; vue-tsc rejects it under typed routes, and it breaks silently without them
router.push('/backups/' + backup.id)
router.push(`/backups/${backup.id}`)

// ❌ WRONG — destructured params: a plain snapshot that goes stale on navigation
const { id } = route.params

// ❌ WRONG — the cast that typed routes make unnecessary
const backupId = computed(() => route.params.id as string)

// ❌ WRONG — a hand-maintained route next to the generated list; two sources of truth
routes: [...routes, { path: '/settings', component: () => import('@/features/settings/SettingsPage.vue') }]
```

**Fallback:** a project on Vue Router 4, or one that keeps a hand-written `routes` array, holds the same invariants by convention: every route has a `name`, navigation goes by name only, every `component` is a dynamic `import()`, params are read through `computed(() => route.params.id)`, and `RouteMeta` is typed as above.

---

## Pattern 11: Script Block Organization

**Why:** `<script setup>` dropped the fixed ordering the Options API enforced, so every component arranges its refs, computeds, and functions differently and readers can't predict where anything lives.

**Rule:** Order `<script setup>` top-to-bottom as **contract before internals, declaration before use**: imports → `defineProps`/`defineEmits`/`defineModel` → composable & store calls → local state (`ref`/`reactive`) → `computed` → `watch` → functions → lifecycle hooks.

```vue
<!-- ✅ CORRECT -->
<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useBackupSearch } from './composables/useBackupSearch'

const props = defineProps<{ backups: Backup[] }>()
const { searchQuery, filteredBackups } = useBackupSearch(() => props.backups)
const expandedId = ref<string | null>(null)
const hasResults = computed(() => filteredBackups.value.length > 0)
watch(searchQuery, () => { expandedId.value = null })
function toggleExpanded(backupId: string): void { /* ... */ }
</script>
```

**Subordinate to Patterns 2 and 4.** Ordering is layout, not cleanliness — a well-ordered god-component is still a god-component. Fix composition first, then order what remains. Skip for trivial scripts; there's no ESLint rule for this, so it's a human convention, not a hard gate.

---

## Pattern 12: No `any` — Reach for a Real Type (CRITICAL)

**Why:** `any` switches off type-checking for everything it touches, and it spreads silently — one `any` and the compiler stops catching typos, missing fields, and renames downstream. In **tests** it is worse than in app code: a mock typed `any` makes a test pass against a shape that no longer matches reality, so the test keeps reporting green while testing nothing. A lying test is worse than no test.

**Rule:** Never write `any` — in app code or in tests. When you genuinely need to step outside the type system, use the narrowest, most explicit escape hatch instead, preferring earlier options:

1. A real type / interface (almost always possible)
2. `unknown` + a narrowing check
3. `Partial<T>` for a partial mock
4. A typed mock factory that returns `T`
5. `as unknown as T` for a deliberate, greppable cast
6. `// @ts-expect-error` on the single line that feeds intentionally-invalid input — self-documenting, and it fails the build if the error ever disappears

```typescript
// ✅ CORRECT — typed mock factory, no `any`
function makeUser(overrides: Partial<User> = {}): User {
  return { id: 'u-1', name: 'Ada', email: 'ada@example.com', ...overrides }
}

const user = makeUser({ name: 'Grace' })          // fully typed; a renamed field breaks the test loudly

// ✅ CORRECT — deliberate invalid input, scoped to one line
// @ts-expect-error — name is required; verifying the guard rejects it
expect(() => renderProfile({ email: 'x@y.z' })).toThrow()
```

```typescript
// ❌ WRONG — `any` mock; the test passes against a shape that no longer exists
const user: any = { nmae: 'Ada' }                 // typo + missing email, both invisible
renderProfile(user)
expect(screen.getByText('Ada')).toBeTruthy()       // green, but exercised nothing real

// ❌ WRONG — `any` to silence one incompatible field, disables checking for the whole object
const response = await fetchUser() as any
```

**Enforcement:** this is enforced by `@typescript-eslint/no-explicit-any` (`error`) in both app and test files — see `frontend-vue-eslint-setup`. The escape hatches above (`as unknown as T`, `@ts-expect-error`) are deliberately *not* `any`, so they pass the rule while staying explicit and local.

---

## Pattern 13: Closed Sets Are Enum Objects, Not Loose Strings (CRITICAL)

**Why:** A status, kind, mode, or state has a fixed set of legal values. Left as raw `'archived'` literals across components, composables, and stores, nothing in the code says the set exists — a typo passes `vue-tsc`, and adding a fourth value means grepping and hoping. A flat family of constants (`BACKUP_STATUS_ACTIVE`, `BACKUP_STATUS_FAILED`, …) names each *value* but never names the *set*, so the prop or parameter stays typed `string` and still accepts anything.

**Rule:** Model the set **once** as an `as const` object plus a type derived from it, in the module that owns the concept. The object gives named members and a runtime list to iterate; the derived type is the literal union, which is exactly what the API layer, router, and validation schemas already speak — so it crosses boundaries without casts. Never use TypeScript's `enum` keyword: its members are nominal, so every value arriving from the wire needs a cast, and it emits runtime code rather than erasing (breaking `erasableSyntaxOnly` and Node type-stripping).

**A bare literal-union alias** — `export type UserRole = 'admin' | 'viewer' | 'editor'` — is the halfway house. It names the set but produces no members and nothing to iterate, so it holds up only while no member is referenced by name and no code needs the value list. The moment either happens — a `=== 'admin'` comparison, a dropdown built from the set — convert it to the pair below. Give the object the alias's existing name and every annotation keeps working unchanged; only the declaration and the literals move.

No linter catches a violation of this pattern — `vue-tsc` is satisfied by any string. It is caught in review or not at all.

```typescript
// ✅ CORRECT — one declaration pair names the set and its members
// src/features/backups/constants.ts
export const BackupStatus = {
  Active: 'active',
  Failed: 'failed',
  Archived: 'archived',
} as const

export type BackupStatus = (typeof BackupStatus)[keyof typeof BackupStatus]

// src/features/backups/composables/useBackups.ts
import { BackupStatus } from '../constants'

const status: BackupStatus = backup.status            // API literal union — no cast
const activeBackups = computed(() =>
  backups.value.filter(backup => backup.status === BackupStatus.Active)
)
```

Per-value data belongs in a `Record` keyed by the union, not in a ternary chain repeated per component. This is where the type earns its keep: add a member to the object and the `Record` stops compiling until it is handled.

```typescript
// ✅ CORRECT — exhaustive by construction
const STATUS_BADGE_CLASS: Record<BackupStatus, string> = {
  [BackupStatus.Active]: 'bg-green-500',
  [BackupStatus.Failed]: 'bg-red-500',
  [BackupStatus.Archived]: 'bg-gray-400',
}

// ✅ CORRECT — the object is also the runtime list: filter dropdowns, tabs, tests
const statusOptions = Object.values(BackupStatus)
```

```typescript
// ❌ WRONG — inline literals: the set is invisible, the typo is silent
const badgeClass = props.status === 'archived' ? 'bg-gray-400' : 'bg-green-500'
const isDone = backup.status === 'arcived'            // compiles if `status` is `string`

// ❌ WRONG — constant family: names each value, but no type names the set
export const BACKUP_STATUS_ACTIVE = 'active' as const
export const BACKUP_STATUS_FAILED = 'failed' as const

// ❌ WRONG — `enum` keyword: emits runtime code, nominal members need casts
export enum BackupStatus { Active = 'active', Failed = 'failed' }
```

**When NOT to apply:**
- The set isn't closed — values come from the server, a config file, or user input (tenant names, tag keys, feature-flag names).
- A single standalone literal with no siblings — a storage key, a poll interval, an API path. That's Pattern 9.
- A presentational prop variant written inline at every call site (`size: 'sm' | 'md' | 'lg'`, used as `<AppButton size="sm">`). A bare literal union is right there: the prop type is the single source of truth and the attribute documents itself. Those repeated attribute values are exempt from Pattern 9 too — do not extract `'sm'` into a constant. Promote to an enum object the moment the value gets stored, compared in more than one module, or iterated.

---

## Pattern 14: Derive with `computed`; `watch` Is for Side Effects

**Why:** Most `watch` misuse falls into two buckets: state that could have been derived, and logic that belongs in the handler that caused it. Both produce extra work, watcher chains that fire in an order nobody planned, and state that is briefly wrong between the source changing and the watcher catching up.

**Rule:** A watcher exists to synchronize with something **outside** Vue's reactivity — the URL, storage, a network connection, a timer, a non-Vue widget. If no external system is involved, you don't need a watcher:

- **Derive with `computed`.** Anything computable from existing state is a `computed`, not a `ref` plus a `watch` that keeps it in sync.
- **User actions belong in handlers.** Logic caused by a click runs in the click handler, not in a watcher that spots the click's consequences.
- **No watcher chains** — one watcher setting state that triggers another watcher is a rewrite signal; compute everything from the event that started it.
- **Reset child state with `:key`,** not with a watcher on a prop that calls setters.
- **Timing is a decision.** Write out `immediate`, `deep`, and `flush` when they matter; prefer `watch` on a named source over `watchEffect` so the dependencies are visible.
- **Clean up inside the run** with `onWatcherCleanup()` when a run starts something asynchronous or subscribes to something; the next run and unmount both cancel it.

```typescript
// ✅ CORRECT — derived, always consistent, no extra state
const fullName = computed(() => `${firstName.value} ${lastName.value}`)

// ❌ WRONG — redundant state kept in sync by a watcher (briefly stale, extra work)
const fullName = ref('')
watch([firstName, lastName], () => {
  fullName.value = `${firstName.value} ${lastName.value}`
})
```

```typescript
// ✅ CORRECT — the action's consequences live in the handler that caused it
function handleDelete(backupId: string): void {
  removeBackup(backupId)
  notify('Backup deleted')
}

// ❌ WRONG — a watcher spies on state to react to a user action
watch(deletedBackupId, id => {
  if (id) {
    notify('Backup deleted')
  }
})
```

```typescript
// ✅ CORRECT — genuine external sync; the cleanup is scoped to the run
import { onWatcherCleanup, watch } from 'vue'

watch(backupId, id => {
  const controller = new AbortController()
  void loadBackup(id, controller.signal)  // a store action (Pattern 7), not an inline fetch
  onWatcherCleanup(() => controller.abort())
}, { immediate: true })
```
