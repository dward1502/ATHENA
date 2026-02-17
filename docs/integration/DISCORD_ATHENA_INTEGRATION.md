> Legacy integration draft: use `docs/setup/INSTALL_CLEAR_BLUEFIN.md` and `docs/setup/CUTOVER_CHECKLIST_MAIN_PC.md` for active operations.

# DISCORD → OH MY OPENCODE → ATHENA INTEGRATION
**Complete Async Development System for Bluefin OS**

**Your Setup:**
- ✅ Bluefin OS (Fedora-based immutable OS)
- ✅ Discord hooked up
- ✅ Oh My OpenCode (Sisyphus agent system)
- ✅ Numenor Prime organized
- ✅ ATHENA warfare system (just built)

**What You Want:**
- Text Discord while doing other things
- System keeps building autonomously
- Get updates in Discord
- Reply in Discord to adjust/continue
- Oh My OpenCode's **`ultrawork`** (ulw) mode activates ATHENA

---

## ARCHITECTURE

```
You (anywhere)
    ↓
Discord Message: "ulw build PLUTUS agent"
    ↓
Discord Bot (receives message)
    ↓
Oh My OpenCode (with ultrawork mode)
    ↓
Calls: python athena.py --objective "Build PLUTUS" --priority CRITICAL
    ↓
ATHENA deploys divisions (APOLLO, ARES, ARTEMIS)
    ↓
Scouts → Integrates → Tests → Builds
    ↓
Updates sent back to Discord
    ↓
You reply "add invoice tracking"
    ↓
System continues building...
```

---

## STEP 1: DISCORD BOT SETUP

### Install Discord.py on Bluefin OS

```bash
# Bluefin uses toolbox for development
toolbox create athena-dev
toolbox enter athena-dev

# Inside toolbox:
pip install discord.py python-dotenv
```

### Create Discord Bot

**File:** `~/Numenor_prime/discord_bot/athena_bot.py`

```python
#!/usr/bin/env python3
"""
Discord Bot → Oh My OpenCode → ATHENA Integration
Allows async development via Discord commands
"""

import discord
from discord.ext import commands
import subprocess
import asyncio
import os
from pathlib import Path
from datetime import datetime

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Paths
ATHENA_DIR = Path.home() / "Numenor_prime" / "athena"
OPENCODE_DIR = Path.home() / "Numenor_prime"

# Active sessions tracking
active_sessions = {}


@bot.event
async def on_ready():
    print(f'🤖 ATHENA Bot ready: {bot.user}')
    print(f'   Connected to {len(bot.guilds)} servers')


@bot.command(name='athena')
async def athena_command(ctx, *, objective: str):
    """
    Deploy ATHENA for an objective
    Usage: !athena build PLUTUS financial agent
    """
    
    await ctx.send(f"⚔️  **ATHENA DEPLOYING**\n```Objective: {objective}```")
    
    # Create session ID
    session_id = f"ATHENA-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    # Store session
    active_sessions[session_id] = {
        'channel_id': ctx.channel.id,
        'objective': objective,
        'status': 'DEPLOYING'
    }
    
    # Run ATHENA
    try:
        result = subprocess.run([
            'python',
            str(ATHENA_DIR / 'athena.py'),
            '--objective', objective,
            '--deadline', '2026-02-19T23:59:59',
            '--priority', 'CRITICAL'
        ], capture_output=True, text=True, timeout=300)
        
        # Send result
        if result.returncode == 0:
            await ctx.send(f"✅ **MISSION ASSIGNED: {session_id}**\n```{result.stdout[:1500]}```")
            active_sessions[session_id]['status'] = 'IN_PROGRESS'
        else:
            await ctx.send(f"❌ **DEPLOYMENT FAILED**\n```{result.stderr[:1500]}```")
            active_sessions[session_id]['status'] = 'FAILED'
            
    except subprocess.TimeoutExpired:
        await ctx.send(f"⏰ **ATHENA working in background**\nSession: {session_id}")
        active_sessions[session_id]['status'] = 'BACKGROUND'


@bot.command(name='ulw')
async def ultrawork(ctx, *, task: str):
    """
    Ultra Work mode: OpenCode + ATHENA combined
    Usage: !ulw you are CEO, build PLUTUS agent with invoice tracking
    """
    
    await ctx.send(f"🔥 **ULTRA WORK MODE ACTIVATED**\n```{task}```")
    
    # Create workspace
    workspace_dir = OPENCODE_DIR / f"ulw-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    # Create OpenCode prompt file
    prompt_file = workspace_dir / "prompt.md"
    prompt_file.write_text(f"""
# ULTRA WORK MODE

{task}

## ATHENA Integration

You have access to ATHENA, an AI warfare system for code harvesting and integration.

To deploy ATHENA:
```bash
python ~/Numenor_prime/athena/athena.py --objective "your objective" --priority CRITICAL
```

ATHENA will:
1. Decompose objective into components
2. Deploy specialized divisions (APOLLO, ARES, ARTEMIS)
3. Scout GitHub for best implementations
4. Integrate code automatically
5. Run comprehensive testing
6. Deliver production-ready code

## Your Role

You are the CEO/Architect. ATHENA is your development army.
- Plan the architecture
- Deploy ATHENA for implementation
- Review and refine results
- Coordinate multiple agents

Work until task is 100% complete.
""")
    
    # Run OpenCode with ultrawork
    try:
        # Start OpenCode in background
        process = await asyncio.create_subprocess_exec(
            'opencode',
            '--prompt', str(prompt_file),
            '--workspace', str(workspace_dir),
            cwd=str(workspace_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await ctx.send(f"🚀 **OpenCode started in workspace:**\n`{workspace_dir}`\n\nMonitoring output...")
        
        # Stream output to Discord
        async def stream_output():
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                    
                message = line.decode().strip()
                if message:
                    # Send important updates to Discord
                    if any(keyword in message.lower() for keyword in 
                           ['athena', 'deploying', 'complete', 'error', 'warning']):
                        await ctx.send(f"```{message[:1900]}```")
                        
        # Start streaming
        asyncio.create_task(stream_output())
        
        # Wait for completion (with timeout)
        try:
            await asyncio.wait_for(process.wait(), timeout=3600)  # 1 hour max
            await ctx.send("✅ **ULTRA WORK COMPLETE**")
        except asyncio.TimeoutError:
            await ctx.send("⏰ **Still working... check workspace for progress**")
            
    except Exception as e:
        await ctx.send(f"❌ **Error:** ```{str(e)}```")


@bot.command(name='status')
async def status(ctx, session_id: str = None):
    """
    Check ATHENA status
    Usage: !status [session_id]
    """
    
    if session_id:
        # Check specific session
        if session_id in active_sessions:
            session = active_sessions[session_id]
            await ctx.send(f"📊 **Session {session_id}**\n"
                          f"```Status: {session['status']}\n"
                          f"Objective: {session['objective']}```")
        else:
            await ctx.send(f"❌ Session {session_id} not found")
    else:
        # List all sessions
        if not active_sessions:
            await ctx.send("No active sessions")
        else:
            status_text = "\n".join([
                f"{sid}: {s['status']} - {s['objective'][:50]}"
                for sid, s in active_sessions.items()
            ])
            await ctx.send(f"📊 **Active Sessions:**\n```{status_text}```")


@bot.command(name='continue')
async def continue_session(ctx, session_id: str, *, additional: str):
    """
    Continue/modify an ATHENA session
    Usage: !continue ATHENA-20260216-120000 add invoice tracking
    """
    
    if session_id not in active_sessions:
        await ctx.send(f"❌ Session {session_id} not found")
        return
        
    await ctx.send(f"🔄 **Continuing {session_id}**\n```{additional}```")
    
    # Re-run ATHENA with modified objective
    session = active_sessions[session_id]
    new_objective = f"{session['objective']} + {additional}"
    
    # Deploy ATHENA again
    await athena_command(ctx, objective=new_objective)


@bot.command(name='ceo')
async def ceo_mode(ctx, *, instruction: str):
    """
    CEO mode: High-level instruction
    Usage: !ceo build complete CITADEL system by Feb 19
    """
    
    await ctx.send(f"👔 **CEO INSTRUCTION RECEIVED**\n```{instruction}```")
    
    # This triggers ultrawork with CEO context
    ceo_task = f"""
You are the CEO. I need:

{instruction}

Break this down into:
1. Strategic plan
2. ATHENA deployments needed
3. Timeline with milestones
4. Execute autonomously

Use ATHENA for all implementation. Report progress to Discord.
"""
    
    await ultrawork(ctx, task=ceo_task)


# Run bot
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("❌ Set DISCORD_BOT_TOKEN environment variable")
        exit(1)
        
    bot.run(TOKEN)
```

---

## STEP 2: OH MY OPENCODE INTEGRATION

### Configure Oh My OpenCode to Call ATHENA

**File:** `~/.config/opencode/oh-my-opencode.json`

```jsonc
{
  // Add ATHENA as a custom agent
  "agents": {
    "athena": {
      "model": "anthropic/claude-opus-4-6",
      "temperature": 0.7,
      "systemPrompt": "You are ATHENA Supreme Commander. You command AI divisions to harvest, integrate, and deploy code. When given an objective, you decompose it, deploy divisions, and coordinate until victory.",
      "permissions": {
        "exec": true,
        "read": true,
        "write": true
      }
    },
    
    // Make Sisyphus aware of ATHENA
    "sisyphus": {
      "systemPrompt": "You are Sisyphus. You have access to ATHENA (~/Numenor_prime/athena/athena.py), an AI warfare system for code harvesting. When ultrawork mode is active, you can deploy ATHENA divisions for large-scale implementation tasks.",
      "permissions": {
        "exec": true
      }
    }
  },
  
  // Add custom command for ATHENA
  "commands": {
    "deploy-athena": {
      "description": "Deploy ATHENA for objective",
      "script": "python ~/Numenor_prime/athena/athena.py --objective \"$1\" --priority CRITICAL"
    }
  },
  
  // Hook ultrawork to ATHENA awareness
  "hooks": {
    "user_prompt_submit": [
      {
        "name": "athena_awareness",
        "enabled": true,
        "script": "if [[ \"$PROMPT\" == *\"ulw\"* ]] || [[ \"$PROMPT\" == *\"ultrawork\"* ]]; then echo 'ATHENA available at ~/Numenor_prime/athena/'; fi"
      }
    ]
  }
}
```

---

## STEP 3: BLUEFIN OS SYSTEMD SERVICE

Make the Discord bot run as a service on Bluefin:

**File:** `~/.config/systemd/user/athena-discord-bot.service`

```ini
[Unit]
Description=ATHENA Discord Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=%h/Numenor_prime/discord_bot
Environment="DISCORD_BOT_TOKEN=your_token_here"
ExecStart=/usr/bin/toolbox run --container athena-dev python athena_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
```

**Enable and start:**

```bash
systemctl --user enable athena-discord-bot
systemctl --user start athena-discord-bot
systemctl --user status athena-discord-bot
```

---

## STEP 4: USAGE WORKFLOW

### 1. Simple ATHENA Deployment

```
You (Discord): !athena build PLUTUS financial agent
Bot: ⚔️ ATHENA DEPLOYING...
     [ATHENA output]
Bot: ✅ MISSION ASSIGNED: ATHENA-20260216-120000
```

### 2. Ultra Work Mode (Full Power)

```
You (Discord): !ulw you are CEO, build complete PLUTUS agent with:
               - Invoice generation
               - Expense tracking  
               - Financial reporting
               - QuickBooks integration
               
Bot: 🔥 ULTRA WORK MODE ACTIVATED
     🚀 OpenCode started...
     [Real-time updates as it builds]
Bot: ⚔️ ATHENA DEPLOYING for invoice generation...
Bot: ✅ Invoice module complete
Bot: ⚔️ ATHENA DEPLOYING for expense tracking...
     [continues until done]
Bot: ✅ ULTRA WORK COMPLETE
```

### 3. CEO Mode (High-Level)

```
You (Discord): !ceo build complete CITADEL platform by Feb 19, 
               including ORACLE, PLUTUS, HERMES, APOLLO agents
               
Bot: 👔 CEO INSTRUCTION RECEIVED
     Breaking down into strategic plan...
     
     STRATEGIC PLAN:
     Day 1 (Feb 16): PLUTUS foundation
     Day 2 (Feb 17): ORACLE voice system
     Day 3 (Feb 18-19): Integration & testing
     
     Deploying ATHENA for PLUTUS...
```

### 4. Continue/Modify Running Task

```
You (Discord): !continue ATHENA-20260216-120000 add invoice PDF export

Bot: 🔄 Continuing session...
     ⚔️ ATHENA redeploying with updated objective...
```

### 5. Check Status Anytime

```
You (Discord): !status

Bot: 📊 Active Sessions:
     ATHENA-20260216-120000: IN_PROGRESS - Build PLUTUS agent
     ATHENA-20260216-140000: COMPLETE - Add invoice tracking
```

---

## HOW IT WORKS

### When You Type `!ulw ...`

1. **Discord bot receives message**
2. **Creates OpenCode workspace** with your task
3. **Injects ATHENA awareness** into Sisyphus's prompt
4. **OpenCode (Sisyphus) analyzes** task in ultrawork mode
5. **Sisyphus deploys ATHENA** via shell command:
   ```bash
   python ~/Numenor_prime/athena/athena.py --objective "Build PLUTUS"
   ```
6. **ATHENA executes:**
   - Decomposes into components
   - Deploys APOLLO/ARES/ARTEMIS divisions
   - Scouts GitHub for code
   - Integrates components
   - Runs tests
   - Delivers code

7. **Updates stream to Discord** in real-time
8. **You can reply** to modify/continue
9. **System keeps working** until complete

---

## CONFIGURATION FILES NEEDED

### 1. Environment Variables

**File:** `~/Numenor_prime/discord_bot/.env`

```bash
DISCORD_BOT_TOKEN=your_discord_bot_token_here
ATHENA_PATH=/home/yourusername/Numenor_prime/athena
OPENCODE_PATH=/home/yourusername/Numenor_prime
```

### 2. Get Discord Bot Token

1. Go to https://discord.com/developers/applications
2. Create New Application → "ATHENA Bot"
3. Bot → Add Bot
4. Copy Token
5. Bot Permissions: Send Messages, Read Messages, Use Slash Commands
6. Invite to your server

---

## FOLDER STRUCTURE

```
~/Numenor_prime/
├── athena/                      # ATHENA warfare system ✅
│   ├── athena.py
│   ├── olympians/
│   ├── heroes/
│   └── warriors/
│
├── discord_bot/                 # NEW: Discord integration
│   ├── athena_bot.py           # Main bot
│   └── .env                     # Bot token
│
├── citadel/                     # Your CITADEL agents
│   ├── PLUTUS/                 # ← Gets built by ATHENA
│   ├── ORACLE/
│   ├── HERMES/
│   └── APOLLO/
│
└── ulw-*/                      # OpenCode ultrawork sessions
    ├── prompt.md
    └── [generated code]
```

---

## ADVANTAGES

### 1. **True Async Development**
- Text Discord from phone/anywhere
- System keeps building while you do other things
- Get real-time updates

### 2. **Full Oh My OpenCode Power**
- Sisyphus orchestrates multiple agents
- Oracle for architecture
- Librarian for docs/code search
- Background agents work in parallel

### 3. **ATHENA Integration**
- Automatic code harvesting from GitHub
- Multi-division deployment
- Comprehensive testing
- Production-ready output

### 4. **Discord = Command Center**
- Visual progress updates
- Easy to modify mid-stream
- Share progress with team
- History of all builds

---

## EXAMPLE: BUILD PLUTUS BY FEB 19

**Feb 16 (Today) 3pm:**
```
You (Discord): !ceo build complete PLUTUS agent by Feb 19
```

**System Response:**
```
👔 CEO INSTRUCTION RECEIVED

STRATEGIC PLAN:
━━━━━━━━━━━━━━━━
📅 Day 1 (Feb 16): Foundation
   • Invoice data models
   • Database schema
   • Basic API structure
   
📅 Day 2 (Feb 17): Features
   • Invoice generation
   • Expense tracking
   • QuickBooks API integration
   
📅 Day 3 (Feb 18-19): Polish & Deploy
   • Testing & validation
   • Documentation
   • CITADEL integration

DEPLOYING ATHENA...
```

**3:15pm - ATHENA Update:**
```
⚔️ APOLLO division scouting invoice libraries...
   Found: invoice-generator, quickbooks-python
   
⚔️ ARES division building API layer...
   HYPERION deploying FastAPI framework
   
🔧 Integration engine combining components...
```

**5:00pm - You leave for dinner**

**6:30pm - Discord notification:**
```
✅ Invoice generation module COMPLETE
   Tests: 47/50 passed
   Coverage: 87%
   
⚔️ Moving to expense tracking...
```

**You reply from phone:**
```
You: !continue add PDF export for invoices
```

**System:**
```
🔄 Continuing with PDF export...
⚔️ ATHENA scouting PDF libraries...
```

**Feb 17, 9am - You wake up:**
```
✅ PLUTUS CORE COMPLETE
   • Invoice generation ✅
   • PDF export ✅  
   • Expense tracking ✅
   • QuickBooks sync ✅
   
Ready for testing phase.
```

---

## BLUEFIN OS NOTES

Since Bluefin is immutable:

1. **Use Toolbox for Python dev:**
   ```bash
   toolbox create athena-dev
   toolbox enter athena-dev
   pip install discord.py python-dotenv
   ```

2. **ATHENA files go in home:**
   - `~/Numenor_prime/` is persistent
   - System is immutable, home is not

3. **Systemd user services work normally**

4. **OpenCode install:**
   ```bash
   # In toolbox:
   npm install -g opencode
   npm install -g oh-my-opencode
   ```

---

## READY TO DEPLOY

**All you need:**

1. Set up Discord bot (10 min)
2. Copy `athena_bot.py` to `~/Numenor_prime/discord_bot/`
3. Add token to `.env`
4. Start service: `systemctl --user start athena-discord-bot`
5. Configure Oh My OpenCode
6. **TEXT DISCORD: `!ulw build PLUTUS`**
7. Go live your life while it builds

---

**This is how you hit the Feb 19 deadline while sipping coffee.** ☕

Let me know what part you want me to build first! 🎖️
