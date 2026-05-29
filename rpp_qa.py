from __future__ import annotations

import importlib.util
import math
import uuid
import wave
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, Sequence

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".aif", ".aiff", ".m4a"}
QUALITY_TRACK_ORDER = ("excellent", "acceptable", "not_evaluated", "poor")
QUALITY_TRACK_NAMES = {
    "excellent": "excellent",
    "acceptable": "acceptable",
    "not_evaluated": "not_evaluated",
    "poor": "poor",
}


class QAResult(Protocol):
    audio_file: str
    quality: str


def new_guid() -> str:
    return "{" + str(uuid.uuid4()).upper() + "}"


def _rpp_quote(value: str) -> str:
    return value.replace("\\", "/").replace('"', "'")


@dataclass
class RPPNode:
    name: str
    args: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    children: list["RPPNode"] = field(default_factory=list)

    def render(self, indent: int = 0) -> str:
        prefix = "  " * indent
        header = f"{prefix}<{self.name}"
        if self.args:
            header += " " + " ".join(self.args)
        header += "\n"
        out = [header]
        for line in self.lines:
            out.append(f"{prefix}  {line}\n")
        for child in self.children:
            out.append(child.render(indent + 1))
        out.append(f"{prefix}>\n")
        return "".join(out)


@dataclass
class Item:
    file_path: Path
    position: float
    length: float
    iid: int
    guid: str = field(default_factory=new_guid)
    iguid: str = field(default_factory=new_guid)

    @property
    def name(self) -> str:
        return self.file_path.name

    def to_node(self) -> RPPNode:
        node = RPPNode("ITEM")
        node.lines.extend(
            [
                f"POSITION {self.position:.8f}",
                "SNAPOFFS 0",
                f"LENGTH {self.length:.8f}",
                "LOOP 1",
                "ALLTAKES 0",
                "FADEIN 1 0 0 1 0 0 0",
                "FADEOUT 1 0 0 1 0 0 0",
                "MUTE 0 0",
                "SEL 0",
                f"IGUID {self.iguid}",
                f"IID {self.iid}",
                f'NAME "{_rpp_quote(self.name)}"',
                "VOLPAN 1 0 1 -1",
                "SOFFS 0",
                "PLAYRATE 1 1 0 -1 0 0.0025",
                "CHANMODE 0",
                f"GUID {self.guid}",
            ]
        )
        source = RPPNode("SOURCE", ["WAVE"])
        source.lines.append(f'FILE "{_rpp_quote(str(self.file_path))}"')
        node.children.append(source)
        return node


@dataclass
class Track:
    name: str
    items: list[Item] = field(default_factory=list)
    guid: str = field(default_factory=new_guid)

    def to_node(self) -> RPPNode:
        node = RPPNode("TRACK", [self.guid])
        node.lines.extend(
            [
                f'NAME "{_rpp_quote(self.name)}"',
                "PEAKCOL 16576",
                "BEAT -1",
                "AUTOMODE 0",
                "PANLAWFLAGS 3",
                "VOLPAN 1 0 -1 -1 1",
                "MUTESOLO 0 0 0",
                "IPHASE 0",
                "PLAYOFFS 0 1",
                "ISBUS 0 0",
                "BUSCOMP 0 0 0 0 0",
                "SHOWINMIX 1 0.6667 0.5 1 0.5 0 0 0 0",
                "FIXEDLANES 9 0 0 0 0",
                "SEL 0",
                "REC 0 0 0 0 0 0 0 0",
                "VU 2",
                "TRACKHEIGHT 0 0 0 0 0 0 0",
                "INQ 0 0 0 0.5 100 0 0 100",
                "NCHAN 2",
                "FX 1",
                f"TRACKID {self.guid}",
                "PERF 0",
                "MIDIOUT -1",
                "MAINSEND 1 0",
            ]
        )
        for item in self.items:
            node.children.append(item.to_node())
        return node


@dataclass
class Project:
    tracks: list[Track]
    name: str = "AsRec QA Review"
    reaper_version: str = '"7.69/win64"'
    sample_rate: int = 48_000

    def _header_lines(self) -> list[str]:
        timestamp = int(datetime.now(tz=timezone.utc).timestamp())
        return [
            f"<REAPER_PROJECT 0.1 {self.reaper_version} {timestamp} 0",
            "  <NOTES 0 2",
            f"    |{_rpp_quote(self.name)}",
            "  >",
            "  RIPPLE 0 0",
            "  GROUPOVERRIDE 0 0 0 0",
            "  AUTOXFADE 135",
            "  RECORD_PATH \"Media\" \"\"",
            "  GLOBAL_AUTO -1",
            "  TEMPO 120 4 4 0",
            "  PLAYRATE 1 0 0.25 4",
            f"  SAMPLERATE {self.sample_rate} 1 0",
            "  MASTER_NCH 2 2",
            "  MASTER_VOLUME 1 0 -1 -1 1",
            "  MASTER_PANMODE 3",
            "  MASTER_FX 1",
        ]

    def render(self) -> str:
        out = [line + "\n" for line in self._header_lines()]
        for track in self.tracks:
            out.append(track.to_node().render(indent=1))
        out.append("  <EXTENSIONS\n")
        out.append("  >\n")
        out.append(">\n")
        return "".join(out)

    def save(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.render(), encoding="utf-8")


@dataclass
class QAProjectConfig:
    source_root: Path
    output_file: Path
    spacing_seconds: float = 3.0
    start_offset: float = 0.0
    sample_rate: int = 48_000


def guessed_item_length(audio_file: Path) -> float:
    """Estimate duration in seconds, preferring exact decoders when available."""
    if importlib.util.find_spec("soundfile"):
        import soundfile as sf

        try:
            info = sf.info(str(audio_file))
            if info.samplerate > 0:
                exact_seconds = info.frames / info.samplerate
                return math.ceil(exact_seconds * 1000) / 1000
        except Exception:
            pass

    if audio_file.suffix.lower() == ".wav":
        try:
            with wave.open(str(audio_file), "rb") as wav_file:
                frame_rate = wav_file.getframerate()
                if frame_rate > 0:
                    exact_seconds = wav_file.getnframes() / frame_rate
                    return math.ceil(exact_seconds * 1000) / 1000
        except wave.Error:
            pass

    size_bytes = audio_file.stat().st_size
    approx_seconds = max(0.25, min(30.0, size_bytes / (48000 * 2 * 2)))
    return math.ceil(approx_seconds * 1000) / 1000


def _build_audio_index(source_root: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in source_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        rel = path.relative_to(source_root).as_posix().lower()
        index.setdefault(rel, path)
        index.setdefault(path.name.lower(), path)
    return index


def _resolve_audio_path(source_root: Path, audio_file: str, audio_index: dict[str, Path]) -> Path | None:
    candidate = Path(audio_file)
    if candidate.is_absolute() and candidate.exists():
        return candidate

    relative_candidate = source_root / candidate
    if relative_candidate.exists():
        return relative_candidate

    normalized = candidate.as_posix().lower()
    if normalized in audio_index:
        return audio_index[normalized]

    return audio_index.get(candidate.name.lower())


def _normalize_quality(value: str) -> str:
    quality = (value or "").strip().lower().replace(" ", "_").replace("-", "_")
    if quality in {"not_evaluated", "not_evaluable", "unevaluated"}:
        return "not_evaluated"
    if quality in {"excellent", "acceptable", "poor"}:
        return quality
    return "not_evaluated"


def generate_qa_project(cfg: QAProjectConfig, results: Sequence[QAResult]) -> Project:
    """Create a REAPER project with one track per transcription quality bucket."""
    if not cfg.source_root.exists() or not cfg.source_root.is_dir():
        raise ValueError(f"Audio folder does not exist or is not a directory: {cfg.source_root}")

    audio_index = _build_audio_index(cfg.source_root)
    if not audio_index:
        raise ValueError(f"No audio files found under: {cfg.source_root}")

    tracks = {quality: Track(name=QUALITY_TRACK_NAMES[quality]) for quality in QUALITY_TRACK_ORDER}
    cursors = {quality: cfg.start_offset for quality in QUALITY_TRACK_ORDER}
    iid = 1
    missing: list[str] = []

    for result in results:
        audio_path = _resolve_audio_path(cfg.source_root, result.audio_file, audio_index)
        if audio_path is None:
            missing.append(result.audio_file)
            continue

        quality = _normalize_quality(result.quality)
        length = guessed_item_length(audio_path)
        tracks[quality].items.append(
            Item(
                file_path=audio_path.resolve(),
                position=cursors[quality],
                length=length,
                iid=iid,
            )
        )
        cursors[quality] += length + cfg.spacing_seconds
        iid += 1

    if missing:
        preview = ", ".join(missing[:5])
        suffix = "" if len(missing) <= 5 else f" ... (+{len(missing) - 5} more)"
        print(f"[WARN] QA Reaper project skipped missing audio files: {preview}{suffix}")

    if not any(track.items for track in tracks.values()):
        raise ValueError("No QA Reaper items could be created from the comparison results.")

    project_tracks = [tracks[quality] for quality in QUALITY_TRACK_ORDER]
    project = Project(tracks=project_tracks, sample_rate=cfg.sample_rate)
    project.save(cfg.output_file)
    return project
