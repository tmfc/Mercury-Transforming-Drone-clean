#ifndef RC_DRIVE_H
#define RC_DRIVE_H

#include <stdbool.h>
#include <stdint.h>

enum {
    RC_SAMPLE_TIMEOUT_US = 350000,
    RC_HEALTH_TIMEOUT_US = 800000,
    RC_CENTER_SAMPLES = 3,
    RC_DEADBAND_US = 30,
    RC_DRIVE_COUNT = 2,
};

typedef struct {
    uint8_t channel;
    uint16_t min_us, center_us, max_us;
} RcCalibration;

typedef struct {
    int8_t demand;
    uint8_t center_samples;
} RcAxis;

typedef struct {
    uint32_t health_at_us;
    uint32_t sample_at_us;
    uint32_t sample_boot_ms;
    RcAxis axis[RC_DRIVE_COUNT];
    bool healthy;
    bool have_sample;
} RcDrive;

static inline void rc_drive_lost(RcDrive *rc) {
    rc->healthy = false;
    rc->have_sample = false;
    for (unsigned i = 0; i < RC_DRIVE_COUNT; ++i) rc->axis[i] = (RcAxis){0};
}

static inline void rc_drive_health(RcDrive *rc, const uint8_t *data, unsigned len, uint32_t now_us) {
    /* SYS_STATUS: RC receiver bit (16) in present, enabled and healthy masks. */
    if (len < 11 || !(data[2] & data[6] & data[10] & 1u)) {
        rc_drive_lost(rc);
        return;
    }
    rc->health_at_us = now_us;
    rc->healthy = true;
}

static inline int rc_drive_percent(const RcCalibration *cal, unsigned pulse_us) {
    /* Low raw values command forward, as verified for this transmitter's CH6. */
    const unsigned low = cal->center_us - RC_DEADBAND_US;
    const unsigned high = cal->center_us + RC_DEADBAND_US;
    if (pulse_us <= cal->min_us) return 100;
    if (pulse_us >= cal->max_us) return -100;
    if (pulse_us < low) return (int)(((low - pulse_us) * 100u) / (low - cal->min_us));
    if (pulse_us > high) return -(int)(((pulse_us - high) * 100u) / (cal->max_us - high));
    return 0;
}

static inline void rc_axis_sample(RcAxis *axis, const RcCalibration *cal, const uint8_t *data) {
    if (data[40] < cal->channel) {
        *axis = (RcAxis){0};
        return;
    }
    const unsigned offset = 4u + 2u * (cal->channel - 1u);
    const unsigned pulse_us = data[offset] | ((unsigned)data[offset + 1] << 8);
    if (pulse_us < 800 || pulse_us > 2200) {
        *axis = (RcAxis){0};
        return;
    }
    if (pulse_us >= cal->center_us - (unsigned)RC_DEADBAND_US &&
        pulse_us <= cal->center_us + (unsigned)RC_DEADBAND_US) {
        if (axis->center_samples < RC_CENTER_SAMPLES) ++axis->center_samples;
        axis->demand = 0;
    } else if (axis->center_samples == RC_CENTER_SAMPLES) {
        axis->demand = (int8_t)rc_drive_percent(cal, pulse_us);
    } else {
        axis->center_samples = 0;
    }
}

static inline void rc_drive_sample(RcDrive *rc, const uint8_t *data, unsigned len, uint32_t now_us) {
    if (!rc->healthy) return;
    /* Explicit RSSI=0 invalidates the shared link; RSSI=255 is unknown. */
    if (len < 42 || data[41] == 0) {
        rc_drive_lost(rc);
        return;
    }
    const uint32_t boot_ms = data[0] | ((uint32_t)data[1] << 8) |
                             ((uint32_t)data[2] << 16) | ((uint32_t)data[3] << 24);
    if (rc->have_sample) {
        const uint32_t elapsed_ms = boot_ms - rc->sample_boot_ms;
        if (elapsed_ms == 0) return; /* A repeated sample cannot qualify start or renew the timeout. */
        if (elapsed_ms > INT32_MAX) {
            rc_drive_lost(rc); /* Flight controller restarted or timestamps went backwards. */
            return;
        }
    }
    rc->sample_boot_ms = boot_ms;
    rc->sample_at_us = now_us;
    rc->have_sample = true;

    static const RcCalibration calibration[RC_DRIVE_COUNT] = {
        {6, 1065, 1499, 1933},
        {12, 1065, 1499, 1933},
    };
    for (unsigned i = 0; i < RC_DRIVE_COUNT; ++i) {
        rc_axis_sample(&rc->axis[i], &calibration[i], data);
    }
}

static inline void rc_drive_expire(RcDrive *rc, uint32_t now_us) {
    if (rc->healthy && (now_us - rc->health_at_us >= RC_HEALTH_TIMEOUT_US ||
                        (rc->have_sample && now_us - rc->sample_at_us >= RC_SAMPLE_TIMEOUT_US))) {
        rc_drive_lost(rc);
    }
}

#endif
