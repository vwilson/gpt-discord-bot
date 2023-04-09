from dataclasses import dataclass
from typing import Optional, List, Dict
import json

SEPARATOR_TOKEN = "<|endoftext|>"


@dataclass(frozen=True)
class Message:
    user: str
    text: Optional[str] = None

    def render(self):
        result = self.user + ":"
        if self.text is not None:
            result += " " + self.text
        return result


@dataclass
class Conversation:
    messages: List[Message]

    def prepend(self, message: Message):
        self.messages.insert(0, message)
        return self

    def render(self):
        return f"\n{SEPARATOR_TOKEN}".join(
            [message.render() for message in self.messages]
        )
    
    def render_messages(self) -> List[str]:
        message_list = []
        for message in self.messages:
            message_list.append(message.user + ": " + (message.text or ""))
        return message_list


@dataclass(frozen=True)
class Config:
    name: str
    instructions: str
    example_conversations: List[Conversation]


@dataclass(frozen=True)
class Prompt:
    header: Message
    examples: List[Conversation]
    convo: Conversation

    def render(self):
        return f"\n{SEPARATOR_TOKEN}".join(
            [self.header.render()]
            + [Message("System", "Example conversations:").render()]
            + [conversation.render() for conversation in self.examples]
            + [Message("System", "Current conversation:").render()]
            + [self.convo.render()],
        )

    def render_json(self):
        messages = []

        # Add the header message
        messages.append({
            "role": "system",
            "content": self.header.render()
        })

        # Add example conversations
        #messages.append({
        #    "role": "system",
        #    "content": "Example conversations:"
        #})

        #for conversation in self.examples:
        #    messages.extend(conversation.render_messages())

        # Add the current conversation
        messages.append({
            "role": "system",
            "content": "Current conversation:" + "\n".join(self.convo.render_messages())
        })

        # Convert the messages list to a JSON-formatted string
        return messages