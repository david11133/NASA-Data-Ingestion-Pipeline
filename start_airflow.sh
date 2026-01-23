#!/bin/bash

##########################################################################################
# Airflow Startup Script
# This script starts both the Airflow webserver and scheduler
##########################################################################################

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="${PROJECT_DIR}/venv"
AIRFLOW_HOME="${PROJECT_DIR}/airflow"

##########################################################################################
# Functions
##########################################################################################

print_header() {
    echo -e "${GREEN}"
    echo "======================================================================"
    echo "  NASA Data Pipeline - Airflow Startup Script"
    echo "======================================================================"
    echo -e "${NC}"
}

check_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${RED}Error: Virtual environment not found at $VENV_DIR${NC}"
        echo "Please create one using: python -m venv venv"
        exit 1
    fi
    echo -e "${GREEN}✓ Virtual environment found${NC}"
}

activate_venv() {
    source "${VENV_DIR}/bin/activate"
    echo -e "${GREEN}✓ Virtual environment activated${NC}"
}

check_airflow_installed() {
    if ! command -v airflow &> /dev/null; then
        echo -e "${RED}Error: Airflow not installed${NC}"
        echo "Install with: pip install apache-airflow==2.8.1"
        exit 1
    fi
    echo -e "${GREEN}✓ Airflow installed ($(airflow version))${NC}"
}

set_environment() {
    export AIRFLOW_HOME="$AIRFLOW_HOME"
    
    # Load .env file
    if [ -f "${PROJECT_DIR}/.env" ]; then
        set -a
        source "${PROJECT_DIR}/.env"
        set +a
        echo -e "${GREEN}✓ Environment variables loaded from .env${NC}"
    fi
}

check_airflow_db() {
    if [ ! -f "${AIRFLOW_HOME}/airflow.db" ]; then
        echo -e "${YELLOW}⚠ Airflow database not initialized${NC}"
        echo "Initializing database..."
        airflow db init
        echo -e "${GREEN}Database initialized${NC}"
        
        echo ""
        echo -e "${YELLOW}Creating admin user...${NC}"
        airflow users create \
            --username admin \
            --firstname David \
            --lastname Admin \
            --role Admin \
            --email davidnady4yad@gmail.com \
            --password admin
    else
        echo -e "${GREEN}Airflow database exists${NC}"
    fi
}

check_dags() {
    if [ ! -d "${AIRFLOW_HOME}/dags" ]; then
        echo -e "${YELLOW}⚠ DAGs directory not found, creating...${NC}"
        mkdir -p "${AIRFLOW_HOME}/dags"
    fi
    
    # Count DAGs
    dag_count=$(find "${AIRFLOW_HOME}/dags" -name "*.py" | wc -l)
    echo -e "${GREEN}Found $dag_count DAG(s)${NC}"
}

kill_existing_processes() {
    echo ""
    echo -e "${YELLOW}Checking for existing Airflow processes...${NC}"
    
    # Kill existing webserver (if any)
    if pgrep -f "airflow webserver" > /dev/null; then
        echo "Killing existing webserver..."
        pkill -f "airflow webserver"
        sleep 2
    fi
    
    # Kill existing scheduler
    if pgrep -f "airflow scheduler" > /dev/null; then
        echo "Killing existing scheduler..."
        pkill -f "airflow scheduler"
        sleep 2
    fi
    
    echo -e "${GREEN}✓ No conflicting processes${NC}"
}

start_services() {
    echo ""
    echo -e "${GREEN}======================================================================"
    echo "  Starting Airflow Services"
    echo "======================================================================${NC}"
    
    # Create logs directory
    mkdir -p "${PROJECT_DIR}/logs/airflow"
    
    echo ""
    echo -e "${YELLOW}Starting Webserver (port 8080)...${NC}"
    nohup airflow webserver --port 8080 \
        > "${PROJECT_DIR}/logs/airflow/webserver.log" 2>&1 &
    WEBSERVER_PID=$!
    echo -e "${GREEN}Webserver started (PID: $WEBSERVER_PID)${NC}"
    
    echo ""
    echo -e "${YELLOW}Starting Scheduler...${NC}"
    nohup airflow scheduler \
        > "${PROJECT_DIR}/logs/airflow/scheduler.log" 2>&1 &
    SCHEDULER_PID=$!
    echo -e "${GREEN}Scheduler started (PID: $SCHEDULER_PID)${NC}"
    
    # Wait a bit for services to start
    echo ""
    echo "Waiting for services to initialize..."
    sleep 5
    
    # Check if processes are still running
    if ps -p $WEBSERVER_PID > /dev/null && ps -p $SCHEDULER_PID > /dev/null; then
        echo -e "${GREEN}All services running successfully!${NC}"
    else
        echo -e "${RED}Warning: Some services may have failed to start${NC}"
        echo "Check logs in: ${PROJECT_DIR}/logs/airflow/"
    fi
}

print_access_info() {
    echo ""
    echo -e "${GREEN}======================================================================"
    echo "  Airflow is Running!"
    echo "======================================================================"
    echo ""
    echo "  Web UI:      http://localhost:8080"
    echo "  Username:    admin"
    echo "  Password:    admin"
    echo ""
    echo "  Logs:        ${PROJECT_DIR}/logs/airflow/"
    echo "  Webserver:   logs/airflow/webserver.log"
    echo "  Scheduler:   logs/airflow/scheduler.log"
    echo ""
    echo "======================================================================"
    echo "  To stop Airflow, run: ./stop_airflow.sh"
    echo "  Or press Ctrl+C and run: pkill -f airflow"
    echo "======================================================================${NC}"
}

##########################################################################################
# Main
##########################################################################################

main() {
    print_header
    
    echo "Project Directory: $PROJECT_DIR"
    echo "Airflow Home: $AIRFLOW_HOME"
    echo ""
    
    check_venv
    activate_venv
    check_airflow_installed
    set_environment
    check_airflow_db
    check_dags
    kill_existing_processes
    start_services
    print_access_info
}

# Run main function
main