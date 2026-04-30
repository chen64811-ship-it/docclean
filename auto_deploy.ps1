# VIP项目自动打包上传脚本
# 功能：自动打包代码并推送到 moudle1 仓库

param(
    [string]$message = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = "C:\Users\ChengXingYu\Desktop\01_Working\vip"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  VIP项目 - 自动打包上传" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 切换到项目目录
Set-Location $projectRoot

# 检查 git 状态
Write-Host "`n[1/5] 检查 Git 状态..." -ForegroundColor Yellow
$status = git status --porcelain
if (-not $status) {
    Write-Host "没有需要提交的更改" -ForegroundColor Green
    exit 0
}

# 添加所有更改
Write-Host "[2/5] 添加所有更改..." -ForegroundColor Yellow
git add -A

# 提交更改
if (-not $message) {
    $message = "自动打包 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
}
Write-Host "[3/5] 提交更改: $message" -ForegroundColor Yellow
git commit -m $message

# 推送到 moudle1 仓库
Write-Host "[4/5] 推送到 moudle1 仓库..." -ForegroundColor Yellow
try {
    git push moudle1 master
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "  推送成功！" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} catch {
    Write-Host "`n推送失败，可能需要身份验证" -ForegroundColor Red
    Write-Host "错误: $_" -ForegroundColor Red
}

# 显示提交记录
Write-Host "`n[5/5] 最近提交记录:" -ForegroundColor Yellow
git log --oneline -5
