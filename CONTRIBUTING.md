## Introduction
We will be glad to receive your pull requests (PRs) and issues for adding new features if you are missing something.
We always look forward to your contributions to the Dialog Flow Framework (DFF). 

## Rules for submitting a PR

All PRs are reviewed by DFF developers team.
In order to make the job of reviewing easier and increase the chance that your PR will be accepted,
please add a short description with information about why this PR is needed and what changes will be made.
Please use the following rules to write the names of branches and commit messages.

### Rules for writing names of branches

We hope that you adhere to the following
[format](https://gist.github.com/seunggabi/87f8c722d35cd07deb3f649d45a31082)
of branch naming: `<type>/<subject>`, where `<type>` can be taken from the following list:

- `feat` or `feature`: (new feature for the user, not a new feature for build script)
- `fix`: (bug fix for the user, not a fix to a build script)
- `docs`: (changes to the documentation)
- `style`: (formatting, missing semi colons, etc; no production code change)
- `refactor`: (refactoring production code, eg. renaming a variable)
- `test`: (adding missing tests, refactoring tests; no production code change)
- `chore`: (updating grunt tasks etc; no production code change)

For example:

```
style/formatting_file_1
^---^ ^---------------^
|     |
|     +---> Issue's keywords
|
+---------> Type
```

### Commit message rules

We ask that you adhere to the following
[commit message format](https://gist.github.com/joshbuchea/6f47e86d2510bce28f8e7f42ae84c716): `<type>: <subject>`,
where `<type>` can be taken from the following list:

- `feat`: (new feature for the user, not a new feature for build script)
- `fix`: (bug fix for the user, not a fix to a build script)
- `docs`: (changes to the documentation)
- `style`: (formatting, missing semi colons, etc; no production code change)
- `refactor`: (refactoring production code, eg. renaming a variable)
- `test`: (adding missing tests, refactoring tests; no production code change)
- `chore`: (updating grunt tasks etc; no production code change)

For example:

```
docs: add description to the func
^--^  ^-------------------------^
|     |
|     +-> Summary in present tense.
|
+-------> Type
```

## Managing your workflow
We use `make` as handy automation tool, which reads `makefile` to get specification for commands.
`make` is a quite popular tool for building software. Usage signature of the `make` is `make COMMAND`.
If your environment supports `make` autocompletions you can use Tab to complete the `COMMAND`.

### Platforms

We suggest using a linux-based platform for addon development.
While the template can be cloned to any platforms that can run `python` and `cookiecutter`,
the `make` functionality will not be available for Windows out of the box.

### Virtual Environment
The most essential part is setting up the virtual environment.
The following command installs all the dependencies, which are required for development.

```bash
make venv
```

Do not forget to activate the environment, if you aim to install any other dependencies.
```bash
source venv/bin/activate
```

### Pre-commit
We also provide a simple pre-commit hook for `git` that prevents you from commiting unchecked code. Note that this action will reinitialize the git repository inside the project directory, if you have already created one. To use it, run

```bash
make pre_commit
```

### Documentation
Assuming you use [reStructuredText (reST) format docstrings](https://sphinx-rtd-tutorial.readthedocs.io/en/latest/docstrings.html)
to annotate your modules and objects. You can easily build the Sphinx documentation for your module 
by activating the virtual environment and then running

```bash
make doc
```

After that `docs/build` dir will be created and you can open index file by your browser:

```bash
$BROWSER docs/build/index.html
```

### Style
For style supporting we propose `black`, which is a PEP 8 compliant opinionated formatter. `Black` reformats entire files in place. Style configuration options are deliberately limited and rarely added. It doesn't take previous formatting into account. See more about [black](https://github.com/psf/black). 
To format your code, run

```bash
make format
```

### Test
We use `black`, `mypy`, `flake8` as code style checkers and `pytest` as unit-test runner.
To run unit-tests only, use
```bash
make test
```
To execute all tests, including integration with DBs and APIs tests, run
```bash
make test_all
```
for successful execution of this command `Docker` and `docker-compose` are required.

To make sure that the code satisfies only the style requirements, run
```bash
make lint
```
And if it doesn't, to automatically fix whatever is possible with `black`, run
```bash
make format
```

Tests are configured via [`.env_file`](.env_file).

### Docker
For integration tests, DFF uses Docker images of supported databases as well as docker-compose configuration.
The following images are required for complete integration testing:
1. `mysql`
2. `postgres`
3. `redis`
4. `mongo`
5. `cr.yandex/yc/yandex-docker-local-ydb`

All of them will be downloaded, launched and awaited upon running integration test make command (`make test_all`).
However, they can be downloaded separately with `make docker_up` and awaited with `make wait_db` commands.

### Other provided features 
You can get more info about `make` commands by `help`:

```bash
make help
```

## Deployment

The template includes a handful of `github` workflows that allow you to lint and test your code as well as to deploy your newly made package straight to [PYPI](https://pypi.org/).

If you plan to use the latter feature, be sure to set the `PYPI_TOKEN` secret in your repository.
