import sys
from pathlib import Path
from dff.core.pipeline import Pipeline, CLIMessengerInterface


sys.path.insert(0, str(Path(__file__).absolute().parent.parent))

from examples.base_example import regex_model, script

pipeline = Pipeline.from_script(
    script,
    start_label=("root", "start"),
    fallback_label=("root", "fallback"),
    messenger_interface=CLIMessengerInterface(intro="Starting Dff bot..."),
    context_storage={},
    pre_services=[regex_model],
)

if __name__ == "__main__":
    pipeline.run()
