# Issues Log

ไฟล์นี้ใช้เก็บปัญหา ความเสี่ยง blocker และข้อสังเกตที่ต้องติดตาม

## Open Issues

| ID | Date | Severity | Topic | Description | Owner | Status | Next Action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ISS-001 | 2026-06-05 | Medium | UI Direction | Blueprint เดิมอ้างอิง Streamlit แต่ implementation target ใช้ PySide6 + MVVM ต้องคุมการแปลแนวคิดให้สอดคล้อง | Engineering | Open | ยึด architecture docs ใหม่เป็น implementation SSOT |
| ISS-002 | 2026-06-05 | Medium | Module Boundary | ต้องป้องกันไม่ให้ `Video Assembly Factory` ไปแก้ asset metadata หลักเองจนความรับผิดชอบซ้อนกับ `Resource Library Management` | Engineering | Open | นิยาม contract และ ownership ของข้อมูลร่วมในเอกสาร architecture และ domain |
| ISS-003 | 2026-06-05 | Low | Packaging Contract | การรัน package ตรงจาก source ต้องมี contract ชัดเจนว่าจะใช้ editable install หรือ entry point อะไร | Engineering | Open | ใช้ `python -m pip install -e .[dev]` และ `mt-resource-library` เป็นทางหลักระหว่างพัฒนา |
| ISS-004 | 2026-06-05 | Medium | Preview Artifacts | แม้ metadata ใช้ `ffprobe` จริงแล้ว แต่ thumbnail/proxy generation ยังไม่ถูกส่งมอบ | Engineering | Open | ออกแบบ FFmpeg-backed thumbnail/proxy contracts เป็น milestone ถัดไป |
| ISS-005 | 2026-06-05 | Medium | Recovery Depth | dashboard/settings ช่วย visibility แล้ว แต่ crash recovery, retry ledger, และ durable recovery flow ยังไม่ถูก implement เชิงลึก | Engineering | Open | วาง recovery slice ถัดไปบน jobs/state persistence และ degraded-operation rules |

## Closed Issues

| ID | Date Closed | Topic | Resolution |
| --- | --- | --- | --- |
| ISS-004-OLD | 2026-06-05 | Metadata Depth | ปิดด้วยการส่งมอบ `FFprobeMetadataAnalyzer` และ config ผ่าน `app_config.toml` |

## Issue Rule

- issue ที่กระทบ scope, architecture, quality, schedule หรือ team alignment ต้องลงไฟล์นี้
- เมื่อปิด issue ต้องสรุป resolution ให้ย้อนอ่านเข้าใจได้
