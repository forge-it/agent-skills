---
name: frontend-vue-code-style
description: Patterns and conventions for writing clean, maintainable Vue 3 applications. Use when writing or reviewing Vue components, composables, stores, or project structure — enforces consistent data flow, component design, and type safety across the codebase.
vibe: Keeps Vue codebases predictable, traceable, and free of spaghetti.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.3"
---

# Vue Code Style — Patterns & Conventions

A living collection of patterns that every component, composable, and store in this codebase must follow. When in doubt, check here first.

---

## Pattern 1: Props Down, Emits Up (One-Way Data Flow)

**Why:** Without it, child components mutate parent state directly, nobody can trace where a change came from, and debugging becomes a nightmare.

**Rule:** A child component never modifies data it receives. It declares what it accepts via `defineProps<T>()`, and reports user actions via `defineEmits<T>()`. The parent owns the state and decides what to do.
```vue
<!-- ✅ CORRECT — child reports, parent decides -->
<!-- BackupRow.vue -->
<script setup lang="ts">
const props = defineProps<{
  id: string
  name: string
  status: 'active' | 'archived' | 'failed'
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
    const res = await fetch('/api/backups')
    backups.value = await res.json()
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

## Pattern 3: Typed provide/inject with InjectionKey

**Why:** Without it, you either prop-drill through layers of components that don't care about the data, or use string-based injection that silently breaks on typos with no type safety.

**Rule:** Define injection keys in a shared `keys.ts` file using `InjectionKey<T>`. Always provide reactive values (`Ref`, not raw primitives) so consumers stay reactive. Never use bare string keys.
```typescript
// ✅ src/keys.ts — typed, Symbol-based, single source of truth
import type { InjectionKey, Ref } from 'vue'

export type UserRole = 'admin' | 'viewer' | 'editor'

export const userRoleKey: InjectionKey<Ref<UserRole>> = Symbol('userRole')
```
```vue
<!-- ✅ Provider — high in the tree -->
<!-- App.vue -->
<script setup lang="ts">
import { provide, ref } from 'vue'
import { userRoleKey, type UserRole } from '@/keys'

const userRole = ref<UserRole>('admin')
provide(userRoleKey, userRole)
</script>
```
```vue
<!-- ✅ Consumer — anywhere deeper, no prop drilling -->
<!-- ServerRow.vue -->
<script setup lang="ts">
import { inject } from 'vue'
import { userRoleKey } from '@/keys'

const userRole = inject(userRoleKey)
</script>

<template>
  <button v-if="userRole === 'admin'">Delete Server</button>
</template>
```
```typescript
// ❌ WRONG — string key, no types, typo = silent undefined
provide('userole', userRole)         // typo, nobody catches it
const role = inject('userRole')      // type is unknown
```

**When to use:** Data needed 3+ levels deep where intermediate components don't use it. For direct parent-child, use props. For global state with read/write from anywhere, use Pinia stores.

---

## Pattern 4: Composable Design Rules

**Why:** Composables are the primary way to organize and reuse logic in Vue 3. Without clear conventions, they become tangled, untestable, and leak resources.

**Rule:** Every composable follows these five constraints:

1. **Single responsibility** — one composable, one concern.
2. **Ref in, ref out** — accept `Ref<T>` as input so it stays reactive, return an object of refs so consumers can destructure.
3. **Cleanup on unmount** — if it creates timers, listeners, or connections, it cleans them up in `onUnmounted`.
4. **Object return shape** — always return a plain object with named properties, never an array.
5. **Synchronous invocation** — call composables at the top level of `<script setup>`, never inside callbacks, conditions, or async functions.

```typescript
// ✅ CORRECT — focused, ref in / ref out, cleanup, object return
import { ref, computed, onMounted, onUnmounted, type Ref } from 'vue'

export function useBackupSearch(backups: Ref<Backup[]>) {
  const searchQuery = ref('')
  const showArchived = ref(false)

  const filteredBackups = computed(() =>
    backups.value.filter(backup => {
      const matchesSearch = backup.name
        .toLowerCase()
        .includes(searchQuery.value.toLowerCase())
      const matchesStatus = showArchived.value || backup.status !== 'archived'
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
// ✅ CORRECT — cleanup on unmount
export function usePolling(url: string, intervalMs = 30_000) {
  const data = ref<unknown>(null)
  let timerId: number | undefined

  async function poll() {
    const res = await fetch(url)
    data.value = await res.json()
  }

  onMounted(() => {
    poll()
    timerId = window.setInterval(poll, intervalMs)
  })

  onUnmounted(() => {
    clearInterval(timerId)
  })

  return { data, refresh: poll }
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
    notifications.value.push({ id: String(Date.now()), message })
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

**When to use shared:** Cross-component state that isn't global enough for a Pinia store — notifications, toasts, a sidebar collapse toggle, a "currently editing" flag. **When to use per-component:** Any logic where each component instance needs its own independent copy — form state, local search queries, component-scoped timers.

---

## Pattern 6: Descriptive Naming (CRITICAL)

**Why:** Single-letter variables and abbreviations force readers to mentally decode what a name represents. They destroy searchability, make code reviews harder, and turn simple debugging into a guessing game.

**Rule:** Never use single-letter variable names or abbreviations. Every variable, parameter, loop variable, and callback parameter must be a descriptive, intent-revealing name. The collection variable and the loop/callback variable must be consistent — the collection is the plural form, the loop variable is the singular.

```vue
<!-- ✅ CORRECT — descriptive, searchable, consistent -->
<template>
  <tr v-for="backup in backups" :key="backup.id">
    <td>{{ backup.name }}</td>
    <td>{{ backup.status }}</td>
  </tr>
</template>
```
```vue
<!-- ❌ WRONG — single-letter loop variable -->
<template>
  <tr v-for="b in backups" :key="b.id">
    <td>{{ b.name }}</td>
  </tr>
</template>
```

```typescript
// ✅ CORRECT — callback parameters are descriptive
backups.value.filter(backup => backup.status !== 'archived')
notifications.value.filter(notification => notification.id !== id)
users.map(user => user.email)

// ❌ WRONG — single-letter or abbreviated callback parameters
backups.value.filter(b => b.status !== 'archived')
notifications.value.filter(n => n.id !== id)
users.map(u => u.email)
```

```typescript
// ✅ CORRECT — descriptive variable names
const searchQuery = ref('')
const selectedBackupId = ref<string | null>(null)
const isLoading = ref(false)

// ❌ WRONG — abbreviated or vague names
const sq = ref('')
const selId = ref<string | null>(null)
const loading = ref(false)  // "loading" is ambiguous — loading what?
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
import type { Backup } from '../types'

export const useBackupStore = defineStore('backups', () => {
  const backups = ref<Backup[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  const activeBackups = computed(() =>
    backups.value.filter(backup => backup.status === 'active')
  )

  async function fetchBackups(): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      const response = await fetch('/api/backups')
      if (!response.ok) {
        throw new Error('Failed to fetch backups')
      }

      backups.value = await response.json()
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
      const matchesStatus = showArchived.value || backup.status !== 'archived'
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

**Rule:** Persist only state that must survive a page reload: auth tokens, remembered user preferences, UI settings, or similarly durable data. Never persist loading flags, error messages, transient search queries, temporary selections, or anything that should reset naturally when the page is refreshed. Prefer `pick` to whitelist persisted fields explicitly instead of persisting the whole store by default.

```typescript
// ✅ CORRECT — persist only durable auth fields
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
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
    pick: ['token', 'rememberMe'],
  },
})
```

```typescript
// ✅ CORRECT — preferences are durable, so persisting the whole store is reasonable
export const usePreferencesStore = defineStore('preferences', () => {
  const sidebarCollapsed = ref(false)
  const theme = ref<'light' | 'dark'>('light')
  const tablePageSize = ref(20)

  function setTheme(nextTheme: 'light' | 'dark'): void {
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
// ✅ CORRECT — single source of truth, imported everywhere
// constants/backups.ts
export const BACKUP_STATUS_ACTIVE = 'active' as const
export const BACKUP_STATUS_FAILED = 'failed' as const
export const BACKUP_STATUS_ARCHIVED = 'archived' as const

export const MAX_BACKUP_RETENTION_DAYS = 90

// composables/useBackups.ts
import { BACKUP_STATUS_ARCHIVED } from '@/constants/backups'

const filteredBackups = computed(() =>
  backups.value.filter(backup => backup.status !== BACKUP_STATUS_ARCHIVED)
)
```

```typescript
// ❌ WRONG — same string hardcoded in multiple places
// composables/useBackups.ts
backups.value.filter(backup => backup.status !== 'archived')

// composables/useBackupSearch.ts
const matchesStatus = showArchived.value || backup.status !== 'archived'  // duplicate!

// components/BackupBadge.vue
const badgeClass = props.status === 'archived' ? 'bg-gray-400' : 'bg-green-500'  // duplicate!
```

```typescript
// ❌ WRONG — same number used in multiple places without a name
setTimeout(poll, 30000)        // what does 30000 mean?
setTimeout(healthCheck, 30000) // is it intentionally the same?

// ✅ CORRECT — named constant, intent is clear
const POLLING_INTERVAL_MS = 30_000
setTimeout(poll, POLLING_INTERVAL_MS)
setTimeout(healthCheck, POLLING_INTERVAL_MS)
```

## Pattern 10: Route Organization — Named Routes, Lazy Loading, Typed Meta, Reactive Params

**Why:** Hardcoded paths like `router.push('/backups/bk-001')` break silently when you rename routes. Eagerly imported route components bloat the initial bundle. Untyped `route.meta` gives you `unknown` everywhere. Destructured `route.params` loses reactivity and causes stale data.

**Rule:** Always navigate by route name, never by path string. Lazy-load every route component with dynamic `import()`. Type `RouteMeta` globally so guards and components get type safety. Read route params through `computed()` to stay reactive — never destructure `route.params` directly.

```typescript
// ✅ CORRECT — named routes, lazy-loaded, typed meta
// src/app/router.ts
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: () => import('@/app/AppLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: 'backups',
          name: 'backups',
          component: () => import('@/features/backups/BackupListPage.vue'),
          meta: { title: 'Backups' },
        },
        {
          path: 'backups/:id',
          name: 'backup-detail',
          component: () => import('@/features/backups/BackupDetailPage.vue'),
          meta: { title: 'Backup Details' },
        },
      ],
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/app/NotFoundPage.vue'),
    },
  ],
})
```

```typescript
// ✅ CORRECT — type RouteMeta globally
// src/app/router.d.ts
import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    title?: string
    requiredRole?: 'admin' | 'viewer' | 'editor'
  }
}
```

```typescript
// ✅ CORRECT — navigate by name, read params reactively
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

// Navigate by name — rename the path later without breaking this
router.push({ name: 'backup-detail', params: { id: 'bk-001' } })

// Reactive param — updates when URL changes
const backupId = computed(() => route.params.id as string)
```

```typescript
// ❌ WRONG — hardcoded path, breaks silently if path changes
router.push('/backups/bk-001')
router.push(`/backups/${id}`)
```

```typescript
// ❌ WRONG — eagerly imported, included in main bundle even if never visited
import SettingsPage from '@/features/settings/SettingsPage.vue'

{
  path: 'settings',
  component: SettingsPage,  // loaded on startup, wastes bandwidth
}
```

```typescript
// ❌ WRONG — destructured params, loses reactivity
const { id } = route.params  // plain string snapshot, goes stale on navigation

// ❌ WRONG — untyped meta, guard has no type safety
if (to.meta.requiresAuth) {  // 'unknown', no autocomplete, no compile-time check
}
```
