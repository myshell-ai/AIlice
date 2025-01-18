FROM ubuntu:latest

RUN apt-get update && apt-get install -y python3 python3-pip python3-venv git cmake ninja-build
RUN apt-get install -y wget \
    && wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/myshell-ai/AIlice.git

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
RUN /opt/venv/bin/pip install --upgrade pip \
    && cd AIlice && /opt/venv/bin/pip install -e .

EXPOSE 5000
EXPOSE 59000-59200

ENTRYPOINT ["/opt/venv/bin/ailice"]
CMD []
