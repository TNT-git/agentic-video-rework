# Agentic Video Rework

> Domaci ukol kurzu **Vibe Coding (Robot Dreams)** — _Agentic Engineering_.
> Prakticky projekt postaveny nad **Claude Agent SDK** s vyuzitim 3 workflow patternu.

## Co projekt dela (1 odstavec)

Ze zaznamu lekce (MP4, typicky 2h staticky zaber prezentatora) vyrobi: (1) kvalitni cesky transkript s word-level timestampy, (2) navrh sestrihu — co je dulezity obsah a co balast, klasifikovany do tagu **CORE / GENERAL / BONUS / SKIP**, (3) po lidskem potvrzeni sestrihne vysledne MP4 a vy-extrahuje "bonusove" odbocky do `bonus.md`. Use case: rework dlouhych skolicich videi do strukturovanych modulu (viz `PROJECT_INSTRUCTIONS.md` v rodicovskem repu).

## Orchestrace (zadani DU)

Pipeline demonstruje **3 workflow patterny** ze 4 (Loop a multi-agent jsou vyslovne mimo scope — nedavaly by v teto architekture realnou hodnotu):

| Pattern | Kde v kodu | Co dela |
|---|---|---|
| **Sequential** | `src/pipeline.py` | Kostra pipeline: kroky 1→6 (extract → transcribe → parallel analyza → synthesize → review → cut). |
| **Parallel** (fan-out/fan-in) | `src/workflows/parallel_analysis.py` | Soubezne bezi 3 analyzatory: scene_detect (PySceneDetect), VAD (silero-vad), LLM classifier (Claude Sonnet). Vysledky se sliji v synthesizer agentu. |
| **Conditional** (IF/ELSE routing) | `src/workflows/conditional_routing.py` | Pro kazdy EDL segment routuje podle tagu do 1 ze 3 kosu: keep (CORE/GENERAL) / bonus (BONUS) / cut (SKIP). |

Pouzity SDK: [`claude-agent-sdk`](https://github.com/anthropics/claude-agent-sdk-python). LLM model: `claude-sonnet-4-6`.

## Architektura

```
[Sequential workflow — pipeline.py]

  1. extract_audio (ffmpeg)               -> data/output/<v>/audio.wav
  2. transcribe (faster-whisper large-v3) -> data/output/<v>/transcript.json
  3. PARALLEL workflow:
       - scene_detect  -> scenes.json
       - vad           -> vad.json
       - classifier    -> (in-memory, segment->tag)
  4. synthesize_edl (LLM)                  -> edl.json
  5. review gate (rich tabulka + y/N)
  6. CONDITIONAL routing per-segment       -> bonus.md
     + ffmpeg cut podle keep[]             -> cut.mp4
```

## Struktura repa

```
agentic-video-rework/
├── pyproject.toml
├── README.md                      <- tento soubor
├── CLAUDE.md                      <- instrukce pro Claude Code v repu
├── .env.example                   <- ANTHROPIC_API_KEY + FFMPEG_PATH
│
├── src/
│   ├── pipeline.py                <- ★ Sequential orchestrator (entry point)
│   ├── review_gate.py             <- human-in-the-loop CLI
│   │
│   ├── workflows/
│   │   ├── parallel_analysis.py   <- ★ Parallel fan-out 3 signalu
│   │   └── conditional_routing.py <- ★ Conditional routing podle tagu
│   │
│   ├── agents/
│   │   ├── classifier.py          <- LLM agent: segment -> CORE/GENERAL/BONUS/SKIP
│   │   └── synthesizer.py         <- LLM agent: 3 signaly -> EDL
│   │
│   └── tools/
│       ├── extract_audio.py       <- ffmpeg: MP4 -> 16kHz WAV
│       ├── transcribe.py          <- faster-whisper large-v3 CZ
│       ├── scene_detect.py        <- PySceneDetect
│       ├── vad.py                 <- silero-vad
│       └── cut_video.py           <- ffmpeg concat sestrih
│
├── data/
│   ├── input/                     <- (gitignore) sem davas MP4
│   ├── output/                    <- (gitignore) transkripty, EDL, cut.mp4
│   └── samples/sample_30s.mp4     <- testovaci 30s vystrizek
│
└── examples/
    └── run_demo.py                <- end-to-end demo na sample
```

## Setup (Windows + GPU)

Predpoklady:
- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- NVIDIA GPU s aktualnimi ovladaci (testovano na RTX 4070 Ti 12GB)
- ffmpeg.exe (napr. `D:\AI_vyvoj\Vibe Coding Robot Dreams AI kurz\tools\ffmpeg.exe`)

```powershell
cd agentic-video-rework
uv venv
.\.venv\Scripts\activate
uv sync
copy .env.example .env
# doplnit ANTHROPIC_API_KEY a (pokud potreba) FFMPEG_PATH
```

## Pouziti

### A) Quick demo na 30s sample

```powershell
python examples\run_demo.py
```

Pokud sample chybi, vyrob ho z lekce:
```powershell
ffmpeg -ss 60 -t 30 -i "data\input\nejaka_lekce.mp4" -c copy "data\samples\sample_30s.mp4"
```

### B) Plne CLI

```powershell
python -m src.pipeline data\input\moje_lekce.mp4
```

Volby:
- `--out PATH` — vlastni vystupni adresar
- `--device cuda|cpu` — kde bezi Whisper (default cuda)
- `--auto-apply` — bez review gate, rovnou sestrihne

### Vystupy v `data/output/<jmeno>/`

| Soubor | Co je uvnitr |
|---|---|
| `audio.wav` | extrahovane audio 16kHz mono |
| `transcript.json` | CZ transkript se segmenty + word timestamps |
| `scenes.json` | detekovane sceny |
| `vad.json` | rec + ticha |
| `edl.json` | finalni navrh sestrihu (EDL) |
| `bonus.md` | BONUS odbocky vy-tazene z videa |
| `cut.mp4` | sestrizene video (jen po potvrzeni v review gate) |

## Tag system

Z `Rework_AI_kurzu/PROJECT_INSTRUCTIONS.md`:

- **CORE** — primo k tematu lekce → zachovat ve videu
- **GENERAL** — princip plati siroce → zachovat ve videu
- **BONUS** — zajimava odbocka → ulozit do `bonus.md`, _nezachovat_ ve videu
- **SKIP** — balast (pauzy, problemy, off-topic) → vyriznout

## Co _neni_ ve scope

Vedome vynechano (planovano jako stretch goal po MVP):
- Multi-agent patterny (Collaboration/Supervisor/Swarm) — v teto pipeline by byly samoucel.
- Loop workflow — iterativni reklasifikace by zlepsila kvalitu, ale komplikuje pipeline.
- Diarizace (kdo mluvi) — ve skolicim videu mluvi hlavne lektor.
- Plny provoz na 2h videich — MVP jede na 30-60s samplu.

## License

Soukromy DU projekt (kurzove odevzdani). Neomezene pouziti pro autora.
