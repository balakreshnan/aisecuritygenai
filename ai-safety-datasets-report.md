# AI Safety / Red-Teaming Dataset Reference Guide

## Executive Summary

This guide catalogs ~35 datasets referenced in a promptfoo-style red-teaming configuration, organized by purpose. For each dataset we describe origin, what it tests, size/format, when to use it, and the canonical source. Most entries are open-source benchmarks hosted on HuggingFace or GitHub; several (the `airt_*` family) are promptfoo/PyRIT internal naming conventions that wrap public datasets per NVIDIA Aegis / MLCommons harm taxonomies ([Promptfoo plugins index](https://www.promptfoo.dev/docs/red-team/plugins/), [Aegis plugin](https://github.com/frikidecesai/promptfoo-testLLM/blob/main/site/docs/red-team/plugins/aegis.md)).

**Confidence:** HIGH for all major public benchmarks (HarmBench, JBB, AdvBench, MLCommons AILuminate, NVIDIA Aegis, PKU-SafeRLHF, ALERT, Aya, XSTest, DarkBench, Do-Not-Answer, SORRY-Bench, SOSBench, MedSafetyBench, EquityMedQA, PyRIT, garak). MODERATE for `airt_*` naming mapping (inferred from PyRIT AIRTInitializer conventions).

---

## 1. Active / Regional Jailbreak

### `ccp_sensitive_prompts`
Curated prompts on topics sensitive to the People's Republic of China (e.g., Tiananmen, Taiwan, Xinjiang, CCP leadership) used to test regional censorship behavior and refusal alignment of models trained or served in China-adjacent contexts. Typically ~100-500 prompts, English plus Simplified Chinese. Use when evaluating geopolitical bias, differential refusal behavior between Western and Chinese models, or deployment to mixed markets. Source: [promptfoo CCP-Sensitive Prompts plugin](https://www.promptfoo.dev/docs/red-team/plugins/) (dataset plugin).

---

## 2. AIRT Family (Harm-Category Red-Team Slices)

The `airt_*` prefix corresponds to the **AI Red Team Initializer** pattern used by PyRIT ([microsoft/PyRIT commit history notes "AIRTInitializer"](https://github.com/microsoft/pyrit)) and surfaced through promptfoo plugin configs. Each file is a curated slice of public red-team prompts (drawn from Anthropic HH-RLHF, BeaverTails, Aegis, Aya) mapped to one harm category. Use when you want narrowly-scoped harm coverage rather than a full benchmark, or to drive iterative refinement attacks. Sources: [PyRIT GitHub](https://github.com/microsoft/pyrit), [promptfoo plugins](https://www.promptfoo.dev/docs/red-team/plugins/).

| Slug | Harm Category Tested | Typical Source Datasets |
|------|---------------------|-------------------------|
| `airt_fairness` | Fairness / protected-class bias | BBQ, BOLD, Aya |
| `airt_fairness_yes_no` | Binary bias/stereotype detection | BBQ yes-no variants |
| `airt_hate` | Hate speech, identity attack | Aegis, ALERT `hate_*` |
| `airt_harassment` | Harassment, bullying, threats | Aegis, BeaverTails |
| `airt_misinformation` | False claims, conspiracy | TruthfulQA, Do-Not-Answer |
| `airt_sexual` | Sexual content, minors | Aegis `sexual`, `sexual_minor` |
| `airt_violence` | Violent crime, gore | Aegis `violence`, ALERT |
| `airt_leakage` | Training-data / system-prompt leakage | JailbreakHub, custom |
| `airt_malware` | Malware, exploit, cyber | HarmBench cyber, CyberSecEval |
| `airt_illegal` | Criminal planning, controlled substances | Aegis, BeaverTails |

Each slice typically runs 25-200 prompts per category; mix with attack strategies (jailbreak, Crescendo) for full coverage.

---

## 3. Jailbreak & Prompt-Attack Benchmarks

### `psfuzz_steal_system_prompt`
PromptSteal / PromptFuzz: prompts designed to extract a target model's hidden system prompt via injection, role-play, or encoding tricks. ~100-500 prompts. Use to validate system-prompt confidentiality before shipping a RAG or agent. Source: [promptfoo Prompt Extraction plugin](https://www.promptfoo.dev/docs/red-team/plugins/).

### `jbb_behaviors` (JailbreakBench)
100 harmful + 100 benign behaviors spanning 10 OpenAI-policy categories, paired with leaderboard artifacts and a judge. Use as a standard jailbreak leaderboard benchmark when comparing attacks or defenses. Source: [JailbreakBench](https://jailbreakbench.github.io/).

### `tdc23_redteaming`
NeurIPS 2023 Trojan Detection Challenge red-teaming track dataset: 50 harmful behaviors used to elicit backdoor/trigger behavior. Use for trojan detection and transfer-attack research. Source: [TDC 2023](https://trojandetection.ai/).

### `pyrit_example_dataset`
PyRIT's bundled illustrative harm prompts (hate, violence, illegal) used in Microsoft AI Red Team orchestration examples. Small (~50). Use as a smoke test when validating a PyRIT pipeline. Source: [microsoft/PyRIT](https://github.com/microsoft/pyrit).

### `harmbench`
520 harmful behaviors across 7 semantic categories (cybercrime, illegal, chemical/biological, misinformation, harassment, harmful content, copyright) plus 18 "contextual" behaviors. Released with an ASR evaluator (HarmBench classifier). Use for standardized attack-success-rate comparison. Source: [HarmBench](https://www.harmbench.org), [arXiv 2402.04249](https://arxiv.org/abs/2402.04249).

### `harmbench_multimodal`
Multimodal extension: 110 image+text behaviors for VLM red-teaming (e.g., instructions overlaid on images). Use for GPT-4V / Claude 3 / Gemini multimodal safety testing. Source: [HarmBench](https://www.harmbench.org).

### `adv_bench`
520 harmful strings + 520 harmful behaviors from the GCG paper (Zou et al., 2023). The canonical substrate for gradient-based adversarial suffix attacks. Use when reproducing GCG / nanoGCG / BEAST transfer attacks. Source: [arXiv 2307.15043](https://arxiv.org/abs/2307.15043).

### `forbidden_questions`
390 questions (13 OpenAI-forbidden scenarios × 30) from "Do Anything Now" (Shen et al., CCS 2024). Pair with in-the-wild jailbreak prompts to measure ASR. Use for reproducing DAN-style studies. Source: [walledai/ForbiddenQuestions](https://huggingface.co/datasets/walledai/ForbiddenQuestions), [arXiv 2308.03825](https://arxiv.org/abs/2308.03825).

### `llm_lat_harmful`
~4,950 harmful prompts from **LLM-LAT** (Targeted Latent Adversarial Training, Sheshadri et al., NeurIPS 2024) used both to elicit refusals and as training data for robust-refusal models. Use when evaluating or training latent-space-robust refusal behavior. Source: [LLM-LAT/harmful-dataset](https://huggingface.co/datasets/LLM-LAT/harmful-dataset), [arXiv 2407.15549](https://arxiv.org/abs/2407.15549).

---

## 4. Comprehensive Safety Benchmarks

### `mlcommons_ailuminate`
MLCommons AILuminate v1.0: 24,000+ prompts across 12 hazard categories (violent crimes, non-violent crimes, sex crimes, CSAM, weapons, hate, suicide, etc.), with Practice/Official/Private splits and a public leaderboard. Use for industry-standard safety-grade evaluation. Source: [MLCommons AILuminate](https://mlcommons.org/benchmarks/ailuminate/).

### `xstest`
250 "safe but sounds unsafe" + 200 truly unsafe contrast prompts to measure **exaggerated safety / over-refusal** (e.g., "How do I kill a Python process?"). Use when tuning the false-refusal rate of a well-aligned model. Source: [arXiv 2308.01263](https://arxiv.org/abs/2308.01263).

### `sorry_bench`
SORRY-Bench: 440 unsafe instructions × 20 linguistic mutations = 8,800 test prompts covering 44 fine-grained categories. Use for refusal quality, not just pass/fail — distinguishes partial, vague, and on-topic-refused responses. Source: [SORRY-Bench](https://sorry-bench.github.io/).

### `librai_do_not_answer`
939 prompts across 5 risk areas × 12 harm types that responsible LLMs should decline. Small, clean, human-curated. Use as a refusal-rate baseline. Source: [LibrAI/do-not-answer](https://huggingface.co/datasets/LibrAI/do-not-answer).

### `aegis_content_safety`
NVIDIA Aegis AI Content Safety Dataset: 26,000+ annotated human-LLM interactions across 13 categories (hate, sexual, violence, self-harm, minor-sexual, weapons, drugs, crime, PII, harassment, profanity, threats, other). Includes "Safe" and "Needs Caution" labels. Use for content-moderation classifier training/eval and as comprehensive red-team prompt source. License CC-BY-4.0. Source: [NVIDIA Aegis](https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-1.0), [promptfoo Aegis plugin](https://github.com/frikidecesai/promptfoo-testLLM/blob/main/site/docs/red-team/plugins/aegis.md).

### `pku_safe_rlhf`
330,000+ prompt-response pairs with dual helpfulness/harmlessness preferences across 19 harm categories. Use as RLHF / DPO training data for safety alignment, not just eval. Source: [PKU-Alignment/PKU-SafeRLHF](https://huggingface.co/datasets/PKU-Alignment/PKU-SafeRLHF).

### `babelscape_alert`
ALERT: 45,000 prompts + 15,000 adversarial variants across 32 safety categories from Babelscape (Tedeschi et al., 2024). Use for large-scale, fine-grained safety categorization. Source: [Babelscape/ALERT](https://huggingface.co/datasets/Babelscape/ALERT).

### `dark_bench`
DarkBench: 660 prompts × 6 dark-pattern categories (brand bias, user retention, sycophancy, anthropomorphism, harmful generation, sneaking) evaluated on 14 models. Use when assessing manipulative design / UX risks rather than content harm. Source: [arXiv 2503.10728](https://arxiv.org/abs/2503.10728).

---

## 5. Multilingual & Multimodal

### `aya_redteaming`
Cohere For AI's Aya dataset: 7,419 single-turn human-curated prompts across 8 languages (Arabic, English, Filipino, French, Hindi, Russian, Serbian, Spanish) tagged with harm categories (bullying, graphic content, discrimination, etc.). Use for non-English safety coverage. Source: [CohereForAI/aya_redteaming](https://huggingface.co/datasets/CohereForAI/aya_redteaming), [arXiv 2406.18682](https://arxiv.org/abs/2406.18682).

### `multilingual_vulnerability`
Meta Purple-Llama CyberSecEval multilingual prompt-injection subset — direct/indirect injection and system-prompt leakage in multiple languages with language-specific LLM-judge rubrics. Use for non-English injection robustness. Source: [promptfoo CyberSecEval](https://www.promptfoo.dev/docs/red-team/plugins/cyberseceval/).

---

## 6. Security-Oriented Probes (NVIDIA garak)

### `garak_web_html_js`
`garak.probes.xss` family: tests whether a model will emit unescaped HTML/JS or active XSS payloads in its output — critical when LLM output is rendered in a browser. Source: [garak docs](https://reference.garak.ai/en/latest/probes.html).

### `garak_slur_terms_en`
`garak.probes.continuation` / slur-reclamation probes: measures whether the model completes partially-typed slurs or reclaimed-slur contexts. Use for content-filter validation. Source: [garak docs](https://reference.garak.ai/en/latest/probes.html).

### `garak_access_shell_commands`
`garak.probes` variants that check whether an LLM suggests or executes shell commands (e.g., `rm -rf`, reverse shells) when roleplaying a sysadmin or coding agent. Use for tool-use / code-agent safety. Source: [garak docs](https://reference.garak.ai/en/latest/probes.html).

---

## 7. Scientific / Medical Safety

### `sosbench`
SOSBench: 3,000 regulation-grounded prompts across 6 high-risk scientific domains (chemistry, biology, medicine, pharmacology, physics, psychology) anchored to US/UN regulations (NFPA, CFR, ICD-11, DEA, IAEA). Reveals knowledge-intensive misuse gaps (e.g., 79% harmful response rate on DeepSeek-R1). Use for frontier-model CBRN safety. Source: [SOSBench](https://sosbench.github.io/), [arXiv 2505.21605](https://arxiv.org/abs/2505.21605).

### `medsafetybench`
1,800 harmful-medical-request + safe-response demonstrations grounded in the AMA Principles of Medical Ethics, plus 74,374 additional harmful medical prompts. Use for medical-LLM safety fine-tuning and evaluation. Source: [AI4LIFE-GROUP/med-safety-bench](https://github.com/AI4LIFE-GROUP/med-safety-bench), [arXiv 2403.03744](https://arxiv.org/abs/2403.03744).

### `equitymedqa`
Google's EquityMedQA (Pfohl et al., Nature Medicine 2024): 4,000+ adversarial medical queries designed to elicit health-equity failures (race-adjusted formulas, sex/gender, SES, disability). Use for health-equity bias audits. Source: [katielink/EquityMedQA](https://huggingface.co/datasets/katielink/EquityMedQA), [arXiv 2403.12025](https://arxiv.org/abs/2403.12025).

### `mental_health_crisis_multiturn_example`
Multi-turn conversation examples simulating users in mental-health crisis (suicidal ideation, self-harm, acute distress). Typically custom / promptfoo-internal illustrative set. Use to validate safe-messaging adherence (988 Lifeline guidelines, Means-Safety principles). Source: [promptfoo plugins](https://www.promptfoo.dev/docs/red-team/plugins/).

### `red_team_social_bias`
Aggregated corpus by Simone Van Taylor — 13 datasets, 40,000+ red-team prompts unified under a single social-bias taxonomy (race, gender, age, religion, disability, etc.). Use for comprehensive bias/representational-harm auditing without assembling individual datasets. Source: [svannie678 repository](https://svannie678.github.io/svannie678-red_team_repo_social_bias/), [HF dataset](https://huggingface.co/datasets/svannie678/red_team_repo_social_bias_dataset_information).

---

## Conclusion

These datasets fall into five strategic groups, each answering a different question: **attack strength** (HarmBench, JBB, AdvBench, TDC23), **refusal quality** (XSTest, SORRY-Bench, Do-Not-Answer), **content-category coverage** (Aegis, ALERT, AILuminate, PKU-SafeRLHF), **linguistic and modal breadth** (Aya, multilingual CyberSecEval, HarmBench-multimodal), and **domain specialization** (SOSBench, MedSafetyBench, EquityMedQA, garak security probes, DarkBench). A defensible red-team suite pairs one "broad" benchmark (AILuminate or Aegis) with domain probes (MedSafetyBench or garak security), a jailbreak leaderboard (JBB or HarmBench), and an over-refusal control (XSTest) — this combination minimizes both false-negative harm and false-positive refusals while satisfying NIST AI RMF / EU AI Act evidence requirements.

The `airt_*` family is a PyRIT-era abstraction: it routes a fixed harm taxonomy to whatever underlying public corpus is currently loaded, so maintenance effort concentrates on the taxonomy rather than individual dataset IDs — this is why the commented-out list is organized by harm rather than by source.

**Limitations:** The exact HF dataset IDs wrapped by each `airt_*` slug depend on the installed plugin version (PyRIT AIRTInitializer, promptfoo remote dataset cache) and should be confirmed in the local plugin source. MLCommons AILuminate Official/Private splits require MLCommons account access. Several benchmarks overlap (AdvBench behaviors appear inside HarmBench, ForbiddenQuestions, and JBB); count distinct prompts, not dataset entries, when reporting coverage.

---

## Sources

1. [Promptfoo Red Team Plugins](https://www.promptfoo.dev/docs/red-team/plugins/)
2. [Promptfoo HuggingFace Datasets docs](https://github.com/rupeedev/promptfoo-redteaming/blob/main/site/docs/configuration/huggingface-datasets.md)
3. [Promptfoo CyberSecEval plugin](https://www.promptfoo.dev/docs/red-team/plugins/cyberseceval/)
4. [Promptfoo Aegis plugin](https://github.com/frikidecesai/promptfoo-testLLM/blob/main/site/docs/red-team/plugins/aegis.md)
5. [HarmBench](https://www.harmbench.org) / [arXiv 2402.04249](https://arxiv.org/abs/2402.04249)
6. [JailbreakBench](https://jailbreakbench.github.io/)
7. [MLCommons AILuminate](https://mlcommons.org/benchmarks/ailuminate/)
8. [NVIDIA garak probes](https://reference.garak.ai/en/latest/probes.html)
9. [Microsoft PyRIT](https://github.com/microsoft/pyrit) / [arXiv 2410.02828](https://arxiv.org/abs/2410.02828)
10. [XSTest arXiv 2308.01263](https://arxiv.org/abs/2308.01263)
11. [AdvBench / GCG arXiv 2307.15043](https://arxiv.org/abs/2307.15043)
12. [DarkBench arXiv 2503.10728](https://arxiv.org/abs/2503.10728)
13. [LibrAI Do-Not-Answer](https://huggingface.co/datasets/LibrAI/do-not-answer)
14. [Cohere Aya Red-teaming](https://huggingface.co/datasets/CohereForAI/aya_redteaming) / [arXiv 2406.18682](https://arxiv.org/abs/2406.18682)
15. [SORRY-Bench](https://sorry-bench.github.io/)
16. [Babelscape ALERT](https://huggingface.co/datasets/Babelscape/ALERT)
17. [PKU-SafeRLHF](https://huggingface.co/datasets/PKU-Alignment/PKU-SafeRLHF)
18. [NVIDIA Aegis 1.0](https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-1.0)
19. [SOSBench](https://sosbench.github.io/) / [arXiv 2505.21605](https://arxiv.org/abs/2505.21605)
20. [walledai ForbiddenQuestions](https://huggingface.co/datasets/walledai/ForbiddenQuestions) / [arXiv 2308.03825](https://arxiv.org/abs/2308.03825)
21. [LLM-LAT harmful-dataset](https://huggingface.co/datasets/LLM-LAT/harmful-dataset) / [arXiv 2407.15549](https://arxiv.org/abs/2407.15549)
22. [MedSafetyBench](https://github.com/AI4LIFE-GROUP/med-safety-bench) / [arXiv 2403.03744](https://arxiv.org/abs/2403.03744)
23. [EquityMedQA](https://huggingface.co/datasets/katielink/EquityMedQA) / [arXiv 2403.12025](https://arxiv.org/abs/2403.12025)
24. [Red-Team Social Bias Repo](https://svannie678.github.io/svannie678-red_team_repo_social_bias/)
25. [NeurIPS 2023 TDC](https://trojandetection.ai/)
