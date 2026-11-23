# Default style

The house look for vertical shorts. The engine reads the settings block below;
everything outside it is explanation for humans. Copy this file to make a new
style and pass it with `--style styles/<name>.md`.

## The look in one paragraph

Fast, clean, readable with the sound off. Big white captions, two or three words
at a time, the spoken word lit in yellow. A hook title sits at the top for the
first three seconds. A thin progress bar runs along the top edge. Jump cuts are
hidden with a slight punch-in on every other segment. No effects beyond that.

## Settings

```json
{
  "canvas": {"width": 1080, "height": 1920, "fps": 30},
  "pacing": {
    "max_pause": 0.45,
    "target_pause": 0.28,
    "lead_in": 0.12,
    "tail": 0.35,
    "long_pause": 1.0,
    "jump_cut_zoom": 1.06
  },
  "captions": {
    "font": "Inter ExtraBold",
    "size": 92,
    "color": "#FFFFFF",
    "highlight": "#FFD60A",
    "outline_color": "#000000",
    "outline": 7,
    "shadow": 3,
    "y": 1290,
    "max_words": 3,
    "max_chars": 16,
    "uppercase": true,
    "pop": true
  },
  "title": {
    "font": "Inter",
    "size": 58,
    "color": "#FFFFFF",
    "box_color": "#111418",
    "y": 250,
    "seconds": 3.0,
    "wrap_chars": 24
  },
  "progress_bar": {"enabled": true, "color": "#FFD60A", "height": 10},
  "audio": {"loudness_lufs": -14, "true_peak_db": -1.5, "music_db": -24},
  "export": {"crf": 18, "preset": "medium", "audio_bitrate": "192k"}
}
```

## Why these numbers

- **Caption position (y 1290 of 1920):** below the face, above the area that
  TikTok, Reels and Shorts cover with their own buttons and captions.
- **Pauses over 0.45 s are tightened to 0.28 s:** short enough to feel fast, long
  enough that sentences do not collide.
- **-14 LUFS:** the loudness the big platforms normalise to.
- **Fonts:** Inter ships in `assets/fonts/` so the look is the same on every machine.
