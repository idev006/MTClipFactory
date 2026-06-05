# MTClipFactory Document Index

เอกสารทั้งหมดในโฟลเดอร์นี้คือแหล่งอ้างอิงหลักของโครงการ ทีมพัฒนาต้องยึดตามเอกสารก่อนเสมอ และเมื่อโค้ดเปลี่ยน เอกสารต้องถูกปรับในงานเดียวกัน
ไฟล์นี้คือ `SSOT` ของชุดเอกสาร หากมีเอกสารใหม่ ต้องถูกเพิ่มเข้ามาที่นี่ก่อนจึงถือว่าเป็นเอกสารทางการของโครงการ

## Reading Order

1. [01_Project_Philosophy.md](/F:/programming/python/MTClipFactory/doc/01_Project_Philosophy.md)
2. [02_Product_Vision_and_Scope.md](/F:/programming/python/MTClipFactory/doc/02_Product_Vision_and_Scope.md)
3. [03_Implementation_Architecture.md](/F:/programming/python/MTClipFactory/doc/03_Implementation_Architecture.md)
4. [04_Engineering_Standards.md](/F:/programming/python/MTClipFactory/doc/04_Engineering_Standards.md)
5. [05_Domain_Model.md](/F:/programming/python/MTClipFactory/doc/05_Domain_Model.md)
6. [06_Database_Design_SQLAlchemy_Alembic.md](/F:/programming/python/MTClipFactory/doc/06_Database_Design_SQLAlchemy_Alembic.md)
7. [07_Testing_Strategy.md](/F:/programming/python/MTClipFactory/doc/07_Testing_Strategy.md)
8. [08_MVP_Roadmap.md](/F:/programming/python/MTClipFactory/doc/08_MVP_Roadmap.md)
9. [09_Team_Working_Agreement.md](/F:/programming/python/MTClipFactory/doc/09_Team_Working_Agreement.md)
10. [10_UML_System_Overview.md](/F:/programming/python/MTClipFactory/doc/10_UML_System_Overview.md)
11. [11_Project_Status_Report.md](/F:/programming/python/MTClipFactory/doc/11_Project_Status_Report.md)
12. [12_Kanban_Board.md](/F:/programming/python/MTClipFactory/doc/12_Kanban_Board.md)
13. [13_Issues_Log.md](/F:/programming/python/MTClipFactory/doc/13_Issues_Log.md)
14. [14_Lessons_Learned.md](/F:/programming/python/MTClipFactory/doc/14_Lessons_Learned.md)
15. [15_System_Decomposition_Library_and_Factory.md](/F:/programming/python/MTClipFactory/doc/15_System_Decomposition_Library_and_Factory.md)
16. [16_Operational_Reliability_and_Control_Center.md](/F:/programming/python/MTClipFactory/doc/16_Operational_Reliability_and_Control_Center.md)

## Governance

- Document-first: เริ่มจากเอกสารก่อนเขียนโค้ด
- SSOT-first: ใช้ `doc/00_Document_Index.md` เป็นประตูทางเข้าชุดเอกสารทั้งหมด
- Architecture-first: ทุกโมดูลใหม่ต้องระบุว่าตรงกับชั้นใดในสถาปัตยกรรม
- Testability-first: โค้ดใหม่ต้องออกแบบให้เทสต์ได้ง่าย ไม่ซ่อน logic ไว้ใน UI
- Traceability-first: การตัดสินใจสำคัญต้องสะท้อนในเอกสาร
- PM-visibility-first: ความคืบหน้า, งานค้าง, issue, และ lesson learned ต้องอัปเดตในเอกสารส่วนกลาง
