# Long Input Inference Test Set

Model max token length is `64`. Requests longer than 64 tokens are truncated before sequence inference.

| Case | Model | Chars | Tokens | Truncated | Intent | Conf. | Source |
|---|---|---:|---:|---|---|---:|---|
| LT-01 | general | 12 | 3 | no | cbc_info | 0.984 | retrieval |
| LT-02 | general | 139 | 28 | no | sample_collection | 0.989 | retrieval |
| LT-03 | general | 216 | 34 | no | fallback | 0.422 | static |
| LT-04 | general | 158 | 30 | no | coag_test | 0.999 | retrieval |
| LT-05 | general | 164 | 26 | no | sample_collection | 0.999 | retrieval |
| LT-06 | general | 163 | 27 | no | blood_smear | 0.950 | retrieval |
| LT-07 | general | 182 | 28 | no | sample_collection | 0.469 | static |
| LT-08 | general | 176 | 29 | no | critical_value_reporting | 0.945 | retrieval |
| LT-09 | general | 239 | 37 | no | sample_collection | 0.576 | retrieval |
| LT-10 | general | 311 | 43 | no | coag_test | 0.986 | retrieval |
| LT-11 | general | 363 | 73 | yes | differential_review | 0.669 | static |
| LT-12 | general | 364 | 73 | yes | coag_test | 0.494 | retrieval |
| LT-13 | general | 437 | 73 | yes | fallback | 0.347 | static |
| LT-14 | general | 438 | 73 | yes | fallback | 0.330 | static |
| LT-15 | general | 470 | 79 | yes | fallback | 0.411 | retrieval |
| LT-16 | report | 42 | 9 | no | report_flag_result_analysis | 0.993 | analysis |
| LT-17 | report | 23 | 4 | no | report_flag_result_analysis | 0.984 | analysis |
| LT-18 | report | 11 | 4 | no | report_numeric_result_analysis | 0.999 | analysis |
| LT-19 | report | 10 | 3 | no | report_numeric_result_analysis | 0.977 | analysis |
| LT-20 | report | 22 | 6 | no | report_numeric_result_analysis | 1.000 | analysis |
| LT-21 | report | 16 | 4 | no | report_numeric_result_analysis | 0.996 | analysis |
| LT-22 | report | 17 | 5 | no | report_numeric_result_analysis | 1.000 | analysis |
| LT-23 | report | 31 | 9 | no | report_numeric_result_analysis | 0.999 | analysis |
| LT-24 | report | 38 | 12 | no | report_numeric_result_analysis | 1.000 | analysis |
| LT-25 | report | 35 | 10 | no | report_numeric_result_analysis | 1.000 | analysis |
| LT-26 | report | 210 | 38 | no | report_numeric_result_analysis | 0.998 | analysis |
| LT-27 | report | 431 | 74 | yes | report_numeric_result_analysis | 0.850 | analysis |
| LT-28 | report | 432 | 74 | yes | report_numeric_result_analysis | 0.850 | analysis |
| LT-29 | report | 222 | 44 | no | report_numeric_result_analysis | 0.771 | analysis |
| LT-30 | report | 304 | 58 | no | report_numeric_result_analysis | 0.957 | analysis |

## Notes

- Cases LT-11, LT-13, LT-15, LT-27, and LT-28 are useful truncation tests.
- Cases LT-23, LT-24, LT-29, and LT-30 are multi-value report analysis tests.
- Cases LT-07, LT-11, LT-13, LT-14, and LT-15 show current failure or drift cases worth keeping as regression tests.

## Full Responses

### LT-01

- Prompt: `What is CBC?`
- Response: A CBC, or complete blood count, is a routine hematology test that reports red blood cells, white blood cells, hemoglobin, hematocrit, platelets, and key red cell indices.

### LT-02

- Prompt: `Hi, before I start my shift in the hematology lab, can you tell me what CBC means and what this test is generally used for in routine work?`
- Response: A hemolyzed sample may compromise result quality and should be reviewed under your CBC acceptance criteria. Severe hemolysis often requires rejection or recollection depending on SOP.

### LT-03

- Prompt: `In our morning collection round we received several specimens and one clinician asked which tube is used for coagulation tests because the form was unclear and the nurse wants to recollect correctly before transport.`
- Response: Sorry, I did not understand that. Could you rephrase?

### LT-04

- Prompt: `Please explain what should be done if a citrate tube for PT and aPTT is underfilled, because the sample came from a difficult draw and the ratio may be wrong.`
- Response: An underfilled citrate tube changes the blood-to-anticoagulant ratio and can falsely prolong PT and aPTT results. Most laboratories reject or recollect underfilled coagulation specimens.

### LT-05

- Prompt: `During specimen reception in hematology, what are the rejection criteria for a CBC sample if the EDTA tube is clotted, mislabeled, leaking, or delayed in transport?`
- Response: Common CBC rejection criteria include wrong tube, unlabeled or mislabeled specimen, visible clotting, severe underfill, and excessive delay outside your lab's stability limits.

### LT-06

- Prompt: `In the blood film bench workflow, can you explain why a peripheral blood smear is prepared and what the technologist is looking for when reviewing cell morphology?`
- Response: A peripheral blood smear is a stained blood film examined microscopically to assess red cell morphology, white cell morphology, platelets, and abnormal circulating elements.

### LT-07

- Prompt: `Our analyzer quality control result is outside range this morning after startup and before patient release, so what should be done first according to standard hematology QC practice?`
- Response: For CBC, collect in an EDTA (lavender top) tube, fill to the line, gently invert 8-10 times, label immediately, and avoid hemolysis. Follow local SOP for stability and transport.

### LT-08

- Prompt: `If a platelet count is critically low and the result is verified, what is the normal critical value reporting workflow in a hematology laboratory before the report is released?`
- Response: A critical hematology value is a result that may indicate urgent clinical risk and must be verified, communicated promptly to the responsible clinical contact, and documented according to local policy.

### LT-09

- Prompt: `I am going to describe a long situation from accessioning, transport, reception, labeling, centrifuge delay, recollection notes, and handoff to the bench, but the key question is simple: which tube is used for CBC collection in hematology?`
- Response: CBC is typically collected in an EDTA tube, commonly the lavender-top tube. Follow your lab SOP for the approved tube type and fill requirements.

### LT-10

- Prompt: `Please ignore the long background about ward handover, transport timing, porter delay, system downtime, label printer issues, extra conversations about lunch, corridor workflow, refrigerator checks, and staffing shortage, and just answer this hematology question: what should be done with a clotted EDTA sample?`
- Response: A clotted citrate sample is generally unsuitable for routine coagulation testing because clot formation invalidates PT and aPTT assessment. Most laboratories reject it and request recollection.

### LT-11

- Prompt: `word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word what is aPTT?`
- Response: Differential review covers neutrophils, lymphocytes, monocytes, eosinophils, basophils, and when manual white-cell review is needed.

### LT-12

- Prompt: `What is aPTT? word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word word `
- Response: aPTT, or activated partial thromboplastin time, evaluates the intrinsic and common coagulation pathways. It is used in coagulation screening and heparin-related monitoring workflows.

### LT-13

- Prompt: `noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise which tube is used for coagulation tests?`
- Response: Sorry, I did not understand that. Could you rephrase?

### LT-14

- Prompt: `which tube is used for coagulation tests? noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise `
- Response: Sorry, I did not understand that. Could you rephrase?

### LT-15

- Prompt: `noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise what are the rejection criteria for a CBC sample? extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra extra `
- Response: A CBC, or complete blood count, is a routine hematology test that reports red blood cells, white blood cells, hemoglobin, hematocrit, platelets, and key red cell indices.

### LT-16

- Prompt: `What is the meaning of anemia in a report?`
- Response: A report flag for anemia usually means hemoglobin and/or hematocrit is below the laboratory reference range. It should be reviewed together with RBC count, MCV, RDW, and smear findings. This is a report pattern rather than a diagnosis.

### LT-17

- Prompt: `My report shows anemia.`
- Response: A report flag for anemia usually means hemoglobin and/or hematocrit is below the laboratory reference range. It should be reviewed together with RBC count, MCV, RDW, and smear findings. This is a report pattern rather than a diagnosis.

### LT-18

- Prompt: `WBC is 13.7`
- Response: Using the assistant's common adult range for WBC, WBC 13.7 (4-11 x10^3/uL) is above range and is commonly reported as leukocytosis when high and leukopenia when low.

### LT-19

- Prompt: `PLT is 365`
- Response: Using the assistant's common adult range for PLT, PLT 365 (150-400 x10^3/uL) is within range and is within a common adult platelet reference interval.

### LT-20

- Prompt: `Adult male HGB is 13.0`
- Response: Using the assistant's common adult male range for HGB, HGB 13 (13.5-17.5 g/dL) is below range and is supportive of an anemia-pattern review when low and an increased hemoglobin pattern when high.

### LT-21

- Prompt: `Female HCT is 45`
- Response: Using the assistant's common adult female range for HCT, HCT 45 (36-46 %) is within range and is within a common adult hematocrit reference interval.

### LT-22

- Prompt: `Child HGB is 10.5`
- Response: Using the assistant's common pediatric range for HGB, HGB 10.5 (11-14.5 g/dL) is below range and is supportive of an anemia-pattern review when low and an increased hemoglobin pattern when high.

### LT-23

- Prompt: `Age is 24 MCV is 72, PLT is 365`
- Response: Using the assistant's common adult range, report review summary: MCV 72 (80-100 fL) is below range and is consistent with a microcytic pattern when low and a macrocytic pattern when high. PLT 365 (150-400 x10^3/uL) is within range and is within a common adult platelet reference interval.

### LT-24

- Prompt: `Age is 50 WBC is 13 MCV is 73 PLT is 1`
- Response: Using the assistant's common adult range, report review summary: WBC 13 (4-11 x10^3/uL) is above range and is commonly reported as leukocytosis when high and leukopenia when low. MCV 73 (80-100 fL) is below range and is consistent with a microcytic pattern when low and a macrocytic pattern when high. PLT 1 (150-400 x10^3/uL) is below range and is commonly reported as thrombocytopenia when low and thrombocytosis when high.

### LT-25

- Prompt: `In my report WBC is 13.36 age is 43`
- Response: Using the assistant's common adult range for WBC, WBC 13.36 (4-11 x10^3/uL) is above range and is commonly reported as leukocytosis when high and leukopenia when low.

### LT-26

- Prompt: `The clinician sent a long message about fatigue, follow-up, previous tests, and general concerns, but the actual report line says WBC is 13.7 and PLT is 365, so please help me interpret the report support only.`
- Response: Using the assistant's common adult range, report review summary: WBC 13.7 (4-11 x10^3/uL) is above range and is commonly reported as leukocytosis when high and leukopenia when low. PLT 365 (150-400 x10^3/uL) is within range and is within a common adult platelet reference interval.

### LT-27

- Prompt: `noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise WBC is 13.7`
- Response: Using the assistant's common adult range for WBC, WBC 13.7 (4-11 x10^3/uL) is above range and is commonly reported as leukocytosis when high and leukopenia when low.

### LT-28

- Prompt: `WBC is 13.7 noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise noise `
- Response: Using the assistant's common adult range for WBC, WBC 13.7 (4-11 x10^3/uL) is above range and is commonly reported as leukocytosis when high and leukopenia when low.

### LT-29

- Prompt: `Age is 16 WBC is 13.1 HGB is 10.5 MCV is 72 and PLT is 420 with comments about school fatigue, recent fever, follow up timing, family concern, and repeated questions from the ward about what the numbers mean in the report.`
- Response: Using the assistant's common pediatric range, report review summary: WBC 13.1 (5-14.5 x10^3/uL) is within range and is within a common adult WBC reference interval. HGB 10.5 (11-14.5 g/dL) is below range and is supportive of an anemia-pattern review when low and an increased hemoglobin pattern when high. MCV 72 (77-95 fL) is below range and is consistent with a microcytic pattern when low and a macrocytic pattern when high. PLT 420 (150-450 x10^3/uL) is within range and is within a common adult platelet reference interval.

### LT-30

- Prompt: `I will give a very long report-style phrase with several distractions about booking forms, queue times, system lag, and transport notes, but the essential part is that my CBC report says RBC is 2.8 RDW is 21.2 MPV is 13.9 and I want help understanding whether these values are high, low, or within range.`
- Response: Using the assistant's common adult range, report review summary: RBC 2.8 (4-6.2 x10^6/uL) is below range and is suggestive of a reduced red-cell count pattern when low and an increased red-cell count pattern when high. RDW 21.2 (11.5-14.5 %) is above range and is indicative of increased red-cell size variation when high. MPV 13.9 (7.5-12.5 fL) is above range and is best reviewed with platelet count and smear findings when abnormal.
