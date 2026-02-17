RECOMMENDED SETUP FOR ATHENA:
Hybrid Strategy (Use What You Have)
ATHENA COMMAND STRUCTURE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TIER 1: Strategic Planning (Cloud API - Expensive but Necessary)
├─ ATHENA Supreme: Claude Opus 4.6
├─ APOLLO: Claude Sonnet 4.6
├─ ARES: Claude Sonnet 4.6
└─ ARTEMIS: Claude Sonnet 4.6

TIER 2: Tactical Execution (Local - RTX 3080)
├─ PROMETHEUS: Qwen3.5-14B INT4
├─ HYPERION: Qwen3.5-14B INT4
├─ HADES: Qwen3.5-14B INT4
├─ HELIOS: Qwen3.5-7B FP16
├─ ORPHEUS: Qwen3.5-7B FP16
└─ ORION: Qwen3.5-7B FP16

TIER 3: Reconnaissance (Local - Beelink SER9)
├─ ACHILLES: Qwen3.5-7B INT4
├─ ODYSSEUS: Qwen3.5-7B INT4
├─ PERSEUS: Qwen3.5-3B FP16
└─ Background Tasks: Qwen3.5-3B FP16

For Your Bluefin OS Setup:
Primary Workstation: 5700X + RTX 3080
bash# Run main Titans here
ollama serve  # Start Ollama server
ollama pull qwen3.5:14b-instruct-q4_K_M  # ~8GB VRAM
ollama pull qwen3.5:7b-instruct-fp16     # ~14GB VRAM

Secondary: Beelink SER9 Pro
bash# Run scout agents here
ollama serve --port 11435  # Different port
ollama pull qwen3.5:7b-instruct-q4_K_M   # ~4GB
ollama pull qwen3.5:3b-instruct-fp16     # ~6GB

# Only use when absolutely needed
CLAUDE_API_KEY=xxx

RTX 3080 Setup:

bash   # Install Ollama
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Pull optimized models
   ollama pull qwen3.5:14b-instruct-q4_K_M  # Main Titans
   ollama pull qwen3.5:7b-instruct-q4_K_M   # Fast execution

Beelink SER9 Setup:

bash   # Same on Beelink
   ollama pull qwen3.5:7b-instruct-q4_K_M   # Scouts
   ollama pull qwen3.5:3b-instruct-fp16     # Background

ATHENA Configuration:

python   # Use hybrid approach
   STRATEGIC = "claude"  # $20 for 3-day build
   TITANS = "qwen-14b"   # Free (RTX 3080)
   SCOUTS = "qwen-7b"    # Free (Beelink)
   BACKGROUND = "qwen-3b"  # Free (Beelink)
   
   Phase 1: Build (Your RTX 3080 Workstation)
   bash# You (CEO): Build PLUTUS
   cd ~/Numenor_prime
   !ulw build PLUTUS financial agent with QuickBooks integration
   
   # Sisyphus activates ATHENA
   # ATHENA deploys APOLLO, ARES, ARTEMIS divisions
   # Scouts find best code on GitHub
   # Integrates into working PLUTUS agent
   # ARTEMIS validates (95%+ test pass rate)
   
   # Export as container
   cd citadel/pods/plutus-pod
   podman build -t plutus:v1.0 .
   podman save plutus:v1.0 > plutus-v1.0.tar
   
   # Same for ORACLE, HERMES, APOLLO
   Phase 2: Deploy (Customer Beelink SER9)
   bash# Transfer containers
   scp plutus-v1.0.tar customer@beelink:~/containers/
   scp oracle-v1.0.tar customer@beelink:~/containers/
   scp hermes-v1.0.tar customer@beelink:~/containers/
   scp apollo-v1.0.tar customer@beelink:~/containers/
   
   # Load on Beelink
   ssh customer@beelink
   cd ~/containers
   for tar in *.tar; do podman load < $tar; done
   
   # Create pods
   ./setup_citadel_pods.sh
   
   # Start coordinator
   systemctl --user enable citadel-coordinator
   systemctl --user start citadel-coordinator
   ```
   
   ### **Phase 3: Run (Customer Uses CITADEL)**
   ```
   Customer: "PLUTUS, generate this month's invoices"
            ↓
   CITADEL Coordinator receives request
            ↓
   Checks: Is plutus-pod running? No.
   Checks: Can we fit it? Yes (only oracle-pod running, using 2GB)
            ↓
   Starts plutus-pod (loads Qwen 7B, ~4GB VRAM)
            ↓
   Executes: Generate invoices
            ↓
   Returns: "Generated 47 invoices, total $23,450"
            ↓
   Waits 5 minutes idle → Stops plutus-pod (frees 4GB VRAM)
   ```
   
   ---
   
   ## **RESOURCE MATH ON BEELINK SER9:**
   
   ### **Available Resources:**
   ```
   Total VRAM (shared): 8GB
   Total RAM: 32GB DDR5
   CPUs: 16 threads (8C/16T)
   ```
   
   ### **Pod Configurations:**
   
   | Pod | Model | VRAM | RAM | Can Run Together? |
   |-----|-------|------|-----|-------------------|
   | **plutus-pod** | Qwen 7B | 4GB | 2GB | ✅ + oracle-pod |
   | **oracle-pod** | Qwen 3B | 2GB | 1GB | ✅ + any other |
   | **hermes-pod** | Qwen 7B | 4GB | 2GB | ✅ + oracle-pod |
   | **apollo-pod** | Qwen 7B | 4GB | 2GB | ✅ + oracle-pod |
   
   ### **Allowed Combinations:**
   
   **Scenario 1: Owner actively working**
   ```
   Running: plutus-pod (4GB) + oracle-pod (2GB) = 6GB VRAM
   Free: 2GB VRAM buffer
   Status: ✅ Responsive
   ```
   
   **Scenario 2: Background analytics**
   ```
   Running: apollo-pod (4GB) only
   Free: 4GB VRAM
   Status: ✅ Room for urgent requests
   ```
   
   **Scenario 3: All idle**
   ```
   Running: None
   Free: 8GB VRAM
   Status: ✅ Maximum resources available
   Power: Minimal (all pods stopped)
   ```
