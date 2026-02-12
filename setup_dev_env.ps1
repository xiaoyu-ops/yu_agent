# yu_agent 开发环境一键启动脚本 (PowerShell 版)
# 用途: 启动 Neo4j 和 Qdrant 容器，运行测试

# 检查 Docker 是否安装
function Test-Docker {
    try {
        $null = docker version
        return $true
    }
    catch {
        return $false
    }
}

# 显示菜单
function Show-Menu {
    Write-Host "============================================================"
    Write-Host "yu_agent 开发环境启动脚本" -ForegroundColor Green
    Write-Host "============================================================"
    Write-Host ""
    Write-Host "选择操作:"
    Write-Host "1. 启动所有服务 (Neo4j + Qdrant)"
    Write-Host "2. 仅启动 Neo4j"
    Write-Host "3. 仅启动 Qdrant"
    Write-Host "4. 停止所有服务"
    Write-Host "5. 查看服务状态"
    Write-Host "6. 清理容器和卷"
    Write-Host ""
}

# 启动容器
function Start-Service {
    param(
        [string]$Name,
        [string]$Port,
        [string]$Image,
        [string]$Env
    )

    Write-Host ""
    Write-Host "启动 $Name..." -ForegroundColor Yellow

    $container = docker ps -a --format "{{.Names}}" | Select-String "^${Name}$"

    if ($container) {
        Write-Host "  容器已存在，尝试启动..."
        docker start $Name 2>$null
    }
    else {
        Write-Host "  创建新容器..."
        if ($Env) {
            docker run -d -p "${Port}:${Port}" $Env --name $Name $Image
        }
        else {
            docker run -d -p "${Port}:${Port}" --name $Name $Image
        }
    }

    Write-Host "✅ $Name 启动中..." -ForegroundColor Green
}

# 等待服务就绪
function Wait-Service {
    param(
        [string]$Name,
        [scriptblock]$CheckBlock
    )

    Write-Host "等待 $Name 就绪..."

    for ($i = 0; $i -lt 30; $i++) {
        try {
            $result = & $CheckBlock
            if ($result) {
                Write-Host "✅ $Name 就绪" -ForegroundColor Green
                return $true
            }
        }
        catch {
            # 继续尝试
        }

        Write-Host -NoNewline "."
        Start-Sleep -Seconds 1
    }

    Write-Host ""
    Write-Host "❌ $Name 启动超时" -ForegroundColor Red
    return $false
}

# 检查 Docker
if (-not (Test-Docker)) {
    Write-Host "❌ Docker 未安装" -ForegroundColor Red
    Write-Host "请从 https://www.docker.com 下载并安装 Docker"
    exit 1
}

Write-Host "✅ Docker 已安装" -ForegroundColor Green

# 显示菜单并获取选择
Show-Menu
$choice = Read-Host "请输入选项 (1-6)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "启动所有服务..."

        # 启动 Neo4j
        Start-Service -Name "neo4j-yu-agent" -Port "7687" -Image "neo4j:latest" `
            -Env "-e NEO4J_AUTH=neo4j/yu-agents-password"

        # 启动 Qdrant
        Start-Service -Name "qdrant-yu-agent" -Port "6333" -Image "qdrant/qdrant:latest" -Env ""

        Write-Host ""
        Write-Host "等待服务就绪..."

        # 等待 Neo4j
        Wait-Service -Name "Neo4j" -CheckBlock {
            docker exec neo4j-yu-agent cypher-shell -u neo4j -p yu-agents-password "RETURN 1" 2>$null
        }

        # 等待 Qdrant
        Wait-Service -Name "Qdrant" -CheckBlock {
            $response = Invoke-WebRequest -Uri "http://localhost:6333/health" -ErrorAction SilentlyContinue
            return ($response.StatusCode -eq 200)
        }

        Write-Host ""
        Write-Host "============================================================"
        Write-Host "✅ 所有服务启动成功!" -ForegroundColor Green
        Write-Host "============================================================"
        Write-Host ""
        Write-Host "连接信息:"
        Write-Host "  Neo4j:"
        Write-Host "    URI: bolt://localhost:7687"
        Write-Host "    用户: neo4j"
        Write-Host "    密码: yu-agents-password"
        Write-Host "    Web UI: http://localhost:7474"
        Write-Host ""
        Write-Host "  Qdrant:"
        Write-Host "    URL: http://localhost:6333"
        Write-Host "    API: http://localhost:6333/docs"
        Write-Host ""
        Write-Host "运行测试:"
        Write-Host "  python test_the_yu_agent/test_rag.py"
        Write-Host ""
    }

    "2" {
        Write-Host ""
        Write-Host "启动 Neo4j..."
        Start-Service -Name "neo4j-yu-agent" -Port "7687" -Image "neo4j:latest" `
            -Env "-e NEO4J_AUTH=neo4j/yu-agents-password"

        Wait-Service -Name "Neo4j" -CheckBlock {
            docker exec neo4j-yu-agent cypher-shell -u neo4j -p yu-agents-password "RETURN 1" 2>$null
        }

        Write-Host "✅ Neo4j 启动成功" -ForegroundColor Green
        Write-Host "Web UI: http://localhost:7474"
    }

    "3" {
        Write-Host ""
        Write-Host "启动 Qdrant..."
        Start-Service -Name "qdrant-yu-agent" -Port "6333" -Image "qdrant/qdrant:latest" -Env ""

        Wait-Service -Name "Qdrant" -CheckBlock {
            $response = Invoke-WebRequest -Uri "http://localhost:6333/health" -ErrorAction SilentlyContinue
            return ($response.StatusCode -eq 200)
        }

        Write-Host "✅ Qdrant 启动成功" -ForegroundColor Green
        Write-Host "API: http://localhost:6333/docs"
    }

    "4" {
        Write-Host ""
        Write-Host "停止所有服务..."

        @("neo4j-yu-agent", "qdrant-yu-agent") | ForEach-Object {
            $container = docker ps -a --format "{{.Names}}" | Select-String "^$_$"
            if ($container) {
                Write-Host "停止 $_..."
                docker stop $_ 2>$null
            }
        }

        Write-Host "✅ 所有服务已停止" -ForegroundColor Green
    }

    "5" {
        Write-Host ""
        Write-Host "服务状态:"
        Write-Host ""
        docker ps -a --filter "name=neo4j-yu-agent|qdrant-yu-agent" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    }

    "6" {
        Write-Host ""
        Write-Host "警告: 此操作将删除容器和数据!" -ForegroundColor Yellow
        $confirm = Read-Host "确实要删除吗? (yes/no)"

        if ($confirm -eq "yes") {
            Write-Host "清理容器..."

            @("neo4j-yu-agent", "qdrant-yu-agent") | ForEach-Object {
                $container = docker ps -a --format "{{.Names}}" | Select-String "^$_$"
                if ($container) {
                    Write-Host "删除 $_..."
                    docker stop $_ 2>$null
                    docker rm $_
                }
            }

            Write-Host "清理卷..."
            docker volume prune -f

            Write-Host "✅ 清理完成" -ForegroundColor Green
        }
        else {
            Write-Host "取消操作"
        }
    }

    default {
        Write-Host "❌ 无效选项" -ForegroundColor Red
        exit 1
    }
}
