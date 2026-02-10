DROP TABLE IF EXISTS bot.test_table;

CREATE TABLE bot.test_table
(
    id                 BIGSERIAL                      NOT NULL
        CONSTRAINT pk_test_table PRIMARY KEY,
    created_date_time  TIMESTAMP(6) WITHOUT TIME ZONE NOT NULL DEFAULT timezone('UTC', CLOCK_TIMESTAMP()),
    last_run_date_time TIMESTAMP(6) WITHOUT TIME ZONE NOT NULL,
    script_version     VARCHAR(20)                    NOT NULL,
    script_checksum    VARCHAR(40)                    NOT NULL,
    script_name        VARCHAR(500)                   NOT NULL,
    success            BOOLEAN
);