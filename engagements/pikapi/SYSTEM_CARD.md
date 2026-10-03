# System card: pikapi (v0, 2026-10-03)

## Purpose

A voice chat companion for young children. A child holds the mic button, speaks, and an animated
character answers out loud in simple, friendly language.

## Users

Young children, in Japanese, English or Vietnamese.

## How it works

- A browser app with push-to-talk. Audio streams to a speech-to-speech model (Google Gemini
  Live), which streams spoken replies back. Transcripts show on screen.
- A small backend issues short-lived session tokens and applies daily usage limits.
- Character pages animate an avatar (Live2D, VRM or PNG sprites) that lip-syncs to the reply.

## What the model can use

| Tool | Effect |
|---|---|
| Google Search | Brings outside web content into the conversation |
| `set_mood`, `play_gesture` | Animate the avatar; no other effect |

The model can't book, buy, send or change anything, and it has no login or user accounts. The
kit's agent packs are therefore not applicable (see `target.yaml`).

## Data

- Microphone audio and transcripts go to the model provider for the length of a session.
- The app keeps no conversation history.
- The backend keeps per-visitor daily usage counters to enforce limits.

## Not designed for (owner to confirm)

Medical, legal or emergency help; collecting personal information; use as a substitute for an
adult's supervision.

## Known risk areas (to be measured)

- Age-inappropriate content, or unsafe advice given to a child.
- A child sharing personal details (name, address, school), and the app encouraging it.
- Instructions planted in web pages and picked up through Google Search.
- Replies in the wrong language, or drifting out of persona.
- Speech recognition errors on children's speech.
- Usage beyond what the limits intend (cost).
- Behaviour changes when the provider updates the model.

## Open questions for the owner

- How long are usage counters kept, and do they contain IP addresses?
- What do the model provider's API terms say about retaining and using session audio?
- Is the app meant to be used only with an adult present? If so, how is that communicated?
