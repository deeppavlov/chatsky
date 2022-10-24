# Statistics collection for Dialog Flow Engine

## Demo

```bash
# assuming that you cloned the repository
pip install .[postgres] # install

docker-compose up -d psql # launch images
docker-compose up -d superset

#
# when superset is launched for the first time, don't forget to use the following commands:
#
# docker exec -it superset superset fab create-admin --username admin \
#              --firstname Superset \
#              --lastname Admin \
#              --email admin@superset.com \
#              --password admin
# docker exec -it superset superset db upgrade
# docker exec -it superset superset init
#

make collect-examples DB_PASSWORD=pass # collect examples

df_stats cfg_from_file examples/config.yaml --outfile=superset_dashboard.zip # visualize examples
df_stats import_dashboard \
    --username=admin \
    --password=admin \
    --infile=superset_dashboard.zip \
    --db.password=password
```

## Index

- [Introduction](#introduction)
- [Installation](#installation)
- [Statistics collection](#statistics-collection)
    - [Run mock examples of statisctics collection](#run-mock-examples-of-statisctics-collection)
- [Display your data](#display-your-data)
    - [Create a Superset instance](#create-a-superset-instance)
    - [Adjust Dashboard Configuration](#adjust-dashboard-configuration)
    - [Import the Dashboard Config](#import-the-dashboard-config)
- [Preset support](#preset-support)

## Introduction

Dialog Flow Node Stats, or `dff_node_stats` is a module, that extends [dialog_flow_engine](https://github.com/deepmipt/dialog_flow_engine). It collects usage statistics for your conversational service and allows you to visualize them using a pre-configured dashboard for [Apache Superset](https://superset.apache.org/) and [Preset](https://preset.io/).

Currently, we offer support for multiple database types that can be used to store your data:

* [Postgresql](https://www.postgresql.org/)
* [Clickhouse](https://clickhouse.com/)
* [CSV](#)

In the future, we intend to add support for other SQL-compatible backends.

## Installation

```bash
pip install df_stats[postgres]
pip install df_stats[clickhouse]
```

## Statistics collection

Assuming that you have defined a `df_engine` **Actor** and assigned it to `actor` variable, you can update your code with the following snippets.

```python
# import dependencies
from df_stats import Stats
# ...

# Define a destination for stats saving
db_uri = "postgresql://user:password@host:5432/default"
#
# clickhouse:
# db_uri = "clickhouse://user:password@host:8123/default"
# CSV:
# db_uri = "csv://mydir/myfile.csv"
#
stats = Stats.from_uri(db_uri)


```

### Statistics collection demo

The easiest way to understand, how the statistics collection works, is to try out one of the demo scripts.
Normally, in order to do so, you should pass your db connection parameters either as cli arguments or as a file.

```bash
python examples/collect_stats.py cfg_from_file --db.password=xxx myconfig.yaml
python examples/collect_stats_vscode_demo.py cfg_from_file --db.password=xxx myconfig.yaml
python examples/pipeline.py cfg_from_file --db.password=xxx myconfig.yaml
```

However, we also provide a makefile shortcut, in which the connection parameters are set to defaults (see `.env_file` and `examples/example_config.yaml`). This means that all you have to do to get an example database is to run:

```bash
pip install df_stats[postgres]
docker-compose up psql
make wait-db
make collect-examples DB_PASSWORD=pass
```

## Display your data

### Create a Superset instance

There are multiple ways to create an Apache Superset instance: you can install it locally or use a [Docker image](https://hub.docker.com/r/apache/superset) with docker or docker-compose. Whichever option you pick, you will still be able to import the standard dashboard template.

* **However, if you intend to use Clickhouse, keep in mind that it requires `clickhouse-connect` library to be installed.** 
The easiest solution is to use a dockerfile with the following structure:

```dockerfile
FROM apache/superset
USER root
RUN pip install clickhouse-connect
USER superset
```
* Please, consult the [Superset documentation](https://superset.apache.org/docs/databases/installing-database-drivers/) for dependency installation instructions, if you deploy Superset locally.

### Adjust Dashboard Configuration

In order to run the dashboard in Apache Superset, you should update the default configuration with the credentials of your local database.
One way is to pass the settings to a configuration script as parameters.

```bash
df_stats cfg_from_opts \
    --db.type=clickhousedb+connect \
    --db.user=user \
    --db.host=localhost \
    --db.port=5432 \
    --db.name=mydb \
    --db.table=mytable \
    --outfile=./superset_dashboard.zip
```

**NB: At this moment, the two possible values for the db.type parameter are: `clickhousedb+connect` and `postgresql`.**

An alternative way is to pass the settings in a YAML file. 


Assuming that you have a file `config.yaml` that contains the following entries, 

```yaml
db:
  type: clickhousedb+connect
  name: test
  user: user
  host: localhost
  port: 5432
  table: dff_stats
```

you can forward it to the script like this:

```bash
df_stats cfg_from_file config.yaml --outfile=./superset_dashboard.zip
```

The script will update the default YAML configuration files with the settings of your choice. Then, the files will be packed into a zip-archive and saved to the designated file.

### Import the Dashboard Config

#### Import through GUI

The configuration archive can be imported via Superset GUI.

Log in to Superset, open the `Dashboards` tab and press the **import** button on the right of the screen. You will be prompted for the database password. If all of the database credentials match, the dashboard will appear in the dashboard list.

#### Import through API

The add-on includes a script that allows for easy interaction with Superset API.

As long as you have created the zip-packed configuration, you can import it using the following command. It requires that your Superset instance should run on localhost on port 8088 (standard for Superset).

```bash
df_stats import_dashboard \\
    --username=admin \\
    --password=admin \\
    --infile=./superset_dashboard.zip \\
    --db.password=password
```

Parameters `username` and `password` should be set to your Superset username and password.

## Preset support

You can also import the dashboard to [Preset](https://preset.io/), a cloud-hosted Superset instance. This is a perfect option, if your database is also hosted remotely. Use the GUI to import the zip-archive, like we did with Superset.

The service needs to be able to access and fetch your data, so do not forget to [whitelist Preset IPs](https://docs.preset.io/docs/connecting-your-data) on the database host machine, before you import the dashboard. 
