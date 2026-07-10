"""Video processing utilities for ZipZop Pro AI Editor."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from moviepy.editor import VideoFileClip, concatenate_videoclips
from moviepy.video.VideoClip import VideoClip


class VideoProcessingError(RuntimeError):
    """Raised when MoviePy cannot process the uploaded video."""


@dataclass(frozen=True)
class ProcessingResult:
    original_duration: float
    processed_duration: float
    removed_seconds: float


def _non_silent_segments(
    clip: VideoFileClip,
    sample_step: float = 0.25,
    silence_threshold: float = 0.018,
    padding: float = 0.25,
) -> list[tuple[float, float]]:
    """Return dynamic non-silent time ranges for the full video duration.

    There is intentionally no fixed duration cap: the loop walks from 0 to
    ``clip.duration`` so clips are processed according to their real length.
    """
    if clip.audio is None:
        return [(0.0, float(clip.duration))]

    ranges: list[tuple[float, float]] = []
    active_start: float | None = None
    current = 0.0
    duration = float(clip.duration)

    while current < duration:
        try:
            frame = clip.audio.get_frame(min(current, duration - 0.001))
            volume = float(abs(frame).mean())
        except Exception as exc:
            raise VideoProcessingError(f"Could not inspect audio at {current:.2f}s: {exc}") from exc

        if volume >= silence_threshold and active_start is None:
            active_start = max(0.0, current - padding)
        elif volume < silence_threshold and active_start is not None:
            ranges.append((active_start, min(duration, current + padding)))
            active_start = None

        current += sample_step

    if active_start is not None:
        ranges.append((active_start, duration))

    if not ranges:
        return [(0.0, duration)]

    merged: list[tuple[float, float]] = []
    for start, end in ranges:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
    return merged


def trim_silence_from_video(input_path: Path, output_path: Path) -> ProcessingResult:
    """Trim silent ranges from a video and write an MP4 output."""
    if not input_path.exists():
        raise VideoProcessingError(f"Input file does not exist: {input_path}")

    try:
        with VideoFileClip(str(input_path)) as clip:
            if not clip.duration or clip.duration <= 0:
                raise VideoProcessingError("Video duration is empty or invalid.")

            segments = _non_silent_segments(clip)
            subclips: list[VideoClip] = [clip.subclip(start, end) for start, end in segments if end > start]

            if not subclips:
                raise VideoProcessingError("No usable video segments were found.")

            final_clip = subclips[0] if len(subclips) == 1 else concatenate_videoclips(subclips)
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                final_clip.write_videofile(
                    str(output_path),
                    codec="libx264",
                    audio_codec="aac",
                    temp_audiofile=str(output_path.with_suffix(".temp-audio.m4a")),
                    remove_temp=True,
                    logger="bar",
                )
                processed_duration = float(final_clip.duration)
            finally:
                if final_clip is not subclips[0]:
                    final_clip.close()
                for subclip in subclips:
                    subclip.close()

            original_duration = float(clip.duration)
            return ProcessingResult(
                original_duration=round(original_duration, 2),
                processed_duration=round(processed_duration, 2),
                removed_seconds=round(max(0.0, original_duration - processed_duration), 2),
            )
    except VideoProcessingError:
        raise
    except Exception as exc:
        raise VideoProcessingError(f"MoviePy failed to process '{input_path.name}': {exc}") from exc
