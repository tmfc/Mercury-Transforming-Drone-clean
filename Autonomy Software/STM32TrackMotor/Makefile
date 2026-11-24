CC = arm-none-eabi-gcc
OBJCOPY = arm-none-eabi-objcopy
BUILD_DIR ?= build

CFLAGS = -mcpu=cortex-m4 -mthumb -std=gnu11 -Os -ffreestanding -fno-builtin -Wall -Wextra -Werror
LDFLAGS = -nostdlib -Tflash.ld -Wl,--gc-sections

all: $(BUILD_DIR)/track-motor.bin

$(BUILD_DIR)/track-motor.bin: $(BUILD_DIR)/track-motor.elf
	$(OBJCOPY) -O binary $< $@

$(BUILD_DIR)/track-motor.elf: main.c rc_drive.h mavlink_rx.h flash.ld Makefile
	mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) $(LDFLAGS) main.c -o $@

.PHONY: all
