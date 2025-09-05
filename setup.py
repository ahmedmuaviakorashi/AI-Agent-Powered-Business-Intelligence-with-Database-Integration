#!/usr/bin/env python3
"""
Simplified MCP BI Assistant Setup Script
"""

import os
import sys
import subprocess
import json
import platform
from pathlib import Path

class BIAssistantSetup:
    def __init__(self):
        self.system = platform.system()
        self.project_root = Path.cwd()
        
    def print_step(self, step: int, total: int, description: str):
        """Print step information"""
        print(f"\n📋 Step {step}/{total}: {description}")
    
    def run_command(self, command: str, description: str = None) -> bool:
        """Run shell command and return success status"""
        if description:
            print(f"   {description}...")
        
        try:
            result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
            if result.stdout.strip():
                print(f"   ✅ {result.stdout.strip()}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error: {e}")
            return False
    
    def create_database(self) -> bool:
        """Create SQLite database with sample data"""
        self.print_step(1, 3, "Creating Database")
        
        # Check if db.py exists
        if not (self.project_root / "db.py").exists():
            print("   ❌ db.py not found")
            return False
        
        return self.run_command(f"{sys.executable} db.py", "Creating database and sample data")
    
    def create_claude_config(self) -> bool:
        """Create Claude Desktop configuration"""
        self.print_step(2, 3, "Creating Claude Desktop Configuration")
        
        # Get paths
        server_path = self.project_root / "bi_server.py"
        
        # Check if bi_server.py exists
        if not server_path.exists():
            print("   ❌ bi_server.py not found")
            return False
        
        # Claude config directory
        if self.system == "Darwin":  # macOS
            config_dir = Path.home() / "Library/Application Support/Claude"
        elif self.system == "Windows":
            config_dir = Path(os.getenv("APPDATA")) / "Claude"
        else:  # Linux
            config_dir = Path.home() / ".config/claude"
        
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "claude_desktop_config.json"
        
        # Load existing config or create new
        config = {}
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
            except json.JSONDecodeError:
                config = {}
        
        # Add BI Assistant server
        if "mcpServers" not in config:
            config["mcpServers"] = {}
        
        config["mcpServers"]["bi-assistant"] = {
            "command": "python",
            "args": [str(server_path)],
            "env": {
                "DATABASE_URL": f"sqlite:///{self.project_root}/bi_assistant.db"
            }
        }
        
        # Save config
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"   ✅ Configuration saved to {config_file}")
        return True
    
    def setup_bi_server(self) -> bool:
        """Check and setup BI server"""
        self.print_step(3, 3, "Setting up BI Server")
        
        server_path = self.project_root / "bi_server.py"
        
        if not server_path.exists():
            print("   ❌ bi_server.py not found")
            print("   💡 Please ensure bi_server.py is in the project directory")
            return False
        
        print(f"   ✅ BI server found at {server_path}")
        
        # Test if server can be imported (basic validation)
        try:
            test_command = f'{sys.executable} -c "import sys; sys.path.append(r\'{self.project_root}\'); import bi_server; print(\'Server validation successful\')"'
            if self.run_command(test_command, "Validating BI server"):
                return True
        except Exception as e:
            print(f"   ⚠️ Server validation failed: {e}")
        
        return True  # Continue even if validation fails
    
    def display_completion(self):
        """Display completion message and next steps"""
        print("\n🎉 Setup completed successfully!")
        print("\n📋 Next Steps:")
        print(f'1. Start the server: python "{self.project_root / "bi_server.py"}"')
        print("2. Open Claude Desktop (it will auto-detect the server)")
        print("3. Look for the 🔧 tools icon")
        print("\n💡 Try these queries:")
        print('   - "Show me the database schema"')
        print('   - "What was the ROAS for Product A in month 5?"')
        print('   - "Which product had the highest ROI?"')
        
        print(f"\n📁 Files created:")
        print(f"   - Database: {self.project_root}/bi_assistant.db")
        print("   - Claude config updated")
    
    def run_setup(self) -> bool:
        """Run the complete setup process"""
        print("🚀 MCP BI Assistant Setup")
        print(f"📂 Project: {self.project_root}")
        print(f"🖥️  System: {self.system}")
        
        steps = [
            self.create_database,
            self.create_claude_config,
            self.setup_bi_server
        ]
        
        for step_func in steps:
            try:
                if not step_func():
                    return False
            except Exception as e:
                print(f"   ❌ Error: {e}")
                return False
        
        self.display_completion()
        return True

def main():
    """Main setup function"""
    setup = BIAssistantSetup()
    
    try:
        if setup.run_setup():
            print("\n✅ Setup successful!")
        else:
            print("\n❌ Setup failed!")
            return False
    except KeyboardInterrupt:
        print("\n⚠️ Setup interrupted")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)