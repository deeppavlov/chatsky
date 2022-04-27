## Introduction
We are almost completely finished with the main functionality. Nevertheless, we will be glad to receive your pull requests and issues for adding new features if you are missing something. We know that we have weaknesses in the documentation and basic examples. 
We will be glad if you contribute to Dialog Flow Engine. 

## Development
### Enviroment
Prepare the enviroment:

```bash
pip install -r requirements_dev.txt
pip install -r requirements_test.txt
pip install -r requirements.txt
pip install -e .
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