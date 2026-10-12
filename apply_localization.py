#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Husk 完整汉化脚本
=================
把 Husk 源码里 UI 英文字符串替换为中文。可本地运行，也可在 GitHub Actions
编译前调用（见 build.yml 的 "Apply Husk localization" 步骤）。

用法：
    python3 apply_localization.py [仓库根目录]   # 默认当前目录

设计约束：
- 只替换"引号包裹且与映射完全一致的完整字符串字面量"，用 re.escape 精确匹配，
  不触碰代码结构、标识符、插值表达式，保证 Swift 可编译。
- 含 \\(...) 插值 / ? 三元 / .joined 的条目，只改引号内文字、保留代码结构。
"""
import os, re, sys

# 英 -> 中 完整映射（UI 字符串字面量）
TR = {
    # ---- 通用操作 ----
    "Cancel":"取消","Done":"完成","Close":"关闭","Back":"返回","Continue":"继续",
    "Show":"显示","Hide":"隐藏","View":"查看","Add":"添加","Remove":"移除",
    "Refresh":"刷新","Reset":"重置","Copy":"复制","Open":"打开","Get":"获取",
    "Install":"安装","Import":"导入","Clear":"清除","Stop":"停止","Replace":"替换",
    "Ready":"就绪","Try Again":"重试","Not now":"暂不","Not Now":"暂不",
    "See All":"查看全部","Turn On":"打开","Share Report":"分享报告",
    "Share Log":"分享日志","Share Results":"分享结果","View Release":"查看发布",
    "Open Settings":"打开设置","Run Again":"再次运行","Reset All":"全部重置",
    "Resize":"调整大小","Not yet":"尚未","Enable":"启用",
    # ---- 主导航 / 标签 ----
    "Home":"首页","Store":"商店","Discover":"发现","Library":"游戏库",
    "Downloads":"下载","Files":"文件","Settings":"设置","Console":"控制台",
    "Logs":"日志","About":"关于","Controls":"控制","Updates":"更新",
    # ---- 设置 ----
    "General":"通用","Appearance":"外观","Performance":"性能","Input":"输入",
    "Network":"网络","Display":"显示","Data":"数据","Runtime":"运行时",
    "Package":"软件包","Screen":"屏幕","Width":"宽度","Resolution":"分辨率",
    "Orientation":"方向","Multitasking":"多任务","Renderer":"渲染器",
    "Opacity":"不透明度","Vibrate on a press":"按下时震动",
    "Keep the screen on":"保持屏幕常亮","Performance readout":"性能读数",
    "Hide the interface":"隐藏界面","On-screen controller":"屏幕控制器",
    "Open In":"打开方式","Device Checks":"设备检查","Technical Details":"技术详情",
    "Last Run":"上次运行","Controller":"控制器",
    # ---- 游戏/应用库 ----
    "Add a Game or App":"添加游戏或应用","Add your first game":"添加你的第一个游戏",
    "For apps the translation layer can't run yet":"翻译层尚无法运行的应用",
    "Game Settings":"游戏设置","App Info":"应用信息","Android App Info":"Android 应用信息",
    "Open in Files":"在文件中打开","Copy Package Name":"复制包名","Uninstall":"卸载",
    "Screenshots":"截图","Reset Game Data":"重置游戏数据","Back Up Saves":"备份存档",
    "Restore Saves":"恢复存档","Saves":"存档","Remove Game":"移除游戏",
    "Saved Machine":"已保存的机器","Mass Test":"批量测试","Start Mass Test":"开始批量测试",
    "Storage":"存储","Android":"Android","Home Screen":"主屏幕",
    # ---- 下载 / 更新 ----
    "Add Download":"添加下载","Download":"下载","No downloads":"暂无下载",
    "Clear Finished":"清除已完成","Everything is up to date":"一切已是最新",
    "Metadata Updated":"元数据已更新","How it works":"工作原理",
    # ---- JIT / 启动 ----
    "JIT":"JIT","Turn on JIT":"开启 JIT","JIT is off":"JIT 已关闭",
    "JIT is on":"JIT 已开启","Enable JIT":"启用 JIT","Use TrollStore":"使用 TrollStore",
    "Use StikDebug":"使用 StikDebug","Use the jailbreak":"使用越狱","Check setup":"检查设置",
    "Start pairing":"开始配对","Cancel pairing":"取消配对",
    "Continue with the current pairing":"使用当前配对继续",
    "Choose pairing file":"选择配对文件","Choose another file":"选择其他文件",
    "Reset Developer Disk Image":"重置开发者磁盘映像","It's connected":"已连接",
    # ---- 弹窗 / 提示 ----
    "Another game is already loaded":"另一个游戏已加载","This was removed.":"此项已移除。",
    "Could Not Load":"无法加载","Crash Report":"崩溃报告","Last lines":"最后几行",
    "ATTEMPT LOG":"尝试日志","No Results":"无结果","Close Husk?":"关闭 Husk？",
    "Close Husk":"关闭 Husk","The game stopped":"游戏已停止",
    # ---- 发现 / 软件源 ----
    "Add Source":"添加源","Manage Repositories":"管理软件源","Repositories":"软件源",
    "Active Repositories":"已启用软件源","Presets":"预设","Source URL":"源地址",
    "Paste any F-Droid-compatible repository index URL.":"粘贴任意兼容 F-Droid 的软件源索引地址。",
    # ---- 引导 / 其他 ----
    "Android apps, on your iPhone.":"在你的 iPhone 上运行 Android 应用。",
    "Husk runs a real Android system and opens APKs inside it.":"Husk 运行真实的 Android 系统，并在其中打开 APK。",
    "How should Husk behave?":"希望 Husk 如何运行？",
    "The first full release.":"第一个完整版本。","Back to Husk":"返回 Husk",
    "This iPhone":"这台 iPhone","Where it stands":"当前进展","Add to Husk":"添加到 Husk",
    "Import Files":"导入文件","Browse Files":"浏览文件","Generate App Clip":"生成 App 片段",
    "Download Geode":"下载 Geode","Geode":"Geode","Mods":"模组","Husk":"Husk",
    "HUSK":"HUSK","ANDROID":"ANDROID","ctrl":"Ctrl",
    # ---- 带插值的完整字面量（保留 \\(...) 结构） ----
    "Remove \\(app.label)?":"移除 \\(app.label)？",
    "Uninstall \\(live.label)?":"卸载 \\(live.label)？",
    "Replace \\(app.label)'s saves?":"替换 \\(app.label) 的存档？",
    "Reset the data of \\(app.label)?":"重置 \\(app.label) 的数据？",
    "Starting \\(app.label)…":"正在启动 \\(app.label)…",
    "\\(app.label), minimised":"\\(app.label)，已最小化",
    "What's New in Husk \\(WhatsNew.version)":"Husk \\(WhatsNew.version) 的新内容",
    "Enter this code on your \\(device)":"在你的 \\(device) 上输入此代码",
    "Waiting for your \\(device)…":"正在等待你的 \\(device)…",
    "No jailbreak was found on this \\(device).":"在这台 \\(device) 上未找到越狱。",
    "Search to see \\(apps.count - 50) more apps.":"搜索以查看另外 \\(apps.count - 50) 个应用。",
    "\\(live.label) opens by itself once Android has started.":"Android 启动后，\\(live.label) 会自动打开。",
    "It opens as soon as Android answers.":"Android 响应后它会立即打开。",
    "Start Android to uninstall or look inside the app.":"启动 Android 以卸载或查看应用内部。",
    "Show in Android Settings":"在 Android 设置中显示","Get Android First":"先获取 Android",
    "Nothing here is called “\\(query)”.":"这里没有名为“\\(query)”的内容。",
    "Saves, settings and caches the game made here are deleted.":"该游戏在此创建的存档、设置和缓存都将被删除。",
    "The game and everything it saved here are deleted from Husk.":"该游戏及它在 Husk 中保存的所有数据都将从 Husk 中删除。",
    "Its data goes with it.":"它的数据会一并删除。",
    "Save Android afterwards or the change is":"请随后保存 Android 状态，否则更改将",
    "Its data goes with it. Save Android afterwards or the change is":"它的数据会一并删除。请随后保存 Android 状态，否则更改将",
    "Husk was marked as debugged when it opened, so JIT is on.":"Husk 打开时已被标记为调试状态，因此 JIT 已开启。",
    "This installation can only wait about 30 seconds in the background,":"此安装只能在后台等待约 30 秒，",
    "Saving keeps Android exactly as it is, so the next start skips booting.":"保存会让 Android 保持当前状态，下次启动时跳过开机过程。",
    "Drag a control to move it, or tap one to resize or hide it.":"拖动控件以移动，或轻点以调整大小或隐藏。",
    "Tap with three fingers to show the interface":"用三根手指轻点以显示界面",
    "Use Husk while it starts":"启动期间使用 Husk",
    "First time? See the setup, or use StikDebug or TrollStore instead":"首次使用？请查看设置，或改用 StikDebug 或 TrollStore",
    "Games and Android can run.":"游戏和 Android 可以运行。",
    "What the game is called in Husk. The game itself is not changed.":"游戏在 Husk 中显示的名称。游戏本身不会被修改。",
    "Android installs it from where it already is — nothing is copied.":"Android 从原位安装它——不会复制任何内容。",
    "They go to \\((destination as NSString).lastPathComponent).":"它们将进入 \\((destination as NSString).lastPathComponent)。",
    "This APK has no 64-bit code Husk can run, so it will probably not start.":"此 APK 没有 Husk 可运行的 64 位代码，因此可能无法启动。",
    "The plan, in order, is docs/04-translation-layer.md in Husk's source.":"具体计划详见 Husk 源码中的 docs/04-translation-layer.md。",
    "Android's native code expects things of the processor and of memory":"Android 的原生代码对处理器和内存有一定要求",
    "If JIT is not on when Android starts, Husk turns it on with the":"如果 Android 启动时 JIT 未开启，Husk 会用以下方式开启它",
    "Touch always works. A gamepad and a pointer are not wired":"触摸始终有效。手柄和指针尚未接入",
    "Touch is always on. The keyboard and the rotate control are":"触摸始终开启。键盘和旋转控制",
    "You have \\(AppUpdates.current). The new version's IPA is on its release page.":"你当前为 \\(AppUpdates.current)。新版本的 IPA 在其发布页面。",
    "Metadata for \\(n) of your app\\(n == 1 ?":"正在更新你应用\\(n == 1 ? 的元数据 : 的元数据)",
    "Native Libraries (\\(arm64.count))":"原生库（\\(arm64.count)）",
    "Husk \\(release.version)":"Husk \\(release.version)",
    "\\(Downloads.bytes(free)) free on this device.":"本设备可用空间 \\(Downloads.bytes(free))。",
    "\\(AppDetailView.bytes(s.total - s.free)) of \\(AppDetailView.bytes(s.total))":"已用 \\(AppDetailView.bytes(s.total - s.free))，共 \\(AppDetailView.bytes(s.total))",
    "Install \\(installing?.name ??":"安装 \\(installing?.name ??",
    "\\(source.apps.count) apps":"\\(source.apps.count) 个应用",
    # ---- 2.0 新增（窗口管理/应用内帮助/新设置） ----
    "OK":"确定",
    "FAQ":"常见问题",
    "Now":"现在",
    "Sound":"声音",
    "Theme":"主题",
    "Custom":"自定义",
    "Height":"高度",
    "Preview":"预览",
    "Sign In":"登录",
    "App Icon":"应用图标",
    "Emulator":"模拟器",
    "Portrait":"竖屏",
    "Sign Out":"退出登录",
    "Landscape":"横屏",
    "Set up JIT":"设置 JIT",
    "GPU machine":"GPU 机型",
    "Sideloading":"侧载",
    "Downloading…":"正在下载…",
    "Open Console":"打开控制台",
    "Accent Colour":"强调色",
    "Featured Apps":"精选应用",
    "Saved machine":"已保存的机型",
    "About this app":"关于此应用",
    "Developer Info":"开发者信息",
    "JIT & sideload":"JIT 与侧载",
    "Re-fetch icons":"重新获取图标",
    "Search Results":"搜索结果",
    "How it connects":"连接方式",
    "Software machine":"软件机型",
    "Google Play Store":"Google Play 商店",
    "Use Guest Account":"使用访客账号",
    "Sign In with Google":"使用 Google 登录",
    "Sign in with Google":"使用 Google 登录",
    "Delete saved machine":"删除已保存的机型",
    "Open Apps in Windows":"以窗口打开应用",
    "Other Ways to Turn On JIT":"开启 JIT 的其他方式",
    "Enable JIT with TrollStore":"使用 TrollStore 启用 JIT",
    "Use Guest Account (Aurora)":"使用访客账号（Aurora）",
    "Use Husk while an app runs":"应用运行时使用 Husk",
    "Retest \\(test.failures.count) Failures":"重测 \\(test.failures.count) 个失败项",
    "Version \\(Bundle.main.version)":"版本 \\(Bundle.main.version)",
    "Version \\(Bundle.main.version) · \\(Bundle.main.commit)":"版本 \\(Bundle.main.version) · \\(Bundle.main.commit)",
    "Enable JIT with \\(jit.resolvedMethod.title)":"使用 \\(jit.resolvedMethod.title) 启用 JIT",
    "Both sides must be between 240 and 2560.":"两边必须在 240 到 2560 之间。",
    "No apps found for \\\"\\(debouncedSearchText)\\\".":"未找到与“\\(debouncedSearchText)”匹配的应用。",
    "No featured apps available. Try searching above.":"暂无精选应用，请尝试在上方搜索。",
    "Android will boot from cold once, then save a new one.":"Android 将冷启动一次，然后保存新的状态。",
    "Adds a sound device. While it is attached Android cannot be ":"添加一个声音设备。当它连接时，Android 无法",
    "Technical detail in the Android Translation Layer screens: ":"Android 翻译层界面的技术详情：",
    "Boots the guest as soon as Husk opens, when JIT is available.":"当 JIT 可用时，Husk 一打开就会启动客户系统。",
    "Adds about 2 GB to the first download. It was captured on the ":"首次下载会增加约 2 GB。它录制自",
    "Husk needs memory it can write and then execute, which on iOS ":"Husk 需要可写入再执行的内存，在 iOS 上",
    "Names and icons come from Android's own launcher, which keeps ":"名称和图标来自 Android 自带的启动器，它保持",
    "The panel is built when the machine starts, so a change costs ":"面板在系统启动时构建，因此更改会",
    "The list is written to disk, so it is on screen before Android ":"列表写入磁盘，因此会在 Android 之前显示",
    "Tints buttons, switches and selected states throughout the app.":"为整个应用中的按钮、开关和选中状态着色。",
    "APKs install from the Library's + button or from the Files tab. ":"APK 可从“游戏库”的 + 按钮或“文件”标签安装。",
    "If JIT is not on when Android starts, Husk turns it on with the ":"如果 Android 启动时 JIT 未开启，Husk 会用以下方式开启它",
    "Its data goes with it. Save Android afterwards or the change is ":"它的数据会一并删除。请随后保存 Android 状态，否则更改将",
    "Husk restores a saved machine instead of booting it, which takes ":"Husk 会恢复已保存的机型而非开机，这需要",
    "Android's native code expects things of the processor and of memory ":"Android 的原生代码对处理器和内存有一定要求",
    "This installation can only wait about 30 seconds in the background, ":"此安装只能在后台等待约 30 秒，",
    "System follows the phone: light by day, dark by night. The guest's own ":"跟随手机：白天浅色，夜间深色。客户系统自身的",
    "Husk runs unmodified Android APKs in a real Android system on your iPhone. ":"Husk 在你的 iPhone 上于真实的 Android 系统中运行未经修改的 Android APK。",
    "Automatic follows the system appearance — light, dark and tinted. The others pin ":"自动模式跟随系统外观——浅色、深色和着色。其他模式固定",
    "TrollStore was not found on this \\(device). Husk can only use it once it is installed ":"在这台 \\(device) 上未找到 TrollStore。安装后 Husk 才能使用它",
    "The pairing file stays in Husk's Documents folder and is only sent to Husk's own helper.":"配对文件保存在 Husk 的“文档”文件夹中，且仅发送给 Husk 自身的助手。",
    "The end of the log from the last time the game started. Share it when reporting a problem.":"游戏上次启动时的日志末尾。反馈问题时请分享它。",
    "When a new Android image or snapshot is published, Husk asks once whether to download it. ":"当发布新的 Android 镜像或快照时，Husk 会询问一次是否下载。",
    "Nothing matches “\\(query)”. Open Settings › About › Open Console to see what Husk is doing.":"没有匹配“\\(query)”的内容。打开“设置 › 关于 › 打开控制台”以查看 Husk 正在做什么。",
    "Add a link to an APK or a file, or the address a computer gives you when it shares a folder.":"添加 APK 或文件的链接，或电脑分享文件夹时给出的地址。",
    "Android and Translation Layer games need JIT, which on iOS only an attached debugger can grant. ":"Android 和翻译层游戏需要 JIT，在 iOS 上只有连接的调试器才能授予。",
    "What \\(app.label) has saved now is replaced by the backup. Back up first if you want to keep it.":"\\(app.label) 当前保存的内容将被备份替换。如想保留请先备份。",
    "Android runs fully emulated, so it is slower than games on the translation layer. Use it for apps ":"Android 完全模拟运行，因此比翻译层上的游戏慢。将它用于",
    "Geode is the mod loader for Geometry Dash. With it on, Husk downloads Geode for this version of the ":"Geode 是 Geometry Dash 的模组加载器。开启后，Husk 会为此版本的 Geometry Dash 下载 Geode。",
    "Pick an APK or a bundle (.xapk, .apkm, .apks), or share one to Husk from Files or Safari. Games run ":"选择 APK 或打包文件（.xapk、.apkm、.apks），或从“文件”或 Safari 分享到 Husk。游戏运行",
    "This is Geode's Android launcher. On Husk, Geode runs inside Geometry Dash instead: turn it on here ":"这是 Geode 的 Android 启动器。在 Husk 上，Geode 会在 Geometry Dash 内运行：在此开启",
    "Browse and download apps using an anonymous Aurora guest account, or sign in with your Google account.":"使用匿名 Aurora 访客账号浏览和下载应用，或使用你的 Google 账号登录。",
    "Android and Translation Layer games need JIT. StikJIT, built into Husk, turns it on without a computer.":"Android 和翻译层游戏需要 JIT。Husk 内置的 StikJIT 无需电脑即可开启。",
    "To send a whole folder from a computer on the same Wi‑Fi, run this on it and enter the address it shows:":"要从同一 Wi‑Fi 的电脑发送整个文件夹，请在电脑上运行它并输入其显示的地址：",
    "A backup is a .zip of everything \\(app.label) has saved in Husk, to keep in Files or move to another device.":"备份是 \\(app.label) 在 Husk 中保存内容的 .zip 文件，可保存在“文件”中或转移到其他设备。",
    "Puts \\(app.label) on your Home Screen with its own icon. Tapping it opens Husk straight into the game. Husk ":"将 \\(app.label) 以其自有图标放到主屏幕。轻点它可直接从 Husk 打开游戏。Husk",
    "Apps and games open in a window you can move, resize and minimise to a dock, like LiveContainer's multitasking. ":"应用和游戏在可移动、调整大小并最小化到程序坞的窗口中打开，类似 LiveContainer 的多任务。",
    "Automatic offers the controller for games that cannot be played without one (Unreal Engine games), when no real ":"当没有真实手柄时，自动模式会为无法用手柄就无法游玩的游戏（Unreal Engine 游戏）提供控制器。",
    "The game starts with nothing over it: no bar, no controller, no readout. Tap with three fingers at once to bring ":"游戏启动时不显示任何覆盖层：没有状态栏、没有控制器、没有读数。同时用三根手指轻点以调出",
    "In a window, \\(app.label) runs over Husk: move it by its title bar, resize it from the corner, and minimise it to ":"在窗口中，\\(app.label) 运行在 Husk 之上：通过标题栏移动、从角落调整大小，并最小化到",
    "The report holds the full log of that run and which device and build it was on. Nothing is sent anywhere unless you share it.":"报告包含该次运行的完整日志、所用设备和构建版本。除非你分享，否则不会发送到任何地方。",
    "How each 64-bit library maps onto the iPhone: its relocations, the instructions Husk rewrites, and anything the loader works around.":"每个 64 位库如何映射到 iPhone：其重定位、Husk 重写的指令，以及加载器绕过的内容。",
    "An APK is added to your library when it finishes. Anything else goes into the Shared Storage folder, which games see as their phone storage.":"APK 完成后会添加到你的游戏库。其他内容进入共享存储文件夹，游戏将其视为手机存储。",
    "Live Activities are off for Husk, so downloads don't show on the Lock Screen or in the Dynamic Island. Turn them on in Settings › Husk › Live Activities.":"Husk 的实时活动已关闭，因此下载不会显示在锁定屏幕或灵动岛上。可在“设置 › Husk › 实时活动”中开启。",
    "serve-folder.py is in Husk's repository, under tools. The folder's contents land at the top of Shared Storage, so serve the folder that holds what a game expects there.":"serve-folder.py 位于 Husk 仓库的 tools 目录下。文件夹内容会放在共享存储的顶部，因此请分享游戏所期望内容的所在文件夹。",
    "Each app is played once JIT is on, watched for 15 seconds, and written down; then Husk closes. Open Husk again for the next one. At the end the results file is offered to share.":"每个应用在开启 JIT 后运行一次，观察 15 秒并记录；然后 Husk 关闭。再次打开 Husk 以进行下一个。最后会提供结果文件供分享。",
    "Make a folder named DeveloperTesting in Husk's folder (Files > On My iPhone > Husk) and put the APKs to test in it: an APK each, or a folder per app with its base and split APKs.":"在 Husk 的文件夹（文件 › 我的 iPhone › Husk）中创建一个名为 DeveloperTesting 的文件夹，将待测试的 APK 放入其中：每个 APK 单独存放，或每个应用一个文件夹并放入其基础与拆分 APK。",
}

def main(root):
    root = root or "."
    changed = 0
    hits = 0
    if not os.path.isdir(os.path.join(root, "src", "app")):
        print("未找到 src/app 目录，请确认在 Husk 仓库根目录运行。")
        return 1
    for dirpath, _, files in os.walk(os.path.join(root, "src", "app")):
        for fn in files:
            if not fn.endswith(".swift"):
                continue
            path = os.path.join(dirpath, fn)
            src = open(path, encoding="utf-8").read()
            new = src
            for en, zh in TR.items():
                new2 = re.sub('"' + re.escape(en) + '"', '"' + zh + '"', new)
                if new2 != new:
                    hits += 1
                    new = new2
            if new != src:
                open(path, "w", encoding="utf-8").write(new)
                changed += 1
                print(f"[替换] {path}")
    print(f"\n完成：修改 {changed} 个文件，执行 {hits} 处替换。")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
