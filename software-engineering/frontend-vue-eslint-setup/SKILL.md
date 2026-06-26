---
name: frontend-vue-eslint-setup
description: One-time setup of eslint.config.js for a NEW Vue 3 project so the feature-based architecture (features → shared/domains → shared foundation) and container/presenter discipline from frontend-vue-development are enforced by the linter — and therefore by CI — from the first commit. Use when bootstrapping a new Vue project's lint config, or adding architecture enforcement to a Vue project that does not have it yet.
vibe: Locks the architecture into CI so structure can't drift.
license: UNLICENSED
metadata:
  author: Cristian
  version: "0.0.1"
---

# Vue ESLint Architecture Enforcement Setup

This is a **one-time setup skill**. It produces a single `eslint.config.js`
that makes the project structure from `frontend-vue-development` a thing the
build *checks*, not a thing people *remember*. A boundary written only in a
doc rots — someone deep-imports across a layer in a hurry, review misses it,
and six months later the dependency graph is tangled. Encoded as a lint rule
set to `error`, the same mistake fails `npm run lint` and blocks the merge.

You do not need an extra dependency (`eslint-plugin-boundaries` etc.). ESLint
flat config lets you define a custom plugin **inline**, so the whole thing is
one self-contained file you drop in.

## When to use

- Bootstrapping a **new** Vue 3 + TypeScript + Vite project → enforce at
  `error` from the first commit (a greenfield project has zero violations,
  so there is nothing to ratchet).
- Adding enforcement to an **existing** project that has none → see
  [Severity: new project vs retrofit](#severity-new-project-vs-retrofit);
  you start at `warn` and ratchet to `error`.

Run this once. After the config exists, you do not re-run this skill.

## What it enforces

Two independent concerns, matching `frontend-vue-development`:

**1. One-way dependency direction between layers.**

```
features/  →  shared/domains/  →  shared/ (foundation)
```

- A feature may import the shared foundation and shared domain modules.
- A feature must **never** import another feature.
- `shared/` (any tier) must **never** import from `features/`.
- A `shared/domains/<x>` module must not import another `shared/domains/<y>`.
- The `shared/` foundation must not import from `shared/domains/`.

**2. Container/presenter discipline.**

- A route `*Page.vue` must not import its own feature's `api/` (it fetches
  through composables).
- A `*Presenter.vue` must not import `vue-router` or any Pinia store
  (navigation and state are owned by the container and passed via props).

These encode separation of concerns and single responsibility: each layer has
one reason to exist, and the dependency arrows only ever point one way.

## Step 1 — Install dependencies

```bash
npm install -D eslint @eslint/js typescript-eslint eslint-plugin-vue \
  eslint-config-prettier globals
```

(`prettier` itself is separate; `eslint-config-prettier` only turns off
formatting rules so ESLint and Prettier don't fight.)

## Step 2 — Confirm the `@` → `src` alias

The boundary rules resolve imports written as `@/features/...` and
`@/shared/...`. The `@` alias **must** map to `src/`. Confirm both files:

```ts
// vite.config.ts
resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } }
```

```jsonc
// tsconfig.app.json
"compilerOptions": { "baseUrl": ".", "paths": { "@/*": ["./src/*"] } }
```

If the project uses a different alias, change the `"@/"` checks in
`resolveImportToSrc` below to match.

## Step 3 — Create `eslint.config.js`

Drop this in at the project root **verbatim**. The custom plugin is named
`architecture` (rename it to your project if you prefer, but keep it
consistent — it prefixes every rule id).

```js
import path from "node:path";
import js from "@eslint/js";
import eslintConfigPrettier from "eslint-config-prettier/flat";
import pluginVue from "eslint-plugin-vue";
import globals from "globals";
import tseslint from "typescript-eslint";

// =========================================================================
// Container / presenter discipline
// =========================================================================

const noFeatureApiInPages = {
  meta: {
    type: "problem",
    docs: {
      description: "Route page components must not import their own feature's API module. Route pages should fetch data through composables.",
    },
    messages: {
      noFeatureApiInPages: "'{{ filename }}' must not import its own feature API ('{{ source }}'). Route pages should fetch data through composables.",
    },
  },
  create(context) {
    const filename = context.filename;
    const isPage = filename.includes("/features/") && filename.endsWith("Page.vue");
    if (!isPage) return {};

    const featureMatch = filename.match(/src\/features\/([^/]+)\//);
    if (!featureMatch) return {};
    const feature = featureMatch[1];

    return {
      ImportDeclaration(node) {
        if (typeof node.source.value !== "string") return;
        const source = node.source.value;

        const isOwnFeatureApi =
          source === `@/features/${feature}/api` ||
          source === `@/features/${feature}/api/` ||
          source.startsWith(`@/features/${feature}/api/`) ||
          source === `../api` ||
          source.startsWith(`../api/`);

        if (isOwnFeatureApi) {
          context.report({
            node,
            messageId: "noFeatureApiInPages",
            data: { filename: filename.split("/").pop() ?? filename, source },
          });
        }
      },
    };
  },
};

const noRouterStoreInPresenters = {
  meta: {
    type: "problem",
    docs: {
      description: "Presenter components must not import vue-router or Pinia stores directly. Navigation and state should be owned by containers and passed via props.",
    },
    messages: {
      noVueRouter: "'{{ filename }}' must not import 'vue-router'. Navigation should be delegated to the container via emits.",
      noSharedStores: "'{{ filename }}' must not import shared stores. State should be owned by composables and passed to presenters via props.",
      noFeatureStores: "'{{ filename }}' must not import feature stores. State should be owned by composables and passed to presenters via props.",
    },
  },
  create(context) {
    const filename = context.filename;
    const isPresenter = filename.endsWith("Presenter.vue");
    if (!isPresenter) return {};

    return {
      ImportDeclaration(node) {
        if (typeof node.source.value !== "string") return;
        if (node.importKind === "type") return;
        const source = node.source.value;

        if (source === "vue-router") {
          context.report({ node, messageId: "noVueRouter", data: { filename: filename.split("/").pop() ?? filename } });
          return;
        }
        if (source === "@/shared/stores" || source.startsWith("@/shared/stores/")) {
          context.report({ node, messageId: "noSharedStores", data: { filename: filename.split("/").pop() ?? filename } });
          return;
        }
        if (source.startsWith("@/features/") && source.includes("/stores/")) {
          context.report({ node, messageId: "noFeatureStores", data: { filename: filename.split("/").pop() ?? filename } });
        }
      },
    };
  },
};

// =========================================================================
// Architectural boundary rules — one-way dependency direction:
//   features/  ->  shared/domains/  ->  shared/ (foundation)
//
// These reason about the *resolved* module path under src/ (both "@/..."
// aliases and relative "./" / "../" imports) and cover static imports as
// well as re-exports ("export ... from"). Dynamic import() — used by the
// router for lazy pages — is intentionally NOT constrained.
// =========================================================================

const SRC_MARKER = "/src/";

// Absolute file path -> module path relative to src/ (e.g. "features/jobs/JobsPage.vue").
function moduleUnderSrc(filename) {
  const normalized = filename.split(path.sep).join("/");
  if (!normalized.includes(SRC_MARKER)) return null;
  return normalized.split(SRC_MARKER).pop() ?? null;
}

// Import source -> module path relative to src/, or null if it is not an internal module.
function resolveImportToSrc(filename, source) {
  if (typeof source !== "string") return null;
  if (source.startsWith("@/")) return source.slice(2);
  if (source.startsWith("./") || source.startsWith("../")) {
    const self = moduleUnderSrc(filename);
    if (!self) return null;
    const resolved = path.posix.normalize(path.posix.join(path.posix.dirname(self), source));
    return resolved.startsWith("..") ? null : resolved;
  }
  return null;
}

function featureName(modulePath) {
  return modulePath?.match(/^features\/([^/]+)(?:\/|$)/)?.[1] ?? null;
}

function domainName(modulePath) {
  return modulePath?.match(/^shared\/domains\/([^/]+)(?:\/|$)/)?.[1] ?? null;
}

function isUnderShared(modulePath) {
  return modulePath?.startsWith("shared/") ?? false;
}

function isUnderDomains(modulePath) {
  return modulePath?.startsWith("shared/domains/") ?? false;
}

function shortName(filename) {
  return filename.split("/").pop() ?? filename;
}

// Run `check` for every import / re-export that has a source string.
function onEverySource(check) {
  function handle(node) {
    if (!node.source || typeof node.source.value !== "string") return;
    check(node, node.source.value);
  }
  return {
    ImportDeclaration: handle,
    ExportNamedDeclaration: handle,
    ExportAllDeclaration: handle,
  };
}

const noCrossFeatureImports = {
  meta: {
    type: "problem",
    docs: { description: "A feature must not import from another feature. Lift shared code to the shared/ foundation (generic) or shared/domains/ (cross-feature concept)." },
    messages: {
      crossFeature: "'{{ filename }}' must not import from another feature ('{{ source }}'). Lift the shared code to the shared/ foundation (if generic) or to shared/domains/ (if a cross-feature business concept).",
    },
  },
  create(context) {
    const ownFeature = featureName(moduleUnderSrc(context.filename));
    if (!ownFeature) return {};
    return onEverySource((node, source) => {
      const targetFeature = featureName(resolveImportToSrc(context.filename, source));
      if (targetFeature && targetFeature !== ownFeature) {
        context.report({ node, messageId: "crossFeature", data: { filename: shortName(context.filename), source } });
      }
    });
  },
};

const noFeatureImportsInShared = {
  meta: {
    type: "problem",
    docs: { description: "Code under shared/ must not import from features/. Dependencies flow features -> shared, never the reverse." },
    messages: {
      featureInShared: "'{{ filename }}' lives under shared/ and must not import from a feature ('{{ source }}'). Dependencies flow features -> shared, never the reverse.",
    },
  },
  create(context) {
    if (!isUnderShared(moduleUnderSrc(context.filename))) return {};
    return onEverySource((node, source) => {
      if (featureName(resolveImportToSrc(context.filename, source))) {
        context.report({ node, messageId: "featureInShared", data: { filename: shortName(context.filename), source } });
      }
    });
  },
};

const noCrossDomainImports = {
  meta: {
    type: "problem",
    docs: { description: "A shared domain module must not import from another shared domain module. Domain modules depend on the shared foundation, not on each other." },
    messages: {
      crossDomain: "'{{ filename }}' must not import from another shared domain module ('{{ source }}'). Domain modules depend on the shared foundation, not on each other.",
    },
  },
  create(context) {
    const ownDomain = domainName(moduleUnderSrc(context.filename));
    if (!ownDomain) return {};
    return onEverySource((node, source) => {
      const targetDomain = domainName(resolveImportToSrc(context.filename, source));
      if (targetDomain && targetDomain !== ownDomain) {
        context.report({ node, messageId: "crossDomain", data: { filename: shortName(context.filename), source } });
      }
    });
  },
};

const noDomainImportsInFoundation = {
  meta: {
    type: "problem",
    docs: { description: "The shared/ foundation must not import from shared/domains/. The foundation is domain-agnostic; domain modules depend on it, not the reverse." },
    messages: {
      domainInFoundation: "'{{ filename }}' is part of the shared foundation and must not import from shared/domains/ ('{{ source }}'). The foundation is domain-agnostic; domain modules depend on it, not the reverse.",
    },
  },
  create(context) {
    const self = moduleUnderSrc(context.filename);
    if (!isUnderShared(self) || isUnderDomains(self)) return {};
    return onEverySource((node, source) => {
      if (isUnderDomains(resolveImportToSrc(context.filename, source))) {
        context.report({ node, messageId: "domainInFoundation", data: { filename: shortName(context.filename), source } });
      }
    });
  },
};

const architecturePlugin = {
  name: "architecture",
  rules: {
    "no-feature-api-in-pages": noFeatureApiInPages,
    "no-router-store-in-presenters": noRouterStoreInPresenters,
    "no-cross-feature-imports": noCrossFeatureImports,
    "no-feature-imports-in-shared": noFeatureImportsInShared,
    "no-cross-domain-imports": noCrossDomainImports,
    "no-domain-imports-in-foundation": noDomainImportsInFoundation,
  },
};

export default tseslint.config(
  { ignores: ["dist/**", "coverage/**"] },

  // Application source.
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended, ...pluginVue.configs["flat/recommended"]],
    files: ["src/**/*.{js,mjs,cjs,ts,vue}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: globals.browser,
      parserOptions: { parser: tseslint.parser },
    },
    plugins: { architecture: architecturePlugin },
    rules: {
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      // Project preference: keep the stricter recommended default for `any`.
      // Uncomment the next line ONLY if the project decides to allow `any`.
      // "@typescript-eslint/no-explicit-any": "off",

      // New project => enforce at "error" from commit one.
      "architecture/no-feature-api-in-pages": "error",
      "architecture/no-router-store-in-presenters": "error",
      "architecture/no-cross-feature-imports": "error",
      "architecture/no-feature-imports-in-shared": "error",
      "architecture/no-cross-domain-imports": "error",
      "architecture/no-domain-imports-in-foundation": "error",
    },
  },

  // Node-side config files: not application code, so the app rules don't apply.
  {
    files: ["vite.config.ts", "eslint.config.js", "prettier.config.js"],
    languageOptions: { globals: globals.node },
    plugins: { architecture: architecturePlugin },
    rules: {
      "architecture/no-feature-api-in-pages": "off",
      "architecture/no-router-store-in-presenters": "off",
    },
  },

  // Tests legitimately import APIs/stores directly to set up the unit under
  // test, so the container/presenter rules are relaxed here. The architectural
  // boundary rules stay ON — a test crossing a feature boundary is still a
  // smell — and `no-explicit-any` stays ON: an `any` mock makes a test pass
  // against a shape that no longer matches reality. For typed test doubles
  // without `any`, see frontend-vue-code-style "No `any`".
  {
    files: ["src/**/*.test.ts", "src/**/*.spec.ts"],
    rules: {
      "architecture/no-feature-api-in-pages": "off",
      "architecture/no-router-store-in-presenters": "off",
    },
  },

  // Must be LAST: turns off rules that conflict with Prettier formatting.
  eslintConfigPrettier,
);
```

## Step 4 — Wire the lint scripts

```jsonc
// package.json
"scripts": {
  "lint": "eslint .",
  "lint:fix": "eslint . --fix"
}
```

`eslint .` exits non-zero on any `error`, so wiring `npm run lint` into CI is
what turns the rules into a merge gate. Without that CI step, the rules only
report locally.

## Step 5 — Verify enforcement actually works

Do not trust a rule you have not seen fire. Create two throwaway probe files,
lint them, confirm the errors, then delete them:

```bash
printf 'import { x } from "@/features/jobs";\nexport const probe = x;\n' > src/features/dashboard/__probe.ts
printf 'import { x } from "@/features/jobs";\nexport const probe = x;\n' > src/shared/utils/__probe.ts
npx eslint src/features/dashboard/__probe.ts src/shared/utils/__probe.ts   # expect 2 errors
rm src/features/dashboard/__probe.ts src/shared/utils/__probe.ts
```

You should see `architecture/no-cross-feature-imports` on the first and
`architecture/no-feature-imports-in-shared` on the second. (Replace the paths
with real folders that exist in the project.)

## Understanding the rules (so you can adapt them)

The mechanism, in one sentence: **an ESLint rule is a visitor over the parsed
syntax tree; an architecture rule keys off *where the file lives*
(`context.filename`) and *what it imports* (`node.source.value`), maps both to
a layer, and reports when the edge points the wrong way.**

- `moduleUnderSrc(filename)` → the file's path relative to `src/`, e.g.
  `features/backups/components/Foo.vue`. This is "which layer am I in".
- `resolveImportToSrc(filename, source)` → the import target's path relative to
  `src/`, normalizing both `@/...` aliases and relative `./`/`../` imports.
  This is "which layer is the target".
- `featureName` / `domainName` / `isUnderShared` / `isUnderDomains` classify a
  path into a layer.
- Each rule opts out early (`return {}`) when the file is not in the layer it
  governs, then reports forbidden edges.
- `onEverySource` registers the same check on `ImportDeclaration`,
  `ExportNamedDeclaration`, and `ExportAllDeclaration` — because a barrel
  re-export (`export { X } from "@/features/jobs"`) creates a dependency edge
  just like an import does.

**Deliberate gaps** (know what you do *not* catch):

- Dynamic `import()` is not visited (it parses as `ImportExpression`), so the
  router's `() => import("@/features/x/XPage.vue")` lazy loads stay legal.
- `app/` is unconstrained — it is allowed to import feature barrels and pages
  to wire routing.

## Severity: new project vs retrofit

- **New project:** every rule at `error`. There are no violations to clean up,
  so there is no reason to soften it.
- **Existing project with violations:** set the four boundary rules to `warn`
  first so CI stays green, run `npm run lint` to get the list, fix the
  violations (most are usually cross-feature *type* imports that should be
  promoted to `shared/domains/` or `shared/types/`), then flip to `error` once
  the count reaches zero. Add a note to `CLAUDE.md`: "boundaries are
  lint-enforced; do not add new violations." Never leave a boundary rule at
  `warn` permanently — a warning that never becomes an error trains everyone to
  ignore it.

## Customization knobs

- **Plugin name** — `architecture` is arbitrary; rename it, but keep it
  consistent across the plugin definition, the `plugins: {}` keys, and every
  rule id.
- **Alias** — if the project does not use `@` → `src`, update the `"@/"`
  branch in `resolveImportToSrc`.
- **`any` policy** — the config keeps the strict recommended default. Allowing
  `any` is a project choice; uncomment the marked line only if you decide to.
- **More rules** — the same skeleton extends to other invariants (e.g. "only
  `app/` may import `vue-router`", "no feature may import another feature's
  `types/`"). Copy a rule, change the classification, register it, set it to
  `error`.
