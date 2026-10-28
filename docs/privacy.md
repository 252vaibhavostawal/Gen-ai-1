# Privacy, Security & Data Governance Specification

## Core Philosophy
The **Multimodal Attendance & Engagement Agent** treats student privacy as a foundational architectural requirement. The application operates **100% offline-first**: all frame processing, acoustic feature extraction, database storage, and report generation take place within the local host environment.

## Data Flows and Ephemeral Processing

```text
[Camera / Video Input] ──> [Frame Decoded into Memory] ──> [Face Detection & Tracking]
                                                                     │
                                                                     ▼
                                                   [Feature Vectors: BBox, Yaw, Pitch]
                                                                     │
[Raw Frame Discarded] <──────────────────────────────────────────────┘
                                                                     │
                                                                     ▼
                                                     [Saved to SQLite: Derived Metrics]
```

### 1. Ephemeral Frame Lifetime
- Raw camera frames and microphone audio streams reside exclusively in volatile memory (RAM) during active detection.
- By default, `RETAIN_RAW_VIDEO = false` and `RETAIN_RAW_AUDIO = false`. Once bounding boxes, landmarks, and acoustic RMS energies are calculated, the underlying pixel arrays and audio buffers are immediately freed.

### 2. Anonymous Tracking vs Identity Verification
- During live sessions, students are initially assigned anonymous session-scoped integers (`Track #1`, `Track #2`).
- Identity mapping to a named student is consent-aware and requires explicit instructor confirmation or approved enrollment mappings.
- The system never infers attendance merely because a student is enrolled in the course roster.

### 3. Configurable Retention & Purging
- Granular 15-second observation windows (pose, movement, audio segments) are stored with configurable retention limits (default 90 days).
- Instructors and administrators can trigger an instant purge via the UI or `POST /api/v1/settings/purge_data` to securely remove historical window metrics while retaining high-level aggregate session summaries.

### 4. Immutable Audit Logs
Every administrative and instructor action generates a permanent audit trail entry in `audit_logs`, recording:
- Event action (`ATTENDANCE_OVERRIDE`, `MAP_STUDENT`, `SESSION_START`, `PURGE_DATA`)
- Target entity and entity ID
- Instructor username and client IP
- Audit timestamp and justification note

### 5. Ethical & Pedagogical Safeguards
- **Observable Behavior vs Mental State**: The application measures observable physical signals (head orientation toward screen/board, physical stillness/movement, and vocal interaction). These indicators **must never** be equated with student attention, comprehension, cognitive effort, or academic performance.
- **Zero High-Stakes Automation**: Automated metrics are strictly formative feedback for instructors. The agent is explicitly prohibited from assigning disciplinary actions, grades, or punitive evaluations.
