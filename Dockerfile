FROM ubuntu:latest

RUN apt-get update && apt-get install -y python3 python3-pip

WORKDIR /scripter

COPY ailice/__init__.py /scripter/ailice/__init__.py
COPY ailice/common/__init__.py /scripter/ailice/common/__init__.py
COPY ailice/common/lightRPC.py /scripter/ailice/common/lightRPC.py
COPY ailice/modules/__init__.py /scripter/ailice/modules/__init__.py
COPY ailice/modules/AScripter.py /scripter/ailice/modules/AScripter.py
COPY ailice/modules/AScrollablePage.py /scripter/ailice/modules/AScrollablePage.py

RUN pip3 install pyzmq

EXPOSE 59000-59200


CMD ["python3", "-m", "ailice.modules.AScripter", "--incontainer", "--addr=tcp://0.0.0.0:59000"]
