# UML System Overview

This document is the living UML source of truth for the current implementation.

## Package Diagram

```mermaid
flowchart TB
    UI["UI Layer"] --> VM["Presentation / ViewModel"]
    VM --> LIB["Resource Library Management"]
    VM --> FAC["Video Assembly Factory"]
    VM --> CC["Control Center"]
    LIB --> CORE["Shared Domain + Infrastructure"]
    FAC --> CORE
    CC --> CORE
    CORE --> DB["SQLite / SQLAlchemy"]
    CORE --> FS["Filesystem / Media Library"]
    CORE --> EXT["FFmpeg / FFprobe"]
```

## Current Component Map

```mermaid
classDiagram
    class ResourceLibraryModule {
        +product_service
        +asset_intake_service
        +artifact_generation_service
        +video_assembly_factory_service
        +tag_management_service
        +system_settings_service
        +dashboard_service
    }

    class ProductApplicationService {
        +create_product(command)
        +update_product(command)
        +delete_product(product_id)
        +list_products()
    }

    class AssetIntakeService {
        +register_asset(command)
        +list_assets(...)
    }

    class ArtifactGenerationService {
        +enqueue_thumbnail_job(asset_id)
        +enqueue_proxy_job(asset_id)
        +run_job(job_id)
        +retry_job(job_id)
        +list_jobs(...)
    }

    class VideoAssemblyFactoryService {
        +create_recipe(command)
        +list_recipes(...)
        +get_recipe(recipe_id)
        +assign_asset_to_recipe(command)
        +enqueue_preview_job(recipe_id)
        +run_preview_job(job_id)
        +list_preview_jobs(...)
    }

    class FFmpegPreviewRenderer {
        +render_preview(...)
    }

    class DashboardService {
        +build_summary()
    }

    class SystemSettingsService {
        +load()
        +save(settings)
        +update(...)
    }

    class AssetLibraryViewModel {
        +load()
        +register_asset(...)
        +generate_thumbnail(asset_id)
        +generate_proxy(asset_id)
    }

    class RecipeBuilderViewModel {
        +load()
        +create_recipe(...)
        +assign_asset_to_recipe(...)
        +queue_preview(recipe_id)
        +select_recipe(recipe_id)
    }

    class DashboardWindow {
        +open_products()
        +open_assets()
        +open_recipes()
        +open_tags()
        +open_settings()
    }

    class RecipeBuilderWindow {
        +create_recipe()
        +attach_asset()
        +build_preview()
    }

    class SqlAlchemyUnitOfWork {
        +products
        +assets
        +tags
        +jobs
        +recipes
        +commit()
        +rollback()
    }

    class SqlAlchemyRecipeRepository {
        +add(recipe)
        +get_by_id(recipe_id)
        +get_by_code(recipe_code)
        +list_summaries(...)
        +add_item(recipe_id, asset_id, role)
        +list_items(recipe_id)
    }

    class SqlAlchemyOutputRepository {
        +add(output)
    }

    class PreviewManifestBuilder {
        +write_manifest(...)
    }

    class Recipe {
        +id
        +product_id
        +recipe_code
        +status
    }

    class Job {
        +id
        +job_code
        +job_type
        +status
        +recipe_id
        +asset_id
    }

    ResourceLibraryModule --> ProductApplicationService
    ResourceLibraryModule --> AssetIntakeService
    ResourceLibraryModule --> ArtifactGenerationService
    ResourceLibraryModule --> VideoAssemblyFactoryService
    ResourceLibraryModule --> DashboardService
    ResourceLibraryModule --> SystemSettingsService
    AssetLibraryViewModel --> AssetIntakeService
    AssetLibraryViewModel --> ArtifactGenerationService
    RecipeBuilderViewModel --> ProductApplicationService
    RecipeBuilderViewModel --> AssetIntakeService
    RecipeBuilderViewModel --> VideoAssemblyFactoryService
    DashboardWindow --> RecipeBuilderWindow
    VideoAssemblyFactoryService --> PreviewManifestBuilder
    VideoAssemblyFactoryService --> FFmpegPreviewRenderer
    ProductApplicationService --> SqlAlchemyUnitOfWork
    AssetIntakeService --> SqlAlchemyUnitOfWork
    ArtifactGenerationService --> SqlAlchemyUnitOfWork
    VideoAssemblyFactoryService --> SqlAlchemyUnitOfWork
    SqlAlchemyUnitOfWork --> SqlAlchemyRecipeRepository
    SqlAlchemyUnitOfWork --> SqlAlchemyOutputRepository
    SqlAlchemyRecipeRepository --> Recipe
    SqlAlchemyUnitOfWork --> Job
```

## Asset Artifact Sequence

```mermaid
sequenceDiagram
    actor User
    participant View as AssetLibraryWindow
    participant VM as AssetLibraryViewModel
    participant Artifact as ArtifactGenerationService
    participant JobRepo as JobRepository
    participant FF as FFmpegArtifactGenerator
    participant DB as SQLite

    User->>View: Generate Thumbnail / Proxy
    View->>VM: generate_thumbnail(asset_id)
    VM->>Artifact: enqueue job
    Artifact->>JobRepo: add(job)
    Artifact->>DB: COMMIT
    VM->>Artifact: run_job(job_id)
    Artifact->>FF: generate artifact
    Artifact->>JobRepo: update(done/failed)
    Artifact->>DB: COMMIT
    VM-->>View: refresh assets and feedback
```

## Recipe Preview Sequence

```mermaid
sequenceDiagram
    actor User
    participant View as RecipeBuilderWindow
    participant VM as RecipeBuilderViewModel
    participant Factory as VideoAssemblyFactoryService
    participant RecipeRepo as RecipeRepository
    participant JobRepo as JobRepository
    participant Preview as PreviewManifestBuilder
    participant Render as FFmpegPreviewRenderer
    participant Out as OutputRepository
    participant DB as SQLite

    User->>View: Build Preview
    View->>VM: queue_preview(recipe_id)
    VM->>Factory: enqueue_preview_job(recipe_id)
    Factory->>JobRepo: add(job)
    Factory->>DB: COMMIT
    VM->>Factory: run_preview_job(job_id)
    Factory->>RecipeRepo: list_items(recipe_id)
    Factory->>Preview: write_manifest(...)
    Factory->>Render: render_preview(...)
    Factory->>Out: add(output)
    Factory->>JobRepo: update(done/failed)
    Factory->>DB: COMMIT
    VM-->>View: refresh recipes and feedback
```

## Workflow State Direction

```mermaid
stateDiagram-v2
    [*] --> PRODUCT_READY
    PRODUCT_READY --> ASSET_READY
    ASSET_READY --> RECIPE_CANDIDATE
    RECIPE_CANDIDATE --> PREVIEW_JOB_QUEUED
    PREVIEW_JOB_QUEUED --> PREVIEW_JOB_PROCESSING
    PREVIEW_JOB_PROCESSING --> PREVIEW_OUTPUT_READY
    PREVIEW_OUTPUT_READY --> HUMAN_REVIEW
    HUMAN_REVIEW --> APPROVED
    HUMAN_REVIEW --> REJECTED
    APPROVED --> FINAL_RENDER_PENDING
```
