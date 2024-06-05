#include "cmmnctn.h"
#include <Arduino.h>

bool cmmnctn_int(const char *com_param)
{
    String param{com_param};

    Serial.begin(param.toInt());

    return Serial;
}

bool cmmnctn_write(const uint8_t *data, size_t dlen)
{
    return (dlen == Serial.write(data, dlen));
}

size_t cmmnctn_read(uint8_t *buf, size_t blen)
{
    while (0 == Serial.available())
    {
        ;
    }

    return Serial.readBytes(buf, blen);
}