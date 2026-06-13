# MTClipFactory Document Index

This folder is the project document SSOT.

When code changes, the related Markdown documents in this folder must be updated in the same delivery loop.

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
17. [17_Project_Progress_Snapshot.md](/F:/programming/python/MTClipFactory/doc/17_Project_Progress_Snapshot.md)
18. [18_Composition_and_Timeline_Policy.md](/F:/programming/python/MTClipFactory/doc/18_Composition_and_Timeline_Policy.md)
19. [19_Implementation_Roadmap.md](/F:/programming/python/MTClipFactory/doc/19_Implementation_Roadmap.md)
20. [20_Master_Test_Plan.md](/F:/programming/python/MTClipFactory/doc/20_Master_Test_Plan.md)
21. [21_Test_Execution_Report_2026-06-08.md](/F:/programming/python/MTClipFactory/doc/21_Test_Execution_Report_2026-06-08.md)
22. [22_UAT_Checklist_2026-06-08.md](/F:/programming/python/MTClipFactory/doc/22_UAT_Checklist_2026-06-08.md)
23. [23_Settings_UI_Audit_Test_Plan_2026-06-11.md](/F:/programming/python/MTClipFactory/doc/23_Settings_UI_Audit_Test_Plan_2026-06-11.md)
24. [24_Settings_UI_Audit_Execution_Report_2026-06-11.md](/F:/programming/python/MTClipFactory/doc/24_Settings_UI_Audit_Execution_Report_2026-06-11.md)
25. [25_Full_System_Release_Audit_Plan_2026-06-11.md](/F:/programming/python/MTClipFactory/doc/25_Full_System_Release_Audit_Plan_2026-06-11.md)
26. [26_Full_System_Release_Audit_Report_2026-06-11.md](/F:/programming/python/MTClipFactory/doc/26_Full_System_Release_Audit_Report_2026-06-11.md)
27. [27_User_Manual_2026-06-12.md](/F:/programming/python/MTClipFactory/doc/27_User_Manual_2026-06-12.md)
28. [28_Controlled_Operator_Rollout_Kickoff_2026-06-12.md](/F:/programming/python/MTClipFactory/doc/28_Controlled_Operator_Rollout_Kickoff_2026-06-12.md)
29. [29_Controlled_Operator_UAT_Execution_Report_2026-06-13.md](/F:/programming/python/MTClipFactory/doc/29_Controlled_Operator_UAT_Execution_Report_2026-06-13.md)
30. [30_Controlled_Operator_UAT_Round2_Report_2026-06-13.md](/F:/programming/python/MTClipFactory/doc/30_Controlled_Operator_UAT_Round2_Report_2026-06-13.md)
31. [31_Asset_Lifecycle_and_Media_Purge_Workflow.md](/F:/programming/python/MTClipFactory/doc/31_Asset_Lifecycle_and_Media_Purge_Workflow.md)
32. [32_Auto_Factory_Batch_Production_Workflow.md](/F:/programming/python/MTClipFactory/doc/32_Auto_Factory_Batch_Production_Workflow.md)

## Governance

- Document-first: update documents before or together with implementation changes.
- SSOT-first: only files linked from this index are official project documents.
- UML-first: architecture and workflow changes must be reflected in the UML document, and non-trivial implementation work should start from an analyzed sequence diagram before code is changed.
- Testability-first: service seams, adapters, and view models must stay easy to verify with `pytest`.
- Traceability-first: roadmap, status, issues, Kanban, and lessons learned must describe the real project state.
- PM-visibility-first: progress must be visible from both the dashboard and the central project documents.
