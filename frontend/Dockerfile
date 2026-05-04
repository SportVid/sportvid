FROM node:24.15.0-bookworm-slim

WORKDIR /app/frontend

COPY package*.json ./

RUN npm install
# RUN npm install -g npm@11.3.0
# RUN apk add --update npm git

COPY . .

RUN npm run build