# NUMENOR PRIME DOCUMENTATION CENTER

## Problem: AI Agents Don't Have Access to Library Docs

**What happens now:**
1. You install `discord.py`
2. Agent tries to use it
3. Agent doesn't have docs in context
4. Agent hallucinates API or asks you
5. You waste time explaining

**What should happen:**
1. You install `discord.py`
2. Documentation automatically available
3. Agent checks docs before coding
4. Code works first try

---

## SOLUTION: `/docs` Directory Structure

```
~/Numenor_prime/
├── docs/                           # ← DOCUMENTATION CENTER
│   ├── README.md                   # Index of all docs
│   ├── INSTRUCTIONS.md             # How agents should use this
│   │
│   ├── apis/                       # External APIs
│   │   ├── discord.md             # Discord.py reference
│   │   ├── anthropic.md           # Claude API
│   │   ├── openai.md              # OpenAI API
│   │   └── github.md              # GitHub API
│   │
│   ├── frameworks/                 # Frameworks & libraries
│   │   ├── oh-my-opencode.md     # Oh My OpenCode config
│   │   ├── redplanet-core.md     # RedPlanet Core MCP
│   │   ├── openclaw.md           # OpenClaw setup
│   │   └── fastapi.md            # FastAPI reference
│   │
│   ├── systems/                    # Your systems
│   │   ├── athena.md              # ATHENA architecture
│   │   ├── citadel.md             # CITADEL agents
│   │   ├── numenor-structure.md  # This project structure
│   │   └── bluefin-os.md         # Bluefin OS specifics
│   │
│   ├── patterns/                   # Design patterns
│   │   ├── async-agents.md        # Async agent patterns
│   │   ├── discord-bots.md        # Discord bot patterns
│   │   ├── tmux-sessions.md       # Tmux integration
│   │   └── mcp-integration.md     # MCP server patterns
│   │
│   └── references/                 # Quick references
│       ├── commands.md            # All CLI commands
│       ├── environment.md         # Environment variables
│       └── troubleshooting.md     # Common issues
│
├── athena/                        # Your code
├── citadel/
└── discord_bot/
```

---

## AUTO-DOCUMENTATION SCRIPT

**File:** `~/Numenor_prime/scripts/sync_docs.sh`

```bash
#!/bin/bash
# Automatically sync documentation when you install packages

DOCS_DIR="$HOME/Numenor_prime/docs"

# Function to fetch and save docs
fetch_docs() {
    local package=$1
    local category=$2
    local url=$3
    
    echo "📥 Fetching docs for $package..."
    
    mkdir -p "$DOCS_DIR/$category"
    
    # Fetch with curl or use local if available
    if [ -n "$url" ]; then
        curl -s "$url" > "$DOCS_DIR/$category/$package.md"
    fi
}

# Discord.py
if pip list | grep -q discord.py; then
    fetch_docs "discord" "apis" "https://raw.githubusercontent.com/Rapptz/discord.py/master/README.md"
    
    # Also create a curated reference
    cat > "$DOCS_DIR/apis/discord.md" << 'EOF'
# Discord.py Quick Reference

## Bot Setup

```python
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Bot ready: {bot.user}')

@bot.command()
async def hello(ctx):
    await ctx.send('Hello!')

bot.run(TOKEN)
```

## Commands

```python
@bot.command(name='build')
async def build_command(ctx, *, args: str):
    """Command with arguments"""
    await ctx.send(f"Building: {args}")
```

## Background Tasks

```python
from discord.ext import tasks

@tasks.loop(seconds=60)
async def my_background_task():
    # Runs every 60 seconds
    pass

@bot.event
async def on_ready():
    my_background_task.start()
```

## Embeds

```python
embed = discord.Embed(
    title="Status",
    description="System running",
    color=discord.Color.green()
)
embed.add_field(name="CPU", value="45%")
await ctx.send(embed=embed)
```

## Full Documentation

https://discordpy.readthedocs.io/en/stable/
EOF
fi

# Oh My OpenCode
if [ -f "$HOME/.config/opencode/oh-my-opencode.json" ]; then
    cat > "$DOCS_DIR/frameworks/oh-my-opencode.md" << 'EOF'
# Oh My OpenCode Configuration

## Location
`~/.config/opencode/oh-my-opencode.json`

## Agent Configuration

```jsonc
{
  "agents": {
    "sisyphus": {
      "model": "anthropic/claude-opus-4-6",
      "systemPrompt": "Your prompt here",
      "permissions": {
        "exec": true,
        "read": true,
        "write": true
      }
    }
  }
}
```

## Ultrawork Mode

Keywords: `ultrawork`, `ulw`

Activates:
- Sisyphus orchestrator
- Background agents
- Aggressive completion
- Todo enforcement

## Full Documentation

https://github.com/code-yeongyu/oh-my-opencode
EOF
fi

# ATHENA
cat > "$DOCS_DIR/systems/athena.md" << 'EOF'
# ATHENA Warfare System

## Architecture

```
ATHENA (Supreme Commander)
├── APOLLO (Frontend/Voice) - 6 Titans
├── ARES (Backend) - 6 Titans
├── ARTEMIS (Testing) - 5 Titans
├── GitHub Scouts (3 Heroes)
└── Code Integrator (1 Warrior)
```

## CLI Usage

```bash
python ~/Numenor_prime/athena/athena.py \
  --objective "Build PLUTUS agent" \
  --deadline "2026-02-19T23:59:59" \
  --priority CRITICAL
```

## From Python

```python
from athena import ATHENA, AthenaCommander

athena = ATHENA()
commander = AthenaCommander(athena)

commander.issue_objective(
    objective="Build voice interface",
    deadline="2026-02-19T23:59:59",
    priority="CRITICAL"
)
```

## Olympians

- **APOLLO**: Frontend, UI, Voice
- **ARES**: Backend, APIs, Databases
- **ARTEMIS**: Testing, QA, Validation

## What It Does

1. Decomposes objective into components
2. Deploys appropriate Olympian divisions
3. Scouts GitHub for best implementations
4. Integrates code automatically
5. Runs comprehensive testing (5 phases)
6. Delivers production-ready code
EOF

echo "✅ Documentation synced to $DOCS_DIR"
```

---

## INSTRUCTIONS FOR AI AGENTS

**File:** `~/Numenor_prime/docs/INSTRUCTIONS.md`

```markdown
# FOR AI AGENTS: How to Use This Documentation

## When You Need Information

**BEFORE asking the user, CHECK HERE:**

1. **APIs** (`docs/apis/`) - External service documentation
2. **Frameworks** (`docs/frameworks/`) - Library references
3. **Systems** (`docs/systems/`) - Architecture documentation
4. **Patterns** (`docs/patterns/`) - Design patterns
5. **References** (`docs/references/`) - Quick lookups

## Example Workflow

### Bad (Don't Do This):
```
Agent: How do I send a Discord message?
User: Check the Discord.py docs
Agent: What's the syntax?
User: [wastes 5 minutes explaining]
```

### Good (Do This):
```
Agent: [Reads docs/apis/discord.md]
Agent: [Writes correct code first try]
User: ✅
```

## How to Read Docs

### For Discord Bot Code:
```bash
cat ~/Numenor_prime/docs/apis/discord.md
```

### For ATHENA Integration:
```bash
cat ~/Numenor_prime/docs/systems/athena.md
```

### For Oh My OpenCode Config:
```bash
cat ~/Numenor_prime/docs/frameworks/oh-my-opencode.md
```

## When Docs Are Missing

1. Check official source (GitHub README)
2. Save relevant info to appropriate `docs/` folder
3. Tell user what you added
4. Proceed with task

## Documentation is REQUIRED Reading

If you write code without checking docs first, you are:
- Wasting the user's time
- Probably writing broken code
- Ignoring available information

**Always check docs before asking questions.**
```

---

## AUTO-INJECT INTO AGENT CONTEXT

### For Oh My OpenCode

**Add to:** `~/.config/opencode/oh-my-opencode.json`

```jsonc
{
  "hooks": {
    "user_prompt_submit": [
      {
        "name": "inject_docs_awareness",
        "enabled": true,
        "script": "echo '\nDOCUMENTATION: Check ~/Numenor_prime/docs/ before asking questions. All installed packages and systems are documented there.\n'"
      }
    ]
  }
}
```

### For ATHENA

**Add to:** `~/Numenor_prime/athena/athena.py`

```python
# At the top of ATHENA
DOCS_PATH = Path.home() / "Numenor_prime" / "docs"

def get_available_docs() -> str:
    """List available documentation"""
    if not DOCS_PATH.exists():
        return ""
    
    docs = []
    for category in DOCS_PATH.iterdir():
        if category.is_dir():
            files = [f.stem for f in category.glob("*.md")]
            if files:
                docs.append(f"{category.name}: {', '.join(files)}")
    
    return "\n".join(docs)

# Inject into agent prompts
AGENT_SYSTEM_PROMPT = f"""
You are an AI agent with access to comprehensive documentation.

DOCUMENTATION AVAILABLE:
{get_available_docs()}

Read docs at: ~/Numenor_prime/docs/<category>/<topic>.md

CHECK DOCS BEFORE ASKING QUESTIONS.
"""
```

---

## MAINTENANCE

### Add New Package Documentation

```bash
# When you install something:
pip install newpackage

# Add its docs:
cat > ~/Numenor_prime/docs/apis/newpackage.md << 'EOF'
# NewPackage Quick Reference
[your curated reference here]
EOF
```

### Update System Documentation

```bash
# When you change ATHENA:
vim ~/Numenor_prime/docs/systems/athena.md

# When you modify CITADEL:
vim ~/Numenor_prime/docs/systems/citadel.md
```

---

## BENEFITS

### 1. Agents Stop Hallucinating
**Before:** Agent guesses Discord API  
**After:** Agent reads correct syntax

### 2. Faster Development
**Before:** 5 questions about how to do X  
**After:** Agent reads docs, does X correctly

### 3. Consistent Patterns
**Before:** Each agent reinvents everything  
**After:** Agents follow documented patterns

### 4. Knowledge Accumulation
**Before:** Every session starts from zero  
**After:** Documentation improves over time

### 5. Less Context Pollution
**Before:** Paste entire README into every prompt  
**After:** Agent reads on-demand

---

## TOOLS INTEGRATION

### Oh My OpenCode

Sisyphus can automatically read docs:

```jsonc
{
  "skills": {
    "read-docs": {
      "description": "Read project documentation",
      "command": "cat ~/Numenor_prime/docs/$1/$2.md"
    }
  }
}
```

### RedPlanet Core

Store docs in memory graph:

```python
# When installing package
core_memory.store(
    key=f"docs:{package_name}",
    value=documentation_content,
    metadata={"type": "reference", "category": "api"}
)
```

---

## EXAMPLE: Discord Bot Development

### Without Docs Center:
```
User: Build Discord bot
Agent: How do I send messages?
User: [explains]
Agent: How do I use commands?
User: [explains]
Agent: How do background tasks work?
User: [explains]
[30 minutes wasted]
```

### With Docs Center:
```
User: Build Discord bot
Agent: [reads docs/apis/discord.md]
Agent: [reads docs/patterns/discord-bots.md]
Agent: [writes complete bot]
User: ✅ works first try
[5 minutes total]
```

---

## START NOW

```bash
# Create structure
mkdir -p ~/Numenor_prime/docs/{apis,frameworks,systems,patterns,references}

# Add Discord docs
cat > ~/Numenor_prime/docs/apis/discord.md << 'EOF'
[paste Discord.py reference]
EOF

# Add ATHENA docs
cat > ~/Numenor_prime/docs/systems/athena.md << 'EOF'
[paste ATHENA architecture]
EOF

# Add instructions
cat > ~/Numenor_prime/docs/INSTRUCTIONS.md << 'EOF'
[paste agent instructions]
EOF
```

**Your agents will thank you.**
