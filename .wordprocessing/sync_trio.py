import copy
import json
import os
import re
from pathlib import Path
import tempfile


WORKSPACE = Path(__file__).resolve().parent
REPO = WORKSPACE.parent
WORKING_FILE = WORKSPACE / "WordProcessingTrio.jet"
PATCH_FILE = REPO / "games/WordProcessing/content/en/WordProcessingTrio.jet"
AUDIO_DIRECTORY = PATCH_FILE.with_suffix("")
AUDIO_FIELDS = {
    "IntroAudio": "intro",
    "TitleAudio0": "buckets_0_audio",
    "TitleAudio1": "buckets_1_audio",
    "TitleAudio2": "buckets_2_audio",
    "OutroAudio": "outro",
}


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as stream:
        return json.load(stream)


def build_patch(working: dict) -> dict:
    if not isinstance(working, dict):
        raise ValueError("Working file must contain a JSON object")
    entries = working.get("content")
    if not isinstance(entries, list):
        raise ValueError("Working file: 'content' must be a list")
    output = copy.deepcopy(working)
    output["content"] = []
    for index, work in enumerate(entries):
        if not isinstance(work, dict):
            raise ValueError(f"Entry {index}: must be a JSON object")
        if type(work.get("done")) is not bool:
            raise ValueError(f"Entry {index} ({work.get('id', '?')}): 'done' must be a JSON boolean")
        if work["done"]:
            result = copy.deepcopy(work)
            del result["done"]
            for name in AUDIO_FIELDS:
                result.pop(name, None)
            output["content"].append(result)
    return output


def build_audio_data(work: dict) -> dict:
    fields = []
    for name, filename in AUDIO_FIELDS.items():
        text = work.get(name)
        if not isinstance(text, str):
            raise ValueError(f"Entry {work.get('id', '?')}: '{name}' must be a string")
        enabled = bool(text.strip())
        fields.append({"t": "B", "v": "true" if enabled else "false", "n": f"Has{name}"})
        audio = {"t": "A", "v": filename, "n": name}
        if enabled:
            audio["s"] = text
        fields.append(audio)
    return {"fields": fields}


def build_audio_files(working: dict) -> dict:
    output = {}
    for work in working["content"]:
        if not work["done"]:
            continue
        prompt_id = str(work.get("id", ""))
        if not re.fullmatch(r"[A-Za-z0-9_-]+", prompt_id):
            raise ValueError(f"Unsafe or missing prompt id: {prompt_id!r}")
        if prompt_id in output:
            raise ValueError(f"Duplicate completed prompt id: {prompt_id}")
        output[prompt_id] = build_audio_data(work)
    return output


def write_json(path: Path, output: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=path.parent,
        prefix=f"{path.stem}.", suffix=".tmp", delete=False,
    ) as stream:
        temp_path = Path(stream.name)
        json.dump(output, stream, ensure_ascii=False, indent=1)
        stream.write("\n")
    try:
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def main() -> None:
    working = read_json(WORKING_FILE)
    # Validate all generated data before writing any output files.
    output = build_patch(working)
    audio_files = build_audio_files(working)
    for prompt_id, data in audio_files.items():
        write_json(AUDIO_DIRECTORY / prompt_id / "data.jet", data)
    write_json(PATCH_FILE, output)
    print(f"{len(output['content'])}/{len(working['content'])} completed prompts copied to {PATCH_FILE}")
    print(f"{len(audio_files)} audio data.jet files written to {AUDIO_DIRECTORY}")


if __name__ == "__main__":
    main()
