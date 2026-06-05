# Testing Strategy

## Testing Goals

ระบบต้องออกแบบให้เทสต์ได้ง่ายตั้งแต่ต้น โดยไม่ต้องพึ่ง UI จริงหรือ filesystem จริงในทุกกรณี

## Test Pyramid

### Unit Tests

เทสต์ domain logic, use case, scoring rule, validator, mapper

### Integration Tests

เทสต์ repository, unit of work, migration, FFmpeg adapter contract

ตัวอย่างปัจจุบัน:

- `ffprobe` metadata integration test
- local asset storage copy behavior
- tag assignment persistence

### UI/ViewModel Tests

เทสต์ว่า ViewModel bind สถานะและเรียก use case ถูกต้อง โดยไม่ต้องเปิดหน้าจอเต็มรูปแบบ

## Module Testing Direction

### Resource Library Management

ควรมี test สำหรับ:

- product and asset use cases
- tag assignment rules
- asset readiness logic
- metadata ingestion contracts

### Video Assembly Factory

ควรมี test สำหรับ:

- recipe creation and validation
- candidate scoring
- job orchestration rules
- approval and final-render gating

## Current Test Conventions

- ใช้ `pytest`
- ใช้ in-memory SQLite สำหรับ repository/application tests
- ไม่ผูก test กับ production DB file
- test file ต้องอ่านแล้วเข้าใจ behavior ได้ทันที

## Design Rules for Easy Testing

- อย่าซ่อน logic ไว้ใน signal handler ที่ฉีด dependency ไม่ได้
- use case ต้องไม่รู้เรื่อง QWidget
- repository ต้องถูกสลับ implementation ได้
- time, filesystem, ffmpeg, random selection ควรถูก wrap เพื่อ mock ได้ภายหลัง
