#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default quiet mode is off
QUIET_MODE=false

# Parse command line arguments
for arg in "$@"; do
  if [ "$arg" == "--quiet" ]; then
    QUIET_MODE=true
  fi
done

# Set output redirection based on quiet mode
if [ "$QUIET_MODE" = true ]; then
  exec > /dev/null 2>&1
fi

# Function to print colored messages
print_message() {
  if [ "$QUIET_MODE" = false ]; then
    echo -e "${2}${1}${NC}"
  fi
}

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Get list of available servers (directory names in src/servers)
get_available_servers() {
  local servers=()
  # Check if src/servers directory exists
  if [ -d "src/servers" ]; then
    # Loop through directories in src/servers
    for dir in src/servers/*/; do
      if [ -d "$dir" ]; then
        # Extract the directory name without path
        local server_name=$(basename "$dir")
        # Skip __pycache__ directory
        if [ "$server_name" != "__pycache__" ]; then
          servers+=("$server_name")
        fi
      fi
    done
  fi
  echo "${servers[@]}"
}

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
  OS="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  OS="Linux"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
  OS="Windows"
else
  OS="Unknown"
fi

print_message "Operating system detected: $OS" "$YELLOW"

# Check for Python
if ! command_exists python3; then
  print_message "Python 3 not found. Will attempt to install Python 3.11..." "$YELLOW"
  
  if [[ "$OS" == "macOS" ]]; then
    if ! command_exists brew; then
      print_message "Homebrew not found. Installing Homebrew..." "$YELLOW"
      /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
      
      # Add Homebrew to PATH
      if [[ -f ~/.zshrc ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
        eval "$(/opt/homebrew/bin/brew shellenv)"
      elif [[ -f ~/.bash_profile ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.bash_profile
        eval "$(/opt/homebrew/bin/brew shellenv)"
      fi
      
      print_message "Homebrew installed successfully." "$GREEN"
    fi
    
    print_message "Installing Python 3.11 with Homebrew..." "$YELLOW"
    brew install python@3.11
    
    # Add Python to PATH if needed
    if ! command_exists python3; then
      if [[ -f ~/.zshrc ]]; then
        echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zshrc
        export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"
      elif [[ -f ~/.bash_profile ]]; then
        echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.bash_profile
        export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"
      fi
    fi

  elif [[ "$OS" == "Linux" ]]; then
    if command_exists apt-get; then
      print_message "Installing Python 3.11 using apt..." "$YELLOW"
      sudo apt-get update
      sudo apt-get install -y python3.11 python3.11-venv python3-pip
      
      # Create symbolic link if needed
      if ! command_exists python3; then
        sudo ln -s /usr/bin/python3.11 /usr/bin/python3
      fi
      
    elif command_exists dnf; then
      print_message "Installing Python 3.11 using dnf..." "$YELLOW"
      sudo dnf install -y python3.11 python3.11-devel
      
      # Create symbolic link if needed
      if ! command_exists python3; then
        sudo ln -s /usr/bin/python3.11 /usr/bin/python3
      fi
      
    else
      print_message "Unable to install Python automatically on this Linux distribution." "$RED"
      print_message "Please install Python 3.11 manually and try again." "$RED"
      exit 1
    fi
  else
    print_message "Unsupported operating system: $OS" "$RED"
    print_message "Please install Python 3.11 manually and try again." "$RED"
    exit 1
  fi
  
  # Verify Python was installed
  if ! command_exists python3; then
    print_message "Failed to install Python 3. Please install it manually and try again." "$RED"
    exit 1
  else
    print_message "Python 3 installed successfully." "$GREEN"
  fi
fi

# Determine Python command to use
PYTHON_CMD="python3"
if ! command_exists python3 && command_exists python; then
  PYTHON_CMD="python"
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
print_message "Python version: $PYTHON_VERSION" "$YELLOW"

if [[ "$PYTHON_VERSION" < "3.11" ]]; then
  print_message "Python 3.11 or later is required. Found version $PYTHON_VERSION." "$RED"
  print_message "Please install Python 3.11 or later and try again." "$RED"
  exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  print_message "Creating virtual environment..." "$YELLOW"
  $PYTHON_CMD -m venv venv
  if [ $? -ne 0 ]; then
    print_message "Failed to create virtual environment." "$RED"
    print_message "Try installing the venv module: $PYTHON_CMD -m pip install virtualenv" "$RED"
    exit 1
  fi
  print_message "Virtual environment created successfully." "$GREEN"
else
  print_message "Virtual environment already exists." "$GREEN"
fi

# Activate virtual environment
source venv/bin/activate
if [ $? -ne 0 ]; then
  print_message "Failed to activate virtual environment." "$RED"
  exit 1
fi

# Check if activation was successful
if [ -z "$VIRTUAL_ENV" ]; then
  print_message "Failed to activate virtual environment." "$RED"
  exit 1
fi

print_message "Virtual environment activated." "$GREEN"

# Install dependencies
print_message "Installing dependencies..." "$YELLOW"
pip install -r requirements.txt || (print_message "Failed to install dependencies." "$RED" && exit 1)
print_message "Dependencies installed successfully." "$GREEN"

# Install dev dependencies
print_message "Installing dev dependencies..." "$YELLOW"
pip install -r requirements-dev.txt || (print_message "Failed to install dev dependencies." "$RED" && exit 1)
print_message "Dev dependencies installed successfully." "$GREEN"

# Get available servers
AVAILABLE_SERVERS=($(get_available_servers))

# If no servers found or directory doesn't exist
if [ ${#AVAILABLE_SERVERS[@]} -eq 0 ]; then
  print_message "No servers found in src/servers. Please check your installation." "$RED"
  exit 1
fi

# If a server name was provided as an argument, check if it's valid
SERVER=""
for arg in "$@"; do
  if [[ "$arg" != "--quiet" ]]; then
    SERVER=$arg
    VALID_SERVER=false
    
    for available_server in "${AVAILABLE_SERVERS[@]}"; do
      if [ "$SERVER" == "$available_server" ]; then
        VALID_SERVER=true
        break
      fi
    done
    
    if [ "$VALID_SERVER" = false ]; then
      print_message "Invalid server '$SERVER' specified." "$RED"
      SERVER=""
    fi
    break
  fi
done

# If no valid server specified, let the user choose
if [ -z "$SERVER" ]; then
  print_message "\nAvailable servers:" "$BLUE"
  for i in "${!AVAILABLE_SERVERS[@]}"; do
    echo "  $((i+1)). ${AVAILABLE_SERVERS[$i]}"
  done
  
  while true; do
    print_message "\nPlease select a server (1-${#AVAILABLE_SERVERS[@]}):" "$YELLOW"
    read -r selection
    
    if [[ "$selection" =~ ^[0-9]+$ ]] && [ "$selection" -ge 1 ] && [ "$selection" -le "${#AVAILABLE_SERVERS[@]}" ]; then
      SERVER="${AVAILABLE_SERVERS[$((selection-1))]}"
      break
    else
      print_message "Invalid selection. Please try again." "$RED"
    fi
  done
fi

# Run the server
print_message "\nStarting $SERVER..." "$GREEN"

# Build command
CMD="python src/servers/local.py --server=$SERVER"

# Execute the command - restore output for the server
if [ "$QUIET_MODE" = true ]; then
  # Restore stdout and stderr for the Python command
  exec > /dev/tty 2>&1
fi

# Run the server
$CMD

# Deactivate virtual environment when done
deactivate 