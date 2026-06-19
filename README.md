> [!IMPORTANT]
> ## Mihon Harmony（非官方兼容分支）
>
> 本仓库是 [Mihon](https://github.com/mihonapp/mihon) 的非官方分支，目标是改善 Mihon 在 HarmonyOS 的卓易通 Android 兼容环境中的可用性。
>
> 当前主要改动是为不支持 SAF `renameDocument` 的文件提供方增加下载文件改名回退方案：当常规改名失败时，通过“复制到目标文件后删除临时文件”完成保存，从而解决漫画图片停留在 `.tmp`、章节下载最终失败的问题。正常支持改名的 Android 设备仍优先使用原有流程。
>
> 本项目不是 HarmonyOS 原生应用，也不隶属于或受 Mihon Open Source Project 官方支持。与本分支相关的问题请提交到[本仓库](https://github.com/zsyou/mihon-harmony/issues)，不要向 Mihon 上游反馈分支特有问题。本分支不提供、不托管任何漫画或内容源。
>
> 本分支保留上游项目的版权声明，并继续遵循 [Apache License 2.0](./LICENSE)。原始项目、主要功能及绝大部分代码均归功于 [Mihon Open Source Project 及其贡献者](https://github.com/mihonapp/mihon/graphs/contributors)。

> [!IMPORTANT]
> ## Mihon Harmony (Unofficial Compatibility Fork)
>
> This repository is an unofficial fork of [Mihon](https://github.com/mihonapp/mihon). Its purpose is to improve Mihon's usability in the ZhuoyiTong Android compatibility environment on HarmonyOS.
>
> The primary change currently included is a download-save fallback for SAF document providers that do not support `renameDocument`. If a normal rename fails, the file or directory is copied to its final destination and the temporary source is removed. This fixes chapter downloads that otherwise remain as `.tmp` files and fail during finalization. Android devices with working rename support continue to use the original path first.
>
> This is not a native HarmonyOS application and is not affiliated with or officially supported by the Mihon Open Source Project. Please report fork-specific issues to [this repository](https://github.com/zsyou/mihon-harmony/issues), not to the upstream Mihon project. This fork does not provide or host any manga or content sources.
>
> This fork retains the upstream copyright notices and remains licensed under the [Apache License 2.0](./LICENSE). The original project, its core functionality, and the great majority of its code are credited to the [Mihon Open Source Project and its contributors](https://github.com/mihonapp/mihon/graphs/contributors).

---

<div align="center">

<a href="https://mihon.app">
    <img src="./.github/assets/logo.png" alt="Mihon logo" title="Mihon logo" width="80"/>
</a>

# Mihon [App](#)

### Full-featured reader
Discover and read manga, webtoons, comics, and more – easier than ever on your Android device.

[![Discord server](https://img.shields.io/discord/1195734228319617024.svg?label=&labelColor=6A7EC2&color=7389D8&logo=discord&logoColor=FFFFFF)](https://discord.gg/mihon)
[![GitHub downloads](https://img.shields.io/github/downloads/mihonapp/mihon/total?label=downloads&labelColor=27303D&color=0D1117&logo=github&logoColor=FFFFFF&style=flat)](https://mihon.app/download)

[![CI](https://img.shields.io/github/actions/workflow/status/mihonapp/mihon/build.yml?labelColor=27303D)](https://github.com/mihonapp/mihon/actions/workflows/build_push.yml)
[![License: Apache-2.0](https://img.shields.io/github/license/mihonapp/mihon?labelColor=27303D&color=0877d2)](/LICENSE)
[![Translation status](https://img.shields.io/weblate/progress/mihon?labelColor=27303D&color=946300)](https://hosted.weblate.org/engage/mihon/)

## Download

[![Mihon Stable](https://img.shields.io/github/release/mihonapp/mihon.svg?maxAge=3600&label=Stable&labelColor=06599d&color=043b69)](https://mihon.app/download)
[![Mihon Beta](https://img.shields.io/github/v/release/mihonapp/mihon-preview.svg?maxAge=3600&label=Beta&labelColor=2c2c47&color=1c1c39)](https://mihon.app/download)

*Requires Android 8.0 or higher.*

## Features

<div align="left">

* Local reading of content.
* A configurable reader with multiple viewers, reading directions and other settings.
* Tracker support: [MyAnimeList](https://myanimelist.net/), [AniList](https://anilist.co/), [Kitsu](https://kitsu.app/), [MangaUpdates](https://mangaupdates.com), [Shikimori](https://shikimori.one), and [Bangumi](https://bgm.tv/) support.
* Categories to organize your library.
* Light and dark themes.
* Schedule updating your library for new chapters.
* Create backups locally to read offline or to your desired cloud service.
* Plus much more...

</div>

## Contributing

[Code of conduct](./CODE_OF_CONDUCT.md) · [Contributing guide](./CONTRIBUTING.md)

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

Before reporting a new issue, take a look at the [FAQ](https://mihon.app/docs/faq/general), the [changelog](https://mihon.app/changelogs/) and the already opened [issues](https://github.com/mihonapp/mihon/issues); if you got any questions, join our [Discord server](https://discord.gg/mihon).


### Repositories

[![mihonapp/website - GitHub](https://github-readme-stats.vercel.app/api/pin/?username=mihonapp&repo=website&bg_color=161B22&text_color=c9d1d9&title_color=0877d2&icon_color=0877d2&border_radius=8&hide_border=true&description_lines_count=2)](https://github.com/mihonapp/website/)
[![mihonapp/bitmap.kt - GitHub](https://github-readme-stats.vercel.app/api/pin/?username=mihonapp&repo=bitmap.kt&bg_color=161B22&text_color=c9d1d9&title_color=0877d2&icon_color=0877d2&border_radius=8&hide_border=true&description_lines_count=2)](https://github.com/mihonapp/bitmap.kt/)

### Credits

Thank you to all the people who have contributed!

<a href="https://github.com/mihonapp/mihon/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=mihonapp/mihon" alt="Mihon app contributors" title="Mihon app contributors" width="800"/>
</a>

### Disclaimer

The developer(s) of this application does not have any affiliation with the content providers available, and this application hosts zero content.

### License

<pre>
Copyright © 2015 Javier Tomás
Copyright © 2024 Mihon Open Source Project

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
</pre>

</div>
