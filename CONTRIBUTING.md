## Introduction
We will be glad to receive your pull requests and issues for adding new features if you are missing something.
We always look forward to your contributions to the Dialog Flow Runner. 

## Managing your workflow
We use `make` as handy automation tool, which reads `makefile` to get specification for commands. `make` is a quite popular tool for building software. Usage signature of the make is `make COMMAND` if your environment supports make autocompletions you can use tab for example:
```bash
make <tab>
```

### Platforms

We suggest using a linux-based platform for addon development. While the template can be cloned to any platforms that can run python and cookiecutter, the make functionality will not be available for Windows out of the box.

### Virtual Environment
The most essential part is setting up the virtual environment. The command also installs all the development dependencies, which are required for development.

```bash
make venv
```

Do not forget to activate the environment, if you aim to install any other dependencies.
```bash
source venv/bin/activate
```

### Pre-commit
We also provide a simple pre-commit hook for git that prevents you from commiting unchecked code. Note that this action will reinitialize the git repository inside the project directory, if you have already created one. To use it, run

```bash
make pre_commit
```

### Documentation
Assuming you use docstrings to annotate your modules and objects, you can easily build the Sphinx documentation for your module 
by activating the virtual environment and then running

```bash
make build_doc
```
after that `docs/build` dir was created and you can open index file by your browser:
```bash
$BROWSER docs/build/html/index.html
```
### Style
For style supporting we propose `black` formatter, which is a PEP 8 compliant opinionated formatter. Black reformats entire files in place. Style configuration options are deliberately limited and rarely added. It doesn't take previous formatting into account. See more about [black](https://github.com/psf/black). 
To format your code, run

```bash
make format
```
### Test
We use `black`, `mypy`, `flake8` as code style checkers and `pytest` as unit-test runner.
```bash
make test_all
```
### Other provided features 
You can get more info about make commands by `help`:

```bash
make help
```

## Deployment

The template includes a handful of github workflows that allow you to lint and test your code as well as to deploy your newly made package straight to [PYPI](https://pypi.org/).

If you plan to use the latter feature, be sure to set the `PYPI_TOKEN` secret in your repository.
