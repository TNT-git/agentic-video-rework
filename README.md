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

## Ukazka skutecneho behu

30s sample vystrizeny z **Lekce 5 - Claude Agent SDK** (od 30. minuty), spusteno na CPU:

```
[init] Whisper device: cpu
============================================================
SEQUENTIAL WORKFLOW: Video-to-EDL pipeline
============================================================

[1/6] Extrahuji audio (ffmpeg)...
  -> data\output\sample_30s\audio.wav

[2/6] Transkribuji (faster-whisper large-v3, CZ)...
  -> 3 segmentu, 30.0s

[3/6] Paralelni analyza (scene + vad + LLM classifier)...
  [parallel] scene_detect: start
  [parallel] vad: start
  [parallel] classifier (LLM): start
  [parallel] vad: done (0 silences)
  [parallel] scene_detect: done (0 scenes)
  [classifier] cost: $0.0118
  [parallel] classifier: done (3 classifications)

[4/6] Synthesizer agent (LLM slouci 3 signaly -> EDL)...
  [synthesizer] cost: $0.0415
  -> EDL ma 3 segmentu

[5/6] Review gate
                             Navrh sestrihu (EDL)
┌────┬─────────┬─────────┬────────┬──────────┬───────────────────────────────┐
│  # │      Od │      Do │ Trvani │ Tag      │ Duvod                         │
├────┼─────────┼─────────┼────────┼──────────┼───────────────────────────────┤
│  1 │    0.00 │   17.10 │  17.10 │ SKIP     │ Organizační poznámka o        │
│    │         │         │        │          │ dočasné složce a stažení      │
│    │         │         │        │          │ zdrojáků, žádný obsah.        │
├────┼─────────┼─────────┼────────┼──────────┼───────────────────────────────┤
│  2 │   17.10 │   23.00 │   5.90 │ GENERAL  │ Obecný tip: Claude Code k     │
│    │         │         │        │          │ vysvětlení kódu, platí        │
│    │         │         │        │          │ univerzálně.                  │
├────┼─────────┼─────────┼────────┼──────────┼───────────────────────────────┤
│  3 │   23.00 │   30.02 │   7.02 │ CORE     │ Výklad Claude Agent SDK,      │
│    │         │         │        │          │ přímo k tématu lekce.         │
└────┴─────────┴─────────┴────────┴──────────┴───────────────────────────────┘

[6/6] Conditional routing (per-segment) + ffmpeg sestrih...
  routing: keep=2 bonus=0 skip=1
  -> data\output\sample_30s\cut.mp4

============================================================
HOTOVO.
============================================================
```

LLM klasifikator spravne rozpoznal 3 odlisne casti: prvni 17s je organizacni preambule (**SKIP**), dalsich 5.9s je obecne pouzitelny tip (**GENERAL**), poslednich 7s je hlavni tema lekce (**CORE**). Conditional routing pak nechal jen GENERAL+CORE → vznikl **cut.mp4 (13s)** se 17s vatou vyhozenou na zacatku.

Celkove naklady na 30s sample: **~$0.05** (Sonnet 4.6) + 0$ za Whisper (lokalne).

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
