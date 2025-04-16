FROM python:3.12-slim

WORKDIR /usr/local/mcp

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "mcp_monitor_send_hash.py"]
