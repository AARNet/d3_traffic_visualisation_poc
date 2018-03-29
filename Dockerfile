FROM nginx:alpine
# COPY nginx.server.whitelist /usr/share/nginx/server.whitelist
COPY index.html /usr/share/nginx/html
COPY institutions.csv /usr/share/nginx/html
COPY matrix.json /usr/share/nginx/html
