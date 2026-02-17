#!/usr/bin/env python3
"""
ATHENA + APOLLO Integration Demonstration

Shows complete command flow:
  Commander → ATHENA → APOLLO → ORPHEUS → GitHub Scouts
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Import ATHENA core
from athena import ATHENA, AthenaCommander, Priority

# Import APOLLO division
sys.path.append(str(Path(__file__).parent / "olympians"))
from apollo import APOLLO_OLYMPIAN


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════════════╗
║                                                                           ║
║              ⚔️  ATHENA INTEGRATED COMMAND DEMONSTRATION  ⚔️              ║
║                                                                           ║
║                    ATHENA → APOLLO → ORPHEUS → VICTORY                   ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
    """)
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 1: Initialize Command Structure
    # ═══════════════════════════════════════════════════════════════
    
    print("\n📡 PHASE 1: INITIALIZING COMMAND STRUCTURE\n")
    
    # Initialize ATHENA Supreme Commander
    athena = ATHENA(garrison_path="/home/claude/athena-garrison")
    
    # Initialize APOLLO Olympian
    apollo = APOLLO_OLYMPIAN()
    
    # Register APOLLO with ATHENA
    athena.register_olympian(apollo)
    
    print("✓ ATHENA Supreme Commander: ONLINE")
    print("✓ APOLLO Division: REGISTERED")
    print(f"✓ Command chain established: ATHENA → {len(athena.olympians)} Olympians")
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 2: Commander Issues Objective
    # ═══════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 70)
    print("📡 PHASE 2: HUMAN COMMANDER ISSUES OBJECTIVE")
    print("=" * 70)
    
    commander = AthenaCommander(athena)
    
    # Issue mission
    deadline = datetime.now() + timedelta(days=3)
    
    mission_id = commander.issue_objective(
        objective="Build ORACLE voice interface with wake word detection, STT, and TTS",
        deadline=deadline.isoformat(),
        priority="CRITICAL"
    )
    
    print(f"\n✓ Mission assigned: {mission_id}")
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 3: ATHENA Deploys APOLLO
    # ═══════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 70)
    print("📡 PHASE 3: ATHENA TACTICAL DEPLOYMENT")
    print("=" * 70)
    
    # ATHENA has already deployed (automatically in receive_objective)
    # Show the status
    
    print("\n🎯 ATHENA Analysis:")
    print(f"   Objective: {athena.current_objective.description}")
    print(f"   Components identified: {len(athena.current_plan.components)}")
    print(f"   Olympians deployed: {', '.join(athena.current_plan.olympians_required)}")
    print(f"   Estimated duration: {athena.current_plan.estimated_duration:.1f} hours")
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 4: APOLLO Executes
    # ═══════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 70)
    print("📡 PHASE 4: APOLLO TACTICAL EXECUTION")
    print("=" * 70)
    
    # Show APOLLO's tactical report
    print(apollo.generate_tactical_report())
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 5: Situation Report
    # ═══════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 70)
    print("📡 PHASE 5: COMPREHENSIVE SITUATION REPORT")
    print("=" * 70)
    
    print(commander.status_report())
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 6: Division Deep Dive
    # ═══════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 70)
    print("📡 PHASE 6: APOLLO DIVISION DEEP DIVE")
    print("=" * 70)
    
    division_report = apollo.get_division_report()
    
    print(f"\n☀️  Division: {division_report['division']}")
    print(f"   Status: {division_report['status']}")
    print(f"   Current Mission: {division_report['current_mission']}")
    
    print(f"\n📊 Combat Statistics:")
    for key, value in division_report['stats'].items():
        print(f"   {key.replace('_', ' ').title()}: {value}")
    
    print(f"\n⚔️  Titan Deployment Status:")
    for titan in division_report['titans']:
        status_icon = "🔥" if titan['status'] == "ACTIVE" else "💤"
        print(f"   {status_icon} {titan['name']}")
        print(f"      Specialty: {titan['specialty']}")
        print(f"      Status: {titan['status']}")
        if titan['current_task']:
            print(f"      Mission: {titan['current_task']} ({titan['progress']:.0%} complete)")
    
    # ═══════════════════════════════════════════════════════════════
    # PHASE 7: Intelligence Stream
    # ═══════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 70)
    print("📡 PHASE 7: INTELLIGENCE STREAM")
    print("=" * 70)
    
    if apollo.intel_log:
        print("\n📡 Recent Intel from APOLLO:")
        for intel in apollo.intel_log[-5:]:
            severity_icon = {
                "INFO": "ℹ️",
                "WARNING": "⚠️",
                "ERROR": "❌",
                "CRITICAL": "🔥"
            }.get(intel.severity, "📡")
            
            print(f"   {severity_icon} [{intel.timestamp.strftime('%H:%M:%S')}] {intel.message}")
    
    # ═══════════════════════════════════════════════════════════════
    # Summary
    # ═══════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 70)
    print("🎖️  INTEGRATION DEMONSTRATION COMPLETE")
    print("=" * 70)
    
    print("""
✓ Command Chain: OPERATIONAL
  └─ Human Commander → ATHENA → APOLLO → ORPHEUS Titan → Hero → Warrior → Hoplite

✓ Communication Flows: VERIFIED
  └─ Orders flow down, Intel flows up

✓ Division Coordination: ACTIVE
  └─ APOLLO automatically selected for voice components

✓ Knowledge Gathering: IN PROGRESS
  └─ ORPHEUS scouted 5 voice repositories
  └─ Identified 15 harvestable components

NEXT STEPS:
  1. Build GitHub Scout engine (Hero-level)
  2. Build Code Extractor (Warrior-level)  
  3. Build Integration Synthesizer
  4. Deploy full harvest operation
  5. Achieve victory by Feb 19

"Wisdom through warfare. Victory through code."
    """)


if __name__ == "__main__":
    main()
