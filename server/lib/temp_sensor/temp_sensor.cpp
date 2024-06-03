/**
 * @file temp_sensor.cpp
 * @brief  This file contains the implementation of the temperature sensor module.
 * @version 0.1
 * @date 2024-05-25
 *
 *
 */

#include "temp_sensor.h"
#include "bsp.h"

void temp_sensor_init()
{
    ;
}

float temp_sensor_read()
{
    return (temp_sensor_read() - 23) / 1.8;
}
