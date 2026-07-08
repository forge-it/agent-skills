# TestApp Harness Implementation

This file contains the complete `TestApp` implementation for end-to-end API tests. `/home/cristi/Projects/agent-skills/software-engineering/rust-testing/SKILL.md` is the normative source — the rules for when and how to use the `TestApp` harness live there (Section 13). This implementation is provided here for direct reference by agents creating or extending e2e test infrastructure.

## infra.rs — TestApp: in-process server with per-test database

```rust
// tests/e2e/api/support/infra.rs
// TestApp runs the real router in-process: real repositories on a per-test
// database, an OS-assigned port, and explicit teardown.
use myproject::infrastructure::api::router::build_router;

use crate::common::builders::build_services;
use crate::common::infra::TestDatabase;

pub struct TestApp {
    pub client: reqwest::Client,
    base_url: String,
    server_handle: tokio::task::JoinHandle<()>,
    test_database: TestDatabase,
}

impl TestApp {
    pub async fn new() -> Self {
        let test_database = TestDatabase::new().await;
        let services = build_services(test_database.pool().clone());

        let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address = listener.local_addr().unwrap();
        let server_handle = tokio::spawn(async move {
            axum::serve(listener, build_router(services)).await.unwrap();
        });

        Self {
            client: reqwest::Client::new(),
            base_url: format!("http://{address}"),
            server_handle,
            test_database,
        }
    }

    pub fn url(&self, path: &str) -> String {
        format!("{}{path}", self.base_url)
    }

    pub async fn teardown(self) {
        self.server_handle.abort();
        self.test_database.teardown().await;
    }
}
```
