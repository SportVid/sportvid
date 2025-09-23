FROM nginx:1.28.0-alpine

# remove default website
RUN rm -rf /usr/share/nginx/html/*

# copy default NGINX config file
COPY ./nginx.conf /etc/nginx/conf.d/default.conf

# copy static web files from the frontend
# COPY --from=frontend_prod /app/frontend/dist/ /usr/share/nginx/html/prod
# COPY src/ /usr/share/nginx/html/dev

EXPOSE 80
EXPOSE 443

CMD ["nginx", "-g", "daemon off;"]
