# Canonical Reference Corpus

This is the deduplicated index of repositories, datasets, papers, sites, and platform documentation discussed during the HIVE / Connectome Bridge session. **Being listed here does not make a project a dependency, a validated scientific result, or an endorsed architecture.**

## Review labels

- **source-inspected** — selected implementation/source files were read in addition to documentation.
- **readme-reviewed** — README/project documentation was read; not a line-by-line source audit.
- **reviewed / research-reviewed** — previously audited at repository/documentation or research-source level.
- **metadata-verified** — location/existence verified, but no deep audit claim.
- **reference-only / discussed** — preserved because it was discussed; no substantive audit claim.

Normalized machine-readable copy: `docs/REFERENCE_CORPUS.json`.

## Normalization notes

- `sahibzada-allahyar/gliner2-ultrafastv` → `sahibzada-allahyar/gliner2-ultrafast`.
- `jgridifier/jev-research-evalv` → `jgridifier/jev-research-eval`.
- `vercel-labs/ai-cliv` → `vercel-labs/ai-cli`.
- Concatenated URLs in the chat were split into individual references and duplicate repetitions were removed.
- Both public FLM locations discussed in the session are preserved (`FLModel/flm` and `nftechie/flm`) rather than silently choosing one.

## Connectome datasets

- [MaleCNS v1.0](https://male-cns.janelia.org/) — **research-reviewed** — Canonical adult male Drosophila CNS data portal.

## C. elegans / worm runtimes

- [GoPiGo C. elegans connectome robot](https://github.com/Connectome/GoPiGo) — **reviewed**
- [jonnonz1/c302](https://github.com/jonnonz1/c302) — **reviewed**
- [OpenWorm c302](https://github.com/openworm/c302) — **readme-reviewed** — Current OpenWorm NeuroML 2 modelling framework; preferred upstream reference.
- [OpenWorm CElegansNeuroML](https://github.com/openworm/CElegansNeuroML) — **readme-reviewed** — Historical project; README points to c302 as the newer initiative.
- [OpenWorm](https://openworm.org/) — **reviewed**
- [celeganssim](https://github.com/vdmkenny/celeganssim) — **readme-reviewed** — Whole-organism C. elegans simulator and checksum/provenance reference.
- [worm-sim](https://github.com/heyseth/worm-sim) — **metadata-verified**
- [Nematoduino](https://github.com/nategri/nematoduino) — **readme-reviewed**
- [worm-whisperer](https://github.com/kairess/worm-whisperer) — **readme-reviewed** — Pre-registered experiments, preserved negative results, wiring-shuffle controls.

## Fly connectome runtimes and experiments

- [fly.ai](https://github.com/alextitonis/fly.ai) — **readme-reviewed** — MaleCNS flybrain runtime; also contains SSH Fighter and reusable reservoir/readout utilities.
- [Flybook](https://github.com/FLModel/flybook) — **metadata-verified**
- [desktop-fly](https://github.com/DenisSergeevitch/desktop-fly) — **reviewed**
- [DOOMFLY](https://github.com/nftechie/doomfly) — **reviewed**
- [DOOM-x-Fly](https://github.com/Aur1ety/DOOM-x-Fly) — **metadata-verified**
- [fly_ocr](https://github.com/jerryjliu/fly_ocr) — **reviewed** — Connectome + small learned decoder; strong separation of fixed substrate and learned readout.
- [fly-chess](https://github.com/tolatolatop/fly-chess) — **reviewed**
- [fruit-fly-lab](https://github.com/vaibhavkedarisetti/fruit-fly-lab) — **reviewed**
- [Lulzx/fly-brain](https://github.com/Lulzx/fly-brain) — **reviewed**
- [fly-dating-app](https://github.com/jaredpalmer/fly-dating-app) — **reviewed**
- [fly-wirehead](https://github.com/mattyhempstead/fly-wirehead) — **reviewed**
- [fly-766/fly](https://github.com/fly-766/fly) — **reviewed** — Useful authority split: neural proposal vs admissibility/accounting/verification.
- [FlyCoder](https://github.com/tolga-ileri/FlyCoder) — **reviewed**
- [yaxis-lab/fly-brain](https://github.com/yaxis-lab/fly-brain) — **reviewed** — Sparse repository; retained as a lower-confidence API/data reference.
- [Stonkfly](https://github.com/nftechie/stonkfly) — **readme-reviewed** — Full MaleCNS proposes trades while deterministic code/AgentKit owns execution limits.
- [Fly64](https://github.com/ornata/fly) — **readme-reviewed** — MaleCNS drives SM64; dashboard makes neural readouts and engineered mappings visible.
- [rembish/fruit-fly](https://github.com/rembish/fruit-fly) — **readme-reviewed**
- [snedea/flybrain](https://github.com/snedea/flybrain) — **metadata-verified** — Repository exists; README was not readable at the path queried.
- [flypoke](https://github.com/vshapenko/flypoke) — **research-reviewed** — CPU-oriented FlyWire spiking simulation precedent.
- [Ommatid](https://github.com/FutureJJ/ommatid) — **research-reviewed** — MaleCNS/FlyVis body-transfer experiment; pre-registration and negative results are useful methodology.

## Connectome + language experiments

- [FLM / Fly Language Model (org location)](https://github.com/FLModel/flm) — **metadata-verified** — Preserved as a canonical project location mentioned by the user; a second public location also exists.
- [FLM / Fly Language Model (nftechie location)](https://github.com/nftechie/flm) — **readme-reviewed** — Fixed MaleCNS graph plus trained small adapter; matched direct-input control is especially relevant.
- [fly-as-a-lm](https://github.com/leetae9yu/fly-as-a-lm) — **reviewed** — Strong factorial/shuffle controls; language task experiments use a subset rather than the full graph.
- [ConnectomeGPT-Worm](https://huggingface.co/drmylesgarveylabs/connectome-gpt-worm) — **research-reviewed** — C. elegans connectome inserted as a biological intermediate layer with explicit dense/random controls.

## Larval insect connectomes

- [Fo170/drosophila_brain](https://github.com/Fo170/drosophila_brain) — **readme-reviewed**
- [CHIMERA](https://github.com/caparison1234/chimera) — **readme-reviewed** — Larval connectome + language-to-sensory translator + MuJoCo body.

## Multi-connectome experiments

- [amfly](https://github.com/aravpanwar/amfly) — **reviewed**

## Embodiment and robotics

- [FlyBody](https://github.com/TuragaLab/flybody) — **reviewed**
- [Fly Brain Bridge](https://www.doriantodd.com/projects/fly-brain-bridge/) — **research-reviewed**
- [CyberFly](https://flymaxxing.com/projects/cyberfly/) — **research-reviewed**
- [NeuroMechFly v2](https://www.nature.com/articles/s41592-024-02497-y) — **research-reviewed**

## Hardware runtimes

- [Hailo Apps](https://github.com/hailo-ai/hailo-apps) — **readme-reviewed** — Pi 5/Hailo deployment reference; not required by current CPU-first HIVE.

## Community indexes

- [Flymaxxing project index](https://flymaxxing.com/) — **research-reviewed**

## Jev / agent / UX projects

- [newsjack](https://github.com/elvisun/newsjack) — **readme-reviewed** — Job-first capability UX; human and agent install paths.
- [jev-semgrep](https://github.com/uehaj/jev-semgrep) — **readme-reviewed** — Semantic proposition grep; AND/OR/NOT composition.
- [NERVE](https://github.com/h100envy/nerve) — **source-inspected** — Each node declares ownership/boundary; deterministic spine and reflexes.
- [SemIf](https://github.com/TheoLeeCJ/SemIf) — **readme-reviewed** — Open typed-decision interface using model logits; useful local-decision precedent.
- [Jev X Sentiment Analysis](https://github.com/brainstormity/Jev-X-Sentiment-Analysis) — **readme-reviewed** — Deterministic preprocessing + Jev + human-readable decision card.
- [Jev Trades](https://github.com/zadescoxp/Jev-Trades) — **readme-reviewed** — Concrete start/stop workflow and dashboard instead of raw model objects.
- [gliner2-ultrafast](https://github.com/sahibzada-allahyar/gliner2-ultrafast) — **readme-reviewed** — Local GLiNER2 browser decision layer; corrected from user typo gliner2-ultrafastv.
- [Jev Cookbook](https://github.com/nexibeo/jev-cookbook) — **readme-reviewed** — Job/recipe framing; code prepares facts and owns actions.
- [OpenWork](https://github.com/different-ai/openwork) — **readme-reviewed** — Workspace/capability front door; internal tools hidden behind user jobs.
- [hermes-jev-approvals](https://github.com/anpicasso/hermes-jev-approvals) — **readme-reviewed** — Approval-only auxiliary task, strict missing-answer handling, operator policy.
- [Clean Code Review](https://github.com/frostney/clean-code-review) — **readme-reviewed** — Evidence-first findings plus concise prose; structured MCP mirror.
- [citation-verifier](https://github.com/MarissaFamularo/citation-verifier) — **readme-reviewed** — Citation/evidence verification reference.
- [Jev Search](https://github.com/superagents-lab/jev-search) — **readme-reviewed** — Intent routing, concurrent search lanes, relevance ranking, human result stream.
- [PageGrade](https://github.com/kitze/pagegrade) — **readme-reviewed** — Progressive visible grades; raw JSON export is secondary.
- [jev-scout](https://github.com/AkashPriyadarshii/jev-scout) — **readme-reviewed** — Human terminal cards by default; JSON only on explicit flag.
- [jev-seo](https://github.com/AkashPriyadarshii/jev-seo) — **readme-reviewed** — Small local Rust CLI/MCP with task-specific commands.
- [Supercov](https://github.com/supercorp-ai/supercov) — **readme-reviewed** — Give the agent a job, show concise evidence by default, JSON optional.
- [jev-reranker](https://github.com/hotchpotch/jev-reranker) — **readme-reviewed** — Evidence relevance filtering between retrieval and generation.
- [jev-skip](https://github.com/valentynkit/jev-skip) — **readme-reviewed** — One typed classification pass, visible uncertainty, conservative action threshold.
- [Jev Social](https://github.com/socai-io/jev-social) — **readme-reviewed** — Goal -> typed read-only operations -> cards/table/evidence report.
- [Jev Ultrafast](https://github.com/browser-use/jev-ultrafast) — **source-inspected** — Bounded observe/choose/act with freshness checks and inspectable trace.
- [jev-agent-browser](https://github.com/forvela/jev-agent-browser) — **readme-reviewed** — Parent owns scope; Jev owns bounded next operation; structured handoff.
- [pi-typesafe-jev](https://github.com/legacybridge-tech/pi-typesafe-jev) — **readme-reviewed** — Narrow judgment tools, question files, strict response validation.
- [jev-judgment](https://github.com/HyunjunJeon/jev-judgment) — **readme-reviewed** — Jev as narrow pre-question/pre-action/post-failure judgment skill.
- [limpet](https://github.com/noplan-inc/limpet) — **readme-reviewed** — Invisible stop hook; user should not babysit the agent.
- [Augustus](https://github.com/24601/Augustus) — **readme-reviewed** — Large design atlas for placing typed judgment vs code/policy/LLM.
- [super-jev](https://github.com/Kevthetech143/super-jev) — **readme-reviewed** — Evidence gates, fetch/routing, pre-rules, explicit no-match behavior.
- [fastbrowse](https://github.com/agent-labs-dev/fastbrowse) — **source-inspected** — Clean split: Jev picks; LLM reads/writes; code owns gates.
- [Jev Browser](https://github.com/jkudish/jev-browser) — **readme-reviewed** — Task+URL front door; final page/screenshot/trace; explicit statuses.
- [pi-fast-jev-compaction](https://github.com/joelhooks/pi-fast-jev-compaction) — **readme-reviewed** — Verbatim conversation preservation while pruning stale tool history.
- [Atomic](https://github.com/bastani-inc/atomic) — **readme-reviewed** — Explicit, checkable execution graphs and long-running verification loops.
- [fast-jev-compaction](https://github.com/tamaratran/fast-jev-compaction) — **readme-reviewed** — Jev context compaction reference.
- [fast-dev-compaction](https://github.com/leonaaardob/fast-dev-compaction) — **readme-reviewed** — Codex port of Jev compaction with explicit fallback contract.
- [BrowserClaw](https://github.com/GoldenLoaf24h/browserclaw) — **readme-reviewed** — Dual-brain local browser architecture and human takeover.
- [Jev for Chrome](https://github.com/chy4pro/jev-for-chrome) — **readme-reviewed** — Watch/step/copy-trace UX in the user’s real browser.
- [jev-pruner](https://github.com/tamaratran/jev-pruner) — **readme-reviewed** — Prunes noisy tool output while preserving verbatim relevant chunks.
- [Jev Desktop](https://github.com/yikangy873-gif/jev-desktop) — **readme-reviewed** — Bounded decision loop inside Computer Use; caller retains scope and verification.
- [jev-curate](https://github.com/AkashPriyadarshii/jev-curate) — **readme-reviewed** — Verbatim data curation/filtering; no generative rewrite.
- [jev-research-eval](https://github.com/jgridifier/jev-research-eval) — **readme-reviewed** — Reproducible browser research evaluation harness; corrected from jev-research-evalv.
- [Vercel ai-cli](https://github.com/vercel-labs/ai-cli) — **readme-reviewed** — Typed evaluate CLI plus human command surface; corrected from ai-cliv.
- [Smithers](https://github.com/smithersai/smithers) — **readme-reviewed** — Codebase maintainer runtime with explicit flows and inspectable runs.
- [jev_stock](https://github.com/sosopop/jev_stock) — **readme-reviewed** — Structured market-state reports; probabilities explicitly not equated to win rate.
- [Jev Trade](https://github.com/aowang-ai/jev-trade) — **readme-reviewed** — Live/paper desk UX; tick->decision->order flow with dry-run first.
- [jev-belay](https://github.com/valentynkit/jev-belay) — **readme-reviewed** — Evidence gate before an agent can claim done.
- [jev-canvas](https://github.com/gaborishka/jev-canvas) — **readme-reviewed** — Direct speech/pointing UX over many typed decisions; code owns thresholds/actions.
- [wakegate](https://github.com/shitianfang/wakegate) — **readme-reviewed** — Cheap decision gate before waking an expensive model; fail-open on uncertainty/error.
- [Jevinik / jevocks](https://github.com/unicodeveloper/jevocks) — **readme-reviewed** — Human terminal with evidence quality/signals/timing instead of raw decision JSON.
- [Jev’s Fly](https://github.com/webdevcody/jevs-fly) — **source-inspected** — Visible HUD maps typed decisions to actions; raw state is inspectable detail.

## Jev integrations

- [Agent Zero plugins / TypeSafe entry](https://github.com/agent0ai/a0-plugins/tree/main/plugins/typesafe_ai) — **reviewed**
- [a0-typesafe-ai](https://github.com/3clyp50/a0-typesafe-ai) — **reviewed**
- [TypeSafe skills](https://github.com/typesafe-ai/skills) — **reference-only**

## Jev ecosystem sites

- [Semantic Space](https://semanticspace.dev/) — **discussed**
- [Made with Jev](https://madewithjev.com/) — **reviewed**
- [Made with Jev — Agents & Browsers](https://madewithjev.com/categories/agents-and-browsers) — **reviewed**

## Bee / insect-navigation research

- [Building a connectome of the insect brain’s navigational center](https://www.lunduniversity.lu.se/publication/36d49300-14d1-4a52-a83d-4efea73dbc29) — **research-reviewed**
- [A projectome of the bumblebee central complex](https://elifesciences.org/articles/68911) — **research-reviewed**
- [Emulating insect brains for neuromorphic navigation](https://arxiv.org/html/2401.00473v1) — **research-reviewed**
- [Phys.org biological neural networks topic](https://phys.org/concepts/biological-neural-networks/) — **reviewed**
- [CEUR insect-inspired random feature network](https://ceur-ws.org/Vol-2986/paper10.pdf) — **research-reviewed**
- [MindStudio brain emulation article](https://www.mindstudio.ai/blog/what-is-brain-emulation-fruit-fly-eon-systems) — **reviewed**
- [Frontiers insect navigation / reinforcement computations](https://www.frontiersin.org/journals/computational-neuroscience/articles/10.3389/fncom.2024.1460006/full) — **research-reviewed**
- [Menzel 2012 bee cognition review](https://www.bcp.fu-berlin.de/biologie/arbeitsgruppen/neurobiologie/ag_menzel/publications/Res/Me-Review-nature-Reviews-Neurosc-2012.pdf) — **research-reviewed**
- [Peng & Chittka 2017 computational mushroom body](https://doi.org/10.1016/j.cub.2016.10.054) — **research-reviewed**
- [Stone et al. 2017 path integration](https://doi.org/10.1016/j.cub.2017.08.052) — **research-reviewed**

## Insect connectome research

- [Eichler et al. 2017 mushroom body — alternate copy](https://www.researchgate.net/publication/346928381_The_complete_connectome_of_a_learning_and_memory_center_in_an_insect_brain) — **research-reviewed**
- [Eichler et al. 2017 Nature DOI](https://doi.org/10.1038/nature23455) — **research-reviewed**

## Platform and protocol documentation

- [Venice models](https://docs.venice.ai/models/overview) — **reviewed**
- [Venice API spec](https://docs.venice.ai/api-reference/api-spec) — **reviewed**
- [Venice Decisions guide](https://docs.venice.ai/guides/features/decisions) — **reviewed**
- [Venice Decisions create](https://docs.venice.ai/api-reference/endpoint/decisions/create) — **reviewed**
- [Venice System One endpoint](https://docs.venice.ai/api-reference/endpoint/decisions/systemone) — **reviewed**
- [LM Studio OpenAI compatibility](https://lmstudio.ai/docs/developer/openai-compat) — **reviewed**
- [LM Studio REST](https://lmstudio.ai/docs/developer/rest) — **reviewed**
- [LM Studio headless](https://lmstudio.ai/docs/developer/core/headless) — **reviewed**
- [LM Studio server CLI](https://lmstudio.ai/docs/cli/serve/server-start) — **reviewed**
- [Model Context Protocol](https://modelcontextprotocol.io/) — **reviewed**
- [MCP Python SDK](https://py.sdk.modelcontextprotocol.io/) — **reviewed**
