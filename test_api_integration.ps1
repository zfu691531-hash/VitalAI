# VitalAI API Integration Test Script
# This script tests all API endpoints

$ErrorActionPreference = "Continue"
$BaseUrl = "http://127.0.0.1:8124"
$TestResults = @()
$PassCount = 0
$FailCount = 0

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Url,
        [object]$Body = $null,
        [scriptblock]$Validate = $null
    )
    
    $result = @{
        Name = $Name
        Method = $Method
        Url = $Url
        Status = "UNKNOWN"
        Response = $null
        Error = $null
    }
    
    try {
        if ($Method -eq "GET") {
            $response = Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec 10
        } else {
            $jsonBody = $Body | ConvertTo-Json -Depth 10
            $response = Invoke-RestMethod -Method Post -Uri $Url -ContentType "application/json" -Body $jsonBody -TimeoutSec 10
        }
        
        $result.Response = $response
        
        if ($Validate) {
            $validationResult = & $Validate $response
            if ($validationResult) {
                $result.Status = "PASS"
                $script:PassCount++
            } else {
                $result.Status = "FAIL"
                $script:FailCount++
            }
        } else {
            $result.Status = "PASS"
            $script:PassCount++
        }
    } catch {
        $result.Status = "FAIL"
        $result.Error = $_.Exception.Message
        $script:FailCount++
    }
    
    $script:TestResults += $result
    return $result
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VitalAI API Integration Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Health Check
Write-Host "[1/12] Testing Health Check..." -ForegroundColor Yellow
Test-Endpoint -Name "Health Check" -Method "GET" -Url "$BaseUrl/vitalai/health" -Validate {
    param($r)
    return $r.status -eq "ok" -and $r.module -eq "VitalAI"
}

# Test 2: Health Alert Flow
Write-Host "[2/12] Testing Health Alert Flow..." -ForegroundColor Yellow
Test-Endpoint -Name "Health Alert Flow" -Method "POST" -Url "$BaseUrl/vitalai/flows/health-alert" -Body @{
    source_agent = "test-script"
    trace_id = "test-health-001"
    user_id = "elder-test-001"
    risk_level = "critical"
} -Validate {
    param($r)
    return $r.accepted -eq $true
}

# Test 3: Daily Life Checkin
Write-Host "[3/12] Testing Daily Life Checkin..." -ForegroundColor Yellow
Test-Endpoint -Name "Daily Life Checkin" -Method "POST" -Url "$BaseUrl/vitalai/flows/daily-life-checkin" -Body @{
    source_agent = "test-script"
    trace_id = "test-daily-001"
    user_id = "elder-test-001"
    need = "shopping"
    urgency = "high"
} -Validate {
    param($r)
    return $r.accepted -eq $true
}

# Test 4: Mental Care Checkin
Write-Host "[4/12] Testing Mental Care Checkin..." -ForegroundColor Yellow
Test-Endpoint -Name "Mental Care Checkin" -Method "POST" -Url "$BaseUrl/vitalai/flows/mental-care-checkin" -Body @{
    source_agent = "test-script"
    trace_id = "test-mental-001"
    user_id = "elder-test-001"
    mood_signal = "lonely"
    support_need = "companionship"
} -Validate {
    param($r)
    return $r.accepted -eq $true
}

# Test 5: Profile Memory Write
Write-Host "[5/12] Testing Profile Memory Write..." -ForegroundColor Yellow
Test-Endpoint -Name "Profile Memory Write" -Method "POST" -Url "$BaseUrl/vitalai/flows/profile-memory" -Body @{
    source_agent = "test-script"
    trace_id = "test-memory-write-001"
    user_id = "elder-test-001"
    memory_key = "favorite_food"
    memory_value = "dumplings"
} -Validate {
    param($r)
    return $r.accepted -eq $true
}

# Test 6: Profile Memory Read
Write-Host "[6/12] Testing Profile Memory Read..." -ForegroundColor Yellow
Test-Endpoint -Name "Profile Memory Read" -Method "GET" -Url "$BaseUrl/vitalai/flows/profile-memory/elder-test-001?source_agent=test-script&trace_id=test-read-001" -Validate {
    param($r)
    return $r.user_id -eq "elder-test-001"
}

# Test 7: User Interaction - Memory Update
Write-Host "[7/12] Testing User Interaction (Memory Update)..." -ForegroundColor Yellow
Test-Endpoint -Name "User Interaction Memory Update" -Method "POST" -Url "$BaseUrl/vitalai/interactions" -Body @{
    user_id = "elder-test-002"
    channel = "test"
    message = "I like jasmine tea"
    event_type = "profile_memory_update"
    trace_id = "test-interaction-001"
    context = @{
        memory_key = "favorite_drink"
        memory_value = "jasmine_tea"
    }
} -Validate {
    param($r)
    return $r.accepted -eq $true
}

# Test 8: User Interaction - Memory Query
Write-Host "[8/12] Testing User Interaction (Memory Query)..." -ForegroundColor Yellow
Test-Endpoint -Name "User Interaction Memory Query" -Method "POST" -Url "$BaseUrl/vitalai/interactions" -Body @{
    user_id = "elder-test-002"
    channel = "test"
    message = "What do you remember?"
    event_type = "profile_memory_query"
    trace_id = "test-interaction-002"
} -Validate {
    param($r)
    return $r.accepted -eq $true
}

# Test 9: Policy Query - Single Role
Write-Host "[9/12] Testing Policy Query (Single Role)..." -ForegroundColor Yellow
Test-Endpoint -Name "Policy Query Single Role" -Method "GET" -Url "$BaseUrl/vitalai/flows/policies/api" -Validate {
    param($r)
    return $r.role -eq "api"
}

# Test 10: Policy Query - Matrix
Write-Host "[10/12] Testing Policy Query (Matrix)..." -ForegroundColor Yellow
Test-Endpoint -Name "Policy Query Matrix" -Method "GET" -Url "$BaseUrl/vitalai/flows/policies" -Validate {
    param($r)
    return $r -ne $null
}

# Test 11: Admin Without Token (Should Fail)
Write-Host "[11/12] Testing Admin Without Token (Should Fail)..." -ForegroundColor Yellow
$adminTestResult = @{
    Name = "Admin Without Token"
    Method = "POST"
    Url = "$BaseUrl/vitalai/admin/runtime-diagnostics/api"
    Status = "UNKNOWN"
    Response = $null
    Error = $null
}
try {
    $response = Invoke-RestMethod -Method Post -Uri "$BaseUrl/vitalai/admin/runtime-diagnostics/api" -TimeoutSec 10
    $adminTestResult.Status = "FAIL"
    $adminTestResult.Error = "Should have been rejected but succeeded"
    $FailCount++
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 403) {
        $adminTestResult.Status = "PASS"
        $PassCount++
        $adminTestResult.Error = "Correctly rejected with 403"
    } else {
        $adminTestResult.Status = "FAIL"
        $adminTestResult.Error = "Wrong error: $($_.Exception.Message)"
        $FailCount++
    }
}
$TestResults += $adminTestResult

# Test 12: User Interaction - Health Event
Write-Host "[12/12] Testing User Interaction (Health Event)..." -ForegroundColor Yellow
Test-Endpoint -Name "User Interaction Health Event" -Method "POST" -Url "$BaseUrl/vitalai/interactions" -Body @{
    user_id = "elder-test-003"
    channel = "test"
    message = "I feel dizzy"
    event_type = "health_alert"
    trace_id = "test-interaction-003"
    context = @{
        risk_level = "critical"
    }
} -Validate {
    param($r)
    return $r.accepted -eq $true
}

# Output Results
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test Results Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

foreach ($result in $TestResults) {
    if ($result.Status -eq "PASS") {
        Write-Host "[PASS] " -ForegroundColor Green -NoNewline
    } else {
        Write-Host "[FAIL] " -ForegroundColor Red -NoNewline
    }
    Write-Host "$($result.Name)" -NoNewline
    Write-Host " ($($result.Method) $($result.Url))"
    if ($result.Error) {
        Write-Host "       Error: $($result.Error)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Total: $($TestResults.Count) | Pass: $PassCount | Fail: $FailCount" -ForegroundColor $(if ($FailCount -eq 0) { "Green" } else { "Red" })
Write-Host "========================================" -ForegroundColor Cyan

# Export results to JSON for report generation
$report = @{
    timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    total_tests = $TestResults.Count
    passed = $PassCount
    failed = $FailCount
    success_rate = [math]::Round(($PassCount / $TestResults.Count) * 100, 2)
    tests = $TestResults
}

$report | ConvertTo-Json -Depth 10 | Out-File -FilePath "test_report.json" -Encoding UTF8

exit $(if ($FailCount -gt 0) { 1 } else { 0 })
