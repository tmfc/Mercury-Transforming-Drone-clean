#include "rc_drive.h"
#include "mavlink_rx.h"

#define REG(base, offset) (*(volatile uint32_t *)((base) + (offset)))
#define BIT(n) (UINT32_C(1) << (n))
#define RCC   UINT32_C(0x40023800)
#define GPIOA UINT32_C(0x40020000)
#define GPIOB UINT32_C(0x40020400)
#define GPIOC UINT32_C(0x40020800)
#define TIM2  UINT32_C(0x40000000)
#define TIM5  UINT32_C(0x40000c00)
#define UART4 UINT32_C(0x40004c00)

enum {
    GPIO_MODER = 0x00, GPIO_PUPDR = 0x0c, GPIO_BSRR = 0x18,
    GPIO_AFRL = 0x20, GPIO_AFRH = 0x24,
    TIM_CR1 = 0x00, TIM_EGR = 0x14, TIM_CCMR1 = 0x18, TIM_CCMR2 = 0x1c, TIM_CCER = 0x20,
    TIM_CNT = 0x24, TIM_PSC = 0x28, TIM_ARR = 0x2c, TIM_CCR1 = 0x34, TIM_CCR3 = 0x3c,
    UART_SR = 0x00, UART_DR = 0x04, UART_BRR = 0x08, UART_CR1 = 0x0c,
    UART_RXNE = BIT(5), UART_ERROR = 0x0f,
    UART_RX_PIN = 1,
    MOTOR1_PWM = 10, MOTOR1_BRK = 11, MOTOR1_DIR = 12, /* PB10/PB11/PB12 */
    MOTOR2_PWM = 15, MOTOR2_BRK = 0, MOTOR2_DIR = 1,   /* PA15/PC0/PC1 */
    UART_BAUD = 115200, UART_FRAME_GAP_US = 5000,
    PWM_COUNTS = 16000,
    PWM_SETTLE_US = 3000,
    DIRECTION_SETTLE_US = 100000,
    REVERSAL_BRAKE_US = 1000000, /* Unloaded bench interval; no shaft-speed feedback. */
};

typedef struct {
    uint32_t gpio, brk, dir;
    unsigned ccr;
} MotorPins;

/* Order matches the RC calibration table: CH6, then CH12. */
static const MotorPins motor_pins[RC_DRIVE_COUNT] = {
    {GPIOB, BIT(MOTOR1_BRK), BIT(MOTOR1_DIR), TIM_CCR3},
    {GPIOC, BIT(MOTOR2_BRK), BIT(MOTOR2_DIR), TIM_CCR1},
};

typedef struct {
    uint32_t pwm_started_us, direction_at_us, braked_at_us;
    int8_t applied;
    enum { STOPPED, PWM_SETTLING, RUNNING } phase;
    bool reverse, direction_settling, reversal_wait;
} Motor;

static void gpio_mode(uint32_t port, unsigned pin, unsigned mode) {
    const unsigned shift = 2u * pin;
    REG(port, GPIO_MODER) = (REG(port, GPIO_MODER) & ~(3u << shift)) | (mode << shift);
}

static void motor_stop(const MotorPins *pins) {
    REG(pins->gpio, GPIO_BSRR) = pins->brk << 16;
    REG(TIM2, pins->ccr) = PWM_COUNTS; /* Idle high at the next PWM cycle. */
}

static void motor_pwm_set(const MotorPins *pins, Motor *motor, int demand) {
    const unsigned magnitude = (unsigned)(demand < 0 ? -demand : demand);
    /* PWM is active-low; only magnitude changes the compare value. */
    REG(TIM2, pins->ccr) = (100u - magnitude) * (PWM_COUNTS / 100u);
    motor->applied = (int8_t)demand;
}

static void motor_step(const MotorPins *pins, Motor *motor, int demand, uint32_t now_us) {
    if (motor->reversal_wait && now_us - motor->braked_at_us >= REVERSAL_BRAKE_US) motor->reversal_wait = false;
    if (motor->direction_settling && now_us - motor->direction_at_us >= DIRECTION_SETTLE_US) motor->direction_settling = false;

    const bool reverse = demand < 0;
    if (motor->phase != STOPPED && (demand == 0 || reverse != motor->reverse)) {
        motor_stop(pins);
        if (motor->phase == RUNNING) {
            motor->braked_at_us = REG(TIM5, TIM_CNT);
            motor->reversal_wait = true;
        }
        motor->phase = STOPPED;
    }
    if (demand == 0) return;

    if (motor->phase == STOPPED) {
        if (reverse != motor->reverse && motor->reversal_wait) return;
        if (reverse != motor->reverse) {
            motor->reverse = reverse;
            REG(pins->gpio, GPIO_BSRR) = reverse ? pins->dir : pins->dir << 16;
            motor->direction_at_us = REG(TIM5, TIM_CNT);
            motor->direction_settling = true;
        }
        motor_pwm_set(pins, motor, demand);
        motor->pwm_started_us = REG(TIM5, TIM_CNT);
        motor->phase = PWM_SETTLING;
    } else {
        if (demand != motor->applied) motor_pwm_set(pins, motor, demand);
        if (motor->phase == PWM_SETTLING && !motor->direction_settling &&
            now_us - motor->pwm_started_us >= PWM_SETTLE_US) {
            REG(pins->gpio, GPIO_BSRR) = pins->brk;
            motor->phase = RUNNING;
        }
    }
}

static void init_hardware(void) {
    /* Hardware reset selects 16 MHz HSI and undivided AHB/APB1. */
    REG(RCC, 0x30) |= BIT(0) | BIT(1) | BIT(2); /* GPIOA, GPIOB, GPIOC */
    (void)REG(RCC, 0x30);
    REG(GPIOB, GPIO_BSRR) = (BIT(MOTOR1_BRK) | BIT(MOTOR1_DIR)) << 16;
    REG(GPIOC, GPIO_BSRR) = (BIT(MOTOR2_BRK) | BIT(MOTOR2_DIR)) << 16;
    gpio_mode(GPIOB, MOTOR1_BRK, 1);
    gpio_mode(GPIOB, MOTOR1_DIR, 1);
    gpio_mode(GPIOC, MOTOR2_BRK, 1);
    gpio_mode(GPIOC, MOTOR2_DIR, 1);

    REG(RCC, 0x40) |= BIT(0) | BIT(3) | BIT(19); /* TIM2, TIM5, UART4 */
    (void)REG(RCC, 0x40);
    REG(TIM2, TIM_ARR) = PWM_COUNTS - 1;
    REG(TIM2, TIM_CCMR1) = (6u << 4) | BIT(3); /* PWM mode 1 with compare preload. */
    REG(TIM2, TIM_CCMR2) = (6u << 4) | BIT(3);
    REG(TIM2, TIM_CCR1) = PWM_COUNTS;
    REG(TIM2, TIM_CCR3) = PWM_COUNTS;
    REG(TIM2, TIM_EGR) = BIT(0);
    REG(TIM2, TIM_CCER) = BIT(0) | BIT(8);
    REG(TIM2, TIM_CR1) = BIT(0); /* Shared free-running PWM; neither motor resets the timer. */
    REG(GPIOB, GPIO_AFRH) |= 1u << (4u * (MOTOR1_PWM - 8)); /* PB10 AF1, TIM2_CH3. */
    REG(GPIOA, GPIO_AFRH) |= 1u << (4u * (MOTOR2_PWM - 8)); /* PA15 AF1, TIM2_CH1. */
    gpio_mode(GPIOB, MOTOR1_PWM, 2);
    gpio_mode(GPIOA, MOTOR2_PWM, 2);

    REG(GPIOA, GPIO_PUPDR) |= 1u << (2u * UART_RX_PIN); /* UART idle is high. */
    REG(GPIOA, GPIO_AFRL) |= 8u << (4u * UART_RX_PIN); /* PA1 AF8: UART4_RX. */
    gpio_mode(GPIOA, UART_RX_PIN, 2);
    REG(UART4, UART_BRR) = (16000000u + UART_BAUD / 2u) / UART_BAUD;
    REG(UART4, UART_CR1) = BIT(13) | BIT(2); /* UART enabled, receive only, 8N1. */
    REG(TIM5, TIM_PSC) = 16 - 1; /* Free-running 32-bit timer, 1 us per count. */
    REG(TIM5, TIM_ARR) = UINT32_MAX;
    REG(TIM5, TIM_EGR) = BIT(0);
    REG(TIM5, TIM_CR1) = BIT(0);
}

_Noreturn static void fault(void) {
    for (unsigned i = 0; i < RC_DRIVE_COUNT; ++i) motor_stop(&motor_pins[i]);
    for (;;) {}
}

_Noreturn void reset(void) {
    init_hardware();
    RcDrive rc;
    rc_drive_lost(&rc);
    MavlinkRx rx;
    mavlink_rx_reset(&rx);
    uint32_t last_byte_us = 0;
    Motor motors[RC_DRIVE_COUNT];
    for (unsigned i = 0; i < RC_DRIVE_COUNT; ++i) {
        motors[i].phase = STOPPED;
        motors[i].reverse = false;
        motors[i].direction_settling = false;
        motors[i].reversal_wait = false;
    }
    for (;;) {
        const uint32_t now_us = REG(TIM5, TIM_CNT);
        rc_drive_expire(&rc, now_us);
        const uint32_t status = REG(UART4, UART_SR);
        if (status & (UART_RXNE | UART_ERROR)) {
            const uint8_t byte = (uint8_t)REG(UART4, UART_DR); /* SR then DR clears errors. */
            if (status & UART_ERROR) {
                mavlink_rx_reset(&rx);
                rc_drive_lost(&rc);
            } else {
                if (now_us - last_byte_us >= UART_FRAME_GAP_US) mavlink_rx_reset(&rx);
                last_byte_us = now_us;
                switch (mavlink_rx_feed(&rx, byte)) {
                case MAV_SYS_STATUS:
                    rc_drive_health(&rc, rx.payload, rx.header[0], now_us);
                    break;
                case MAV_RC_CHANNELS:
                    rc_drive_sample(&rc, rx.payload, rx.header[0], now_us);
                    break;
                case MAV_NONE:
                    break;
                }
            }
        }
        for (unsigned i = 0; i < RC_DRIVE_COUNT; ++i) {
            motor_step(&motor_pins[i], &motors[i], rc.axis[i].demand, now_us);
        }
    }
}

__attribute__((section(".vectors"), used))
static const uintptr_t vectors[16] = {
    0x20020000u, (uintptr_t)reset,
    [2 ... 15] = (uintptr_t)fault,
};
