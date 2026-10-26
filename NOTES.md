# Implementation notes (max 250 words)

**Implementation approach:**
SignalTrace V2 is structured into modular Python components: ingestion & validation (`validator.py`), complaint extraction & LLM integration (`extractor.py`), incident signal detection (`investigator.py`), and CLI orchestration (`main.py`). The pipeline enforces strict data integrity: strict UTC timestamps (`YYYY-MM-DDTHH:MM:SSZ`), field validations, and non-reserving deduplication satisfying `total = accepted + invalid + duplicates`. All accepted events are chronologically sorted before applying deterministic incident rules. LLM extraction is validated in Python against the raw text to enforce order ID uniqueness and sanitize unknown issues.

**Tests performed:**
1. Unit and integration verification on `data/smoke/`, achieving 100% exact match against `data/smoke/expected.json`.
2. Full validation and offline incident detection on `data/challenge/`, outputting `result_offline.json` (46 cases).
3. Live LLM evaluation on `data/sample/`, yielding `result_live.json` with 100% equivalence to sample fixtures and zero `llm_errors`.

**Known limitations:**
Sequential API requests in live mode can become a throughput bottleneck for massive ticket volumes; batching or asynchronous concurrent requests (`asyncio`/`aiohttp`) would improve scaling.

**Relevant failure mode or security risk:**
Prompt injection via untrusted customer text or support notes attempting to override system behavior (e.g., instructing the model to mark cases `SIGNAL_FOUND`). Mitigated by strict system prompting, isolating text as raw data, and performing all verdict decisions deterministically in Python.

**Live API provider and result (no keys or secrets):**
Groq API (`qwen/qwen3.8-27b`) via JSON mode (with Gemini fallback); 15 accepted complaints evaluated, 0 LLM errors, exact match with offline extractions.
