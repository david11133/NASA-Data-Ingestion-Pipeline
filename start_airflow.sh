#!/bin/bash

##############################################################################
# Airflow Startup Script
# This script helps you start/stop Airflow easily
##############################################################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project paths
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PATH="$PROJECT_ROOT/venv"

##############################################################################
# Functions
##############################################################################

print_header() {
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  NASA NEO Pipeline - Airflow Manager${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

check_venv() {
    if [ ! -d "$VENV_PATH" ]; then
        print_error "Virtual environment not found at $VENV_PATH"
        print_info "Please create it first: python3 -m venv venv"
        exit 1
    fi
}

activate_venv() {
    source "$VENV_PATH/bin/activate"
    print_success "Virtual environment activated"
}

load_env() {
    if [ -f "$PROJECT_ROOT/.env" ]; then
        source "$PROJECT_ROOT/.env"
        print_success "Environment variables loaded"
    else
        print_warning ".env file not found"
    fi
}

check_airflow_home() {
    if [ -z "$AIRFLOW_HOME" ]; then
        export AIRFLOW_HOME="$PROJECT_ROOT/airflow"
        print_info "AIRFLOW_HOME set to $AIRFLOW_HOME"
    fi
}

check_port() {
    if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null ; then
        print_warning "Port 8080 is already in use"
        echo -e "  Process: $(lsof -ti:8080 | xargs ps -p | tail -1)"
        return 1
    else
        print_success "Port 8080 is available"
        return 0
    fi
}

start_webserver() {
    print_info "Starting Airflow webserver..."
    
    # Check if already running
    if pgrep -f "airflow webserver" > /dev/null; then
        print_warning "Webserver is already running"
        return
    fi
    
    # Start webserver
    airflow webserver --port 8080 --daemon
    
    # Wait a bit and check
    sleep 3
    if pgrep -f "airflow webserver" > /dev/null; then
        print_success "Webserver started successfully"
        print_info "Access at: http://localhost:8080"
    else
        print_error "Failed to start webserver"
    fi
}

start_scheduler() {
    print_info "Starting Airflow scheduler..."
    
    # Check if already running
    if pgrep -f "airflow scheduler" > /dev/null; then
        print_warning "Scheduler is already running"
        return
    fi
    
    # Start scheduler
    airflow scheduler --daemon
    
    # Wait a bit and check
    sleep 3
    if pgrep -f "airflow scheduler" > /dev/null; then
        print_success "Scheduler started successfully"
    else
        print_error "Failed to start scheduler"
    fi
}

stop_airflow() {
    print_info "Stopping Airflow services..."
    
    # Stop webserver
    if pgrep -f "airflow webserver" > /dev/null; then
        pkill -f "airflow webserver"
        print_success "Webserver stopped"
    else
        print_info "Webserver was not running"
    fi
    
    # Stop scheduler
    if pgrep -f "airflow scheduler" > /dev/null; then
        pkill -f "airflow scheduler"
        print_success "Scheduler stopped"
    else
        print_info "Scheduler was not running"
    fi
}

status() {
    echo ""
    print_info "Airflow Status:"
    echo ""
    
    # Check webserver
    if pgrep -f "airflow webserver" > /dev/null; then
        print_success "Webserver: RUNNING (PID: $(pgrep -f 'airflow webserver'))"
    else
        print_error "Webserver: STOPPED"
    fi
    
    # Check scheduler
    if pgrep -f "airflow scheduler" > /dev/null; then
        print_success "Scheduler: RUNNING (PID: $(pgrep -f 'airflow scheduler'))"
    else
        print_error "Scheduler: STOPPED"
    fi
    
    # Check port
    echo ""
    if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null ; then
        print_info "Port 8080: IN USE"
    else
        print_info "Port 8080: FREE"
    fi
    
    echo ""
}

init_airflow() {
    print_info "Initializing Airflow..."
    
    # Initialize database
    print_info "Initializing database..."
    airflow db init
    
    if [ $? -eq 0 ]; then
        print_success "Database initialized"
        
        # Create admin user
        echo ""
        print_info "Creating admin user..."
        print_warning "You will be prompted to enter a password"
        echo ""
        
        airflow users create \
            --username admin \
            --firstname David \
            --lastname Admin \
            --role Admin \
            --email admin@example.com
        
        if [ $? -eq 0 ]; then
            print_success "Admin user created"
            print_info "Username: admin"
            print_info "Remember your password!"
        else
            print_error "Failed to create admin user"
        fi
    else
        print_error "Failed to initialize database"
    fi
}

list_dags() {
    print_info "Listing DAGs..."
    echo ""
    airflow dags list
}

test_dag() {
    if [ -z "$1" ]; then
        print_error "Please specify a DAG ID"
        print_info "Usage: $0 test <dag_id>"
        exit 1
    fi
    
    print_info "Testing DAG: $1"
    python "$PROJECT_ROOT/dags/$1.py"
}

trigger_dag() {
    if [ -z "$1" ]; then
        print_error "Please specify a DAG ID"
        print_info "Usage: $0 trigger <dag_id>"
        exit 1
    fi
    
    print_info "Triggering DAG: $1"
    airflow dags trigger "$1"
}

show_logs() {
    if [ -z "$1" ] || [ -z "$2" ]; then
        print_error "Please specify DAG ID and task ID"
        print_info "Usage: $0 logs <dag_id> <task_id> [execution_date]"
        exit 1
    fi
    
    EXEC_DATE=${3:-$(date +%Y-%m-%d)}
    
    print_info "Showing logs for $1 > $2 ($EXEC_DATE)"
    airflow tasks logs "$1" "$2" "$EXEC_DATE"
}

##############################################################################
# Main Script
##############################################################################

print_header
echo ""

# Setup
check_venv
activate_venv
load_env
check_airflow_home

echo ""

# Parse command
case "$1" in
    start)
        print_info "Starting Airflow..."
        echo ""
        start_webserver
        start_scheduler
        echo ""
        status
        ;;
    
    stop)
        stop_airflow
        ;;
    
    restart)
        stop_airflow
        echo ""
        sleep 2
        start_webserver
        start_scheduler
        echo ""
        status
        ;;
    
    status)
        status
        ;;
    
    init)
        init_airflow
        ;;
    
    dags)
        list_dags
        ;;
    
    test)
        test_dag "$2"
        ;;
    
    trigger)
        trigger_dag "$2"
        ;;
    
    logs)
        show_logs "$2" "$3" "$4"
        ;;
    
    web)
        start_webserver
        ;;
    
    scheduler)
        start_scheduler
        ;;
    
    *)
        echo "Usage: $0 {start|stop|restart|status|init|dags|test|trigger|logs|web|scheduler}"
        echo ""
        echo "Commands:"
        echo "  start      - Start webserver and scheduler"
        echo "  stop       - Stop all Airflow processes"
        echo "  restart    - Restart all Airflow processes"
        echo "  status     - Show status of Airflow services"
        echo "  init       - Initialize Airflow database and create admin user"
        echo "  dags       - List all DAGs"
        echo "  test       - Test a DAG: $0 test <dag_id>"
        echo "  trigger    - Trigger a DAG: $0 trigger <dag_id>"
        echo "  logs       - Show logs: $0 logs <dag_id> <task_id> [date]"
        echo "  web        - Start only webserver"
        echo "  scheduler  - Start only scheduler"
        echo ""
        echo "Examples:"
        echo "  $0 start"
        echo "  $0 trigger nasa_neo_daily_pipeline"
        echo "  $0 logs nasa_neo_daily_pipeline extract_data 2026-01-18"
        exit 1
        ;;
esac

echo ""
print_info "Done!"
echo ""
