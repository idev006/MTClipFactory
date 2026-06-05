# Database Design with SQLAlchemy and Alembic

## Principles

- ORM ใช้เพื่อให้ schema และ object model เดินไปด้วยกัน
- Alembic ใช้ควบคุม version ของ schema ทุกครั้ง
- SQLite ถูกใช้เป็น local system ledger ของ workflow

## Current Tables

- `products`
- `assets`
- `tags`
- `asset_tags`
- `recipes`
- `recipe_items`
- `jobs`
- `outputs`

## Implementation Notes

- SQLAlchemy models อยู่ที่ `src/mt_clip_factory/infrastructure/models.py`
- migration เริ่มต้นอยู่ที่ `alembic/versions/20260605_0001_initial_schema.py`
- approval audit fields เพิ่มผ่าน `alembic/versions/20260606_0002_approval_audit_fields.py`
- repository ตัวแรกคือ `SqlAlchemyProductRepository`
- transaction ถูกควบคุมผ่าน `SqlAlchemyUnitOfWork`
- runtime schema guard อยู่ที่ `src/mt_clip_factory/infrastructure/migrations.py`

## Current Audit Fields

- `recipes.decision_actor`
- `recipes.decision_at`
- `recipes.decision_reason`
- `outputs.approved_by`
- `outputs.approved_at`
- `outputs.approval_reason`

## Runtime Migration Policy

- database ใหม่จะถูกสร้างจาก model ล่าสุดแล้ว `stamp head`
- database เดิมที่ยังไม่มี `alembic_version` จะถูก `stamp` ที่ baseline revision ก่อน แล้ว `upgrade head`
- database ที่มี revision อยู่แล้วจะถูก `upgrade head` ตามปกติ
- ห้ามอ้างว่า schema feature เสร็จ หากยังไม่มี migration และ runtime path รองรับจริง

## Migration Discipline

1. อัปเดต model
2. สร้าง migration ใหม่
3. review migration
4. run migration ใน environment ทดสอบ
5. update เอกสารที่เกี่ยวข้อง
