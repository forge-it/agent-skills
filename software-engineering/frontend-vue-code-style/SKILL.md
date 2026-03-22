---
name: Vue Code Style
description: Patterns and conventions for writing clean, maintainable Vue 3 applications. Use when writing or reviewing Vue components, composables, stores, or project structure — enforces consistent data flow, component design, and type safety across the codebase.
vibe: Keeps Vue codebases predictable, traceable, and free of spaghetti.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.1"
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

**Rule:** When a component mixes data logic with rendering, split it. The container handles data (fetch, filter, mutate, error handling). The presenter handles display (template, styles, user interaction). The presenter receives everything via props and reports via emits — zero data fetching, zero business logic.
```vue
<!-- ✅ Container — data logic, no template -->
<!-- BackupListContainer.vue -->
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import BackupListPresenter from './BackupListPresenter.vue'
import type { Backup } from './types'

const backups = ref<Backup[]>([])
const search = ref('')
const isLoading = ref(false)
const error = ref<string | null>(null)

const filtered = computed(() =>
  backups.value.filter(b =>
    b.name.toLowerCase().includes(search.value.toLowerCase())
  )
)

async function fetchBackups(): Promise<void> {
  isLoading.value = true
  error.value = null
  try {
    const res = await fetch('/api/backups')
    backups.value = await res.json()
  } catch {
    error.value = 'Failed to load backups'
  } finally {
    isLoading.value = false
  }
}

function deleteBackup(id: string): void {
  backups.value = backups.value.filter(b => b.id !== id)
}

onMounted(fetchBackups)
</script>

<template>
  <BackupListPresenter
    :backups="filtered"
    :is-loading="isLoading"
    :error="error"
    v-model:search="search"
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

defineEmits<{
  delete: [id: string]
  retry: []
}>()
</script>

<template>
  <div>
    <input v-model="search" placeholder="Search…" />
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
