# CLAUDE.md — agentic-video-rework

Pokyny pro Claude Code / Agent SDK pracujici v tomto repu.

## Co repo dela

Pipeline, ktera ze zaznamu lekce (MP4) udela:
1. CZ transkript s word-level timestampy (faster-whisper large-v3)
2. Detekuje sceny obrazu (PySceneDetect) a ticha/reci (silero-vad)
3. LLM (Claude Sonnet pres Agent SDK) klasifikuje segmenty do tagu CORE / GENERAL / BONUS / SKIP
4. Synthesizer agent slouci 3 signaly → EDL (edit decision list)
5. Human review gate v CLI (uzivatel potvrzuje navrh)
6. ffmpeg sestrihne MP4 podle EDL

## Orchestracni patterny (zadani DU)

- **Sequential workflow** — `src/pipeline.py` (kostra: kroky 1→6)
- **Parallel workflow** — `src/workflows/parallel_analysis.py` (3 souběžné analyzátory)
- **Conditional workflow** — `src/workflows/conditional_routing.py` (per-segment IF/ELSE podle tagu)

Multi-agent patterny (Collaboration/Supervisor/Swarm) nejsou ve scope — pridavaly by komplexitu bez prinosu pro tuto pipeline.

## Konvence

- Python 3.10+, async kde to dava smysl (parallel workflow, agent calls).
- LLM volani: `claude-agent-sdk` (`query()` pro one-shot, `ClaudeSDKClient` pro stateful).
- Soubory bez diakritiky (pozadavek kurzu).
- Komentare jen kde je WHY netrivialni — ne na kazdy radek.
- Kazdy modul ma docstring s jednou vetou: co dela.

## Tag system (z PROJECT_INSTRUCTIONS.md)

- **CORE** — primo k tematu lekce → zachovat
- **GENERAL** — princip plati siroce (i kdyz to bylo o jine platforme) → zachovat
- **BONUS** — zajimave odbocky / Q&A → ulozit do BONUS.md, vyriznout z videa
- **SKIP** — balast (pauzy, technicke problemy, off-topic) → vyriznout

## Cesty

- ffmpeg binarka: `D:\AI_vyvoj\Vibe Coding Robot Dreams AI kurz\tools\ffmpeg.exe` (env `FFMPEG_PATH`)
- vstupy: `data/input/*.mp4`
- vystupy: `data/output/<video_name>/`
- sample: `data/samples/sample_30s.mp4`
