# Mock Implementations

This file contains the complete hand-written mock implementations and the service tests that consume them. `/home/cristi/Projects/agent-skills/software-engineering/rust-testing/SKILL.md` is the normative source — the rules for when and how to write hand-written port mocks live there (Section 5). These implementations are provided here for direct reference by agents writing unit-test mocks.

## mocks.rs — Multi-port hand-written mock module

```rust
// tests/unit/support/mocks.rs — the canonical home for hand-written port mocks
use std::sync::Arc;

use tokio::sync::Mutex;

#[derive(Clone, Default)]
pub struct MockAuthorRepository {
    pub authors: Arc<Mutex<Vec<Author>>>,
    pub create_result: Arc<Mutex<Option<Result<Author, CreateAuthorError>>>>,
}

impl MockAuthorRepository {
    pub fn with_create_result(result: Result<Author, CreateAuthorError>) -> Self {
        Self {
            create_result: Arc::new(Mutex::new(Some(result))),
            ..Default::default()
        }
    }
}

impl AuthorRepository for MockAuthorRepository {
    async fn create(
        &self,
        request: &CreateAuthorRequest,
    ) -> Result<Author, CreateAuthorError> {
        if let Some(result) = self.create_result.lock().await.take() {
            return result;
        }

        let author = Author::new(AuthorId::new(), request.name.clone());
        self.authors.lock().await.push(author.clone());
        Ok(author)
    }

    async fn find_by_id(&self, id: &AuthorId) -> Result<Option<Author>, FindAuthorError> {
        let authors = self.authors.lock().await;
        Ok(authors.iter().find(|author| author.id() == id).cloned())
    }
}

#[derive(Clone, Default)]
pub struct MockMetrics {
    pub success_count: Arc<Mutex<u64>>,
    pub failure_count: Arc<Mutex<u64>>,
}

impl AuthorMetrics for MockMetrics {
    async fn record_creation_success(&self) {
        *self.success_count.lock().await += 1;
    }

    async fn record_creation_failure(&self) {
        *self.failure_count.lock().await += 1;
    }
}

#[derive(Clone, Default)]
pub struct MockNotifier {
    pub notified_authors: Arc<Mutex<Vec<AuthorId>>>,
}

impl AuthorNotifier for MockNotifier {
    async fn author_created(&self, author: &Author) {
        self.notified_authors.lock().await.push(author.id().clone());
    }
}
```

## author_service.rs — Service tests consuming the mocks

```rust
// tests/unit/application/author_service.rs
use super::super::support::mocks::{MockAuthorRepository, MockMetrics, MockNotifier};

mod create_author {
    use super::*;

    #[tokio::test]
    async fn should_record_success_metric() {
        let repository = MockAuthorRepository::default();
        let metrics = MockMetrics::default();
        let notifier = MockNotifier::default();
        let service = AuthorService::new(repository, metrics.clone(), notifier);
        let request = CreateAuthorRequest {
            name: AuthorName::new("Test Author").unwrap(),
        };

        service.create_author(&request).await.expect("create_author should succeed");

        assert_eq!(*metrics.success_count.lock().await, 1);
        assert_eq!(*metrics.failure_count.lock().await, 0);
    }

    #[tokio::test]
    async fn should_record_failure_metric_on_duplicate() {
        let repository = MockAuthorRepository::with_create_result(
            Err(CreateAuthorError::Duplicate {
                name: AuthorName::new("Existing").unwrap()
            })
        );
        let metrics = MockMetrics::default();
        let notifier = MockNotifier::default();
        let service = AuthorService::new(repository, metrics.clone(), notifier);
        let request = CreateAuthorRequest {
            name: AuthorName::new("Existing").unwrap(),
        };

        let result = service.create_author(&request).await;

        assert!(matches!(result, Err(CreateAuthorError::Duplicate { .. })));
        assert_eq!(*metrics.failure_count.lock().await, 1);
        assert_eq!(*metrics.success_count.lock().await, 0);
    }
}
```
