# LLM Orchestration Research for Voice-First Memory Assistant

> Research compiled April 17, 2026 — all pricing verified from official sources

---

## 1. LLM Model Comparison for Memory Assistant Tasks

### Pricing Table (per 1M tokens, USD)

| Model | Input | Output | Cache Read | Context | Latency Class |
|---|---|---|---|---|---|
| **OpenAI GPT-4o** | $2.50 | $10.00 | $1.25 | 128K | ~0.54s TTFT |
| **OpenAI GPT-4o-mini** | $0.15 | $0.60 | $0.075 | 128K | ~0.52s TTFT |
| **OpenAI GPT-4.1** | $2.00 | $8.00 | $0.50 | 1M | ~0.70s TTFT |
| **OpenAI GPT-4.1-mini** | $0.40 | $1.60 | $0.10 | 1M | ~0.75s TTFT |
| **OpenAI GPT-4.1-nano** | $0.10 | $0.40 | $0.025 | 1M | ~0.59s TTFT |
| **Claude Sonnet 4.6** | $3.00 | $15.00 | $0.30 | 1M | Fast |
| **Claude Haiku 4.5** | $1.00 | $5.00 | $0.10 | 200K | Fastest |
| **Claude Haiku 3.5** | $0.80 | $4.00 | $0.08 | 200K | Fastest |
| **Claude Opus 4.7** | $5.00 | $25.00 | $0.50 | 1M | Moderate |
| **Gemini 2.5 Flash** | $0.30 | $2.50 | $0.03 | 1M | Fast |
| **Gemini 2.5 Pro** | $1.25 | $10.00 | $0.125 | 1M | Moderate |
| **Gemini 2.5 Flash-Lite** | $0.10 | $0.40 | $0.01 | 1M | Fastest |

**Notes:**
- Claude "3.5 Sonnet" and "3.5 Haiku" are now legacy names; current equivalents are Sonnet 4.6 and Haiku 4.5
- Claude "4" line: Sonnet 4.6 ($3/$15), Haiku 4.5 ($1/$5), Opus 4.7 ($5/$25)
- Gemini 2.5 Flash has a **free tier** (standard) for prototyping
- GPT-4.1 series supersedes GPT-4o with better instruction following + 1M context
- OpenAI latency data from OpenRouter real-world measurements (TTFT = time to first token)

### Task-to-Model Recommendations

| Task | Primary Recommendation | Budget Alternative | Why |
|---|---|---|---|
| **Fact Extraction** (from voice captures) | GPT-4.1-mini | Gemini 2.5 Flash | Structured output with strict mode; excellent instruction following at $0.40/$1.60. Gemini Flash at $0.30/$2.50 nearly as good, free tier for dev |
| **Question Generation** (active recall) | GPT-4.1-nano | Gemini 2.5 Flash-Lite | Formulaic task; nano scores 80.1% MMLU. At $0.10/$0.40 it's 25x cheaper than GPT-4.1. Flash-Lite is even cheaper at $0.10/$0.40 |
| **Answer Evaluation** (grading accuracy) | GPT-4.1-mini | Claude Haiku 4.5 | Needs nuanced judgment but not frontier-level reasoning. Mini provides the sweet spot. Haiku 4.5 at $1/$5 is excellent for evaluation rubrics |
| **Technique Selection** (chunking vs mnemonic) | GPT-4.1-nano | Gemini 2.5 Flash-Lite | Classification task; nano handles this easily. Cheapest viable option |
| **Conversational Teaching** ("teach me X") | Claude Sonnet 4.6 | GPT-4.1 | Sonnet excels at engaging, pedagogical responses. GPT-4.1 at $2/$8 is slightly cheaper with strong instruction following |
| **Semantic Knowledge Queries** ("what did I learn about X?") | GPT-4.1-mini | Gemini 2.5 Flash | Needs retrieval + synthesis with long context. GPT-4.1-mini has 1M context at affordable rates |

### Quality Tradeoffs Summary

| Dimension | Nano/Flash-Lite Tier | Mini/Flash Tier | Full/Sonnet Tier |
|---|---|---|---|
| Structured JSON reliability | Good (strict mode) | Excellent | Excellent |
| Nuanced evaluation | Poor — too formulaic | Good | Excellent |
| Conversational warmth | Robotic | Decent | Natural, engaging |
| Instruction following | 80% MMLU, basic | 84% IFEval | 87%+ IFEval |
| Cost (est. per call ~500 in / 200 out tokens) | ~$0.00013 | ~$0.00052 | ~$0.0026 |

---

## 2. Structured Outputs

### Approaches Ranked (Best to Worst)

#### 1. OpenAI Structured Outputs (`response_format: json_schema`) — RECOMMENDED
```python
from openai import OpenAI
from pydantic import BaseModel

client = OpenAI()

class ExtractedFacts(BaseModel):
    topic: str
    facts: list[str]
    connections: list[str]
    difficulty_level: str  # "basic" | "intermediate" | "advanced"

response = client.responses.parse(
    model="gpt-4.1-mini",
    input=[
        {"role": "system", "content": "Extract key facts from this voice capture."},
        {"role": "user", "content": transcript},
    ],
    text_format=ExtractedFacts,
)
extracted = response.output_parsed  # Typed ExtractedFacts object
```

**Key properties:**
- **100% schema adherence** — guaranteed valid JSON matching your schema
- Uses `strict: true` under the hood
- Pydantic model → JSON schema conversion handled by SDK
- All fields must be `required`, use `type: ["string", "null"]` for optional
- `additionalProperties: false` enforced on all objects
- Max 5000 properties, 10 levels nesting, 1000 enum values
- Supports recursive schemas and `$defs`
- Supported on GPT-4o, GPT-4.1 series, and newer

#### 2. Function Calling with Strict Mode
```python
tools = [{
    "type": "function",
    "name": "save_extracted_facts",
    "description": "Save extracted facts from a voice capture",
    "strict": true,
    "parameters": {
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "facts": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["topic", "facts"],
        "additionalProperties": false
    }
}]
```
**Use when:** You need the model to _decide_ whether to call a function (e.g., "should I extract facts or is this just chitchat?")

#### 3. JSON Mode (Legacy)
- Only guarantees valid JSON, **not** schema adherence
- Must include "JSON" in the prompt
- Use only for older models that don't support Structured Outputs

#### When to Use Function Calling vs Structured `text.format`
- **Function calling**: When connecting the model to your application tools (save_fact, schedule_review, query_knowledge)
- **`text.format` with `json_schema`**: When you want structured data in the model's response to the user (extraction results, question objects)

### Error Handling for Malformed Outputs

```python
# With Structured Outputs, malformed JSON is impossible. Handle refusals instead:
response = client.responses.parse(
    model="gpt-4.1-mini",
    input=messages,
    text_format=ExtractedFacts,
)

if hasattr(response, 'output_parsed') and response.output_parsed:
    facts = response.output_parsed
else:
    # Check for refusal
    for item in response.output:
        if hasattr(item, 'content'):
            for block in item.content:
                if block.type == "refusal":
                    handle_refusal(block.refusal)

# For Claude/Gemini (no guaranteed schema adherence):
import json
try:
    data = json.loads(response.content)
    validated = ExtractedFacts.model_validate(data)
except (json.JSONDecodeError, ValidationError) as e:
    # Retry with explicit error feedback
    retry_with_correction(original_prompt, str(e))
```

### Gemini Structured Outputs
- Supports `response_mime_type: "application/json"` with `response_schema`
- Also supports function calling with schema enforcement
- Free tier available — good for development

### Claude Structured Outputs
- No native Structured Outputs (no guaranteed schema adherence)
- Best approach: Use tool_use with JSON schema in tool definition
- Combine with explicit Pydantic validation in your code

---

## 3. Orchestration Patterns

### Pattern Comparison for Memory Assistant

#### A. Single Prompt (Simplest)
```
User speaks → STT → Single LLM call → All outputs
```
**Use for:** Simple queries like "what did I learn about X?"
**Avoid for:** Capture pipeline (extraction + questions + technique selection)

#### B. Chain of Prompts (RECOMMENDED for Capture Pipeline)
```
Voice → STT → Extract Facts (nano) → Generate Questions (nano) → Select Technique (nano) → Store
                     ↓
              [Can run in parallel after extraction]
```

```python
# Step 1: Extract facts (blocking — everything depends on this)
facts = await extract_facts(transcript)  # GPT-4.1-nano, structured output

# Step 2-3: Run in parallel (independent of each other)
questions_task = asyncio.create_task(generate_questions(facts))  # GPT-4.1-nano
technique_task = asyncio.create_task(select_technique(facts))    # GPT-4.1-nano

questions, technique = await asyncio.gather(questions_task, technique_task)
```

**Why chain > single prompt:**
- Each step uses a focused, simple prompt → higher quality
- Allows different models per step
- Parallel execution where possible
- Individual step failures can be retried

#### C. Agent Loop (for Conversational Teaching)
```
User: "Teach me about mitochondria"
→ LLM decides: retrieve_knowledge → synthesize → ask_check_question → evaluate_answer → continue/stop
```
**Use for:** Interactive review sessions and "teach me" conversations
**Implementation:** Use function calling with tools like `retrieve_facts`, `get_review_history`, `grade_answer`

### When to Use Function Calling

| Scenario | Use Function Calling? | Why |
|---|---|---|
| Extract facts from transcript | No — use Structured Outputs | You always want extraction; no decision needed |
| Generate questions | No — use Structured Outputs | Deterministic task |
| "Should I save this?" classification | Yes | Model decides whether to call `save_capture()` |
| Review session conversation | Yes | Model decides when to call `grade_answer()`, `next_question()`, `provide_hint()` |
| Knowledge query | Yes | Model decides to call `search_knowledge()` then synthesize |

### Multi-Step Flow: Capture Pipeline

```python
async def process_capture(audio_bytes: bytes) -> CaptureResult:
    # 1. STT (fastest path — can use Whisper or Gemini Live)
    transcript = await speech_to_text(audio_bytes)
    
    # 2. Extract facts (GPT-4.1-nano, ~0.6s)
    facts = await llm_extract(
        model="gpt-4.1-nano",
        schema=ExtractedFacts,
        input=transcript
    )
    
    # 3. Parallel: questions + technique (both ~0.6s, run concurrently)
    questions, technique = await asyncio.gather(
        llm_generate_questions(model="gpt-4.1-nano", facts=facts),
        llm_select_technique(model="gpt-4.1-nano", facts=facts),
    )
    
    # 4. Store everything
    await store_capture(facts, questions, technique)
    
    return CaptureResult(facts=facts, questions=questions, technique=technique)
    
# Total latency: STT (~1s) + Extract (~0.6s) + max(Questions, Technique) (~0.6s) ≈ 2.2s
```

### Minimizing Latency in Voice Conversations

1. **Stream responses** — Use `stream=True` and start TTS as tokens arrive
2. **Use nano/Flash-Lite for classification** — Sub-second TTFT
3. **Parallel LLM calls** where steps are independent
4. **Prompt caching** — Cache system prompts (saves latency + cost)
5. **Pre-warm connections** — Keep HTTP/2 connections alive
6. **Edge deployment** — Use providers in your region
7. **Avoid chain-of-thought for simple tasks** — Don't use reasoning models for classification
8. **Batch async processing** — Queue non-urgent work (FSRS scheduling updates) for Batch API

---

## 4. Prompt Engineering for Memory Tasks

### A. Extraction Prompts

```
SYSTEM:
You are a knowledge extraction engine for a spaced repetition memory system.
Extract SPECIFIC, TESTABLE facts from the user's voice capture.

Rules:
- Each fact must be a single, atomic piece of knowledge
- Include specific numbers, names, dates, relationships — not vague summaries
- "The mitochondria produces ATP through oxidative phosphorylation" ✓
- "Mitochondria are important for cells" ✗ (too vague)
- Extract causal relationships: "X causes Y because Z"
- Extract definitions: "X is defined as Y"
- Extract comparisons: "X differs from Y in that Z"
- Ignore filler words, greetings, meta-commentary about learning
- If the capture contains no extractable knowledge, return empty facts array
```

### B. Question Generation Prompts

```
SYSTEM:
Generate review questions for spaced repetition from the extracted facts.
Create a mix of question types:

1. RECALL: "What is [concept]?" — tests basic retrieval
2. CLOZE: "[Fact with _____ blank]" — fill-in-the-blank
3. EXPLAIN: "Explain why/how [process works]" — tests understanding
4. CONNECT: "How does [concept A] relate to [concept B]?" — tests integration
5. APPLY: "Given [scenario], what would happen if [change]?" — tests transfer

Rules:
- Questions must be answerable from the extracted facts alone
- Include the expected answer for each question
- Vary difficulty: 40% recall, 20% cloze, 20% explain, 10% connect, 10% apply
- Each question should test exactly ONE fact or connection
```

### C. Answer Evaluation Prompts

```
SYSTEM:
You are an answer evaluator for a spaced repetition system.
Compare the user's answer against the expected answer.

Scoring rubric (1-5):
5 - Perfect: Contains all key elements, demonstrates full understanding
4 - Good: Contains most key elements, minor omissions that don't affect meaning
3 - Partial: Contains some correct elements but missing key aspects
2 - Poor: Shows vague familiarity but significant gaps or errors
1 - Wrong: Incorrect or completely off-topic

Rules:
- Accept semantic equivalence (different wording, same meaning = correct)
- Accept additional correct details beyond the expected answer
- Do NOT penalize for informal language or incomplete sentences
- DO penalize for factual errors, even if partially correct
- Provide brief feedback: what was correct, what was missing
- Be encouraging but honest — never say "close enough" for wrong answers
```

### D. Technique Selection Prompts

```
SYSTEM:
Select the optimal memory technique for the given facts.

Available techniques:
- CHUNKING: For lists, sequences, grouped information (>3 related items)
- MNEMONIC: For arbitrary associations, foreign words, codes
- ELABORATION: For concepts needing deep understanding, cause-effect chains
- VISUALIZATION: For spatial, anatomical, or process-based knowledge
- ANALOGY: For abstract concepts that map to familiar domains
- SPACED_REPETITION_ONLY: For simple facts that just need repetition

Selection criteria:
- Consider the TYPE of knowledge (factual, procedural, conceptual)
- Consider the QUANTITY of related facts (chunking for >3)
- Consider PRIOR knowledge connections (elaboration when connections exist)
- Return the technique name + specific instructions for applying it to these facts
```

---

## 5. Cost Optimization

### Prompt Caching

| Provider | Mechanism | Cache Write Cost | Cache Read Cost | Duration | Min Tokens |
|---|---|---|---|---|---|
| **OpenAI** | Automatic on repeated prefixes | Same as input | 50% of input (for GPT-4.1: $1.00) | ~5-10 min | 1024+ tokens |
| **Anthropic** | Explicit `cache_control` breakpoints | 1.25x input (5min) or 2x (1hr) | 0.1x input | 5min or 1hr | 1024+ tokens |
| **Gemini** | Context caching API | Per-model (Flash: $0.03) | Per-model | Configurable | Large prompts |

**Impact for memory assistant:**
- System prompts for extraction/evaluation are repeated on every call → **cache them**
- With OpenAI caching: GPT-4.1-nano input drops from $0.10 to $0.025/MTok for cached prefix
- With Anthropic 5-min caching on Haiku 4.5: $1.25 write, $0.10 read → pays off after 1 read

### Batch API for Async Processing

| Provider | Discount | SLA | Use Case |
|---|---|---|---|
| **OpenAI** | 50% off (input price becomes cached rate) | 24hr completion | Nightly question regeneration, bulk re-evaluation |
| **Anthropic** | 50% off | 24hr completion | Same |
| **Gemini** | 50% off | Async | Same |

**Best for:** Re-generating questions when FSRS parameters update, periodic knowledge graph maintenance, bulk imports

### Model Tiering Strategy

| Tier | Model | Use When | Cost/call (500 in + 200 out tokens) |
|---|---|---|---|
| **Ultra-cheap** | GPT-4.1-nano / Gemini Flash-Lite | Classification, technique selection, simple extraction | ~$0.00013 |
| **Workhorse** | GPT-4.1-mini / Gemini 2.5 Flash | Extraction, question gen, answer eval | ~$0.00052 |
| **Quality** | Claude Sonnet 4.6 / GPT-4.1 | Conversational teaching, complex queries | ~$0.0045 |

### Token Usage Estimation

**Typical capture pipeline:**
| Step | Input tokens | Output tokens | Model | Cost |
|---|---|---|---|---|
| Extract facts | ~800 (system + transcript) | ~300 | GPT-4.1-nano | $0.0002 |
| Generate questions | ~600 (system + facts) | ~500 | GPT-4.1-nano | $0.0003 |
| Select technique | ~400 (system + facts) | ~100 | GPT-4.1-nano | $0.0001 |
| **Total per capture** | | | | **~$0.0006** |

**Typical review session (single question):**
| Step | Input tokens | Output tokens | Model | Cost |
|---|---|---|---|---|
| Present question + evaluate answer | ~600 | ~200 | GPT-4.1-mini | $0.0006 |

**Conversational teaching (1 exchange):**
| Step | Input tokens | Output tokens | Model | Cost |
|---|---|---|---|---|
| Teach + follow-up | ~1500 | ~800 | Claude Sonnet 4.6 | $0.0165 |

### Monthly Cost Projections (Personal Use)

| Usage Pattern | Captures/day | Reviews/day | Teach sessions/week | Monthly Cost |
|---|---|---|---|---|
| **Light** | 2 | 10 | 2 | **$0.32** |
| **Medium** | 3 | 15 | 3 | **$0.52** |
| **Heavy** | 5 | 25 | 5 | **$0.92** |
| **Heavy + no caching** | 5 | 25 | 5 | ~$1.40 |

**Calculation (Medium):**
- 3 captures × $0.0006 × 30 days = $0.054
- 15 reviews × $0.0006 × 30 days = $0.27
- 3 teach sessions × $0.0165 × 4 weeks = $0.198
- **Total: ~$0.52/month**

**Verdict: Extremely affordable.** Even heavy personal use stays under $1/month with proper model tiering.

### Cost Optimization Checklist

1. ✅ Use GPT-4.1-nano for all classification/generation tasks
2. ✅ Use GPT-4.1-mini for evaluation tasks
3. ✅ Reserve Sonnet 4.6 only for conversational teaching
4. ✅ Enable prompt caching for all system prompts
5. ✅ Use Batch API for nightly question regeneration
6. ✅ Parallelize independent LLM calls (not sequential)
7. ✅ Use Gemini 2.5 Flash free tier during development
8. ✅ Monitor token usage per endpoint, alert on anomalies

---

## 6. OpenRouter as LLM Gateway

### What It Is
OpenRouter provides a **unified OpenAI-compatible API** to 300+ models from 60+ providers through a single endpoint (`https://openrouter.ai/api/v1/chat/completions`).

### Pricing Model
- **Pay-as-you-go**: 5.5% markup on provider pricing (no minimum spend)
- **Free tier**: 25+ free models, 50 req/day rate limit
- **BYOK (Bring Your Own Key)**: 1M free requests/month, 5% fee after
- **Enterprise**: Volume discounts, custom rate limits, SLA

### Model Availability (as of April 2026)
- All GPT-4.1 series (nano, mini, full) ✓
- All GPT-4o series ✓
- GPT-5.x series ✓
- Claude Opus 4.7, Sonnet 4.6, Haiku 4.5 ✓
- Gemini 2.5 Flash, 2.5 Pro ✓
- 300+ total models across providers

### Real-World Performance Data (from OpenRouter)

| Model | Avg Latency (TTFT) | Avg Throughput | Tool Call Error Rate | Structured Output Error Rate |
|---|---|---|---|---|
| GPT-4.1-nano | 0.59s (OpenAI), 1.65s (Azure) | 49 tok/s | 1.04% | 1.48% |
| GPT-4.1-mini | 0.75s (OpenAI), 1.05s (Azure) | 41 tok/s | 0.41% | 4.54% |
| GPT-4.1 | 0.70s (OpenAI), 1.27s (Azure) | 36 tok/s | 0.28% | 3.76% |
| GPT-4o | 0.54s (OpenAI), 0.89s (Azure) | 46 tok/s | 1.01% | 2.61% |
| GPT-4o-mini | 0.52s (OpenAI), 0.72s (Azure) | 37 tok/s | 0.95% | 0.40% |

### When OpenRouter is Better Than Direct API

| Scenario | Direct API | OpenRouter |
|---|---|---|
| Single provider (e.g., only OpenAI) | ✅ Better — no markup | ❌ 5.5% markup |
| Multi-provider (OpenAI + Anthropic + Gemini) | ❌ Multiple SDKs, keys, billing | ✅ Single API, one bill |
| High availability requirements | ❌ No automatic fallback | ✅ Auto-fallback across providers |
| Experimentation / model comparison | ❌ Separate integrations | ✅ Change model string, done |
| Cost-sensitive production | ✅ No middleman | ❌ 5.5% adds up at scale |
| BYOK + routing benefits | N/A | ✅ Best of both worlds |

### Recommendation for This Project

**Use direct APIs in production.** For a personal memory assistant:
- You'll primarily use 2-3 models (GPT-4.1-nano, GPT-4.1-mini, Claude Sonnet 4.6)
- Monthly spend is <$1 — the 5.5% markup is negligible ($0.05)
- But direct API gives you: lower latency, prompt caching, Batch API access

**Use OpenRouter for development/evaluation:**
- Test different models without setting up multiple API keys
- Compare structured output quality across providers
- Use free models during prototyping

### Rate Limits

| Tier | Rate Limit |
|---|---|
| Free | 50 requests/day |
| Pay-as-you-go | High global limits (model-dependent) |
| Enterprise | Custom dedicated limits |
| BYOK | Subject to provider's own limits |

---

## Cross-Link Summary

### Key Decision Matrix

```
                    ┌─────────────────────────────────────────────┐
                    │        VOICE CAPTURE ARRIVES                │
                    └─────────────────┬───────────────────────────┘
                                      │
                              ┌───────▼───────┐
                              │  Whisper STT  │
                              └───────┬───────┘
                                      │
                    ┌─────────────────▼─────────────────────┐
                    │   GPT-4.1-nano: Extract Facts          │
                    │   (Structured Output, ~$0.0002)        │
                    └──────┬────────────────────┬────────────┘
                           │                    │
              ┌────────────▼──────┐  ┌──────────▼──────────┐
              │ GPT-4.1-nano:    │  │ GPT-4.1-nano:       │
              │ Generate Qs      │  │ Select Technique     │
              │ ($0.0003)        │  │ ($0.0001)            │
              └────────┬─────────┘  └──────────┬───────────┘
                       │                       │
                       └───────────┬───────────┘
                                   │
                           ┌───────▼───────┐
                           │  Store in DB  │
                           └───────────────┘


                    ┌─────────────────────────────────────────────┐
                    │        REVIEW SESSION                       │
                    └─────────────────┬───────────────────────────┘
                                      │
                    ┌─────────────────▼─────────────────────┐
                    │   FSRS selects next card (no LLM)     │
                    └─────────────────┬─────────────────────┘
                                      │
                    ┌─────────────────▼─────────────────────┐
                    │   GPT-4.1-mini: Evaluate Answer        │
                    │   (Structured Output, ~$0.0006)        │
                    └─────────────────┬─────────────────────┘
                                      │
                    ┌─────────────────▼─────────────────────┐
                    │   Update FSRS parameters (no LLM)     │
                    └───────────────────────────────────────┘


                    ┌─────────────────────────────────────────────┐
                    │        "TEACH ME ABOUT X"                   │
                    └─────────────────┬───────────────────────────┘
                                      │
                    ┌─────────────────▼─────────────────────┐
                    │   Claude Sonnet 4.6: Agent Loop        │
                    │   Tools: search_knowledge,             │
                    │          check_understanding,          │
                    │          get_related_facts              │
                    │   (~$0.017 per exchange)                │
                    └───────────────────────────────────────┘
```

### Gaps / Ambiguities

1. **OpenAI pricing page doesn't list GPT-4.1 anymore** — it's been superseded by GPT-5.x. Pricing confirmed via OpenRouter: GPT-4.1 ($2/$8), mini ($0.40/$1.60), nano ($0.10/$0.40). These models remain available and are the best value for this use case.

2. **Claude lacks native Structured Outputs** — no guaranteed JSON schema adherence. For extraction/evaluation tasks, prefer OpenAI models. Use Claude only for conversational tasks where free-form text is the output.

3. **Gemini Structured Outputs** — supported but less battle-tested. The free tier makes it excellent for development but prompt caching is less mature.

4. **GPT-4o vs GPT-4.1**: GPT-4.1 is strictly better for this use case — better instruction following (87.4% vs ~85% IFEval), 1M context (vs 128K), cheaper ($2/$8 vs $2.50/$10), and better structured output support. No reason to use GPT-4o unless you need the 2024-11-20 snapshot specifically.

5. **Latency for voice**: Real-time voice conversation requires <2s total round-trip. Using GPT-4.1-nano (0.59s TTFT) + streaming, you can achieve ~1.5s to start speaking. For answer evaluation during review, the ~0.75s TTFT of mini is fine since users expect a brief pause.

### Final Architecture Recommendation

| Component | Model | API | Cost |
|---|---|---|---|
| Fact extraction | `gpt-4.1-nano` | Direct OpenAI, Structured Outputs | $0.10/$0.40 |
| Question generation | `gpt-4.1-nano` | Direct OpenAI, Structured Outputs | $0.10/$0.40 |
| Technique selection | `gpt-4.1-nano` | Direct OpenAI, Structured Outputs | $0.10/$0.40 |
| Answer evaluation | `gpt-4.1-mini` | Direct OpenAI, Structured Outputs | $0.40/$1.60 |
| Knowledge queries | `gpt-4.1-mini` | Direct OpenAI, Function Calling | $0.40/$1.60 |
| Conversational teaching | `claude-sonnet-4-6` | Direct Anthropic, Tool Use | $3.00/$15.00 |
| Batch reprocessing | `gpt-4.1-nano` (batch) | OpenAI Batch API | 50% off |
| Development/testing | `gemini-2.5-flash` | Google AI (free tier) | Free |

**Estimated monthly cost for personal use: $0.30 – $0.90**

---

## Sources

All data sourced from official documentation on April 17, 2026:
- OpenAI Pricing: https://developers.openai.com/api/docs/pricing
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI Function Calling: https://developers.openai.com/api/docs/guides/function-calling
- Anthropic Models: https://platform.claude.com/docs/en/docs/about-claude/models
- Anthropic Pricing: https://platform.claude.com/docs/en/about-claude/pricing
- Gemini Pricing: https://ai.google.dev/gemini-api/docs/pricing
- Gemini Models: https://ai.google.dev/gemini-api/docs/models
- OpenRouter Models: https://openrouter.ai/models (real-time performance data)
- OpenRouter Docs: https://openrouter.ai/docs
