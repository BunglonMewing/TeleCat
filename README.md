# TeleCat

TeleCat is a third-party Telegram client built on [Nekogram](https://github.com/Nekogram/Nekogram).
It keeps the Nekogram feature set and adds a full Material 3 look plus a Liquid Glass
look, both shipped as built-in themes.

- Fork repository: https://github.com/BunglonMewing/TeleCat
- Upstream project: https://github.com/Nekogram/Nekogram
- Upstream Telegram for Android: https://github.com/DrKLO/Telegram

## Themes

Two theme families are registered in `Settings → Appearance → Themes`, first in the list:

| Theme | What it is |
| --- | --- |
| Material 3 | Light scheme from a Material 3 tonal palette seeded with Telegram's accent. Tonal surfaces, outlined fields, pill buttons, primary containers for outgoing messages. |
| Material 3 Dark | The same roles on dark tones. |
| Liquid Glass | iOS-style palette: translucent bars, sheets and bubbles over the chat wallpaper, `#0071E3` accent, iMessage-like bubbles. |
| Liquid Glass Dark | Glass in dark mode, true-black canvas. |

Each theme writes all 822 Telegram color keys, so screens that older themes left on the
default blue palette follow the scheme too. Both families keep text contrast at or above
WCAG AA (4.5:1) for message text, list text and dialog text.

The themes are generated. Edit `Tools/telecat-themes/generate.py`, then run:

```bash
python3 Tools/telecat-themes/generate.py
```

This rewrites `TMessagesProj/src/main/assets/telecat_*.attheme`. The script prints the
contrast of every text pair it can check; a value below 4.5 means the palette needs work.
To add a theme by hand, drop an `.attheme` file in `TMessagesProj/src/main/assets` and
register it in `Theme.java` next to the existing built-in themes (`themes.add` plus
`themesDict.put`), and list its name in `ThemeInfo.isDark()`.

## Build

1. Clone with submodules:
   `git clone --recursive --shallow-submodules https://github.com/BunglonMewing/TeleCat.git`
2. Create a Telegram application at https://my.telegram.org and put its credentials in
   `local.properties`:
   ```
   apiId=123456
   apiHash=0123456789abcdef0123456789abcdef
   ```
3. Optional signing: add `storeFile`, `storePassword`, `keyAlias`, `keyPassword` to
   `local.properties` to sign release builds. Without them release builds use debug signing.
4. Optional Firebase: create two Android apps for `tw.nekomimi.nekogram` and
   `tw.nekomimi.nekogram.beta`, enable Firebase Messaging and copy `google-services.json`
   into `TMessagesProj_App/`.
5. Build:
   ```bash
   ./gradlew assembleDebug
   ```
   APKs land in `TMessagesProj_App/build/outputs/apk/`.

GitHub Actions runs `.github/workflows/android-build.yml` on every push and pull request
using debug builds, and can build release APKs from the Actions tab. Repository secrets
it reads: `API_ID`, `API_HASH`, `HELPER_BOT_ID`, `HELPER_BOT_USERNAME`, `MAPS_API_KEY`,
`SENTRY_DSN`, `SENTRY_PROPERTIES` (base64, required by release builds), `KEYSTORE_BASE64`,
`KEYSTORE_PASSWORD`, `KEY_ALIAS`, `KEY_PASSWORD`, `GOOGLE_SERVICES_JSON` (base64).

Without them a debug build still compiles: the workflow writes placeholder `apiId`/`apiHash`,
a placeholder `google-services.json` with a client for both `tw.nekomimi.nekogram` and
`tw.nekomimi.nekogram.beta`, and falls back to debug signing. That APK cannot sign in to
Telegram and push notifications do not work until the real values are set.

## Localization

Most strings follow Telegram for Android translations:
https://translations.telegram.org/en/android/. Nekogram-specific strings are translated
upstream in the [Nekogram Crowdin project](https://neko.crowdin.com/nekogram).

## Credits and license

TeleCat is a fork of Nekogram by the Nekogram authors, which is itself a fork of Telegram
for Android by Telegram FZ-LLC. Both are licensed under GPLv3; TeleCat keeps that license,
see [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

If you redistribute TeleCat, keep the Nekogram and Telegram attribution and publish your
source under GPLv3.
