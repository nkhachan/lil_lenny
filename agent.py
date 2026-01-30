import numpy as np

from agents import Agent
from agents.voice import (
    AudioInput,
    SingleAgentVoiceWorkflow,
    SingleAgentWorkflowCallbacks,
    VoicePipeline,
)
from audio_player import AudioPlayer
from recording_util import record_audio
from yoga.corepower_tools import get_yoga_reservations, get_yoga_classes, make_yoga_reservation
from gcalendar.gcalender_mcp_server import list_calendar_events, create_calendar_event

from dotenv import load_dotenv
load_dotenv()


agent = Agent(
    name="Assistant",
    instructions=
        "You're speaking to a human, so be polite and concise. Speak in english.",
    model="gpt-5-mini",
    tools=[get_yoga_classes, get_yoga_reservations, make_yoga_reservation, list_calendar_events, create_calendar_event],
)


class WorkflowCallbacks(SingleAgentWorkflowCallbacks):
    def on_run(self, workflow: SingleAgentVoiceWorkflow, transcription: str) -> None:
        print(f"[debug] User input: {transcription}")


async def main_voice():
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



