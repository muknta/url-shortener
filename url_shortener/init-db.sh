#!/bin/bash
set -e

# Create additional roles and databases
psql -U heknt <<-EOSQL
    CREATE USER heknt WITH PASSWORD '1234';
    CREATE DATABASE django_url_shortener;
    GRANT ALL PRIVILEGES ON DATABASE django_url_shortener TO heknt;
EOSQL
