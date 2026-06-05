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
        +list_outputs(...)
        +list_jobs(...)
        +approve_output(output_id)
        +approve_recipe(recipe_id)
        +reject_recipe(recipe_id)
        +assign_asset_to_recipe(command)
        +enqueue_preview_job(recipe_id)
        +run_preview_job(job_id)
        +list_preview_jobs(...)
        +enqueue_final_render_job(recipe_id)
        +run_final_render_job(job_id)
        +list_final_render_jobs(...)
        +retry_job(job_id)
    }

    class FFmpegPreviewRenderer {
        +render_preview(...)
    }

    class DashboardService {
        +build_summary()
        +recover_queued_jobs(...)
        +should_auto_recover_queued_jobs()
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

## Review And Final Sequence

```mermaid
sequenceDiagram
    actor User
    participant View as RecipeBuilderWindow
    participant VM as RecipeBuilderViewModel
    participant Factory as VideoAssemblyFactoryService
    participant Out as OutputRepository
    participant JobRepo as JobRepository
    participant Render as FFmpegPreviewRenderer
    participant DB as SQLite

    User->>View: approve preview output
    View->>VM: approve_output(output_id)
    VM->>Factory: approve_output(output_id)
    Factory->>Out: update(approved=True)
    Factory->>DB: COMMIT
    User->>View: approve recipe
    View->>VM: approve_recipe(recipe_id)
    VM->>Factory: approve_recipe(recipe_id)
    Factory->>DB: COMMIT
    User->>View: build final
    View->>VM: queue_final_render(recipe_id)
    VM->>Factory: enqueue_final_render_job(recipe_id)
    Factory->>JobRepo: add(job)
    Factory->>DB: COMMIT
    VM->>Factory: run_final_render_job(job_id)
    Factory->>Render: render_output(...)
    Factory->>Out: add(final output)
    Factory->>JobRepo: update(done/failed)
    Factory->>DB: COMMIT
```

## Retry Recovery Sequence

```mermaid
sequenceDiagram
    actor User
    participant Dash as DashboardWindow
    participant Factory as VideoAssemblyFactoryService
    participant JobRepo as JobRepository
    participant Render as FFmpegPreviewRenderer
    participant DB as SQLite

    User->>Dash: inspect failed job on dashboard
    User->>Factory: retry_job(job_id)
    Factory->>JobRepo: load failed job
    Factory->>JobRepo: reset status=queued
    Factory->>DB: COMMIT
    Factory->>Render: run preview/final job again
    Factory->>JobRepo: update(done/failed)
    Factory->>DB: COMMIT
```

## Queued Recovery Sequence

```mermaid
sequenceDiagram
    participant Boot as Bootstrap
    participant Dash as DashboardService
    participant Artifact as ArtifactGenerationService
    participant Factory as VideoAssemblyFactoryService
    participant DB as SQLite

    Boot->>Dash: should_auto_recover_queued_jobs()
    alt startup policy enabled
        Boot->>Dash: recover_queued_jobs(trigger="startup")
        Dash->>Artifact: run_job(queued artifact)
        Dash->>Factory: run_preview_job(queued preview)
        Dash->>Factory: run_final_render_job(queued final)
        Dash->>DB: persisted state refreshed per job
    else startup policy disabled
        Boot-->>DB: no recovery side effect
    end
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
    PREVIEW_OUTPUT_READY --> OUTPUT_APPROVED
    PREVIEW_OUTPUT_READY --> HUMAN_REVIEW
    OUTPUT_APPROVED --> RECIPE_APPROVED
    HUMAN_REVIEW --> APPROVED
    HUMAN_REVIEW --> REJECTED
    RECIPE_APPROVED --> FINAL_RENDER_PENDING
    FINAL_RENDER_PENDING --> FINAL_RENDER_DONE
```
