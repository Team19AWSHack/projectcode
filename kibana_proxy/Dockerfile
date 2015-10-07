FROM nginx:latest
MAINTAINER Adam Simpson <simpsonadam@gmail.com>

RUN apt-get update && apt-get install curl -y
COPY ./nginx.conf /etc/nginx/

EXPOSE 8088
