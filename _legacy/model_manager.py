class ModelManager:
    """Manages model loading across multiple machines"""

    def __init__(self):
        self.primary_server = "http://localhost:11434"  # RTX 3080
        self.scout_server = "http://beelink:11435"  # Beelink SER9
        self.cloud_api = "https://api.anthropic.com"

    def get_model(self, agent_type: str) -> str:
        """Route agent to appropriate model/server"""

        if agent_type in ["ATHENA", "APOLLO", "ARES", "ARTEMIS"]:
            # Strategic - Use cloud
            return self.cloud_api + "/claude-opus-4-6"

        elif agent_type in ["PROMETHEUS", "HYPERION", "HADES"]:
            # Tactical - Use RTX 3080 with 14B
            return self.primary_server + "/qwen3.5:14b-instruct-q4_K_M"

        elif agent_type in ["HELIOS", "ORPHEUS", "ORION"]:
            # Execution - Use RTX 3080 with 7B
            return self.primary_server + "/qwen3.5:7b-instruct-fp16"

        elif agent_type in ["ACHILLES", "ODYSSEUS", "PERSEUS"]:
            # Scouts - Use Beelink with 7B/3B
            return self.scout_server + "/qwen3.5:7b-instruct-q4_K_M"

        else:
            # Background tasks - Use Beelink with 3B
            return self.scout_server + "/qwen3.5:3b-instruct-fp16"
