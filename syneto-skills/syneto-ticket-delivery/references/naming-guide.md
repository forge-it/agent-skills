# Naming things in Syneto code

The reference for stage 7's naming designers. A name should say what a thing is for to the
person reading the call site, without opening its definition. Python is the main stack here;
the team rules (`T1`-`T7`) hold in every language.

- **Names only.** The naming round reviews names. Do not propose moving code, adding types,
  splitting a class or turning constants into an enum. The design advice below explains why a
  name is wrong; it is not a task.
- **Cite a rule by its id:** `T2`, `P4`, `PEP8`. Team rules are `T1`-`T7`, the Python
  principles `P1`-`P6`.
- **When rules disagree:** the repository's gates and its `CLAUDE.md` first, then the Team
  rules, then **python-code-style** and **python-ddd**, then the rest of this guide, then PEP 8.
- **Neighbours count.** Before proposing a name, grep the repository for the same concept. A
  name the codebase already uses for it wins over a better word you would pick (`T5`).

## Names you do not propose to change

These names pre-date the change or leave the repository, so you never propose renaming one
that already exists. A name on this list that the change itself introduces (a new column in
its migration, a new JSON field, a new error code, a new job name) is still judged: propose it
marked "needs his word", and the orchestrator leaves it to the stage 8 report.

- **Anything on the wire or stored.** A database column, table or index in a migration already
  on the target branch;
  a Mongo collection or document key; an Alembic revision; a camelCase JSON field or a Pydantic
  `alias`; a route path or query parameter; an error code (`REMOTE_SUPPORT_NOT_ALLOWED`); an
  event or job name; a `BannerKey` value; a protobuf message or field; an environment variable
  or settings key; a log event name; a Prometheus or alert label (`machine_serial`); a Pulumi
  resource name; a variable an email or Jinja template reads (`{{machine_serial}}`). Renaming
  the Python attribute behind an explicit `Field(alias=...)` is fine only when the alias stays
  and the change added the attribute.
- **A schema field with no explicit alias is itself the wire name** when its model camelises:
  every `BasePantheonModel` subclass (diana, mercurio) and mercurio's `ExternalUrls` set
  `alias_generator = camel_case` with `allow_population_by_field_name = True`, so
  `central_hub_signup` is served as `centralHubSignup` and accepted as both; rest-api's
  `camel_asdict` does the same for dataclass fields. Treat those attribute names as wire.
- **An attribute mapped to storage by its own name is a stored name.** In rest-api a dataclass
  passed to `map_imperatively` without a `properties` entry for that field
  (`adapters/orm/mappers.py`, e.g. `GrantRequest`) takes its column's name; in central-backend
  the `iam/*/entity.py` dataclass fields are the protobuf field names and, through
  `*_fields_mapping`, the Mongo keys. Treat them like a column.
- **Class names Pantheon turns into wire names.** Pantheon derives routing keys, queue names
  and job titles from command, event and schema class names, and FastAPI names the OpenAPI
  document after the schemas. In rest-api that covers every class in `domain/commands.py` and
  `domain/events.py`, every handler function, and every request-body, `response_model` and
  presentation schema (rest-api `CLAUDE.md`, ADR-012). An existing one is never renamed.
- **Codes other systems match on:** license, tier and edition codes are camelCase
  (`hasChronos`, `registeredVms`, `community`) and stay that way.
- **What `src/diana/api-docs/*.md` names.** In syneto-diana those files are the served OpenAPI
  contract (`src/diana/fastapi.py` passes the directory as `docs_directory`).
- **Shared library items** another repository imports: `syneto-pantheon` (`BasePantheonModel`),
  `protolib/` in central-backend, anything a sibling service calls by name.
- **The house's layer vocabulary** from **python-ddd** and the repositories' own base classes:
  `Abstract<Port>`, `Fake<Port>`, `BaseValidator` with its `Validation`/`Validator` family
  (python-ddd §8, rest-api `application/validations/` and `application/validators/`), a port
  declared as a `Protocol` in a `ports.py` (`CompanyVatReader`, `MachineReader`), rest-api's
  `AbstractAsyncUnitOfWork`, `AbstractCoordinatedUnitOfWork`, `AbstractAsyncSqlRepository[T]`
  and the `uow.repo` attribute, `domain/models/<concept>.py`, `infrastructure/gateway/`.
  `Abstract`, `Fake` and `Base` on those are sanctioned; `P5` does not apply to them.
- **Framework hooks and overrides:** `dispatch`, `__call__`, a FastAPI dependency whose name a
  router already injects, a pytest hook, a method a base class or Protocol fixes.

## Casing (PEP8)

- `snake_case`: modules, packages, functions, methods, attributes, parameters, locals.
- `CapWords`: classes, Protocols, exceptions, enums, type aliases and `TypeVar`s.
- `UPPER_CASE`: module constants (PEP 8) and enum members (Rule 16; PEP 8 does not cover them).
- One leading underscore for private. Never a double underscore: it mangles to
  `_ClassName__attr` and forces tests to poke at the mangled name.
- A new exception class ends in `Error` (`EntityNotFoundError`), as most Syneto exceptions
  do, unless it is a control signal that is not an error. An existing `*Exception` stays.
- Acronyms: PEP 8 capitalises the whole acronym in CapWords (`HTTPServerError`), but Syneto code
  spells both ways (`YUMGateway` in central-backend, `YumGateway` and `CompanyVatReader` in
  rest-api). Follow the spelling the neighbouring
  code uses for that acronym. Never propose a rename only to change an acronym's case.

## Principles

**P1. No abbreviations, and no shorthand the project invented.**
python-code-style Rule 1: `elapsed_time_in_days`, never `t`; `repository`, never `repo`, except
rest-api's Unit-of-Work attribute `uow.repo`, which every UoW there already spells that way;
`configuration` or `config` as the neighbours spell it. The shorthand Python and the stack
already settled on stays: `id`, `url`, `uuid`, `json`, `db`, `env`, `args`, `kwargs`, and `uow`
where the repository already spells the Unit of Work that way (rest-api); python-ddd itself
writes `unit_of_work`. `sess_mgr` and `usr_cnt` are out.

**P2. A loop or comprehension variable is the singular of its collection.**
python-code-style Rule 2: `for compute_host in compute_hosts`. When they do not match, rename
the collection, never the loop variable to something generic. `_` only for a value thrown away.

**P3. Do not put types in names.**
No `_str`, `_list`, `_dict`, `_obj`, `_dto`, `_int` suffixes, and no Hungarian prefixes.
Rebinding a name to the parsed value is fine when it is the same value refined
(`port = int(port)`). When it holds something else, it gets a new name.

**P4. Units: let the type carry them, else the name.**
A duration is a `timedelta` where the code already uses one; a raw number keeps a unit suffix
(`timeout_seconds`, `budget_bytes`, `retention_days`). Do not propose a `timedelta` in place of
a suffix: that is a design change.

**P5. No `I`, `Base`, `Impl`, `Interface`, `Mixin`-as-filler decorations.**
- A Protocol or port is named for the capability or the concept (`EntitlementReader`), the
  general name goes to the abstraction, and the specific name goes to the implementation
  (`SqlEntitlementReader`, `HttpEntitlementReader`). The python-ddd `Abstract`/`Fake` names and
  `BaseValidator` above are the exception.
- An enum member does not repeat the enum's name: `RefusalBasis.MAINTENANCE_RULE`, not
  `RefusalBasis.REFUSAL_BASIS_MAINTENANCE_RULE`.

**P6. Under `src/`, no `utils/`, `helpers/`, `common/` or `misc/` folder, and a new module is
named for its capability (`infrastructure/clock.py`, `infrastructure/ids.py`) unless it is
python-ddd's one sanctioned bucket, a layer's `utils.py` for a helper several concepts share**
(python-ddd Project Structure, Rule 6 "No Weak Bucket Folders"). Under `tests/`, `utils/` is
the python-testing §6 home for support modules and is not a finding. Test builders live in
`builders.py` (rest-api, mercurio; diana: `utils/builders.py`) and query or assertion helpers
in `helpers.py`; central-backend has no `builders.py`: `make_*` builders live in
`tests/tools.py`, `build_*` beside query helpers in `helpers.py`. Follow the directory. Item
names keep their concept word even inside a module of the same name (`AlertingServiceError`
in central-backend's `alerting/exceptions.py`): callers import the item by name.

## Python and python-ddd conventions

- **Repository methods (python-ddd §4):** `get(id)` raises when missing, `find_by_id` /
  `find_by_<attribute>` return `None`, `list_<criterion>` returns a list. No `update`, no
  `get_by_fields`. A method named after a domain question, not a SQL shape.
  rest-api's four base repositories (`AbstractAsyncSqlRepository`, `AbstractSyncSqlRepository`,
  `AbstractSyncMongoRepository`, `AbstractAsyncMongoRepository` in `adapters/repository.py`)
  already fix `get`, `get_all`, `get_by_fields`, `get_with_limit_and_offset`,
  `search_with_limit_and_offset`, `get_or_create_by_fields`, `set_by_id`, `delete_by_id`,
  `update` and, on the sync SQL base, `upsert`. central-backend's `CommonRepository`
  (`core/infrastructure/database/blueprints/repository.py`) fixes `find_all`,
  `find_satisfying`, `update`, `update_all` and `get_all`, and its lookups are
  `find_by_<attribute>` as python-ddd spells them. An override or sibling of those is not a
  finding; a new method follows its base.
- **Properties are nouns,** with no `get_` prefix: `product.expiry_date`, not
  `product.get_expiry_date()`. A method that does I/O, computes something costly or goes
  through a port keeps a verb (`get_`, `fetch_`, `load_`, `read_`, `calculate_`); `get_` is
  rest-api's usual verb for that and is not a finding on its own.
- **Conversions:** `to_<target>()` returns a new representation (`to_schema`, `to_dict`); a
  classmethod `from_<source>()` builds one (`from_row`, `from_schema`). `as_` is for a cheap view.
- **Enums (python-code-style Rule 16):** a `StrEnum` class is a singular noun for the set
  (`BackupStatus`), members `UPPER_CASE`; the member value is the wire spelling.
- **Constants (Rule 6):** named for the value's meaning (`IDEMPOTENCY_KEY_HEADER`), not its
  content (`HEADER_STRING`), and defined once in the module that owns the concept.

## Booleans

- A predicate function or method reads as a question and **names its subject**:
  `is_maintenance_expired(product)`, `product.has_remote_support`. `is_unlimited(value)` was
  rejected in a mercurio review ("is_unlimited what?") and became
  `Grant.is_unlimited`; diana's `is_unlimited(grant)` in `domain/supported_actions.py` predates
  the rule and is not precedent.
- A bool attribute, column, parameter or local reads as a true/false statement:
  `is_latest_attempt`, `is_support_contact`, `keep_cache`, `allow_partial`. A bare verb
  (`stop`, `disable_cache`) reads as an order, and a bare noun (`maintenance`) does not say
  which way true points: rename it so it reads as a statement, never by adding `_flag`.
- A keyword-only bool hides little at the call site (`rename(path, overwrite=True)`); a
  positional bool hides its meaning. Note a positional bool on a public function as a remark
  for him, not as a rename.

## Team rules

Cristian's rules for Syneto code, from his reviews. Where they differ from the rest of this
guide, they win. T1 to T4 and T6 admit no deviation. For T5 and T7, a deviation with a
one-line `# why:` that names the constraint (`# why: mirrors the column Central already
exposes`) is not a finding; flag a hollow one (`# why: shorter`).

**T1. No single-letter names, and no abbreviations beyond P1's settled shorthand.** No
exception for loop, comprehension or lambda variables: `for entry in entries`,
`lambda product: product.id`. `_` for a discarded value and a `TypeVar` `T` are the only
single letters.

**T2. Name it after the job it does for its callers, never its mechanism.**
- `LicensingSnapshotWriter` was rejected: the class keeps sync, activation and unlink from
  overwriting each other's licensing data, and the name says "a stored blob, being written".
- Column `pending_slot` (a unique-index trick) became `is_latest_attempt`.
- Words that usually name a mechanism: `Snapshot`, `Writer`, `Blob`, `Lock`, `Cache`,
  `Wrapper`, `Shared`, `Inner`, `Proxy`, `Holder`, `Dict`, `Payload`. They are right only when
  the job *is* that mechanism (a cache module whose purpose is caching).
- Name after what a thing holds, not how it is held: `queue_ledger`, never `shared_queue` for
  a value behind a lock.

**T3. Name a function after what it achieves, not who it calls or how.**
`_ask_mercurio`, `_call_central`, `_hit_iam`, `_do_request` name the plumbing. Say what comes
back or what changes: `_read_remote_support_entitlement`, `_fetch_customer_licenses`. A name
also never hides a side effect: a `get_`/`find_` that writes, a `validate_` that saves, a
`check_` that raises and also sends a notification.

**T4. Say what it holds in the domain's words, never spec slang or a version label.**
`_generosity` (slang from a spec) and "v1 blob / v2 blob" were rejected: say what is stored
(`addons` for Central's 6.0 answer, `licenses` and `grants` for 6.1). Read a field aloud as
"the X of the Y": `activation_key` holds the activation key; `lookup` holding it does not.

**T5. One concept, one name: reuse the approved one.**
- Before a new name, grep for the same concept. In rest-api `serial_number` is the name, so a
  new `machine_serial` there is wrong; in central-backend's alerting the Prometheus label and
  `Alert.machine_serial` already fix `machine_serial`, and that is the neighbour to follow. A
  new name needs a real argument.
- Flag two names for one concept in the change (`grant` here, `entitlement` there, for the
  same thing), and one name for two concepts.
- Wire vocabulary stays at the wire: central-backend says `permitted_channels` in Python
  while the payload says `availableUpgradeChannels`; the wire word lives only in the path and
  field constants.
- Suffixes the repository already reserves keep their meaning: do not add a `*Service` where
  `Service` is taken, a `*Gateway` outside the gateway role, or a `*Reader` that also writes.

**T6. Length, and words that rarely pass alone.**
- Count the snake_case or CapWords words; `Id`, an acronym and a version number count as one.
  Up to four words is normal; five when no shorter name says the same. Propose a longer name
  only beside the shorter option it beats.
- Read the name at a call site without opening its definition. If you cannot say what it
  holds, decides or does, it is vague. Words that rarely pass alone: `Data`, `Info`, `State`,
  `Context`, `Handler`, `Manager`, `Processor`, `Item`, `Value`, `Result`, `Details`,
  `Object`, `process`, `handle`, `do`, `run`, `execute`, `perform`. This is a prompt to look,
  not an automatic fail: a `handle` on a command handler is the pattern's own word.
- Avoid words that read two ways: `full` ("is full" or "may use all"), `valid` ("checked" or
  "should pass"), `active` (licensed, running or selected).

**T7. A binding of one of the repository's own types is named the snake_case of that type,
the same way for every sibling.**
- An attribute always: it is read far from its declaration. `self._product_repository:
  AbstractProductRepository`, `self._notification_gateway: NotificationGateway`, never
  `self._repo` beside `self._gateway`. The `Abstract` prefix drops from the name.
- A parameter or local only when a sibling of a related kind is in scope:
  `def cancel(self, id: JobId)` is fine; `def attach(self, job_id: JobId, plan_id: PlanId)`
  names both.
- Look through `Optional`, `list`, `Callable[[], ...]` factories (`unit_of_work_factory`, or
  `uow_factory` in rest-api). It does not apply to std, FastAPI, SQLAlchemy or primitive types
  (`session`, `request`, `count`).

## Tests

Follow **python-testing** §4 and the repository's own test layout (central-backend:
`tests/<domain>/<category>/`, plain pytest, no `unittest` classes; file names are `test_*.py`
in some domains and `*_test.py` in others, e.g. `tests/alerting/unit/arbiters_test.py`, so a
new file takes its directory's form).

- A test name says the behaviour and the case: `test_<unit>_should_<outcome>_when_<case>`, or
  the shorter `test_<unit>_<outcome>_<case>` the neighbouring tests use. Match the file's
  neighbours. Flag a name that misstates what the test checks, or says only the unit
  (`test_get_customer_details`).
- Fixtures are nouns for what they provide (`expired_product`, `sql_uow`), builders verbs
  (`build_product`, `build_activation_request`; `make_` only where the file's neighbours use it),
  fakes `Fake<Port>`.
- T1 to T7 apply to test code too. Flag only the names the change adds or renames.

## Other stacks

- **React (central-hub, central-ui) and vanilla JS (syneto-os-frontend):** components, types
  and enum objects `PascalCase` with `PascalCase` members (`BackupStatus.Archived`), hooks
  `use<Thing>` only when they call hooks, everything else `camelCase`; the naming rules are
  **frontend-react-code-style** Pattern 4 (hook names), Pattern 6 and Pattern 15. The house
  vanilla JS uses camelCase functions and PascalCase constructors. T1 to T7 apply. Never
  propose renaming an i18n key, a `gt-*` component, an observable-store key, or a field the API
  returns. A Vue repository, if one appears, takes **frontend-vue-code-style**.
- **Rust:** **rust-code-style**'s naming rules, plus T1 to T7.

Sources:
- [PEP 8, naming conventions](https://peps.python.org/pep-0008/#naming-conventions)
- python-code-style Rules 1, 2, 6, 16; python-ddd §4, §8, Project Structure Rule 6;
  python-testing §4, §6; rest-api ADR-012
