#!/bin/bash

# To get stock Init for MariaDB
wget https://raw.githubusercontent.com/xwiki/xwiki-docker/master/14/mariadb-tomcat/mariadb/init.sql
# To get stock docker-compose for MariaDB
wget https://raw.githubusercontent.com/xwiki/xwiki-docker/master/14/mariadb-tomcat/docker-compose.yml
# To Get stock env file
wget https://raw.githubusercontent.com/xwiki/xwiki-docker/master/14/mariadb-tomcat/.env

# Substituite the XWiki version in .env
var="XWIKI_VERSION=13.10.5"
sed -i "2s/.*/$var/" .env

#...
