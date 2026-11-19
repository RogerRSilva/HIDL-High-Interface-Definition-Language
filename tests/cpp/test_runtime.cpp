// Testa hidl/runtime.hpp isolado (sem contrato). A referência é a lógica bit a bit que antes
// era emitida dentro de cada .hpp gerado: o runtime novo tem de produzir resultados idênticos.
#include <cstdio>
#include <random>
#include <type_traits>

#include "hidl/runtime.hpp"

namespace legacy {
std::uint64_t read_be(const std::uint8_t* b, std::size_t off, unsigned w) {
    std::uint64_t v = 0;
    for (unsigned i = 0; i < w; ++i) {
        const std::size_t bit = off + i;
        v = (v << 1) | ((b[bit >> 3] >> (7 - (bit & 7))) & 1u);
    }
    return v;
}
void write_be(std::uint8_t* b, std::size_t off, unsigned w, std::uint64_t v) {
    for (unsigned i = 0; i < w; ++i) {
        const std::size_t bit = off + w - 1 - i;
        const std::uint8_t mask = static_cast<std::uint8_t>(1u << (7 - (bit & 7)));
        if ((v >> i) & 1u) b[bit >> 3] = static_cast<std::uint8_t>(b[bit >> 3] | mask);
        else               b[bit >> 3] = static_cast<std::uint8_t>(b[bit >> 3] & ~mask);
    }
}
std::int64_t sign_extend(std::uint64_t v, unsigned w) {
    if (w < 64 && ((v >> (w - 1)) & 1u)) v |= (~std::uint64_t(0)) << w;
    return static_cast<std::int64_t>(v);
}
}  // namespace legacy

static int g_fail = 0, g_checks = 0;
#define CHECK(c) do { ++g_checks; if (!(c)) { ++g_fail; std::printf("FALHA linha %d: %s\n", __LINE__, #c); } } while (0)

static std::mt19937_64 rng(12345);

template <typename T, bool S = std::is_signed<T>::value> struct Ref;
template <typename T> struct Ref<T, true> {
    static T from(std::uint64_t raw, unsigned w) { return static_cast<T>(legacy::sign_extend(raw, w)); }
};
template <typename T> struct Ref<T, false> {
    static T from(std::uint64_t raw, unsigned) { return static_cast<T>(raw); }
};

template <typename T, std::size_t Off, unsigned W>
void check_field() {
    for (int it = 0; it < 300; ++it) {
        std::uint8_t buf[16];
        for (int i = 0; i < 16; ++i) buf[i] = static_cast<std::uint8_t>(rng());

        const T got = hidl::rt::read_be<T, Off, W>(buf);
        CHECK(got == Ref<T>::from(legacy::read_be(buf, Off, W), W));

        // escrita sobre buffer sujo: bits fora do campo não podem mudar
        std::uint8_t a[16], b[16];
        for (int i = 0; i < 16; ++i) a[i] = b[i] = buf[i];
        const T v = static_cast<T>(rng());
        hidl::rt::write_be<T, Off, W>(a, v);
        legacy::write_be(b, Off, W, static_cast<std::uint64_t>(static_cast<std::int64_t>(v)));
        for (int i = 0; i < 16; ++i) CHECK(a[i] == b[i]);
        // round-trip: o que se lê é o valor truncado/estendido a W bits
        CHECK((hidl::rt::read_be<T, Off, W>(a) == Ref<T>::from(legacy::read_be(b, Off, W), W)));
    }
}

int main() {
    // alinhados em byte (caminho rápido)
    check_field<std::int16_t, 0, 16>();
    check_field<std::int16_t, 16, 16>();
    check_field<std::uint8_t, 8, 8>();
    check_field<std::int8_t, 0, 8>();
    check_field<std::int32_t, 32, 32>();
    check_field<std::uint32_t, 8, 24>();
    check_field<std::int64_t, 0, 64>();
    check_field<std::uint64_t, 8, 64>();
    // não alinhados / cruzando byte (caminho bit a bit)
    check_field<std::uint8_t, 3, 5>();
    check_field<std::int8_t, 3, 5>();
    check_field<std::uint8_t, 7, 1>();
    check_field<std::uint16_t, 5, 11>();
    check_field<std::int16_t, 13, 12>();
    check_field<std::uint32_t, 7, 20>();
    check_field<std::int32_t, 1, 31>();
    check_field<std::uint64_t, 3, 61>();
    check_field<std::int64_t, 3, 61>();
    check_field<std::uint64_t, 0, 63>();
    // alinhado em offset mas não em largura, e vice-versa
    check_field<std::uint16_t, 8, 12>();
    check_field<std::uint16_t, 4, 8>();

    // bool
    { std::uint8_t b[2] = {0x00, 0x40};
      CHECK((hidl::rt::read_be<bool, 9, 1>(b) == true));
      CHECK((hidl::rt::read_be<bool, 8, 1>(b) == false));
      hidl::rt::write_be<bool, 0, 1>(b, true);
      CHECK(b[0] == 0x80 && b[1] == 0x40);
      hidl::rt::write_be<bool, 9, 1>(b, false);
      CHECK(b[1] == 0x00); }

    // extensão de sinal explícita
    { std::uint8_t b[2] = {0xFF, 0xFF};
      CHECK((hidl::rt::read_be<std::int16_t, 0, 16>(b) == -1)); }
    { std::uint8_t b[1] = {0xF8};
      CHECK((hidl::rt::read_be<std::int8_t, 0, 5>(b) == -1));
      CHECK((hidl::rt::read_be<std::uint8_t, 0, 5>(b) == 31)); }
    { std::uint8_t b[1] = {0x78};  // 01111 -> +15
      CHECK((hidl::rt::read_be<std::int8_t, 0, 5>(b) == 15)); }

    // truncamento na escrita (como cast C): 9 em uint3 vira 1
    { std::uint8_t b[1] = {0};
      hidl::rt::write_be<std::uint8_t, 0, 3>(b, 9);
      CHECK(b[0] == 0x20); }

    // little-endian
    { std::uint8_t b[8] = {0};
      hidl::rt::write_le<std::uint32_t, 0, 32>(b, 0x11223344u);
      CHECK(b[0] == 0x44 && b[1] == 0x33 && b[2] == 0x22 && b[3] == 0x11);
      CHECK((hidl::rt::read_le<std::uint32_t, 0, 32>(b) == 0x11223344u));
      hidl::rt::write_le<std::int16_t, 32, 16>(b, std::int16_t(-2));
      CHECK(b[4] == 0xFE && b[5] == 0xFF);
      CHECK((hidl::rt::read_le<std::int16_t, 32, 16>(b) == -2));
      hidl::rt::write_le<std::int64_t, 0, 64>(b, INT64_MIN);
      CHECK((hidl::rt::read_le<std::int64_t, 0, 64>(b) == INT64_MIN)); }

    std::printf("%d verificacoes, %d falhas\n", g_checks, g_fail);
    return g_fail ? 1 : 0;
}
