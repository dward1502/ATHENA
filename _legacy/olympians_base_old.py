# ~/Numenor_prime/athena/olympians/base.py

AVAILABLE_MODELS = {
    # Premium (for strategic decisions)
    "opus": "anthropic/claude-opus-4-6",
    "sonnet": "anthropic/claude-sonnet-4-6",
    # Free (for execution)
    "qwen-72b": "qwen/qwen3.5-72b",
    "qwen-14b": "qwen/qwen3.5-14b",
    "qwen-7b": "qwen/qwen3.5-7b",
    "qwen-3b": "qwen/qwen3.5-3b",
}


class Titan:
    def __init__(self, name: str, specialty: str, model: str = "qwen-14b"):
        self.model = AVAILABLE_MODELS.get(model, model)
