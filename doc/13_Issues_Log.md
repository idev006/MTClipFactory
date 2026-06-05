# Issues Log

ไฟล์นี้ใช้เก็บปัญหา ความเสี่ยง blocker และข้อสังเกตที่ต้องติดตาม

## Open Issues

| ID | Date | Severity | Topic | Description | Owner | Status | Next Action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ISS-001 | 2026-06-05 | Medium | UI Direction | Blueprint เดิมอ้างอิง Streamlit แต่ implementation target ใช้ PySide6 + MVVM ต้องคุมการแปลแนวคิดให้สอดคล้อง | Engineering | Open | ยึด architecture docs ใหม่เป็น implementation SSOT |
| ISS-002 | 2026-06-05 | Medium | Module Boundary | ต้องป้องกันไม่ให้ `Video Assembly Factory` ไปแก้ asset metadata หลักเองจนความรับผิดชอบซ้อนกับ `Resource Library Management` | Engineering | Open | นิยาม contract และ ownership ของข้อมูลร่วมในเอกสาร architecture และ domain |
| ISS-003 | 2026-06-05 | Low | Packaging Contract | การรัน package ตรงจาก source ต้องมี contract ชัดเจนว่าจะใช้ editable install หรือ entry point อะไร | Engineering | Open | ใช้ `python -m pip install -e .[dev]` และ `mt-resource-library` เป็นทางหลักระหว่างพัฒนา |
| ISS-004 | 2026-06-05 | Medium | Metadata Depth | `BasicFileMetadataAnalyzer` ใน MVP อ่านได้เพียง metadata ขั้นต้น ยังไม่ครอบคลุม duration/resolution จริงจาก FFmpeg | Engineering | Open | ออกแบบ FFmpeg-backed analyzer เป็น implementation ถัดไปหลัง tag/readiness milestone |

## Closed Issues

| ID | Date Closed | Topic | Resolution |
| --- | --- | --- | --- |
| None | - | - | - |

## Issue Rule

- issue ที่กระทบ scope, architecture, quality, schedule หรือ team alignment ต้องลงไฟล์นี้
- เมื่อปิด issue ต้องสรุป resolution ให้ย้อนอ่านเข้าใจได้
