FROM python:3.11-alpine

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

ENV POSTGRES_USER = postgres
ENV POSTGRES_PASSWORD = postgres
ENV POSTGRES_HOST = 127.0.0.1
ENV POSTGRES_PORT = postgres
ENV POSTGRES_DB = postgres
ENV OLDER = 10
ENV KEYCLOAK_URL = https://62.72.21.79:8442/auth/realms/react-keycloak/protocol/openid-connect/userinfo

CMD ["python3", "main.py"]
