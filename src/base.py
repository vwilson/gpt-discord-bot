from dataclasses import dataclass

SEPARATOR_TOKEN = "<|endoftext|>"

@dataclass(frozen=True)
class Message:
    role: str
    content: str  

@dataclass(frozen=True)
class Config:
    name: str
    system_message: str    