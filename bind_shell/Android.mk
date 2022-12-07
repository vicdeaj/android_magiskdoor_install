LOCAL_PATH := $(call my-dir)

include $(CLEAR_VARS)
LOCAL_MODULE := revshell
LOCAL_LDLIBS := -llog

LOCAL_SRC_FILES := \
	revshell.cpp

include $(BUILD_EXECUTABLE)
