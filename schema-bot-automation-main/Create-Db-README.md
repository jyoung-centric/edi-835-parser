# Creating Initial bot_automation Database, Users, and Schema

## Creating bot and botuser Users, and Database Instance

To create bot user and database for the existing local or Aurora PostgreSQL instance:

- As user `postgres` or another superuser, execute the following commands to create `bot` user:
    ```sql
    CREATE ROLE bot WITH
        LOGIN
        NOSUPERUSER
        CREATEDB
        CREATEROLE
        INHERIT
        PASSWORD '<PASSWORD>';
    ```
- As user `postgres` or another superuser, execute the following commands to create `botuser` user:
    ```sql
    CREATE USER botuser WITH LOGIN PASSWORD '<PASSWORD>';
    ```
- As user `bot` (connecting to postgres database), execute the following commands to create `bot_automation` database:
    ```sql
    CREATE DATABASE bot_automation
        WITH 
        OWNER = bot
        ENCODING = 'UTF8'
        CONNECTION LIMIT = -1;
    ```
- As user `postgres` or another superuser, connecting to `bot_automation` database and execute the following commands to create all the necessary database extensions:
    ```sql
    CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA pg_catalog;
    CREATE EXTENSION IF NOT EXISTS btree_gin WITH SCHEMA pg_catalog;
    CREATE EXTENSION IF NOT EXISTS fuzzystrmatch WITH SCHEMA pg_catalog;
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA pg_catalog;
    CREATE EXTENSION IF NOT EXISTS "citext" WITH SCHEMA pg_catalog;
    ```
- As user `bot` user connecting to `bot_automation` database, execute the following commands to create `bot` schema for `bot_automation` database:
    ```sql
    CREATE SCHEMA IF NOT EXISTS bot;
    ```


 ## Grant Permissions to botuser User
 - As user `postgres` or another superuser, connecting to `bot_automation` database and execute the following commands:
     ```sql
        ALTER ROLE bot SET search_path TO bot;
        ALTER ROLE botuser SET search_path TO bot;
   
        GRANT USAGE ON SCHEMA bot TO botuser;
        
        -- Permissions for current objects
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA bot TO botuser;
        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA bot TO botuser;
        GRANT USAGE ON ALL SEQUENCES IN SCHEMA bot TO botuser;
        
        -- Default permissions for future objects created by bot
        ALTER DEFAULT PRIVILEGES FOR ROLE bot IN SCHEMA bot GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO botuser;
        ALTER DEFAULT PRIVILEGES FOR ROLE bot IN SCHEMA bot GRANT USAGE ON SEQUENCES TO botuser;
        ALTER DEFAULT PRIVILEGES FOR ROLE bot IN SCHEMA bot GRANT EXECUTE ON FUNCTIONS TO botuser;
     ```


     
