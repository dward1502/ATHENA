#!/usr/bin/env python3
"""
CITADEL Pod Coordinator
Manages Podman containers for CITADEL agents on BluefinOS

Key Features:
- Start/stop pods on demand (save resources)
- Only one heavy pod running at a time
- Intelligent queuing with pod lifecycle
- Auto-shutdown idle pods
"""

import asyncio
import subprocess
from dataclasses import dataclass
from typing import Optional, Dict, List
from enum import Enum
import time
from pathlib import Path


class PodState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"


class Priority(Enum):
    CRITICAL = 1   # User waiting now
    HIGH = 2       # Time-sensitive
    NORMAL = 3     # Background
    LOW = 4        # Batch jobs


@dataclass
class AgentRequest:
    """Request for an agent"""
    agent_name: str
    task: str
    priority: Priority
    timestamp: float
    user_id: Optional[str] = None
    
    def __lt__(self, other):
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.timestamp < other.timestamp


class PodManager:
    """Manages Podman pod lifecycle"""
    
    def __init__(self):
        self.pods = {
            "PLUTUS": "plutus-pod",
            "ORACLE": "oracle-pod", 
            "HERMES": "hermes-pod",
            "APOLLO": "apollo-pod"
        }
        
        # Resource requirements (estimated VRAM/RAM)
        self.pod_resources = {
            "plutus-pod": {"vram": 4.0, "ram": 2.0},
            "oracle-pod": {"vram": 2.0, "ram": 1.0},
            "hermes-pod": {"vram": 4.0, "ram": 2.0},
            "apollo-pod": {"vram": 4.0, "ram": 2.0}
        }
        
        self.pod_states: Dict[str, PodState] = {}
        self.last_used: Dict[str, float] = {}
        self.idle_timeout = 300  # Stop pods after 5 min idle
        
        # Check which pods are running
        self._sync_pod_states()
    
    def _sync_pod_states(self):
        """Check actual pod states"""
        for agent, pod_name in self.pods.items():
            state = self._get_pod_state(pod_name)
            self.pod_states[pod_name] = state
    
    def _get_pod_state(self, pod_name: str) -> PodState:
        """Get current state of a pod"""
        try:
            result = subprocess.run(
                ['podman', 'pod', 'ps', '--filter', f'name={pod_name}', '--format', '{{.Status}}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if 'Running' in result.stdout:
                return PodState.RUNNING
            elif result.stdout.strip():
                return PodState.STOPPED
            else:
                # Pod doesn't exist
                return PodState.STOPPED
                
        except subprocess.TimeoutExpired:
            return PodState.STOPPED
    
    async def start_pod(self, agent_name: str) -> bool:
        """Start pod for agent"""
        
        pod_name = self.pods.get(agent_name)
        if not pod_name:
            print(f"❌ Unknown agent: {agent_name}")
            return False
        
        current_state = self.pod_states.get(pod_name, PodState.STOPPED)
        
        if current_state == PodState.RUNNING:
            print(f"♻️  Pod already running: {pod_name}")
            self.last_used[pod_name] = time.time()
            return True
        
        if current_state == PodState.STARTING:
            print(f"⏳ Pod starting: {pod_name}")
            await self._wait_for_pod(pod_name)
            return True
        
        # Start the pod
        print(f"🚀 Starting pod: {pod_name}")
        self.pod_states[pod_name] = PodState.STARTING
        
        try:
            result = subprocess.run(
                ['podman', 'pod', 'start', pod_name],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                self.pod_states[pod_name] = PodState.RUNNING
                self.last_used[pod_name] = time.time()
                print(f"✅ Pod started: {pod_name}")
                
                # Wait for services to be ready
                await asyncio.sleep(3)
                return True
            else:
                print(f"❌ Failed to start {pod_name}: {result.stderr}")
                self.pod_states[pod_name] = PodState.STOPPED
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏱️  Timeout starting {pod_name}")
            self.pod_states[pod_name] = PodState.STOPPED
            return False
    
    async def stop_pod(self, pod_name: str):
        """Stop a pod"""
        
        if self.pod_states.get(pod_name) != PodState.RUNNING:
            return
        
        print(f"🛑 Stopping pod: {pod_name}")
        self.pod_states[pod_name] = PodState.STOPPING
        
        subprocess.run(
            ['podman', 'pod', 'stop', pod_name],
            capture_output=True,
            timeout=10
        )
        
        self.pod_states[pod_name] = PodState.STOPPED
        print(f"💤 Pod stopped: {pod_name}")
    
    async def _wait_for_pod(self, pod_name: str, timeout: int = 30):
        """Wait for pod to be running"""
        start = time.time()
        while time.time() - start < timeout:
            if self.pod_states.get(pod_name) == PodState.RUNNING:
                return True
            await asyncio.sleep(0.5)
        return False
    
    async def stop_idle_pods(self):
        """Stop pods that have been idle"""
        current_time = time.time()
        
        for pod_name, last_used in list(self.last_used.items()):
            if current_time - last_used > self.idle_timeout:
                if self.pod_states.get(pod_name) == PodState.RUNNING:
                    print(f"⏰ Pod idle for {self.idle_timeout}s: {pod_name}")
                    await self.stop_pod(pod_name)
    
    def get_running_pods(self) -> List[str]:
        """Get list of running pods"""
        return [
            pod for pod, state in self.pod_states.items()
            if state == PodState.RUNNING
        ]


class CitadelPodCoordinator:
    """Coordinates CITADEL agents via Podman pods"""
    
    def __init__(self, max_concurrent_pods: int = 2):
        self.pod_manager = PodManager()
        self.request_queue = asyncio.PriorityQueue()
        self.max_concurrent_pods = max_concurrent_pods
        self.is_processing = False
        
        self.stats = {
            "total_requests": 0,
            "completed": 0,
            "avg_wait_time": 0.0,
            "pod_starts": 0,
            "pod_stops": 0
        }
    
    async def submit_request(
        self,
        agent_name: str,
        task: str,
        priority: Priority = Priority.NORMAL,
        user_id: Optional[str] = None
    ) -> str:
        """Submit request to agent"""
        
        request = AgentRequest(
            agent_name=agent_name,
            task=task,
            priority=priority,
            timestamp=time.time(),
            user_id=user_id
        )
        
        await self.request_queue.put(request)
        self.stats["total_requests"] += 1
        
        print(f"\n📨 Request queued: {agent_name} ({priority.name})")
        print(f"   Task: {task[:60]}...")
        print(f"   Queue size: {self.request_queue.qsize()}")
        
        # Start processor if not running
        if not self.is_processing:
            asyncio.create_task(self._process_queue())
        
        # Start idle pod killer
        asyncio.create_task(self._idle_pod_killer())
        
        return f"Request queued for {agent_name}"
    
    async def _process_queue(self):
        """Process requests from queue"""
        
        if self.is_processing:
            return
        
        self.is_processing = True
        
        while not self.request_queue.empty():
            request = await self.request_queue.get()
            
            wait_time = time.time() - request.timestamp
            
            print(f"\n{'='*60}")
            print(f"🎯 Processing Request")
            print(f"   Agent: {request.agent_name}")
            print(f"   Priority: {request.priority.name}")
            print(f"   Wait time: {wait_time:.1f}s")
            
            # Check if we need to stop other pods
            running_pods = self.pod_manager.get_running_pods()
            pod_name = self.pod_manager.pods.get(request.agent_name)
            
            # If too many pods running and this isn't one of them
            if (len(running_pods) >= self.max_concurrent_pods and 
                pod_name not in running_pods):
                
                # Stop oldest pod
                oldest_pod = min(
                    running_pods,
                    key=lambda p: self.pod_manager.last_used.get(p, 0)
                )
                print(f"⚠️  Max pods reached, stopping: {oldest_pod}")
                await self.pod_manager.stop_pod(oldest_pod)
                self.stats["pod_stops"] += 1
            
            # Start pod for this agent
            pod_started = await self.pod_manager.start_pod(request.agent_name)
            
            if pod_started:
                self.stats["pod_starts"] += 1
                
                # Execute task
                result = await self._execute_task(request)
                
                # Update stats
                self.stats["completed"] += 1
                self.stats["avg_wait_time"] = (
                    (self.stats["avg_wait_time"] * (self.stats["completed"] - 1) + wait_time)
                    / self.stats["completed"]
                )
                
                print(f"✅ Task completed")
            else:
                print(f"❌ Failed to start pod for {request.agent_name}")
        
        self.is_processing = False
        print(f"\n💤 Queue empty, coordinator idle")
        print(f"   Running pods: {self.pod_manager.get_running_pods()}")
    
    async def _execute_task(self, request: AgentRequest) -> str:
        """Execute task in pod"""
        
        pod_name = self.pod_manager.pods[request.agent_name]
        
        # In production, this would send request to pod's API endpoint
        # For demo, simulate execution
        print(f"⚙️  Executing in {pod_name}...")
        await asyncio.sleep(2)  # Simulate work
        
        return f"Completed: {request.task}"
    
    async def _idle_pod_killer(self):
        """Background task to stop idle pods"""
        while True:
            await asyncio.sleep(60)  # Check every minute
            await self.pod_manager.stop_idle_pods()
    
    def get_status(self) -> Dict:
        """Get coordinator status"""
        return {
            "queue_size": self.request_queue.qsize(),
            "is_processing": self.is_processing,
            "running_pods": self.pod_manager.get_running_pods(),
            "stats": self.stats
        }


# ============================================================================
# DEMO
# ============================================================================

async def demo():
    """Demo pod-based CITADEL"""
    
    print("""
╔═══════════════════════════════════════════════════════════════╗
║            CITADEL POD COORDINATOR (BluefinOS)                ║
║                                                               ║
║  Demonstrates intelligent pod lifecycle management           ║
╚═══════════════════════════════════════════════════════════════╝

Scenario: Small business on Beelink SER9
- Limited resources (8GB shared VRAM)
- Only 2 pods can run simultaneously
- Pods auto-start on demand
- Pods auto-stop when idle
    """)
    
    coordinator = CitadelPodCoordinator(max_concurrent_pods=2)
    
    print("\n" + "="*60)
    print("📋 SIMULATING BUSINESS DAY")
    print("="*60)
    
    # Morning: Owner generates invoices
    print("\n🌅 MORNING: Invoice generation")
    await coordinator.submit_request(
        "PLUTUS",
        "Generate invoices for all outstanding work orders",
        priority=Priority.CRITICAL,
        user_id="owner"
    )
    
    await asyncio.sleep(5)
    
    # Owner wants to send emails
    print("\n📧 MORNING: Email drafting")
    await coordinator.submit_request(
        "HERMES",
        "Draft follow-up emails to 5 clients",
        priority=Priority.CRITICAL,
        user_id="owner"
    )
    
    await asyncio.sleep(5)
    
    # Background analytics (low priority)
    print("\n📊 BACKGROUND: Analytics")
    await coordinator.submit_request(
        "APOLLO",
        "Generate weekly performance report",
        priority=Priority.LOW
    )
    
    await asyncio.sleep(5)
    
    # Owner uses voice interface
    print("\n🎤 MIDDAY: Voice query")
    await coordinator.submit_request(
        "ORACLE",
        "What's on my calendar today?",
        priority=Priority.CRITICAL,
        user_id="owner"
    )
    
    await asyncio.sleep(10)
    
    # Show final status
    print("\n" + "="*60)
    print("📊 FINAL STATUS")
    print("="*60)
    
    status = coordinator.get_status()
    print(f"\nRequests processed: {status['stats']['completed']}")
    print(f"Average wait time: {status['stats']['avg_wait_time']:.1f}s")
    print(f"Pod starts: {status['stats']['pod_starts']}")
    print(f"Pod stops: {status['stats']['pod_stops']}")
    print(f"Currently running: {status['running_pods']}")
    
    print("""
💡 BENEFITS:
   ✅ Only necessary pods running (saves VRAM/RAM)
   ✅ Critical tasks get priority
   ✅ Automatic resource management
   ✅ Idle pods auto-shutdown
   ✅ Perfect for small business Beelink hardware
    """)


if __name__ == "__main__":
    asyncio.run(demo())
