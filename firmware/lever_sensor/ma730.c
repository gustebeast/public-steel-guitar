/* ma730.c -- see ma730.h for the wiring and the datasheet pages each number comes from. */
#include "ch32v20x.h"
#include "ma730.h"

#define CS_LO() (GPIOB->BCR = GPIO_Pin_5)
#define CS_HI() (GPIOB->BSHR = GPIO_Pin_5)

void ma730_init(void)
{
    GPIO_InitTypeDef g = {0};
    SPI_InitTypeDef s = {0};

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA | RCC_APB2Periph_GPIOB | RCC_APB2Periph_SPI1, ENABLE);

    /* CS high BEFORE the pin is an output, so it never glitches low and starts a frame */
    CS_HI();
    g.GPIO_Pin = GPIO_Pin_5;
    g.GPIO_Mode = GPIO_Mode_Out_PP;
    g.GPIO_Speed = GPIO_Speed_10MHz;
    GPIO_Init(GPIOB, &g);

    g.GPIO_Pin = GPIO_Pin_5 | GPIO_Pin_7;           /* SCK, MOSI */
    g.GPIO_Mode = GPIO_Mode_AF_PP;
    GPIO_Init(GPIOA, &g);
    g.GPIO_Pin = GPIO_Pin_6;                        /* MISO: the sensor drives it, or its pull-down holds it */
    g.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOA, &g);

    /* Mode 3 (CPOL 1, CPHA 1): the part takes 0 or 3 and works out which itself (p.11). 16-bit
     * frames, MSB first. /8 at a 48 MHz PCLK2 is 6 MHz, a quarter of the part's 25 MHz, over 12 mm
     * of track: margin, not speed, is what a lever read needs. */
    s.SPI_Direction = SPI_Direction_2Lines_FullDuplex;
    s.SPI_Mode = SPI_Mode_Master;
    s.SPI_DataSize = SPI_DataSize_16b;
    s.SPI_CPOL = SPI_CPOL_High;
    s.SPI_CPHA = SPI_CPHA_2Edge;
    s.SPI_NSS = SPI_NSS_Soft;
    s.SPI_BaudRatePrescaler = SPI_BaudRatePrescaler_8;
    s.SPI_FirstBit = SPI_FirstBit_MSB;
    s.SPI_CRCPolynomial = 7;
    SPI_Init(SPI1, &s);
    SPI_Cmd(SPI1, ENABLE);
}

/* One 16-bit frame. The CS -> first edge minimum (80 ns, p.12) is four cycles at 48 MHz and the
 * register writes between CS_LO and the clock starting take longer than that. */
static uint16_t frame(uint16_t out)
{
    uint16_t in;

    CS_LO();
    while (!(SPI1->STATR & SPI_I2S_FLAG_TXE))
        ;
    SPI1->DATAR = out;
    while (!(SPI1->STATR & SPI_I2S_FLAG_RXNE))
        ;
    in = SPI1->DATAR;
    while (SPI1->STATR & SPI_I2S_FLAG_BSY)
        ;
    CS_HI();
    return in;
}

uint16_t ma730_angle(void)
{
    /* 14 bits used, two zeros padded below (p.13). The 150 ns the part wants between two reads
     * is seven cycles at 48 MHz: a return and a call take longer than that. */
    return frame(0) >> 2;
}

uint8_t ma730_read(uint8_t reg)
{
    uint8_t v;

    Delay_Us(1);                                    /* 750 ns before (p.12) */
    frame(0x4000 | ((uint16_t)(reg & 0x1F) << 8));  /* 010 aaaaa 00000000 */
    Delay_Us(1);
    v = frame(0) >> 8;                              /* the value, high byte */
    Delay_Us(1);                                    /* ...and after */
    return v;
}

uint8_t ma730_field(void)
{
    return ma730_read(MA730_REG_FLAGS) & (MA730_MGH | MA730_MGL);
}

static uint8_t write(uint8_t reg, uint8_t v)
{
    Delay_Us(1);
    frame(0x8000 | ((uint16_t)(reg & 0x1F) << 8) | v);   /* 100 aaaaa vvvvvvvv */
    Delay_Ms(20);                                   /* non-volatile memory update (p.12) */
    v = frame(0) >> 8;                              /* what the part now holds */
    Delay_Us(1);
    return v;
}

uint8_t ma730_thresholds(uint8_t mglt, uint8_t mght)
{
    uint8_t now = ma730_read(MA730_REG_THRESH);
    uint8_t want = (uint8_t)(((mglt & 7) << 5) | ((mght & 7) << 2) | (now & 0x03));

    return now == want ? now : write(MA730_REG_THRESH, want);
}
