import os
from dotenv import load_dotenv
from groq import Groq
from faster_whisper import WhisperModel


#load groq api key
print("Loading Groq API key...")
load_dotenv()
api_key = os.getenv("Api_Key")

client = Groq(api_key=api_key)



model_size = "small.en"

model = WhisperModel(
    model_size,
    device="cpu",
    compute_type="int8"
)


# transcibe meeting
audio_file = "Meeting in General-20260921_105953-Meeting Recording.mp4"

print(f"File: {audio_file}")

segments, info = model.transcribe(
    audio_file,
    task="translate",
    beam_size=5
)

# create complete transcript
transcript = ""

for segment in segments:
    transcript += segment.text + " "

    print(segment.text)


transcript = transcript.strip()

if not transcript:
    raise ValueError("Transcript is empty. AI analysis cannot continue.")

print(transcript)



print("\nPreparing transcript for AI analysis...")

prompt = f"""
You are an AI meeting analysis assistant.

Analyze the following meeting transcript and provide a structured analysis.

Provide the following information:

1. Meeting Summary
   - Give a concise summary of the meeting.
   - Include only information explicitly mentioned in the transcript.

2. Key Topics
   - List the main topics discussed during the meeting.
   - Do not add topics that are not mentioned in the transcript.

3. Decisions
   - List the important decisions explicitly made during the meeting.
   - If no decisions are mentioned, write "No decisions identified".

4. Action Items
   - Identify tasks that need to be completed based only on the transcript.
   - For each action item, provide:
     - Task
     - Assignee
     - Deadline

   Rules for Action Items:
   - If the assignee is not explicitly mentioned, write "Not specified".
   - If the deadline is not explicitly mentioned, write "Not specified".
   - Never guess, assume, calculate, or create a deadline.
   - Never use today's date or any future date as a deadline unless it is explicitly mentioned in the transcript.
   - Never infer an assignee from the speaker or context.
   - If no action items are mentioned, write "No action items identified".

Important Rules:
- Do not invent information.
- Only use information available in the transcript.
- Do not guess names, deadlines, tasks, or decisions.
- If information is not mentioned in the transcript, write "Not specified".
- Preserve the original meaning of the transcript.
- Do not use external knowledge to fill missing information.

Meeting Transcript:

{transcript}
"""

# send transcript to groq
print("AI analysis in progress...")

response = client.chat.completions.create(
    model="openai/gpt-oss-20b",
    messages=[
        {
            "role": "user",
            "content": prompt
        }
    ]
)


result = response.choices[0].message.content

print(result)
