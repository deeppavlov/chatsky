FROM apache/superset:2.0.0rc2
USER root
RUN pip install clickhouse-connect
COPY . /app/dialog_flow_node_stats/
RUN pip install /app/dialog_flow_node_stats/
USER superset