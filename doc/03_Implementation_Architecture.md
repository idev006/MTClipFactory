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

เก็บ widget, window, dialog หรือ QML adapter ถ้ามี

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

## Deployment Guidance

- ช่วงแรกให้ใช้ codebase เดียวและฐานข้อมูลเดียว
- การแยกนี้เป็น `module split` ก่อน ไม่ใช่ `repository split`
- อนุญาตให้มีหลาย entry point ได้ในอนาคต
- ยังไม่บังคับให้เป็น 2 executable apps ตั้งแต่ MVP

## Shared Core

ทั้ง `Library` และ `Factory` ต้องใช้สิ่งเหล่านี้ร่วมกัน:

- shared domain model
- shared SQLite schema
- shared tag dictionary
- shared identity and naming rules
- shared audit and traceability rules

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

## Planned Evolution

สถาปัตยกรรมนี้เปิดทางให้:

- เปลี่ยน SQLite เป็น PostgreSQL
- เปลี่ยน local worker เป็น distributed worker
- เพิ่ม Docker build/runtime ภายหลัง
- แยก desktop shell ออกจาก backend service ถ้าจำเป็น
