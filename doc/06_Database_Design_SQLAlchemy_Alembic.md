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
- repository ตัวแรกคือ `SqlAlchemyProductRepository`
- transaction ถูกควบคุมผ่าน `SqlAlchemyUnitOfWork`

## Migration Discipline

1. อัปเดต model
2. สร้าง migration ใหม่
3. review migration
4. run migration ใน environment ทดสอบ
5. update เอกสารที่เกี่ยวข้อง

