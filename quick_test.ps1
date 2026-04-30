# VIP 项目快速测试 - 简化版
$ErrorActionPreference = "Continue"

$BASE = "C:\Users\ChengXingYu\Desktop\01_Working\vip"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VIP 项目快速诊断" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 测试API
Write-Host "`n测试API接口..." -ForegroundColor Yellow
$apis = @(
    "http://localhost:5000/api/files",
    "http://localhost:5000/api/kb/list",
    "http://localhost:5000/api/kb/config",
    "http://localhost:5000/api/list-docx"
)

foreach ($url in $apis) {
    try {
        $r = Invoke-WebRequest -Uri $url -TimeoutSec 5 -UseBasicParsing
        Write-Host "  ✅ $url" -ForegroundColor Green
    } catch {
        Write-Host "  ❌ $url - $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 检查前端代码
Write-Host "`n检查前端代码..." -ForegroundColor Yellow
$html = Get-Content "$BASE\frontend\index.html" -Raw -Encoding UTF8

# 关键检查
if ($html -match 'var API = window\.location\.origin') {
    Write-Host "  ❌ API定义有问题 - 使用了不安全的 origin" -ForegroundColor Red
    $html = $html -replace 'var API = window\.location\.origin', 'var API = (window.location.origin || (window.location.protocol + "//" + window.location.host))'
    Write-Host "  ✅ 已修复" -ForegroundColor Green
    $html | Set-Content "$BASE\frontend\index.html" -Encoding UTF8 -NoNewline
} else {
    Write-Host "  ✅ API定义正常" -ForegroundColor Green
}

# 检查JS语法 - 查找常见问题
Write-Host "`n检查JS语法..." -ForegroundColor Yellow
$scriptBlock = $html -match '<script>([\s\S]*?)</script>'
if ($matches) {
    $js = $matches[1]

    # 查找未闭合的函数或语句
    $openBraces = ($js | Select-String -Pattern '{' -AllMatches).Matches.Count
    $closeBraces = ($js | Select-String -Pattern '}' -AllMatches).Matches.Count

    if ($openBraces -eq $closeBraces) {
        Write-Host "  ✅ 大括号配对正确 ($openBraces 对)" -ForegroundColor Green
    } else {
        Write-Host "  ❌ 大括号不配对: 开 $openBraces / 闭 $closeBraces" -ForegroundColor Red
    }

    # 查找可疑的注释
    if ($js -match '// ={20,}\s*//') {
        Write-Host "  ⚠ 发现连续的注释行，可能导致问题" -ForegroundColor Yellow
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "诊断完成!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`n请在浏览器中打开: http://localhost:5000" -ForegroundColor White
Write-Host "如果还有问题，按 F12 查看控制台错误" -ForegroundColor White
