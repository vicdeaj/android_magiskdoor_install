APP_BUILD_SCRIPT := Android.mk
APP_ABI          := armeabi-v7a arm64-v8a x86 x86_64
APP_CFLAGS       := -Wall -Oz -fomit-frame-pointer -flto
APP_LDFLAGS      := -flto
APP_CPPFLAGS     := -std=c++20
APP_STL          := none
APP_PLATFORM     := android-21
APP_THIN_ARCHIVE := true
APP_STRIP_MODE   := --strip-all
