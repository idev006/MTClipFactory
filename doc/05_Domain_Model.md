# Domain Model

## Primary Concepts

### Product

หน่วยตรรกะหลักของสินค้า 1 ตัว มี product code, ชื่อ, brand, category และ default platform

### Asset

วัตถุดิบสื่อที่ผูกกับ product เช่น foreground, background, voiceover, music, template

### Tag

คำอธิบายแบบมี dictionary ควบคุม ไม่เปิดให้ free text แบบไร้มาตรฐาน

### Recipe

สูตรการประกอบคลิป 1 ชิ้น ประกอบด้วย asset หลาย role และ metadata ที่ใช้ scoring/review

### Job

หน่วยงานที่ orchestrator และ worker ประมวลผล เช่น analyze asset, create proxy, render preview

### Output

ไฟล์ผลลัพธ์ preview/final ที่ trace กลับไปหา recipe และ product ได้

## Context Split

### Library Context

ใช้แนวคิดหลักดังนี้:

- `Product`
- `Asset`
- `Tag`
- `AssetReadiness`

### Factory Context

ใช้แนวคิดหลักดังนี้:

- `Recipe`
- `Job`
- `Output`
- `ApprovalDecision`

### Shared Concepts

- Product identity
- Tag dictionary
- File naming convention
- Traceability rules

## Aggregate Direction

- Product เป็น aggregate root เชิง business identity
- Recipe และ Asset อ้างอิง Product เสมอ
- Job และ Output ต้อง trace ถึง Recipe หรือ Asset ที่เกี่ยวข้องได้

## Invariants

- `product_code` ต้อง unique
- recipe ต้องผูกกับ product
- output ต้อง trace ไปยัง recipe ได้
- final render ต้องเกิดจาก approved recipe
- asset ต้องมีสถานะพร้อมใช้งานก่อนถูกนำเข้าสู่ workflow ของ factory
