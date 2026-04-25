# Unified Voice Personal Assistant — Decision Logic
**Version:** 1.0  
**Date:** April 19, 2026  
**Status:** Ready for implementation  
**Depends on:** `docs/deepgram-voice-design.md`, `docs/orchestrator-logic.md`, `docs/system-design.md`  
**Replaces:** Mode-selector approach (capture/review/teach tabs)

---

## 0. Design Summary

The current voice feature requires users to **manually select a mode** (Capture, Review, Teach) before speaking. The unified PA replaces this with a **single conversational agent** that classifies user intent from natural speech and routes to the appropriate backend service — like talking to a smart study coach.

**Key architectural change:** Instead of 3 separate system prompts chosen at connection time, there is **one unified system prompt** with all functions available. The LLM decides which functions to call based on conversation context.

**What stays the same:**
- Deepgram Voice Agent API pipeline (STT → LLM → TTS)
- Server-side WebSocket proxy architecture
- All existing backend services (CaptureService, ReviewService, TeachService, etc.)
- Function calling mechanism (Deepgram intercepts → backend dispatches → result returns)

**What changes:**
- Single WebSocket endpoint: `/ws/voice` (no `?mode=` parameter)
- One unified system prompt replaces 3 mode-specific prompts
- All functions available simultaneously (LLM decides)
- New functions added: `get_user_context`, `start_review_session`, `start_teach_session`, `submit_reflection`, `get_stats`
- Session state tracks conversation phase instead of locked mode
- Proactive behavior based on injected user context

---

## 1. Workflow Inventory

| # | Workflow | One-line Description | Trigger |
|---|---|---|---|
| W1 | **Session Start** | Greet user with contextual suggestion based on stats/time | WebSocket connect |
| W2 | **Capture** | User dictates knowledge → AI extracts facts + generates questions | User shares information to remember |
| W3 | **Review** | FSRS spaced repetition quiz loop | User asks to be quizzed or PA suggests |
| W4 | **Teach** | AI teaches a topic in chunks with recall checks | User asks to learn about a topic |
| W5 | **Knowledge Search** | Query user's personal knowledge base | User asks about something they captured |
| W6 | **General Q&A** | Answer a question directly without capturing | User asks a factual/general question |
| W7 | **Stats Check** | Report learning stats and progress | User asks about progress/performance |
| W8 | **Reflection** | Evening reflection on what was learned today | User reflects or PA prompts reflection |
| W9 | **Mid-Session Switch** | Transition between workflows mid-conversation | User changes intent mid-conversation |
| W10 | **Session End** | Graceful wrap-up with summary + suggestion | User ends or max duration reached |

---

## 2. Intent Taxonomy

### 2.1 Intent Definitions

```
INTENT: CAPTURE
  Description: User is sharing information they want to remember
  Confidence threshold: 0.7
  
  Trigger patterns:
    - "I just learned that..."
    - "I want to remember that..."
    - "Today I learned..."
    - "Save this: ..."
    - "Note that..."
    - "Remember this..."
    - "Here's what I learned about..."
    - "Capture this..."
    - "So the key takeaway is..."
    - User starts explaining a concept unprompted (declarative speech)
    - Long monologue of factual content (>2 sentences of explanation)
  
  NOT capture (disambiguation):
    - "Tell me about X" → Teach or Q&A (user wants to RECEIVE, not give)
    - "What did I learn about X?" → Search (querying existing knowledge)
    - One-word or very short vague utterance → Clarify

  Functions called: finish_capture, save_why_it_matters
  Conversation flow:
    1. PA acknowledges and listens silently (brief "Got it" on pauses)
    2. User signals done → PA calls finish_capture
    3. PA reports: "Captured X facts and Y review questions."
    4. PA asks: "Why does this matter to you?"
    5. User responds → PA calls save_why_it_matters
    6. PA transitions: "Want me to quiz you on this now?" or returns to idle

---

INTENT: REVIEW
  Description: User wants to practice recall via spaced repetition
  Confidence threshold: 0.8
  
  Trigger patterns:
    - "Quiz me"
    - "Test me"
    - "Start a review"
    - "Review session"
    - "Let's do some practice"
    - "What's due for review?"
    - "Let's study"
    - "I want to practice"
    - "Flash cards" / "flashcards"
    - "Do I have anything to review?"
    - "Let's go through my questions"
  
  Functions called: start_review_session, get_next_question, evaluate_answer, rate_question
  Conversation flow: See §3B (Review Loop)

---

INTENT: TEACH
  Description: User wants the PA to teach them a topic
  Confidence threshold: 0.8
  
  Trigger patterns:
    - "Teach me about [topic]"
    - "Explain [topic] to me"
    - "I want to learn about [topic]"
    - "Help me understand [topic]"
    - "Walk me through [topic]"
    - "Break down [topic] for me"
    - "Can you teach me [topic]?"
    - "Let's learn about [topic]"
    - "I need to understand [topic]"
  
  Required parameter: topic (extracted from utterance)
  
  Disambiguation from Q&A:
    - "What is a hash table?" → Q&A (wants quick answer)
    - "Teach me about hash tables" → Teach (wants structured lesson)
    - "Explain hash tables" → AMBIGUOUS — resolve by length expectation:
      IF user says "briefly" / "in a nutshell" / "quickly" → Q&A
      ELSE → Teach (default for "explain")
    - "Tell me about X" → AMBIGUOUS — resolve:
      IF X is a broad topic ("sorting algorithms", "Docker networking") → Teach
      IF X is a narrow fact ("the capital of France") → Q&A
      IF unclear → PA asks: "Want a quick answer or a full lesson on that?"
  
  Functions called: start_teach_session, get_current_teach_chunk, submit_teach_answer
  Conversation flow: See §3C (Teach Loop)

---

INTENT: SEARCH
  Description: User wants to query their personal knowledge base
  Confidence threshold: 0.7
  
  Trigger patterns:
    - "What did I learn about [topic]?"
    - "What do I know about [topic]?"
    - "Search my notes for [topic]"
    - "Did I capture anything about [topic]?"
    - "What did I save about [topic]?"
    - "Find my notes on [topic]"
    - "Recall what I learned about [topic]"
    - "When did I learn about [topic]?"
    - "What were the key points about [topic]?"
  
  Key discriminator: The user is asking about THEIR OWN captured knowledge
  (possessive language: "my", "I learned", "I captured", "I saved")
  
  Functions called: search_knowledge
  Conversation flow:
    1. PA calls search_knowledge(query)
    2. IF results found → PA summarizes findings with sources
    3. IF no results → PA says "I don't have anything about [topic] in your knowledge base. Would you like me to teach you about it?"
    4. Return to idle

---

INTENT: GENERAL_QA
  Description: User asks a factual question — just answer it, don't capture
  Confidence threshold: 0.6
  
  Trigger patterns:
    - "What is [concept]?"
    - "How does [thing] work?"
    - "What's the difference between [A] and [B]?"
    - "Define [term]"
    - "Give me a quick answer about..."
    - Factual question without possessive/memory language
  
  Key discriminator: No possessive language, no "I learned" — user wants
  information FROM the PA, not about their own knowledge base
  
  Functions called: None (LLM answers directly from its training data)
  
  Post-answer flow:
    PA answers the question, then asks:
    "Want me to save that to your knowledge base?"
    IF yes → PA calls finish_capture with the Q&A content as transcript
    IF no → return to idle

---

INTENT: STATS
  Description: User wants to know their learning progress
  Confidence threshold: 0.8
  
  Trigger patterns:
    - "How am I doing?"
    - "What are my stats?"
    - "Show me my progress"
    - "What's my streak?"
    - "How's my retention?"
    - "How many reviews do I have?"
    - "Give me a summary"
    - "Dashboard"
  
  Functions called: get_stats
  Conversation flow:
    1. PA calls get_stats
    2. PA reports key metrics conversationally:
       "You're on a [N]-day streak! You have [X] reviews due today.
        Your retention rate is [Y]%. You've captured [Z] facts this week."
    3. PA suggests action based on stats (see §4 Proactive Behavior)

---

INTENT: REFLECTION
  Description: User wants to do their evening reflection
  Confidence threshold: 0.7
  
  Trigger patterns:
    - "Let me reflect"
    - "Daily reflection"
    - "What did I learn today?"
    - "Let me think about what I learned"
    - "Time for reflection"
    - "Evening review"
    - PA proactively suggests it (evening hours)
  
  Functions called: submit_reflection
  Conversation flow:
    1. PA prompts: "What did you learn today? Even a sentence or two."
    2. User speaks their reflection
    3. PA calls submit_reflection with the content
    4. PA responds: "Nice reflection! I extracted [X] facts and created [Y] review questions from that. Your reflection streak is now [Z] days."

---

INTENT: FOLLOW_UP
  Description: User continues the previous topic/action
  Confidence threshold: 0.5 (context-dependent)
  
  Trigger patterns:
    - "Tell me more about that"
    - "Can you elaborate?"
    - "What else?"
    - "Go on"
    - "And?"
    - "Continue"
    - "More details"
    - "What about [related subtopic]?"
  
  Resolution: Depends on previous state:
    IF previous = TEACH → continue teaching / elaborate on last chunk
    IF previous = SEARCH → expand on the search result
    IF previous = GENERAL_QA → elaborate on the answer
    IF previous = CAPTURE → "Are you still capturing? Keep going."
    IF previous = REVIEW → "Ready for the next question?"
    IF no previous context → "What would you like to know more about?"

---

INTENT: SWITCH
  Description: User wants to change what they're doing mid-conversation
  Confidence threshold: 0.7
  
  Trigger patterns:
    - "Actually, quiz me instead"
    - "Wait, let me capture something first"
    - "Can we switch to..."
    - "Never mind, teach me about..."
    - "Forget that, let's review"
    - "Stop this, I want to..."
  
  Handling: See §3D (Mid-Session Switch)

---

INTENT: END_SESSION
  Description: User wants to stop the voice session
  Confidence threshold: 0.9
  
  Trigger patterns:
    - "I'm done"
    - "Stop"
    - "Goodbye"
    - "See you later"
    - "That's all"
    - "End session"
    - "Bye"
    - "Exit"
    - "Quit"
  
  Functions called: end_session
  Conversation flow: See §3E (Session End)

---

INTENT: UNCLEAR
  Description: Cannot determine what the user wants
  Confidence threshold: < 0.5 on all other intents
  
  Trigger patterns:
    - Single words with no context ("okay", "hmm", "yeah")
    - Completely off-topic ("What's the weather?", "Order me pizza")
    - Garbled/misheard speech
  
  Handling:
    - PA responds: "I'm your study assistant — I can help you capture knowledge,
      quiz you on what you've learned, or teach you something new. What would you like?"
    - If user repeats unclear input twice → "Sorry, I'm having trouble understanding.
      Try saying something like 'quiz me' or 'teach me about [topic]'."
```

### 2.2 Intent Priority (When Multiple Match)

```
When the LLM detects multiple possible intents in a single utterance,
use this priority order:

1. END_SESSION (highest — always honor exit)
2. SWITCH (explicit intent change overrides current activity)
3. REVIEW (if user says "quiz me" while doing something else)
4. CAPTURE (explicit "save/capture/remember this")
5. TEACH (explicit "teach me")
6. SEARCH (possessive knowledge query)
7. STATS (progress check)
8. REFLECTION (evening reflection)
9. GENERAL_QA (factual question)
10. FOLLOW_UP (continue previous)
11. UNCLEAR (lowest — ask for clarification)
```

### 2.3 Multi-Intent Handling

```
Utterance: "Capture this and then quiz me"
  → Split into sequential intents:
    STEP 1: Enter CAPTURE mode, listen for knowledge
    STEP 2: After capture completes, automatically start REVIEW
  → PA says: "Got it, I'll capture what you share and then start a quiz. Go ahead."

Utterance: "How am I doing? And do I have anything to review?"
  → Merge into STATS (which includes due count)
  → PA reports stats + suggests starting review if items are due

Utterance: "What is a linked list? Save that to my notes."
  → Sequential: GENERAL_QA first, then auto-CAPTURE the answer
  → PA answers, then confirms capture without asking
```

---

## 3. Decision Flows (Per Workflow)

### 3A. Session Start

```
Workflow: Session Start
Trigger: WebSocket connection opened to /ws/voice
Preconditions: Valid authentication (future), Deepgram API key configured
Input: user_context (injected at session start — see §5)

Logic:
  1. Backend creates VoiceSession (unified — no mode lock)
  2. Backend calls get_user_context() to gather:
     - due_count (reviews due now)
     - streak (consecutive review days)
     - retention_rate (%)
     - recent_captures (last 3 topics captured)
     - time_of_day (morning/afternoon/evening/night)
     - last_activity (what they did last session)
     - user_name (if known)
  3. Context is injected into the system prompt as a preamble
  4. Deepgram agent speaks the greeting (decided by LLM based on context)

  Greeting decision tree (encoded in system prompt instructions):
  
  IF time_of_day == "morning" AND due_count > 0:
    → "Good morning{, name}! You have {due_count} reviews due. Want to knock those out?"
  
  ELIF time_of_day == "morning" AND due_count == 0:
    → "Good morning{, name}! You're all caught up on reviews. Want to capture something new or learn a topic?"
  
  ELIF time_of_day == "evening" AND has_not_reflected_today:
    → "Good evening{, name}! How about a quick reflection on what you learned today?"
  
  ELIF time_of_day == "evening" AND due_count > 0:
    → "Hey{, name}! You still have {due_count} reviews left today. Want to squeeze those in?"
  
  ELIF streak > 0 AND streak % 7 == 0:
    → "Hey{, name}! {streak}-day streak — impressive! What are we working on today?"
  
  ELIF last_activity == "capture" AND due_count > 0:
    → "Welcome back{, name}! Last time you captured some notes about {last_topic}. Ready to review those?"
  
  ELSE:
    → "Hey{, name}! I'm here to help you learn. You can share something to remember, ask me to quiz you, or pick a topic to learn. What sounds good?"

Output: Agent speaks greeting, waits for user input
Edge Cases:
  - Context fetch fails → generic greeting, log error
  - User speaks before greeting finishes → barge-in handled by Deepgram, classify immediately
  - User says nothing for 10s → agent prompts: "I'm here when you're ready!"
```

### 3B. Review Loop

```
Workflow: Review
Trigger: User says "quiz me" / PA suggests review / user confirms review suggestion
Preconditions: User has reviews due (due_count > 0)
Input: None (questions fetched by function call)

Logic:

  STEP 1: START REVIEW
    PA calls start_review_session()
    
    IF response.due_count == 0:
      → PA says: "You're all caught up — no reviews due right now! 
         Want to capture something new or learn a topic?"
      → Return to IDLE
    
    IF response.due_count > 0:
      → PA says: "Let's do it! You have {due_count} questions to review. Here's the first one."
      → PA calls get_next_question()
      → Enter ASKING state

  STEP 2: ASKING (per question)
    PA speaks the question clearly
    
    IF question has context_hint (from the capture):
      → PA adds: "This was from your notes on {topic}."
    
    → Enter LISTENING state (wait for user)
    
    IF user says nothing for 15s:
      → PA prompts: "Take your time. Want me to repeat the question?"
    
    IF user says "repeat":
      → PA re-reads the question
      → Stay in LISTENING
    
    IF user says "skip":
      → PA says "Okay, skipping."
      → PA calls get_next_question()
      → IF more questions → ASKING
      → IF done → COMPLETE
    
    IF user says "hint" AND question has mnemonic_hint:
      → PA says: "Here's a hint: {mnemonic_hint}"
      → Stay in LISTENING
    
    IF user gives an answer:
      → Enter EVALUATING

  STEP 3: EVALUATING
    PA calls evaluate_answer(question_id, user_answer)
    
    → Enter FEEDBACK state

  STEP 4: FEEDBACK
    score = evaluation.score  (correct / partial / incorrect)
    
    IF score == "correct":
      → PA says: "That's right! {brief praise}. {correct_answer}"
    ELIF score == "partial":
      → PA says: "You're on the right track! {what they got right}. 
         The full answer is: {correct_answer}"
    ELIF score == "incorrect":
      → PA says: "Not quite, but that's how we learn! 
         The answer is: {correct_answer}"
    
    IF question has mnemonic_hint AND score != "correct":
      → PA adds: "Here's a memory trick: {mnemonic_hint}"
    
    → PA asks: "How did you find that? Say again, hard, good, or easy."
    → Enter RATING state

  STEP 5: RATING
    User speaks rating word
    LLM maps to integer:
      "again" | "forgot" | "didn't know" | "no" | "1"        → 1
      "hard" | "barely" | "struggled" | "difficult" | "2"    → 2
      "good" | "got it" | "knew it" | "correct" | "yes" | "3" → 3
      "easy" | "too easy" | "obvious" | "trivial" | "4"      → 4
      
    IF cannot parse → PA asks: "Sorry, was that again, hard, good, or easy?"
    
    PA calls rate_question(question_id, rating)
    
    → PA says: "Got it. {next_due_message}."
      WHERE next_due_message:
        IF interval < 1 hour → "You'll see this again soon."
        IF interval < 1 day  → "I'll ask you again later today."
        IF interval < 7 days → "Scheduled for {interval_days} days from now."
        ELSE → "See you on this one in {interval_days} days."
    
    PA calls get_next_question()
    
    IF more questions:
      → "Next one!" → ASKING
    IF no more:
      → COMPLETE

  STEP 6: COMPLETE
    PA says: "Great session! You reviewed {count} questions.
      {encouragement based on performance}."
    
    IF average score was high:
      → "You're really retaining this well!"
    ELIF average score was mixed:
      → "Some tricky ones today — that's totally normal."
    ELIF average score was low:
      → "Tough session, but showing up is what matters. You'll get stronger!"
    
    → PA suggests next action:
      "Want to capture something new, or should we call it?"
    
    → Return to IDLE

Output: Review stats (count, scores, duration)
Edge Cases:
  - User starts answering before PA finishes question → Deepgram barge-in handles this
  - User says "stop" mid-review → end_session, report partial stats
  - User asks unrelated question mid-review → PA answers via search_knowledge or
    general knowledge, then says "Let's get back to the review. Here's the question again."
  - User rates inconsistently ("easy" for wrong answer) → trust user's self-rating, FSRS handles it
  - evaluate_answer LLM call fails → fallback: "I couldn't evaluate that. How did you feel about your answer? Again, hard, good, or easy?" (skip to rating)
```

### 3C. Teach Loop

```
Workflow: Teach
Trigger: User says "teach me about [topic]"
Preconditions: Topic extracted from utterance
Input: topic (string)

Logic:

  STEP 1: START TEACH SESSION
    PA calls start_teach_session(topic)
    
    IF start fails (LLM couldn't generate plan):
      → PA says: "I'm having trouble putting together a lesson on that. 
         Could you be more specific about what you want to learn?"
      → Return to IDLE
    
    → PA says: "Great, let's learn about {topic}! I've broken it down into 
       {total_chunks} parts. Let's start with the first one."
    → PA calls get_current_teach_chunk()
    → Enter TEACHING

  STEP 2: TEACHING
    PA presents the chunk:
      1. "{chunk_title}"
      2. Explains chunk_content conversationally
      3. Weaves in chunk_analogy if present
    
    → PA asks the recall_question
    → Enter RECALL_LISTENING

  STEP 3: RECALL_LISTENING
    User answers the recall question
    
    IF user says "repeat" or "say that again":
      → PA re-explains the chunk (using different words)
      → Re-asks the recall question
      → Stay in RECALL_LISTENING
    
    IF user says "skip":
      → PA says "No worries, let's move on."
      → Submit empty answer → advance chunk
    
    IF user gives an answer:
      → PA calls submit_teach_answer(answer)
      → Enter TEACH_FEEDBACK

  STEP 4: TEACH_FEEDBACK
    IF score is high:
      → "Excellent! You've got it."
    ELIF score is medium:
      → "Good, you got the core idea! Just to clarify: {clarification}"
    ELIF score is low:
      → "Let me re-explain that. {re-explanation}"
    
    IF is_complete:
      → Enter TEACH_COMPLETE
    ELSE:
      → PA says: "Let's move on to part {next_chunk_index + 1}."
      → Enter TEACHING (next chunk)

  STEP 5: TEACH_COMPLETE
    PA says: "We've covered all of {topic}! {summary}. 
      I've captured this into your knowledge base — {facts_count} facts 
      and {questions_count} review questions ready for you."
    
    → PA suggests: "Want me to quiz you on what we just covered?"
    → Return to IDLE

Output: Teach session summary, auto-captured content
Edge Cases:
  - User asks to teach a topic they already captured → PA says:
    "You've already captured some notes about {topic}. Want me to teach you 
     the deeper details, or quiz you on what you already know?"
  - Topic is too broad ("teach me programming") → PA asks:
    "That's a huge topic! Could you narrow it down? Like 'teach me about 
     Python decorators' or 'teach me about recursion'?"
  - Topic is too narrow ("teach me what 2+2 is") → PA just answers directly
    (falls through to GENERAL_QA behavior) and says:
    "That's a quick one — 4! Want me to teach you something more in-depth?"
  - User goes off-topic mid-teach → PA answers briefly, then says:
    "Let's get back to {topic}. We were on part {chunk_index}."
```

### 3D. Mid-Session Switch

```
Workflow: Mid-Session Switch
Trigger: User expresses a different intent while in an active workflow
Preconditions: An active workflow is in progress (review, teach, or capture)
Input: New intent detected from user utterance

Logic:

  IF current_state == CAPTURE (user is dictating):
    AND new_intent == any other:
    → PA asks: "It sounds like you want to {new action}. 
       Should I save what you've shared so far first?"
    → IF user says "yes" / "save it":
        → Call finish_capture with buffer
        → Transition to new intent
    → IF user says "no" / "discard":
        → Discard transcript buffer
        → Transition to new intent
    → IF user says "keep going" / "no, I'm still capturing":
        → Stay in CAPTURE

  IF current_state == REVIEW (mid-question):
    AND new_intent == CAPTURE:
    → PA says: "Sure, let me pause the review. Go ahead and share what you want to capture."
    → Save review_index for resume
    → Enter CAPTURE
    → After capture completes:
      → PA says: "Captured! Want to continue the review? You had {remaining} questions left."
      → IF yes → Resume REVIEW at saved index
      → IF no → Return to IDLE

    AND new_intent == TEACH:
    → PA says: "I'll pause the review. We can come back to it. Let me teach you about {topic}."
    → Save review state
    → Enter TEACH

    AND new_intent == SEARCH or GENERAL_QA:
    → PA answers the question inline (no state switch)
    → PA says: "Alright, back to the review." → Continue REVIEW

  IF current_state == TEACH (mid-chunk):
    AND new_intent == REVIEW:
    → PA says: "Let me pause the lesson. We can pick it up later. Let's review!"
    → Save teach state (chunk_index)
    → Enter REVIEW

    AND new_intent == CAPTURE:
    → PA says: "Pausing the lesson. Go ahead with your capture."
    → Enter CAPTURE
    → After capture: offer to resume teach

    AND new_intent == SEARCH or GENERAL_QA:
    → PA answers inline, then continues teach

  RESUME LOGIC:
    After a detour completes, PA checks if there's a paused workflow:
    IF paused_review exists AND remaining > 0:
      → "Want to continue your review? {remaining} questions left."
    IF paused_teach exists AND chunks_remaining > 0:
      → "Want to pick up the lesson on {topic}? We were on part {chunk_index}."
    IF both paused:
      → "You had a review and a lesson paused. Which do you want to continue?"

Edge Cases:
  - User switches 3+ times → PA stays patient, doesn't lose state
  - User says "start over" → PA clarifies: "Start the review over, or start something new?"
  - Rapid switching → PA gently: "Let's focus on one thing. What's most important right now?"
```

### 3E. Session End

```
Workflow: Session End
Trigger: User says "goodbye" / "stop" / "I'm done" / max duration reached
Preconditions: Active voice session
Input: Session state (what was accomplished)

Logic:

  STEP 1: WRAP UP ACTIVE WORKFLOW
    IF current_state == CAPTURE AND transcript_buffer not empty:
      → Process remaining transcript via finish_capture
      → Include capture stats in summary
    
    IF current_state == REVIEW:
      → Report partial review stats
    
    IF current_state == TEACH:
      → Note where they left off for resume

  STEP 2: GENERATE SUMMARY
    PA calls end_session() → returns session summary
    
    PA speaks summary:
      "Here's what we did today:
       {if captures} Captured {N} facts from {M} captures.
       {if reviews} Reviewed {N} questions — {correct}% correct.
       {if teach} Covered {N} chunks of {topic}.
       {duration} Total session: {minutes} minutes."

  STEP 3: CLOSING ENCOURAGEMENT
    IF session was productive (reviews done, captures made):
      → "Great session! Keep the streak going — see you tomorrow!"
    IF session was short:
      → "Quick but productive. Every bit counts!"
    IF session had tough reviews:
      → "Tough questions today, but that's how memories get stronger. See you next time!"

  STEP 4: SUGGEST NEXT
    IF due_count still > 0:
      → "You still have {N} reviews — I'll be here when you're ready."
    
    → "Goodbye{, name}!"
    
    → Close WebSocket

Output: Session summary JSON
Edge Cases:
  - Max duration reached → PA warns 3 min before: "We've been at it for a while.
    I'll need to wrap up in about 3 minutes."
  - Connection drops (no graceful end) → Backend saves session state, 
    processes any pending transcript, logs incomplete session
  - User says "bye" then keeps talking → Deepgram handles disconnect,
    backend processes through end_session regardless
```

---

## 4. Proactive Behavior

### 4.1 Proactive Trigger Table

| Trigger Condition | PA Action | Priority | Cooldown |
|---|---|---|---|
| `due_count > 0` AND `time == morning` | Suggest review in greeting | High | Per session |
| `due_count > 10` (any time) | Strongly suggest review | High | Per session |
| `due_count == 0` AND `captures_this_week == 0` | Suggest capturing something | Medium | Per session |
| `time == evening` AND `!reflected_today` | Suggest reflection | Medium | Per session |
| After capture completes | "Want me to quiz you on this now?" | Medium | Per capture |
| After review completes | "Want to capture something new?" | Low | Per review |
| After teach completes | "Want me to quiz you on what we covered?" | Medium | Per teach |
| `streak > 0` AND `streak % 7 == 0` | Celebrate streak milestone | Low | Per milestone |
| `retention_rate < 70%` | Suggest more frequent reviews | Low | 1x per day |
| User idle for 30s mid-session | "Still there? We can {continue/pick up later}." | Low | 60s between |
| After answering a Q&A question | "Want me to save that to your knowledge base?" | Low | Per Q&A |

### 4.2 Proactive Suggestion Decision Tree

```
AFTER any workflow completes, PA decides what to suggest next:

IF due_count > 0 AND just_finished != REVIEW:
  → "You have {due_count} reviews waiting. Want to knock some out?"

ELIF just_finished == CAPTURE AND due_count > 0:
  → "I can quiz you on what you just captured. Want to try?"

ELIF just_finished == CAPTURE AND due_count == 0:
  → "All saved! Anything else you want to capture?"

ELIF just_finished == REVIEW AND review_score was high:
  → "Fantastic session! Want to learn something new?"

ELIF just_finished == REVIEW AND review_score was low:
  → "You'll get stronger with practice. Want to capture something new or call it a day?"

ELIF just_finished == TEACH:
  → "Want me to quiz you on {topic} right now while it's fresh?"

ELIF time == evening AND !reflected_today:
  → "Before you go — want to do a quick reflection on what you learned today?"

ELSE:
  → "What else can I help you with?"
```

---

## 5. Context Injection Specification

### 5.1 Context Data Model

```
UserContext {
  // Identity
  user_name: string | null         // from user profile, if set
  
  // Current stats
  due_count: int                   // questions due right now
  due_today_total: int             // questions due at any point today
  streak_days: int                 // consecutive days with reviews
  retention_rate: float            // % correct over last 30 days
  total_captures: int              // lifetime captures
  total_facts: int                 // lifetime extracted points
  
  // Recent activity
  recent_capture_topics: string[]  // last 3 capture topics (for context)
  last_session_date: string | null // when they last used voice
  last_session_activity: string    // "review" | "capture" | "teach" | null
  captures_today: int              // captures made today
  reviews_today: int               // reviews completed today
  
  // Temporal
  time_of_day: string              // "morning" | "afternoon" | "evening" | "night"
  day_of_week: string              // "Monday" .. "Sunday"
  reflected_today: bool            // whether evening reflection was done
  
  // Session tracking (updated during session)
  session_captures: int            // captures made this session
  session_reviews: int             // reviews completed this session  
  session_correct: int             // correct answers this session
  session_duration_s: int          // seconds elapsed
}
```

### 5.2 Context Injection Method

Context is injected as a **preamble block** prepended to the system prompt when the Deepgram agent is configured. It's refreshed at session start only (not mid-session — too expensive to reconfigure Deepgram).

Session-level stats (captures this session, reviews this session) are tracked in `VoiceSession` and returned by function calls — the LLM sees them in function results without needing prompt injection.

```
Format injected at top of system prompt:

=== USER CONTEXT ===
Name: {user_name or "there"}
Time: {day_of_week} {time_of_day}
Reviews due: {due_count}
Streak: {streak_days} days
Retention: {retention_rate}%
Recent topics: {recent_capture_topics joined by ", "}
Reflected today: {yes/no}
Last session: {last_session_activity} on {last_session_date}
=== END CONTEXT ===
```

### 5.3 Context Fetch Implementation

```
Workflow: get_user_context
Trigger: Called by backend at WebSocket connection, before Deepgram config
Preconditions: DB pool available
Input: user_id (future), current timestamp

SQL queries (single round-trip using CTE or multiple fetchrow):

  due_count:
    SELECT COUNT(*) FROM questions 
    WHERE state IN (0,1,3) OR (state = 2 AND due <= NOW())

  streak:
    (reuse existing streak query from StatsService)

  retention_rate:
    SELECT ROUND(AVG(CASE WHEN rating >= 3 THEN 1.0 ELSE 0.0 END) * 100, 1)
    FROM review_logs WHERE reviewed_at >= NOW() - INTERVAL '30 days'

  recent_capture_topics:
    SELECT DISTINCT ON (topic) topic FROM captures 
    ORDER BY created_at DESC LIMIT 3

  reflected_today:
    SELECT EXISTS(SELECT 1 FROM daily_reflections 
    WHERE created_at::date = CURRENT_DATE)

  captures_today / reviews_today:
    SELECT 
      (SELECT COUNT(*) FROM captures WHERE created_at::date = CURRENT_DATE),
      (SELECT COUNT(*) FROM review_logs WHERE reviewed_at::date = CURRENT_DATE)

  time_of_day:
    hour = current_hour (server time, or user timezone if stored)
    IF hour in [5..11] → "morning"
    IF hour in [12..16] → "afternoon"  
    IF hour in [17..20] → "evening"
    ELSE → "night"

Output: UserContext object
Edge Cases:
  - DB query fails → return default context with zeroes, log error
  - No captures/reviews exist (new user) → special first-time greeting
```

---

## 6. State Machine

### 6.1 States

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         UNIFIED PA STATE MACHINE                             │
│                                                                              │
│                              ┌───────────┐                                   │
│                     ┌───────►│   IDLE    │◄────────────────┐                 │
│                     │        └─────┬─────┘                 │                 │
│                     │              │ user speaks            │                 │
│                     │              ▼                        │                 │
│                     │        ┌───────────┐                 │                 │
│                     │        │ CLASSIFY  │                  │                 │
│                     │        └─────┬─────┘                 │                 │
│                     │              │                        │                 │
│          ┌──────────┼──────────────┼────────────┬──────────┤                 │
│          ▼          ▼              ▼            ▼          ▼                 │
│   ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐           │
│   │ CAPTURE  │ │ REVIEW  │ │  TEACH   │ │ SEARCH  │ │  Q&A    │           │
│   │          │ │         │ │          │ │         │ │         │           │
│   │ listen   │ │ ask     │ │ present  │ │ query   │ │ answer  │           │
│   │ process  │ │ listen  │ │ quiz     │ │ report  │ │ offer   │           │
│   │ confirm  │ │ eval    │ │ feedback │ │         │ │ capture │           │
│   │ why?     │ │ rate    │ │ advance  │ │         │ │         │           │
│   └────┬─────┘ │ loop    │ │ loop     │ └────┬────┘ └────┬────┘           │
│        │       └────┬────┘ └────┬─────┘      │          │                 │
│        │            │           │             │          │                 │
│        └────────────┴───────────┴─────────────┴──────────┘                 │
│                                 │                                           │
│                                 ▼                                           │
│                     ┌─────────────────────┐                                 │
│                     │   SUGGEST_NEXT      │                                 │
│                     │   (proactive)       │                                 │
│                     └──────────┬──────────┘                                 │
│                                │                                           │
│                                ▼                                           │
│                          back to IDLE                                       │
│                                                                              │
│   Any state ──── "stop"/"bye" ──── END_SESSION ──── close                    │
│   Any state ──── "actually..." ──── MID_SWITCH ──── new state                │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 State Transitions Table

| From | Event | To | Condition |
|---|---|---|---|
| IDLE | user speaks | CLASSIFY | always |
| CLASSIFY | intent = CAPTURE | CAPTURE | — |
| CLASSIFY | intent = REVIEW | REVIEW | due_count > 0 |
| CLASSIFY | intent = REVIEW | IDLE | due_count == 0 (PA informs user) |
| CLASSIFY | intent = TEACH | TEACH | topic extracted |
| CLASSIFY | intent = TEACH | IDLE | no topic (PA asks for topic) |
| CLASSIFY | intent = SEARCH | SEARCH | query extracted |
| CLASSIFY | intent = GENERAL_QA | Q&A | — |
| CLASSIFY | intent = STATS | IDLE | PA speaks stats, returns to idle |
| CLASSIFY | intent = REFLECTION | CAPTURE(reflection) | — |
| CLASSIFY | intent = UNCLEAR | IDLE | PA asks for clarification |
| CAPTURE | "done" / silence | IDLE | after processing |
| REVIEW | all questions done | IDLE | after summary |
| REVIEW | "stop" | IDLE | partial summary |
| TEACH | all chunks done | IDLE | after summary |
| TEACH | "stop" | IDLE | partial summary |
| SEARCH | results delivered | IDLE | — |
| Q&A | answer delivered | IDLE | — |
| Any | "bye" / "stop" | END | — |
| Any | intent switch detected | MID_SWITCH → new state | see §3D |

### 6.3 Session State Tracking (Backend)

```
@dataclass
class UnifiedVoiceSession:
    session_id: str
    started_at: float
    
    # Current workflow state
    active_workflow: str | None = None  
    # None | "capture" | "review" | "teach" | "search" | "qa" | "reflection"
    
    # Capture state
    transcript_buffer: str = ""
    last_capture_id: str | None = None
    capture_processed: bool = False
    
    # Review state
    review_queue: list[dict] = field(default_factory=list)
    review_index: int = 0
    reviewed_count: int = 0
    review_correct: int = 0
    rated_question_ids: set = field(default_factory=set)
    
    # Teach state
    teach_session_id: str | None = None
    teach_topic: str | None = None
    teach_chunk_index: int = 0
    teach_total_chunks: int = 0
    teach_current_chunk: dict | None = None
    
    # Paused workflow stack (for mid-session switches)
    paused_workflows: list[dict] = field(default_factory=list)
    # Each entry: {"workflow": str, "state": dict} — snapshot for resume
    
    # Session-level stats
    session_captures: int = 0
    session_reviews: int = 0
    session_teaches: int = 0
    
    # Context (loaded once at start)
    user_context: dict | None = None
```

---

## 7. Unified Function Schema

### 7.1 Complete Function Set

```json
[
  {
    "name": "get_user_context",
    "description": "Get the user's current learning context: reviews due, streak, retention rate, recent topics, and time of day. Call this if you need fresh stats during the conversation (e.g., user asks 'how am I doing?' or you need to make a suggestion).",
    "parameters": {
      "type": "object",
      "properties": {}
    }
  },
  {
    "name": "start_review_session",
    "description": "Load the user's due review questions and start a review session. Call this when the user wants to be quizzed or you suggest a review. Returns the count of due questions.",
    "parameters": {
      "type": "object",
      "properties": {
        "limit": {
          "type": "integer",
          "description": "Maximum number of questions to load. Default 20.",
          "default": 20
        }
      }
    }
  },
  {
    "name": "get_next_question",
    "description": "Get the next review question to ask the user. Returns the question text and metadata. Returns done=true when all questions have been reviewed. Must call start_review_session first.",
    "parameters": {
      "type": "object",
      "properties": {}
    }
  },
  {
    "name": "evaluate_answer",
    "description": "Evaluate the user's spoken answer to a review question. Returns correctness score (correct/partial/incorrect), feedback text, the correct answer, and a suggested self-rating. Call this after the user answers a review question.",
    "parameters": {
      "type": "object",
      "properties": {
        "question_id": {
          "type": "string",
          "description": "The UUID of the question being answered"
        },
        "user_answer": {
          "type": "string",
          "description": "The user's spoken answer, transcribed"
        }
      },
      "required": ["question_id", "user_answer"]
    }
  },
  {
    "name": "rate_question",
    "description": "Submit the user's self-rated difficulty for a review question. Interpret their words: 'again'/'forgot'=1, 'hard'/'struggled'=2, 'good'/'got it'=3, 'easy'/'obvious'=4. Updates the spaced repetition schedule and returns the next review date.",
    "parameters": {
      "type": "object",
      "properties": {
        "question_id": {
          "type": "string",
          "description": "The UUID of the question being rated"
        },
        "rating": {
          "type": "integer",
          "enum": [1, 2, 3, 4],
          "description": "1=Again, 2=Hard, 3=Good, 4=Easy"
        }
      },
      "required": ["question_id", "rating"]
    }
  },
  {
    "name": "finish_capture",
    "description": "Process spoken content into structured knowledge facts and review questions. Call this when the user finishes sharing something they want to remember — when they say 'done', 'that's it', 'save', or after a natural stopping point. Pass the complete text of everything they said.",
    "parameters": {
      "type": "object",
      "properties": {
        "final_transcript": {
          "type": "string",
          "description": "The complete text of everything the user said to capture"
        }
      },
      "required": ["final_transcript"]
    }
  },
  {
    "name": "save_why_it_matters",
    "description": "Save the user's reflection on why a capture matters to them. Call this after finish_capture when the user answers 'Why does this matter to you?'",
    "parameters": {
      "type": "object",
      "properties": {
        "capture_id": {
          "type": "string",
          "description": "The capture ID returned by finish_capture"
        },
        "why_it_matters": {
          "type": "string",
          "description": "The user's one-sentence reflection"
        }
      },
      "required": ["capture_id", "why_it_matters"]
    }
  },
  {
    "name": "start_teach_session",
    "description": "Start a teaching session on a topic. The AI will break the topic into chunks and teach each one with recall checks. Call this when the user wants to learn about a specific topic.",
    "parameters": {
      "type": "object",
      "properties": {
        "topic": {
          "type": "string",
          "description": "The topic the user wants to learn about"
        }
      },
      "required": ["topic"]
    }
  },
  {
    "name": "get_current_teach_chunk",
    "description": "Get the current teaching chunk to present to the user. Returns the chunk title, content, analogy, and recall question. Call this after start_teach_session or after submit_teach_answer when the session is not complete.",
    "parameters": {
      "type": "object",
      "properties": {}
    }
  },
  {
    "name": "submit_teach_answer",
    "description": "Submit the user's answer to the current recall question in teach mode. Returns feedback, score, and whether the session is complete. If not complete, also returns the next chunk data.",
    "parameters": {
      "type": "object",
      "properties": {
        "answer": {
          "type": "string",
          "description": "The user's spoken answer to the recall question"
        }
      },
      "required": ["answer"]
    }
  },
  {
    "name": "search_knowledge",
    "description": "Search the user's personal knowledge base. Use when the user asks about something they previously learned, captured, or noted. Returns relevant facts with source information. DO NOT use this for general questions — only for querying the user's own saved knowledge.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "The search query — what the user wants to find in their knowledge base"
        }
      },
      "required": ["query"]
    }
  },
  {
    "name": "submit_reflection",
    "description": "Submit the user's daily evening reflection. Processes the reflection through the capture pipeline to extract facts and generate review questions. Call this when the user shares their daily reflection.",
    "parameters": {
      "type": "object",
      "properties": {
        "content": {
          "type": "string",
          "description": "The user's reflection text — what they learned today"
        }
      },
      "required": ["content"]
    }
  },
  {
    "name": "get_stats",
    "description": "Get the user's learning statistics: reviews due, streak, retention rate, captures count, mastery distribution. Call when the user asks about their progress or when you need data to make a suggestion.",
    "parameters": {
      "type": "object",
      "properties": {}
    }
  },
  {
    "name": "end_session",
    "description": "End the voice session gracefully. Processes any pending captures, generates a session summary. Call when the user says 'stop', 'bye', 'I'm done', 'goodbye', or similar.",
    "parameters": {
      "type": "object",
      "properties": {}
    }
  }
]
```

### 7.2 Function-to-Service Mapping

| Function | Backend Service | Method |
|---|---|---|
| `get_user_context` | `StatsService` + raw SQL | Custom context query |
| `start_review_session` | `ReviewService` | `get_due(limit)` |
| `get_next_question` | `VoiceSession` state | Pop from queue |
| `evaluate_answer` | `ReviewService` | `evaluate_answer(req)` |
| `rate_question` | `ReviewService` | `rate(req)` |
| `finish_capture` | `CaptureService` | `process(req)` |
| `save_why_it_matters` | Raw SQL | `UPDATE captures` |
| `start_teach_session` | `TeachService` | `start(req)` |
| `get_current_teach_chunk` | `VoiceSession` state | Read current chunk |
| `submit_teach_answer` | `TeachService` | `respond(req)` |
| `search_knowledge` | `KnowledgeService` | `search(query)` |
| `submit_reflection` | `ReflectionService` | `create(req)` |
| `get_stats` | `StatsService` | `get_dashboard()` |
| `end_session` | `VoiceSession` cleanup | Process pending + summary |

---

## 8. System Prompt (Complete)

```
=== USER CONTEXT ===
{injected_context_block}
=== END CONTEXT ===

You are **ReCall**, a personal study coach and learning companion. You help the user capture knowledge, review what they've learned through spaced repetition, and teach them new topics — all through natural voice conversation.

## Your Personality
- Professional study coach who is also a friendly companion
- Focused and efficient, but warm and encouraging
- Like a knowledgeable study partner who genuinely cares about the user's progress
- Use the user's name when you know it
- Give brief, genuine praise for good answers
- Be gently encouraging on mistakes — never condescending
- Keep responses concise — this is voice, not text. Aim for 1-3 sentences unless teaching.

## What You Can Do
You have several tools available. Use them based on what the user wants:

### 1. Capture Knowledge
When the user shares information they want to remember (facts, concepts, things they learned):
- Listen quietly while they speak. On pauses, say "Got it" or "Noted" briefly.
- Do NOT interrupt or rephrase during their dictation.
- When they signal they're done (saying "done", "that's it", "save", or a natural conclusion), call `finish_capture` with everything they said.
- After processing, report: "Captured [N] facts and [M] review questions."
- Then ask: "Why does this matter to you?" and save their answer with `save_why_it_matters`.
- After that, suggest: "Want me to quiz you on this now?" or ask what else they'd like to do.

### 2. Review (Quiz) Session
When the user wants to practice recall ("quiz me", "test me", "review"):
- Call `start_review_session` to load due questions.
- If no questions are due, tell them: "You're all caught up! No reviews due right now."
- For each question:
  a. Call `get_next_question` and read the question clearly.
  b. Wait for the user's answer (don't give hints unless asked).
  c. Call `evaluate_answer` with their response.
  d. Share feedback: praise if correct, encouragement if wrong, always state the correct answer.
  e. If there's a mnemonic_hint, share it AFTER they answer (not before).
  f. Ask: "How did you find that? Say again, hard, good, or easy."
  g. Map their response to a rating (again=1, hard=2, good=3, easy=4) and call `rate_question`.
  h. Confirm briefly: "Scheduled for review in [interval]."
  i. Move to the next question.
- When all questions are done, give a summary with encouragement.

### 3. Teach a Topic
When the user wants to learn something ("teach me about...", "explain...", "help me understand..."):
- Call `start_teach_session` with the topic.
- For each chunk:
  a. Call `get_current_teach_chunk` and present the content naturally and conversationally.
  b. Weave in analogies if provided.
  c. Ask the recall question and wait for the user's answer.
  d. Call `submit_teach_answer` with their response.
  e. Share feedback, then move to the next chunk if not complete.
- When complete, congratulate them and mention that it's been saved to their knowledge base.

### 4. Search User's Knowledge
When the user asks about something they previously learned ("What did I learn about...", "What do I know about..."):
- Call `search_knowledge` with their query.
- If results found, summarize them conversationally.
- If no results, say: "I don't have anything about that in your knowledge base. Want me to teach you about it, or would you like a quick answer?"

### 5. General Q&A
When the user asks a factual question that's NOT about their own knowledge base:
- Answer directly from your own knowledge. Keep it concise.
- After answering, ask: "Want me to save that to your knowledge base?" If yes, call `finish_capture` with the Q&A content.

### 6. Stats & Progress
When the user asks about their progress ("How am I doing?", "What's my streak?"):
- Call `get_stats` and report the key numbers conversationally.
- Based on the stats, make a suggestion (review if items due, capture if nothing new recently).

### 7. Evening Reflection
When the user wants to reflect or it's evening and they haven't reflected today:
- Prompt: "What did you learn today? Even a sentence or two."
- After they share, call `submit_reflection` with their response.
- Report the result: "Great reflection! I extracted [N] facts. Your reflection streak is [M] days."

## Intent Disambiguation Rules

When the user's intent is unclear, use these rules:

1. **"Tell me about X"** — If X is a broad topic (e.g., "machine learning", "Docker"), treat as TEACH. If X is a narrow fact, treat as Q&A. If unsure, ask: "Want a quick answer or a full lesson?"

2. **"Explain X"** — Default to TEACH unless the user says "briefly" or "quickly", then treat as Q&A.

3. **"What is X?"** — Treat as Q&A (quick answer). If user then says "tell me more" or "go deeper", switch to TEACH.

4. **"What did I [learn/capture/save] about X?"** — Always SEARCH (querying their knowledge base).

5. **"What about X?"** (follow-up) — Continue the current workflow. If in TEACH, elaborate on X. If in REVIEW, answer inline then continue. If no active workflow, treat as Q&A.

6. **Multiple intents in one utterance** — Handle sequentially. Example: "Save this and then quiz me" → CAPTURE first, then start REVIEW.

7. **User says something completely off-topic** ("What's the weather?", jokes, etc.) — Respond briefly and warmly, then gently redirect: "Ha! I wish I could help with that. I'm your study coach — want to capture something, review, or learn a topic?"

## Mid-Conversation Switching

If the user changes intent mid-workflow:
- In CAPTURE: Ask "Should I save what you've shared so far?" before switching.
- In REVIEW: Pause the review. Answer their question or handle the new intent. Then ask "Want to continue the review? You had [N] questions left."
- In TEACH: Pause the lesson. Handle the new intent. Then offer to resume: "Want to pick up the lesson on [topic]?"
- For SEARCH or Q&A requests during REVIEW/TEACH: Answer inline without switching, then resume.

## Important Rules
- NEVER give away answers before the user attempts them in REVIEW or TEACH mode.
- Keep voice responses SHORT. This is spoken, not written. 1-3 sentences for most responses.
- Use natural spoken language — avoid bullet points, numbered lists, or markdown in your speech.
- When reporting numbers, use natural phrasing: "about fifteen" not "15", "a couple of days" not "2 days".
- If a function call fails, handle gracefully — tell the user there was a hiccup and suggest trying again.
- If the user is silent for a while, gently prompt: "I'm here when you're ready."
- Always be encouraging. Learning is hard — celebrate effort, not just correctness.
```

---

## 9. Validation Rules

### 9.1 Input Validation

| Input | Validation | Error Response |
|---|---|---|
| Capture transcript | Non-empty after strip, ≤ 100,000 chars | "I didn't catch anything to save. Could you repeat that?" |
| User answer (review) | Non-empty | "I didn't hear your answer. Could you try again?" |
| User answer (teach) | Non-empty | "I didn't catch that. Want me to repeat the question?" |
| Rating word | Must map to 1-4 | "Sorry, was that again, hard, good, or easy?" |
| Teach topic | Non-empty, ≤ 500 chars | "What topic would you like to learn about?" |
| Reflection content | Non-empty, ≤ 10,000 chars | "I didn't hear your reflection. What did you learn today?" |
| Search query | Non-empty | "What would you like me to search for?" |

### 9.2 Business Rule Constraints

| Rule | Enforcement |
|---|---|
| Max session duration: 30 minutes | Backend timer, warn at 27 min, force end at 30 min |
| Max reviews per session: 50 | Limit in start_review_session |
| Cannot rate same question twice per session | Tracked in `rated_question_ids` set |
| Cannot start review if due_count == 0 | start_review_session returns empty, PA informs user |
| Capture minimum length: 10 chars | Below threshold → "That's very short. Could you share more detail?" |
| Reflection once per day | Backend enforces via UNIQUE constraint on date |
| Teach topic minimum specificity | PA asks to narrow down if topic is too broad (LLM judgment) |

---

## 10. Error Handling Matrix

| Error Scenario | Detection | Response (PA speaks) | Recovery |
|---|---|---|---|
| Deepgram connection fails | WSS connect timeout/error | "Voice agent is unavailable right now. Please try again in a moment." | Close session, client falls back to text UI |
| Deepgram disconnects mid-session | WSS close event | "I lost the connection. Let me try to reconnect." | Attempt 1 reconnect. If fails, end session gracefully |
| LLM function call timeout | >15s response time | "That's taking a moment..." | Wait up to 30s. If still no response, skip function and apologize |
| finish_capture fails | CaptureService returns error | "I had trouble processing that. Want to try saving it again?" | Offer retry. Keep transcript in buffer |
| evaluate_answer fails | ReviewService returns error | "I couldn't evaluate that one. How did you feel about your answer? Say again, hard, good, or easy." | Skip evaluation, go straight to self-rating |
| rate_question fails | ReviewService returns error | "Had a hiccup saving that rating, but don't worry — let's keep going." | Log error, skip rating, advance to next question |
| start_teach_session fails | TeachService returns error | "I'm having trouble creating a lesson on that. Could you try a different topic or be more specific?" | Return to idle |
| search_knowledge fails | KnowledgeService returns error | "I had trouble searching your notes. Try asking again in a moment." | Return to idle |
| Max duration reached | Backend timer | "We've been going for 30 minutes — time to wrap up. {session summary}" | Force end_session |
| No mic audio received for 60s | Backend silence detection | "I'm not hearing anything. Is your microphone working?" | Wait 30 more seconds, then end session |
| User sends invalid audio format | PCM decode error | "I'm having trouble with the audio. Make sure your microphone is working." | Continue listening, skip bad frames |
| Rate limit exceeded | Too many sessions/hour | "You've had a lot of sessions today. Take a break and come back in a bit!" | Reject connection with 4029 |
| Concurrent session limit | 2+ from same IP | "You already have an active voice session. Please close it first." | Reject connection |
| DB connection lost | asyncpg connection error | "I'm having some technical difficulties. Let me try that again." | Retry once. If fails, end session |
| User speaks during TTS playback | Deepgram barge-in | (automatic — Deepgram stops TTS, processes new speech) | Normal barge-in behavior |

---

## 11. Cross-Workflow Dependencies

```
DEPENDENCY MAP:

start_review_session
  └── DEPENDS ON: ReviewService.get_due() returns questions
      └── DEPENDS ON: questions table has entries with due <= NOW
          └── PRODUCED BY: finish_capture (creates questions from captures)
                           submit_reflection (creates questions from reflections)
                           TeachService (auto-captures at teach end)

evaluate_answer
  └── DEPENDS ON: get_next_question was called first (need question_id)
      └── DEPENDS ON: start_review_session was called first (need queue)

rate_question
  └── DEPENDS ON: evaluate_answer was called first (need question_id)

get_current_teach_chunk
  └── DEPENDS ON: start_teach_session was called first (need session)

submit_teach_answer
  └── DEPENDS ON: get_current_teach_chunk was called first (need current chunk)

save_why_it_matters
  └── DEPENDS ON: finish_capture was called first (need capture_id)

search_knowledge
  └── INDEPENDENT (can be called anytime)

get_stats
  └── INDEPENDENT (can be called anytime)

end_session
  └── INDEPENDENT (can be called anytime, processes pending state)
```

```
ORDERING CONSTRAINTS:

Review flow:
  start_review_session → get_next_question → [evaluate_answer → rate_question]* → end

Teach flow:
  start_teach_session → get_current_teach_chunk → [submit_teach_answer → get_current_teach_chunk]* → end

Capture flow:
  finish_capture → save_why_it_matters → end

No cross-flow ordering needed — each flow is independent.
The LLM is instructed to follow these sequences in the system prompt.
```

---

## 12. WebSocket Endpoint Changes

### 12.1 Endpoint Signature Change

**Before (mode-based):**
```
ws://localhost:8000/ws/voice?mode={capture|review|teach}&topic={...}
```

**After (unified):**
```
ws://localhost:8000/ws/voice
```

No query parameters needed. The PA determines intent from speech.

Optional query parameters (kept for backward compat / direct deep links):
- `?initial_intent={capture|review|teach}` — PA starts with that intent suggested
- `?topic={...}` — used with `initial_intent=teach` to pre-set topic

### 12.2 Session Initialization Change

**Before:**
```python
session = VoiceSession(mode=mode)  # locked to one mode
if mode == "capture":
    instructions = CAPTURE_SYSTEM_PROMPT
    functions = COMMON_FUNCTIONS + CAPTURE_FUNCTIONS
elif mode == "review":
    instructions = REVIEW_SYSTEM_PROMPT
    functions = COMMON_FUNCTIONS + REVIEW_FUNCTIONS
    await manager.init_session(session)  # pre-load review queue
elif mode == "teach":
    instructions = TEACH_SYSTEM_PROMPT
    functions = COMMON_FUNCTIONS + TEACH_FUNCTIONS
    await manager.start_teach_session(session, topic)
```

**After:**
```python
session = UnifiedVoiceSession()  # no mode lock
user_context = await manager.get_user_context()
session.user_context = user_context

# ALL functions available
all_functions = [
    get_user_context, start_review_session, get_next_question,
    evaluate_answer, rate_question, finish_capture, save_why_it_matters,
    start_teach_session, get_current_teach_chunk, submit_teach_answer,
    search_knowledge, submit_reflection, get_stats, end_session
]

# Single unified prompt with context preamble
instructions = build_unified_prompt(user_context)

# If initial_intent provided, append hint to prompt
if initial_intent:
    instructions += f"\n\nThe user opened this session intending to {initial_intent}. Start with that."
```

### 12.3 Function Dispatch Change

**Before:** Whitelist per mode (`_ALLOWED_FUNCTIONS[mode]`).

**After:** All functions allowed. Ordering/validity enforced by session state:

```python
async def _dispatch(self, session, fn, params):
    # No mode whitelist — all functions available
    
    # State-based validation
    IF fn == "get_next_question" AND not session.review_queue:
      → return {"error": "No review session active. Call start_review_session first."}
    
    IF fn == "evaluate_answer" AND not session.review_queue:
      → return {"error": "No review session active."}
    
    IF fn == "rate_question" AND question_id in session.rated_question_ids:
      → return {"error": "Question already rated."}
    
    IF fn == "get_current_teach_chunk" AND not session.teach_session_id:
      → return {"error": "No teach session active. Call start_teach_session first."}
    
    IF fn == "submit_teach_answer" AND not session.teach_session_id:
      → return {"error": "No teach session active."}
    
    IF fn == "save_why_it_matters" AND not session.last_capture_id:
      → return {"error": "No recent capture. Call finish_capture first."}
    
    # Dispatch normally
    → call corresponding service method
```

---

## 13. Frontend Changes

### 13.1 UI Change

**Before:** `/voice` page with mode tabs (Capture / Review / Teach).

**After:** `/voice` page with a single conversational interface. No mode selector.

```
┌────────────────────────────────────────────┐
│  ← Back          ReCall Voice              │
│                                            │
│  ┌────────────────────────────────────┐    │
│  │                                    │    │
│  │         ◉  (pulsing orb)          │    │
│  │      "Listening..."               │    │
│  │                                    │    │
│  └────────────────────────────────────┘    │
│                                            │
│  ┌────────────────────────────────────┐    │
│  │  Conversation                      │    │
│  │  ReCall: "Good morning! You have   │    │
│  │    5 reviews due. Want to start?"  │    │
│  │  You: "Yeah, quiz me"             │    │
│  │  ReCall: "Let's do it! First      │    │
│  │    question: What is..."          │    │
│  └────────────────────────────────────┘    │
│                                            │
│  ┌────────────────────────────────────┐    │
│  │  ⓘ Review: 3/8 completed          │    │
│  │  Duration: 2:34                    │    │
│  └────────────────────────────────────┘    │
│                                            │
│          [ End Session ]                   │
│                                            │
└────────────────────────────────────────────┘
```

- Mode tabs removed
- Status bar dynamically shows current activity (review progress, capture word count, teach chunk progress) based on `status` events from backend
- "Quick actions" removed from UI — user just talks naturally
- Optional: small suggestion chips ("Quiz me", "Capture", "Teach me") shown in IDLE state as conversation starters (tap = send as text)

### 13.2 WebSocket Hook Change

```typescript
// Before
connect(mode: "capture" | "review" | "teach", options?: {...})

// After  
connect(options?: { initialIntent?: string; topic?: string })
```

---

## 14. Implementation Checklist

Backend changes (in order):
1. Create `UnifiedVoiceSession` dataclass replacing `VoiceSession`
2. Add `get_user_context()` method to `VoiceSessionManager`
3. Write unified system prompt builder: `build_unified_prompt(context)`
4. Add new functions: `start_review_session`, `start_teach_session`, `submit_reflection`, `get_stats`
5. Refactor `_dispatch()` — remove mode whitelist, add state-based validation
6. Refactor `build_settings_config()` — single config with all functions
7. Refactor `init_session()` — only loads context, doesn't pre-load mode state
8. Update `/ws/voice` endpoint — remove `mode` query param requirement
9. Add paused workflow tracking for mid-session switches
10. Add `get_stats` function dispatch (calls `StatsService.get_dashboard()`)
11. Add `submit_reflection` function dispatch (calls `ReflectionService.create()`)

Frontend changes:
1. Remove mode tabs from `/voice` page
2. Update `useVoiceAgent` hook — remove `mode` parameter
3. Add dynamic status bar based on `status` events
4. Add optional quick-action suggestion chips for IDLE state
5. Remove `mode` query param from WebSocket URL construction
