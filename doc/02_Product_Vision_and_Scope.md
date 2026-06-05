# Product Vision and Scope

## Vision

ระบบนี้ช่วยให้ผู้ใช้สร้างคลิปโฆษณาหลายรูปแบบจากคลังวัตถุดิบของสินค้าแต่ละตัว โดยคุมคุณภาพ ความสอดคล้อง และการตรวจสอบย้อนหลังได้

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

- Product CRUD
- Asset registration metadata path
- Tag dictionary and asset tagging
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

