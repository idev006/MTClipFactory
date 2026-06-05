# Lessons Learned

ไฟล์นี้ใช้สรุปบทเรียนที่ควรส่งต่อให้ทีมหลัง milestone หรือเหตุการณ์สำคัญ

## Entries

### LL-001 | 2026-06-05 | Foundation Setup

- Blueprint ฝั่ง product/process มีความชัดเจนสูง แต่ implementation stack ต้องถูกล็อกใหม่ให้ชัดตั้งแต่ต้น
- การสร้าง `document-first` และ `testable skeleton` ก่อน feature จริงช่วยลดความเสี่ยงการแก้สถาปัตยกรรมภายหลัง
- การกำหนด `.venv`, `.md`, `.toml`, และ SSOT ตั้งแต่วันแรกช่วยลดความสับสนของทีมได้มาก

### LL-002 | 2026-06-05 | System Split Decision

- การแยกเป็น `Resource Library Management` และ `Video Assembly Factory` ช่วยให้ขอบเขตธุรกิจชัดขึ้นมากกว่าการแยกตามหน้าจอ
- ช่วง MVP ควรแยกเป็นโมดูลใน codebase เดียวก่อน ไม่ควรรีบแยกเป็นหลาย repo
- ถ้าไม่ล็อก ownership ของ `Asset`, `Tag`, และ `Recipe` ตั้งแต่ต้น จะเกิด rule duplication ง่าย

### LL-003 | 2026-06-05 | First Library Milestone

- การเริ่มจาก `Product CRUD foundation` ทำให้ทั้ง DB, service, ViewModel, UI, และ test seam ถูกเดินให้ครบเส้นครั้งแรก
- การติดตั้ง package แบบ editable ช่วยลด friction ของทีมเวลาทดลอง UI และ import package ในงานพัฒนา
- การทำ UI smoke test แบบ offscreen เป็นตัวช่วยที่ดีระหว่างยังไม่มี test harness ฝั่ง widget เต็มรูปแบบ

### LL-004 | 2026-06-05 | Asset Intake Foundation

- การแยก `AssetIntakeService`, `LocalAssetStorage`, และ `MetadataAnalyzer` ออกจากกันช่วยให้เปลี่ยน implementation จริงเป็น FFmpeg ภายหลังได้โดยไม่กระทบ use case
- MVP ของ asset intake ควรเดินแบบ synchronous ก่อน เพื่อพิสูจน์สัญญาระหว่าง storage, analyzer, และ repository
- การเพิ่มหน้าต่าง `AssetLibraryWindow` แบบแยกจาก product screen ช่วยควบคุมขนาดไฟล์และลดความเสี่ยง UI บวมเร็วเกินไป

### LL-005 | 2026-06-05 | FFmpeg and Tag Foundation

- การอ้าง FFmpeg path ผ่าน `app_config.toml` ช่วยให้ runtime tooling ชัดเจนและตรวจสอบได้
- `ffprobe` เหมาะมากสำหรับ metadata phase และควรถูกแยกจากงาน render/proxy ที่จะตามมา
- การทำ `Tag Dictionary` เป็นหน้าต่างแยกช่วยให้ขอบเขตของ library ชัดขึ้นและหลีกเลี่ยงการยัดทุกอย่างในหน้า asset intake

### LL-006 | 2026-06-05 | Query Visibility Matters

- เมื่อมี tag แล้ว ต้องรีบทำให้มองเห็นและกรองได้ ไม่อย่างนั้นคุณค่าของ dictionary จะยังไม่ส่งผลต่อ workflow จริง
- การให้ query layer คืน `tag labels` พร้อม filter ช่วยลด logic กระจัดกระจายใน UI และทำให้การทดสอบง่ายกว่า

### LL-007 | 2026-06-05 | Control Center First

- เมื่อระบบเริ่มมีหลายโมดูล ควรยก dashboard และ settings ขึ้นเป็นของจริงเร็ว ไม่อย่างนั้นความรู้เรื่องระบบจะกระจายตามหน้าจอและไฟล์ config
- การทำ settings ผ่าน service และ TOML กลางช่วยให้ admin/user คุมระบบได้โดยไม่ต้องไล่แก้หลายจุด


## Lesson Rule

- ทุก milestone ต้องมีอย่างน้อย 1 lesson learned ถ้ามีสาระสำคัญ
- lesson learned ต้อง actionable และใช้ปรับวิธีทำงานของทีมได้จริง
