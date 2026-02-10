# Schema Bot Automation

## Overview

This project contains the PostgreSQL database schema for bot automation and data exchange. It is managed and deployed using [Flyway](https://www.red-gate.com/products/flyway/) inside a Docker container through Jenkins.

## Deployment Process

The schema deployment is automated via Jenkins, using Docker and Flyway. During deployment, `docker compose up` is executed, which runs the following Flyway commands:

- **repair**: Fixes metadata issues in the schema history table
- **migrate**: Applies new migration scripts in order
- **validate**: Checks if the applied migrations match the expected ones

### Manual Deployment Commands

You can run migrations manually using Docker (for DEV bot_automation database):

```sh
# Export Env Vars
export DB_URL=postgresql://botdb.prxdev.com:5432/bot_automation?currentSchema=bot
export DB_USER=bot
export DB_PASSWORD=<PASSWORD>

# Using Docker Compose
docker compose run --rm flyway migrate
```

## Flyway Migration Scripts

### Migration File Naming Convention

Migration scripts must be placed in the `migrations` folder and follow this naming convention:

`V1.0.0__description.sql`

- The **V** must be uppercase
- Version number follows semantic versioning (`major.minor.patch`)
- Double underscore (`__`) separates the version from the description
- Description provides context for the migration
- You CANNOT have the same version with different description, i.e. V1.1.0__script1.sql and V1.1.0__script2.sql

#### Example Migration Filenames

```
V1.0.0__initial_schema.sql
V1.1.0__add_new_table.sql
V2.0.0__modify_column_type.sql
```

### Archive Folder

Older scripts can be moved to the `archive` folder for historical reference. These archived scripts are not used by Flyway.

## Flyway Schema History Table

Flyway automatically creates a `flyway_schema_history` table to track applied migrations. This table is generated when Flyway is first initialized with a **baseline**.

### Table Metadata

The table includes the following information:
- **Version**: Migration version number
- **Description**: Description from the filename
- **Installed By**: User who ran the migration
- **Execution Time**: Duration of the migration

Each new migration adds a record to this table, ensuring migrations are applied in the correct order and not repeated unnecessarily.
