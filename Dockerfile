FROM --platform=linux/amd64 python:3.8 as build
RUN mkdir /app
WORKDIR /app
COPY ./src/requirements.txt .
RUN pip install --upgrade pip
RUN pip3 install -r /app/requirements.txt

FROM build as runtime
COPY ./src/app.py .
ENTRYPOINT ["python3", "/app/app.py"]
