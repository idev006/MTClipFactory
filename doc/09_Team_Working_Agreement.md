# Team Working Agreement

## Shared Rules

- ใช้ Python จาก `F:\programming\python\MTClipFactory\.venv` เท่านั้น
- ก่อนติดตั้ง package หรือรันคำสั่ง Python ให้ activate `.venv` เสมอ
- เอกสารทางการทั้งหมดต้องอยู่ใน `doc` และเป็น `.md`
- ถ้าจำเป็นต้องสร้าง config file ใหม่ ให้ใช้ `.toml`
- `doc/00_Document_Index.md` คือ SSOT ของชุดเอกสาร
- architecture หรือ workflow สำคัญต้องมี UML และใช้ Mermaid ได้
- งานทุกชิ้นต้องอัปเดตเอกสารใน `doc` ถ้ามีพฤติกรรมหรือโครงสร้างเปลี่ยน
- ห้าม merge code ที่ไม่มี test coverage ตามระดับที่เหมาะสม
- ห้ามใส่ business logic ลงใน UI โดยตรง
- ห้ามแก้ฐานข้อมูลแบบ manual ข้าม Alembic
- ต้องอัปเดต `Kanban`, `Project Status`, `Issues Log`, และ `Lessons Learned` ตามความเหมาะสมของงาน

## Delivery Checklist

1. เอกสารอัปเดตแล้ว
2. UML และ diagram ที่เกี่ยวข้องอัปเดตแล้ว
3. โค้ดสอดคล้องกับ architecture
4. มี test ที่เกี่ยวข้อง
5. รัน test ผ่านใน `.venv`
6. Kanban และ project status สะท้อนสถานะล่าสุด
7. issue และ lesson learned ถูกบันทึกเมื่อมีสาระสำคัญ
8. มีเส้นทางขยายต่อโดยไม่ทำลาย design

9. architecture/process review checkpoint completed if the milestone changes workflow, persistence, or delivery policy

## Decision Rule

ถ้าโค้ดกับเอกสารขัดกัน ให้ถือว่า implementation ยังไม่สมบูรณ์ จนกว่าจะปรับให้ตรงกันหรือแก้เอกสารอย่างเป็นทางการ

## Project Manager Cadence

- every milestone must include a revision checkpoint for architecture, process, and SSOT docs before commit/push

- ทุกช่วงงานต้องมี owner และ next step ชัดเจนในเอกสารความคืบหน้า
- ถ้ามี blocker ต้องสะท้อนใน issue log และ Kanban ภายในงานเดียวกัน
- เมื่อจบ milestone ให้บันทึกบทเรียนลง lessons learned
