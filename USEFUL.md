# convert plist into xml IN-PLACE

    plutil -convert xml1 xxx.plist

# notifications flags

    flags = 1351102785 | 1010000100010000011000101000001 |    | Base, everything deactivated
    flags = 1384657217 | 1010010100010000011000101000001 | 25 | Active
    flags = 1384657225 | 1010010100010000011000101001001 |  3 | Appearance: Banners
    flags = 1384657233 | 1010010100010000011000101010001 |  4 | Appearance: Alerts
    flags = 1921528129 | 1110010100010000011000101000001 | 29 | Allow time-sensitive alerts
    flags = 1384653121 | 1010010100010000010000101000001 | 12 | Show notifications on Lock Screen
    flags = 1384657216 | 1010010100010000011000101000000 |  0 | Show in Notification Centre
    flags = 1384657219 | 1010010100010000011000101000011 |  1 | Badge application icon
    flags = 1384657221 | 1010010100010000011000101000101 |  2 | Play sound for notification
    
    "content_visibility" = 0 | Show previews: Default
    "content_visibility" = 1 | Show previews: Never
    "content_visibility" = 2 | Show previews: When Unlocked
    "content_visibility" = 3 | Show previews: Always
    
    grouping = 0 | Notification grouping: Automatic
    grouping = 1 | Notification grouping: By Application
    grouping = 2 | Notification grouping: Off

    src: https://github.com/jalmeroth/ncprefs/issues/1

# notifications related

- https://github.com/jalmeroth/ncprefs/
- https://github.com/jacobsalmela/NCutil

org.chromium.Chromium 8396814  00000000100000000010000000001110
org.chromium.Chromium 41951246 00000010100000000010000000001110
org.chromium.Chromium.framework.AlertNotificationService 8396822  00000000100000000010000000010110
org.chromium.Chromium.framework.AlertNotificationService 41951254 00000010100000000010000000010110

00000000100000000010000000001110 - badges, sounds, banners
00000000100000000010000000010110 - badges, sounds, alerts

# menu bar clock setup

https://github.com/tech-otaku/menu-bar-clock

# utils to manage app capabilities to access folders and devices

- https://github.com/carlashley/tccprofile
- https://github.com/jslegendre/tccplus

# xcode cli tools version compatibility

| macos | tools      |
|-------|------------|
| 13.6  | 14.3       |
| 14.7  | 14.3, 15.3 |
| 15.0  | 16.0       |
