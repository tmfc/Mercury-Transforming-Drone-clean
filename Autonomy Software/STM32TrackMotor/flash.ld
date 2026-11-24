ENTRY(reset)
MEMORY { FLASH (rx) : ORIGIN = 0x08000000, LENGTH = 16K }
SECTIONS {
    .text : {
        KEEP(*(.vectors))
        *(.text .text.*)
        *(.rodata .rodata.*)
        . = ALIGN(4);
    } > FLASH
    .data : { *(.data .data.*) } > FLASH
    .bss (NOLOAD) : { *(.bss .bss.* COMMON) } > FLASH
    /DISCARD/ : { *(.ARM.exidx* .ARM.extab*) }
}
ASSERT(SIZEOF(.data) == 0 && SIZEOF(.bss) == 0, "startup does not initialize RAM sections")
