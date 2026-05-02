# Submission Checklist for Hybrid Haematology Chatbot Dissertation

This checklist converts the appendix guide into a submission-oriented control document. Each item should be marked as `Complete`, `In Progress`, or `Not Included` before the final upload.

## 1. Front Matter Checklist

- [ ] Title page updated with final programme name, student name, student ID, supervisor name, and submission year.
- [ ] Abstract limited to one page and checked against the final dissertation body.
- [ ] Acknowledgements included only if required.
- [ ] Table of contents updated in Word.
- [ ] Page numbering begins from Chapter 1 and appears at the bottom centre.
- [ ] Font, line spacing, and margins checked against the university template.

## 2. Main Body Checklist

### Chapter 1: Introduction
- [ ] Background, problem statement, aim, objectives, scope, and contribution are clearly presented.
- [ ] The project scope is stated as a bounded haematology laboratory assistant rather than a diagnostic system.

### Chapter 2: Literature Review
- [ ] Healthcare chatbot literature is cited.
- [ ] Sequential model literature is cited.
- [ ] Retrieval-based response generation is justified.
- [ ] MLOps and technical-debt literature are cited.
- [ ] Harvard referencing style is consistent.

### Chapter 3: Design and Development
- [ ] SDLC / iterative methodology is explained.
- [ ] System architecture is described.
- [ ] Dataset design and split policy are documented.
- [ ] BiLSTM model design is explained.
- [ ] Retrieval layer and knowledge base are explained.
- [ ] Deployment, monitoring, and retraining workflow are documented.

### Chapter 4: Result Analysis and Evaluation
- [ ] Final split-aware evaluation metrics are reported.
- [ ] Testing strategy is described.
- [ ] Advantages and limitations are discussed critically.
- [ ] Admin monitoring and inference-trace evidence are discussed.
- [ ] Overfitting / generalisation discussion is evidence-based.

### Chapter 5: Conclusions and Further Work
- [ ] Project aims are revisited and answered clearly.
- [ ] Limitations are acknowledged.
- [ ] Future work is realistic and aligned with the current scope.

## 3. Figures and Tables Checklist

- [ ] Figure numbers and captions are consistent.
- [ ] Every figure is referenced from the text.
- [ ] Screenshots are readable at print scale.
- [ ] Figure 3.1 system architecture included.
- [ ] Figure 3.2 MLOps lifecycle included.
- [ ] Figure 3.3 chat UI included.
- [ ] Table 4.1 final model metrics included.
- [ ] Figure 4.1 metric comparison included.
- [ ] Figure 4.2 training curves included.
- [ ] Figure 4.3 dataset and split visual included.
- [ ] Figure 4.4 automated test summary included.
- [ ] Figure 4.5 admin overview included.
- [ ] Figure 4.6 inference trace included.

## 4. References Checklist

- [ ] All in-text citations appear in the final reference list.
- [ ] All reference-list items are cited in the text.
- [ ] DOI / URL / access-date information is complete where required.
- [ ] References are placed after Chapter 5 and not at the end of Chapter 2.

## 5. Appendix Checklist

### Appendix A: Programme Route / Schedule
- [ ] Gantt chart or milestone schedule included.
- [ ] Work sequence reflects the actual project progression.

### Appendix B: Ethics Documentation
- [ ] Ethics or scope statement included.
- [ ] Safety boundary against diagnosis / treatment claims stated clearly.

### Appendix C: Supervision and Control Documentation
- [ ] Supervision notes or meeting records included.
- [ ] Selected issue-log entries included.

### Appendix D: Data and Split Documentation
- [ ] `chatbot/config.yaml` snapshot included.
- [ ] `chatbot/data/splits/general/metadata.json` included.
- [ ] `chatbot/data/splits/report/metadata.json` included.
- [ ] Dataset counts and split ratios summarised.

### Appendix E: UI and Admin Screenshots
- [ ] Chat UI screenshot included.
- [ ] Admin overview screenshot included.
- [ ] Admin data preprocessing screenshot included.
- [ ] Admin inference trace screenshot included.
- [ ] Admin review queue screenshot included.

### Appendix F: Testing Documentation
- [ ] Pytest execution summary showing `26 passed` included.
- [ ] Key test modules listed.
- [ ] Selected regression cases included if space permits.

### Appendix G: Evaluation Documentation
- [ ] `general_model_eval_split_701515` summary included.
- [ ] `report_model_eval_split_701515` summary included.
- [ ] Confusion matrix and per-class outputs included.

### Appendix H: User and Deployment Guide
- [ ] Local direct installation guide included.
- [ ] PostgreSQL configuration included.
- [ ] Docker deployment guide included.
- [ ] Retraining steps from reviewed logs included.

## 6. Artefact Checklist

- [ ] Source code is committed and organised.
- [ ] README is up to date.
- [ ] Dockerfile and Docker Compose file are present.
- [ ] Model artefacts exist for `general` and `report`.
- [ ] Admin panel is reachable.
- [ ] Chat UI is reachable.
- [ ] Required data and evaluation artefacts are preserved.

## 7. Final Submission Checklist

- [ ] Dissertation proofread in full.
- [ ] Spellings standardised to British English / programme expectation.
- [ ] Word count checked for the main body.
- [ ] PDF export generated if required.
- [ ] Source artefact package prepared.
- [ ] Presentation deck prepared.
- [ ] User guide included in appendices or artefact package.
- [ ] Final filenames checked before upload.
