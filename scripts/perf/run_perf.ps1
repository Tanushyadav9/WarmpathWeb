# scripts/perf/run_perf.ps1 - Automated Locust benchmark runner
param(
    [string]$HostUrl = "http://localhost:8000",
    [int]$DurationSeconds = 60
)

$OutputDir = Join-Path $PSScriptRoot "results"
if (!(Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
}

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "         WarmPath Automated Load Benchmark Suite       " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "Target Host: $HostUrl"
Write-Host "Step Duration: ${DurationSeconds}s"

$UserLevels = @(50, 200, 500)
$SpawnRates = @(10, 40, 50)

for ($i = 0; $i -lt $UserLevels.Length; $i++) {
    $Users = $UserLevels[$i]
    $Rate = $SpawnRates[$i]
    $CsvPrefix = Join-Path $OutputDir "benchmark_${Users}_users"

    Write-Host "`n[*] Starting Benchmark for $Users concurrent users (spawn rate: $Rate/s)..." -ForegroundColor Yellow

    locust -f (Join-Path $PSScriptRoot "locustfile.py") `
        --headless `
        --host $HostUrl `
        --users $Users `
        --spawn-rate $Rate `
        --run-time "${DurationSeconds}s" `
        --csv $CsvPrefix `
        --html "${CsvPrefix}.html" `
        --only-summary

    Write-Host "[+] Completed test for $Users users. Results saved to ${CsvPrefix}*.csv" -ForegroundColor Green
}

Write-Host "`n[✓] All benchmarks completed successfully. Inspect results in $OutputDir" -ForegroundColor Green
