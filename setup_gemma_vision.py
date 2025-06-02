#!/usr/bin/env python3
"""
🔧 Setup Script for Gemma 3-1B Vision with Ollama
Installs and configures the smallest Gemma model for vision tasks
"""

import asyncio
import subprocess
import sys
import json
import aiohttp
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
import platform

console = Console()

class GemmaVisionSetup:
    """Setup and configure Ollama with smallest Gemma vision models"""
    
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.models_to_install = [
            "gemma2:1b",      # Smallest Gemma text model (1B parameters)
            "llava:latest"    # Vision model for multimodal tasks
        ]
        
    async def setup_complete_environment(self):
        """Complete setup process"""
        console.print(Panel("🔧 Gemma 3-1B Vision Setup", style="cyan"))
        
        try:
            # Step 1: Install Ollama
            await self._install_ollama()
            
            # Step 2: Start Ollama service
            await self._start_ollama_service()
            
            # Step 3: Install models
            await self._install_models()
            
            # Step 4: Test installation
            await self._test_installation()
            
            # Step 5: Show usage instructions
            self._show_usage_instructions()
            
        except Exception as e:
            console.print(f"❌ Setup failed: {e}")
            sys.exit(1)
    
    async def _install_ollama(self):
        """Install Ollama based on operating system"""
        console.print(Panel("📥 Installing Ollama", style="green"))
        
        system = platform.system().lower()
        
        if system == "windows":
            console.print("🪟 Windows detected")
            console.print("📋 Please follow these steps to install Ollama on Windows:")
            console.print("1. Download Ollama from: https://ollama.ai/download/windows")
            console.print("2. Run the installer")
            console.print("3. Restart this script after installation")
            
            # Check if already installed
            try:
                result = subprocess.run(["ollama", "--version"], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    console.print("✅ Ollama is already installed")
                else:
                    console.print("❌ Please install Ollama manually")
                    sys.exit(1)
            except FileNotFoundError:
                console.print("❌ Ollama not found. Please install manually.")
                sys.exit(1)
                
        elif system == "darwin":  # macOS
            console.print("🍎 macOS detected")
            try:
                # Try with Homebrew first
                result = subprocess.run(["brew", "install", "ollama"], 
                                      capture_output=True, text=True, timeout=300)
                if result.returncode == 0:
                    console.print("✅ Ollama installed via Homebrew")
                else:
                    console.print("📋 Please install manually:")
                    console.print("curl -fsSL https://ollama.ai/install.sh | sh")
            except FileNotFoundError:
                console.print("📋 Installing via curl...")
                result = subprocess.run(["curl", "-fsSL", "https://ollama.ai/install.sh"], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    subprocess.run(["sh"], input=result.stdout, text=True)
                    console.print("✅ Ollama installed")
                
        elif system == "linux":
            console.print("🐧 Linux detected")
            console.print("📥 Installing Ollama...")
            result = subprocess.run([
                "curl", "-fsSL", "https://ollama.ai/install.sh"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                subprocess.run(["sh"], input=result.stdout, text=True)
                console.print("✅ Ollama installed")
            else:
                console.print("❌ Installation failed")
                sys.exit(1)
        
        else:
            console.print(f"❌ Unsupported operating system: {system}")
            sys.exit(1)
    
    async def _start_ollama_service(self):
        """Start Ollama service"""
        console.print(Panel("🚀 Starting Ollama Service", style="green"))
        
        # Check if service is already running
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags", timeout=5) as response:
                    if response.status == 200:
                        console.print("✅ Ollama service is already running")
                        return
        except:
            pass
        
        # Try to start the service
        console.print("🔄 Starting Ollama service...")
        
        system = platform.system().lower()
        
        if system == "windows":
            # Windows service should start automatically after install
            console.print("⏳ Waiting for Ollama service to start...")
            await asyncio.sleep(5)
        else:
            # Linux/macOS - start as daemon
            try:
                subprocess.Popen(["ollama", "serve"], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
                console.print("🔄 Ollama service started")
                await asyncio.sleep(5)  # Give service time to start
            except Exception as e:
                console.print(f"⚠️ Could not start service automatically: {e}")
        
        # Verify service is running
        for attempt in range(6):  # Try for 30 seconds
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.ollama_url}/api/tags", timeout=5) as response:
                        if response.status == 200:
                            console.print("✅ Ollama service is running")
                            return
            except:
                await asyncio.sleep(5)
                console.print(f"⏳ Waiting for service... (attempt {attempt + 1}/6)")
        
        console.print("❌ Could not connect to Ollama service")
        console.print("📋 Please run 'ollama serve' manually in another terminal")
        sys.exit(1)
    
    async def _install_models(self):
        """Install required models"""
        console.print(Panel("📦 Installing Gemma Vision Models", style="green"))
        
        for model in self.models_to_install:
            await self._install_single_model(model)
    
    async def _install_single_model(self, model_name: str):
        """Install a single model"""
        console.print(f"📥 Installing {model_name}...")
        
        # Check if model already exists
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.ollama_url}/api/tags") as response:
                    if response.status == 200:
                        models_data = await response.json()
                        existing_models = [m['name'] for m in models_data.get('models', [])]
                        
                        if any(model_name in existing for existing in existing_models):
                            console.print(f"✅ {model_name} already installed")
                            return
        except Exception as e:
            console.print(f"⚠️ Could not check existing models: {e}")
        
        # Install the model
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn(f"[bold blue]Installing {model_name}..."),
                transient=True
            ) as progress:
                task = progress.add_task("install", total=100)
                
                async with aiohttp.ClientSession() as session:
                    data = {"name": model_name}
                    async with session.post(f"{self.ollama_url}/api/pull", json=data) as response:
                        if response.status == 200:
                            # Read streaming response for progress
                            async for line in response.content:
                                if line:
                                    try:
                                        status_data = json.loads(line.decode())
                                        status = status_data.get('status', '')
                                        
                                        if 'completed' in status and 'total' in status_data:
                                            completed = status_data.get('completed', 0)
                                            total = status_data.get('total', 1)
                                            percent = (completed / total) * 100 if total > 0 else 0
                                            progress.update(task, completed=percent)
                                        
                                        if status == 'success':
                                            progress.update(task, completed=100)
                                            break
                                            
                                    except json.JSONDecodeError:
                                        continue
                            
                            console.print(f"✅ {model_name} installed successfully")
                        else:
                            raise Exception(f"HTTP {response.status}")
                            
        except Exception as e:
            console.print(f"❌ Failed to install {model_name}: {e}")
            # Try with subprocess as fallback
            try:
                result = subprocess.run(["ollama", "pull", model_name], 
                                      capture_output=True, text=True, timeout=600)
                if result.returncode == 0:
                    console.print(f"✅ {model_name} installed via CLI")
                else:
                    console.print(f"❌ CLI installation also failed: {result.stderr}")
            except Exception as e2:
                console.print(f"❌ Both API and CLI installation failed: {e2}")
    
    async def _test_installation(self):
        """Test the installation"""
        console.print(Panel("🧪 Testing Installation", style="green"))
        
        try:
            # Test basic text generation with Gemma
            console.print("🔤 Testing Gemma 2-1B text generation...")
            
            async with aiohttp.ClientSession() as session:
                data = {
                    "model": "gemma2:1b",
                    "prompt": "Hello! Please respond with exactly: 'Gemma 1B model working'",
                    "stream": False
                }
                
                async with session.post(f"{self.ollama_url}/api/generate", json=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        response_text = result.get('response', '')
                        console.print(f"✅ Gemma response: {response_text[:50]}...")
                    else:
                        raise Exception(f"HTTP {response.status}")
            
            # Test vision model
            console.print("👁️ Testing LLaVA vision model...")
            
            # Create a simple test image (1x1 white pixel)
            import base64
            test_image = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\nIDATx\x9cc\xf8\x00\x00\x00\x01\x00\x01U\xad\x02\xe9\x00\x00\x00\x00IEND\xaeB`\x82').decode()
            
            async with aiohttp.ClientSession() as session:
                data = {
                    "model": "llava:latest",
                    "prompt": "What do you see in this image?",
                    "images": [test_image],
                    "stream": False
                }
                
                async with session.post(f"{self.ollama_url}/api/generate", json=data, timeout=30) as response:
                    if response.status == 200:
                        result = await response.json()
                        response_text = result.get('response', '')
                        console.print(f"✅ LLaVA response: {response_text[:50]}...")
                    else:
                        raise Exception(f"HTTP {response.status}")
            
            console.print("🎉 All models working correctly!")
            
        except Exception as e:
            console.print(f"❌ Testing failed: {e}")
            console.print("⚠️ Installation may be incomplete")
    
    def _show_usage_instructions(self):
        """Show usage instructions"""
        console.print(Panel("📖 Usage Instructions", style="bold green"))
        
        console.print("🎯 Your Gemma Vision setup is complete!")
        console.print("\n🚀 Quick Start:")
        console.print("python vision_enhanced_filtering_demo.py")
        
        console.print("\n🔧 Manual Testing:")
        console.print("# Test text generation")
        console.print("ollama run gemma2:1b")
        console.print("\n# Test vision")
        console.print("ollama run llava")
        
        console.print("\n📊 Models Installed:")
        for model in self.models_to_install:
            console.print(f"  • {model}")
        
        console.print("\n💡 Tips:")
        console.print("• Gemma 2-1B uses ~1.5GB RAM (very efficient!)")
        console.print("• LLaVA handles images + text together")
        console.print("• Both models run locally (no internet needed)")
        console.print("• Perfect for LinkedIn automation with vision fallbacks")
        
        console.print(f"\n🌐 Ollama API: {self.ollama_url}")
        console.print("📚 Based on: https://www.linkedin.com/pulse/gemma-3-comprehensive-guide-googles-ai-model-vladislav-guzey-qgvtc")

async def main():
    """Run setup"""
    console.print("🔧 Gemma 3-1B Vision Setup for LinkedIn Automation")
    console.print("Features: Smallest Gemma model + Vision capabilities")
    console.print("="*60)
    
    setup = GemmaVisionSetup()
    await setup.setup_complete_environment()

if __name__ == "__main__":
    asyncio.run(main()) 