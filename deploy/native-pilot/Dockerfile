# Build recipe only: not built/deployed in cloud. Review/pin base image digest before live use.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt constraints-python312.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt -c constraints-python312.txt && python -m pip check
COPY . .
USER 10001:10001
# No default credential, public host, port publication or permissive launch flag.
ENTRYPOINT ["python", "-m", "muse_audit.native_connector.server"]
