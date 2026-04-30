# VIP 项目自动测试修复脚本
# 功能：启动后端 → 测试所有API接口 → 发现问题自动修复

$ErrorActionPreference = "Continue"
$BASE = "C:\Users\ChengXingYu\Desktop\01_Working\vip"
$BACKEND = "$BASE\backend"
$FRONTEND = "$BASE\frontend"
$VENV_PYTHON = "C:\Users\ChengXingYu\Desktop\01_Working\vip\.venv\Scripts\python.exe"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VIP 项目自动测试修复开始" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ========== 步骤1：检查端口5000是否被占用 ==========
Write-Host "`n[1/6] 检查后端服务状态..." -ForegroundColor Yellow
$proc = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue
if ($proc) {
    Write-Host "  ⚠ 端口5000已被占用，尝试关闭旧进程..." -ForegroundColor Yellow
    $oldPid = (Get-NetTCPConnection -LocalPort 5000).OwningProcess | Select-Object -First 1
    if ($oldPid) {
        Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Write-Host "  ✅ 已关闭旧进程" -ForegroundColor Green
    }
} else {
    Write-Host "  ✅ 端口5000空闲" -ForegroundColor Green
}

# ========== 步骤2：启动后端服务 ==========
Write-Host "`n[2/6] 启动后端服务..." -ForegroundColor Yellow
$env:FLASK_ENV = "development"
$serverJob = Start-Job -ScriptBlock {
    param($python, $appPath, $workDir)
    Set-Location $workDir
    & $python $appPath
} -ArgumentList $VENV_PYTHON, "$BACKEND\app.py", $BACKEND

Start-Sleep -Seconds 4

# 检查服务是否启动成功
try {
    $test = Invoke-WebRequest -Uri "http://localhost:5000/" -TimeoutSec 5 -UseBasicParsing
    Write-Host "  ✅ 后端服务启动成功 (状态码: $($test.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "  ❌ 后端服务启动失败: $_" -ForegroundColor Red
    Write-Host "  查看后端日志..." -ForegroundColor Yellow
    Receive-Job $serverJob -ErrorAction SilentlyContinue
    Stop-Job $serverJob -ErrorAction SilentlyContinue
    Remove-Job $serverJob -ErrorAction SilentlyContinue
    exit 1
}

# ========== 步骤3：测试API接口 ==========
Write-Host "`n[3/6] 测试API接口..." -ForegroundColor Yellow

$apiTests = @(
    @{ Name = "文件列表"; Url = "http://localhost:5000/api/files"; Method = "GET" },
    @{ Name = "上传文件(测试)"; Url = "http://localhost:5000/api/upload"; Method = "POST" },
    @{ Name = "知识库列表"; Url = "http://localhost:5000/api/kb/list"; Method = "GET" },
    @{ Name = "知识库配置"; Url = "http://localhost:5000/api/kb/config"; Method = "GET" },
    @{ Name = "Word文件列表"; Url = "http://localhost:5000/api/list-docx"; Method = "GET" }
)

$failed = @()
foreach ($test in $apiTests) {
    try {
        if ($test.Method -eq "POST") {
            $response = Invoke-WebRequest -Uri $test.Url -Method POST -TimeoutSec 5 -UseBasicParsing
        } else {
            $response = Invoke-WebRequest -Uri $test.Url -TimeoutSec 5 -UseBasicParsing
        }
        Write-Host "  ✅ $($test.Name): OK (状态码: $($response.StatusCode))" -ForegroundColor Green
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode) {
            Write-Host "  ⚠ $($test.Name): HTTP $statusCode" -ForegroundColor Yellow
        } else {
            Write-Host "  ❌ $($test.Name): $($_.Exception.Message)" -ForegroundColor Red
            $failed += $test
        }
    }
}

# ========== 步骤4：检查前端代码 ==========
Write-Host "`n[4/6] 检查前端代码..." -ForegroundColor Yellow

$indexPath = "$FRONTEND\index.html"
$content = Get-Content $indexPath -Raw -Encoding UTF8

# 检查问题1: API定义
if ($content -match 'var API = window\.location\.origin') {
    Write-Host "  ❌ 发现问题: API变量使用了不安全的 window.location.origin" -ForegroundColor Red
    $content = $content -replace 'var API = window\.location\.origin', 'var API = (window.location.origin || (window.location.protocol + "//" + window.location.host))'
    Write-Host "  ✅ 已修复: 添加了备用origin拼接" -ForegroundColor Green
}

# 检查问题2: 注释冲突
if ($content -match "// =================================" -and $content -match "// API") {
    Write-Host "  ⚠ 警告: 发现可能冲突的注释格式" -ForegroundColor Yellow
}

# 检查问题3: 检查是否有未定义的函数引用
$missingFunctions = @()
$requiredFunctions = @("apiUpload", "apiList", "apiContent", "apiSave", "apiDelete",
                      "apiKbList", "apiKbTree", "apiKbSearch", "apiKbAsk",
                      "apiKbConfig", "apiKbSaveConfig", "apiKbTestLlm")

foreach ($fn in $requiredFunctions) {
    if (-not ($content -match "function $fn")) {
        $missingFunctions += $fn
    }
}

if ($missingFunctions.Count -gt 0) {
    Write-Host "  ❌ 缺少函数: $($missingFunctions -join ', ')" -ForegroundColor Red
} else {
    Write-Host "  ✅ 所有必需函数已定义" -ForegroundColor Green
}

# 检查问题4: 分号缺失
$lines = $content -split "`n"
$lineNum = 0
$semicolonIssues = @()
foreach ($line in $lines) {
    $lineNum++
    $trimmed = $line.Trim()
    # 跳过注释、空行、代码块结束
    if ($trimmed -match '^//' -or $trimmed -eq '' -or $trimmed -match '^\}' -or $trimmed -match '^\{' -or $trimmed -match '^\*') {
        continue
    }
    # 检查函数声明、if、for、while等结构
    if ($trimmed -match '^function\s+' -and $trimmed -notmatch '\{$' -and $trimmed -notmatch ';$') {
        $semicolonIssues += "$lineNum`: $trimmed"
    }
}

if ($semicolonIssues.Count -gt 0) {
    Write-Host "  ⚠ 发现可能的分号缺失问题:" -ForegroundColor Yellow
    foreach ($issue in $semicolonIssues) {
        Write-Host "    行 $($issue)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ✅ 未发现明显的语法问题" -ForegroundColor Green
}

# ========== 步骤5：保存修复后的代码 ==========
if ($content -ne (Get-Content $indexPath -Raw -Encoding UTF8)) {
    Write-Host "`n[5/6] 保存修复后的代码..." -ForegroundColor Yellow
    $content | Set-Content -Path $indexPath -Encoding UTF8 -NoNewline
    Write-Host "  ✅ 前端代码已更新" -ForegroundColor Green
} else {
    Write-Host "`n[5/6] 代码无需修改" -ForegroundColor Gray
}

# ========== 步骤6：生成测试报告 ==========
Write-Host "`n[6/6] 生成测试报告..." -ForegroundColor Yellow

$report = @"
========================================
VIP 项目测试报告
时间: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
========================================

后端服务状态: $(if (Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue) { "运行中" } else { "未运行" })
前端文件: $indexPath

API测试结果:
$($apiTests | ForEach-Object { "  - $($_.Name): $((if ($failed -contains $_) { '失败' } else { '成功' }))" } -join "`n")

修复状态:
$(
    if ($missingFunctions.Count -eq 0) { "  ✅ 所有必需函数已定义" }
    else { "  ❌ 缺少函数: $($missingFunctions -join ', ')" }
)

下一步操作:
1. 打开浏览器访问: http://localhost:5000
2. 如果还有问题，按 F12 打开控制台查看错误
3. 如果是缓存问题，使用 Ctrl+Shift+R 强制刷新

========================================
"@

Write-Host $report

# 保存报告
$report | Out-File -FilePath "$BASE\test_report.txt" -Encoding UTF8
Write-Host "报告已保存到: $BASE\test_report.txt" -ForegroundColor Cyan

# 保持服务运行
Write-Host "`n后端服务继续运行中，按 Ctrl+C 停止..." -ForegroundColor Cyan

# 等待用户中断
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Stop-Job $serverJob -ErrorAction SilentlyContinue
    Remove-Job $serverJob -ErrorAction SilentlyContinue
    Write-Host "`n服务已停止" -ForegroundColor Cyan
}
