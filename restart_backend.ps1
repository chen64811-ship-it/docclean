# VIP 后端一键重启脚本
# 清理缓存 + 停止旧进程 + 启动新服务

$ErrorActionPreference = "Stop"
$VENV_PYTHON = "C:\Users\ChengXingYu\Desktop\01_Working\vip\.venv\Scripts\python.exe"
$BACKEND_DIR = "C:\Users\ChengXingYu\Desktop\01_Working\vip\backend"
$PYTHON = "C:\Users\ChengXingYu\Desktop\01_Working\vip\.venv\Scripts\python.exe"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VIP 后端一键重启" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. 清理所有 Python 缓存
Write-Host "`n[1/4] 清理 Python 缓存..." -ForegroundColor Yellow
Get-ChildItem -Path "$BACKEND_DIR" -Include "__pycache__" -Recurse -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "  ✅ 缓存已清理" -ForegroundColor Green

# 2. 停止旧的后端进程
Write-Host "`n[2/4] 停止旧服务..." -ForegroundColor Yellow
$portProcess = Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue
if ($portProcess) {
    $oldPid = $portProcess[0].OwningProcess
    Write-Host "  找到进程 PID: $oldPid" -ForegroundColor White
    Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "  ✅ 旧服务已停止" -ForegroundColor Green
} else {
    Write-Host "  ⚠ 没有找到运行中的服务" -ForegroundColor Yellow
}

# 3. 验证 docx 文件
Write-Host "`n[3/4] 验证 docx 文件..." -ForegroundColor Yellow
$VipRoot = "C:\Users\ChengXingYu\Desktop\01_Working\vip"
$docxFiles = Get-ChildItem -Path $VipRoot -Filter "*.docx" -ErrorAction SilentlyContinue
if ($docxFiles) {
    foreach ($f in $docxFiles) {
        Write-Host "  ✅ 找到: $($f.Name)" -ForegroundColor Green
    }
} else {
    Write-Host "  ❌ 未找到 .docx 文件！" -ForegroundColor Red
}

# 4. 启动新服务
Write-Host "`n[4/4] 启动服务..." -ForegroundColor Yellow
Set-Location $BACKEND_DIR
& $PYTHON app.py

# 如果服务启动失败，显示错误
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n❌ 服务启动失败！" -ForegroundColor Red
    exit 1
}
