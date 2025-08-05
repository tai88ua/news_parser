FROM python:3.13-slim

WORKDIR /usr/src/app



RUN apt update -y
RUN apt install pipenv -y
RUN apt install pip -y

# copy requirements
COPY app/requirements.txt ./requirements.txt

# install requirements
RUN pip install --no-cache-dir -r requirements.txt


CMD [ "tail", "-f", "welcome.txt" ]