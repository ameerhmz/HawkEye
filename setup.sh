#!/bin/bash

# Hawk Eye - AI-Powered Surveillance System - Setup Script
# This script automates the complete setup for Mac/Linux

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Hawk Eye - AI Surveillance Setup${NC}"
echo -e "${BLUE}Setup Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print step
print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# ============ Check Prerequisites ============
print_step "Checking Prerequisites..."
echo ""

# Check Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    print_success "Python 3 found: $PYTHON_VERSION"
else
    print_error "Python 3 is not installed"
    echo "Install it with: brew install python3"
    exit 1
fi

# Check Node.js
if command_exists node; then
    NODE_VERSION=$(node --version)
    print_success "Node.js found: $NODE_VERSION"
else
    print_error "Node.js is not installed"
    echo "Install it with: brew install node"
    exit 1
fi

# Check npm
if command_exists npm; then
    NPM_VERSION=$(npm --version)
    print_success "npm found: $NPM_VERSION"
else
    print_error "npm is not installed"
    exit 1
fi

echo ""

# ============ System Dependencies (Optional but recommended) ============
print_step "Checking System Dependencies (Optional)..."
echo ""

if command_exists brew; then
    print_success "Homebrew found"
    
    # Check LiveKit
    if command_exists livekit; then
        print_success "LiveKit Server is installed"
    else
        print_warning "LiveKit Server is not installed"
        echo "  Install with: brew install livekit"
        read -p "  Auto-install LiveKit? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_step "Installing LiveKit..."
            brew install livekit
            print_success "LiveKit installed"
        fi
    fi
    
    # Check Cloudflared
    if command_exists cloudflared; then
        print_success "Cloudflared is installed"
    else
        print_warning "Cloudflared is not installed"
        echo "  Install with: brew install cloudflare-warp"
        read -p "  Auto-install Cloudflared? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_step "Installing Cloudflared..."
            brew install cloudflare-warp
            print_success "Cloudflared installed"
        fi
    fi
    
    # Check ngrok
    if command_exists ngrok; then
        print_success "ngrok is installed"
    else
        print_warning "ngrok is not installed"
        echo "  Install with: brew install ngrok"
        read -p "  Auto-install ngrok? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_step "Installing ngrok..."
            brew install ngrok
            print_success "ngrok installed"
        fi
    fi
    
    # Check PostgreSQL
    if command_exists psql; then
        print_success "PostgreSQL is installed"
    else
        print_warning "PostgreSQL is not installed"
        echo "  Install with: brew install postgresql"
        read -p "  Auto-install PostgreSQL? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_step "Installing PostgreSQL..."
            brew install postgresql
            print_success "PostgreSQL installed"
        fi
    fi
else
    print_warning "Homebrew not found (macOS only requirement)"
fi

echo ""

# ============ Setup Backend ============
print_step "Setting up Backend..."
echo ""

# Check if venv already exists
if [ -d ".venv" ]; then
    print_warning "Virtual environment already exists"
    read -p "Do you want to recreate it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf .venv
        print_step "Creating Python virtual environment..."
        python3 -m venv .venv
    fi
else
    print_step "Creating Python virtual environment..."
    python3 -m venv .venv
fi

print_step "Activating virtual environment..."
source .venv/bin/activate

print_step "Installing Python dependencies from backend/requirements.txt..."
pip install --upgrade pip setuptools wheel
pip install -r backend/requirements.txt

if [ $? -eq 0 ]; then
    print_success "Python dependencies installed successfully"
else
    print_error "Failed to install Python dependencies"
    exit 1
fi

echo ""

# ============ Setup Dashboard ============
print_step "Setting up Dashboard..."
echo ""

if [ ! -d "dashboard/node_modules" ]; then
    print_step "Installing Node.js dependencies..."
    cd dashboard
    npm install
    
    if [ $? -eq 0 ]; then
        print_success "Dashboard dependencies installed successfully"
    else
        print_error "Failed to install Dashboard dependencies"
        cd ..
        exit 1
    fi
    cd ..
else
    print_warning "Dashboard node_modules already exists"
    read -p "Do you want to reinstall? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd dashboard
        rm -rf node_modules package-lock.json
        npm install
        cd ..
    fi
fi

echo ""

# ============ Create Required Directories ============
print_step "Creating required directories..."

mkdir -p logs
mkdir -p backend/static/snapshots
mkdir -p static/snapshots

print_success "Directories created"
echo ""

# ============ Environment Files Check ============
print_step "Environment Files Setup..."
echo ""

if [ ! -f "backend/.env" ]; then
    print_warning "backend/.env not found"
    echo "  You need to create this file with your configuration"
    echo "  Refer to the README.md for required environment variables"
fi

if [ ! -f "dashboard/.env.local" ]; then
    print_warning "dashboard/.env.local not found"
    echo "  You need to create this file with your configuration"
    echo "  Refer to the README.md for required environment variables"
fi

echo ""

# ============ Summary ============
print_step "Setup Summary..."
echo ""
print_success "Python environment: .venv/bin/python"
print_success "Backend dependencies: Installed"
print_success "Dashboard dependencies: Installed"
echo ""

echo -e "${YELLOW}NEXT STEPS:${NC}"
echo "1. Create backend/.env with your configuration"
echo "2. Create dashboard/.env.local with your configuration"
echo "3. Set up PostgreSQL database (if not already done)"
echo "4. Run the application:"
echo "   ${BLUE}source .venv/bin/activate${NC}  # Activate virtual environment"
echo "   ${BLUE}./scripts/dev.sh${NC}              # Start all services"
echo ""
echo -e "${YELLOW}For detailed setup instructions, see: README.md${NC}"
echo ""

print_success "Setup completed successfully!"
