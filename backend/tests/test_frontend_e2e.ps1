## Frontend E2E API Test Script
## Tests every API endpoint the frontend calls

$base = "http://localhost:8001"
$pass = 0
$fail = 0
$skip = 0
$results = @()

function Test-Endpoint {
    param($Name, $ScriptBlock)
    try {
        $result = & $ScriptBlock
        $script:pass++
        $script:results += [PSCustomObject]@{Test=$Name; Status="PASS"; Detail=$result}
        Write-Host "  PASS  $Name" -ForegroundColor Green
        if ($result) { Write-Host "        $result" -ForegroundColor DarkGray }
        return $true
    } catch {
        $script:fail++
        $errMsg = $_.Exception.Message
        $script:results += [PSCustomObject]@{Test=$Name; Status="FAIL"; Detail=$errMsg}
        Write-Host "  FAIL  $Name" -ForegroundColor Red
        Write-Host "        $errMsg" -ForegroundColor DarkRed
        return $false
    }
}

Write-Host "`n========================================" -ForegroundColor White
Write-Host "  ReCall MVP - Frontend E2E API Tests" -ForegroundColor White
Write-Host "========================================`n" -ForegroundColor White

# ─── 1. DASHBOARD ───
Write-Host "[1/9] DASHBOARD" -ForegroundColor Cyan
Test-Endpoint "GET /api/stats/dashboard" {
    $r = Invoke-RestMethod "$base/api/stats/dashboard"
    if ($null -eq $r.total_captures -or $null -eq $r.total_questions -or $null -eq $r.due_today) { throw "Missing fields" }
    "captures=$($r.total_captures) questions=$($r.total_questions) due=$($r.due_today) reviews=$($r.reviews_today) streak=$($r.streak_days) retention=$($r.retention_rate)"
}

# ─── 2. CAPTURE ───
Write-Host "`n[2/9] CAPTURE" -ForegroundColor Cyan

# Text capture
Test-Endpoint "POST /api/captures/ (text)" {
    $body = @{
        raw_text = "Photosynthesis is the process by which plants convert light energy into chemical energy. Chlorophyll in the leaves absorbs sunlight. Carbon dioxide and water are converted into glucose and oxygen."
        source_type = "text"
        why_it_matters = "Understanding how plants produce energy is foundational to biology."
    } | ConvertTo-Json
    $r = Invoke-RestMethod "$base/api/captures/" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 60
    if (-not $r.capture_id) { throw "No capture ID returned" }
    $script:testCaptureId = $r.capture_id
    "id=$($r.capture_id) facts=$($r.facts_count) questions=$($r.questions_count) status=$($r.status)"
}

# URL capture
Test-Endpoint "POST /api/captures/url" {
    $body = @{ url = "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Functions" } | ConvertTo-Json
    $r = Invoke-RestMethod "$base/api/captures/url" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 60
    if (-not $r.capture_id) { throw "No capture ID returned" }
    $script:urlCaptureId = $r.capture_id
    "id=$($r.capture_id) facts=$($r.facts_count) questions=$($r.questions_count) status=$($r.status)"
}

# ─── 3. HISTORY ───
Write-Host "`n[3/9] HISTORY" -ForegroundColor Cyan

Test-Endpoint "GET /api/captures/?limit=5&offset=0" {
    $r = Invoke-RestMethod "$base/api/captures/?limit=5&offset=0"
    if ($r.Count -eq 0) { throw "No captures returned" }
    $script:firstCaptureId = $r[0].id
    "count=$($r.Count) first_id=$($r[0].id) first_title=$($r[0].title)"
}

# ─── 4. CAPTURE DETAIL ───
Write-Host "`n[4/9] CAPTURE DETAIL" -ForegroundColor Cyan

if ($script:firstCaptureId) {
    Test-Endpoint "GET /api/captures/{id}" {
        $r = Invoke-RestMethod "$base/api/captures/$($script:firstCaptureId)"
        if (-not $r.id) { throw "No detail returned" }
        "id=$($r.id) title=$($r.title) facts=$($r.extracted_points.Count) questions=$($r.questions.Count) source=$($r.source)"
    }
} else {
    Write-Host "  SKIP  GET /api/captures/{id} - no capture available" -ForegroundColor Yellow
    $skip++
}

# ─── 5. REVIEW ───
Write-Host "`n[5/9] REVIEW" -ForegroundColor Cyan

Test-Endpoint "GET /api/reviews/due?limit=20" {
    $r = Invoke-RestMethod "$base/api/reviews/due?limit=20"
    $questions = $r.questions
    $totalDue = $r.total_due
    "due_count=$totalDue questions_returned=$($questions.Count)"
    if ($questions.Count -gt 0) {
        $script:testQuestionId = $questions[0].question_id
        $script:testQuestionText = $questions[0].question_text
        "first_q_id=$($questions[0].question_id) text=$($questions[0].question_text)"
    }
}

if ($script:testQuestionId) {
    Test-Endpoint "POST /api/reviews/evaluate" {
        $body = @{
            question_id = $script:testQuestionId
            question_text = $script:testQuestionText
            user_answer = "I think it involves converting sunlight into energy using chlorophyll in the leaves."
        } | ConvertTo-Json
        $r = Invoke-RestMethod "$base/api/reviews/evaluate" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 30
        if (-not $r.score) { throw "Missing score field" }
        $preview = if ($r.feedback) { $r.feedback.Substring(0, [Math]::Min(80, $r.feedback.Length)) } else { 'N/A' }
        "score=$($r.score) suggested_rating=$($r.suggested_rating) feedback=$preview..."
    }

    Test-Endpoint "POST /api/reviews/rate" {
        $body = @{
            question_id = $script:testQuestionId
            rating = 3
        } | ConvertTo-Json
        $r = Invoke-RestMethod "$base/api/reviews/rate" -Method POST -Body $body -ContentType "application/json"
        if (-not $r.next_due) { throw "Missing next_due" }
        "next_due=$($r.next_due) interval=$($r.interval_days) state=$($r.state_label)"
    }
} else {
    Write-Host "  SKIP  POST /api/reviews/evaluate - no due questions" -ForegroundColor Yellow
    Write-Host "  SKIP  POST /api/reviews/rate - no due questions" -ForegroundColor Yellow
    $skip += 2
}

# ─── 6. KNOWLEDGE SEARCH ───
Write-Host "`n[6/9] KNOWLEDGE SEARCH" -ForegroundColor Cyan

Test-Endpoint "POST /api/knowledge/search" {
    $body = @{
        query = "photosynthesis"
        limit = 5
    } | ConvertTo-Json
    $r = Invoke-RestMethod "$base/api/knowledge/search" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 20
    "results=$($r.Count)"
    if ($r.Count -gt 0) {
        "top_result: similarity=$($r[0].similarity) text=$($r[0].content.Substring(0, [Math]::Min(60, $r[0].content.Length)))..."
    }
}

# ─── 7. TEACH MODE ───
Write-Host "`n[7/9] TEACH MODE" -ForegroundColor Cyan

Test-Endpoint "POST /api/teach/start" {
    $body = @{ topic = "How the solar system formed" } | ConvertTo-Json
    $r = Invoke-RestMethod "$base/api/teach/start" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 60
    if (-not $r.session_id) { throw "No session_id" }
    $script:teachSessionId = $r.session_id
    $preview = if ($r.chunk_content) { $r.chunk_content.Substring(0, [Math]::Min(60, $r.chunk_content.Length)) } else { 'N/A' }
    "session_id=$($r.session_id) chunks=$($r.total_chunks) preview=$preview..."
}

if ($script:teachSessionId) {
    Test-Endpoint "POST /api/teach/respond" {
        $body = @{
            session_id = $script:teachSessionId
            answer = "Plants use chlorophyll to absorb sunlight and convert CO2 and water into glucose."
        } | ConvertTo-Json
        $r = Invoke-RestMethod "$base/api/teach/respond" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 60
        if (-not $r.score) { throw "Missing score field" }
        $preview = if ($r.feedback) { $r.feedback.Substring(0, [Math]::Min(60, $r.feedback.Length)) } else { 'N/A' }
        "score=$($r.score) is_complete=$($r.is_complete) feedback=$preview..."
    }

    Test-Endpoint "GET /api/teach/{sessionId}" {
        $r = Invoke-RestMethod "$base/api/teach/$($script:teachSessionId)"
        if (-not $r.session_id) { throw "No session data" }
        "session_id=$($r.session_id) topic=$($r.topic) status=$($r.status)"
    }
} else {
    Write-Host "  SKIP  POST /api/teach/respond - no session" -ForegroundColor Yellow
    Write-Host "  SKIP  GET /api/teach/{id} - no session" -ForegroundColor Yellow
    $skip += 2
}

# ─── 8. REFLECTION ───
Write-Host "`n[8/9] REFLECTION" -ForegroundColor Cyan

Test-Endpoint "GET /api/reflections/status" {
    $r = Invoke-RestMethod "$base/api/reflections/status"
    "completed_today=$($r.completed_today) streak=$($r.streak_days)"
}

Test-Endpoint "GET /api/reflections/?limit=5" {
    $r = Invoke-RestMethod "$base/api/reflections/?limit=5&offset=0"
    "count=$($r.Count)"
}

Test-Endpoint "POST /api/reflections/" {
    $body = @{
        content = "Today I learned about photosynthesis and how plants convert light into chemical energy. The concept of chlorophyll absorption was particularly interesting."
    } | ConvertTo-Json
    try {
        $r = Invoke-RestMethod "$base/api/reflections/" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 30
        if (-not $r.id) { throw "No reflection ID" }
        $preview = if ($r.ai_insight) { $r.ai_insight.Substring(0, [Math]::Min(80, $r.ai_insight.Length)) } else { 'N/A' }
        "id=$($r.id) insight=$preview..."
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -eq 409) {
            # 409 = already reflected today — endpoint works correctly
            "Already reflected today (409) - endpoint works"
        } else {
            throw
        }
    }
}

# ─── 9. VOICE AGENT ───
Write-Host "`n[9/9] VOICE AGENT" -ForegroundColor Cyan

Test-Endpoint "GET /api/voice/status" {
    $r = Invoke-RestMethod "$base/api/voice/status"
    "enabled=$($r.enabled) available=$($r.available)"
}

Test-Endpoint "POST /api/voice/tts" {
    $body = @{ text = "Hello, this is a test of the text to speech endpoint." } | ConvertTo-Json
    $r = Invoke-WebRequest "$base/api/voice/tts" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 15 -UseBasicParsing
    if ($r.StatusCode -ne 200) { throw "Status $($r.StatusCode)" }
    "status=200 content_type=$($r.Headers['Content-Type']) size=$($r.Content.Length) bytes"
}

# ─── SUMMARY ───
Write-Host "`n========================================" -ForegroundColor White
Write-Host "  RESULTS SUMMARY" -ForegroundColor White
Write-Host "========================================" -ForegroundColor White
Write-Host "  PASSED: $pass" -ForegroundColor Green
Write-Host "  FAILED: $fail" -ForegroundColor $(if ($fail -gt 0) { "Red" } else { "Green" })
Write-Host "  SKIPPED: $skip" -ForegroundColor $(if ($skip -gt 0) { "Yellow" } else { "Green" })
Write-Host "  TOTAL:  $($pass + $fail + $skip)" -ForegroundColor White
Write-Host "========================================`n" -ForegroundColor White

if ($fail -gt 0) {
    Write-Host "FAILED TESTS:" -ForegroundColor Red
    $results | Where-Object { $_.Status -eq "FAIL" } | ForEach-Object {
        Write-Host "  - $($_.Test): $($_.Detail)" -ForegroundColor Red
    }
}
