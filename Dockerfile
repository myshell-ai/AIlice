FROM ubuntu:latest

RUN apt-get update && apt-get install -y python3 python3-pip

WORKDIR /scripter

COPY __init__.py /scripter/__init__.py
COPY common/__init__.py /scripter/common/__init__.py
COPY common/lightRPC.py /scripter/common/lightRPC.py
COPY common/resourcePool.py /scripter/common/resourcePool.py
COPY modules/AScripter.py /scripter/AScripter.py

RUN pip3 install pyzmq

EXPOSE 2005

CMD ["python3", "/scripter/AScripter.py", "--incontainer"]
