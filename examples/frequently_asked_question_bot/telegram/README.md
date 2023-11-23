## Description

Example FAQ bot built on `dff`. Uses telegram as an interface.

This bot listens for user questions and finds similar questions in its database by using the `clips/mfaq` model.

It displays found questions as buttons. Upon pressing a button, the bot sends an answer to the question from the database.


An example of bot usage:

![image](https://user-images.githubusercontent.com/61429541/219064505-20e67950-cb88-4cff-afa5-7ce608e1282c.png)

## Running the bot in docker

### Step 1: Configuring the docker services

In order for the bot to work, update the [.env](.env) file replacing the template with the actual value of your Telegram token.

```
TG_BOT_TOKEN=***
```

## Step 2: Launching the docker project
*The commands below should be run from the /examples/frequently_asked_question_bot/telegram directory.*

Build the bot:
```commandline
docker-compose build
```
Testing the bot:
```commandline
docker-compose run bot pytest test.py
```

Running the bot:
```commandline
docker-compose run bot python run.py
```

Running in background
```commandline
docker-compose up -d
```
## Running the bot in the local Python environment

### Step 1: Configuring the service

In order for the bot to work, update the [.env](.env) file replacing the template with the actual value of your Telegram token.

```
TG_BOT_TOKEN=***
```
### Step 2: Installing dependencies

Build the bot:
```commandline
pip3 install -r requirements.txt
```
### Step 3: Runnig with CLI

Running the bot:
```commandline
python run.py
```

To launch the test suite, run:
```commandline
pytest test.py
```
