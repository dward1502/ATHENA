> Legacy troubleshooting notes: use `docs/setup/INSTALL_CLEAR_BLUEFIN.md` for current commands and bot entrypoint.

!ulw build PLUTUS agent
# Bot actually starts OpenCode in tmux
# You see real output in Discord

!input ULW-20260216-120000 yes, add invoice tracking
# Your response actually gets sent to the running session

!log ULW-20260216-120000
# See what's actually happening

!attach ULW-20260216-120000
# Get tmux command to see it on your computer
```

---

### **ISSUE 2: Documentation Center** ✅

**Problem:**
- Agents don't have library docs
- Hallucinate APIs
- Waste your time asking

**Solution:**
- `~/Numenor_prime/docs/` structure
- Auto-sync when installing packages
- Agents check before asking
- Knowledge accumulates

**Structure:**
```
docs/
├── apis/           # discord.md, anthropic.md
├── frameworks/     # oh-my-opencode.md
├── systems/        # athena.md, citadel.md
├── patterns/       # async-agents.md
└── references/     # commands.md

cd ~/Numenor_prime/discord_bot
cp discord_bot_fixed.py athena_bot.py
# Merge with your existing CEO bot if needed

mkdir -p ~/Numenor_prime/docs/{apis,frameworks,systems,patterns,references}
# Add initial docs for Discord, ATHENA, Oh My OpenCode
Test Integration (15 min)

# Start bot
python athena_bot.py

# In Discord:
!ulw build simple Flask API
# Watch it actually work this time

!input <session-id> add user authentication
# See your input actually get processed
