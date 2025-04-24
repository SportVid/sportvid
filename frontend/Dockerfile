FROM nginx:1.28.0-alpine

RUN apk add --update npm git
RUN npm install -g npm@11.3.0
COPY ./default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
WORKDIR /frontend

CMD ["nginx", "-g", "daemon off;"]
