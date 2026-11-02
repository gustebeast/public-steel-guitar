/* What the optical board's loader and application share. See board.h. */
#include <string.h>
#include "board.h"
#include "tusb.h"

/* ---- clocks: everything audio from PLL1, so the carrier and the frame sync are locked -- */
int clock_setup(void)
{
    HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY);
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE1);
    while (!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) { }
    RCC_OscInitTypeDef o = {0};
    o.OscillatorType = RCC_OSCILLATORTYPE_HSE;
    o.HSEState = RCC_HSE_ON;
    o.PLL.PLLState = RCC_PLL_ON;
    o.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    o.PLL.PLLM = 5;                       /* 25 MHz / 5 = 5 MHz */
    o.PLL.PLLN = 157;                     /* x 157.2864 = 786.432 MHz */
    o.PLL.PLLFRACN = 2346;                /* .2864 x 8192 */
    o.PLL.PLLP = 4;                       /* 196.608 MHz: the core, and 4096 x 48 kHz */
    o.PLL.PLLQ = 16;                      /* 49.152 MHz: the SAI kernel, 4 x the bit clock */
    o.PLL.PLLR = 4;
    o.PLL.PLLRGE = RCC_PLL1VCIRANGE_2;
    o.PLL.PLLVCOSEL = RCC_PLL1VCOWIDE;
    if (HAL_RCC_OscConfig(&o) != HAL_OK) return -1;
    RCC_ClkInitTypeDef c = {0};
    c.ClockType = RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_D1PCLK1
                | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2 | RCC_CLOCKTYPE_D3PCLK1;
    c.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    c.SYSCLKDivider = RCC_SYSCLK_DIV1;
    c.AHBCLKDivider = RCC_HCLK_DIV1;      /* 196.608 MHz */
    c.APB3CLKDivider = RCC_APB3_DIV2;
    c.APB1CLKDivider = RCC_APB1_DIV2;     /* 98.304 MHz; its timers run at twice that */
    c.APB2CLKDivider = RCC_APB2_DIV2;
    c.APB4CLKDivider = RCC_APB4_DIV2;
    if (HAL_RCC_ClockConfig(&c, FLASH_LATENCY_2) != HAL_OK) return -1;
    RCC_PeriphCLKInitTypeDef p = {0};
    p.PeriphClockSelection = RCC_PERIPHCLK_SAI1 | RCC_PERIPHCLK_SAI23;
    p.Sai1ClockSelection = RCC_SAI1CLKSOURCE_PLL;       /* PLL1 Q */
    p.Sai23ClockSelection = RCC_SAI23CLKSOURCE_PLL;
    return HAL_RCCEx_PeriphCLKConfig(&p) == HAL_OK ? 0 : -1;
}

void SysTick_Handler(void) { HAL_IncTick(); }

void pin(GPIO_TypeDef *port, uint32_t pins, uint32_t mode, uint32_t speed, uint32_t af)
{
    GPIO_InitTypeDef g = {0};
    g.Pin = pins; g.Mode = mode; g.Pull = GPIO_NOPULL; g.Speed = speed; g.Alternate = af;
    HAL_GPIO_Init(port, &g);
}

void usb_pins(void)
{
    __HAL_RCC_GPIOA_CLK_ENABLE(); __HAL_RCC_GPIOB_CLK_ENABLE(); __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOH_CLK_ENABLE(); __HAL_RCC_GPIOI_CLK_ENABLE();
    /* the PHY: D0 PA3, D1 PB0, D2 PB1, D3 PB10, D4 PB11, D5 PB12, D6 PB13, D7 PB5,
       CK PA5, STP PC0, DIR PI11, NXT PH4 (elec/optical.py ULPI) */
    const uint32_t V = GPIO_SPEED_FREQ_VERY_HIGH;
    /* Start with STP high, as a link coming out of reset should */
    HAL_GPIO_WritePin(GPIOC, GPIO_PIN_0, GPIO_PIN_SET);
    pin(GPIOC, GPIO_PIN_0, GPIO_MODE_OUTPUT_PP, V, 0);
    HAL_Delay(2);
    pin(GPIOA, GPIO_PIN_3 | GPIO_PIN_5, GPIO_MODE_AF_PP, V, GPIO_AF10_OTG2_HS);
    pin(GPIOB, GPIO_PIN_0 | GPIO_PIN_1 | GPIO_PIN_5 | GPIO_PIN_10 | GPIO_PIN_11 | GPIO_PIN_12
               | GPIO_PIN_13, GPIO_MODE_AF_PP, V, GPIO_AF10_OTG2_HS);
    pin(GPIOC, GPIO_PIN_0, GPIO_MODE_AF_PP, V, GPIO_AF10_OTG2_HS);
    pin(GPIOI, GPIO_PIN_11, GPIO_MODE_AF_PP, V, GPIO_AF10_OTG2_HS);
    pin(GPIOH, GPIO_PIN_4, GPIO_MODE_AF_PP, V, GPIO_AF10_OTG2_HS);
}

void _init(void) { }                      /* the C library's start-up calls it; nothing to do */

size_t board_get_unique_id(uint8_t id[], size_t max_len)
{   /* the serial number the descriptors report: the chip's own 96-bit id */
    size_t n = max_len < 12 ? max_len : 12;
    memcpy(id, (const void *)UID_BASE, n);
    return n;
}
uint32_t tusb_time_millis_api(void) { return HAL_GetTick(); }

void OTG_HS_IRQHandler(void) { tud_int_handler(1); }

int usb_setup(void)
{
    __HAL_RCC_USB1_OTG_HS_ULPI_CLK_ENABLE();
    __HAL_RCC_USB1_OTG_HS_CLK_ENABLE();
    HAL_PWREx_EnableUSBVoltageDetector();
    /* With the PHY, its oscillator or one ULPI line dead, the core's reset never completes
       and the USB stack would wait for it for ever: try it here first, with a time limit. */
    USB1_OTG_HS->GUSBCFG &= ~USB_OTG_GUSBCFG_PHYSEL;
    uint32_t t0 = HAL_GetTick();
    while (!(USB1_OTG_HS->GRSTCTL & USB_OTG_GRSTCTL_AHBIDL))
        if (HAL_GetTick() - t0 > 100) return -1;
    USB1_OTG_HS->GRSTCTL |= USB_OTG_GRSTCTL_CSRST;
    while (USB1_OTG_HS->GRSTCTL & USB_OTG_GRSTCTL_CSRST)
        if (HAL_GetTick() - t0 > 200) return -1;
    tud_configure_dwc2_t cfg = CFG_TUD_CONFIGURE_DWC2_DEFAULT;
    cfg.vbus_sensing = false;             /* VBUS is not wired to the core */
    tud_configure(1, TUD_CFGID_DWC2, &cfg);
    tusb_rhport_init_t init = { .role = TUSB_ROLE_DEVICE, .speed = TUSB_SPEED_AUTO };
    if (!tusb_init(1, &init)) return -1;
    /* Leave the bus long enough to be seen gone, so a host that missed the reset starts over */
    tud_disconnect();
    HAL_Delay(200);
    tud_connect();
    return 0;
}

/* The PHY stays powered through a reset and its RESET pin is grounded. Once, an ST-LINK reset
   with USB up left it off the bus until a power cycle; resets from here, and the watchdog's
   with USB up, have all come back (bench, 2026-11-01). Cause not found. */
void reset_to(uint32_t go)
{
    tud_disconnect();
    HAL_Delay(50);
    BOOT_WORDS[0] = go; BOOT_WORDS[1] = ~go;
    NVIC_SystemReset();
}
