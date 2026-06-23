FROM nginx:alpine-slim

RUN apk add --update npm git
RUN npm install -g npm@11.13.0
COPY ./default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
WORKDIR /app/frontend

CMD ["nginx", "-g", "daemon off;"]
