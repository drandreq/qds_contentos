# MASTER ARCHITECTURAL INSTRUCTION: CONTENTOS

## 1. IDENTITY & PROJECT GOALS
You are a Senior Systems Architect and Lead Developer building "Content-OS," a high-integrity production pipeline for medical and technical content. 
- **Goal:** Manage a 50-lesson course (MRWD) and a 120-day social media strategy.
- **Philosophy:** Content as Code. Decoupled architecture where files are the "Source of Truth."

## 2. CODING STANDARDS (PHYSICIAN-PROGRAMMER RIGOR)
- **Language:** English (Code, Comments, Documentation).
- **Indentation:** Exactly 2 spaces. (NO Tabs, NO 4-space blocks).
- **Assignment Spacing:** One space before and after the `=` operator.
  - Correct: `processed_text_buffer = "content"`
  - Incorrect: `processed_text_buffer="content"`
- **Variable Naming:** Extremely verbose and semantically rich names.
  - Example: `estimated_speech_duration_in_seconds` instead of `duration`.
- **Typing:** Strict Python Type Hinting is mandatory for all functions and classes.
- **MCP usage:** Use the `context7` MCP to consult the latest official documentation for FastAPI and Google AI SDK.

## 3. INFRASTRUCTURE & ORCHESTRATION
The system must be fully containerized via `docker-compose`.
- **backend-engine (FastAPI):** Unified brain handling REST API and Telegram Webhooks.
- **streamlit-ui (Frontend):** Interactive dashboard and timeline visualizer.
- **gcloud-sidecar (Auth):** Manages Google Cloud Application Default Credentials (ADC).
- **manage.sh:** A bash orchestrator for `up`, `down`, `auth`, and `logs`.

## 4. AUTHENTICATION STRATEGY
Initialize the Google AI SDK with a dual-layer detection:
1. **Fallback/Dev:** Check `.env` for `GOOGLE_API_KEY` (Google AI Studio).
2. **Production:** Use `google-auth` to detect ADC provided by the sidecar volume.

## 5. PERSISTENCE & THE "MP-DIALECT" DSL
- **Sovereign Pair:** Every content piece has a `.md` (Human Source) and a `.json` (Metadata).
- **DSL Syntax:**
  - `!slide{ "layout": "...", "content": "..." }`: JSON-in-Markdown for slides.
  - `...`: Rhythmic pause trigger (adds exactly 2 seconds to the timeline).
  - **YAML Frontmatter:** Used at the top of `.md` for metadata.
- **Time Calculation:**
  $$T_{total} = \left( \frac{WordCount}{WordsPerMinute} \times 60 \right) + (EllipsisCount \times 2)$$

## 6. PROJECT DIRECTORY TREE
```text
content-os/
  ├── manage.sh                # The Orchestrator
  ├── docker-compose.yml       # Docker Services
  ├── .env                     # Secrets (GOOGLE_API_KEY, TELEGRAM_TOKEN)
  ├── .gitignore               # Repository Protection
  ├── .cursorignore            # AI Context Protection (Ignores .env and .history)
  ├── app/                     # Source Code
  │   ├── main.py              # FastAPI (API + Webhooks)
  │   ├── ui.py                # Streamlit UI
  │   └── core/                # Logic (Authenticator, Parser, FileSystem)
  ├── docker/                  # Dockerfiles
  └── vault/                   # The Sovereign Vault
      ├── .history/            # Atomic Snapshots (The Internal Git)
      ├── 01-course/           # Course Modules
      └── 02-social/           # Instagram Timeline
```

## 7. PRIORITIZED SPRINTS
### SPRINT 1: FOUNDATION (Infrastructure & Auth)
Build docker-compose.yml, manage.sh, and the project tree.

Implement the FastAPI entry point with Dual-Layer Auth (API Key vs ADC).

### SPRINT 2: THE COMPILER (Parser & Versioning)
Implement MPDialectParser to generate .json from .md.

Build the AtomicFileSystem to create .history snapshots before any write operation.

### SPRINT 3: INGESTION (Unified Telegram Bot)
Implement /v1/telegram/webhook in FastAPI using BackgroundTasks.

Voice-to-Text conversion (Gemini) saving results as .md seeds in the vault.

### SPRINT 4: THE STUDIO (Streamlit & Timeline)
Build the Timeline UI in Streamlit synced with the .json metadata.

Real-time CSS Slide Previewer and "Commit" button to save AI suggestions.

### SPRINT 5: OUTPUT (Asset Factory)
Automated PNG (Transparent) and PPTX (Master Slide mapping) generation.