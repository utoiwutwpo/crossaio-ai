# CrossAIO - uvicorn 自愈型守护进程
# =====================================
# 1) 每 5 秒检查 :9000 是否在监听；没有就自动拉起 uvicorn（服务自杀自愈）
# 2) 发现 .restart-trigger 触发文件 -> 删触发文件 -> 杀 :9000 -> 重新拉起（远程改码重启）
# 3) 启动后连续失败超过 N 次，仍会继续重试（每 15s 一次），直到成功为止
# 由 install-watcher.bat / START-ALL.bat 注册为开机自启，隐藏窗口运行。

$backend  = "D:\Claude\crossbot-ai\backend"
$trigger  = Join-Path $backend ".restart-trigger"
$starter  = Join-Path $backend "start-uvicorn.bat"
$log      = Join-Path $backend "watcher.log"
$port     = 9000

function Write-Log($msg) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg" | Out-File -FilePath $log -Append -Encoding utf8
}

function Test-PortAlive($p) {
    try {
        $c = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
        return ($null -ne $c -and @($c).Count -gt 0)
    } catch { return $false }
}

function Stop-PortOwner($p) {
    try {
        Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique |
            ForEach-Object {
                Write-Log "killing PID $_ on port $p"
                Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
            }
    } catch { Write-Log "kill error: $_" }
    # 清掉残留的 uvicorn 进程（含 --reload 父进程 / 上一轮的僵尸实例），
    # 否则旧代码进程会继续占着 9000，新代码永远上不去。
    try {
        Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -like '*uvicorn*app.main:app*' } |
            ForEach-Object {
                Write-Log "killing leftover uvicorn PID $($_.ProcessId)"
                Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
            }
    } catch { Write-Log "leftover kill error: $_" }
    Start-Sleep -Milliseconds 1200
}

function Start-Uvicorn($reason) {
    if (-not (Test-Path $starter)) { Write-Log "ERROR: start-uvicorn.bat not found"; return }
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "`"$starter`"" `
        -WorkingDirectory $backend -WindowStyle Hidden
    Write-Log "uvicorn start requested ($reason)"
}

Write-Log "=== watcher started (self-healing mode, port $port) ==="

# 先清理旧版 watcher 进程，再抢锁 —— 顺序不能反：
# 若先抢锁，旧实例仍持锁，新实例会直接退出，导致脚本更新永远不生效。
try {
    $selfPid = $PID
    Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like '*uvicorn-watcher.ps1*' -and $_.ProcessId -ne $selfPid } |
        ForEach-Object {
            Write-Log "killing stale watcher PID $($_.ProcessId)"
            Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        }
    Start-Sleep -Milliseconds 800
} catch { Write-Log "stale cleanup error: $_" }

# 单实例互斥：已有实例在跑就直接退出
$mutex = New-Object System.Threading.Mutex($false, "Global\CrossAIO-Watcher-Mutex")
$owned = $false
try { $owned = $mutex.WaitOne(0) } catch { $owned = $true }
if (-not $owned) {
    Write-Log "another watcher instance already running, exiting"
    exit 0
}

$failStreak = 0
while ($true) {
    try {
        if (Test-Path $trigger) {
            Remove-Item $trigger -Force -ErrorAction SilentlyContinue
            Write-Log "trigger found -> force restart uvicorn"
            Stop-PortOwner $port
            Start-Sleep -Seconds 2
            Start-Uvicorn "trigger"
            $failStreak = 0
            Start-Sleep -Seconds 8
            continue
        }

        if (-not (Test-PortAlive $port)) {
            $failStreak++
            Write-Log "port $port NOT listening (streak=$failStreak) -> auto start"
            Start-Uvicorn "self-heal"
            Start-Sleep -Seconds 12
        } else {
            if ($failStreak -ne 0) {
                Write-Log "port $port healthy again, reset streak"
                $failStreak = 0
            }
            Start-Sleep -Seconds 5
        }
    } catch {
        Write-Log "loop error: $_"
        Start-Sleep -Seconds 5
    }
}
