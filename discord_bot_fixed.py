#!/usr/bin/env python3
"""
WORKING Discord Bot → Oh My OpenCode → ATHENA Integration

FIXES:
1. Actually runs OpenCode in background (tmux)
2. Streams output to Discord in real-time
3. Captures your CLI responses
4. Allows interaction via Discord while it runs
"""

import discord
from discord.ext import commands, tasks
import subprocess
import asyncio
import os
import re
import shlex
from pathlib import Path
from datetime import datetime
import json

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Paths
if load_dotenv:
    load_dotenv()

NUMENOR = Path(os.getenv("NUMENOR_PATH", str(Path.home() / "Numenor_prime"))).expanduser()
ATHENA_DIR = NUMENOR / "athena"
OPENCODE_DIR = NUMENOR
ATHENA_GARRISON_PATH = Path(
    os.getenv("ATHENA_GARRISON_PATH", str(NUMENOR / "athena-garrison"))
).expanduser()
ATHENA_REQUIRE_CORE = os.getenv("ATHENA_REQUIRE_CORE", "1").strip() not in {"0", "false", "False"}
ATHENA_CORE_BASE_URL = os.getenv("CORE_API_BASE_URL")
ATHENA_CORE_SCORE_THRESHOLD = os.getenv("ATHENA_CORE_SCORE_THRESHOLD", "0.35")
ATHENA_CORE_TEMPLATE_SCORE_THRESHOLD = os.getenv("ATHENA_CORE_TEMPLATE_SCORE_THRESHOLD", "0.50")
ATHENA_CORE_REFRESH_TIMEOUT = os.getenv("ATHENA_CORE_REFRESH_TIMEOUT", "8")

# Active sessions
active_sessions = {}
runtime_tools = {}


class OpenCodeSession:
    """Manages an active OpenCode session in tmux"""
    
    def __init__(self, session_id: str, channel_id: int, task: str):
        self.session_id = session_id
        self.channel_id = channel_id
        self.task = task
        self.tmux_session = f"omc-{session_id}"
        self.log_file = NUMENOR / f"logs/{session_id}.log"
        self.status = "STARTING"
        self.last_output_line = 0
        
    async def start(self):
        """Start OpenCode in tmux session"""
        
        # Create log directory
        self.log_file.parent.mkdir(exist_ok=True)
        
        # Create workspace
        workspace = NUMENOR / f"workspace/{self.session_id}"
        workspace.mkdir(parents=True, exist_ok=True)
        
        # Create prompt file
        prompt_file = workspace / "prompt.md"
        prompt_file.write_text(f"""# Task

{self.task}

# ATHENA Integration

You have access to ATHENA warfare system at:
`python {ATHENA_DIR}/athena.py --objective "..." --priority CRITICAL`

ATHENA provides:
- Code harvesting from GitHub
- Multi-agent coordination
- Automated testing
- Production-ready output

# Session Info

Session ID: {self.session_id}
This session is monitored via Discord.
All output is logged to: {self.log_file}

Work until task is 100% complete.
""")
        
        # Kill existing session if any
        subprocess.run(['tmux', 'kill-session', '-t', self.tmux_session], 
                      stderr=subprocess.DEVNULL)
        
        # Start tmux session with OpenCode
        run_cmd = (
            f"cd {shlex.quote(str(workspace))} && "
            f"opencode --prompt {shlex.quote(str(prompt_file))} 2>&1 | "
            f"tee {shlex.quote(str(self.log_file))}"
        )
        cmd = [
            'tmux', 'new-session', '-d', '-s', self.tmux_session,
            run_cmd
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            self.status = "RUNNING"
            return True
        else:
            self.status = "FAILED"
            return False
    
    def send_input(self, text: str):
        """Send input to the running OpenCode session"""
        
        # Send to tmux session
        subprocess.run([
            'tmux', 'send-keys', '-t', self.tmux_session,
            text, 'Enter'
        ])
        
        # Also log it
        with open(self.log_file, 'a') as f:
            f.write(f"\n[USER INPUT] {text}\n")
    
    def get_new_output(self) -> list:
        """Get new lines from log file since last check"""
        
        if not self.log_file.exists():
            return []
        
        with open(self.log_file, 'r') as f:
            lines = f.readlines()
        
        new_lines = lines[self.last_output_line:]
        self.last_output_line = len(lines)
        
        return [line.strip() for line in new_lines if line.strip()]
    
    def is_alive(self) -> bool:
        """Check if tmux session is still running"""
        
        result = subprocess.run(
            ['tmux', 'has-session', '-t', self.tmux_session],
            capture_output=True
        )
        return result.returncode == 0
    
    def stop(self):
        """Stop the session"""
        
        subprocess.run(['tmux', 'kill-session', '-t', self.tmux_session],
                      stderr=subprocess.DEVNULL)
        self.status = "STOPPED"


@bot.event
async def on_ready():
    print(f'🤖 ATHENA Bot ready: {bot.user}')
    print(f'   Monitoring {len(active_sessions)} active sessions')
    
    # Start background task to monitor sessions
    if not monitor_sessions.is_running():
        monitor_sessions.start()


@tasks.loop(seconds=5)
async def monitor_sessions():
    """Background task to monitor all active sessions"""
    
    for session_id, session in list(active_sessions.items()):
        channel = bot.get_channel(session.channel_id)
        if not channel:
            continue
        
        # Check if session is still alive
        if not session.is_alive() and session.status == "RUNNING":
            session.status = "COMPLETED"
            await channel.send(f"✅ **Session {session_id} completed**")
            continue
        
        # Get new output
        new_lines = session.get_new_output()
        
        if new_lines:
            # Filter for important updates
            important = [line for line in new_lines if any(
                keyword in line.lower() for keyword in [
                    'athena', 'deploying', 'complete', 'error', 
                    'warning', 'success', 'failed', 'done',
                    'working on', 'task', 'olympian', 'division'
                ]
            )]
            
            if important:
                # Send to Discord (max 2000 chars)
                output = '\n'.join(important[-10:])  # Last 10 important lines
                if len(output) > 1900:
                    output = output[-1900:]
                
                await channel.send(f"```\n{output}\n```")


@bot.command(name='ulw')
async def ultrawork(ctx, *, task: str):
    """
    Ultra Work mode: Start OpenCode session
    Usage: !ulw build PLUTUS financial agent
    """
    
    session_id = f"ULW-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    await ctx.send(f"🔥 **ULTRA WORK MODE**\n```Session: {session_id}\nTask: {task}```")
    
    # Create session
    session = OpenCodeSession(session_id, ctx.channel.id, task)
    active_sessions[session_id] = session
    
    # Start it
    if await session.start():
        await ctx.send(f"✅ **Session started**\n"
                      f"• Tmux: `{session.tmux_session}`\n"
                      f"• Log: `{session.log_file}`\n"
                      f"• Send input with: `!input {session_id} <text>`\n"
                      f"• View log with: `!log {session_id}`")
    else:
        await ctx.send(f"❌ **Failed to start session**")
        del active_sessions[session_id]


@bot.command(name='input')
async def send_input(ctx, session_id: str, *, text: str):
    """
    Send input to running session
    Usage: !input ULW-20260216-120000 yes, continue with that approach
    """
    
    if session_id not in active_sessions:
        await ctx.send(f"❌ Session {session_id} not found")
        return
    
    session = active_sessions[session_id]
    session.send_input(text)
    
    await ctx.send(f"📝 **Sent to {session_id}:**\n```{text}```")


@bot.command(name='log')
async def view_log(ctx, session_id: str, lines: int = 20):
    """
    View recent log lines
    Usage: !log ULW-20260216-120000 50
    """
    
    if session_id not in active_sessions:
        await ctx.send(f"❌ Session {session_id} not found")
        return
    
    session = active_sessions[session_id]
    
    if not session.log_file.exists():
        await ctx.send(f"❌ No log file yet")
        return
    
    with open(session.log_file, 'r') as f:
        all_lines = f.readlines()
    
    recent = all_lines[-lines:]
    output = ''.join(recent)
    
    # Split if too long
    if len(output) > 1900:
        output = output[-1900:]
    
    await ctx.send(f"📜 **Last {len(recent)} lines:**\n```\n{output}\n```")


@bot.command(name='attach')
async def attach_terminal(ctx, session_id: str):
    """
    Get command to attach to tmux session
    Usage: !attach ULW-20260216-120000
    """
    
    if session_id not in active_sessions:
        await ctx.send(f"❌ Session {session_id} not found")
        return
    
    session = active_sessions[session_id]
    
    await ctx.send(f"🖥️  **To attach to terminal:**\n"
                  f"```bash\n"
                  f"tmux attach-session -t {session.tmux_session}\n"
                  f"# Detach with: Ctrl+B, then D\n"
                  f"```")


@bot.command(name='stop')
async def stop_session(ctx, session_id: str):
    """
    Stop a running session
    Usage: !stop ULW-20260216-120000
    """
    
    if session_id not in active_sessions:
        await ctx.send(f"❌ Session {session_id} not found")
        return
    
    session = active_sessions[session_id]
    session.stop()
    
    await ctx.send(f"🛑 **Stopped {session_id}**")


@bot.command(name='sessions')
async def list_sessions(ctx):
    """List all active sessions"""
    
    if not active_sessions:
        await ctx.send("No active sessions")
        return
    
    output = []
    for sid, session in active_sessions.items():
        alive = "🟢" if session.is_alive() else "🔴"
        output.append(f"{alive} **{sid}** ({session.status})")
        output.append(f"   Task: {session.task[:80]}")
        output.append(f"   Tmux: `{session.tmux_session}`\n")
    
    await ctx.send('\n'.join(output))


@bot.command(name='stack')
async def stack_status(ctx):
    """Show runtime stack readiness (OpenCode + Claw + Core env)."""
    lines = []
    lines.append(f"NUMENOR_PATH: {NUMENOR}")
    lines.append(f"ATHENA entrypoint: {'OK' if (ATHENA_DIR / 'athena.py').exists() else 'MISSING'}")
    for tool in ["tmux", "opencode", "zeptoclaw", "picoclaw"]:
        path = runtime_tools.get(tool) or "MISSING"
        lines.append(f"{tool}: {path}")

    omoc_config = Path.home() / ".config" / "opencode" / "oh-my-opencode.json"
    lines.append(f"oh-my-opencode config: {'OK' if omoc_config.exists() else 'MISSING'}")
    lines.append(f"CORE_API_KEY set: {'YES' if bool(os.getenv('CORE_API_KEY')) else 'NO'}")
    await ctx.send("```" + "\n".join(lines) + "```")


@bot.command(name='athena')
async def deploy_athena(ctx, *, objective: str):
    """
    Deploy ATHENA directly
    Usage: !athena build invoice module for PLUTUS
    """
    
    await ctx.send(f"⚔️  **ATHENA DEPLOYING**\n```{objective}```")
    
    # Run ATHENA in tmux
    session_id = f"ATHENA-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    tmux_session = f"athena-{session_id}"
    log_file = NUMENOR / f"logs/{session_id}.log"
    log_file.parent.mkdir(exist_ok=True)
    deadline = datetime.now().replace(microsecond=0).isoformat()

    athena_args = [
        "python",
        str(ATHENA_DIR / "athena.py"),
        "--objective", objective,
        "--deadline", deadline,
        "--garrison-path", str(ATHENA_GARRISON_PATH),
        "--core-score-threshold", str(ATHENA_CORE_SCORE_THRESHOLD),
        "--core-template-score-threshold", str(ATHENA_CORE_TEMPLATE_SCORE_THRESHOLD),
        "--core-refresh-timeout", str(ATHENA_CORE_REFRESH_TIMEOUT),
        "--priority", "CRITICAL",
        "--require-core" if ATHENA_REQUIRE_CORE else "--no-require-core",
    ]
    if ATHENA_CORE_BASE_URL:
        athena_args.extend(["--core-base-url", str(ATHENA_CORE_BASE_URL)])
    run_cmd = " ".join(shlex.quote(part) for part in athena_args)
    run_cmd = f"{run_cmd} 2>&1 | tee {shlex.quote(str(log_file))}"
    
    cmd = [
        'tmux', 'new-session', '-d', '-s', tmux_session,
        run_cmd
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        await ctx.send(f"✅ **ATHENA deployed**\n"
                      f"Session: {session_id}\n"
                      f"Tmux: `{tmux_session}`\n"
                      f"Log: `!tail {log_file}`")
        
        # Monitor it
        asyncio.create_task(monitor_athena_session(ctx.channel, session_id, tmux_session, log_file))
    else:
        await ctx.send(f"❌ Failed: ```{result.stderr}```")


async def monitor_athena_session(channel, session_id, tmux_session, log_file):
    """Monitor ATHENA session and send updates"""
    
    last_line = 0
    
    while True:
        await asyncio.sleep(10)
        
        # Check if still running
        result = subprocess.run(['tmux', 'has-session', '-t', tmux_session],
                              capture_output=True)
        
        if result.returncode != 0:
            await channel.send(f"✅ **{session_id} completed**")
            break
        
        # Read new output
        if log_file.exists():
            with open(log_file, 'r') as f:
                lines = f.readlines()
            
            new_lines = lines[last_line:]
            last_line = len(lines)
            
            # Send important updates
            important = [line.strip() for line in new_lines if any(
                keyword in line.lower() for keyword in
                ['olympian', 'deploying', 'complete', 'error', 'success']
            )]
            
            if important:
                output = '\n'.join(important[-5:])
                if len(output) < 1900:
                    await channel.send(f"```\n{output}\n```")


@bot.command(name='tail')
async def tail_file(ctx, filepath: str, lines: int = 20):
    """
    Tail a log file
    Usage: !tail /home/user/Numenor_prime/logs/ATHENA-20260216.log
    """
    
    path = Path(filepath)
    
    if not path.exists():
        await ctx.send(f"❌ File not found: {filepath}")
        return
    
    result = subprocess.run(['tail', f'-n{lines}', str(path)],
                          capture_output=True, text=True)
    
    output = result.stdout
    if len(output) > 1900:
        output = output[-1900:]
    
    await ctx.send(f"```\n{output}\n```")


# Run bot
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("❌ Set DISCORD_BOT_TOKEN environment variable")
        exit(1)
    
    # Ensure tmux is installed
    if subprocess.run(['which', 'tmux'], capture_output=True).returncode != 0:
        print("❌ tmux not installed. Run: sudo dnf install tmux")
        exit(1)

    # Ensure OpenCode is installed
    if subprocess.run(['which', 'opencode'], capture_output=True).returncode != 0:
        print("❌ opencode not installed in this runtime")
        exit(1)

    # Ensure Oh My OpenCode config exists
    omoc_config = Path.home() / ".config" / "opencode" / "oh-my-opencode.json"
    if not omoc_config.exists():
        print(f"❌ Missing oh-my-opencode config: {omoc_config}")
        exit(1)

    if not ATHENA_DIR.exists():
        print(f"❌ ATHENA directory not found: {ATHENA_DIR}")
        exit(1)
    if not (ATHENA_DIR / "athena.py").exists():
        print(f"❌ ATHENA entrypoint not found: {ATHENA_DIR / 'athena.py'}")
        exit(1)
    ATHENA_GARRISON_PATH.mkdir(parents=True, exist_ok=True)

    required_stack = os.getenv("REQUIRE_CLAW_STACK", "1").strip() not in {"0", "false", "False"}
    for tool in ["tmux", "opencode", "zeptoclaw", "picoclaw"]:
        result = subprocess.run(["which", tool], capture_output=True, text=True)
        path = result.stdout.strip() if result.returncode == 0 else None
        runtime_tools[tool] = path
        if required_stack and not path:
            print(f"❌ Required tool missing: {tool}")
            exit(1)
    
    print("🚀 Starting ATHENA Discord Bot...")
    print(f"   Numenor Prime: {NUMENOR}")
    print(f"   ATHENA: {ATHENA_DIR}")
    print(f"   ATHENA garrison: {ATHENA_GARRISON_PATH}")
    print(f"   OpenCode config: {omoc_config}")
    print(f"   Claw stack strict mode: {required_stack}")
    print(f"   ATHENA require core: {ATHENA_REQUIRE_CORE}")
    
    bot.run(TOKEN)
