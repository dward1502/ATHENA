# CITADEL COORDINATOR
**Lightweight Agent Management for Production Runtime**

## Architecture

```
User Request
    ↓
CITADEL Coordinator (lightweight Python service)
    ↓
Request Queue (priority-based)
    ↓
Model Manager (loads/unloads efficiently)
    ↓
Agent Execution (one at a time, fast switching)
    ↓
Response to User
```

**Key Difference from ATHENA:**
- ATHENA: "Deploy all divisions, work in parallel, finish ASAP"
- CITADEL: "Queue requests, execute serially, optimize for responsiveness"

---

## FILE: `~/Numenor_prime/citadel/coordinator.py`

```python
#!/usr/bin/env python3
"""
CITADEL Coordinator
Manages agent execution on resource-constrained hardware
"""

import asyncio
from dataclasses import dataclass
from typing import Optional, Dict
from enum import Enum
import time
from pathlib import Path

class Priority(Enum):
    CRITICAL = 1   # User waiting actively
    HIGH = 2       # Time-sensitive
    NORMAL = 3     # Background processing
    LOW = 4        # Batch jobs


@dataclass
class AgentRequest:
    """Single agent execution request"""
    agent_name: str
    task: str
    priority: Priority
    timestamp: float
    user_id: Optional[str] = None
    
    def __lt__(self, other):
        # Higher priority = lower number = executed first
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.timestamp < other.timestamp


class ModelManager:
    """Manages model loading/unloading for memory efficiency"""
    
    def __init__(self, max_vram_gb: float = 6.0):
        self.max_vram_gb = max_vram_gb
        self.currently_loaded: Optional[str] = None
        self.models = {
            "PLUTUS": "qwen3.5:7b-instruct-q4_K_M",    # 4GB
            "HERMES": "qwen3.5:7b-instruct-q4_K_M",    # 4GB
            "ORACLE": "qwen3.5:3b-instruct-fp16",      # 2GB
            "APOLLO": "qwen3.5:7b-instruct-q4_K_M",    # 4GB
        }
        self.vram_usage = {
            "qwen3.5:7b-instruct-q4_K_M": 4.0,
            "qwen3.5:3b-instruct-fp16": 2.0,
        }
    
    async def load_model(self, agent_name: str) -> bool:
        """Load model for agent, unload previous if needed"""
        
        model = self.models.get(agent_name)
        if not model:
            return False
        
        # If same model already loaded, reuse it
        if self.currently_loaded == model:
            print(f"♻️  Reusing loaded model: {model}")
            return True
        
        # Unload previous model
        if self.currently_loaded:
            print(f"📤 Unloading: {self.currently_loaded}")
            await self._unload_model()
        
        # Load new model
        print(f"📥 Loading: {model} for {agent_name}")
        await self._load_model(model)
        self.currently_loaded = model
        
        return True
    
    async def _load_model(self, model: str):
        """Actually load the model (calls Ollama)"""
        # In production, this would call Ollama API
        # For now, simulate load time
        await asyncio.sleep(2)  # Model load takes ~2 seconds
    
    async def _unload_model(self):
        """Unload current model to free VRAM"""
        # In production, this would stop Ollama model
        await asyncio.sleep(0.5)
        self.currently_loaded = None


class Agent:
    """Base CITADEL agent"""
    
    def __init__(self, name: str, model_manager: ModelManager):
        self.name = name
        self.model_manager = model_manager
    
    async def execute(self, task: str) -> str:
        """Execute agent task"""
        
        # Ensure model is loaded
        await self.model_manager.load_model(self.name)
        
        # Execute task (simplified - would call Ollama in production)
        print(f"⚙️  {self.name} executing: {task[:50]}...")
        
        # Simulate execution time
        await asyncio.sleep(1)
        
        return f"{self.name} completed: {task}"


class CitadelCoordinator:
    """Main coordinator for CITADEL agents"""
    
    def __init__(self, max_vram_gb: float = 6.0):
        self.model_manager = ModelManager(max_vram_gb)
        self.request_queue = asyncio.PriorityQueue()
        self.agents: Dict[str, Agent] = {}
        self.is_processing = False
        self.stats = {
            "total_requests": 0,
            "completed": 0,
            "avg_wait_time": 0.0
        }
        
        # Initialize agents
        for agent_name in ["PLUTUS", "HERMES", "ORACLE", "APOLLO"]:
            self.agents[agent_name] = Agent(agent_name, self.model_manager)
    
    async def submit_request(
        self, 
        agent_name: str, 
        task: str, 
        priority: Priority = Priority.NORMAL,
        user_id: Optional[str] = None
    ) -> str:
        """Submit a request to an agent"""
        
        if agent_name not in self.agents:
            return f"Error: Unknown agent {agent_name}"
        
        request = AgentRequest(
            agent_name=agent_name,
            task=task,
            priority=priority,
            timestamp=time.time(),
            user_id=user_id
        )
        
        await self.request_queue.put(request)
        self.stats["total_requests"] += 1
        
        print(f"📨 Request queued: {agent_name} ({priority.name})")
        print(f"   Queue size: {self.request_queue.qsize()}")
        
        # Start processor if not running
        if not self.is_processing:
            asyncio.create_task(self._process_queue())
        
        return f"Request queued for {agent_name}"
    
    async def _process_queue(self):
        """Process requests from queue"""
        
        if self.is_processing:
            return
        
        self.is_processing = True
        
        while not self.request_queue.empty():
            # Get highest priority request
            request = await self.request_queue.get()
            
            wait_time = time.time() - request.timestamp
            print(f"\n🎯 Processing: {request.agent_name}")
            print(f"   Priority: {request.priority.name}")
            print(f"   Wait time: {wait_time:.1f}s")
            
            # Execute
            agent = self.agents[request.agent_name]
            result = await agent.execute(request.task)
            
            # Update stats
            self.stats["completed"] += 1
            self.stats["avg_wait_time"] = (
                (self.stats["avg_wait_time"] * (self.stats["completed"] - 1) + wait_time) 
                / self.stats["completed"]
            )
            
            print(f"✅ Completed: {result[:50]}...")
        
        self.is_processing = False
        print("\n💤 Queue empty, coordinator idle")
    
    def get_status(self) -> Dict:
        """Get coordinator status"""
        return {
            "queue_size": self.request_queue.qsize(),
            "is_processing": self.is_processing,
            "loaded_model": self.model_manager.currently_loaded,
            "stats": self.stats
        }


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demonstrate CITADEL Coordinator"""
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                   CITADEL COORDINATOR DEMO                    ║
║                                                               ║
║  Simulating multiple agent requests on limited hardware      ║
╚═══════════════════════════════════════════════════════════════╝
    """)
    
    coordinator = CitadelCoordinator(max_vram_gb=6.0)
    
    # Simulate various requests
    print("\n📋 Submitting requests...\n")
    
    # Background task (low priority)
    await coordinator.submit_request(
        "APOLLO", 
        "Generate weekly analytics report",
        priority=Priority.LOW
    )
    
    # User waiting (critical priority)
    await coordinator.submit_request(
        "PLUTUS",
        "Generate invoice #1234",
        priority=Priority.CRITICAL,
        user_id="owner"
    )
    
    # Normal task
    await coordinator.submit_request(
        "HERMES",
        "Draft email to client about project update",
        priority=Priority.NORMAL
    )
    
    # Another user task (critical)
    await coordinator.submit_request(
        "ORACLE",
        "Process voice command: what's on my calendar?",
        priority=Priority.CRITICAL,
        user_id="owner"
    )
    
    # Wait for processing
    await asyncio.sleep(15)
    
    # Show final stats
    print("\n" + "="*60)
    status = coordinator.get_status()
    print(f"📊 Final Status:")
    print(f"   Requests processed: {status['stats']['completed']}")
    print(f"   Average wait time: {status['stats']['avg_wait_time']:.1f}s")
    print(f"   Queue: {status['queue_size']} pending")


if __name__ == "__main__":
    asyncio.run(demo())
```

---

## OPTIMIZATIONS FOR BEELINK

### 1. Model Sharing (Most Agents Use Same Model)

```python
# Instead of loading different models:
PLUTUS → Qwen 7B (load)
HERMES → Qwen 7B (reuse!) ← NO RELOAD NEEDED
APOLLO → Qwen 7B (reuse!) ← NO RELOAD NEEDED

# Only ORACLE is different:
ORACLE → Qwen 3B (reload)
```

**Result:** Most requests don't trigger model reload

### 2. Keep-Alive (Don't Unload Between Requests)

```python
class ModelManager:
    def __init__(self, keep_alive_seconds: int = 300):
        self.keep_alive = keep_alive_seconds
        self.last_used = time.time()
    
    async def maybe_unload(self):
        """Only unload if idle for keep_alive seconds"""
        if time.time() - self.last_used > self.keep_alive:
            await self._unload_model()
```

### 3. Predictive Loading

```python
# If user just used PLUTUS, they might use HERMES next
# Both use same model, so keep it loaded

USAGE_PATTERNS = {
    "PLUTUS": ["HERMES", "APOLLO"],  # Often followed by these
    "HERMES": ["PLUTUS"],
    "ORACLE": ["HERMES"]
}
```

---

## COMPARISON TABLE

| Aspect | ATHENA (Development) | CITADEL (Production) |
|--------|---------------------|---------------------|
| **Purpose** | Build new software | Run business operations |
| **Execution** | Parallel (all divisions) | Serial (one at a time) |
| **Hardware** | High (multiple GPUs ideal) | Modest (single 8GB shared) |
| **Duration** | Hours to days | 24/7/365 |
| **Optimization** | Speed to completion | Resource efficiency |
| **User Pattern** | Single user (dev) | Multiple users (business) |
| **Model Loading** | Keep all loaded | Load/unload as needed |
| **Priority** | Finish ASAP | Respond to user quickly |

---

## DEPLOYMENT STRATEGY

### For Your Beelink SER9:

```
1. Build with ATHENA (on RTX 3080 machine)
   ├─ Use full ATHENA system
   ├─ Deploy all divisions
   ├─ Build PLUTUS, ORACLE, HERMES, APOLLO
   └─ Takes 3 days, uses heavy compute

2. Deploy to CITADEL (on Beelink SER9)
   ├─ Use CITADEL Coordinator
   ├─ Load models efficiently
   ├─ Queue user requests
   └─ Runs forever, light compute
```

**Analogy:**
- ATHENA = **Factory** (builds cars, heavy machinery)
- CITADEL = **Dealership** (sells/services cars, light operations)

---

## BENEFITS FOR SMALL BUSINESS

### Owner Experience:

**Without Coordinator (Slow):**
```
Owner: "PLUTUS, generate invoices" [waits 5 min]
Owner: "HERMES, draft email" [waits 3 min for model swap]
Owner: 😡 "This is too slow!"
```

**With Coordinator (Fast):**
```
Owner: "PLUTUS, generate invoices" [queued, CRITICAL priority]
         → Executes immediately (2 min)
Owner: "HERMES, draft email" [queued, CRITICAL priority]
         → Uses same model, no reload (30 sec)
Owner: 😊 "This is great!"
```

### Background Tasks Still Work:

```
System: [Queue = PLUTUS (CRITICAL), HERMES (CRITICAL), APOLLO (LOW)]
        → Process PLUTUS first
        → Process HERMES second (same model, fast)
        → Process APOLLO when idle (owner not waiting)
```

---

## CONFIGURATION FILE

```yaml
# ~/Numenor_prime/citadel/config.yaml

hardware:
  max_vram_gb: 6.0
  keep_alive_seconds: 300  # Keep model loaded 5 min
  
agents:
  PLUTUS:
    model: "qwen3.5:7b-instruct-q4_K_M"
    priority_boost: true  # Owner requests get CRITICAL
    
  HERMES:
    model: "qwen3.5:7b-instruct-q4_K_M"
    priority_boost: true
    
  ORACLE:
    model: "qwen3.5:3b-instruct-fp16"
    priority_boost: true
    
  APOLLO:
    model: "qwen3.5:7b-instruct-q4_K_M"
    priority_boost: false  # Background only

optimization:
  enable_model_sharing: true
  predictive_loading: true
  batch_similar_requests: true
```

---

## SUMMARY

**Your Insight:**
> "ATHENA concept is good but applied differently for CITADEL"

**You're 100% right:**

✅ **ATHENA:** Build new systems (development time)
- Heavy parallel execution
- All divisions deployed
- Finish as fast as possible
- Use on powerful hardware (RTX 3080)

✅ **CITADEL:** Run business operations (runtime)
- Efficient serial execution
- One agent at a time
- Respond to users quickly
- Works great on Beelink SER9

**Best of both worlds:**
1. Build PLUTUS/ORACLE/HERMES/APOLLO with ATHENA (RTX 3080, 3 days)
2. Deploy to CITADEL Coordinator (Beelink SER9, runs forever)
3. Small business gets responsive AI operations on modest hardware

**The Beelink SER9 is PERFECT for CITADEL runtime.** 🎖️
