# Third-party notices

TeleCat is derived work. This file records where it comes from and what the upstream
projects ask of redistributors. It does not replace the license texts.

## Nekogram

- Source: https://github.com/Nekogram/Nekogram
- Authors and maintainers: the Nekogram project, including @Duang
- License: GNU General Public License v3.0 (`LICENSE` in this repository)

TeleCat is a fork of Nekogram. The Nekogram-specific code under
`TMessagesProj/src/main/java/tw/nekomimi/` and the settings, translator, session, passkey,
folder and streaming modules come from Nekogram and stay under its license. TeleCat
changes the visible branding, adds the Material 3 and Liquid Glass themes, and reworks the
appearance settings entry points. The Java package names keep the `tw.nekomimi` namespace
so upstream modules and the build plugins keep resolving; they are not a claim of
affiliation.

Nekogram's own strings, translation project and update channel are referenced where they
are functionally needed. They remain Nekogram's.

## Telegram for Android

- Source: https://github.com/DrKLO/Telegram
- License: GNU General Public License v3.0

The client core, MTProto implementation and resources are Telegram for Android. TeleCat
does not modify the Telegram API, the network protocol or the servers it talks to.

## Bundled components

The build pulls third-party native and Java components whose licenses ship with them,
among others: TDLib (`TMessagesProj/jni/td`), TGVoip (`TMessagesProj/jni/tgcalls`),
FFmpeg, libvpx, dav1d, libyuv, OpenH264, BoringSSL, abseil, wasm-micro-runtime, tlottie,
jlatexmath, the Nekogram `media` module, `gifski` and the `translator` Android libraries.
Check each submodule and Gradle dependency for its own terms before redistributing a
binary.

## License

TeleCat as a whole is distributed under GPLv3. If you publish a modified build, you must
publish the corresponding source under the same license and keep the attributions above.
