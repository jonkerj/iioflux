FROM debian:bullseye-slim as base
RUN apt-get update && apt-get install -y python3 python3-libiio

# build
FROM base as builder
RUN apt-get update && apt-get install -y build-essential python3-venv libpython3-dev
RUN python3 -m venv --system-site-packages /venv 
ENV PATH="/venv/bin:$PATH"
COPY requirements.txt /venv
RUN pip install -r /venv/requirements.txt

# run
FROM base as runner
WORKDIR /app
COPY --from=builder /venv /venv
COPY submitter.py /app/submitter.py
ENV PATH="/venv/bin/$PATH"
CMD ["python3", "submitter.py"]
