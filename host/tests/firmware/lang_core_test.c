/* Host test for the screen words as a language pack (patch K11): the words.txt reader, its refusals, a fuzz of damaged files,
 * and the fallback to English. cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers> lang_core_test.c.
 * Run it under -fsanitize=address,undefined to catch an out-of-range read. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "maipai_lang_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static uint32_t rs = 7;
static uint32_t rnd(void)
{
    rs = rs * 1664525u + 1013904223u;
    return rs >> 8;
}

#define PARSE(text, out) mlw_parse((text), strlen(text), (out))

static const char FR[] =
    "lang=fr\norder=dmy\nweekdays=dim,lun,mar,mer,jeu,ven,sam\n"
    "months=jan,fev,mar,avr,mai,jun,jul,aou,sep,oct,nov,dec\nalarm=Alarme\ntimer=Minut.\n";

/* the words the host builds for the other languages (host/maipai_body/language_packs.py), as the unit must read them */
static const char* const HOST_PACKS[5] = {
    "lang=es\norder=dmy\nweekdays=dom,lun,mar,mie,jue,vie,sab\nmonths=ene,feb,mar,abr,may,jun,jul,ago,sep,oct,nov,dic\nalarm=Alarma\ntimer=Tiempo\n",
    FR,
    "lang=de\norder=dmy\nweekdays=So,Mo,Di,Mi,Do,Fr,Sa\nmonths=Jan,Feb,Mar,Apr,Mai,Jun,Jul,Aug,Sep,Okt,Nov,Dez\nalarm=Wecker\ntimer=Timer\n",
    "lang=pt\norder=dmy\nweekdays=dom,seg,ter,qua,qui,sex,sab\nmonths=jan,fev,mar,abr,mai,jun,jul,ago,set,out,nov,dez\nalarm=Alarme\ntimer=Tempo\n",
    "lang=it\norder=dmy\nweekdays=dom,lun,mar,mer,gio,ven,sab\nmonths=gen,feb,mar,apr,mag,giu,lug,ago,set,ott,nov,dic\nalarm=Sveglia\ntimer=Timer\n",
};

static int sane(const mlw_t* w)
{
    if (strlen(w->code) != 2) return 0;
    for (int i = 0; i < 7; i++) { if (strlen(w->wd[i]) == 0 || strlen(w->wd[i]) >= MLW_WORD) return 0; }
    for (int i = 0; i < 12; i++) { if (strlen(w->mon[i]) == 0 || strlen(w->mon[i]) >= MLW_WORD) return 0; }
    if (strlen(w->alarm) == 0 || strlen(w->timer) == 0) return 0;
    const char* all[] = {w->alarm, w->timer};
    for (int k = 0; k < 2; k++) { for (const unsigned char* p = (const unsigned char*)all[k]; *p; p++) { if (*p < 0x20 || *p > 0x7E) return 0; } }
    for (int i = 0; i < 7; i++) { for (const unsigned char* p = (const unsigned char*)w->wd[i]; *p; p++) { if (*p < 0x21 || *p > 0x7E) return 0; } }
    for (int i = 0; i < 12; i++) { for (const unsigned char* p = (const unsigned char*)w->mon[i]; *p; p++) { if (*p < 0x21 || *p > 0x7E) return 0; } }
    return 1;
}

int main(void)
{
    mlw_t w;
    memset(&w, 0, sizeof(w));

    /* the structure stays small: it lives in PSRAM twice (two slots) */
    CHECK(sizeof(mlw_t) <= 184);
    CHECK(sane(&MLW_EN) && strcmp(MLW_EN.code, "en") == 0 && MLW_EN.dmy == 0);
    CHECK(strcmp(MLW_EN.wd[0], "Sun") == 0 && strcmp(MLW_EN.mon[10], "Nov") == 0);

    /* a good file reads whole */
    CHECK(PARSE(FR, &w) == MLW_OK);
    CHECK(strcmp(w.code, "fr") == 0 && w.dmy == 1 && strcmp(w.wd[3], "mer") == 0 && strcmp(w.mon[7], "aou") == 0);
    CHECK(strcmp(w.alarm, "Alarme") == 0 && strcmp(w.timer, "Minut.") == 0 && sane(&w));
    for (int i = 0; i < 5; i++) {
        mlw_t x;
        CHECK(PARSE(HOST_PACKS[i], &x) == MLW_OK && sane(&x));
    }
    /* CRLF line ends, comments, blank lines, unknown keys, no final newline, key order */
    CHECK(PARSE("# a pack\r\n\r\nweekdays=dom,lun,mar,mie,jue,vie,sab\r\nlang=es\r\nextra=ignored\r\nmonths=ene,feb,mar,abr,may,jun,jul,ago,sep,oct,nov,dic\r\n"
                "order=dmy\r\nalarm=Alarma\r\ntimer=Tiempo", &w) == MLW_OK && strcmp(w.code, "es") == 0 && strcmp(w.timer, "Tiempo") == 0);
    CHECK(PARSE("lang=en\norder=mdy\nweekdays=Sun,Mon,Tue,Wed,Thu,Fri,Sat\nmonths=Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec\nalarm=Alarm\ntimer=Timer\n", &w) == MLW_OK && w.dmy == 0);
    /* a chip word may hold a space; it is trimmed */
    CHECK(PARSE("lang=fr\norder=dmy\nweekdays=dim,lun,mar,mer,jeu,ven,sam\nmonths=jan,fev,mar,avr,mai,jun,jul,aou,sep,oct,nov,dec\nalarm= Reveil \ntimer=Min. cuis\n", &w) == MLW_OK
          && strcmp(w.alarm, "Reveil") == 0 && strcmp(w.timer, "Min. cuis") == 0);

    /* refusals: each leaves the target exactly as it was */
    {
        mlw_t keep;
        CHECK(PARSE(FR, &keep) == MLW_OK);
        mlw_t t = keep;
        const char* bad[] = {
            "",                                                                                                   /* size */
            "lang=fr\norder=dmy\nweekdays=dim,lun,mar,mer,jeu,ven,sam\nmonths=jan,fev,mar,avr,mai,jun,jul,aou,sep,oct,nov,dec\nalarm=Alarme\n", /* timer missing */
            "lang=fr\norder=dmy\nweekdays=dim,lun,mar,mer,jeu,ven\nmonths=jan,fev,mar,avr,mai,jun,jul,aou,sep,oct,nov,dec\nalarm=A\ntimer=T\n", /* six weekdays */
            "lang=fr\norder=dmy\nweekdays=dim,lun,mar,mer,jeu,ven,sam,xxx\nmonths=jan,fev,mar,avr,mai,jun,jul,aou,sep,oct,nov,dec\nalarm=A\ntimer=T\n", /* eight */
            "lang=fr\norder=dmy\nweekdays=dim,lun,mar,mer,jeu,ven,sam\nmonths=jan,fev,mar,avr,mai,jun,jul,aou,sep,oct,nov\nalarm=A\ntimer=T\n", /* eleven months */
            "lang=fr\norder=dmy\nweekdays=dim,lun,mar,mer,jeu,ven,sam\nmonths=jan,fev,mar,avr,mai,jun,jul,aou,sep,oct,nov,dec,jan\nalarm=A\ntimer=T\n",
            "lang=fr\norder=dmy\nweekdays=dim,lun,mar,mer,jeu,ven,\nmonths=jan,fev,mar,avr,mai,jun,jul,aou,sep,oct,nov,dec\nalarm=A\ntimer=T\n", /* empty word */
            "lang=fr\norder=dmy\nweekdays=dimanche,lun,mar,mer,jeu,ven,sam\nmonths=jan,fev,mar,avr,mai,jun,jul,aou,sep,oct,nov,dec\nalarm=A\ntimer=T\n", /* 8 letters */
            "lang=fr\norder=dmy\nweekdays=di m,lun,mar,mer,jeu,ven,sam\nmonths=jan,fev,mar,avr,mai,jun,jul,aou,sep,oct,nov,dec\nalarm=A\ntimer=T\n", /* space in a day word */
            "lang=FR\norder=dmy\nweekdays=dim,lun,mar,mer,jeu,ven,sam\nmonths=jan,fev,mar,avr,mai,jun,jul,aou,sep,oct,nov,dec\nalarm=A\ntimer=T\n",
            "lang=fra\norder=dmy\nweekdays=dim,lun,mar,mer,jeu,ven,sam\nmonths=jan,fev,mar,avr,mai,jun,jul,aou,sep,oct,nov,dec\nalarm=A\ntimer=T\n",
            "lang=f1\norder=dmy\nweekdays=dim,lun,mar,mer,jeu,ven,sam\nmonths=jan,fev,mar,avr,mai,jun,jul,aou,sep,oct,nov,dec\nalarm=A\ntimer=T\n",
            "lang=fr\norder=ymd\nweekdays=dim,lun,mar,mer,jeu,ven,sam\nmonths=jan,fev,mar,avr,mai,jun,jul,aou,sep,oct,nov,dec\nalarm=A\ntimer=T\n",
            "lang=fr\norder=dmy\nweekdays=dim,lun,mar,mer,jeu,ven,sam\nmonths=jan,fev,mar,avr,mai,jun,jul,aou,sep,oct,nov,dec\nalarm=Alarme tres longue\ntimer=T\n", /* chip word over 11 */
            "lang=fr\nno equals sign here\n",
            "=fr\n",
        };
        for (size_t i = 0; i < sizeof(bad) / sizeof(bad[0]); i++) {
            const mlw_err_t e = PARSE(bad[i], &t);
            CHECK(e != MLW_OK);
            CHECK(memcmp(&t, &keep, sizeof(t)) == 0);
        }
        /* a byte outside ASCII: an accented letter is refused because the screen font would draw a box */
        char acc[512];
        snprintf(acc, sizeof(acc), "%s", FR);
        char* at = strstr(acc, "aou");
        at[1] = (char)0xC3; /* UTF-8 start byte */
        CHECK(mlw_parse(acc, strlen(acc), &t) == MLW_ERR_ASCII && memcmp(&t, &keep, sizeof(t)) == 0);
        snprintf(acc, sizeof(acc), "%s", FR);
        acc[10] = 0x07; /* a control byte */
        CHECK(mlw_parse(acc, strlen(acc), &t) == MLW_ERR_ASCII);
        char big[2048];
        memset(big, 'a', sizeof(big));
        CHECK(mlw_parse(big, sizeof(big), &t) == MLW_ERR_SIZE && mlw_parse(NULL, 5, &t) == MLW_ERR_SIZE && mlw_parse(FR, 0, &t) == MLW_ERR_SIZE);
        CHECK(mlw_parse(big, MLW_FILE_MAX, &t) != MLW_OK); /* at the limit, still refused as a file of "aaaa..." (no line has an equals sign) */
        CHECK(mlw_parse(NULL, 0, &t) == MLW_ERR_SIZE);
    }

    /* the words shown: the pack only for its own language, English for everything else, and for no pack */
    {
        mlw_t fr;
        CHECK(PARSE(FR, &fr) == MLW_OK);
        CHECK(mlw_for(&fr, "fr") == &fr);
        CHECK(mlw_for(&fr, "de") == &MLW_EN && mlw_for(&fr, "es") == &MLW_EN && mlw_for(&fr, "en") == &MLW_EN && mlw_for(&fr, "") == &MLW_EN);
        CHECK(mlw_for(NULL, "fr") == &MLW_EN && mlw_for(&fr, NULL) == &MLW_EN);
        mlw_t blank;
        memset(&blank, 0, sizeof(blank));
        CHECK(mlw_for(&blank, "") == &MLW_EN); /* a pack with no code is never chosen */
    }

    /* FUZZ: damage a good file at random; the reader never reads out of range, and says yes only to a file whose words are all sane */
    {
        char buf[600];
        int accepted = 0, refused = 0;
        for (int round = 0; round < 40000; round++) {
            const char* src = HOST_PACKS[rnd() % 5];
            size_t n        = strlen(src);
            memcpy(buf, src, n);
            const int edits = 1 + (int)(rnd() % 4);
            for (int k = 0; k < edits; k++) {
                const size_t at = rnd() % n;
                switch (rnd() % 5) {
                case 0: buf[at] = (char)(rnd() & 0xFF); break;
                case 1: buf[at] = ','; break;
                case 2: buf[at] = '\n'; break;
                case 3: if (n > 4) { memmove(buf + at, buf + at + 1, n - at - 1); n--; } break;
                default: buf[at] = "abcxyz=,\n \x01\x80"[rnd() % 12]; break;
                }
            }
            mlw_t keep, t;
            memset(&keep, 0x5A, sizeof(keep));
            t = keep;
            const mlw_err_t e = mlw_parse(buf, n, &t);
            if (e == MLW_OK) {
                accepted++;
                CHECK(sane(&t));
            } else {
                refused++;
                CHECK(memcmp(&t, &keep, sizeof(t)) == 0);
            }
        }
        CHECK(accepted > 0 && refused > 1000);
        /* truncation at every length */
        for (size_t cut = 0; cut <= strlen(FR); cut++) {
            mlw_t t, keep;
            memset(&keep, 0x33, sizeof(keep));
            t = keep;
            const mlw_err_t e = mlw_parse(FR, cut, &t);
            if (e != MLW_OK) CHECK(memcmp(&t, &keep, sizeof(t)) == 0); else CHECK(sane(&t));
        }
    }

    if (failures != 0) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
