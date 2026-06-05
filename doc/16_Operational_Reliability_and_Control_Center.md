# Operational Reliability and Control Center

เอกสารนี้นิยามข้อกำหนดด้าน dashboard, settings, reliability, recoverability, durability, performance, และ component-based design ของระบบ

## Control Center Requirements

### Dashboard

Dashboard คือหน้าหลักของระบบ และต้องเป็น operational truth surface สำหรับ admin/user

อย่างน้อย dashboard ต้องแสดง:

- product count
- asset count
- ready / needs_review asset count
- tag count
- runtime dependency readiness
- database path
- media root
- FFmpeg / FFprobe paths
- operational thresholds

### Settings

Settings คือหน้า system authority สำหรับ admin/user

อย่างน้อย settings ต้องควบคุมได้:

- FFmpeg root
- FFprobe path
- FFmpeg path
- CPU limit threshold
- RAM limit threshold
- disk free minimum
- preview/final worker limits
- auto refresh cadence

## Reliability Principles

ระบบต้อง:

- survive partial dependency failures เมื่อทำได้
- degrade gracefully เมื่อ dependency หลักไม่พร้อม
- ให้ข้อมูลสถานะชัดเจนผ่าน dashboard
- เก็บ source of truth อย่างเป็นระบบ
- เลี่ยง hidden state ที่ตรวจสอบไม่ได้

## Recoverability Principles

ระบบต้องมุ่งไปสู่ความสามารถเหล่านี้:

- resume งานจาก persisted state
- retry เฉพาะ component ที่ล้มเหลว
- ไม่ recompute ซ้ำโดยไม่จำเป็น
- trace ปัญหาย้อนกลับได้

## Durability Principles

- ไฟล์จริงเก็บใน media storage
- ความหมายของระบบเก็บใน database และ config ที่ชัดเจน
- runtime settings สำคัญต้อง persist
- การเปลี่ยนค่า config ต้องตรวจสอบย้อนหลังได้

## Performance Principles

- ใช้ FFprobe สำหรับ metadata phase
- ใช้ caching และ artifact reuse
- อย่าให้ UI query งานหนักเกินความจำเป็น
- aggregate data ผ่าน service ที่ควบคุมได้

## Component-Based Design Rule

ทุกความสามารถใหม่ควรถูกวางเป็น component ที่มี:

- responsibility ชัดเจน
- interface ชัดเจน
- test seam ชัดเจน
- persistence story ชัดเจน

## Current Foundation Delivered

- Dashboard window and view model
- Settings window and service
- FFmpeg/FFprobe config via `app_config.toml`
- Asset readiness status
- Tag dictionary and asset tagging

## Next Reliability Slice

สิ่งที่ยังควรทำต่อ:

1. thumbnail/proxy generation with persisted artifacts
2. job retry/recovery rules
3. degraded-mode policies when FFmpeg parts fail
4. richer system alerts surfaced on dashboard
