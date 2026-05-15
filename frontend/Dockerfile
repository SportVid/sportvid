FROM nginx:1.28.0-alpine-slim

RUN apk add --update npm git
RUN npm install -g npm@11.13.0 \
    && sed -i '/^globalignorefile=/d;/^python=/d' /usr/local/lib/node_modules/npm/npmrc
COPY ./default.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
WORKDIR /app/frontend

CMD ["nginx", "-g", "daemon off;"]
