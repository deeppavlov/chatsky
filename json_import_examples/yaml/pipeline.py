from pathlib import Path

from chatsky import Pipeline
from chatsky.messengers.http_interface import HTTPMessengerInterface

SCRIPT_FILE = Path(__file__).parent / "script.yaml"

messenger_interface = HTTPMessengerInterface()
pipeline = Pipeline.from_file(SCRIPT_FILE, messenger_interface=messenger_interface)

if __name__ == "__main__":
    pipeline.run()
