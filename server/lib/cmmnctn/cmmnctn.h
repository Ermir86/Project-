#ifndef CMMNCTN_H
#define CMMNCTN_H

#include <stdint.h>
#include <stddef.h>

bool cmmnctn_int(const char *com_param);

bool cmmnctn_write(const uint8_t *data, size_t dlen);

size_t cmmnctn_read(uint8_t *buf, size_t blen);

#endif