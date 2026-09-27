FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .
ENV DEFI_MANAGER_DATABASE_PATH=/data/defi-manager.sqlite3
VOLUME ["/data"]
CMD ["defi-manager", "selftest"]

