import re
import sys

from automac import AutoMac, InputLangs


def cask_full(cask, app, enable_notifications=True):
    if not mac.app_exists(app):
        mac.brew.install_cask(cask)
    mac.quarantine_remove_app(app)
    mac.notifications.change_app(app, enable_notifications)


with AutoMac() as mac:
    mac = mac  # type: AutoMac # wtf pycharm :(
    mac.add_lookup_folder('~/Dropbox/config/macos')

    if not mac.file_exists('~/Dropbox'):
        mac.brew.install_homebrew()
        mac.brew.analytics_off()
        cask_full('dropbox', 'Dropbox')
        mac.manual_step('Start Dropbox; sync config folder; start this script again')
        sys.exit(0)

    mac.brew.install_homebrew()
    mac.brew.analytics_off()
    # mac.brew.install_casks('brew-cask-basic.txt')
    # app.brew.install_formulas('brew-formula-basic.txt')
    mac.brew.install_formulas('brew-formula-mini.txt')

    mac.mkdirs('~/bin', '~/.secrets', '~/venv', '~/tmp', '~/projects')
    mac.link('~/Dropbox', '~/d')
    mac.unset_hidden_flag('~/Library')
    # mac.unset_hidden_flag('/Volumes')

    mac.link('~/Dropbox/config/dotfiles/bashrc.sh', '~/.bashrc')
    mac.link('~/Dropbox/config/dotfiles/bash_profile.sh', '~/.bash_profile')
    mac.link('~/Dropbox/config/dotfiles/vimrc.txt', '~/.vimrc')
    mac.link('~/Dropbox/config/dotfiles/curlrc.txt', '~/.curlrc')
    mac.link('~/Dropbox/config/dotfiles/inputrc.txt', '~/.inputrc')
    mac.link('~/Library/Preferences', '~/prefs')
    mac.link('~/Library/Application Support', '~/appsup')

    mac.link('~/Dropbox/config/sublime/User', '~/Library/Application Support/Sublime Text/Packages/User')
    # MANUAL STEP: Start Sublime; install package control; packages will be installed automatically

    if re.match('XKPWR...YP', mac.get_machine_serial()):
        mac.all_computer_names('bmp')
    elif mac.is_virtual_machine():
        mac.all_computer_names(f'vm-{mac.get_mac_version_str().replace(".", "-")}')

    if mac.is_virtual_machine():
        mac.screen_lock_off('1111')

    mac.user_shell('/opt/homebrew/bin/bash')

    mac.timezone('Europe/Moscow')

    # mac.keyboard_languages_abc_and_ru_pc()
    mac.keyboard_languages(InputLangs.EN_US, InputLangs.RU_PC)
    mac.keyboard_navigation_enable()

    mac.trackpad_tap_to_click()
    mac.trackpad_drag_three_fingers()

    mac.menubar_input_language_show()
    mac.menubar_date_hide()
    mac.menubar_dow_hide()
    mac.menubar_spotlight_hide()

    mac.dock_minimize_window_into_app_icon()
    mac.dock_icon_size(38)
    mac.dock_orientation_left()

    mac.close_windows_when_quitting_an_app()

    mac.trash_empty_warning_disable()

    mac.finder_file_extensions_show()
    mac.finder_file_extensions_rename_silently()
    mac.finder_view_as_list()
    mac.finder_default_folder_downloads()
    # mac.finder_sort_folders_atop(True)
    # mac.finder_path_in_title(True)

    mac.locale_region('en_US', 'EUR')
    mac.locale_preferred_languages('en-US', 'ru-RU')
    mac.locale_temperature_celsius()
    # mac.locale_temperature_fahrenheit()
    mac.locale_metric()
    mac.locale_date_format_iso()
    mac.locale_first_day_monday()
    # mac.locale_time_format_12h()
    mac.locale_time_format_24h()

    mac.theme_dark()

    mac.desktop_iphone_widgets_disable()

    cask_full('dropbox', 'Dropbox')
    cask_full('appcleaner', 'AppCleaner')
    # cask_full('brave-browser', 'Brave Browser')
    cask_full('iina', 'IINA.app')
    cask_full('iterm2', 'iTerm.app')
    cask_full('keepassxc', 'KeePassXC.app')
    # cask_full('pycharm-ce', 'PyCharm CE.app')
    cask_full('sublime-text', 'Sublime Text.app')
    cask_full('telegram', 'Telegram.app')
    cask_full('topnotch', 'TopNotch.app')
    # cask_full('dbeaver-community', 'DBeaver')
    # cask_full('openmtp', 'OpenMTP')

    mac.notifications.enable_app(
        '/Applications/Brave Browser.app/Contents/Frameworks/Brave Browser Framework.framework/Versions/Current/Helpers/Brave Browser Helper (Alerts).app')

    (mac.notifications
     .disable_bundle_id('com.apple.tips')
     .disable_bundle_id('com.apple.Music')
     .disable_bundle_id('com.apple.news')
     .disable_bundle_id('com.apple.TV')
     .disable_bundle_id('com.apple.Photos')
     .disable_bundle_id('com.apple.studentd.notifications')
     .disable_bundle_id('com.apple.Maps')
     .disable_bundle_id('com.apple.voicebanking.usernotifications'))

    # todo `plist` - WARNING Failed reassigning `plist` from `com.apple.dt.Xcode` to `com.sublimetext.4` with role `editor`. Probably you want a stronger role: `editor` or `all`
    text_files = 'bash bat cfg css groovy gradle java js json kt log m md nfo php properties ps1 py rb reg sh sublime-syntax todo treetop txt xml yaml yml csv srt vtt'.split()
    video_files = 'avi divx flv m4v mkv mov mp4 mpg vob webm wmv'.split()
    audio_files = 'aac aif aiff ape fla flac m4a mp3 ogg wav wma'.split()
    mac.assoc_file_extensions_editor('Sublime Text', text_files)
    mac.assoc_file_extensions_viewer('IINA', video_files)
    mac.assoc_file_extensions_viewer('IINA', audio_files)

    (mac.appcleaner
     .update_disable()
     .analytics_off()
     .mark_as_launched_before())

    (mac.iterm2
     .update_disable()
     .analytics_off()
     .quit_silently()
     .quit_when_all_windows_closed())

    mac.login_items_add('/Applications/TopNotch.app')
    mac.run_app('TopNotch')
