# Implementation Architecture

## Target Stack

- Python 3.12 only
- SQLite for local source of truth
- SQLAlchemy 2.x as ORM
- Alembic for schema migration
- PySide6 for desktop UI
- pytest for automated tests
- MVVM for presentation structure

## Architectural Layers

### Domain

เก็บ entity, enum, business invariant, domain policy และ protocol ที่ไม่ผูกกับ framework

### Application

เก็บ use case และ application service เช่น create product, queue preview render, approve recipe

### Infrastructure

เก็บ implementation ของ database, filesystem, FFmpeg adapter, repository, unit of work

### Presentation

เก็บ ViewModel ที่เชื่อม UI กับ application service โดยไม่แบก business rule หนัก

### UI

- packaged QSS theme assets should be loaded through a dedicated theme helper instead of embedding inline stylesheet strings inside window code

เก็บ widget, window, dialog หรือ QML adapter ถ้ามี

### Control Center

เก็บ dashboard, settings, และ system-level orchestration view ที่รวมข้อมูลจากหลายโมดูลมาแสดงใน operational surface เดียว

## System Modules

สถาปัตยกรรมเชิง business ถูกแบ่งเป็น 2 โมดูลหลักที่ใช้ domain และ infrastructure ร่วมกัน

### Resource Library Management Module

รับผิดชอบ:

- product setup
- asset lifecycle ก่อนเข้าสู่การผลิต
- metadata, tags, thumbnails, proxy, readiness

### Video Assembly Factory Module

รับผิดชอบ:

- recipe lifecycle
- orchestration ของ preview/final workflow
- quality gate, approval, output tracking

## Timeline-Driven Composition Rule

Future render architecture must evolve toward:

- `master timeline` resolution
- semantic segment planning
- layered audio/visual composition
- configurable loop, trim, and duck policy
- persisted render-decision reporting

Current implemented baseline now includes:

- persisted `composition_plans`
- persisted `timeline_segments`
- persisted `render_decisions`
- service-level composition plan retrieval with validation-backed segment planning
- segment-aware preview/final composition with manifest-guided visual clip selection
- runtime voice/music mix foundation with manifest-visible audio-mix evidence
- settings-driven duck gain and attack/release policy consumption in preview/final renderers
- configurable duck mode selection with `sidechain_compressor` as the higher-quality default and `windowed_volume_duck` as fallback
- settings-driven voice/music gain staging with manifest-visible balance evidence
- review-gate assessment with configurable duration and visual-repetition thresholds
- manifest-backed review evidence plus output quality/duplicate-risk summaries
- recipe-level score/risk persistence derived from metadata completeness, asset diversity, and runtime review evidence
- desktop app runtime path reload via whole-module rebuild plus reloadable service proxies

The architecture must keep `voice-over` as a foreground layer:

- narration does not auto-loop
- music may loop
- music ducks while narration is active

## Deployment Guidance

- ช่วงแรกให้ใช้ codebase เดียวและฐานข้อมูลเดียว
- การแยกนี้เป็น `module split` ก่อน ไม่ใช่ `repository split`
- อนุญาตให้มีหลาย entry point ได้ในอนาคต
- ยังไม่บังคับให้เป็น 2 executable apps ตั้งแต่ MVP

## Control Center Architecture Rule

- `Dashboard` ต้องเป็น entry surface หลักของระบบ
- `Dashboard` ต้อง aggregate จาก service layer ไม่ query DB ตรงใน UI
- `Settings` ต้องผ่าน service ที่ควบคุม source of truth อย่างชัดเจน
- runtime paths และ operational thresholds ต้องถูกอ่านจาก config/service กลางเดียว
- review thresholds and flagged-recipe counts must flow through the same dashboard/settings authority surfaces
- settings-window styling should flow through reusable theme assets so the same theme-loading seam can expand to other Qt windows later

## Shared Core

ทั้ง `Library` และ `Factory` ต้องใช้สิ่งเหล่านี้ร่วมกัน:

- shared domain model
- shared SQLite schema
- shared tag dictionary
- shared identity and naming rules
- shared audit and traceability rules
- shared decision-event ledger for immutable review history

## Runtime Tooling

- FFmpeg runtime ถูกอ้างอิงผ่าน `app_config.toml`
- ฝั่ง Library ใช้ `ffprobe` สำหรับ metadata analysis
- runtime tool path ต้องอ่านได้จาก config ไม่ hardcode กระจัดกระจายหลายจุด

## MVVM Rules

- View รับ input และ bind กับ ViewModel
- ViewModel เรียก use case ผ่าน service ที่ inject เข้ามา
- ViewModel ไม่ query database ตรง
- ViewModel ไม่เขียน SQL และไม่จัดการ transaction
- Domain และ Application ต้องรันเทสต์ได้โดยไม่ต้องเปิด UI

## Testability Seams

- Repository ถูก inject ผ่าน protocol
- Unit of work ถูก inject ผ่าน factory
- ViewModel ใช้ service abstraction แทนการสร้าง dependency เอง
- Infrastructure สามารถถูกแทนด้วย in-memory adapter ใน test

## Documentation and Modeling Rules

- เอกสารโครงการทั้งหมดต้องเก็บเป็น `.md`
- ไฟล์ config ใหม่ให้ใช้ `.toml`
- architecture, workflow, และ state transition สำคัญต้องมี UML
- สามารถใช้ Mermaid ใน Markdown เพื่อสื่อ UML ได้
- diagram ต้องอัปเดตพร้อมกับการเปลี่ยนแปลงเชิงสถาปัตยกรรม

## Revision Checkpoint Rule

- every milestone ends with a revision checkpoint across docs, architecture notes, Kanban, issues, and lessons learned
- if the checkpoint reveals workflow or boundary drift, the documents are corrected before claiming the milestone complete

## Planned Evolution

สถาปัตยกรรมนี้เปิดทางให้:

- เปลี่ยน SQLite เป็น PostgreSQL
- เปลี่ยน local worker เป็น distributed worker
- เพิ่ม Docker build/runtime ภายหลัง
- แยก desktop shell ออกจาก backend service ถ้าจำเป็น
