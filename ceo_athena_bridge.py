# ceo_athena_bridge.py
from athena import ATHENA, AthenaCommander


class CEOCommand:
    def __init__(self):
        self.athena = ATHENA()
        self.commander = AthenaCommander(self.athena)

    def execute(self, objective: str, deadline: str):
        """CEO issues command to ATHENA"""
        return self.commander.issue_objective(
            objective=objective, deadline=deadline, priority="CRITICAL"
        )
