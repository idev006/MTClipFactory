# Project Status Report

## Reporting Purpose

ไฟล์นี้ทำหน้าที่เป็น project manager snapshot กลาง เพื่อให้ทุกคนในทีมเห็นความคืบหน้า สถานะปัจจุบัน owner และ next steps

## Current Status

- Project phase: Foundation
- Overall status: In Progress
- Report date: 2026-06-05
- Current focus: control-center milestone with dashboard, settings authority, and reliability foundations

## Completed

- อ่านและตีความ blueprint หลักของโครงการ
- สร้างเอกสารนำโครงการใน `doc`
- วางสถาปัตยกรรม `Python 3.12 + SQLite + SQLAlchemy + Alembic + PySide6 + pytest + MVVM`
- สร้าง project skeleton แบบ `src/`
- สร้าง Alembic baseline migration
- สร้าง baseline tests และรันผ่านใน `.venv`
- ยกระดับ governance ให้รองรับ SSOT, UML, Kanban, issue log, lessons learned, และ PM reporting
- กำหนดทิศทางโครงการให้แบ่งเป็น `Resource Library Management` และ `Video Assembly Factory`
- เพิ่ม module packages สำหรับ `library` และ `factory`
- ส่งมอบ `Product CRUD foundation` สำหรับ `Resource Library Management`
- สร้าง `ProductLibraryViewModel` และ `ProductLibraryWindow` สำหรับ desktop flow แรก
- ติดตั้ง package แบบ editable และเพิ่ม entry point `mt-resource-library`
- ยืนยันด้วย `pytest` 16 tests ผ่าน และ UI smoke test แบบ offscreen ผ่าน
- ส่งมอบ `asset intake flow` เบื้องต้นพร้อม `metadata analyzer seam`
- สร้าง `AssetLibraryViewModel` และ `AssetLibraryWindow`
- เพิ่ม `LocalAssetStorage` และ `BasicFileMetadataAnalyzer` สำหรับ MVP
- ยืนยันด้วย `pytest` 23 tests ผ่าน และ UI smoke test ของทั้งสองหน้าต่างผ่าน
- เชื่อม `F:\ffmpeg` ผ่าน `app_config.toml`
- เพิ่ม `FFprobeMetadataAnalyzer` พร้อม fallback analyzer
- ส่งมอบ `TagManagementService`, `TagDictionaryViewModel`, และ `TagDictionaryWindow`
- เพิ่ม `asset readiness rules` ให้ asset ถูกจัด status อัตโนมัติตอน ingest
- ยืนยันด้วย `pytest` 32 tests ผ่าน และ UI smoke test ของสามหน้าต่างผ่าน
- เพิ่ม asset library filters และ tag visibility ใน asset list
- ยืนยันรอบล่าสุดด้วย `pytest` 33 tests ผ่าน
- ส่งมอบ `DashboardWindow`, `DashboardViewModel`, และ `DashboardService`
- ส่งมอบ `SettingsWindow`, `SettingsViewModel`, และ `SystemSettingsService`
- ยกระดับ `app_config.toml` ให้เป็น operational config surface ผ่าน UI
- ยืนยันรอบล่าสุดด้วย `pytest` 37 tests ผ่าน และ UI smoke test ของ dashboard/settings ผ่าน

## In Progress

- Define `Library` to `Factory` contracts
- Thumbnail/proxy generation planning on top of FFmpeg
- Recovery and durability implementation planning beyond config/dashboard visibility

## Next Steps

1. Add thumbnail/proxy generation contracts on top of FFmpeg
2. Add richer asset preview artifacts in the library workflow
3. Prepare `Video Assembly Factory` recipe and job contracts

## Owners

- Resource Library Management foundation: Engineering
- Documentation governance and status visibility: Project Management

## Reporting Rule

- อัปเดตไฟล์นี้ทุกครั้งที่ milestone เปลี่ยนหรือมี blocker สำคัญ
- ถ้างานย้ายคอลัมน์ใน Kanban ต้องสะท้อนในรายงานนี้ด้วยเมื่อมีผลต่อภาพรวม
