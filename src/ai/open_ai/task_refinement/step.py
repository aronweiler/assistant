from typing import List


class Step:
    def __init__(self, step, recommended_tool=None):
        self.step = step
        self.recommended_tool = recommended_tool
        self.sub_steps: List[Step] = []
