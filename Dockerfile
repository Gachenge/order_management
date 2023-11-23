FROM python:3.10-bullseye
COPY . /app
WORKDIR /app
CMD [ "python", "app.py"  ]
