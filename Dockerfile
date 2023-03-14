FROM python:3.11
RUN apt-get update && apt-get install -y
WORKDIR /app/
COPY . /app/
RUN /bin/bash -c 'pip install -r requirements.txt'
CMD ["python3 bot.py"]
