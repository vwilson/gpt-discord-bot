from enum import Enum
from dataclasses import dataclass
import openai
import json
from src.moderation import moderate_message
from typing import Optional, List
from src.constants import (    
    BOT_NAME,    
)
import discord
from src.base import Message
from src.utils import split_into_shorter_messages, close_thread, logger
from src.moderation import (
    send_moderation_flagged_message,
    send_moderation_blocked_message,
)

MY_BOT_NAME = BOT_NAME

class ChatCompletionResult(Enum):
    OK = 0
    TOO_LONG = 1
    INVALID_REQUEST = 2
    OTHER_ERROR = 3
    MODERATION_FLAGGED = 4
    MODERATION_BLOCKED = 5

@dataclass
class ChatCompletionData:
    status: ChatCompletionResult
    reply_text: Optional[str]
    status_text: Optional[str]

class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)

async def generate_chatcompletion_response(
    messages: List[Message]
) -> ChatCompletionData:
    try:        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": x.role, "content": x.content} for x in messages],
            temperature=0.8,
            top_p=0.9,
            max_tokens=512,
            stop=["<|endoftext|>"],
            user="racemaniax bot"
        )
        reply = response.choices[0].message.content.strip()
        if reply:           
            return ChatCompletionData(
                status=ChatCompletionResult.OK, reply_text=reply, status_text=None
        )
    except openai.error.InvalidRequestError as e:
        if "This model's maximum context length" in e.user_message:
            return ChatCompletionData(
                status=ChatCompletionResult.TOO_LONG, reply_text=None, status_text=str(e)
            )
        else:
            logger.exception(e)
            return ChatCompletionData(
                status=ChatCompletionResult.INVALID_REQUEST,
                reply_text=None,
                status_text=str(e),
            )
    except Exception as e:
        logger.exception(e)
        return ChatCompletionData(
            status=ChatCompletionResult.OTHER_ERROR, reply_text=None, status_text=str(e)
        )

async def process_response(
    user: str, thread: discord.Thread, response_data: ChatCompletionData
):
    status = response_data.status
    reply_text = response_data.reply_text
    status_text = response_data.status_text
    if status is ChatCompletionResult.OK or status is ChatCompletionResult.MODERATION_FLAGGED:
        sent_message = None
        if not reply_text:
            sent_message = await thread.send(
                embed=discord.Embed(
                    description=f"**Invalid response** - empty response",
                    color=discord.Color.yellow(),
                )
            )
        else:
            shorter_response = split_into_shorter_messages(reply_text)
            for r in shorter_response:
                sent_message = await thread.send(r)
        if status is ChatCompletionResult.MODERATION_FLAGGED:
            await send_moderation_flagged_message(
                guild=thread.guild,
                user=user,
                flagged_str=status_text,
                message=reply_text,
                url=sent_message.jump_url if sent_message else "no url",
            )

            await thread.send(
                embed=discord.Embed(
                    description=f"⚠️ **This conversation has been flagged by moderation.**",
                    color=discord.Color.yellow(),
                )
            )
    elif status is ChatCompletionResult.MODERATION_BLOCKED:
        await send_moderation_blocked_message(
            guild=thread.guild,
            user=user,
            blocked_str=status_text,
            message=reply_text,
        )

        await thread.send(
            embed=discord.Embed(
                description=f"❌ **The response has been blocked by moderation.**",
                color=discord.Color.red(),
            )
        )
    elif status is ChatCompletionResult.TOO_LONG:
        await close_thread(thread)
    elif status is ChatCompletionResult.INVALID_REQUEST:
        await thread.send(
            embed=discord.Embed(
                description=f"**Invalid request** - {status_text}",
                color=discord.Color.yellow(),
            )
        )
    else:
        await thread.send(
            embed=discord.Embed(
                description=f"**Error** - {status_text}",
                color=discord.Color.yellow(),
            )
        )
