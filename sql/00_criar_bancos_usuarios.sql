CREATE ROLE grupo5_owner LOGIN PASSWORD 'grupo5_owner_123';

CREATE ROLE grupo5_app LOGIN PASSWORD 'grupo5_app_123';

CREATE ROLE grupo7_integracao LOGIN PASSWORD 'grupo7_leitura_123';

CREATE DATABASE grupo5_db OWNER grupo5_owner ENCODING 'UTF8' TEMPLATE template0;

REVOKE ALL ON DATABASE grupo5_db FROM PUBLIC;
GRANT CONNECT ON DATABASE grupo5_db TO grupo5_app;
GRANT CONNECT ON DATABASE grupo5_db TO grupo7_integracao;
