# Engineering Standards

## Source Layout

- `src/mt_clip_factory/domain`
- `src/mt_clip_factory/application`
- `src/mt_clip_factory/infrastructure`
- `src/mt_clip_factory/presentation`
- `src/mt_clip_factory/ui`
- `src/mt_clip_factory/library`
- `src/mt_clip_factory/factory`
- `tests`
- `doc`

## File Format Standards

- เอกสารโครงการใช้ `.md`
- ไฟล์ config ใหม่ใช้ `.toml`
- diagram ฝังใน `.md` โดยใช้ Mermaid ได้
- หลีกเลี่ยง config format หลายแบบโดยไม่จำเป็น

## Coding Rules

- ใช้ `src/` layout เสมอ
- ใช้ type hints ใน public API
- เขียน class/function ให้มี dependency ชัดเจนและ inject ได้
- หลีกเลี่ยง global mutable state
- แยก pure logic ออกจาก IO ให้มากที่สุด
- ใช้ dataclass หรือ domain model ที่เรียบง่ายในชั้น domain
- แยก use case ของ `Library` และ `Factory` คนละโมดูลให้ชัด
- ห้าม copy business rule เดียวกันไปคนละฝั่งโดยไม่มี shared abstraction

## Database Rules

- ห้ามแก้ schema โดยตรงใน production DB
- schema change ทุกครั้งต้องมี Alembic migration
- SQLite เป็น source of truth สำหรับสถานะ workflow

## UI Rules

- UI component ห้ามตัดสินใจเชิง domain เอง
- UI ต้องแสดงสถานะงานจาก view model
- Long-running work ต้องออกจาก main thread

## Logging and Errors

- ทุก use case ต้องคืน error ที่อธิบายได้
- ทุก background job ต้องมี status ที่ query ย้อนหลังได้
- ทุก failure path ต้องออกแบบให้ recover ได้

## Project Management Standards

- ต้อง maintain Kanban กลางของโครงการ
- ต้องมี status report ที่ทีมอ่านแล้วเข้าใจภาพรวมได้ทันที
- ต้องมี issue log สำหรับปัญหา ความเสี่ยง และ blocker
- ต้องมี lessons learned log สำหรับสรุปบทเรียนหลัง milestone หรือเหตุการณ์สำคัญ
