## Phase 5 E2E Tests
## Tests: Push Notifications, Method of Loci, Knowledge Graph, Analytics

$base = "http://localhost:8001"
$pass = 0
$fail = 0
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
Write-Host "  ReCall MVP - Phase 5 E2E Tests" -ForegroundColor White
Write-Host "========================================`n" -ForegroundColor White

# ─── 1. PUSH NOTIFICATIONS ───
Write-Host "[1/4] PUSH NOTIFICATIONS" -ForegroundColor Cyan

Test-Endpoint "POST /api/notifications/subscribe" {
    $body = @{
        endpoint = "https://fcm.googleapis.com/fcm/send/test-endpoint-$(Get-Random)"
        keys = @{
            p256dh = "BMpNHGqWfFV8GFZdqFwvz_TEST_KEY_DATA"
            auth = "kdrLQj3IeYP_TEST_AUTH"
        }
    } | ConvertTo-Json -Depth 3
    $r = Invoke-RestMethod "$base/api/notifications/subscribe" -Method POST -Body $body -ContentType "application/json"
    if (-not $r.id) { throw "No subscription ID returned" }
    $script:subId = $r.id
    "subscription_id=$($r.id) success=$($r.success)"
}

Test-Endpoint "GET /api/notifications/settings" {
    $r = Invoke-RestMethod "$base/api/notifications/settings"
    "enabled=$($r.enabled) review_reminder=$($r.review_reminder) daily_reflection=$($r.daily_reflection) review_time=$($r.review_time)"
}

Test-Endpoint "PATCH /api/notifications/settings" {
    $body = @{
        enabled = $true
        review_reminder = $true
        daily_reflection = $true
        review_time = "09:00"
    } | ConvertTo-Json
    $r = Invoke-RestMethod "$base/api/notifications/settings" -Method PATCH -Body $body -ContentType "application/json"
    "enabled=$($r.enabled) review_reminder=$($r.review_reminder) review_time=$($r.review_time)"
}

Test-Endpoint "POST /api/notifications/test" {
    $r = Invoke-RestMethod "$base/api/notifications/test" -Method POST
    "sent=$($r.sent) message=$($r.message)"
}

# ─── 2. METHOD OF LOCI ───
Write-Host "`n[2/4] METHOD OF LOCI" -ForegroundColor Cyan

Test-Endpoint "POST /api/loci/session" {
    $body = @{
        description = "My childhood home - starting from the front door"
        num_loci = 5
    } | ConvertTo-Json
    $r = Invoke-RestMethod "$base/api/loci/session" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 60
    if (-not $r.session_id) { throw "No session_id returned" }
    $script:lociSessionId = $r.session_id
    $preview = if ($r.walkthrough) { $r.walkthrough.Substring(0, [Math]::Min(80, $r.walkthrough.Length)) } else { 'N/A' }
    "session_id=$($r.session_id) loci_count=$($r.loci.Count) walkthrough=$preview..."
}

if ($script:lociSessionId) {
    Test-Endpoint "GET /api/loci/session/{id}" {
        $r = Invoke-RestMethod "$base/api/loci/session/$($script:lociSessionId)"
        if (-not $r.session_id) { throw "No session data" }
        "session_id=$($r.session_id) description=$($r.description) loci_count=$($r.loci.Count) completed=$($r.completed)"
    }

    Test-Endpoint "POST /api/loci/session/{id}/recall" {
        $body = @{
            recalled_items = @("Item at location 1", "Item at location 2", "Item at location 3")
        } | ConvertTo-Json
        $r = Invoke-RestMethod "$base/api/loci/session/$($script:lociSessionId)/recall" -Method POST -Body $body -ContentType "application/json" -TimeoutSec 30
        if ($null -eq $r.score) { throw "Missing score field" }
        $preview = if ($r.feedback) { $r.feedback.Substring(0, [Math]::Min(80, $r.feedback.Length)) } else { 'N/A' }
        "score=$($r.score) capture_created=$($r.capture_created) feedback=$preview..."
    }
} else {
    Write-Host "  SKIP  GET /api/loci/session/{id} - no session" -ForegroundColor Yellow
    Write-Host "  SKIP  POST /api/loci/session/{id}/recall - no session" -ForegroundColor Yellow
}

# ─── 3. KNOWLEDGE GRAPH ───
Write-Host "`n[3/4] KNOWLEDGE GRAPH" -ForegroundColor Cyan

Test-Endpoint "GET /api/knowledge/graph/data?limit=50" {
    $r = Invoke-RestMethod "$base/api/knowledge/graph/data?limit=50"
    if (-not $r.nodes -or -not $r.edges) { throw "Missing nodes or edges" }
    "nodes=$($r.nodes.Count) edges=$($r.edges.Count)"
}

Test-Endpoint "GET /api/knowledge/graph/data?limit=100&min_similarity=0.6" {
    $r = Invoke-RestMethod "$base/api/knowledge/graph/data?limit=100&min_similarity=0.6"
    "nodes=$($r.nodes.Count) edges=$($r.edges.Count) (filtered by similarity)"
}

# ─── 4. ANALYTICS ───
Write-Host "`n[4/4] ANALYTICS" -ForegroundColor Cyan

Test-Endpoint "GET /api/stats/analytics" {
    $r = Invoke-RestMethod "$base/api/stats/analytics"
    "comprehensive analytics returned"
}

Test-Endpoint "GET /api/stats/analytics/retention" {
    $r = Invoke-RestMethod "$base/api/stats/analytics/retention?weeks=4"
    if (-not $r.data) { throw "Missing data field" }
    "weeks=$($r.data.Count)"
}

Test-Endpoint "GET /api/stats/analytics/weak-areas" {
    $r = Invoke-RestMethod "$base/api/stats/analytics/weak-areas?limit=10"
    if (-not $r.questions) { throw "Missing questions field" }
    "weak_questions=$($r.questions.Count)"
    if ($r.questions.Count -gt 0) {
        $first = $r.questions[0]
        "first: id=$($first.question_id) failures=$($first.failure_count)"
    }
}

Test-Endpoint "GET /api/stats/analytics/activity" {
    $r = Invoke-RestMethod "$base/api/stats/analytics/activity?days=30"
    if (-not $r.data) { throw "Missing data field" }
    "days=$($r.data.Count)"
}

# ─── SUMMARY ───
Write-Host "`n========================================" -ForegroundColor White
Write-Host "  PHASE 5 RESULTS SUMMARY" -ForegroundColor White
Write-Host "========================================" -ForegroundColor White
Write-Host "  PASSED: $pass" -ForegroundColor Green
Write-Host "  FAILED: $fail" -ForegroundColor $(if ($fail -gt 0) { "Red" } else { "Green" })
Write-Host "  TOTAL:  $($pass + $fail)" -ForegroundColor White
Write-Host "========================================`n" -ForegroundColor White

if ($fail -gt 0) {
    Write-Host "FAILED TESTS:" -ForegroundColor Red
    $results | Where-Object { $_.Status -eq "FAIL" } | ForEach-Object {
        Write-Host "  - $($_.Test): $($_.Detail)" -ForegroundColor Red
    }
    Write-Host ""
}

# Return exit code based on results
exit $fail
