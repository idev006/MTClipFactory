# Product Vision and Scope

## Vision

ระบบนี้ช่วยให้ผู้ใช้สร้างคลิปโฆษณาหลายรูปแบบจากคลังวัตถุดิบของสินค้าแต่ละตัว โดยคุมคุณภาพ ความสอดคล้อง และการตรวจสอบย้อนหลังได้

## Product Decomposition

ระบบถูกแบ่งเป็น 2 ส่วนหลัก:

### 1. Resource Library Management

หน้าที่ของส่วนนี้คือเตรียม ดูแล และควบคุมคุณภาพของวัตถุดิบก่อนเข้าสู่การประกอบวิดีโอ

ขอบเขตหลัก:

- product CRUD
- asset intake และการจัดเก็บไฟล์
- rename และจัด folder ตามมาตรฐาน
- metadata analysis
- thumbnail / proxy generation
- tag dictionary และ tag editor
- asset search / filter / grouping
- preflight quality checks ของ asset

### 2. Video Assembly Factory

หน้าที่ของส่วนนี้คือเลือกวัตถุดิบที่พร้อมใช้งานแล้วมาประกอบเป็น preview และ final output ตาม workflow ที่ควบคุมได้

ขอบเขตหลัก:

- manual recipe builder
- candidate generation
- scoring และ rule-based filtering
- preview queue
- approval workflow
- final render queue
- job monitor
- output report และ traceability

## Boundary Rule

- `Library` เป็นแหล่งข้อมูลและวัตถุดิบที่ผ่านการเตรียม
- `Factory` เป็นผู้บริโภควัตถุดิบและ orchestrator ของการประกอบ
- `Factory` ห้ามแก้ metadata หลักของ asset โดยตรงนอก contract ที่กำหนดไว้
- ข้อมูลร่วมต้องอาศัย SSOT เดียวกัน ไม่สร้าง dictionary ซ้ำสองฝั่ง

## Core Capabilities

- Product-centric media organization
- Tag-driven asset discovery
- Recipe generation and scoring
- Preview-first review workflow
- Green/blue screen compositing
- Audio mix and loudness control
- Template-driven overlays
- Quality gate before final output
- Job orchestration with resumable state

## MVP Boundary

MVP ต้องรองรับสิ่งต่อไปนี้ก่อน:

### MVP-A: Resource Library Management

- Product CRUD
- Asset registration metadata path
- Tag dictionary and asset tagging
- Asset library query foundation

### MVP-B: Video Assembly Factory

- Manual recipe creation
- Preview render pipeline
- Final render after approval
- Job persistence in SQLite

## Explicitly Deferred

- Cloud storage
- Remote workers
- Redis/Celery
- PostgreSQL
- Full React/FastAPI stack
- Dockerized deployment pipeline

Deferred ไม่ได้แปลว่าไม่ออกแบบเผื่อ แต่แปลว่ายังไม่ implement ในช่วงแรก
