from pathlib import Path

from dff import Pipeline


SCRIPT_FILE = Path(__file__).parent / "script.json"

pipeline = Pipeline.from_file(SCRIPT_FILE)


if __name__ == "__main__":
    pipeline.run()
