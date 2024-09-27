from pathlib import Path
import logging

from chatsky import Pipeline


logging.basicConfig(level=logging.INFO)

current_dir = Path(__file__).parent

pipeline = Pipeline.from_file(
    file=current_dir / "pipeline.yaml",
    custom_dir=current_dir / "custom_dir",
    # these paths can also be relative (e.g. file="pipeline.yaml")
    # but that would only work if executing pipeline in this directory
)

if __name__ == "__main__":
    pipeline.run()
