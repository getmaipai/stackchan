/* Host test for the power readings core (patch SF48). cc -std=gnu99 -Wall -Wextra -Werror -I<dir with the header>. */
#include <stdio.h>
#include "maipai_power_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

int main(void)
{
    /* the ADC: 14 bits in millivolts, the high byte's top two bits ignored */
    CHECK(mpw_adc_mv(0x14, 0x50) == 5200);          /* 0x1450 = 5200 mV: a USB supply */
    CHECK(mpw_adc_mv(0xd4, 0x50) == 5200);          /* the upper two bits are not part of the value */
    CHECK(mpw_adc_mv(0x10, 0x68) == 4200);          /* 0x1068 = 4200 mV: a full battery */
    CHECK(mpw_adc_mv(0, 0) == 0);
    /* status bits */
    CHECK(mpw_vbus_good(0x20) == 1 && mpw_vbus_good(0x00) == 0);
    CHECK(mpw_battery_present(0x08) == 1 && mpw_battery_present(0x20) == 0);
    CHECK(mpw_direction(0x20) == 1 && mpw_direction(0x40) == 2 && mpw_direction(0x00) == 0 && mpw_direction(0x60) == 3);
    CHECK(mpw_charge_state(0x23) == 3 && mpw_charge_state(0x24) == 4 && mpw_charge_state(0x45) == 5);
    /* limits */
    CHECK(mpw_input_limit_ma(0) == 100 && mpw_input_limit_ma(1) == 500 && mpw_input_limit_ma(2) == 900 && mpw_input_limit_ma(3) == 1000);
    CHECK(mpw_input_limit_ma(4) == 1500 && mpw_input_limit_ma(5) == 2000 && mpw_input_limit_ma(6) == -1 && mpw_input_limit_ma(0xfd) == 2000);
    CHECK(mpw_vindpm_mv(0) == 3880 && mpw_vindpm_mv(6) == 4360 && mpw_vindpm_mv(15) == 5080 && mpw_vindpm_mv(0xf6) == 4360);
    /* the sag: the resting reading minus the lowest reading during the move; failed reads are ignored */
    mpw_sag_t s;
    mpw_sag_begin(&s, 50);
    mpw_sag_add(&s, 49);
    mpw_sag_add(&s, -1);
    mpw_sag_add(&s, 44);
    mpw_sag_add(&s, 51);
    CHECK(s.n == 3 && s.lowest == 44 && s.highest == 51 && mpw_sag(&s) == 6);
    mpw_sag_begin(&s, 50);
    CHECK(mpw_sag(&s) == 0);
    /* the verdict */
    CHECK(mpw_supply_verdict(0, 0) == 0 && mpw_supply_verdict(-1, 0) == 0);
    CHECK(mpw_supply_verdict(50, 2) == 1);
    CHECK(mpw_supply_verdict(50, 6) == 2 && mpw_supply_verdict(44, 1) == 2);
    CHECK(mpw_supply_verdict(50, 11) == 3 && mpw_supply_verdict(39, 0) == 3);
    if (failures) return 1;
    printf("power core ok\n");
    return 0;
}
