"""Build the playable Trio patch from the English source and completed translations.

Set ``done`` to true in WordProcessingTrio.jet for each completed prompt, then run:
    python .workspace/WordProcessing/sync_trio.py

The original snapshot fixes all technical fields to the build used when the
working copy was created. Only prompts marked ``done: true`` are written to
the playable patch.
"""

import copy
import json
import os
from pathlib import Path
import tempfile


WORKSPACE = Path(__file__).resolve().parent
REPO = WORKSPACE.parent.parent
WORKING_FILE = WORKSPACE / "WordProcessingTrio.jet"
ORIGINAL_FILE = WORKSPACE / "WordProcessingTrio.original.jet"
PATCH_FILE = REPO / "games/WordProcessing/content/en/WordProcessingTrio.jet"


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as stream:
        return json.load(stream)


def entries_by_id(data: dict, label: str) -> dict:
    entries = data.get("content")
    if not isinstance(entries, list):
        raise ValueError(f"{label}: 'content' must be a list")
    ids = [entry.get("id") for entry in entries]
    if len(ids) != len(set(ids)) or any(not isinstance(id_, str) for id_ in ids):
        raise ValueError(f"{label}: IDs must be unique strings")
    return {entry["id"]: entry for entry in entries}


def validate_buckets(work: dict, original: dict) -> None:
    work_buckets = work.get("buckets")
    original_buckets = original.get("buckets")
    if not isinstance(work_buckets, list) or len(work_buckets) != len(original_buckets):
        raise ValueError(f"{work['id']}: bucket count differs from English original")
    for bucket, source_bucket in zip(work_buckets, original_buckets):
        if not isinstance(bucket, dict) or bucket.keys() != source_bucket.keys():
            raise ValueError(f"{work['id']}: bucket fields differ from English original")
        if not isinstance(bucket.get("answers"), list) or not all(
            isinstance(answer, str) for answer in bucket["answers"]
        ):
            raise ValueError(f"{work['id']}: answers must be a list of strings")
        for field in ("bucketTitle", "shorthand"):
            if not isinstance(bucket.get(field), str):
                raise ValueError(f"{work['id']}: {field} must be a string")


def main() -> None:
    working = read_json(WORKING_FILE)
    original = read_json(ORIGINAL_FILE)
    if working.keys() != original.keys():
        raise ValueError("Working and original files have different top-level fields")

    work_by_id = entries_by_id(working, "Working file")
    source_by_id = entries_by_id(original, "English original")
    if list(work_by_id) != list(source_by_id):
        raise ValueError("Prompt IDs or order differ from the English original")

    output = copy.deepcopy(original)
    output["content"] = []
    completed = 0
    for source in original["content"]:
        id_ = source["id"]
        work = work_by_id[id_]
        done = work.get("done")
        if type(done) is not bool:
            raise ValueError(f"{id_}: 'done' must be a JSON boolean")
        work_technical = {key: value for key, value in work.items() if key not in ("buckets", "done")}
        source_technical = {key: value for key, value in source.items() if key != "buckets"}
        if work_technical != source_technical:
            raise ValueError(f"{id_}: technical fields differ from the English original")
        validate_buckets(work, source)
        if done:
            result = copy.deepcopy(source)
            result["buckets"] = copy.deepcopy(work["buckets"])
            output["content"].append(result)
            completed += 1

    PATCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=PATCH_FILE.parent,
        prefix="WordProcessingTrio.", suffix=".tmp", delete=False,
    ) as stream:
        temp_path = Path(stream.name)
        json.dump(output, stream, ensure_ascii=False, indent=1)
        stream.write("\n")
    try:
        os.replace(temp_path, PATCH_FILE)
    finally:
        temp_path.unlink(missing_ok=True)
    print(f"{completed}/{len(original['content'])} completed prompts copied to {PATCH_FILE}")


if __name__ == "__main__":
    main()
