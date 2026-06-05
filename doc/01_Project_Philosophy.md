# Project Philosophy

## Purpose

MTClipFactory ถูกสร้างขึ้นเพื่อเป็นโรงงานผลิตคลิปโฆษณาสินค้าแบบควบคุมได้ ไม่ใช่ random video generator

## Core Philosophy

1. Build a controlled creative production factory.
2. Single source of truth before local opinions.
3. Workflow before code.
4. Preview before final render.
5. Cache before recompute.
6. Tag before random selection.
7. Quality before quantity.
8. Human review before publishing.
9. Database stores meaning, folder stores files.
10. Recoverability is a feature, not a bonus.
11. Tests are part of the design, not a cleanup step.
12. Project visibility is part of engineering discipline.

## Non-Negotiable Rules

- `doc/00_Document_Index.md` คือ SSOT ของเอกสารทั้งหมด
- ทุก feature ต้องมีเอกสารรองรับก่อนเริ่ม implement
- ทุก architecture สำคัญต้องมี UML ประกอบเสมอ
- ใช้ Mermaid ได้เมื่อช่วยให้ UML อ่านง่ายและแก้ไขใน `.md` ได้สะดวก
- ทุกการเปลี่ยน schema ต้องผ่าน Alembic migration
- Business logic ห้ามฝังอยู่ใน `QWidget`, `QDialog`, หรือ callback ที่เทสต์ยาก
- ViewModel ต้องบางและเน้น orchestration, ไม่แบก logic เชิง domain หนัก
- Infrastructure เช่น FFmpeg, filesystem, DB ต้องถูก inject ผ่าน interface หรือ seam ที่ mock ได้
- Final render ต้องเกิดหลัง preview และ approval เท่านั้น ยกเว้นงานทดสอบเฉพาะทาง
- ทุก issue สำคัญต้องลงบันทึกใน issue log
- ทุก milestone ต้องสรุป lesson learned
- สถานะโครงการต้องถูกสื่อสารในเอกสาร PM และ Kanban อย่างต่อเนื่อง
- ทีมต้องไม่สร้างระบบเพื่อหลบการตรวจจับแพลตฟอร์ม หรือผลิต spam ปริมาณมากแบบคุณภาพต่ำ

## Working Mindset

- เอกสารคือสัญญาระหว่างทีม
- โค้ดคือ implementation ของเอกสาร
- เทสต์คือหลักฐานว่า implementation ยังรักษาสัญญานั้นอยู่
- ความคืบหน้าของโครงการต้องมองเห็นได้จากเอกสารส่วนกลางเสมอ
