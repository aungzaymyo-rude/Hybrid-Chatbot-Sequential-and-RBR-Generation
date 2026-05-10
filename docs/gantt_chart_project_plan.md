# Hybrid Chatbot Project Gantt Chart

## One-Month Implementation Plan

This Gantt chart presents a structured one-month development schedule for the Hybrid Chatbot for Medical Haematology project. It reflects the practical sequence of work followed in the project lifecycle, from problem definition and dataset preparation through model development, evaluation, deployment, monitoring, and documentation.

```mermaid
gantt
    title Hybrid Chatbot for Medical Haematology - One-Month Project Schedule
    dateFormat  YYYY-MM-DD
    axisFormat  %d %b

    section Project Planning
    Topic selection and scope definition           :done, p1, 2026-04-01, 2d
    Literature review and requirements analysis    :done, p2, 2026-04-02, 4d
    System architecture planning                   :done, p3, 2026-04-04, 3d

    section Data Engineering
    Initial data collection and intent design      :done, d1, 2026-04-05, 4d
    Label refinement and dataset balancing         :done, d2, 2026-04-08, 4d
    Split generation train/val/test               :done, d3, 2026-04-10, 2d

    section Model Development
    General model training                         :done, m1, 2026-04-11, 3d
    Report model training                          :done, m2, 2026-04-13, 3d
    Inference rules and routing integration        :done, m3, 2026-04-15, 3d

    section Application Development
    FastAPI backend implementation                 :done, a1, 2026-04-14, 4d
    Chat UI implementation                         :done, a2, 2026-04-16, 4d
    Admin panel and monitoring UI                  :done, a3, 2026-04-19, 4d

    section Evaluation and MLOps
    Automated testing and debugging                :done, e1, 2026-04-21, 4d
    Retraining pipeline and export tools           :done, e2, 2026-04-23, 3d
    HTTPS, Docker, and deployment validation       :done, e3, 2026-04-25, 3d

    section Finalisation
    Report-analysis expansion and final retraining :done, f1, 2026-04-26, 3d
    Dissertation writing and figures               :done, f2, 2026-04-28, 3d
    Final review, appendix, and submission prep    :done, f3, 2026-04-30, 1d
```

## Weekly Summary

### Week 1
- project topic selection
- requirements analysis
- literature review
- architecture planning

### Week 2
- dataset collection
- intent definition
- label balancing
- split generation
- initial model training

### Week 3
- backend and frontend implementation
- routing logic
- retrieval layer
- admin panel
- monitoring functions

### Week 4
- testing and debugging
- retraining pipeline
- deployment and Docker setup
- dissertation writing
- final validation and submission preparation

## Suggested Dissertation Placement

This chart fits well in:
- `Appendix C` as project control documentation
- `Chapter 3` as a short SDLC planning figure if your supervisor wants timeline evidence in the main body

## Figure Caption Suggestion

Use this caption in the dissertation:

**Figure A.1 Project Gantt chart showing the one-month implementation schedule for the hybrid haematology chatbot**
