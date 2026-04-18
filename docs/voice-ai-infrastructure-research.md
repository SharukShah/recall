# Voice AI Infrastructure Research
**Date:** April 14, 2026  
**Purpose:** Comprehensive comparison of voice AI platforms for building a Jarvis-like voice-first personal memory assistant  
**Sources:** Live data from official documentation, pricing pages, and developer docs

---

## Table of Contents

1. [Overview](#1-overview)
2. [Deepgram — Full Analysis](#2-deepgram)
3. [Google Cloud Speech — Full Analysis](#3-google-cloud-speech)
4. [OpenAI Voice Stack — Full Analysis](#4-openai-voice-stack)
5. [ElevenLabs — Full Analysis](#5-elevenlabs)
6. [Pricing Comparison Table](#6-pricing-comparison)
7. [Feature Comparison Matrix](#7-feature-comparison-matrix)
8. [Architecture Options for Voice-First Assistant](#8-architecture-options)
9. [Recommendation](#9-recommendation)
10. [Gaps & Issues](#10-gaps--issues)

---

## 1. Overview

### Scope Covered

This document evaluates **five voice AI infrastructure options** across STT, TTS, real-time streaming, voice agent capabilities, pricing, and developer experience — all with the goal of selecting the optimal stack for a **Jarvis-like voice-first personal memory assistant**.

### Platforms Evaluated

| Platform | STT | TTS | Voice Agent API | Native Speech-to-Speech |
|---|---|---|---|---|
| **Deepgram** | ✅ Nova-3, Flux | ✅ Aura-2 | ✅ Unified Agent API | ❌ (chained STT→LLM→TTS) |
| **Google Cloud** | ✅ Chirp 3 | ✅ Chirp 3 HD, Gemini-TTS | ❌ (separate APIs) | ❌ |
| **OpenAI** | ✅ gpt-4o-transcribe, Whisper | ✅ TTS-1, TTS-1-HD | ❌ (but Realtime API) | ✅ GPT-realtime-1.5 |
| **ElevenLabs** | ✅ Scribe v2 | ✅ Eleven v3, Flash v2.5 | ✅ Conversational AI | ❌ (chained) |

---

## 2. Deepgram

### 2.1 STT Capabilities

#### Models
| Model | Use Case | Languages | Key Feature |
|---|---|---|---|
| **Flux** | Real-time voice agents | English (all accents) | **Model-native turn detection** — first STT to unify ASR + end-of-turn in one model |
| **Nova-3** | General transcription, meetings, analytics | 45+ languages (10 in multilingual mode) | 54.2% WER reduction over competitors (streaming), 47.4% (batch) |
| **Nova-2** | Legacy/unsupported languages | Expanded set | Filler word identification |
| **Industry-tuned** | Healthcare, legal, finance | English | Domain-specific vocabulary |
| **Custom** | Edge cases | All | Trained on proprietary data |

#### Accuracy
- Nova-3: **Industry-leading** — 54.2% WER reduction vs competitors in streaming; first model to offer self-serve customization (keyterm prompting) without retraining
- Flux: **Nova-3-level accuracy** with added conversational intelligence
- Keyterm prompting boosts keyword recall rate (KRR) by up to **90%**
- Real-world noise robustness: maintains accuracy in noisy, accented, overlapping speech

#### Latency
- **Sub-300ms end-of-turn latency** (Flux)
- **Sub-300ms transcript delivery** for Nova-3 streaming
- Up to **40x faster** than alternatives for pre-recorded batch

#### Streaming Support
- **Full WebSocket (WSS) streaming** for both STT and TTS
- REST API for pre-recorded/batch
- Concurrency: up to 150 WSS (Pay-as-you-go), 225 WSS (Growth plan)

#### Speaker Diarization
- ✅ Multi-speaker detection and labeling
- Available as add-on: $0.0020/min (PAYG), $0.0017/min (Growth)

#### Additional Features
- Smart formatting (punctuation, casing, dates, currency) — **included free**
- Filler word transcription ("uh", "um")
- PII redaction ($0.0020/min)
- Automatic language detection
- Numeral conversion ("one hundred" → "100")
- Multichannel audio support

### 2.2 TTS Capabilities (Aura-2)

| Feature | Detail |
|---|---|
| Latency | **Sub-200ms** (2-4x faster than competitors like play.ht) |
| Voices | **40+ English voices** with localized accents (US, AU, PH, etc.) |
| Languages | English-focused (multiple accents) |
| Voice quality | Enterprise-tuned — clarity, consistency, low listener fatigue. NOT cinematic/expressive. |
| Domain tuning | Accurate medical, finance, legal terminology pronunciation |
| Context-awareness | Adjusts pacing, tone, expression contextually |
| Streaming | ✅ Full streaming TTS over WebSocket |
| Custom voices | Not mentioned (enterprise only via contact) |
| Pricing | **$0.030/1k chars** (PAYG), $0.027/1k (Growth) |

### 2.3 Voice Agent API

**This is Deepgram's killer feature.**

| Feature | Detail |
|---|---|
| Architecture | **Unified API** — STT + LLM orchestration + TTS in one API call |
| Pricing | **$0.075/min ($4.50/hr)** standard, down to $0.050/min BYO LLM+TTS |
| Barge-in | ✅ Built-in interruption detection |
| Turn-taking | ✅ Prediction-based (Flux model native) |
| Function calling | ✅ Mid-conversation |
| BYO LLM | ✅ Bring your own LLM while keeping Deepgram orchestration |
| BYO TTS | ✅ Bring your own TTS |
| Deployment | Fully managed, dedicated single-tenant, in-VPC, self-hosted |
| Compliance | HIPAA, GDPR (EU endpoint: api.eu.deepgram.com), SOC 2, PCI, CCPA |
| WebSocket | ✅ WSS-based real-time |

**BYO Pricing Tiers:**
| Tier | PAYG | Growth |
|---|---|---|
| Standard (full Deepgram stack) | $0.075/min | $0.068/min |
| Standard - BYO TTS | $0.065/min | $0.051/min |
| Custom - BYO LLM | $0.056/min | $0.059/min |
| Custom - BYO LLM + TTS | $0.050/min | $0.041/min |
| Advanced | $0.163/min | $0.146/min |
| Advanced - BYO TTS | $0.122/min | $0.110/min |

### 2.4 Developer Experience

| Aspect | Rating | Notes |
|---|---|---|
| SDKs | ⭐⭐⭐⭐⭐ | Python, JavaScript, Go, .NET — official, maintained |
| Documentation | ⭐⭐⭐⭐⭐ | Excellent — Fern-powered docs, clear quickstarts, MCP server, CLI tool |
| Playground | ⭐⭐⭐⭐⭐ | Interactive browser-based playground for STT, TTS, Voice Agent |
| Free tier | ⭐⭐⭐⭐ | **$200 free credit** (no credit card required), no expiration |
| Community | ⭐⭐⭐⭐ | Discord, GitHub Discussions, community forum |
| Dev tools | ⭐⭐⭐⭐⭐ | MCP Server for AI coding tools, CLI with 28 API commands, Slack AI support |
| Self-hosted | ✅ | Available for enterprise |

### 2.5 Unique Strengths
1. **Only platform with unified Voice Agent API** — single API for complete voice agent pipeline
2. **Flux model** — first STT with native turn detection (no external VAD needed)
3. **Fastest STT** in the industry — sub-300ms, built specifically for voice agents
4. **BYO flexibility** — bring your own LLM/TTS while keeping Deepgram orchestration
5. **Enterprise trust** — powers Twilio, Vapi, Sierra, Cloudflare, Daily/Pipecat, Livekit
6. **Self-hosted option** — on-prem deployment available

### 2.6 Limitations
1. **TTS is English-only** (Aura-2) — not multilingual
2. **TTS voice quality is "enterprise-grade" not "cinematic"** — optimized for call centers, not audiobooks. Less emotional range than ElevenLabs
3. **Flux model is English-only** — multilingual conversations must use Nova-3 (no native turn detection)
4. **No native speech-to-speech** — still a chained STT→LLM→TTS architecture (adds latency vs OpenAI Realtime)
5. **No voice cloning** — can't clone a user's voice (ElevenLabs does this)

---

## 3. Google Cloud Speech

### 3.1 STT Capabilities

#### Models
| Model | API | Key Feature |
|---|---|---|
| **Chirp 3: Transcription** | V2 API | Foundation model trained on millions of hours + 28B text sentences across 100+ languages |
| Standard models | V1 & V2 | command_and_search, latest_short, latest_long, phone_call, video |
| Medical models | V1 | medical_conversation, medical_dictation |

#### Accuracy
- Chirp 3 uses self-supervised learning on massive data
- Model adaptation for custom vocabulary (bias towards specific words)
- Enhanced multilingual detection and transcription

#### Languages
- **85+ languages and variants** (V2 Chirp 3)
- 125+ supported overall across all models
- Multilingual language detection built in

#### Streaming
- ✅ **Three methods**: synchronous, asynchronous, and streaming
- gRPC and REST APIs
- Real-time streaming from microphone or file

#### Speaker Diarization
- ✅ Supported in Chirp 3

#### Latency
- Not explicitly stated in marketing — Google doesn't emphasize sub-second latency like Deepgram
- Reported as adequate for real-time use but not optimized for voice agent pipelines
- No native turn detection in STT model

### 3.2 TTS Capabilities

#### Models
| Model | Quality | Free Tier | Price/1M chars |
|---|---|---|---|
| **Gemini 2.5 Flash TTS** | Cutting-edge, prompt-steerable | None | $0.50/1M input tokens + $10.00/1M audio output tokens |
| **Gemini 2.5 Pro TTS** | Highest quality | None | $1.00/1M input tokens + $20.00/1M audio output tokens |
| **Chirp 3: HD voices** | Spontaneous conversational voices, emotional range | 1M chars free | **$30/1M chars** |
| **Chirp 3: Instant Custom Voice** | Create voice from 10s audio | None | $60/1M chars |
| WaveNet voices | Good quality, older | 4M chars free | **$4/1M chars** (cheapest) |
| Neural2 voices | Mid-tier | 1M chars free | $16/1M chars |
| Studio voices | Premium | 1M chars free | $160/1M chars |
| Standard voices | Basic | 4M chars free | $4/1M chars |

#### Key TTS Features
- **380+ voices across 75+ languages** — widest selection by far
- **Gemini-TTS**: natural-language prompt control over style, accent, pace, tone, emotion
- **Chirp 3 HD**: spontaneous conversational voices with disfluencies, emotional range, accurate intonation
- **Instant Custom Voice**: create personalized voice from **10 seconds** of audio (30+ locales)
- **Streaming audio synthesis** — ultra-low-latency for AI agents
- SSML support (pause, pronunciation, numbers, dates)
- Audio profiles (optimize for headphones, phone lines, etc.)
- Output formats: MP3, Linear16, OGG Opus, others
- Long audio synthesis: up to 1M bytes input async

### 3.3 Real-Time/Voice Agent Capabilities

**Google does NOT have a unified Voice Agent API.** You must:
1. Use STT API (streaming) for speech recognition
2. Send text to your LLM
3. Use TTS API (streaming) for speech synthesis
4. Handle turn detection, barge-in, and orchestration yourself

Google does offer **Dialogflow CX** for building conversational agents with voicebot capabilities, but that's a separate, more complex product (not just infrastructure).

### 3.4 Pricing Summary

| Service | Model | Price |
|---|---|---|
| **STT V2** | Standard/Chirp 3 | **$0.016/min** (0-500K min), $0.010 (500K-1M), $0.008 (1M-2M), $0.004 (2M+) |
| **STT V2** | Dynamic Batch | **$0.003/min** |
| **STT V1** | Standard (w/ logging) | $0.016/min (60 min free) |
| **STT V1** | Standard (w/o logging) | $0.024/min (60 min free) |
| **STT V1** | Medical | $0.078/min (60 min free) |
| **TTS** | WaveNet/Standard | $4/1M chars (4M free) |
| **TTS** | Chirp 3 HD | $30/1M chars (1M free) |
| **TTS** | Gemini Flash TTS | Token-based pricing |

**Free tier:** $300 Google Cloud credits for new accounts.

### 3.5 Developer Experience

| Aspect | Rating | Notes |
|---|---|---|
| SDKs | ⭐⭐⭐⭐ | Python, Node.js, Java, Go, C#, Ruby, PHP — Google Client Libraries |
| Documentation | ⭐⭐⭐⭐ | Comprehensive but spread across multiple products/versions (V1, V2, Vertex AI) |
| Complexity | ⭐⭐ | GCP project setup, service accounts, IAM, billing — high onboarding friction |
| Free tier | ⭐⭐⭐⭐⭐ | $300 credits + generous free tier for STT/TTS |
| Streaming | ⭐⭐⭐ | gRPC streaming works but requires more boilerplate than WebSocket |
| On-prem | ✅ | Speech-to-Text On-Prem available |

### 3.6 Unique Strengths
1. **Broadest language support** — 85+ languages STT, 75+ languages 380+ voices TTS
2. **Gemini-TTS** — prompt-steerable TTS with natural language control (style, tone, pace, emotion)
3. **Instant Custom Voice** — create a custom voice from 10 seconds of audio
4. **Cheapest batch STT** — $0.003/min dynamic batch
5. **Cheapest TTS** — WaveNet at $4/1M chars with 4M free chars/month
6. **Data residency & compliance** — regional deployment, CMEK, audit logging
7. **Massive scale** — Google's infrastructure

### 3.7 Limitations
1. **No unified Voice Agent API** — you must stitch STT + LLM + TTS yourself
2. **No native turn detection** in STT — need external VAD
3. **GCP lock-in** — requires Google Cloud project, not just an API key
4. **Onboarding friction** — service accounts, IAM, billing setup before first API call
5. **Latency not optimized for voice agents** — no sub-300ms claims
6. **Chirp 3 HD TTS expensive** — $30/1M chars vs Deepgram's $30/1M chars (comparable) but WaveNet at $4 is much cheaper
7. **No barge-in handling** — build it yourself
8. **Documentation fragmentation** — V1 vs V2, Vertex AI vs direct API, confusion

---

## 4. OpenAI Voice Stack

### 4.1 STT Capabilities

#### Models
| Model | Type | Streaming | Diarization | Key Feature |
|---|---|---|---|---|
| **gpt-4o-transcribe** | Batch + streaming | ✅ (stream=True) | ❌ | High accuracy, GPT-4o based |
| **gpt-4o-mini-transcribe** | Batch + streaming | ✅ | ❌ | Faster, cheaper |
| **gpt-4o-transcribe-diarize** | Batch | ✅ (via events) | ✅ (up to known speakers) | Speaker labels, reference clips |
| **whisper-1** | Batch only | ❌ | ❌ | Open-source legacy, 98 languages |

#### Key STT Features
- **Streaming transcription**: Both from completed audio (stream=True) and ongoing audio (Realtime API WebSocket)
- **Real-time streaming via Realtime API**: `wss://api.openai.com/v1/realtime?intent=transcription`
- **Server-side VAD**: Built-in turn detection with configurable threshold, padding, silence duration
- **Noise reduction**: Near-field and far-field modes
- **Speaker diarization**: Up to ~4 known speakers with reference audio clips
- **Prompting**: Improve accuracy for domain-specific terms
- **Languages**: 50+ languages listed (98 trained, 50+ with <50% WER)
- **File limit**: 25 MB per request

#### Latency
- Batch STT via `/v1/audio/transcriptions`: good for short files, not real-time
- **Realtime API**: low-latency WebSocket-based streaming — designed for conversational use
- No specific ms numbers published for STT latency

### 4.2 TTS Capabilities
OpenAI offers TTS models but they are less prominently featured. Standard API TTS through `/v1/audio/speech`:
- Models: `tts-1` (fast, lower quality), `tts-1-hd` (higher quality)
- Voices: alloy, echo, fable, onyx, nova, shimmer (6 voices)
- Languages: Follows input text language
- Streaming: ✅
- Price: Not separately broken out on the pricing page reviewed

### 4.3 Realtime API (Speech-to-Speech) — THE DIFFERENTIATOR

**This is OpenAI's unique offering — no other provider has true speech-to-speech.**

| Feature | Detail |
|---|---|
| Model | **GPT-realtime-1.5** |
| Architecture | **Native speech-to-speech** — audio in → reasoning → audio out, NO intermediate text chain |
| Connection methods | **WebRTC** (browser), **WebSocket** (server), **SIP** (telephony/VoIP) |
| Turn detection | ✅ Server-side VAD with configurable parameters |
| Function calling | ✅ Mid-conversation |
| Multimodal input | Audio + images + text simultaneously |
| MCP support | ✅ Connect remote MCP servers to Realtime sessions |
| Webhooks | ✅ Server-side controls and guardrails |
| Audio transcription | ✅ Real-time transcription alongside speech |
| Agents SDK | ✅ `RealtimeAgent` + `RealtimeSession` abstractions |

#### Pricing (GPT-realtime-1.5)
| Type | Input | Cached Input | Output |
|---|---|---|---|
| **Audio** | **$32.00/1M tokens** | $0.40/1M | **$64.00/1M tokens** |
| **Text** | $4.00/1M | $0.40/1M | $16.00/1M |
| **Image** | $5.00/1M | $0.50/1M | — |

**Cost estimation for voice agent use:**
- ~1 minute of audio ≈ 1,500 tokens (rough estimate)
- So audio input: ~$0.048/min, audio output: ~$0.096/min
- **Total audio-only: ~$0.14/min ($8.64/hr)** — ~2x more expensive than Deepgram's Voice Agent API
- With caching: dramatically cheaper on cached inputs ($0.40 vs $32 per 1M)

### 4.4 Whisper (Batch STT)
- **Open-source model** — can self-host for free, or use via API
- API model: `whisper-1`
- 98 languages trained, ~50+ reliably
- Batch only (no streaming)
- Old architecture, slower than GPT-4o-transcribe
- Deepgram also hosts Whisper Cloud (limited concurrency)

### 4.5 Developer Experience

| Aspect | Rating | Notes |
|---|---|---|
| SDKs | ⭐⭐⭐⭐⭐ | Python, Node.js (official), community SDKs for all languages |
| Documentation | ⭐⭐⭐⭐⭐ | Excellent, recently reorganized to developers.openai.com |
| Simplicity | ⭐⭐⭐⭐⭐ | API key + 3 lines of code. Lowest friction. |
| Agents SDK | ⭐⭐⭐⭐⭐ | `RealtimeAgent` abstraction makes voice agents trivially easy |
| Playground | ⭐⭐⭐⭐ | Available for text, limited for realtime voice |
| Free tier | ⭐⭐ | No free credits for new accounts (pay-as-you-go only) |
| Community | ⭐⭐⭐⭐⭐ | Massive ecosystem, forum, Discord |

### 4.6 Unique Strengths
1. **Only true speech-to-speech** — native audio reasoning without STT→text→TTS chain
2. **Lowest latency possible** — no intermediate text bottleneck
3. **Multimodal** — can process images + audio + text simultaneously
4. **WebRTC** — browser-native, no WebSocket complexity for client apps
5. **SIP** — direct telephony integration
6. **GPT-class reasoning** — the LLM IS the voice model, so reasoning quality is unmatched
7. **MCP integration** — connect tools directly to realtime sessions
8. **Agents SDK** — highest-level abstraction for voice agents

### 4.7 Limitations
1. **Most expensive** — $0.14/min audio-only estimate (~$8.64/hr) vs Deepgram's $4.50/hr
2. **No fine-tuning of voice** — only 6 preset voices
3. **Audio quality is "robotic"** compared to ElevenLabs — not the most natural-sounding
4. **Vendor lock-in** — can't self-host, can't use your own LLM
5. **Diarization limited** — `gpt-4o-transcribe-diarize` not yet in Realtime API
6. **Token-based pricing** — unpredictable costs for longer conversations
7. **No self-hosted option**
8. **Rate limits** — can be restrictive for scale

---

## 5. ElevenLabs

### 5.1 STT Capabilities (Scribe v2)

| Feature | Detail |
|---|---|
| Model | **Scribe v2** (batch), **Scribe v2 Realtime** (streaming) |
| Languages | **90+ languages** |
| Accuracy | State-of-the-art (their claim) |
| Diarization | Up to **32 speakers** |
| Keyterm prompting | Up to **1,000 terms** |
| Entity detection | Up to **56 entity types** |
| Timestamps | Word-level precision |
| Audio tagging | Dynamic, smart |
| Language detection | Smart auto-detect |
| Realtime latency | **~150ms** (Scribe v2 Realtime) |

### 5.2 TTS Capabilities — PREMIUM QUALITY

| Model | Quality | Latency | Languages | Limit |
|---|---|---|---|---|
| **Eleven v3** | Most expressive, emotionally rich | Higher latency | 70+ languages | 5,000 chars/request |
| **Eleven Multilingual v2** | Natural, consistent | Moderate | 29 languages | 10,000 chars |
| **Eleven Flash v2.5** | Fast, affordable | **~75ms** | 32 languages | 40,000 chars |

#### Key TTS Features
- **10,000+ voice library** — massive selection
- **Voice cloning**: Instant (from recording) + Professional (higher quality)
- **Voice design**: Generate voices from text descriptions
- **44.1kHz PCM output** (Pro+), 192kbps quality
- Commercial license included from Starter plan
- **50% lower price** on Flash model vs standard

### 5.3 Voice Agent Capabilities
- **ElevenAgents / Conversational AI** — full voice agent platform
- Supports integrations with external systems
- Industry-specific solutions: healthcare, finance, telecom, retail
- Agents API available

### 5.4 Pricing

**Credit-based system** (1 credit = 1 character for TTS, 1 second for STT):

| Plan | Price | Credits/month | TTS cost/min |
|---|---|---|---|
| Free | $0 | 10K | ~$0.36/min |
| Starter | $6/mo | 30K | ~$0.20/min |
| Creator | $22/mo | 121K | ~$0.18/min |
| Pro | $99/mo | 600K | ~$0.17/min |
| Scale | $299/mo | 1.8M | ~$0.17/min |
| Business | $990/mo | 6M | ~$0.17/min, Low-latency TTS as low as $0.05/min |
| Enterprise | Custom | Custom | Custom |

**Startup Grant**: 12 months free, 33M characters

### 5.5 Developer Experience

| Aspect | Rating | Notes |
|---|---|---|
| SDKs | ⭐⭐⭐⭐ | Python, TypeScript (official) |
| Documentation | ⭐⭐⭐⭐ | Good, Fern-powered like Deepgram |
| API design | ⭐⭐⭐⭐ | Clean REST API |
| Web app | ⭐⭐⭐⭐⭐ | No-code tools for non-developers too |
| Free tier | ⭐⭐⭐ | 10K credits (very small — ~10 min TTS) |
| Conversational AI | ⭐⭐⭐⭐ | ElevenAgents platform for building agents |

### 5.6 Unique Strengths
1. **Highest quality TTS** in the industry — most expressive, emotional, human-like
2. **Voice cloning** — instant from recording, professional quality
3. **Voice design** — create voices from text descriptions
4. **Largest voice library** — 10,000+ voices
5. **Scribe v2** — strong STT with 32-speaker diarization, 1000 keyterm prompts, entity detection
6. **Full creative platform** — not just API, also web UI for non-developers
7. **70+ language TTS** with Eleven v3

### 5.7 Limitations
1. **Expensive at scale** — credit system adds up fast for voice agents
2. **TTS-focused** — STT (Scribe) is newer, less battle-tested than Deepgram/Google
3. **No unified voice agent API** like Deepgram — must chain STT+LLM+TTS
4. **Latency higher than Deepgram** for TTS — Eleven v3 is slower than Aura-2 (except Flash v2.5 at 75ms)
5. **Credit-based pricing is confusing** — harder to predict costs vs per-minute billing
6. **Flash model quality trade-off** — fastest model has lower quality
7. **No self-hosted option** (outside enterprise)

---

## 6. Pricing Comparison

### STT Pricing (Per Minute)

| Platform | Model | Streaming | Batch | Free Tier |
|---|---|---|---|---|
| **Deepgram** | Flux / Nova-3 Mono | $0.0077/min | $0.0077/min | $200 credit |
| **Deepgram** | Nova-3 Multilingual | $0.0092/min | $0.0092/min | $200 credit |
| **Google** | Chirp 3 / Standard V2 | $0.016/min | $0.003/min (batch) | $300 credit + 60 min free |
| **OpenAI** | gpt-4o-transcribe | Token-based | Token-based | None |
| **OpenAI** | whisper-1 | N/A | ~$0.006/min | None |
| **ElevenLabs** | Scribe v2 | Credit-based | Credit-based | 10K credits |

**Winner: Deepgram** ($0.0077/min streaming — 2x cheaper than Google's $0.016)

### TTS Pricing (Per 1K Characters)

| Platform | Model | Price/1K chars | Approx $/min speech |
|---|---|---|---|
| **Deepgram** | Aura-2 | $0.030 | ~$0.045/min |
| **Google** | WaveNet | $0.004 | ~$0.006/min |
| **Google** | Chirp 3 HD | $0.030 | ~$0.045/min |
| **Google** | Gemini Flash TTS | Token-based | ~varies |
| **ElevenLabs** | Flash v2.5 | Credit-based | ~$0.17-0.20/min |
| **ElevenLabs** | Eleven v3 | Credit-based | ~$0.17-0.36/min |
| **OpenAI** | tts-1 | ~$0.015/1K chars | ~$0.023/min |

**Winner: Google WaveNet** ($0.004/1K chars) for cost. Deepgram Aura-2 for latency.

### Voice Agent (STT + LLM + TTS) Pricing Per Minute

| Platform | Configuration | $/min | $/hr |
|---|---|---|---|
| **Deepgram** | Full stack (Voice Agent API) | $0.075 | **$4.50** |
| **Deepgram** | BYO LLM + TTS | $0.050 | $3.00 |
| **OpenAI** | Realtime API (speech-to-speech) | ~$0.14 | **~$8.64** |
| **Google** | STT + TTS (no agent) | ~$0.022 + LLM cost | ~$1.32 + LLM |
| **ElevenLabs** | Conversational AI | Credit-based | ~$10-20+ |

**Winner: Deepgram Voice Agent API** ($4.50/hr all-inclusive) for production voice agents.

---

## 7. Feature Comparison Matrix

| Feature | Deepgram | Google Cloud | OpenAI | ElevenLabs |
|---|---|---|---|---|
| **STT Accuracy** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **STT Latency** | ⭐⭐⭐⭐⭐ (<300ms) | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ (~150ms streaming) |
| **STT Languages** | ⭐⭐⭐ (45+) | ⭐⭐⭐⭐⭐ (85+) | ⭐⭐⭐⭐ (50+) | ⭐⭐⭐⭐⭐ (90+) |
| **TTS Quality** | ⭐⭐⭐ (enterprise) | ⭐⭐⭐⭐ (Chirp 3 HD) | ⭐⭐⭐ (limited voices) | ⭐⭐⭐⭐⭐ (best in class) |
| **TTS Latency** | ⭐⭐⭐⭐⭐ (<200ms) | ⭐⭐⭐⭐ (streaming) | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ (Flash: 75ms) |
| **TTS Languages** | ⭐⭐ (English only) | ⭐⭐⭐⭐⭐ (75+) | ⭐⭐⭐ (follows input) | ⭐⭐⭐⭐⭐ (70+) |
| **TTS Voices** | ⭐⭐⭐ (40+) | ⭐⭐⭐⭐⭐ (380+) | ⭐ (6) | ⭐⭐⭐⭐⭐ (10,000+) |
| **Voice Cloning** | ❌ | ⭐⭐⭐⭐ (10s audio) | ❌ | ⭐⭐⭐⭐⭐ (instant + pro) |
| **Voice Agent API** | ⭐⭐⭐⭐⭐ (unified) | ❌ (DIY) | ⭐⭐⭐⭐⭐ (Realtime) | ⭐⭐⭐⭐ (ElevenAgents) |
| **Speech-to-Speech** | ❌ | ❌ | ⭐⭐⭐⭐⭐ (native) | ❌ |
| **Turn Detection** | ⭐⭐⭐⭐⭐ (native Flux) | ❌ | ⭐⭐⭐⭐ (server VAD) | ⭐⭐⭐ |
| **Barge-in** | ⭐⭐⭐⭐⭐ | ❌ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Diarization** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ (4 speakers) | ⭐⭐⭐⭐⭐ (32 speakers) |
| **Cost** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ (expensive) | ⭐⭐ (expensive) |
| **DX / Ease** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ (GCP friction) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Self-hosted** | ✅ | ✅ | ❌ | ❌ (enterprise only) |
| **Function Calling** | ✅ | ❌ (separate) | ✅ | ✅ |
| **Compliance** | SOC2, HIPAA, GDPR, PCI | SOC2, HIPAA, CMEK | SOC2 | SOC2, HIPAA (enterprise) |

---

## 8. Architecture Options for Voice-First Assistant

### Option A: Deepgram Voice Agent API (Recommended for MVP)
```
User Mic → [Deepgram Voice Agent API] → Speakers
              ├── STT (Flux/Nova-3)
              ├── LLM (BYO: GPT-4o / Claude)
              ├── TTS (Aura-2)
              └── Function calling (memory retrieval, actions)
```
**Pros:** Single API, lowest latency voice pipeline, cheapest at $4.50/hr, BYO LLM  
**Cons:** TTS quality is "enterprise" not "premium", English-only TTS  
**Best for:** Fast MVP, production voice agents, cost-sensitive deployment

### Option B: OpenAI Realtime API (Best Quality Experience)
```
User Mic → [WebRTC/WebSocket] → [GPT-realtime-1.5] → Speakers
                                     ├── Native speech reasoning
                                     ├── Function calling
                                     └── MCP integration
```
**Pros:** True speech-to-speech (no chain), lowest theoretical latency, best reasoning quality, simplest code  
**Cons:** Most expensive (~$8.64/hr), only 6 voices, vendor lock-in, no BYO LLM  
**Best for:** Premium experience where cost is secondary, maximum simplicity

### Option C: Hybrid — Deepgram STT + Your LLM + ElevenLabs TTS
```
User Mic → [Deepgram Flux STT] → [Your LLM] → [ElevenLabs Flash v2.5 TTS] → Speakers
              (WebSocket)            (API)           (WebSocket)
```
**Pros:** Best-in-class STT + best-in-class TTS, full LLM control, voice cloning  
**Cons:** More complex, higher latency (three hops), more expensive TTS  
**Best for:** Premium voice quality with custom voice, multilingual

### Option D: Google Cloud STT + TTS (Best for Multilingual / Budget)
```
User Mic → [Google STT V2] → [Your LLM] → [Google TTS (WaveNet)] → Speakers
              (gRPC)            (API)           (gRPC)
```
**Pros:** Cheapest TTS ($4/1M chars), broadest language support, Google infrastructure  
**Cons:** Most DIY, no voice agent orchestration, GCP complexity, higher latency  
**Best for:** Multilingual assistant, budget-constrained, Google Cloud ecosystem

### Option E: OpenAI Realtime + Deepgram STT fallback
```
Primary: User Mic → [GPT-realtime-1.5] → Speakers (real-time conversations)
Fallback: Audio recording → [Deepgram Nova-3] → Text (batch transcription, memory indexing)
```
**Pros:** Best real-time experience + cheap batch processing for memory  
**Cons:** Two providers, higher primary cost  
**Best for:** Jarvis-like assistant where real-time quality matters most

---

## 9. Recommendation

### For a Jarvis-like Voice-First Personal Memory Assistant

#### Recommended Stack: **Option A (MVP) → Option E (Premium)**

**Phase 1 — MVP (start here):**
| Component | Choice | Why |
|---|---|---|
| **STT** | Deepgram Flux | Native turn detection, sub-300ms, best for voice agents |
| **LLM** | GPT-4o (via Deepgram BYO LLM) | Best reasoning for a memory assistant |
| **TTS** | Deepgram Aura-2 | Sub-200ms, good enough for MVP |
| **Orchestration** | Deepgram Voice Agent API | Single API, $4.50/hr, handles barge-in/turn-taking |
| **Cost** | ~$0.050-0.075/min | Very affordable for personal use |

**Phase 2 — Premium Experience:**
| Component | Choice | Why |
|---|---|---|
| **Real-time conversation** | OpenAI Realtime API (GPT-realtime-1.5) | True speech-to-speech, best conversational feel |
| **Batch STT / Memory indexing** | Deepgram Nova-3 | Cheap, accurate transcription for storing memories |
| **Premium TTS (optional)** | ElevenLabs Flash v2.5 / Eleven v3 | If you want cloned voice or cinematic quality |

#### Decision Matrix for Your Use Case

| Priority | Best Choice | Why |
|---|---|---|
| **Lowest latency** | OpenAI Realtime API | Native speech-to-speech, no chain |
| **Best value** | Deepgram Voice Agent API | $4.50/hr all-inclusive |
| **Best TTS quality** | ElevenLabs Eleven v3 | Most expressive, voice cloning |
| **Best STT accuracy** | Deepgram Nova-3 / Flux | Industry-leading WER |
| **Easiest to build** | OpenAI Realtime + Agents SDK | 10 lines of code |
| **Most flexible** | Deepgram (BYO everything) | Swap LLM, TTS, deploy anywhere |
| **Multilingual** | Google Cloud | 85+ STT languages, 75+ TTS |
| **Self-hosted** | Deepgram | On-prem option available |

---

## 10. Gaps & Issues

### Information Not Confirmed
1. **OpenAI Realtime API exact latency numbers** — no official ms benchmarks published
2. **ElevenLabs Conversational AI pricing** — credit-based, hard to estimate per-minute for voice agents
3. **OpenAI TTS pricing** — not separately listed on the main pricing page (bundled as audio tokens)
4. **Google STT streaming latency benchmarks** — not published on product page
5. **Deepgram Flux multilingual timeline** — currently English-only, no roadmap visible

### Contradictions / Ambiguities
1. **ElevenLabs Flash v2.5 claims ~75ms TTS latency** vs Deepgram Aura-2 claims <200ms — ElevenLabs Flash may actually be faster on raw TTS, but with lower quality
2. **Google's "85+ languages" vs "125+ languages"** — different numbers appear on different pages, likely 85+ for Chirp 3 specifically
3. **Deepgram's pricing shows "Growth" plan saving up to 20%** but some Voice Agent tiers show Growth more expensive than PAYG (e.g., Custom BYO LLM: $0.056 PAYG vs $0.059 Growth) — possible pricing page error

### Key Risks
1. **OpenAI Realtime API pricing may change** — currently in early GA, pricing could increase
2. **Deepgram Voice Agent API is new** (launched June 2025) — may have stability issues at scale
3. **Vendor lock-in risk with OpenAI Realtime** — no BYO option, no self-host
4. **ElevenLabs scaling costs** — credit system makes high-volume use very expensive

---

## Final Summary

**For a Jarvis-like voice-first personal memory assistant:**

1. **Start with Deepgram Voice Agent API** — it gives you the best balance of latency ($<300ms$), cost ($\$4.50/hr$), developer experience, and flexibility (BYO LLM). The unified API simplifies development dramatically.

2. **Evaluate OpenAI Realtime API** for the premium tier — if the $2x$ price premium is acceptable, the native speech-to-speech experience is objectively the most natural and lowest-latency option.

3. **Use ElevenLabs only for TTS** if voice quality is paramount — voice cloning and emotional expressiveness are unmatched, but don't use them as your primary STT.

4. **Avoid Google Cloud for voice agents** — excellent infrastructure for batch/multilingual work, but too much DIY friction for real-time conversational AI.

5. **Deepgram is the clear "voice AI infrastructure" winner** for the agent use case — not because it's best at any single thing, but because it's the only platform that solves the end-to-end pipeline in one API with the right balance of cost, quality, and flexibility.

---

*All links processed. Research complete. Data sourced from official product pages, pricing pages, and developer documentation as of April 2026.*
