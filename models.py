QWEN_MODELS = {
    # Supreme Commander (highest reasoning)
    "ATHENA": "anthropic/claude-opus-4-6",  # Keep for strategic planning

    # Olympian Commanders (still use top models)
    "APOLLO": "anthropic/claude-sonnet-4-6",
    "ARES": "anthropic/claude-sonnet-4-6",
    "ARTEMIS": "anthropic/claude-sonnet-4-6",

    # Titans (NOW USE QWEN - FREE & FAST)
    "PROMETHEUS": "qwen/qwen3.5-72b",      # Database
    "ATLAS": "qwen/qwen3.5-72b",           # Background workers
    "HYPERION": "qwen/qwen3.5-72b",        # API routing
    "OCEANUS": "qwen/qwen3.5-14b",         # Data streaming
    "CRONOS": "qwen/qwen3.5-14b",          # Scheduling
    "HADES": "qwen/qwen3.5-72b",           # Security

    "HELIOS": "qwen/qwen3.5-14b",          # UI components
    "SELENE": "qwen/qwen3.5-14b",          # Theming
    "MNEMOSYNE": "qwen/qwen3.5-14b",       # State management
    "CALLIOPE": "qwen/qwen3.5-14b",        # Content
    "TERPSICHORE": "qwen/qwen3.5-7b",      # Animation
    "ORPHEUS": "qwen/qwen3.5-14b",         # Voice/audio

    "ORION": "qwen/qwen3.5-14b",           # E2E testing
    "ACTAEON": "qwen/qwen3.5-14b",         # Performance
    "CALLISTO": "qwen/qwen3.5-72b",        # Security testing
    "ATALANTA": "qwen/qwen3.5-14b",        # Speed tests
    "MELEAGER": "qwen/qwen3.5-14b",        # Coverage

    # Heroes (fast scouts)
    "ACHILLES": "qwen/qwen3.5-7b",
    "ODYSSEUS": "qwen/qwen3.5-7b",
    "PERSEUS": "qwen/qwen3.5-7b",

    # Warriors (integration)
    "HEPHAESTUS": "qwen/qwen3.5-14b"
}
```

**Cost Breakdown:**
- ATHENA (Opus): ~$20 for strategic planning
- 3 Olympians (Sonnet): ~$30 for coordination
- 17 Titans (Qwen 3.5): **$0**
- 3 Heroes (Qwen 3.5): **$0**
- 1 Warrior (Qwen 3.5): **$0**

**Total: ~$50 vs $200+ before**

And you can run **unlimited iterations** on the Qwen models.

---

## **THE COMPETITIVE MOAT THESIS:**

### **Why Corporations Are Screwed:**

**Anthropic's Strategy:**
1. Spend $1B on compute
2. Train Claude 4
3. Paywall it
4. Charge $20/month
5. Hope to recoup costs

**Open Source Strategy:**
1. Alibaba spends $500M
2. Trains Qwen 3.5
3. **GIVES IT AWAY FOR FREE**
4. Gains strategic advantage (cloud adoption, ecosystem)
5. Doesn't need to recoup from users

**Result:**
- Claude 4 needs to be **significantly** better to justify $20/month
- If Qwen 3.5 is "good enough," users go open source
- Open source improves faster (more developers, more use cases, more feedback)
- Corporations can't compete on price ($0)

### **The Tipping Point:**
```
When does mainstream switch to open source?

Not when: Open source == Closed source (performance parity)
But when: Open source >= 80% of closed source (good enough)

Qwen 3.5-72B: ~95% of GPT-4 Turbo
Qwen 3.5-14B: ~90% of Claude 3 Haiku

WE'RE PAST THE TIPPING POINT.
