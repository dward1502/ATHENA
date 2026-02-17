> Legacy doc: use `docs/setup/INSTALL_CLEAR_BLUEFIN.md` as source of truth.

Discord: "!ulw you are CEO, build PLUTUS"
    ↓
Oh My OpenCode Sisyphus Agent (with ultrawork mode)
    ↓
Sisyphus reads injected context:
  "You have ATHENA at ~/Numenor_prime/athena/athena.py"
    ↓
Sisyphus executes:
  python ~/Numenor_prime/athena/athena.py --objective "Build PLUTUS"
    ↓
ATHENA deploys APOLLO, ARES, ARTEMIS divisions
    ↓
Builds autonomously while you do other things
    ↓
Updates sent to Discord

# 1. Discord bot in toolbox
toolbox enter moria
pip install discord.py

# 2. Configure Oh My OpenCode to know about ATHENA
~/.config/opencode/oh-my-opencode.json

# 3. Run bot as systemd service
systemctl --user start athena-discord-bot

# 4. Text Discord from anywhere:
"!ulw build PLUTUS by Feb 19"

# 5. System builds while you do other stuff
# 6. Get updates in Discord
# 7. Reply to adjust: "add PDF export"
# 8. System continues
Phase 1: Basic Discord Bot (1 hour)
bashtoolbox enter athena-dev
pip install discord.py
# Copy athena_bot.py
# Get Discord token
python athena_bot.py
Test: !athena build simple Flask app
Phase 2: Oh My OpenCode Config (30 min)
bash# Add ATHENA awareness to ~/.config/opencode/oh-my-opencode.json
# Test: opencode with "ulw" in prompt
Test: See if Sisyphus mentions ATHENA
Phase 3: Full Integration (2 hours)
bash# Wire Discord → Oh My OpenCode → ATHENA
# Test: !ulw build PLUTUS foundation
Test: Get Discord updates while it builds
Phase 4: Deploy & Scale (Rest of 3 days)
bash# Use it to build PLUTUS for real
# Let it run overnight
# Wake up to working code

curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3.5:72b
ollama pull qwen3.5:14b

// ~/.config/opencode/oh-my-opencode.json
{
  "agents": {
    "sisyphus": {
      "model": "qwen/qwen3.5-72b",  // ← FREE GPT-4 level
      "temperature": 0.7
    },
    "oracle": {
      "model": "anthropic/claude-opus-4-6"  // Keep for architecture
    },
    "librarian": {
      "model": "qwen/qwen3.5-14b"  // ← FREE for doc search
    }
  }
}
