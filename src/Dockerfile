FROM python:3-slim-buster

EXPOSE 8000

RUN adduser app
WORKDIR /home/app
USER app

COPY requirements.txt .

RUN pip install --no-cache-dir --no-warn-script-location -r requirements.txt

COPY *.py .
COPY ./persists_dir ./persists_dir

# switch to root to ensure we can write temporary files during sed
USER root
# for CLRF compatibility
RUN find . -type f -name "*.py" -exec sed -i 's/\r$//' {} +

USER app

CMD ["tail", "-f", "/dev/null"]
