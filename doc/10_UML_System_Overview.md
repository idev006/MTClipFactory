# UML System Overview

เอกสารนี้เป็น UML กลางของระบบสำหรับใช้สื่อสาร architecture กับทีม โดยใช้ Mermaid ใน Markdown เพื่อให้แก้ไขง่ายและเป็นส่วนหนึ่งของ SSOT

## Package Diagram

```mermaid
flowchart TB
    UI["UI Layer"] --> VM["Presentation / ViewModel"]
    VM --> LIB["Resource Library Management"]
    VM --> FAC["Video Assembly Factory"]
    LIB --> APP["Shared Application Services"]
    FAC --> APP
    APP --> DOMAIN["Domain"]
    APP --> INFRA["Infrastructure"]
    INFRA --> DB["SQLite / SQLAlchemy"]
    INFRA --> FS["Filesystem / Media Library"]
    INFRA --> EXT["FFmpeg / External Tools"]
```

## Module Relationship

```mermaid
flowchart LR
    L["Resource Library Management"] -->|"prepared assets"| F["Video Assembly Factory"]
    L -->|"product, asset, tag SSOT"| DB["Shared SQLite"]
    F -->|"recipe, job, output state"| DB
```

## Component Responsibilities

```mermaid
classDiagram
    class ResourceLibraryModule {
        +product_service
        +asset_intake_service
    }

    class VideoAssemblyFactoryModule {
        +build_recipe()
        +queue_preview()
        +approve_recipe()
        +queue_final_render()
    }

    class ProductLibraryWindow {
        +show()
        +create_product()
        +update_product()
        +delete_product()
    }

    class AssetLibraryWindow {
        +show()
        +register_asset()
        +refresh()
    }

    class TagDictionaryWindow {
        +show()
        +create_tag()
        +assign_tag()
    }

    class ProductLibraryViewModel {
        +load()
        +create_product(command)
        +get_product(product_id)
        +update_product(command)
        +delete_product(product_id)
        +status
        +products
        +feedback
    }

    class AssetLibraryViewModel {
        +load()
        +register_asset(...)
        +products
        +assets
        +feedback
    }

    class TagDictionaryViewModel {
        +load()
        +create_tag(...)
        +assign_tag_to_asset(...)
        +tags
        +assets
    }

    class ProductApplicationService {
        +create_product(command)
        +get_product(product_id)
        +update_product(command)
        +delete_product(product_id)
        +list_products()
    }

    class AssetIntakeService {
        +register_asset(command)
        +list_assets(product_id)
    }

    class TagManagementService {
        +create_tag(command)
        +list_tags(tag_group)
        +assign_tag_to_asset(command)
    }

    class SqlAlchemyUnitOfWork {
        +products
        +assets
        +tags
        +commit()
        +rollback()
    }

    class SqlAlchemyProductRepository {
        +add(product)
        +get_by_code(product_code)
        +list_summaries()
    }

    class SqlAlchemyAssetRepository {
        +add(asset)
        +get_by_id(asset_id)
        +get_by_code(asset_code)
        +list_summaries(product_id)
    }

    class SqlAlchemyTagRepository {
        +add(tag)
        +get_by_id(tag_id)
        +get_by_name_and_group(name, group)
        +list_summaries(tag_group)
    }

    class Product {
        +id
        +product_code
        +product_name
    }

    class Asset {
        +id
        +asset_code
        +asset_type
        +file_name
        +status
    }

    class Tag {
        +id
        +tag_name
        +tag_group
    }

    ProductLibraryWindow --> ProductLibraryViewModel
    AssetLibraryWindow --> AssetLibraryViewModel
    TagDictionaryWindow --> TagDictionaryViewModel
    ResourceLibraryModule --> ProductApplicationService
    ResourceLibraryModule --> AssetIntakeService
    ResourceLibraryModule --> TagManagementService
    VideoAssemblyFactoryModule --> ProductApplicationService
    ProductLibraryViewModel --> ProductApplicationService
    AssetLibraryViewModel --> ProductApplicationService
    AssetLibraryViewModel --> AssetIntakeService
    TagDictionaryViewModel --> TagManagementService
    TagDictionaryViewModel --> AssetIntakeService
    ProductApplicationService --> SqlAlchemyUnitOfWork
    AssetIntakeService --> SqlAlchemyUnitOfWork
    TagManagementService --> SqlAlchemyUnitOfWork
    SqlAlchemyUnitOfWork --> SqlAlchemyProductRepository
    SqlAlchemyUnitOfWork --> SqlAlchemyAssetRepository
    SqlAlchemyUnitOfWork --> SqlAlchemyTagRepository
    SqlAlchemyProductRepository --> Product
    SqlAlchemyAssetRepository --> Asset
    SqlAlchemyTagRepository --> Tag
```

## Product Creation Sequence

```mermaid
sequenceDiagram
    actor User
    participant View as ProductLibraryWindow
    participant VM as ProductLibraryViewModel
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

## Asset Intake Sequence

```mermaid
sequenceDiagram
    actor User
    participant View as AssetLibraryWindow
    participant VM as AssetLibraryViewModel
    participant App as AssetIntakeService
    participant Store as LocalAssetStorage
    participant Analyze as MetadataAnalyzer
    participant UoW as SqlAlchemyUnitOfWork
    participant Repo as SqlAlchemyAssetRepository
    participant DB as SQLite

    User->>View: choose product, asset type, source file
    View->>VM: register_asset(...)
    VM->>App: register_asset(command)
    App->>Store: store_asset(...)
    Store-->>App: stored file path
    App->>Analyze: analyze(file_path)
    Analyze-->>App: metadata
    App->>UoW: open
    UoW->>Repo: add(asset)
    Repo->>DB: INSERT asset
    App->>UoW: commit()
    UoW->>DB: COMMIT
    App-->>VM: asset_id
    VM-->>View: refresh state
```

## Tag Assignment Sequence

```mermaid
sequenceDiagram
    actor User
    participant View as TagDictionaryWindow
    participant VM as TagDictionaryViewModel
    participant App as TagManagementService
    participant UoW as SqlAlchemyUnitOfWork
    participant TagRepo as SqlAlchemyTagRepository
    participant AssetRepo as SqlAlchemyAssetRepository
    participant DB as SQLite

    User->>View: select tag and asset
    View->>VM: assign_tag_to_asset(...)
    VM->>App: assign_tag_to_asset(command)
    App->>UoW: open
    UoW->>AssetRepo: get_by_id(asset_id)
    UoW->>TagRepo: get_by_id(tag_id)
    UoW->>AssetRepo: assign_tag(asset_id, tag_id)
    AssetRepo->>DB: INSERT asset_tags
    App->>UoW: commit()
    UoW->>DB: COMMIT
    App-->>VM: success
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

## Responsibility Rule

- `Resource Library Management` รับผิดชอบความพร้อมของวัตถุดิบ
- `Video Assembly Factory` รับผิดชอบการประกอบและ workflow ของ output
- ทั้งสองส่วนแชร์ SSOT เดียวกัน แต่ไม่ควรทับความรับผิดชอบกัน
