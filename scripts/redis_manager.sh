#!/bin/bash
# Redis Stack Management Script
# Simplifies common Redis operations for Superlinked

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_COMPOSE_FILE="$PROJECT_ROOT/docker-compose.redis.yml"
REDIS_DATA_DIR="$PROJECT_ROOT/data/redis"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Ensure data directory exists
ensure_data_dir() {
    if [ ! -d "$REDIS_DATA_DIR" ]; then
        info "Creating Redis data directory: $REDIS_DATA_DIR"
        mkdir -p "$REDIS_DATA_DIR"
    fi
}

# Ensure config directory exists
ensure_config_dir() {
    local config_dir="$PROJECT_ROOT/config"
    if [ ! -d "$config_dir" ]; then
        info "Creating config directory: $config_dir"
        mkdir -p "$config_dir"
    fi
}

# Start Redis Stack
start() {
    info "Starting Redis Stack..."
    ensure_data_dir
    ensure_config_dir

    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d

    # Wait for Redis to be ready
    info "Waiting for Redis to be ready..."
    for i in {1..30}; do
        if docker exec superlinked-redis-stack redis-cli ping > /dev/null 2>&1; then
            success "Redis Stack is running!"
            info "Redis Server: localhost:6379"
            info "RedisInsight UI: http://localhost:8001"
            return 0
        fi
        sleep 1
    done

    error "Redis failed to start within 30 seconds"
    return 1
}

# Stop Redis Stack
stop() {
    info "Stopping Redis Stack..."
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    success "Redis Stack stopped"
}

# Restart Redis Stack
restart() {
    stop
    start
}

# Check Redis status
status() {
    if docker ps | grep -q superlinked-redis-stack; then
        success "Redis Stack is running"
        docker exec superlinked-redis-stack redis-cli info | grep -E "(redis_version|used_memory_human|connected_clients|total_commands_processed)"
    else
        warning "Redis Stack is not running"
        return 1
    fi
}

# View Redis logs
logs() {
    docker-compose -f "$DOCKER_COMPOSE_FILE" logs -f redis-stack
}

# Access Redis CLI
cli() {
    info "Connecting to Redis CLI..."
    docker exec -it superlinked-redis-stack redis-cli
}

# Backup Redis data
backup() {
    ensure_data_dir
    local backup_file="$PROJECT_ROOT/backups/redis-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    local backup_dir="$(dirname "$backup_file")"

    if [ ! -d "$backup_dir" ]; then
        mkdir -p "$backup_dir"
    fi

    info "Creating backup: $backup_file"

    # Trigger Redis save
    docker exec superlinked-redis-stack redis-cli BGSAVE
    sleep 2

    # Backup data directory
    tar -czf "$backup_file" -C "$PROJECT_ROOT/data" redis/
    success "Backup created: $backup_file"
}

# Restore Redis data from backup
restore() {
    local backup_file="$1"

    if [ -z "$backup_file" ]; then
        error "Usage: $0 restore <backup-file>"
        return 1
    fi

    if [ ! -f "$backup_file" ]; then
        error "Backup file not found: $backup_file"
        return 1
    fi

    warning "This will overwrite existing Redis data. Are you sure? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        info "Restore cancelled"
        return 0
    fi

    info "Stopping Redis..."
    stop

    info "Restoring backup..."
    rm -rf "$REDIS_DATA_DIR"
    mkdir -p "$PROJECT_ROOT/data"
    tar -xzf "$backup_file" -C "$PROJECT_ROOT/data"

    info "Starting Redis..."
    start

    success "Restore complete"
}

# Clean Redis data (with confirmation)
clean() {
    warning "This will DELETE all Redis data. Are you sure? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        info "Clean cancelled"
        return 0
    fi

    info "Stopping Redis..."
    stop

    info "Removing Redis data..."
    rm -rf "$REDIS_DATA_DIR"

    success "Redis data cleaned"
}

# Show help
help() {
    echo "Redis Stack Manager for Superlinked"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  start       Start Redis Stack (server + RedisInsight UI)"
    echo "  stop        Stop Redis Stack"
    echo "  restart     Restart Redis Stack"
    echo "  status      Show Redis status and info"
    echo "  logs        View Redis logs (follow mode)"
    echo "  cli         Access Redis CLI"
    echo "  backup      Create backup of Redis data"
    echo "  restore     Restore Redis data from backup"
    echo "  clean       Delete all Redis data (with confirmation)"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 status"
    echo "  $0 backup"
    echo "  $0 restore backups/redis-backup-20250314-120000.tar.gz"
}

# Main command router
case "${1:-help}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    cli)
        cli
        ;;
    backup)
        backup
        ;;
    restore)
        restore "$2"
        ;;
    clean)
        clean
        ;;
    help|--help|-h)
        help
        ;;
    *)
        error "Unknown command: $1"
        help
        exit 1
        ;;
esac
