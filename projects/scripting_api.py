from dataclasses import dataclass, field
from typing import Callable

@dataclass
class Script:
    name:str
    code:str
    enabled:bool=True

class ScriptRegistry:
    def __init__(self): self.scripts={}
    def add(self,s:Script): self.scripts[s.name]=s
    def list(self): return list(self.scripts.values())
    def run(self,name,ctx=None):
        s=self.scripts[name]
        ns={"context":ctx or {}}
        exec(s.code,{"__builtins__":{"len":len,"range":range,"print":print}},ns)
        return ns
