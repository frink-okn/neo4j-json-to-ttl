FROM python:3.11.11-slim-bullseye
LABEL authors="kebedey"


RUN mkdir /code/
WORKDIR /code
COPY ./requirements.txt /code/
RUN pip install -r requirements.txt
RUN rm requirements.txt

# copy code and scripts


COPY ./src/main.py main.py
