#!/bin/bash

# yu_agent 开发环境一键启动脚本
# 用途: 启动 Neo4j 和 Qdrant 容器，运行测试

set -e

echo "============================================================"
echo "yu_agent 开发环境启动脚本"
echo "============================================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安装${NC}"
    echo "请从 https://www.docker.com 下载并安装 Docker"
    exit 1
fi

echo -e "${GREEN}✅ Docker 已安装${NC}"

# 函数: 启动容器
start_service() {
    local name=$1
    local port=$2
    local image=$3
    local env=$4

    echo ""
    echo -e "${YELLOW}启动 $name...${NC}"

    # 检查容器是否已存在
    if docker ps -a --format '{{.Names}}' | grep -q "^${name}$"; then
        echo "  容器已存在，尝试启动..."
        docker start "$name" 2>/dev/null || true
    else
        echo "  创建新容器..."
        if [ -z "$env" ]; then
            docker run -d -p "$port:$port" --name "$name" "$image"
        else
            docker run -d -p "$port:$port" $env --name "$name" "$image"
        fi
    fi

    echo -e "${GREEN}✅ $name 启动中...${NC}"
}

# 函数: 等待服务就绪
wait_service() {
    local name=$1
    local port=$2
    local check_cmd=$3

    echo "等待 $name 就绪..."

    for i in {1..30}; do
        if eval "$check_cmd" &>/dev/null; then
            echo -e "${GREEN}✅ $name 就绪${NC}"
            return 0
        fi
        echo -n "."
        sleep 1
    done

    echo ""
    echo -e "${RED}❌ $name 启动超时${NC}"
    return 1
}

# 主程序
main() {
    echo ""
    echo "选择操作:"
    echo "1. 启动所有服务 (Neo4j + Qdrant)"
    echo "2. 仅启动 Neo4j"
    echo "3. 仅启动 Qdrant"
    echo "4. 停止所有服务"
    echo "5. 查看服务状态"
    echo "6. 清理容器和卷"
    echo ""
    read -p "请输入选项 (1-6): " choice

    case $choice in
        1)
            echo ""
            echo "启动所有服务..."

            # 启动 Neo4j
            start_service "neo4j-yu-agent" "7687" "neo4j:latest" \
                "-e NEO4J_AUTH=neo4j/yu-agents-password"

            # 启动 Qdrant
            start_service "qdrant-yu-agent" "6333" "qdrant/qdrant:latest" ""

            echo ""
            echo "等待服务就绪..."

            # 等待 Neo4j
            wait_service "Neo4j" "7687" \
                "docker exec neo4j-yu-agent cypher-shell -u neo4j -p yu-agents-password 'RETURN 1' &>/dev/null"

            # 等待 Qdrant
            wait_service "Qdrant" "6333" \
                "curl -s http://localhost:6333/health | grep -q alive"

            echo ""
            echo "============================================================"
            echo -e "${GREEN}✅ 所有服务启动成功!${NC}"
            echo "============================================================"
            echo ""
            echo "连接信息:"
            echo "  Neo4j:"
            echo "    URI: bolt://localhost:7687"
            echo "    用户: neo4j"
            echo "    密码: yu-agents-password"
            echo "    Web UI: http://localhost:7474"
            echo ""
            echo "  Qdrant:"
            echo "    URL: http://localhost:6333"
            echo "    API: http://localhost:6333/docs"
            echo ""
            echo "运行测试:"
            echo "  python test_the_yu_agent/test_rag.py"
            echo ""
            ;;

        2)
            echo ""
            echo "启动 Neo4j..."
            start_service "neo4j-yu-agent" "7687" "neo4j:latest" \
                "-e NEO4J_AUTH=neo4j/yu-agents-password"
            wait_service "Neo4j" "7687" \
                "docker exec neo4j-yu-agent cypher-shell -u neo4j -p yu-agents-password 'RETURN 1' &>/dev/null"
            echo -e "${GREEN}✅ Neo4j 启动成功${NC}"
            echo "Web UI: http://localhost:7474"
            ;;

        3)
            echo ""
            echo "启动 Qdrant..."
            start_service "qdrant-yu-agent" "6333" "qdrant/qdrant:latest" ""
            wait_service "Qdrant" "6333" \
                "curl -s http://localhost:6333/health | grep -q alive"
            echo -e "${GREEN}✅ Qdrant 启动成功${NC}"
            echo "API: http://localhost:6333/docs"
            ;;

        4)
            echo ""
            echo "停止所有服务..."

            for container in neo4j-yu-agent qdrant-yu-agent; do
                if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
                    echo "停止 $container..."
                    docker stop "$container" || true
                fi
            done

            echo -e "${GREEN}✅ 所有服务已停止${NC}"
            ;;

        5)
            echo ""
            echo "服务状态:"
            echo ""
            docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | \
                grep -E "(neo4j-yu-agent|qdrant-yu-agent)" || echo "没有运行的服务"
            ;;

        6)
            echo ""
            echo -e "${YELLOW}警告: 此操作将删除容器和数据!${NC}"
            read -p "确实要删除吗? (yes/no): " confirm

            if [ "$confirm" = "yes" ]; then
                echo "清理容器..."
                for container in neo4j-yu-agent qdrant-yu-agent; do
                    if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
                        echo "删除 $container..."
                        docker stop "$container" 2>/dev/null || true
                        docker rm "$container"
                    fi
                done

                echo "清理卷..."
                docker volume prune -f

                echo -e "${GREEN}✅ 清理完成${NC}"
            else
                echo "取消操作"
            fi
            ;;

        *)
            echo -e "${RED}❌ 无效选项${NC}"
            exit 1
            ;;
    esac
}

# 运行主程序
main
