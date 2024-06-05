#include "cmmnctn.h"
#include <Arduino.h>

enum
{
    STATUS_OKAY,
    STATUS_ERROR
};

enum
{
    SESSION_CLOSE,
    SESSION_GET_TEMP,
    SESSION_TOGGLE_LED,

    SESSION_OKAY,
    SESSION_ERROR,
    SESSION_ESTABLISH
};

static uint64_t session_id = 0;

void setup()
{
    pinMode(GPIO_NUM_32, OUTPUT);

    cmmnctn_int("115200");
}

void loop()
{
    uint8_t buffer[16] = {0};
    size_t length = cmmnctn_read(buffer, sizeof(buffer));

    if (length == 1)
    {
        switch (buffer[0])
        {
        case SESSION_TOGGLE_LED:
        {
            static uint8_t state = LOW;
            state = (state == LOW) ? HIGH : LOW;
            digitalWrite(GPIO_NUM_32, state);

            buffer[1] = digitalRead(GPIO_NUM_32);
            buffer[0] = (state == buffer[1]) ? STATUS_OKAY : STATUS_ERROR;

            cmmnctn_write(buffer, 2);
        }
        break;

        case SESSION_ESTABLISH:
        {
            buffer[0] = STATUS_OKAY;
            uint8_t *ptr = (uint8_t *)&session_id;
            for (int i = 0; i < sizeof(session_id); i++)
            {
                ptr[i] = random(1, 256);
            }

            memcpy(buffer + 1, &session_id, sizeof(session_id));

            cmmnctn_write(buffer, 1 + sizeof(session_id));
        }
        break;

        case SESSION_CLOSE:
        {
            session_id = 0;
            buffer[0] = STATUS_OKAY;
            cmmnctn_write(buffer, 1);
        }
        break;

        default:
            break;
        }
    }
    else
    {
    }
}