#include "cmmnctn.h"
#include <Arduino.h>
#include <mbedtls/md.h>
#include <mbedtls/pk.h>
#include <mbedtls/rsa.h>
#include <mbedtls/aes.h>
#include <mbedtls/entropy.h>
#include <mbedtls/ctr_drbg.h>

enum
{
    STATUS_OKAY,
    STATUS_ERROR,
    STATUS_EXPIRED,
    STATUS_HASH_ERROR,
    STATUS_BAD_REQUEST,
    STATUS_INVALID_SESSION,
};

typedef enum
{
    SESSION_CLOSE,
    SESSION_GET_TEMP,
    SESSION_TOGGLE_LED,

    SESSION_ERROR,
    SESSION_ESTABLISH,
} request_t;

constexpr int AES_SIZE{32};
constexpr int DER_SIZE{294};
constexpr int RSA_SIZE{256};
constexpr int HASH_SIZE{32};
constexpr int EXPONENT{65537};
constexpr int KEEP_ALIVE{60000};
constexpr int AES_BLOCK_SIZE{16};

static mbedtls_aes_context aes_ctx;
static mbedtls_md_context_t hmac_ctx;
static mbedtls_pk_context client_ctx;
static mbedtls_pk_context server_ctx;
static mbedtls_entropy_context entropy;
static mbedtls_ctr_drbg_context ctr_drbg;

static uint32_t accessed{0};
static uint64_t session_id{0};
static uint8_t aes_key[AES_SIZE]{0};
static uint8_t enc_iv[AES_BLOCK_SIZE]{0};
static uint8_t dec_iv[AES_BLOCK_SIZE]{0};
static uint8_t buffer[DER_SIZE + RSA_SIZE] = {0};
static const uint8_t secret_key[HASH_SIZE] = {0x29, 0x49, 0xde, 0xc2, 0x3e, 0x1e, 0x34, 0xb5, 0x2d, 0x22, 0xb5,
                                              0xba, 0x4c, 0x34, 0x23, 0x3a, 0x9d, 0x3f, 0xe2, 0x97, 0x14, 0xbe,
                                              0x24, 0x62, 0x81, 0x0c, 0x86, 0xb1, 0xf6, 0x92, 0x54, 0xd6};

#define ON "on"
#define OFF "off"

bool session_init(const char *com_param);

void session_close(void);

bool session_establish(void);

request_t session_request(void);

bool session_response(bool success, const uint8_t *res, size_t rlen);

void setup()
{
    pinMode(GPIO_NUM_21, OUTPUT);
    pinMode(GPIO_NUM_32, OUTPUT);

    if (!session_init("115200"))
    {
        while (1)
        {
            digitalWrite(GPIO_NUM_21, !digitalRead(GPIO_NUM_21));
            delay(500);
        }
    }
}

void loop()
{
    char response[8] = {0};
    static uint8_t state = LOW;

    request_t request = session_request();
    digitalWrite(GPIO_NUM_32, LOW);

    switch (request)
    {
    case SESSION_ESTABLISH:
        if (!session_establish())
        {
            request = SESSION_ERROR;
        }
        break;

    case SESSION_CLOSE:
        session_close();
        if (!session_response(true, nullptr, 0))
        {
            request = SESSION_ERROR;
        }
        break;
    case SESSION_GET_TEMP:
        sprintf((char *)&response, "%2.2f", temperatureRead());
        if (!session_response(true, (const uint8_t *)response, strlen(response)))
        {
            request = SESSION_ERROR;
        }
        break;

    case SESSION_TOGGLE_LED:
        state = (state == LOW) ? HIGH : LOW;
        digitalWrite(GPIO_NUM_21, state);
        strcpy(response, (LOW == digitalRead(GPIO_NUM_21)) ? OFF : ON);

        if (!session_response((state == digitalRead(GPIO_NUM_21)), (const uint8_t *)response, strlen(response)))
        {
            request = SESSION_ERROR;
        }
        break;

    default:
        break;
    }

    if (request == SESSION_ERROR)
    {
        digitalWrite(GPIO_NUM_32, HIGH);
    }
}

static size_t client_read(uint8_t *buf, size_t blen)
{
    size_t length = cmmnctn_read(buf, blen);

    if (length > HASH_SIZE)
    {
        length -= HASH_SIZE;
        uint8_t hmac[HASH_SIZE]{0};
        mbedtls_md_hmac_starts(&hmac_ctx, secret_key, HASH_SIZE);
        mbedtls_md_hmac_update(&hmac_ctx, buf, length);
        mbedtls_md_hmac_finish(&hmac_ctx, hmac);
        if (0 != memcmp(hmac, buf + length, HASH_SIZE))
        {
            length = 0;
        }
    }
    else
    {
        length = 0;
    }

    return length;
}

static bool client_write(uint8_t *buf, size_t dlen)
{
    mbedtls_md_hmac_starts(&hmac_ctx, secret_key, HASH_SIZE);
    mbedtls_md_hmac_update(&hmac_ctx, buf, dlen);
    mbedtls_md_hmac_finish(&hmac_ctx, buf + dlen);
    dlen += HASH_SIZE;

    return cmmnctn_write(buf, dlen);
}

static void exchange_public_keys(void)
{
    session_id = 0;
    size_t olen, length;

    mbedtls_pk_init(&client_ctx);
    uint8_t cipher[3 * RSA_SIZE + HASH_SIZE] = {0};

    assert(0 == mbedtls_pk_parse_public_key(&client_ctx, buffer, DER_SIZE));
    assert(MBEDTLS_PK_RSA == mbedtls_pk_get_type(&client_ctx));

    assert(DER_SIZE == mbedtls_pk_write_pubkey_der(&server_ctx, buffer, DER_SIZE));

    assert(0 == mbedtls_pk_encrypt(&client_ctx, buffer, DER_SIZE / 2, cipher,
                                   &olen, RSA_SIZE, mbedtls_ctr_drbg_random, &ctr_drbg));

    assert(0 == mbedtls_pk_encrypt(&client_ctx, buffer + DER_SIZE / 2, DER_SIZE / 2,
                                   cipher + RSA_SIZE, &olen, RSA_SIZE, mbedtls_ctr_drbg_random, &ctr_drbg));

    length = 2 * RSA_SIZE;
    assert(client_write(cipher, length));

    length = client_read(cipher, sizeof(cipher));
    assert(length == 3 * RSA_SIZE);

    assert(0 == mbedtls_pk_decrypt(&server_ctx, cipher, RSA_SIZE, buffer, &olen, RSA_SIZE,
                                   mbedtls_ctr_drbg_random, &ctr_drbg));

    length = olen;
    assert(0 == mbedtls_pk_decrypt(&server_ctx, cipher + RSA_SIZE, RSA_SIZE, buffer + length,
                                   &olen, RSA_SIZE, mbedtls_ctr_drbg_random, &ctr_drbg));

    length += olen;
    assert(0 == mbedtls_pk_decrypt(&server_ctx, cipher + 2 * RSA_SIZE, RSA_SIZE, buffer + length,
                                   &olen, RSA_SIZE, mbedtls_ctr_drbg_random, &ctr_drbg));

    length += olen;
    assert(length == (DER_SIZE + RSA_SIZE));

    mbedtls_pk_init(&client_ctx);
    assert(0 == mbedtls_pk_parse_public_key(&client_ctx, buffer, DER_SIZE));
    assert(MBEDTLS_PK_RSA == mbedtls_pk_get_type(&client_ctx));

    assert(0 == mbedtls_pk_verify(&client_ctx, MBEDTLS_MD_SHA256, secret_key, HASH_SIZE, buffer + DER_SIZE, RSA_SIZE));

    strcpy((char *)buffer, "DONE");
    assert(0 == mbedtls_pk_encrypt(&client_ctx, buffer, strlen((const char *)buffer),
                                   cipher, &olen, RSA_SIZE, mbedtls_ctr_drbg_random, &ctr_drbg));

    assert(client_write(cipher, RSA_SIZE));
}

static bool session_write(const uint8_t *res, size_t size)
{
    bool status = false;
    uint8_t response[AES_BLOCK_SIZE] = {0};
    uint8_t cipher[AES_BLOCK_SIZE + HASH_SIZE] = {0};

    memcpy(response, res, size);

    if (0 == mbedtls_aes_crypt_cbc(&aes_ctx, MBEDTLS_AES_ENCRYPT, sizeof(response), enc_iv, response, cipher))
    {
        status = client_write(cipher, AES_BLOCK_SIZE);
    }

    return status;
}

bool session_init(const char *com_param)
{
    bool status = false;

    if (cmmnctn_init(com_param))
    {

        mbedtls_md_init(&hmac_ctx);

        if (0 == mbedtls_md_setup(&hmac_ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1))
        {

            mbedtls_aes_init(&aes_ctx);

            uint8_t initial[AES_SIZE]{0};
            mbedtls_entropy_init(&entropy);
            mbedtls_ctr_drbg_init(&ctr_drbg);
            for (size_t i = 0; i < sizeof(initial); i++)
            {
                initial[i] = random(0x100);
            }

            if (0 == mbedtls_ctr_drbg_seed(&ctr_drbg, mbedtls_entropy_func, &entropy, initial, sizeof(initial)))
            {
                // RSA-2048
                mbedtls_pk_init(&server_ctx);
                if (0 == mbedtls_pk_setup(&server_ctx, mbedtls_pk_info_from_type(MBEDTLS_PK_RSA)))
                {
                    status = (0 == mbedtls_rsa_gen_key(mbedtls_pk_rsa(server_ctx), mbedtls_ctr_drbg_random, &ctr_drbg, RSA_SIZE * CHAR_BIT, EXPONENT));
                }
            }
        }
    }

    return status;
}

bool session_establish(void)
{
    session_id = 0;
    bool status = false;
    size_t olen, length;
    uint8_t cipher[2 * RSA_SIZE]{0};

    if (0 == mbedtls_pk_decrypt(&server_ctx, buffer, RSA_SIZE, cipher, &olen, RSA_SIZE, mbedtls_ctr_drbg_random, &ctr_drbg))
    {
        length = olen;

        if (0 == mbedtls_pk_decrypt(&server_ctx, buffer + RSA_SIZE, RSA_SIZE, cipher + length, &olen, RSA_SIZE, mbedtls_ctr_drbg_random, &ctr_drbg))
        {
            length += olen;

            if (length == RSA_SIZE)
            {
                if (0 == mbedtls_pk_verify(&client_ctx, MBEDTLS_MD_SHA256, secret_key, HASH_SIZE, cipher, RSA_SIZE))
                {
                    uint8_t *ptr{(uint8_t *)&session_id};
                    for (size_t i = 0; i < sizeof(session_id); i++)
                    {
                        ptr[i] = random(1, 0x100);
                    }

                    for (size_t i = 0; i < sizeof(enc_iv); i++)
                    {
                        enc_iv[i] = random(0x100);
                    }
                    memcpy(dec_iv, enc_iv, sizeof(dec_iv));

                    for (size_t i = 0; i < sizeof(aes_key); i++)
                    {
                        aes_key[i] = random(0x100);
                    }

                    if (0 == mbedtls_aes_setkey_enc(&aes_ctx, aes_key, sizeof(aes_key) * CHAR_BIT))
                    {
                        memcpy(buffer, &session_id, sizeof(session_id));
                        length = sizeof(session_id);

                        memcpy(buffer + length, enc_iv, sizeof(enc_iv));
                        length += sizeof(enc_iv);

                        memcpy(buffer + length, aes_key, sizeof(aes_key));
                        length += sizeof(aes_key);

                        status = true;
                    }
                    else
                    {
                        session_id = 0;
                    }
                }
            }
        }
    }

    if (!status)
    {
        memset(buffer, 0, sizeof(buffer));
        length = sizeof(session_id) + sizeof(enc_iv) + sizeof(aes_key);
    }

    if (0 == mbedtls_pk_encrypt(&client_ctx, buffer, length, cipher, &olen, RSA_SIZE, mbedtls_ctr_drbg_random, &ctr_drbg))
    {
        if (!client_write(cipher, RSA_SIZE))
        {
            status = false;
        }
    }

    if (status)
    {
        accessed = millis();
    }
    else
    {
        session_id = 0;
    }

    return status;
}

void session_close(void)
{
    session_id = 0;
}

request_t session_request(void)
{
    uint8_t response = STATUS_OKAY;
    request_t request = SESSION_ERROR;

    size_t length = client_read(buffer, sizeof(buffer));

    if (length == DER_SIZE)
    {
        exchange_public_keys();

        length = client_read(buffer, sizeof(buffer));
    }

    if (length == 2 * RSA_SIZE)
    {
        request = SESSION_ESTABLISH;
    }
    else if (length == AES_BLOCK_SIZE)
    {
        if (session_id != 0)
        {
            uint32_t now = millis();

            if (now - accessed <= KEEP_ALIVE)
            {
                accessed = now;

                uint8_t temp[AES_BLOCK_SIZE]{0};

                if (0 == mbedtls_aes_crypt_cbc(&aes_ctx, MBEDTLS_AES_DECRYPT, AES_BLOCK_SIZE, dec_iv, buffer, temp))
                {
                    if (temp[AES_BLOCK_SIZE - 1] == 9)
                    {
                        if (0 == memcmp(&session_id, &temp[1], sizeof(session_id)))
                        {
                            switch (temp[0])
                            {
                            case SESSION_CLOSE:
                            case SESSION_GET_TEMP:
                            case SESSION_TOGGLE_LED:
                                request = (request_t)temp[0];
                                break;
                            default:
                                response = STATUS_BAD_REQUEST;
                                break;
                            }
                        }
                        else
                        {
                            response = STATUS_INVALID_SESSION;
                        }
                    }
                    else
                    {
                        response = STATUS_BAD_REQUEST;
                    }
                }
                else
                {
                    response = STATUS_ERROR;
                }
            }
            else
            {
                session_id = 0;
                response = STATUS_EXPIRED;
            }
        }
        else
        {
            response = STATUS_INVALID_SESSION;
        }
    }
    else
    {
        response = STATUS_HASH_ERROR;
    }

    if (request == SESSION_ERROR)
    {
        assert(session_write(&response, sizeof(response)));
    }

    return request;
}

bool session_response(bool success, const uint8_t *res, size_t rlen)
{
    size_t len = 1;
    uint8_t response[AES_BLOCK_SIZE] = {0};

    response[0] = success ? STATUS_OKAY : STATUS_ERROR;

    if ((res != nullptr) && (rlen > 0))
    {
        memcpy(response + len, res, rlen);
        len += rlen;
    }

    return session_write(response, len);
}