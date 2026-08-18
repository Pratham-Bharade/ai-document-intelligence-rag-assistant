# CHANGELOG

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Format
Each release entry uses these categories:
- **Added** — New features
- **Changed** — Changes to existing functionality
- **Deprecated** — Features that will be removed in future
- **Removed** — Features removed in this version
- **Fixed** — Bug fixes
- **Security** — Security-related changes

---

## [Unreleased]

### Added
- Initial project requirements and architecture (Phase 0)
- Development environment setup (Phase 1)

---

## [0.1.0] - 2026-08-18

### Added
- Project repository initialization
- Professional `.gitignore` for Python + Node + AI project
- `.env.example` template with all required environment variables
- `README.md` with project overview, architecture, and setup instructions
- `CHANGELOG.md` following Keep a Changelog format
- Complete backend folder structure (`app/api`, `app/core`, `app/rag`, etc.)
- Backend `requirements.txt` with all planned dependencies
- Python virtual environment setup
- `LICENSE` (MIT)
- Phase 0: Complete system architecture and requirements document

### Technical Notes
- Python 3.10+ required
- PostgreSQL 16+ with pgvector extension planned for Phase 7
- sentence-transformers used for local embeddings (no API cost)
- Groq API used for LLM inference (generous free tier)

---

<!-- Links for diff comparison (update these as you add versions) -->
[Unreleased]: https://github.com/YOUR_USERNAME/ai-rag-assistant/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/YOUR_USERNAME/ai-rag-assistant/releases/tag/v0.1.0
