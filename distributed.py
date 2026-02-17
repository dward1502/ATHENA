COMPUTE_NODES = {
    "primary": {
        "host": "localhost",
        "ollama_port": 11434,
        "gpu": "RTX 3080",
        "vram": "10GB",  # or 12GB
        "models": ["qwen3.5:14b-q4", "qwen3.5:7b-fp16"],
    },
    "scout": {
        "host": "beelink.local",  # mDNS hostname
        "ollama_port": 11435,
        "gpu": "Radeon 780M",
        "vram": "8GB",
        "models": ["qwen3.5:7b-q4", "qwen3.5:3b-fp16"],
    },
}


def assign_agent_to_node(agent_type: str) -> dict:
    """Load balance agents across compute nodes"""

    if agent_type in HEAVY_TITANS:
        return COMPUTE_NODES["primary"]
    elif agent_type in SCOUTS:
        return COMPUTE_NODES["scout"]
    else:
        # Background tasks on whichever has capacity
        return min(COMPUTE_NODES.values(), key=lambda n: get_current_load(n))
