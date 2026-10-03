# Engagement scope: pikapi

| | |
|---|---|
| **Target** | pikapi, a voice chat app for young children ([live site](https://www.dora-tech.net/pikapi/)) |
| **Owner** | Luu Tien Duc (also the assessor) |
| **Authorisation** | The owner authorises testing of their own system within this scope (2026-10-03) |
| **Version** | v0, 2026-10-03 |

## In scope

- **Pages:** `/`, `/miku/`, `/vrm/`, `/pngtuber/`, and a local development copy of the same app.
- **Conversation behaviour:** safety and suitability for children, staying in Japanese, English
  or Vietnamese, staying in persona.
- **Attacks on the model:** jailbreaks, prompt injection, system-prompt disclosure, and
  injection through content the app pulls in from Google Search.
- **The app's own backend:** access control and usage limits on the session-token service.
- **Cost abuse:** ways to make the app spend more than intended.
- **Voice channel:** speech recognition accuracy, response latency, and instructions hidden in
  audio.

## Out of scope

- Google's Gemini service itself, beyond how this app uses it.
- Cloud infrastructure beyond the app's own endpoints, and other sites on the same domain.
- Denial-of-service and load testing.
- Social engineering of people.

## Rules of engagement

- Synthetic test data only. No real children's voices or personal data.
- Harmful-content tests check that the app refuses or redirects. They don't try to extract
  complete harmful instructions.
- Development runs use the kit's mock target and free local stand-ins. Paid runs against the real
  app happen once, in the final phase, under a monthly budget cap.
- Most runs target the local copy. The live site gets a small confirmation set.
- A finding's details are published only after it is fixed and re-tested.
