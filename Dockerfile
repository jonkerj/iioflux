FROM debian:buster-slim
RUN apt-get update && apt-get install -y \
	python3 \
	python3-yaml \
	python3-influxdb \
	python3-libiio
COPY submitter.py /submitter.py
ENTRYPOINT ["/usr/bin/python3", "/submitter.py", "--config", "/config/config.yaml", "--secrets", "/secrets"]
