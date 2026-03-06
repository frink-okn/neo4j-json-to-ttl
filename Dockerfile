FROM python:3.11.11-slim-bullseye
LABEL authors="kebedey"

RUN apt-get -y update
RUN apt-get -y install wget
RUN apt-get -y install zstd

RUN mkdir /code/
WORKDIR /code
COPY ./requirements.txt /code/
RUN pip install -r requirements.txt
RUN rm requirements.txt

# copy code and scripts
COPY ./src/main.py /code/main.py
COPY startup.sh /code/startup.sh
RUN chmod +x /code/startup.sh

ENTRYPOINT ["/code/startup.sh"]
