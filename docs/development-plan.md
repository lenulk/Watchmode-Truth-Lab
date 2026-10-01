# แผนพัฒนาสู่การใช้งานจริง — 2026-10-01

สถานะ: ผู้ใช้อนุญาตให้พัฒนา ทดสอบ และอัปโหลด GitHub เมื่อสำเร็จ พัฒนา CLI/starter/diagnostics/report และ installed workflow แล้ว กำลังตรวจรับเวอร์ชัน 1.0.0 และ CI ก่อนส่งมอบ

## เป้าหมาย

ให้ผู้ใช้ติดตั้ง Watchmode Truth Lab เป็น CLI แล้วตรวจได้ว่าผลลัพธ์ของ watch process อัปเดตหลังแก้ซอร์สหรือไม่ ตั้งแต่เตรียม scenario ตรวจ dependency รันทดสอบ อ่านสาเหตุที่ไม่ผ่าน และนำไปเป็นขั้นตอนตรวจรับใน CI ทั้งหมดต้องทำได้จากแพ็กเกจและคู่มือที่ส่งมอบ โดยไม่ต้องพึ่ง checkout ของผู้พัฒนา

เป้าหมายคือเครื่องมือที่ใช้งานได้ครบตามหน้าที่: file/HTTP freshness และ browser HMR พร้อมติดตั้ง วินิจฉัย รายงาน และตรวจอัตโนมัติ ใช้ Windows, Debian, WSL2 และ browser engines ที่มีอยู่เป็นสถานที่เก็บหลักฐานตามแต่ละงาน การเลือกเครื่องทดสอบเป็นลำดับทำงาน ไม่ใช่การลดเกณฑ์จบงาน แอปที่ไม่ได้นำมาทดสอบต้องยังระบุว่า unverified

0.2.0 เป็น milestone ระหว่างพัฒนา เป้าหมายส่งมอบคือเครื่องมือที่ทำ workflow ครบและผ่านเกณฑ์ทุกระยะ รวมถึง installed package และงานจริงที่เลือกทดสอบ จากนั้นอัปโหลด GitHub ตามที่ผู้ใช้อนุญาต ไม่จบงานเพียงเพราะ suite เดิมผ่าน และไม่อ้างผลบน platform/application ที่ไม่ได้ตรวจ

## สถานะตั้งต้นก่อนงาน installed product (หลักฐานย้อนหลัง)

ก่อนเริ่มระยะนี้ หลักฐานยืนยัน Windows และ Debian 30/30 ไม่มี skip, Windows Vite 120 positive updates และ Windows installed-wheel smoke ผ่าน ช่องว่างที่พบจากการตรวจซอร์ส:

- CLI รับ scenario และส่ง JSON ได้ แต่ยังไม่มีขั้นตอนสร้าง starter หรือแยกตรวจ config/dependency ก่อนรัน
- wheel บรรจุ Python package; ตัวอย่าง Vite, browser adapter และ Node dependencies ยังอยู่ใน checkout ต้องกำหนดวิธีส่งมอบให้ผู้ใช้ที่ติดตั้งแพ็กเกจ
- Linux installed-wheel execution และ Python 3.10 ที่ประกาศรองรับยังไม่มีหลักฐานทดสอบจริง
- มี Git remote แล้ว แต่ checkout ที่ตรวจยังไม่มี workflow CI; การทำงานหรือสิทธิ์ CI บน remote ยังไม่ได้ตรวจ
- Browser fixture ปัจจุบันครอบคลุม dependency-accept HMR ยังไม่มีเกณฑ์ตรวจรับของแอปจริง
- มี `schema_version = 1` และ exit codes 0/1/2 แล้ว ต้องจัดทำสัญญาที่ตรงกับ implementation ก่อนเพิ่มรูปแบบผลลัพธ์หรือการเรียกใหม่

## ลำดับพัฒนาและเกณฑ์ตรวจรับ

| ระยะ | งานส่งมอบ | เกณฑ์ผ่าน |
| --- | --- | --- |
| 1. ติดตั้งแล้วเริ่มใช้ได้ | สัญญา CLI, config preflight, starter, dependency diagnostics, คู่มือเริ่มใช้ | ติดตั้ง artifact เดียวกันใน Windows/Debian venv ใหม่; สร้าง scenario นอก checkout; file และ Vite HTTP ผ่าน; อ่าน report ได้; ไม่ใช้ source fallback |
| 2. ผลลัพธ์และการหยุดงานเชื่อถือได้ | สัญญา report, ข้อความวินิจฉัย, การยกเลิกงาน, การเขียนรายงานอย่างปลอดภัย | Failure cases ด้านล่างผ่าน; ไม่มี false pass; reason/exit code ถูกต้อง; ยกเลิกแล้ว ordinary descendants ถูกเก็บ; export ล้มเหลวไม่ทำรายงานเดิมเสีย |
| 3. ใช้กับ workflow จริง | Scenario ของแอปที่เลือก, oracle ที่ตรงกับงาน, stale control, reproduction | ทุก watcher/mutation ที่ประกาศผ่านอย่างน้อย 20 rounds ต่อ combination; stale control ต้องไม่ผ่าน; reproduce จากสำเนาได้; ต้นฉบับไม่ถูก mutate |
| 4. ตรวจทุกการเปลี่ยนและเตรียม release | CI, support matrix, artifact retention, release gate | Windows/Linux required jobs ผ่านโดยไม่ซ่อน skip; wheel/sdist ของ release candidate ติดตั้งได้; เก็บ failed evidence; runtime/adapter ที่ประกาศมีหลักฐาน |
| 5. ทดลองใช้และส่งมอบ | คู่มือติดตั้ง/แก้ปัญหา, ตัวอย่างจริง, release candidate, rollback | ผู้ใช้ทำ workflow จาก environment สะอาดตามคู่มือได้; ไม่มี P0/P1 ค้าง; checklist 1.0.0 ผ่าน |

ระยะถัดไปเริ่มเมื่อเกณฑ์ที่เกี่ยวข้องผ่าน ให้แยกปัญหาที่พบใหม่และแก้ทีละประเด็น ความผ่านของ suite เดิมยังไม่ถือว่าระยะใหม่เสร็จ

### ระยะ 1 — เส้นทางติดตั้งครบ

1. กำหนดสัญญา CLI และ exit codes รักษาการเรียก `watchmode-truth-lab scenario.json ...` เดิม
2. แยกการอ่าน/ตรวจ scenario ออกจากการเริ่ม process ให้ตรวจ config โดยไม่ mutate, spawn หรือเรียก version command ได้ พร้อมชี้ field ที่ต้องแก้
3. ตรวจ dependency ตาม scenario: executable, Node, adapter dependencies, browser build เมื่อเลือก browser และสิทธิ์เขียนรายงาน แสดงวิธีแก้ missing dependency; ไม่ติดตั้งระบบด้วย root อัตโนมัติ
4. ส่งมอบ starter สำหรับ file และ Vite HTTP จาก package resources หรือ adapter bundle ที่ version/checksum ผูกกัน รวม template/lockfile ที่จำเป็น สร้างลงโฟลเดอร์ใหม่และไม่ทับงานผู้ใช้
5. ตรวจ Linux wheel install และ wheel/sdist ใน clean venv; ทดสอบ starter จาก installed assets จริง ไม่มีไฟล์ตกค้างจาก checkout ช่วยให้ผ่าน
6. ทดสอบ Python 3.10 ตาม floor ที่ประกาศ หากยังทำไม่ได้ให้คงสถานะ unverified และไม่รับรองรุ่นนั้นใน release candidate จนมีหลักฐานหรือปรับ support policy อย่างชัดเจน

**งานลงมือรอบแรก:** สัญญา CLI + config preflight พร้อม regression ว่าไม่มี side effects แล้วตรวจแพ็กเกจ Debian จากนั้นเพิ่ม starter และ diagnostics ทีละรอบ

### ระยะ 2 — อ่านสาเหตุและจัดการการหยุดงานได้

- ทำคำอธิบาย `pass`, `stale`, `timeout`, `inconclusive` ให้ตรงกับ reason จริง รวมกรณี match ได้แต่ไม่ทัน stable window ทบทวน README ให้ตรงกับ runner
- เพิ่ม summary ที่อ่านง่ายและเลือก JSON สำหรับ automation ได้ กำหนด stdout/stderr และรักษา consumer เดิมก่อนเปลี่ยน output default
- ตรวจ Ctrl+C/termination ระหว่าง startup, HTTP pending, mutation และ browser observation บน Windows/Linux ก่อนเลือกแก้ lifecycle; ไม่ถือว่ามี defect โดยไม่มี reproduction
- ตรวจ export failure และการแทนที่ report: ไฟล์เดิมยังอ่านได้เมื่อเขียนใหม่ไม่สำเร็จ, temporary file ถูกเก็บ, error ไม่ทำผลกลายเป็น pass
- กำหนด report compatibility; field ใหม่ไม่ทำ reader เดิมเสีย หรือเพิ่ม schema version/migration เมื่อจำเป็น
- ตรวจ bounded logs และการปกปิดข้อมูลที่เลือกไว้ด้วย controlled fixtures รายงานจากคำสั่งผู้ใช้ยังต้องตรวจข้อมูลก่อนแชร์ ไม่รับรองว่าตัวกรองลบทุก secret ได้

กรณีตรวจรับ: dependency หาย, config ผิด, baseline ไม่พร้อม, process ตาย, stale output, HTTP ช้า/ใหญ่, mutation ล้มเหลว, report เขียนไม่ได้, ยกเลิกงาน และ path มีช่องว่าง/Unicode เลือกตรวจ behavior และ integration ที่ได้รับผลจากการแก้แต่ละรอบ

### ระยะ 3 — Workflow ที่มีความหมาย

เลือกโปรเจคและนิยาม “อัปเดตสำเร็จ” ก่อนเขียน oracle: เช่น HTTP token ใหม่, DOM ใหม่โดยไม่ reload หรือ output file ใหม่ HTTP pass ใช้รับรองเฉพาะ endpoint ส่วน browser HMR ต้องมี DOM/session evidence

ถ้ายังไม่มีแอปจริง ให้ใช้ reference app Vite ที่มีหลาย module เตรียม adapter และระบุว่าเป็น fixture การรับรองว่าใช้กับงานผู้ใช้ได้ยังต้องมีแอปหรือ workflow ที่ผู้ใช้เลือก หากแอปใช้ framework ให้เพิ่ม acceptance ของ framework นั้นแทนการอนุมานจาก JavaScript fixture เดิม

ครอบคลุม overwrite, atomic replace, burst ทั้ง native/polling และ watcher-disabled control ใช้สำเนา fixture, dependency ที่ reproduce ได้ และตรวจ manifest ว่ามีไฟล์จำเป็นโดยไม่นำ secrets/live data เข้ามา แยกผล Debian VM, WSL2, Windows และ physical Linux กรณี WSL2 mounted Windows storage ต้องใช้ expectation ตามข้อจำกัดที่บันทึกไว้

เพิ่ม compiler/generator หรือ adapter อื่นเมื่อมีงานและ oracle ชัดเจน Physical Linux และ Safari เป็น release gate เมื่อเลือกประกาศรองรับจริง

### ระยะ 4 — CI และ release artifacts

เตรียม workflow ใน repository สำหรับ Windows/Linux แยก core, Vite และ browser requirements ให้ชัด ทดสอบ minimum Python และ runtime ที่ประกาศรองรับ Browser build/dependency ต้องกำหนด version; required job ที่ skip ถือว่ายังไม่ครบ Optional environments แสดงสถานะแยก

เก็บ JSON/log ทั้ง pass/fail พร้อม code/artifact hashes ใช้ `scripts/test_cycle.py` และ matrix ที่มี control ใช้งานสั้นสำหรับ regression ที่เกี่ยวข้อง และงาน matrix สำหรับ adapter/lifecycle/release changes ไม่เพิ่มรอบซ้ำที่ไม่มีความเสี่ยงต้องตรวจ

Build release artifacts ครั้งเดียวแล้วทดสอบ artifacts เหล่านั้นใน environment สะอาด ตรวจ metadata, LICENSE, installed assets และ console จัด checksum, changelog, troubleshooting และวิธีย้อนกลับ version การเปิดใช้ remote CI, upload, publication และการติดต่อผู้อื่นทำตามขอบเขตที่ผู้ใช้อนุญาตในตอนนั้น

### ระยะ 5 — Checklist ปล่อย 1.0.0

- [ ] ผู้ใช้ใหม่ติดตั้งและทำ first run ตามคู่มือจากเครื่องหรือ venv สะอาดได้
- [ ] Windows/Debian installed-package end-to-end ผ่านจาก artifact ที่จะส่งมอบ
- [ ] ทุก environment/runtime/adapter ที่ประกาศมี required evidence ไม่มี skip ที่นับเป็น pass
- [ ] Workflow จริงที่เลือกผ่าน positive matrix และ stale control ตาม timing policy
- [ ] ไม่มี P0/P1: false pass, ทำข้อมูลผู้ใช้เสีย, ordinary process รั่วที่ reproduce ได้ หรือ workflow หลักติดตั้ง/รันไม่ได้
- [ ] Failed/inconclusive มี reason, exit code และวิธีตรวจต่อ; compatibility ของ CLI/report ผ่าน
- [ ] คู่มือ, support matrix, known limitations, license, changelog และ rollback ตรงกับ artifact
- [ ] ตรวจ artifact/report ที่จะแชร์ว่าไม่พา credentials หรือข้อมูลส่วนตัวออกไป

เริ่ม pilot จากหนึ่ง workflow แล้ววิเคราะห์ปัญหาจริงก่อนเพิ่ม adapter ตั้ง milestone 1.0 เมื่อสัญญา CLI/report นิ่งและ workflow ที่ประกาศใช้งานซ้ำได้ หากเกณฑ์ยังไม่ครบให้คงสถานะ pilot และบอกสิ่งที่ยังขาด

## วิธีทำงานทุกระยะ

Completion check → ตรวจสถานะปัจจุบัน → reproduce fault → แก้หนึ่ง principal issue → ตรวจ behavior/boundary/integration ที่ได้รับผล → เก็บผลและวิเคราะห์ใน [test log](test-log.md) ก่อนรอบถัดไป → review diff → commit

บันทึก defect ที่พิสูจน์แล้วใน [engineering notes](engineering-notes.md) พร้อม priority/reproduction/fix/verification แยก planned work จาก proven fault เก็บ failed evidence และไม่ retry เพื่อเปลี่ยน fail เป็น pass โดยไม่มีการวิเคราะห์ Full suite ใช้เมื่อ core behavior เปลี่ยนหรือถึง release gate เอกสารตรวจ content/links ตามความเสี่ยง

การใช้งานจริงประเมินจากเกณฑ์แผนนี้ [กติกางานวิจัยเดิม](experiment-plan.md) ยังคงใช้กับการอ้างความใหม่/coverage gap และ upstream contribution ตอนนี้ยังไม่ได้พิสูจน์ Vite bug ใหม่หรือ maintainer usefulness การติดต่อผู้อื่นต้องได้รับอนุญาตก่อน
