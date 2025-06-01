"""
Browser Automation Service - Suna-inspired advanced browser control
Provides visual feedback, progress tracking, and real-time browser viewing
"""
import asyncio
import logging
import json
import base64
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn

logger = logging.getLogger(__name__)

@dataclass
class TaskProgress:
    """Track task progress like Suna's todo.md system"""
    task_id: str
    title: str
    status: str = "pending"  # pending, running, completed, failed
    progress: float = 0.0
    steps: List[str] = field(default_factory=list)
    current_step: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    screenshots: List[str] = field(default_factory=list)

@dataclass
class BrowserState:
    """Current browser state for real-time monitoring"""
    url: str = ""
    title: str = ""
    screenshot_base64: str = ""
    elements_found: int = 0
    viewport_width: int = 1366
    viewport_height: int = 768
    last_action: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

class SunaInspiredBrowserService:
    """Advanced browser automation service with Suna-inspired features"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.tasks: Dict[str, TaskProgress] = {}
        self.browser_state = BrowserState()
        self.connected_websockets: List[WebSocket] = []
        self.app = FastAPI()
        self.setup_routes()
        
        # Enhanced browser configuration inspired by Suna
        self.browser_config = {
            'viewport': {'width': 1366, 'height': 768},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'extra_http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Upgrade-Insecure-Requests': '1'
            }
        }
        
        # Create screenshots directory
        Path("data/screenshots").mkdir(parents=True, exist_ok=True)
    
    def setup_routes(self):
        """Setup FastAPI routes for browser interface"""
        
        @self.app.get("/")
        async def browser_interface():
            """Main browser interface"""
            return HTMLResponse(self.get_browser_interface_html())
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket for real-time browser updates"""
            await websocket.accept()
            self.connected_websockets.append(websocket)
            
            try:
                # Send initial state
                await websocket.send_json({
                    "type": "browser_state",
                    "data": {
                        "url": self.browser_state.url,
                        "title": self.browser_state.title,
                        "screenshot": self.browser_state.screenshot_base64,
                        "elements_found": self.browser_state.elements_found,
                        "last_action": self.browser_state.last_action
                    }
                })
                
                # Keep connection alive
                while True:
                    await websocket.receive_text()
                    
            except WebSocketDisconnect:
                self.connected_websockets.remove(websocket)
        
        @self.app.get("/api/tasks")
        async def get_tasks():
            """Get all tasks and their progress"""
            return {"tasks": [task.__dict__ for task in self.tasks.values()]}
        
        @self.app.get("/api/browser/screenshot")
        async def get_screenshot():
            """Get current browser screenshot"""
            if self.page:
                screenshot = await self.take_screenshot()
                return {"screenshot": screenshot}
            return {"screenshot": None}
    
    def get_browser_interface_html(self) -> str:
        """Generate HTML interface for browser viewing"""
        return """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI Job Agent - Live Browser View</title>
            <style>
                body { 
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                    margin: 0; 
                    padding: 20px; 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                .container { 
                    max-width: 1400px; 
                    margin: 0 auto; 
                    background: rgba(255,255,255,0.1);
                    border-radius: 20px;
                    padding: 30px;
                    backdrop-filter: blur(10px);
                }
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                }
                .header h1 {
                    font-size: 2.5em;
                    margin: 0;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                }
                .status-bar {
                    background: rgba(0,0,0,0.2);
                    padding: 15px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .browser-frame {
                    background: white;
                    border-radius: 15px;
                    overflow: hidden;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                    margin-bottom: 20px;
                }
                .browser-toolbar {
                    background: #f1f3f4;
                    color: #333;
                    padding: 10px 15px;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }
                .browser-buttons {
                    display: flex;
                    gap: 5px;
                }
                .browser-button {
                    width: 12px;
                    height: 12px;
                    border-radius: 50%;
                }
                .close { background: #ff5f57; }
                .minimize { background: #ffbd2e; }
                .maximize { background: #28ca42; }
                .url-bar {
                    flex: 1;
                    background: white;
                    border: 1px solid #ddd;
                    border-radius: 20px;
                    padding: 5px 15px;
                    margin-left: 15px;
                    font-size: 14px;
                }
                .browser-screen {
                    background: white;
                    min-height: 600px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    position: relative;
                }
                .browser-screen img {
                    max-width: 100%;
                    max-height: 600px;
                    border-radius: 0 0 15px 15px;
                }
                .task-panel {
                    background: rgba(0,0,0,0.2);
                    border-radius: 10px;
                    padding: 20px;
                }
                .task-item {
                    background: rgba(255,255,255,0.1);
                    margin: 10px 0;
                    padding: 15px;
                    border-radius: 8px;
                    border-left: 4px solid #4CAF50;
                }
                .progress-bar {
                    background: rgba(255,255,255,0.2);
                    height: 8px;
                    border-radius: 4px;
                    margin: 10px 0;
                    overflow: hidden;
                }
                .progress-fill {
                    background: #4CAF50;
                    height: 100%;
                    transition: width 0.3s ease;
                }
                .status-online { color: #4CAF50; }
                .status-offline { color: #f44336; }
                .loading {
                    color: #333;
                    font-size: 18px;
                    font-weight: bold;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🤖 AI Job Agent - Live Browser View</h1>
                    <p>Real-time browser automation inspired by Suna AI</p>
                </div>
                
                <div class="status-bar">
                    <div>
                        <strong>Connection Status:</strong> 
                        <span id="connection-status" class="status-offline">Disconnected</span>
                    </div>
                    <div>
                        <strong>Last Action:</strong> 
                        <span id="last-action">Initializing...</span>
                    </div>
                    <div>
                        <strong>Elements Found:</strong> 
                        <span id="elements-found">0</span>
                    </div>
                </div>
                
                <div class="browser-frame">
                    <div class="browser-toolbar">
                        <div class="browser-buttons">
                            <div class="browser-button close"></div>
                            <div class="browser-button minimize"></div>
                            <div class="browser-button maximize"></div>
                        </div>
                        <input type="text" class="url-bar" id="current-url" readonly placeholder="No page loaded">
                    </div>
                    <div class="browser-screen" id="browser-screen">
                        <div class="loading">🔄 Waiting for browser connection...</div>
                    </div>
                </div>
                
                <div class="task-panel">
                    <h3>📋 Task Progress</h3>
                    <div id="task-list">
                        <div class="task-item">
                            <div><strong>System Status:</strong> Ready</div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: 100%"></div>
                            </div>
                            <div><small>Browser automation service initialized</small></div>
                        </div>
                    </div>
                </div>
            </div>
            
            <script>
                let ws = null;
                let reconnectAttempts = 0;
                const maxReconnectAttempts = 5;
                
                function connectWebSocket() {
                    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                    const wsUrl = protocol + '//' + window.location.host + '/ws';
                    
                    ws = new WebSocket(wsUrl);
                    
                    ws.onopen = function() {
                        console.log('WebSocket connected');
                        document.getElementById('connection-status').textContent = 'Connected';
                        document.getElementById('connection-status').className = 'status-online';
                        reconnectAttempts = 0;
                    };
                    
                    ws.onmessage = function(event) {
                        const message = JSON.parse(event.data);
                        
                        if (message.type === 'browser_state') {
                            updateBrowserState(message.data);
                        } else if (message.type === 'task_progress') {
                            updateTaskProgress(message.data);
                        }
                    };
                    
                    ws.onclose = function() {
                        console.log('WebSocket disconnected');
                        document.getElementById('connection-status').textContent = 'Disconnected';
                        document.getElementById('connection-status').className = 'status-offline';
                        
                        // Attempt to reconnect
                        if (reconnectAttempts < maxReconnectAttempts) {
                            reconnectAttempts++;
                            setTimeout(connectWebSocket, 2000 * reconnectAttempts);
                        }
                    };
                    
                    ws.onerror = function(error) {
                        console.error('WebSocket error:', error);
                    };
                }
                
                function updateBrowserState(data) {
                    document.getElementById('current-url').value = data.url || 'No page loaded';
                    document.getElementById('last-action').textContent = data.last_action || 'Idle';
                    document.getElementById('elements-found').textContent = data.elements_found || 0;
                    
                    const browserScreen = document.getElementById('browser-screen');
                    if (data.screenshot) {
                        browserScreen.innerHTML = '<img src="data:image/png;base64,' + data.screenshot + '" alt="Browser Screenshot">';
                    } else {
                        browserScreen.innerHTML = '<div class="loading">🔄 Loading page...</div>';
                    }
                }
                
                function updateTaskProgress(tasks) {
                    const taskList = document.getElementById('task-list');
                    taskList.innerHTML = '';
                    
                    tasks.forEach(task => {
                        const taskItem = document.createElement('div');
                        taskItem.className = 'task-item';
                        taskItem.innerHTML = `
                            <div><strong>${task.title}</strong> - ${task.status}</div>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${task.progress}%"></div>
                            </div>
                            <div><small>${task.current_step || 'Waiting...'}</small></div>
                        `;
                        taskList.appendChild(taskItem);
                    });
                }
                
                // Initialize WebSocket connection
                connectWebSocket();
                
                // Refresh screenshot every 5 seconds
                setInterval(async function() {
                    if (ws && ws.readyState === WebSocket.OPEN) {
                        ws.send(JSON.stringify({type: 'ping'}));
                    }
                }, 5000);
            </script>
        </body>
        </html>
        """
    
    async def start_browser(self) -> bool:
        """Initialize browser with enhanced configuration"""
        try:
            logger.info("🚀 Starting enhanced browser automation service...")
            
            playwright = await async_playwright().start()
            
            # Launch browser with enhanced options
            self.browser = await playwright.chromium.launch(
                headless=False,  # Keep visible for debugging
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--no-sandbox',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-dev-shm-usage',
                    '--no-first-run',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ]
            )
            
            # Create context with enhanced settings
            self.context = await self.browser.new_context(
                viewport=self.browser_config['viewport'],
                user_agent=self.browser_config['user_agent'],
                extra_http_headers=self.browser_config['extra_http_headers'],
                locale='en-US',
                timezone_id='America/New_York'
            )
            
            # Add stealth scripts
            await self.context.add_init_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                
                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                
                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                
                // Mock chrome property
                window.chrome = {
                    runtime: {},
                };
            """)
            
            # Create page
            self.page = await self.context.new_page()
            
            logger.info("✅ Enhanced browser automation service started successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start browser: {e}")
            return False
    
    async def take_screenshot(self) -> str:
        """Take screenshot and return as base64"""
        if not self.page:
            return ""
        
        try:
            screenshot_bytes = await self.page.screenshot(
                type="png",
                full_page=False
            )
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode()
            
            # Save screenshot to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"data/screenshots/browser_{timestamp}.png"
            with open(screenshot_path, "wb") as f:
                f.write(screenshot_bytes)
            
            return screenshot_base64
            
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return ""
    
    async def update_browser_state(self, action: str = ""):
        """Update browser state and notify connected clients"""
        if not self.page:
            return
        
        try:
            # Get current page info
            url = self.page.url
            title = await self.page.title()
            screenshot = await self.take_screenshot()
            
            # Count elements on page
            elements_count = await self.page.evaluate("""
                () => {
                    const elements = document.querySelectorAll('a, button, input, select, textarea');
                    return elements.length;
                }
            """)
            
            # Update state
            self.browser_state = BrowserState(
                url=url,
                title=title,
                screenshot_base64=screenshot,
                elements_found=elements_count,
                last_action=action,
                timestamp=datetime.now()
            )
            
            # Notify connected WebSocket clients
            message = {
                "type": "browser_state",
                "data": {
                    "url": url,
                    "title": title,
                    "screenshot": screenshot,
                    "elements_found": elements_count,
                    "last_action": action
                }
            }
            
            # Send to all connected clients
            for websocket in self.connected_websockets.copy():
                try:
                    await websocket.send_json(message)
                except:
                    self.connected_websockets.remove(websocket)
            
        except Exception as e:
            logger.error(f"Failed to update browser state: {e}")
    
    async def navigate_to(self, url: str, task_id: str = None) -> bool:
        """Navigate to URL with progress tracking"""
        if not self.page:
            await self.start_browser()
        
        try:
            if task_id:
                await self.update_task_progress(task_id, f"Navigating to {url}", 10)
            
            logger.info(f"🌐 Navigating to: {url}")
            
            response = await self.page.goto(
                url, 
                wait_until='domcontentloaded',
                timeout=30000
            )
            
            await self.update_browser_state(f"Navigated to {url}")
            
            if task_id:
                await self.update_task_progress(task_id, f"Successfully loaded {url}", 30)
            
            success = response and response.status == 200
            if success:
                logger.info(f"✅ Successfully navigated to {url}")
            else:
                logger.warning(f"⚠️ Navigation warning - Status: {response.status if response else 'No response'}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Navigation failed: {e}")
            if task_id:
                await self.update_task_progress(task_id, f"Navigation failed: {str(e)}", error=str(e))
            return False
    
    async def create_task(self, title: str, steps: List[str] = None) -> str:
        """Create a new task with progress tracking"""
        task_id = f"task_{int(time.time())}"
        task = TaskProgress(
            task_id=task_id,
            title=title,
            steps=steps or [],
            start_time=datetime.now()
        )
        self.tasks[task_id] = task
        
        logger.info(f"📋 Created task: {title} (ID: {task_id})")
        await self.broadcast_task_update()
        return task_id
    
    async def update_task_progress(self, task_id: str, current_step: str, progress: float, error: str = None):
        """Update task progress"""
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        task.current_step = current_step
        task.progress = min(100, max(0, progress))
        
        if error:
            task.status = "failed"
            task.error_message = error
            task.end_time = datetime.now()
        elif progress >= 100:
            task.status = "completed"
            task.end_time = datetime.now()
        else:
            task.status = "running"
        
        logger.info(f"📊 Task {task_id}: {current_step} ({progress}%)")
        await self.broadcast_task_update()
    
    async def broadcast_task_update(self):
        """Broadcast task updates to connected clients"""
        message = {
            "type": "task_progress",
            "data": [task.__dict__ for task in self.tasks.values()]
        }
        
        for websocket in self.connected_websockets.copy():
            try:
                await websocket.send_json(message)
            except:
                self.connected_websockets.remove(websocket)
    
    async def enhanced_job_search(self, site_name: str, keywords: str, num_results: int = 10) -> Dict[str, Any]:
        """Enhanced job search with visual feedback and progress tracking"""
        task_id = await self.create_task(
            f"Job Search: {keywords} on {site_name}",
            ["Initialize browser", "Navigate to site", "Search jobs", "Extract data", "Process results"]
        )
        
        try:
            await self.update_task_progress(task_id, "Initializing browser automation", 5)
            
            if not self.page:
                await self.start_browser()
            
            await self.update_task_progress(task_id, f"Navigating to {site_name}", 15)
            
            # This would be called by the actual scrapers
            results = {
                "task_id": task_id,
                "site_name": site_name,
                "keywords": keywords,
                "status": "ready_for_scraper",
                "browser_ready": True
            }
            
            await self.update_task_progress(task_id, "Browser ready for job scraping", 25)
            
            return results
            
        except Exception as e:
            await self.update_task_progress(task_id, f"Failed to initialize: {str(e)}", error=str(e))
            raise e
    
    async def close(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            logger.info("🔄 Browser automation service closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
    
    def start_server(self, host: str = "localhost", port: int = 8080):
        """Start the browser interface server"""
        logger.info(f"🌐 Starting browser interface server at http://{host}:{port}")
        uvicorn.run(self.app, host=host, port=port)

# Global instance for use across the application
browser_service = SunaInspiredBrowserService() 