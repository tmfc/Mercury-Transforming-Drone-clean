#ifndef MAVLINK_RX_H
#define MAVLINK_RX_H

#include <stdbool.h>
#include <stdint.h>

enum MavlinkMessage {
    MAV_NONE = 0,
    MAV_SYS_STATUS = 1,
    MAV_RC_CHANNELS = 65,
};

typedef struct {
    uint16_t offset;
    uint16_t crc;
    uint8_t header_len;
    uint8_t header[9];
    uint8_t payload[42];  /* Only the prefix used by these two messages. */
    enum MavlinkMessage type;
} MavlinkRx;

static inline uint16_t mavlink_crc_byte(uint16_t crc, uint8_t byte) {
    uint8_t tmp = byte ^ (uint8_t)crc;
    tmp ^= (uint8_t)(tmp << 4);
    return (uint16_t)((crc >> 8) ^ (tmp << 8) ^ (tmp << 3) ^ (tmp >> 4));
}

static inline void mavlink_rx_reset(MavlinkRx *rx) {
    rx->header_len = 0;
}

/* PX4's default IDs: vehicle 1, autopilot component 1. This is a dedicated UART. */
static inline enum MavlinkMessage mavlink_rx_feed(MavlinkRx *rx, uint8_t byte) {
    if (!rx->header_len) {
        if (byte == 0xfe || byte == 0xfd) {
            rx->header_len = byte == 0xfe ? 5 : 9;
            rx->offset = 0;
            rx->crc = 0xffff;
        }
        return MAV_NONE;
    }

    const unsigned at = rx->offset++;
    const bool v2 = rx->header_len == 9;
    if (at < rx->header_len) {
        rx->header[at] = byte;
        rx->crc = mavlink_crc_byte(rx->crc, byte);
        if (at + 1 == rx->header_len) {
            const uint8_t id = rx->header[v2 ? 6 : 4];
            const bool expected_source = rx->header[v2 ? 4 : 2] == 1 &&
                                         rx->header[v2 ? 5 : 3] == 1;
            const bool supported = !v2 || !(rx->header[1] | rx->header[7] | rx->header[8]);
            rx->type = expected_source && supported && (id == MAV_SYS_STATUS || id == MAV_RC_CHANNELS)
                ? (enum MavlinkMessage)id : MAV_NONE;
        }
        return MAV_NONE;
    }

    const unsigned slot = at - rx->header_len;
    const unsigned len = rx->header[0];
    if (slot < len) {
        if (rx->type != MAV_NONE) {
            if (slot < sizeof(rx->payload)) rx->payload[slot] = byte;
            rx->crc = mavlink_crc_byte(rx->crc, byte);
        }
    } else if (slot == len && rx->type != MAV_NONE) {
        /* CRC extras from MAVLink common.xml: SYS_STATUS=124, RC_CHANNELS=118. */
        rx->crc = mavlink_crc_byte(rx->crc, rx->type == MAV_SYS_STATUS ? 124 : 118);
        if ((uint8_t)rx->crc != byte) rx->type = MAV_NONE;
    } else if (slot == len + 1u + (v2 && (rx->header[1] & 1u) ? 13u : 0u)) {
        /* Signed frames are not accepted, but their signature is still consumed. */
        mavlink_rx_reset(rx);
        if (byte == (rx->crc >> 8)) return rx->type;
    }
    return MAV_NONE;
}

#endif
