# UML System Overview

เอกสารนี้เป็น UML กลางของระบบสำหรับใช้สื่อสาร architecture กับทีม โดยใช้ Mermaid ใน Markdown เพื่อให้แก้ไขง่ายและเป็นส่วนหนึ่งของ SSOT

## Package Diagram

```mermaid
flowchart TB
    UI["UI Layer"] --> VM["Presentation / ViewModel"]
    VM --> APP["Application Services"]
    APP --> DOMAIN["Domain"]
    APP --> INFRA["Infrastructure"]
    INFRA --> DB["SQLite / SQLAlchemy"]
    INFRA --> FS["Filesystem / Media Library"]
    INFRA --> EXT["FFmpeg / External Tools"]
```

## Component Responsibilities

```mermaid
classDiagram
    class ProductDashboardViewModel {
        +load()
        +status
        +products
    }

    class ProductApplicationService {
        +create_product(command)
        +list_products()
    }

    class SqlAlchemyUnitOfWork {
        +products
        +commit()
        +rollback()
    }

    class SqlAlchemyProductRepository {
        +add(product)
        +get_by_code(product_code)
        +list_summaries()
    }

    class Product {
        +id
        +product_code
        +product_name
    }

    ProductDashboardViewModel --> ProductApplicationService
    ProductApplicationService --> SqlAlchemyUnitOfWork
    SqlAlchemyUnitOfWork --> SqlAlchemyProductRepository
    SqlAlchemyProductRepository --> Product
```

## Product Creation Sequence

```mermaid
sequenceDiagram
    actor User
    participant View as UI View
    participant VM as ProductDashboardViewModel
    participant App as ProductApplicationService
    participant UoW as SqlAlchemyUnitOfWork
    participant Repo as SqlAlchemyProductRepository
    participant DB as SQLite

    User->>View: submit create product
    View->>VM: trigger command
    VM->>App: create_product(command)
    App->>UoW: open
    UoW->>Repo: get_by_code(product_code)
    Repo->>DB: SELECT product
    DB-->>Repo: result
    App->>Repo: add(product)
    Repo->>DB: INSERT product
    App->>UoW: commit()
    UoW->>DB: COMMIT
    App-->>VM: product_id
    VM-->>View: refresh state
```

## Workflow State Direction

```mermaid
stateDiagram-v2
    [*] --> CREATED
    CREATED --> ASSETS_READY
    ASSETS_READY --> PREVIEW_PENDING
    PREVIEW_PENDING --> PREVIEW_RENDERING
    PREVIEW_RENDERING --> PREVIEW_RENDERED
    PREVIEW_RENDERED --> QUALITY_CHECK_PENDING
    QUALITY_CHECK_PENDING --> QUALITY_CHECKED
    QUALITY_CHECKED --> NEEDS_HUMAN_REVIEW
    NEEDS_HUMAN_REVIEW --> APPROVED
    NEEDS_HUMAN_REVIEW --> REJECTED
    APPROVED --> FINAL_RENDER_PENDING
    FINAL_RENDER_PENDING --> FINAL_RENDERING
    FINAL_RENDERING --> FINAL_RENDERED
    FINAL_RENDERED --> DONE
```

