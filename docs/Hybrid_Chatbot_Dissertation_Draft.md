# Hybrid Hematology Lab Assistant: Sequential Intent Classification and Retrieval-Based Response Generation

## Title Page (Template)
- Dissertation Draft
- Programme: [Update Programme Title]
- Student: [Update Name]
- Student ID: [Update ID]
- Supervisor: [Update Supervisor]
- Submission Year: 2026

## Abstract
This dissertation investigated the design and evaluation of a hybrid hematology laboratory assistant that combined sequential intent classification with retrieval-based response generation. The project addressed the need for consistent, explainable, and domain-focused assistance in hematology workflows, including complete blood count interpretation support, specimen handling guidance, and quality control queries. A dual-model strategy was implemented using BiLSTM-based classifiers: a general model for workflow and communication intents and a report-focused model for CBC report interpretation intents. The architecture was integrated into a FastAPI service with an administrative interface for logging, review, and export of interaction data.

The dataset pipeline was structured into labeled data ingestion, model-specific dataset construction, and fixed train/validation/test split generation to improve reproducibility. The models were trained with validation-driven checkpoint selection and evaluated on held-out test sets. Reported results indicated strong performance, with the general model achieving approximately 0.893 accuracy and 0.865 macro-F1, and the report model achieving approximately 0.904 accuracy and 0.860 macro-F1 on their respective test sets.

The findings suggested that combining machine learning intent detection with targeted retrieval and rule-based safeguards provided practical and robust behaviour in a constrained medical-support domain. Limitations included class imbalance risks, dependence on curated knowledge content, and constrained multilingual capability. Future work should include broader external validation, confidence calibration studies, and advanced retrieval augmentation.

## Acknowledgements
The support of the project supervisor, peers, and all contributors to testing and feedback was gratefully acknowledged.

## Table of Contents
1. Introduction
2. Literature Review
3. Design and Development
4. Results Analysis and Evaluation
5. Conclusions and Further Work
References
Appendices

## Chapter 1: Introduction
### 1.1 Background
Clinical laboratory environments require timely and consistent communication of procedural guidance and report interpretation support. Hematology workflows involve recurrent, terminology-heavy interactions where errors in understanding can reduce efficiency and potentially increase operational risk. Conversational assistants have therefore been explored as a decision-support and communication aid in focused domains.

### 1.2 Problem Statement
General-purpose chat systems often lack domain constraints, while fully rule-based systems can be brittle and difficult to scale. The project therefore addressed how a hybrid architecture could provide both adaptability and safety for hematology lab use-cases.

### 1.3 Aim and Objectives
The project aimed to design, implement, test, and evaluate a hybrid chatbot for hematology laboratory assistance. Objectives included: (a) developing reproducible data preparation workflows, (b) training sequential intent classifiers, (c) integrating retrieval and routing logic, (d) deploying an API and admin interface, and (e) evaluating predictive and operational performance.

### 1.4 Scope
The implemented system focused on English-only inputs and on predefined hematology intent sets. The scope included two model profiles: a general assistant and a report-focused assistant. Out-of-scope areas included direct diagnosis automation and unrestricted open-domain dialogue.

## Chapter 2: Literature Review
### 2.1 Domain-Specific Conversational Systems
Prior work in domain conversational AI has indicated that constrained-intent systems may achieve stronger reliability than open-domain generative systems in operational contexts. In healthcare-adjacent environments, explainability, predictable behaviour, and traceability are frequently prioritised.

### 2.2 Sequential Models for Intent Classification
Recurrent neural architectures such as LSTM and BiLSTM have historically shown effective sequence modelling for short-text classification tasks. Their strengths include contextual token modelling and comparatively stable training behaviour on moderate-sized datasets.

### 2.3 Retrieval-Based Response Generation
Retrieval-based strategies are widely adopted when factual consistency is required. By selecting responses from curated knowledge sources using lexical similarity approaches (e.g., TF-IDF), systems may reduce hallucination risks compared with unrestricted generation.

### 2.4 Hybrid Architectures and Safety Rules
Hybrid pipelines combine classification, deterministic routing, and retrieval layers to balance flexibility and control. In sensitive domains, static guardrails are often applied for unsupported language, out-of-scope requests, and safety-critical prompts.

### 2.5 Research Gap
A practical gap remained in integrating reproducible ML lifecycle practices (data versioning, fixed splits, exportable evaluation artifacts) with day-to-day admin workflows in a compact laboratory assistant stack. This project addressed that gap through an end-to-end implementation.

## Chapter 3: Design and Development
### 3.1 System Architecture
The system was implemented as a FastAPI application with model registry support, inference routing, and administrative endpoints. The service exposed health, chat, model listing, tracing, and log management routes.

### 3.2 Data Engineering Workflow
A staged data framework was applied: labeled files were merged into a master dataset, model-specific datasets were derived, and fixed train/validation/test splits were generated. This enabled consistent retraining and fair comparative evaluation across model profiles.

### 3.3 Model Design
The core model was a sequential classifier using embeddings, BiLSTM encoding, dropout regularisation, and a linear classification head. Tokenization and vocabulary construction were controlled by configurable frequency and sequence-length constraints.

### 3.4 Dual-Profile Strategy
Two profiles were configured: general and report. The general profile included workflow and communication intents; the report profile emphasised CBC report interpretation intents while retaining shared communication and safety intents.

### 3.5 Response and Routing Layer
After intent prediction, a routing layer resolved static intents and mapped selected intents to retrieval-backed responses from a curated hematology knowledge file. Language checks and guardrails were applied to enforce English-only support and fallback handling.

### 3.6 Persistence and Admin Tooling
Chat logs were stored via a PostgreSQL-backed history store configuration. Administrative APIs supported low-confidence filtering, intent breakdown reporting, review workflows, and CSV export.

### 3.7 Implementation Decisions
It was decided that deterministic routing should be retained for safety-critical and unsupported cases. It was also decided that fixed splits should be used for final metrics to avoid optimistic estimates from non-reproducible holdout configurations.

## Chapter 4: Results Analysis and Evaluation
### 4.1 Evaluation Procedure
Evaluation was carried out on held-out test splits for each model profile. Validation data were used for model selection, while test data were reserved for final reporting.

### 4.2 Quantitative Results
The general model evaluation snapshot reported test accuracy of approximately 0.8928 and macro-F1 of approximately 0.8649. The report model evaluation snapshot reported test accuracy of approximately 0.9040 and macro-F1 of approximately 0.8604.

### 4.3 Interpretation
The results suggested stable predictive quality across both profiles. The higher report-model accuracy indicated good alignment between curated report intents and user-query patterns. Macro-F1 values indicated that minority-class performance remained an important consideration.

### 4.4 Deliverable Assessment Against Learning Outcomes
LO1 was addressed through domain-grounded system design and critical engagement with intent modelling and retrieval paradigms. LO3 was addressed through end-to-end implementation, testing, and evaluation of a substantial software artifact. LO4 was addressed through structured reporting, critical reflection on limitations, and formal citation planning.

### 4.5 Limitations
The system remained dependent on curated intent labels and knowledge content quality. English-only operation limited accessibility. External generalisation beyond the available dataset and workflow context was not fully established.

### 4.6 Validation Artifacts
The evaluation pipeline produced reusable outputs including metrics, confusion matrices, intent distributions, and misclassification logs to support transparent review and iterative improvement.

## Chapter 5: Conclusions and Further Work
### 5.1 Conclusions
A hybrid chatbot architecture for hematology support was successfully designed and implemented. The combined use of sequential intent classification, deterministic routing, and retrieval-based responses produced a practical and auditable assistant aligned with laboratory communication needs.

### 5.2 Further Work
Future work should include multicentre data collection, expanded intent coverage, multilingual extension, confidence calibration, and retrieval enhancement with semantic search. Additional user-centred studies should be conducted to quantify usability and trust in real operational settings.

### 5.3 Reflective Summary
The project demonstrated that robust outcomes were supported not only by model selection but by disciplined engineering practices, including dataset governance, fixed-split evaluation, and traceable admin tooling.

## References (Harvard Style Placeholder)
[Add full Harvard references here, ensuring all in-text citations are matched.]

## Appendices
- Appendix A: Programme Route Diagram
- Appendix B: Ethics Documentation
- Appendix C: Project Schedule/Gantt and Supervision Records
- Appendix D: Design Documentation
- Appendix E: Development Documentation
- Appendix F: Testing Documentation
- Appendix G: Evaluation Documentation
- Appendix H: User Guide
