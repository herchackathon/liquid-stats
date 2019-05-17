FROM python:2-alpine

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

VOLUME /usr/src/app/liquid.db

CMD [ "python", "-u", "./parse-chain.py" ]
