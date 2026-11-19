// HIDL runtime: implementação de referência do mapeamento C++ (docs/SPEC_MAPEAMENTO.md, seções 3-5).
// Escrito à mão, header-only, C++11, independente de qualquer contrato.
// O código gerado por `hidl compile --cpp` inclui este arquivo e só emite o que
// varia com o contrato (structs, offsets, larguras).
//
// Convenção de bits (big-endian de rede): o bit 0 do pacote é o MSB do byte 0.
#ifndef HIDL_RUNTIME_HPP_
#define HIDL_RUNTIME_HPP_

#include <cstddef>
#include <cstdint>
#include <type_traits>

// Versão da ABI entre runtime e código gerado. O gerador emite
//   static_assert(HIDL_RUNTIME_ABI == N, ...)
// Incrementar quando a semântica de read/write mudar.
#define HIDL_RUNTIME_ABI 1

namespace hidl {
namespace rt {
namespace detail {

// Estende o sinal de um valor de w bits (1 <= w <= 63) para 64 bits.
inline std::int64_t sign_extend(std::uint64_t v, unsigned w) {
    if (w < 64 && ((v >> (w - 1)) & 1u)) v |= (~std::uint64_t(0)) << w;
    return static_cast<std::int64_t>(v);
}

// Conversão entre o valor cru de W bits e o tipo C++ do campo.
template <typename T, unsigned W, bool IsBool = std::is_same<T, bool>::value,
          bool IsSigned = std::is_signed<T>::value>
struct Conv;

template <typename T, unsigned W>
struct Conv<T, W, true, false> {
    static T from_raw(std::uint64_t raw) { return raw != 0; }
    static std::uint64_t to_raw(T v) { return v ? 1u : 0u; }
};

template <typename T, unsigned W>
struct Conv<T, W, false, true> {
    static_assert(std::is_integral<T>::value, "HIDL: tipo de campo deve ser inteiro");
    static_assert(W >= 1 && W <= 64, "HIDL: largura deve estar em [1, 64]");
    static_assert(W <= sizeof(T) * 8, "HIDL: tipo C++ menor que a largura do campo");
    static T from_raw(std::uint64_t raw) { return static_cast<T>(sign_extend(raw, W)); }
    static std::uint64_t to_raw(T v) { return static_cast<std::uint64_t>(static_cast<std::int64_t>(v)); }
};

template <typename T, unsigned W>
struct Conv<T, W, false, false> {
    static_assert(std::is_integral<T>::value, "HIDL: tipo de campo deve ser inteiro");
    static_assert(W >= 1 && W <= 64, "HIDL: largura deve estar em [1, 64]");
    static_assert(W <= sizeof(T) * 8, "HIDL: tipo C++ menor que a largura do campo");
    static T from_raw(std::uint64_t raw) { return static_cast<T>(raw); }
    static std::uint64_t to_raw(T v) { return static_cast<std::uint64_t>(v); }
};

// Big-endian. Caminho rápido (leitura por byte) quando offset e largura são múltiplos de 8;
// caso contrário, laço bit a bit (o compilador desenrola, pois Off e W são constantes).
template <std::size_t Off, unsigned W, bool Aligned = (Off % 8 == 0 && W % 8 == 0)>
struct Be;

template <std::size_t Off, unsigned W>
struct Be<Off, W, true> {
    static std::uint64_t read(const std::uint8_t* b) {
        std::uint64_t v = 0;
        for (unsigned i = 0; i < W / 8; ++i) v = (v << 8) | b[Off / 8 + i];
        return v;
    }
    static void write(std::uint8_t* b, std::uint64_t v) {
        for (unsigned i = 0; i < W / 8; ++i)
            b[Off / 8 + i] = static_cast<std::uint8_t>((v >> (8 * (W / 8 - 1 - i))) & 0xFFu);
    }
};

template <std::size_t Off, unsigned W>
struct Be<Off, W, false> {
    static std::uint64_t read(const std::uint8_t* b) {
        std::uint64_t v = 0;
        for (unsigned i = 0; i < W; ++i) {
            const std::size_t bit = Off + i;
            v = (v << 1) | ((b[bit >> 3] >> (7 - (bit & 7))) & 1u);
        }
        return v;
    }
    static void write(std::uint8_t* b, std::uint64_t v) {
        for (unsigned i = 0; i < W; ++i) {
            const std::size_t bit = Off + W - 1 - i;
            const std::uint8_t m = static_cast<std::uint8_t>(1u << (7 - (bit & 7)));
            if ((v >> i) & 1u) b[bit >> 3] = static_cast<std::uint8_t>(b[bit >> 3] | m);
            else               b[bit >> 3] = static_cast<std::uint8_t>(b[bit >> 3] & ~m);
        }
    }
};

// Little-endian: só campos alinhados em byte (verificado em tempo de compilação).
template <std::size_t Off, unsigned W>
struct Le {
    static_assert(Off % 8 == 0 && W % 8 == 0, "HIDL: little-endian exige campo alinhado em byte");
    static std::uint64_t read(const std::uint8_t* b) {
        std::uint64_t v = 0;
        for (unsigned i = 0; i < W / 8; ++i) v |= static_cast<std::uint64_t>(b[Off / 8 + i]) << (8 * i);
        return v;
    }
    static void write(std::uint8_t* b, std::uint64_t v) {
        for (unsigned i = 0; i < W / 8; ++i)
            b[Off / 8 + i] = static_cast<std::uint8_t>((v >> (8 * i)) & 0xFFu);
    }
};

}  // namespace detail

// Lê o campo de W bits no bit Off do pacote `b`. Inteiros com sinal sofrem extensão de sinal.
template <typename T, std::size_t Off, unsigned W>
inline T read_be(const std::uint8_t* b) { return detail::Conv<T, W>::from_raw(detail::Be<Off, W>::read(b)); }

// Grava os W bits menos significativos de `value` (valor fora da faixa é truncado, como um cast C).
template <typename T, std::size_t Off, unsigned W>
inline void write_be(std::uint8_t* b, T value) { detail::Be<Off, W>::write(b, detail::Conv<T, W>::to_raw(value)); }

template <typename T, std::size_t Off, unsigned W>
inline T read_le(const std::uint8_t* b) { return detail::Conv<T, W>::from_raw(detail::Le<Off, W>::read(b)); }

template <typename T, std::size_t Off, unsigned W>
inline void write_le(std::uint8_t* b, T value) { detail::Le<Off, W>::write(b, detail::Conv<T, W>::to_raw(value)); }

}  // namespace rt
}  // namespace hidl

#endif  // HIDL_RUNTIME_HPP_
