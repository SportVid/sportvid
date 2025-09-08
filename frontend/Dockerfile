FROM nginx:1.28.0-alpine

RUN apk add --update npm git
RUN npm install -g npm@11.3.0

# remove default website
RUN rm -rf /usr/share/nginx/html/*

# copy static web files ???
# COPY src/ /usr/share/nginx/html

# copy default NGINX config file
COPY ./dev.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
EXPOSE 443

WORKDIR /app/frontend

CMD ["nginx", "-g", "daemon off;"]
