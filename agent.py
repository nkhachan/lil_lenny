import asyncio
import random

import numpy as np

from agents import Agent, function_tool
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions
from agents.voice import (
    AudioInput,
    SingleAgentVoiceWorkflow,
    SingleAgentWorkflowCallbacks,
    VoicePipeline,
)
from audio_player import AudioPlayer
from recording_util import record_audio
from corepower_tools import get_corepower_reservations
from gcalender_mcp_server import list_events_tool, create_event_tool
from dotenv import load_dotenv
load_dotenv()


agent = Agent(
    name="Assistant",
    instructions=
        "You're speaking to a human, so be polite and concise. Speak in english.",
        #" If the user asks about the weather in any city, call the `get_weather` tool.",
    model="gpt-5-mini",
    tools=[get_corepower_reservations, list_events_tool, create_event_tool],
)


class WorkflowCallbacks(SingleAgentWorkflowCallbacks):
    def on_run(self, workflow: SingleAgentVoiceWorkflow, transcription: str) -> None:
        print(f"[debug] User input: {transcription}")


async def main():
    pipeline = VoicePipeline(
        workflow=SingleAgentVoiceWorkflow(agent, callbacks=WorkflowCallbacks())
    )

    while True:
        audio_input = AudioInput(buffer=record_audio())

        result = await pipeline.run(audio_input)

        with AudioPlayer() as player:
            async for event in result.stream():
                if event.type == "voice_stream_event_audio":
                    player.add_audio(event.data)

            # Add 1 second of silence to the end of the stream to avoid cutting off the last audio.
            player.add_audio(np.zeros(24000 * 1, dtype=np.int16))


if __name__ == "__main__":
    asyncio.run(main())