#!/usr/bin/env python3
"""
MCP BI Assistant Setup Script
Automates the installation and configuration process
"""

import os
import sys
import subprocess
import json
import platform
from pathlib import Path
from typing import Dict, Any

class BIAssistantSetup:
    def __init__(self):
        self.system = platform.system()
        self.python_executable = sys.executable
        self.project_root = Path.cwd()
        self.venv_path = self.project_root / "bi_venv"
        
    def print_header(self, text: str):
        """Print formatted header"""
        print(f"\n{'='*60}")
        print(f" {text}")
        print(f"{'='*60}")
    
    def print_step(self, step: int, total: int, description: str):
        """Print step information"""
        print(f"\n📋 Step {step}/{total}: {description}")
    
    def run_command(self, command: str, description: str = None) -> bool:
        """Run shell command and return success status"""
        if description:
            print(f"   Running: {description}")
        
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                check=True, 
                capture_output=True, 
                text=True
            )
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error: {e}")
            if e.stderr:
                print(f"   Error details: {e.stderr}")
            return False
    
    def check_prerequisites(self) -> bool:
        """Check system prerequisites"""
        self.print_step(1, 8, "Checking Prerequisites")
        
        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 11):
            print(f"   ❌ Python 3.11+ required. Found: {python_version.major}.{python_version.minor}")
            return False
        print(f"   ✅ Python version: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # Check pip
        if not self.run_command("pip --version", "Checking pip"):
            print("   ❌ pip not found. Please install pip.")
            return False
        print("   ✅ pip is available")
        
        # Check PostgreSQL (optional)
        if self.run_command("psql --version", "Checking PostgreSQL"):
            print("   ✅ PostgreSQL is available")
        else:
            print("   ⚠️  PostgreSQL not found. You can install it later or use SQLite for development.")
        
        # Check git
        if self.run_command("git --version", "Checking git"):
            print("   ✅ Git is available")
        else:
            print("   ⚠️  Git not found but not required for basic setup")
        
        return True
    
    def create_virtual_environment(self) -> bool:
        """Create and activate virtual environment"""
        self.print_step(2, 8, "Creating Virtual Environment")
        
        if self.venv_path.exists():
            print(f"   Virtual environment already exists at {self.venv_path}")
            return True
        
        if not self.run_command(f"{self.python_executable} -m venv {self.venv_path}", "Creating virtual environment"):
            return False
        
        print(f"   ✅ Virtual environment created at {self.venv_path}")
        return True
    
    def install_dependencies(self) -> bool:
        """Install Python dependencies"""
        self.print_step(3, 8, "Installing Dependencies")
        
        # Get pip path for virtual environment
        if self.system == "Windows":
            pip_path = self.venv_path / "Scripts" / "pip"
            python_path = self.venv_path / "Scripts" / "python"
        else:
            pip_path = self.venv_path / "bin" / "pip"
            python_path = self.venv_path / "bin" / "python"
        
        # Create requirements.txt if it doesn't exist
        requirements_content = """# MCP BI Assistant Server Requirements
mcp>=1.0.0
asyncpg>=0.29.0
psycopg2-binary>=2.9.9
sqlalchemy>=2.0.25
pandas>=2.1.4
python-dotenv>=1.0.0
structlog>=23.2.0
pytest>=7.4.3
pytest-asyncio>=0.21.1"""
        
        requirements_path = self.project_root / "requirements.txt"
        if not requirements_path.exists():
            with open(requirements_path, 'w') as f:
                f.write(requirements_content)
            print("   Created requirements.txt")
        
        # Upgrade pip first
        if not self.run_command(f"{python_path} -m pip install --upgrade pip", "Upgrading pip"):
            return False
        
        # Install requirements
        if not self.run_command(f"{pip_path} install -r requirements.txt", "Installing dependencies"):
            return False
        
        print("   ✅ Dependencies installed successfully")
        return True
    
    def setup_database(self) -> bool:
        """Setup database configuration"""
        self.print_step(4, 8, "Setting up Database Configuration")
        
        # Create .env file if it doesn't exist
        env_path = self.project_root / ".env"
        if env_path.exists():
            print("   .env file already exists")
            return True
        
        # Get database configuration from user
        print("   Database setup options:")
        print("   1. PostgreSQL (recommended for production)")
        print("   2. SQLite (for development/testing)")
        
        choice = input("   Enter choice (1 or 2): ").strip()
        
        if choice == "1":
            # PostgreSQL setup
            db_host = input("   Database host [localhost]: ").strip() or "localhost"
            db_port = input("   Database port [5432]: ").strip() or "5432"
            db_name = input("   Database name [bi_assistant]: ").strip() or "bi_assistant"
            db_user = input("   Database username: ").strip()
            db_password = input("   Database password: ").strip()
            
            database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            
            # Test connection
            print("   Testing database connection...")
            test_command = f"psql '{database_url}' -c 'SELECT 1;'"
            if not self.run_command(test_command, "Testing PostgreSQL connection"):
                print("   ⚠️  Database connection test failed. Please verify credentials.")
                print("   You can update the DATABASE_URL in .env later.")
        
        elif choice == "2":
            # SQLite setup
            db_path = input("   SQLite database path [./db/bi_assistant.db]: ").strip() or "./db/bi_assistant.db"
            database_url = f"sqlite:///{db_path}"
        
        else:
            print("   Invalid choice. Using default SQLite configuration.")
            database_url = "sqlite:///./bi_assistant.db"
        
        # Create .env file
        env_content = f"""# Database Configuration
DATABASE_URL={database_url}

# Logging Configuration
LOG_LEVEL=INFO

# MCP Server Configuration
MCP_SERVER_NAME=bi-assistant
MCP_SERVER_VERSION=1.0.0

# Database Pool Settings
DB_POOL_MIN_SIZE=1
DB_POOL_MAX_SIZE=10
DB_COMMAND_TIMEOUT=60
"""
        
        with open(env_path, 'w') as f:
            f.write(env_content)
        
        print(f"   ✅ Created .env file with database URL: {database_url}")
        return True
    
    def create_database_schema(self) -> bool:
        """Create database schema and sample data"""
        self.print_step(5, 8, "Creating Database Schema")
        
        # Check if schema SQL file exists
        schema_path = self.project_root / "database_schema.sql"
        if not schema_path.exists():
            print("   ❌ database_schema.sql not found. Please ensure the SQL file is in the project directory.")
            return False
        
        # Load database URL from .env
        env_path = self.project_root / ".env"
        if not env_path.exists():
            print("   ❌ .env file not found. Please run the database setup step first.")
            return False
        
        # Simple .env parser for DATABASE_URL
        database_url = None
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith('DATABASE_URL='):
                    database_url = line.split('=', 1)[1].strip()
                    break
        
        if not database_url:
            print("   ❌ DATABASE_URL not found in .env file.")
            return False
        
        if database_url.startswith('postgresql://'):
            # PostgreSQL schema creation
            if self.run_command(f"psql '{database_url}' -f {schema_path}", "Creating PostgreSQL schema"):
                print("   ✅ PostgreSQL schema created successfully")
                return True
            else:
                print("   ❌ Failed to create PostgreSQL schema")
                return False
        
        elif database_url.startswith('sqlite://'):
            # SQLite schema creation (would need adaptation)
            print("   ⚠️  SQLite schema creation not implemented in this setup script.")
            print("   Please manually run the schema SQL with sqlite3 or use PostgreSQL.")
            return True
        
        return False
    
    def create_claude_config(self) -> bool:
        """Create Claude Desktop configuration"""
        self.print_step(6, 8, "Creating Claude Desktop Configuration")
        
        # Get absolute path to server script
        server_script_path = self.project_root / "server" / "bi_server.py"
        
        # Get Python executable path in virtual environment
        if self.system == "Windows":
            python_path = self.venv_path / "Scripts" / "python.exe"
        else:
            python_path = self.venv_path / "bin" / "python"
        
        # Claude Desktop config paths
        if self.system == "Darwin":  # macOS
            config_dir = Path.home() / "Library" / "Application Support" / "Claude"
        elif self.system == "Windows":
            config_dir = Path(os.getenv("APPDATA")) / "Claude"
        else:  # Linux
            config_dir = Path.home() / ".config" / "claude"
        
        config_file = config_dir / "claude_desktop_config.json"
        
        # Create config directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing config or create new one
        config = {}
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
            except json.JSONDecodeError:
                print("   ⚠️  Existing config file is invalid JSON. Creating backup.")
                backup_file = config_file.with_suffix('.json.backup')
                config_file.rename(backup_file)
                config = {}
        
        # Add or update MCP server configuration
        if "mcpServers" not in config:
            config["mcpServers"] = {}
        
        # Get DATABASE_URL from .env
        database_url = None
        env_path = self.project_root / ".env"
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('DATABASE_URL='):
                        database_url = line.split('=', 1)[1].strip()
                        break
        
        config["mcpServers"]["bi-assistant"] = {
            "command": str(python_path),
            "args": [str(server_script_path)],
            "env": {
                "DATABASE_URL": database_url or "sqlite:///D:\\Confiz\\Project 8- AI Powered BI Bot\\model\\db\\bi_assistant.db"
            }
        }
        
        # Save config
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"   ✅ Claude Desktop configuration created at {config_file}")
        print(f"   Server command: {python_path} {server_script_path}")
        return True
    
    def run_tests(self) -> bool:
        """Run validation tests"""
        self.print_step(7, 8, "Running Validation Tests")
        
        # Check if test script exists
        test_script_path = self.project_root / "test_bi_assistant.py"
        if not test_script_path.exists():
            print("   ⚠️  test_bi_assistant.py not found. Skipping tests.")
            return True
        
        # Get Python executable path in virtual environment
        if self.system == "Windows":
            python_path = self.venv_path / "Scripts" / "python"
        else:
            python_path = self.venv_path / "bin" / "python"
        
        if self.run_command(f"{python_path} {test_script_path}", "Running validation tests"):
            print("   ✅ All tests passed!")
            return True
        else:
            print("   ⚠️  Some tests failed. Please check the output above.")
            return True  # Don't fail setup for test failures
    
    def display_next_steps(self):
        """Display next steps to user"""
        self.print_step(8, 8, "Setup Complete!")
        
        print("\n🎉 MCP BI Assistant setup completed successfully!")
        
        print("\n📋 Next Steps:")
        print("1. Start the MCP server:")
        if self.system == "Windows":
            python_cmd = f"{self.venv_path}\\Scripts\\python"
        else:
            python_cmd = f"{self.venv_path}/bin/python"
        
        print(f"   {python_cmd} server/bi_server.py")
        
        print("\n2. Open Claude Desktop application")
        print("   - It should automatically detect the MCP server")
        print("   - Look for the 🔧 tools icon in the interface")
        
        print("\n3. Try these sample queries:")
        sample_queries = [
            "What was the ROAS for Product A in Month 5?",
            "Show me all performance metrics for Product B",
            "Which product had the highest ROI?",
            "Compare ROAS across all products for Month 6"
        ]
        
        for i, query in enumerate(sample_queries, 1):
            print(f"   {i}. \"{query}\"")
        
        print(f"\n📖 Documentation:")
        print(f"   - README.md: Comprehensive usage guide")
        print(f"   - Database schema: database_schema.sql")
        print(f"   - Test validation: test_bi_assistant.py")
        
        print(f"\n⚙️  Configuration files created:")
        print(f"   - Environment: .env")
        print(f"   - Python dependencies: requirements.txt")
        print(f"   - Virtual environment: {self.venv_path}")
        
        if self.system == "Darwin":  # macOS
            config_path = "~/Library/Application Support/Claude/claude_desktop_config.json"
        elif self.system == "Windows":
            config_path = "%APPDATA%\\Claude\\claude_desktop_config.json"
        else:
            config_path = "~/.config/claude/claude_desktop_config.json"
        
        print(f"   - Claude Desktop config: {config_path}")
    
    def run_setup(self) -> bool:
        """Run the complete setup process"""
        self.print_header("MCP BI Assistant Setup")
        print("This script will set up the MCP-powered BI Assistant system.")
        print(f"Project directory: {self.project_root}")
        print(f"Python executable: {self.python_executable}")
        print(f"Operating system: {self.system}")
        
        steps = [
            ("Check Prerequisites", self.check_prerequisites),
            ("Create Virtual Environment", self.create_virtual_environment),
            ("Install Dependencies", self.install_dependencies),
            ("Setup Database", self.setup_database),
            ("Create Database Schema", self.create_database_schema),
            ("Create Claude Config", self.create_claude_config),
            ("Run Tests", self.run_tests),
            ("Display Next Steps", lambda: (self.display_next_steps(), True)[1])
        ]
        
        for i, (step_name, step_func) in enumerate(steps, 1):
            try:
                if not step_func():
                    print(f"\n❌ Setup failed at: {step_name}")
                    return False
            except Exception as e:
                print(f"\n❌ Setup failed at: {step_name}")
                print(f"Error: {e}")
                return False
        
        return True

def main():
    """Main setup function"""
    setup = BIAssistantSetup()
    
    try:
        success = setup.run_setup()
        if success:
            print("\n✅ Setup completed successfully!")
            return True
        else:
            print("\n❌ Setup failed. Please review the errors above.")
            return False
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user.")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error during setup: {e}")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)