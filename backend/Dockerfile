FROM python:3.12-slim

# node (to run student JS) + solc (to compile Solidity)
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates gnupg rustc \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && curl -fsSL -o /usr/local/bin/solc \
       https://github.com/ethereum/solidity/releases/download/v0.8.26/solc-static-linux \
    && chmod +x /usr/local/bin/solc \
    && apt-get purge -y gnupg && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY content ./content

ENV DATA_DIR=/srv/data WORKSPACES_DIR=/srv/workspaces
VOLUME ["/srv/data", "/srv/workspaces"]

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
