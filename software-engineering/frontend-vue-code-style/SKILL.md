---
name: Vue Code Style
description: Patterns and conventions for writing clean, maintainable Vue 3 applications. Use when writing or reviewing Vue components, composables, stores, or project structure — enforces consistent data flow, component design, and type safety across the codebase.
vibe: Keeps Vue codebases predictable, traceable, and free of spaghetti.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.2"
---

# Vue Code Style — Patterns & Conventions

A living collection of patterns that every component, composable, and store in this codebase must follow. When in doubt, check here first.

---

## Pattern 1: Props Down, Emits Up (One-Way Data Flow)

**Why:** Without it, child components mutate parent state directly, nobody can trace where a change came from, and debugging becomes a nightmare.

**Rule:** A child component never modifies data it receives. It declares what it accepts via `defineProps<T>()`, and reports user actions via `defineEmits<T>()`. The parent owns the state and decides what to do.
```vue

---
name: Vue Code Style
description: Patterns and conventions for writing clean, maintainable Vue 3 applications. Use when writing or reviewing Vue components, composables, stores, or project structure — enforces consistent data flow, component design, and type safety across the codebase.
vibe: Keeps Vue codebases predictable, traceable, and free of spaghetti.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.1.0"
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
      <tr v-for="b in backups" :key="b.id">
        <td>{{ b.name }}</td>
        <td><button @click="$emit('delete', b.id)">Delete</button></td>
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
    backups.value.filter(b => {
      const matchesSearch = b.name
        .toLowerCase()
        .includes(searchQuery.value.toLowerCase())
      const matchesStatus = showArchived.value || b.status !== 'archived'
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
    notifications.value = notifications.value.filter(n => n.id !== id)
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