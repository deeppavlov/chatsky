## Description

Example FAQ bot built on `dff` with a web interface.

This example serves bot responses either through Telegram or through a website with a chat interface using `WebSockets`. You can configure the service to use either of those using the
"INTERFACE" environment variable by setting it to "telegram" or "web", respectively. 
Chat history is stored inside a `postgresql` database.


The web interface is accessible via http://localhost:80. In case with Telegram,
the service will power the bot the token of which you pass at the configuration stage.

**Note that Telegram needs to configure a web hook, so you'll only be able to launch it using an SSL-protected url which needs to be passed through the HOST environment variable.**

The bot itself works as follows:

Whenever a user asks a question it searches for the most similar question in its database using `clips/mfaq` an answer to which is sent to the user.

A showcase of the website:
![faq_web](https://user-images.githubusercontent.com/61429541/233875303-b9bc81c9-522b-4596-8599-6efcfa708d1e.gif)

## Running the project

### Step 1: Configuring docker services

The project services need to be configured with variables that can be set through the [.env](.env) file. Update the file replacing the placeholders with desired values.

```shell
POSTGRES_USERNAME=***
POSTGRES_PASSWORD=***
POSTGRES_DB=***
TELEGRAM_TOKEN=***
INTERFACE=telegram
# or INTERFACE=web
# or INTERFACE=cli
HOST=*** # required for telegram
```

### Step 2: Launching the docker project
*The commands below should be run from the /examples/frequently_asked_question_bot/web directory.*

Launching the project
```commandline
docker-compose up --build -d
```
