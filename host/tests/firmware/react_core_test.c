/* Host test for the word reaction core (patch U02): cc -std=c99 -Wall -Wextra -Werror -I<dir with the headers>. */
#include <stdio.h>
#include <string.h>
#include "maipai_react_core.h"

static int failures;
#define CHECK(cond)                                        \
    do {                                                   \
        if (!(cond)) {                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond); \
            failures++;                                    \
        }                                                  \
    } while (0)

static void fold_is(const char* in, const char* want)
{
    char out[64];
    mr_fold(in, out, sizeof(out));
    if (strcmp(out, want) != 0) {
        printf("FAIL fold(\"%s\") = \"%s\", wanted \"%s\"\n", in, out, want);
        failures++;
    }
}

static void test_fold(void)
{
    fold_is("Hello!", "hello");
    fold_is("  Thank   you,  so much.. ", "thank you so much");
    fold_is("Te quiero", "te quiero");
    fold_is("Désolé", "desole");
    fold_is("Buenas Noches", "buenas noches");
    fold_is("ma\xC3\xB1" "ana", "manana");        /* n with a tilde */
    fold_is("gr\xC3\xBC\xC3\x9F" "e", "grusse");   /* u umlaut, sharp s */
    fold_is("je t'aime", "je taime");
    fold_is("A\xC3\x86" "B", "aaeb");
    fold_is("\xE4\xBD\xA0\xE5\xA5\xBD", "");       /* characters this screen cannot show are a gap */
    fold_is("ok \xE4\xBD\xA0 go", "ok go");
    fold_is("", "");
    char tiny[4];
    CHECK(mr_fold("abcdefgh", tiny, sizeof(tiny)) == 3 && strcmp(tiny, "abc") == 0);
    CHECK(mr_fold(NULL, tiny, sizeof(tiny)) == 0);
}

static void test_add_checks(void)
{
    mr_table_t t;
    mr_clear(&t);
    CHECK(mr_add(&t, "hello", "happy", "", "sparkles", "") == MR_OK && t.n == 1);
    CHECK(mr_add(&t, "HELLO!", "sad", "", "", "") == MR_ERR_DUP); /* the same words after folding */
    CHECK(mr_add(&t, "a", "happy", "", "", "") == MR_ERR_PHRASE);
    CHECK(mr_add(&t, "", "happy", "", "", "") == MR_ERR_PHRASE);
    CHECK(mr_add(&t, "this phrase is far too long to keep", "happy", "", "", "") == MR_ERR_PHRASE);
    CHECK(mr_add(&t, "wow", "grumpy", "", "", "") == MR_ERR_FACE);
    CHECK(mr_add(&t, "wow", "happy", "siren", "", "") == MR_ERR_SOUND);
    CHECK(mr_add(&t, "wow", "happy", "exclamation", "", "") == MR_ERR_SOUND); /* alarm-like sounds are not allowed */
    CHECK(mr_add(&t, "wow", "happy", "", "confetti", "") == MR_ERR_DECOR);
    CHECK(mr_add(&t, "wow", "happy", "", "", "moonwalk") == MR_ERR_DANCE);
    CHECK(mr_add(&t, "wow", "none", "none", "none", "none") == MR_ERR_EMPTY);
    CHECK(mr_add(&t, "wow", NULL, NULL, NULL, "robot") == MR_OK && t.n == 2);
    CHECK(t.n == 2); /* nothing was added by the errors */
    for (int i = 0; t.n < MR_MAX; i++) {
        char p[16];
        snprintf(p, sizeof(p), "word %d", i);
        CHECK(mr_add(&t, p, "happy", "", "", "") == MR_OK);
    }
    CHECK(mr_add(&t, "one more", "happy", "", "", "") == MR_ERR_FULL);
}

static const mr_entry_t* hit(const mr_table_t* t, const char* text)
{
    const int i = mr_match(t, text);
    return i < 0 ? NULL : &t->e[i];
}

static void test_defaults_and_matching(void)
{
    mr_table_t t;
    mr_defaults(&t);
    CHECK(t.n == MR_DEFAULT_COUNT); /* every built-in row passed the checks */
    CHECK(t.n >= 30);
    const mr_entry_t* e = hit(&t, "Hello there, Nova!");
    CHECK(e != NULL && strcmp(e->phrase, "hello") == 0 && e->face == 1 && e->decor == MD_SPARKLES);
    e = hit(&t, "Thank you so much");
    CHECK(e != NULL && strcmp(e->phrase, "thank you") == 0 && e->sound != 0);
    e = hit(&t, "I love this song");
    CHECK(e != NULL && strcmp(e->phrase, "love") == 0 && e->dance == 1 && e->decor == MD_HEART);
    e = hit(&t, "sorry about that");
    CHECK(e != NULL && e->face == 2 && e->decor == 0);
    e = hit(&t, "Good night!");
    CHECK(e != NULL && e->face == 5 && e->decor == MD_ZZZ);
    /* Spanish, French, German, Portuguese, Italian pairs */
    CHECK(hit(&t, "Hola amigo") != NULL);
    CHECK(hit(&t, "Muchas gracias") != NULL);
    CHECK(hit(&t, "Te quiero mucho") != NULL && hit(&t, "Te quiero mucho")->dance == 1);
    CHECK(hit(&t, "Lo siento") != NULL);
    CHECK(hit(&t, "Buenas noches") != NULL);
    CHECK(hit(&t, "Bonjour") != NULL && hit(&t, "Merci beaucoup") != NULL && hit(&t, "Je t'aime") != NULL);
    CHECK(hit(&t, "Désolé") != NULL && hit(&t, "Bonne nuit") != NULL);
    CHECK(hit(&t, "Hallo") != NULL && hit(&t, "Danke") != NULL && hit(&t, "Ich liebe dich") != NULL);
    CHECK(hit(&t, "Es tut mir leid") != NULL && hit(&t, "Gute Nacht") != NULL);
    CHECK(hit(&t, "Olá") != NULL && hit(&t, "Obrigada") != NULL && hit(&t, "Te amo") != NULL);
    CHECK(hit(&t, "Desculpa") != NULL && hit(&t, "Boa noite") != NULL);
    CHECK(hit(&t, "Ciao!") != NULL && hit(&t, "Grazie mille") != NULL && hit(&t, "Ti voglio bene") != NULL);
    CHECK(hit(&t, "Scusa") != NULL && hit(&t, "Buonanotte") != NULL);
    /* whole words only */
    CHECK(hit(&t, "what a sorrow") == NULL);
    CHECK(hit(&t, "glovely") == NULL);
    CHECK(hit(&t, "") == NULL);
    CHECK(hit(&t, "the weather is cloudy") == NULL);
}

static void test_longest_wins(void)
{
    mr_table_t t;
    mr_clear(&t);
    CHECK(mr_add(&t, "you", "sad", "", "", "") == MR_OK);
    CHECK(mr_add(&t, "thank you", "happy", "", "", "") == MR_OK);
    CHECK(mr_add(&t, "thank you very much", "angry", "", "", "") == MR_OK);
    CHECK(hit(&t, "thank you very much indeed")->face == 3);
    CHECK(hit(&t, "oh thank you")->face == 1);
    CHECK(hit(&t, "see you")->face == 2);
}

static void test_record_round_trip_and_damage(void)
{
    mr_table_t a, b;
    mr_defaults(&a);
    uint8_t buf[MR_BLOB_MAX];
    const size_t n = mr_save(&a, buf, sizeof(buf));
    CHECK(n == 2 + (size_t)a.n * MR_ROW_BYTES + 1);
    CHECK(mr_load(&b, buf, n) == MR_OK);
    CHECK(b.n == a.n && memcmp(&a.e[3], &b.e[3], sizeof(a.e[3])) == 0);
    CHECK(mr_save(&a, buf, 10) == 0); /* a buffer that is too small writes nothing */
    uint8_t bad[MR_BLOB_MAX];
    memcpy(bad, buf, n);
    bad[5] ^= 0x40;
    CHECK(mr_load(&b, bad, n) == MR_ERR_BLOB && b.n == 0);
    memcpy(bad, buf, n);
    bad[0] = 9;
    CHECK(mr_load(&b, bad, n) == MR_ERR_BLOB);
    CHECK(mr_load(&b, buf, n - 1) == MR_ERR_BLOB);
    CHECK(mr_load(&b, buf, 2) == MR_ERR_BLOB);
    CHECK(mr_load(&b, NULL, 0) == MR_ERR_BLOB);
    /* a row that names a face or decorator that does not exist is refused even with a good checksum */
    memcpy(bad, buf, n);
    bad[2 + MR_PHRASE] = 77;
    bad[n - 1] = mr_sum(bad, n - 1);
    CHECK(mr_load(&b, bad, n) == MR_ERR_BLOB);
    mr_table_t empty;
    mr_clear(&empty);
    CHECK(mr_save(&empty, buf, sizeof(buf)) == 3 && mr_load(&b, buf, 3) == MR_OK && b.n == 0);
}

static void test_every_error_has_words(void)
{
    for (int e = MR_ERR_BLOB; e <= MR_ERR_PHRASE; e++) {
        CHECK(strlen(mr_err_word(e)) > 10);
    }
}

int main(void)
{
    test_fold();
    test_add_checks();
    test_defaults_and_matching();
    test_longest_wins();
    test_record_round_trip_and_damage();
    test_every_error_has_words();
    if (failures) {
        printf("%d failures\n", failures);
        return 1;
    }
    printf("all passed\n");
    return 0;
}
