## Introduction
We are almost completely finished with the main functionality. Nevertheless, we will be glad to receive your pull requests and issues for adding new features if you are missing something.
We always look forward to your contributions to Dialog Flow Generics. 

## Development
### Enviroment
Prepare the enviroment:

```bash
make venv
# optionally, you can set test-first pre-commit hooks
make hooks
```
### Documentation
Build documentation:
```bash
make build_doc
```
after that `docs/build` dir was created and you can open index file by your browser:
```bash
firefox docs/build/html/index.html
```
### Style
```bash
make format
```
### Test
```bash
make test_all
```